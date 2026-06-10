"""F0 baseline runner — Phase 5 Week 1.

F0 means: committed model + frozen decoding + committed bench tasks, with
**all Proteus loops disabled**. No controller, no signal, no chain. Just the
floor that B2/B3/B4 will later be compared against.

The committed bundle modules are imported AS-IS from the repo, never copied,
never modified. Modifying them would be a benchmark edit (out of scope for this
runbook and forbidden by §0).

Each `f0_*` function is independently runnable, idempotent, and resumable:
if its output file already contains a record for some (seed, episode_id), that
work is skipped on re-run.

This module is invoked by `harness/f0/cli.py`, not directly.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import math
import os
import pathlib
import statistics
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable

# --- Repo paths --------------------------------------------------------------

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
BENCH = REPO_ROOT / "proteus-bench-v1.0.2"
CANARY_TASKS = BENCH / "canary" / "t_can_tasks.json"

# Import committed bundle modules as-is (runbook §3).
sys.path.insert(0, str(BENCH / "generators"))
sys.path.insert(0, str(BENCH / "calibration"))

import t_pa_pool  # noqa: E402
import t_ds_staircase as t_ds  # noqa: E402
import t_can_generate  # noqa: E402
import fit_band  # noqa: E402

# --- Schema constants --------------------------------------------------------

from harness.results.schema import (  # noqa: E402
    BUNDLE_LEDGER_ENTRY,
    BUNDLE_MANIFEST_HASH_V1_0_2,
)

# --- Frozen decoding (BENCHMARK §2) ------------------------------------------

DECODING_TASK = {"temperature": 0.7, "top_p": 0.95}
DECODING_CANARY = {"temperature": 0.0}  # greedy
N_CTX = 8192
SCAFFOLD_MAX_TOKENS = 1024
ENTROPY_WINDOW = 64

# T-PA episode shape — turns and convention introduction per BENCHMARK §3.
T_PA_TURNS = 40
T_PA_INTRO_TURNS = 5

# Per-turn max generation tokens — engineering choice, sized to fit the
# scaffold + answer + a few step lines comfortably under N_CTX with full history.
MAX_GEN_TASK = 256
MAX_GEN_CANARY = 64
MAX_GEN_CAL = 128


# --- Stop-token handling (F-A2 from LOOP_A_RUN_REPORT.md) --------------------

STOP_MARKERS = (
    "<|im_end|>",
    "</s>",
    "<|endoftext|>",
    "<|eot_id|>",
    "\nHuman:",
    "\nUser:",
)


def _trim_stops(text: str) -> str:
    out = text
    for s in STOP_MARKERS:
        out = out.split(s)[0]
    return out


def _first_line_answer(text: str) -> str:
    """Per F-A2: take the first non-empty stripped line as the answer."""
    for line in _trim_stops(text).strip().splitlines():
        if line.strip():
            return line.strip()
    return ""


# --- Model wrapper -----------------------------------------------------------

@dataclass
class ModelHandle:
    """Thin wrapper around llama-cpp-python with logits_all=True.

    We import llama_cpp lazily so the schema, CLI parsing, and result
    validation all work in environments without the model runtime installed
    (e.g. the PR-review CI sandbox).
    """
    model_path: str
    model_sha256: str
    n_threads: int
    seed: int | None = None
    _llm: Any = None

    def open(self) -> None:
        from llama_cpp import Llama  # local import — see class docstring
        kwargs = dict(
            model_path=self.model_path,
            n_ctx=N_CTX,
            logits_all=True,
            verbose=False,
            n_threads=self.n_threads,
        )
        if self.seed is not None:
            kwargs["seed"] = self.seed
        self._llm = Llama(**kwargs)

    def close(self) -> None:
        self._llm = None

    def tokenize(self, text: str) -> list[int]:
        return self._llm.tokenize(text.encode(), add_bos=True)

    def detokenize(self, ids: list[int]) -> str:
        return self._llm.detokenize(ids).decode(errors="replace")

    def token_eos(self) -> int:
        return self._llm.token_eos()

    def eval(self, ids: list[int]) -> None:
        self._llm.eval(ids)

    @property
    def n_tokens(self) -> int:
        return self._llm.n_tokens

    def last_logits(self) -> list[float]:
        return self._llm.scores[self._llm.n_tokens - 1, :].tolist()


# --- Entropy + sampling ------------------------------------------------------

def shannon_entropy_nats(logits: Iterable[float]) -> float:
    """Exact Shannon entropy (nats) of the full-vocab softmax."""
    lg = list(logits)
    mx = max(lg)
    exps = [math.exp(x - mx) for x in lg]
    z = sum(exps)
    h = 0.0
    for e in exps:
        p = e / z
        if p > 1e-12:
            h -= p * math.log(p)
    return h


def _sample_top_p(logits: list[float], temperature: float, top_p: float,
                  rng: "Any") -> int:
    """Top-p sampling on temperature-scaled logits. Used for non-greedy suites.

    `rng` is a `random.Random` seeded by the runner so seed bookkeeping stays
    explicit. For greedy decoding (T-CAN), the caller picks argmax directly
    and never enters this path.
    """
    import numpy as np
    arr = np.asarray(logits, dtype=np.float64) / max(temperature, 1e-9)
    arr -= arr.max()
    p = np.exp(arr)
    p /= p.sum()
    order = np.argsort(-p)
    sorted_p = p[order]
    cum = np.cumsum(sorted_p)
    cutoff = np.searchsorted(cum, top_p) + 1
    keep = order[:cutoff]
    mass = p[keep] / p[keep].sum()
    r = rng.random()
    c = 0.0
    for idx, m in zip(keep, mass):
        c += float(m)
        if r <= c:
            return int(idx)
    return int(keep[-1])


def _greedy_argmax(logits: list[float]) -> int:
    best_i, best_v = 0, logits[0]
    for i in range(1, len(logits)):
        if logits[i] > best_v:
            best_i, best_v = i, logits[i]
    return best_i


# --- Generation primitives ---------------------------------------------------

def generate_with_entropy(
    mh: ModelHandle,
    prompt: str,
    *,
    max_tokens: int,
    decoding: dict,
    rng: "Any",
) -> tuple[str, list[float]]:
    """Generate up to `max_tokens` tokens, capturing per-token pre-sampling entropy.

    Returns `(decoded_text, per_token_entropy_nats)`.
    """
    import random  # noqa: F401 — declared so callers can pass `random.Random`
    mh._llm.reset()
    toks = mh.tokenize(prompt)
    mh.eval(toks)
    out_ids: list[int] = []
    ents: list[float] = []
    eos = mh.token_eos()
    greedy = decoding.get("temperature", 0.0) == 0.0
    for _ in range(max_tokens):
        logits = mh.last_logits()
        ents.append(shannon_entropy_nats(logits))
        if greedy:
            nxt = _greedy_argmax(logits)
        else:
            nxt = _sample_top_p(
                logits,
                temperature=decoding["temperature"],
                top_p=decoding["top_p"],
                rng=rng,
            )
        if nxt == eos:
            break
        out_ids.append(nxt)
        partial = mh.detokenize(out_ids)
        if any(s in partial for s in STOP_MARKERS):
            break
        mh.eval([nxt])
    text = mh.detokenize(out_ids)
    text = _trim_stops(text)
    return text, ents


def _windowed_means(values: list[float], window: int = ENTROPY_WINDOW) -> list[float]:
    """Non-overlapping window means; matches calibration/fit_band.py semantics."""
    if not values:
        return []
    out: list[float] = []
    for i in range(0, len(values), window):
        chunk = values[i:i + window]
        if chunk:
            out.append(statistics.mean(chunk))
    return out


# --- File I/O + resumability -------------------------------------------------

def _load_partial(path: str) -> dict | None:
    p = pathlib.Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _atomic_write_json(path: str, payload: dict) -> None:
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(p)


def _now_utc_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _envelope(suite: str, model_path: str, model_sha256: str, *,
              stub_validation: bool, seeds: list[int]) -> dict:
    return {
        "schema_version": "proteus-f0-results-v1",
        "bundle_manifest_hash": BUNDLE_MANIFEST_HASH_V1_0_2,
        "bundle_ledger_entry": BUNDLE_LEDGER_ENTRY,
        "suite": suite,
        "model_path": model_path,
        "model_sha256": model_sha256,
        "decoding": {
            "task": DECODING_TASK,
            "canary": DECODING_CANARY,
            "n_ctx": N_CTX,
            "scaffold_max_tokens_per_turn": SCAFFOLD_MAX_TOKENS,
            "entropy_window": ENTROPY_WINDOW,
        },
        "seeds": seeds,
        "stub_validation": stub_validation,
        "ts_run_start_utc": _now_utc_iso(),
        "records": [],
        "summary": {},
    }


# --- Calibration -------------------------------------------------------------

def f0_calibration_pass(
    model_path: str,
    out_path: str,
    *,
    model_sha256: str,
    n_threads: int = 8,
    stub_validation: bool = False,
    n_prompts: int | None = None,
) -> dict:
    """Run the 200-prompt calibration set, log windowed entropies per prompt.

    Output JSON is suitable as input to `fit_band.py --fit` (a list of per-prompt
    lists of windowed mean entropies, plus the provenance envelope).
    """
    prompts_blob = fit_band.emit_prompts()
    prompts = prompts_blob["prompts"]
    if n_prompts is not None:
        prompts = prompts[:n_prompts]

    payload = _load_partial(out_path) or _envelope(
        "calibration", model_path, model_sha256,
        stub_validation=stub_validation, seeds=[],
    )
    done_ids = {r["cal_id"] for r in payload["records"]}
    if not done_ids:
        payload["ts_run_start_utc"] = _now_utc_iso()

    mh = ModelHandle(model_path=model_path, model_sha256=model_sha256,
                     n_threads=n_threads, seed=0)
    mh.open()
    try:
        import random as _r
        rng = _r.Random(0)
        for p in prompts:
            if p["cal_id"] in done_ids:
                continue
            _, ents = generate_with_entropy(
                mh, p["prompt"], max_tokens=MAX_GEN_CAL,
                decoding=DECODING_TASK, rng=rng,
            )
            windows = _windowed_means(ents, ENTROPY_WINDOW)
            payload["records"].append({
                "cal_id": p["cal_id"],
                "kind": p["kind"],
                "n_tokens": len(ents),
                "windowed_entropies": windows,
            })
            _atomic_write_json(out_path, payload)
    finally:
        mh.close()

    # Shape that fit_band.fit() expects: list[list[float]]
    payload["fit_input"] = [r["windowed_entropies"] for r in payload["records"]]
    payload["summary"] = {
        "n_prompts": len(payload["records"]),
        "n_windows_total": sum(len(r["windowed_entropies"]) for r in payload["records"]),
    }
    payload["ts_run_end_utc"] = _now_utc_iso()
    _atomic_write_json(out_path, payload)
    return payload


# --- Suite: T-PA -------------------------------------------------------------

def _t_pa_prompt(history: list[dict], conventions: list[dict], task_text: str,
                 *, turn: int) -> str:
    """Build a T-PA turn prompt under the 1024-token scaffold cap.

    Conventions are introduced explicitly across turns 1..5 (BENCHMARK §3).
    From turn 6 onward they remain part of the visible system instruction, since
    F0 has no consolidation mechanism to internalize them — that's the whole
    point of F0 as the floor for B2.
    """
    lines: list[str] = []
    lines.append("System: Follow every convention below in every reply.")
    for c in conventions[: min(len(conventions), max(1, turn))]:
        lines.append(f"- {c['desc']}")
    lines.append("")
    for h in history[-4:]:  # keep prior 4 turns visible (engineering choice; ≤1024 tokens)
        lines.append(f"User: {h['user']}")
        lines.append(f"Assistant: {h['assistant']}")
    lines.append(f"User: {task_text}")
    lines.append("Assistant:")
    return "\n".join(lines)


def _t_pa_episode_tasks(episode_seed: int, episode_id: str) -> list[str]:
    """Produce 40 simple user turns. These exist to surface adherence pressure
    on the conventions; they are NOT task-accuracy probes (T-DS is for that)."""
    import random as _r
    rng = _r.Random(hashlib.sha256(
        f"{episode_seed}|{episode_id}|TPA-USER-TURNS".encode()
    ).digest())
    topics = ["a city", "a job", "a book", "an idea", "a problem",
              "a result", "a meeting", "a list", "a plan", "a rule"]
    verbs = ["describe", "summarize", "list facts about",
             "give one observation about", "compare two examples of"]
    turns: list[str] = []
    for _ in range(T_PA_TURNS):
        turns.append(f"Please {rng.choice(verbs)} {rng.choice(topics)} in one sentence.")
    return turns


def f0_baseline_t_pa(
    model_path: str,
    seeds: list[int],
    episodes: int,
    out_path: str,
    *,
    model_sha256: str,
    n_threads: int = 8,
    stub_validation: bool = False,
) -> dict:
    """Per-turn adherence scores under F0 (no Proteus loops)."""
    payload = _load_partial(out_path) or _envelope(
        "T-PA", model_path, model_sha256,
        stub_validation=stub_validation, seeds=list(seeds),
    )
    done = {(r["seed"], r["episode_id"], r["turn"]) for r in payload["records"]}

    pool = t_pa_pool.build_pool()

    mh = ModelHandle(model_path=model_path, model_sha256=model_sha256, n_threads=n_threads)
    mh.open()
    try:
        import random as _r
        for seed in seeds:
            for ep in range(episodes):
                episode_id = f"ep-{ep:03d}"
                conventions = t_pa_pool.draw_episode(pool, seed, episode_id, n=5)
                tasks = _t_pa_episode_tasks(seed, episode_id)
                history: list[dict] = []
                rng = _r.Random(int(hashlib.sha256(
                    f"{seed}|{episode_id}|TPA-DECODE".encode()
                ).hexdigest()[:16], 16))
                for turn, user_text in enumerate(tasks):
                    if (seed, episode_id, turn) in done:
                        history.append({"user": user_text, "assistant": "(skipped, prior run)"})
                        continue
                    prompt = _t_pa_prompt(history, conventions, user_text, turn=turn + 1)
                    text, _ents = generate_with_entropy(
                        mh, prompt, max_tokens=MAX_GEN_TASK,
                        decoding=DECODING_TASK, rng=rng,
                    )
                    answer = _first_line_answer(text)
                    per_conv = [bool(t_pa_pool.check(c, answer)) for c in conventions]
                    score = sum(per_conv) / max(1, len(per_conv))
                    payload["records"].append({
                        "seed": seed,
                        "episode_id": episode_id,
                        "turn": turn,
                        "score": score,
                        "per_convention": per_conv,
                        "convention_ids": [c["conv_id"] for c in conventions],
                    })
                    history.append({"user": user_text, "assistant": answer})
                    _atomic_write_json(out_path, payload)
    finally:
        mh.close()

    payload["summary"] = _summarize_t_pa(payload["records"])
    payload["ts_run_end_utc"] = _now_utc_iso()
    _atomic_write_json(out_path, payload)
    return payload


def _summarize_t_pa(records: list[dict]) -> dict:
    if not records:
        return {"adherence_rate": 0.0, "adherence_rate_turns_20_40": 0.0, "n_turns": 0}
    overall = statistics.mean(r["score"] for r in records)
    window = [r["score"] for r in records if 20 <= r["turn"] < 40]
    return {
        "adherence_rate": overall,
        "adherence_rate_turns_20_40": statistics.mean(window) if window else 0.0,
        "n_turns": len(records),
    }


# --- Suite: T-DS -------------------------------------------------------------

def _t_ds_prompt(task: dict) -> str:
    return f"User: {task['prompt']}\nAssistant:"


def f0_baseline_t_ds(
    model_path: str,
    seeds: list[int],
    episodes: int,
    out_path: str,
    *,
    model_sha256: str,
    n_threads: int = 8,
    stub_validation: bool = False,
) -> dict:
    """Per-turn accuracy + windowed entropy under F0."""
    payload = _load_partial(out_path) or _envelope(
        "T-DS", model_path, model_sha256,
        stub_validation=stub_validation, seeds=list(seeds),
    )
    done = {(r["seed"], r["episode_id"], r["turn"]) for r in payload["records"]}

    mh = ModelHandle(model_path=model_path, model_sha256=model_sha256, n_threads=n_threads)
    mh.open()
    try:
        import random as _r
        for seed in seeds:
            for ep in range(episodes):
                episode_id = f"ep-{ep:03d}"
                tasks = t_ds.generate_episode(seed, episode_id)
                rng = _r.Random(int(hashlib.sha256(
                    f"{seed}|{episode_id}|TDS-DECODE".encode()
                ).hexdigest()[:16], 16))
                for task in tasks:
                    if (seed, episode_id, task["turn"]) in done:
                        continue
                    prompt = _t_ds_prompt(task)
                    text, ents = generate_with_entropy(
                        mh, prompt, max_tokens=MAX_GEN_TASK,
                        decoding=DECODING_TASK, rng=rng,
                    )
                    answer = _first_line_answer(text)
                    correct = bool(t_ds.check(task, answer))
                    mean_h = statistics.mean(ents) if ents else None
                    payload["records"].append({
                        "seed": seed,
                        "episode_id": episode_id,
                        "turn": task["turn"],
                        "level": task["level"],
                        "correct": correct,
                        "mean_entropy": mean_h,
                        "windowed_entropies": _windowed_means(ents, ENTROPY_WINDOW),
                    })
                    _atomic_write_json(out_path, payload)
    finally:
        mh.close()

    payload["summary"] = _summarize_t_ds(payload["records"])
    payload["ts_run_end_utc"] = _now_utc_iso()
    _atomic_write_json(out_path, payload)
    return payload


def _summarize_t_ds(records: list[dict]) -> dict:
    if not records:
        return {"accuracy": 0.0, "n_turns": 0, "accuracy_per_level": {}}
    acc = statistics.mean(1.0 if r["correct"] else 0.0 for r in records)
    by_level: dict[int, list[float]] = {}
    for r in records:
        by_level.setdefault(r["level"], []).append(1.0 if r["correct"] else 0.0)
    return {
        "accuracy": acc,
        "n_turns": len(records),
        "accuracy_per_level": {str(k): statistics.mean(v) for k, v in sorted(by_level.items())},
    }


# --- Suite: T-CAN ------------------------------------------------------------

def f0_baseline_t_can(
    model_path: str,
    out_path: str,
    *,
    model_sha256: str,
    n_threads: int = 8,
    stub_validation: bool = False,
) -> dict:
    """Per-task correctness on the frozen 100-task canary set, greedy decoding."""
    tasks_blob = json.loads(CANARY_TASKS.read_text(encoding="utf-8"))
    tasks = tasks_blob["tasks"]

    payload = _load_partial(out_path) or _envelope(
        "T-CAN", model_path, model_sha256,
        stub_validation=stub_validation, seeds=[],
    )
    done = {r["task_id"] for r in payload["records"]}

    mh = ModelHandle(model_path=model_path, model_sha256=model_sha256,
                     n_threads=n_threads, seed=0)
    mh.open()
    try:
        import random as _r
        rng = _r.Random(0)  # unused — greedy path
        for task in tasks:
            if task["task_id"] in done:
                continue
            text, _ents = generate_with_entropy(
                mh, f"User: {task['prompt']}\nAssistant:",
                max_tokens=MAX_GEN_CANARY,
                decoding=DECODING_CANARY, rng=rng,
            )
            answer = _first_line_answer(text)
            correct = bool(t_can_generate.check(task, answer))
            payload["records"].append({
                "task_id": task["task_id"],
                "category": task["category"],
                "correct": correct,
            })
            _atomic_write_json(out_path, payload)
    finally:
        mh.close()

    correct_count = sum(1 for r in payload["records"] if r["correct"])
    payload["summary"] = {
        "correctness": correct_count / max(1, len(payload["records"])),
        "correct_count": correct_count,
        "n_tasks": len(payload["records"]),
    }
    payload["ts_run_end_utc"] = _now_utc_iso()
    _atomic_write_json(out_path, payload)
    return payload


# --- Band fitter wrapper -----------------------------------------------------

def fit_band_from_calibration(calibration_path: str, out_path: str) -> dict:
    """Run `fit_band.fit` against a calibration result file, write [theta_lo, theta_hi]."""
    data = json.loads(pathlib.Path(calibration_path).read_text(encoding="utf-8"))
    if "fit_input" not in data:
        raise ValueError(f"{calibration_path} missing 'fit_input'; "
                         f"was f0_calibration_pass() interrupted before summary?")
    # Pass the fit_input through a temp file so fit_band reads its own format.
    tmp = pathlib.Path(out_path).with_suffix(".fit_input.json")
    tmp.write_text(json.dumps(data["fit_input"]), encoding="utf-8")
    try:
        result = fit_band.fit(str(tmp))
    finally:
        tmp.unlink(missing_ok=True)
    band = {
        "schema_version": "proteus-f0-results-v1",
        "bundle_manifest_hash": BUNDLE_MANIFEST_HASH_V1_0_2,
        "bundle_ledger_entry": BUNDLE_LEDGER_ENTRY,
        "calibration_source": str(calibration_path),
        "model_sha256": data.get("model_sha256"),
        "stub_validation": data.get("stub_validation", False),
        "band": result,
        "ts": _now_utc_iso(),
    }
    _atomic_write_json(out_path, band)
    return band


# --- Hash check for the CLI --------------------------------------------------

def verify_model_sha256(model_path: str, expected: str | None) -> str:
    """Return the actual SHA-256 and raise if it doesn't match `expected`.

    `expected` may be `None` (no fingerprint locked yet) or the literal string
    `"HASH PENDING"` (the placeholder in ENVIRONMENT.md). In both cases the
    actual hash is returned without enforcement, and the caller is responsible
    for tagging the run `stub_validation=True`.
    """
    actual = _file_sha256(model_path)
    if expected and expected != "HASH PENDING" and expected.lower() != actual.lower():
        raise RuntimeError(
            f"model SHA-256 mismatch:\n  expected: {expected}\n  actual:   {actual}\n"
            f"Refusing to run. Update harness/ENVIRONMENT.md or use --stub."
        )
    return actual
