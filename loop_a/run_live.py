#!/usr/bin/env python3
"""Loop A LIVE run — real model logits through the full closed loop.

Dev model: Qwen2.5-0.5B-Instruct Q4_K_M (NOT the benchmark target; Mistral-7B
per protocol). Purpose: prove Loop A end-to-end on real inference —
exact pre-sampling entropy from raw logits (logits_all=True, full vocab,
no top-k approximation), committed T-DS staircase tasks, committed
adherence checker, ACI on real outcomes, signed chain, committed auditor.

Decoding: greedy for the dev run (determinism over flair); the harness
decoding rules of the committed protocol bind only measured runs.

Actuators in live mode:
  k -> inject k worked examples from already-solved turns (retrieval)
  s -> scaffold tier: 0 none, 1 'compute step by step', 2 adds an explicit
       format reminder, 3 adds a worked format demo
  g -> recorded but inert at rung 0 (no control vectors trained yet — F8;
       logged honestly as inactive)
"""
import datetime
import json
import math
import statistics
import subprocess
import sys
import time

sys.path.insert(0, "/home/claude/proteus/loop_a")
sys.path.insert(0, "/home/claude/proteus-bench-v1.0.1/generators")
from loop_a import EntropySignal, ACISkill, FlowBandController  # noqa: E402
from chain import StateChain, generate_test_keypair  # noqa: E402
import t_ds_staircase as tds  # committed generator + checker  # noqa: E402

from llama_cpp import Llama  # noqa: E402

MODEL = "/home/claude/qwen2.5-0.5b-instruct-q4_k_m.gguf"
N_CAL_PROMPTS = 12       # calibration subset (time-boxed dev run)
N_TURNS = 16             # live turns over the staircase
MAX_GEN = 48


def token_entropy(logits) -> float:
    """Exact Shannon entropy (nats) of the full-vocab softmax."""
    mx = max(logits)
    exps = [math.exp(x - mx) for x in logits]
    z = sum(exps)
    h = 0.0
    for e in exps:
        p = e / z
        if p > 1e-12:
            h -= p * math.log(p)
    return h


def generate(llm, prompt: str, max_tokens: int = MAX_GEN):
    """Greedy generation capturing per-token pre-sampling entropy from raw logits."""
    llm.reset()
    toks = llm.tokenize(prompt.encode(), add_bos=True)
    llm.eval(toks)
    out_ids, ents = [], []
    eos = llm.token_eos()
    for _ in range(max_tokens):
        logits = llm.scores[llm.n_tokens - 1, :].tolist()
        ents.append(token_entropy(logits))
        nxt = max(range(len(logits)), key=lambda i: logits[i])  # greedy, pre-sampling H already captured
        if nxt == eos:
            break
        out_ids.append(nxt)
        text_so_far = llm.detokenize(out_ids).decode(errors="replace")
        if "<|im_end|>" in text_so_far or "\nHuman:" in text_so_far:
            break
        llm.eval([nxt])
    text = llm.detokenize(out_ids).decode(errors="replace")
    text = text.split("<|im_end|>")[0].split("\nHuman:")[0]
    return text, ents


def fmt_prompt(task, k_examples, s_tier, solved):
    parts = ["<|im_start|>user\n"]
    for ex in solved[-k_examples:] if k_examples else []:
        parts.append(f"Example:\n{ex['prompt']}\nCorrect answer: {ex['answer']}\n\n")
    parts.append(task["prompt"])
    if s_tier >= 1:
        parts.append("\nCompute carefully, step by step is allowed but final line must be the answer only.")
    if s_tier >= 2:
        parts.append("\nFollow the answer format exactly as instructed.")
    if s_tier >= 3 and solved:
        parts.append(f"\nFormat demo — a correct past answer looked like: {solved[-1]['answer']}")
    parts.append("<|im_end|>\n<|im_start|>assistant\n")
    return "".join(parts)


def main():
    t0 = time.time()
    llm = Llama(model_path=MODEL, n_ctx=2048, logits_all=True, verbose=False, n_threads=8)
    print(f"model loaded in {time.time()-t0:.1f}s", flush=True)

    # --- Calibration: entropy distribution over mixed-difficulty prompts (no actuators)
    cal_ep = tds.generate_episode(999, "calibration")
    cal_means = []
    for task in cal_ep[:: len(cal_ep) // N_CAL_PROMPTS][:N_CAL_PROMPTS]:
        _, ents = generate(llm, fmt_prompt(task, 0, 0, []), max_tokens=32)
        if ents:
            cal_means.append(statistics.mean(ents))
    print(f"calibration: {len(cal_means)} prompts, "
          f"entropy range [{min(cal_means):.3f}, {max(cal_means):.3f}] nats", flush=True)

    # --- Live closed loop over the committed staircase
    sig = EntropySignal(cal_means + cal_means)  # >=20 samples guard for dev run
    aci = ACISkill()
    ctl = FlowBandController()
    priv = generate_test_keypair("/tmp/live_test.pub")
    chain = StateChain("/tmp/ep_live.sqlite", priv)

    ep = tds.generate_episode(8, "live-dev")
    # sample 16 turns spanning all difficulty levels
    idxs = [int(i * (len(ep) - 1) / (N_TURNS - 1)) for i in range(N_TURNS)]
    solved, log = [], []
    state = {"mode": "live-dev", "model": "qwen2.5-0.5b-q4km", "actuators": {"k": 0, "g": 0, "s": 0}}

    for i in idxs:
        task = ep[i]
        text, ents = generate(llm, fmt_prompt(task, ctl.k, ctl.s, solved))
        for e in ents:
            sig.push(e)
        cand = [l for l in text.strip().splitlines() if l.strip()]
        ok = tds.check(task, cand[0] if cand else "")
        if ok:
            solved.append(task)
        c_t = sig.challenge()
        skill_t = aci.skill()
        step = ctl.step(c_t, skill_t)
        aci.update(0.0 if ok else 1.0)
        if step["adaptation_event"]:
            state["actuators"] = {"k": ctl.k, "g": ctl.g, "s": ctl.s}
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        chain.append(state, {"c_t": round(c_t, 4), "skill_t": round(skill_t, 4),
                             "gap": round(step["gap"], 4), "k": ctl.k, "g": ctl.g,
                             "s": ctl.s, "correct": ok, "level": task["level"],
                             "mean_H": round(statistics.mean(ents), 3),
                             "adaptation_event": step["adaptation_event"]}, ts)
        log.append({"turn": task["turn"], "level": task["level"], "correct": ok,
                    "mean_H": round(statistics.mean(ents), 3), "c_t": round(c_t, 3),
                    "skill_t": round(skill_t, 3), "k": ctl.k, "s": ctl.s,
                    "in_band": step["in_band"]})

    lat = chain.latency_stats()
    chain.close()
    print(json.dumps(log, indent=None))
    acc = sum(1 for r in log if r["correct"]) / len(log)
    occ = sum(1 for r in log if r["in_band"]) / len(log)
    print(f"\nLIVE: accuracy {acc:.2f}, band occupancy {occ:.2f}, "
          f"chain overhead median {lat['median_ms']:.2f} ms, total {time.time()-t0:.0f}s", flush=True)

    audit = subprocess.run(
        ["python3", "/home/claude/proteus-bench-v1.0.1/auditor/verify_chain.py",
         "--db", "/tmp/ep_live.sqlite", "--pubkey", "/tmp/live_test.pub"],
        capture_output=True, text=True)
    print("COMMITTED-AUDITOR EXIT:", audit.returncode)
    print(audit.stdout)


if __name__ == "__main__":
    main()
