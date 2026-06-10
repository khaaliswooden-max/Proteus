"""F0 runner plumbing tests.

These tests validate the harness ITSELF, not the benchmark. They cover:
  - schema acceptance / rejection of bundle_manifest_hash mismatches
  - the runner's stop-token / first-line answer extraction (F-A2 from LOOP_A)
  - windowed-entropy aggregation matches calibration/fit_band semantics
  - resumability: re-running with a partial output file skips done work

A second test class exercises the FULL F0 pipeline against a stub model. It is
skipped unless the env var PROTEUS_F0_STUB_MODEL points at a small GGUF file
(TinyLlama, Qwen2.5-0.5B-Instruct, etc.). Stub runs MUST emit
`"stub_validation": true` — that's the assertion that prevents a stub run from
ever masquerading as a measured F0 result.

  PROTEUS_F0_STUB_MODEL=~/models/tinyllama.gguf python -m pytest harness/tests
"""
from __future__ import annotations

import json
import os
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def test_schema_rejects_wrong_manifest_hash():
    from harness.results.schema import F0Results
    bad = {
        "schema_version": "proteus-f0-results-v1",
        "bundle_manifest_hash": "0" * 64,  # not the v1.0.2 hash
        "bundle_ledger_entry": 4,
        "llama_cpp_build_hash": "deadbeef",
        "model_sha256": "0" * 64,
        "hardware_tag": {"cpu_model": "x", "ram_gb": 32, "gpu_model_or_none": None,
                         "os": "linux", "threads_used": 8},
        "decoding": {},
        "calibration": None,
        "f0_scores": {},
        "seeds": [1, 2, 3, 5, 8],
        "ts_run_start_utc": "2026-06-10T00:00:00Z",
        "ts_run_end_utc": "2026-06-10T00:00:01Z",
        "tokens_generated": 0,
    }
    with pytest.raises(Exception) as ei:
        F0Results.model_validate(bad)
    assert "bundle_manifest_hash" in str(ei.value)


def test_schema_rejects_wrong_ledger_entry():
    from harness.results.schema import F0Results, BUNDLE_MANIFEST_HASH_V1_0_2
    bad = {
        "schema_version": "proteus-f0-results-v1",
        "bundle_manifest_hash": BUNDLE_MANIFEST_HASH_V1_0_2,
        "bundle_ledger_entry": 99,  # not #0004
        "llama_cpp_build_hash": "deadbeef",
        "model_sha256": "0" * 64,
        "hardware_tag": {"cpu_model": "x", "ram_gb": 32, "gpu_model_or_none": None,
                         "os": "linux", "threads_used": 8},
        "decoding": {},
        "calibration": None,
        "f0_scores": {},
        "seeds": [1, 2, 3, 5, 8],
        "ts_run_start_utc": "2026-06-10T00:00:00Z",
        "ts_run_end_utc": "2026-06-10T00:00:01Z",
        "tokens_generated": 0,
    }
    with pytest.raises(Exception) as ei:
        F0Results.model_validate(bad)
    assert "ledger_entry" in str(ei.value) or "LEDGER" in str(ei.value)


def test_schema_accepts_well_formed_stub_result():
    from harness.results.schema import F0Results, BUNDLE_MANIFEST_HASH_V1_0_2
    good = {
        "schema_version": "proteus-f0-results-v1",
        "bundle_manifest_hash": BUNDLE_MANIFEST_HASH_V1_0_2,
        "bundle_ledger_entry": 4,
        "llama_cpp_build_hash": "deadbeef",
        "model_sha256": "0" * 64,
        "hardware_tag": {"cpu_model": "x", "ram_gb": 32, "gpu_model_or_none": None,
                         "os": "linux", "threads_used": 8},
        "decoding": {"temperature_task": 0.7, "top_p_task": 0.95,
                     "temperature_canary": 0.0, "n_ctx": 8192,
                     "scaffold_max_tokens_per_turn": 1024, "entropy_window": 64},
        "calibration": None,
        "f0_scores": {},
        "seeds": [1, 2, 3, 5, 8],
        "ts_run_start_utc": "2026-06-10T00:00:00Z",
        "ts_run_end_utc": "2026-06-10T00:00:01Z",
        "tokens_generated": 0,
        "stub_validation": True,
    }
    r = F0Results.model_validate(good)
    assert r.stub_validation is True


# ---------------------------------------------------------------------------
# Stop-token + first-line extraction (F-A2)
# ---------------------------------------------------------------------------

def test_first_line_answer_strips_stop_markers():
    from harness.f0.run_f0 import _first_line_answer
    s = "RESULT: 42 /end\n<|im_end|> garbage that should not leak\nstray"
    assert _first_line_answer(s) == "RESULT: 42 /end"


def test_first_line_answer_skips_blanks():
    from harness.f0.run_f0 import _first_line_answer
    assert _first_line_answer("\n\n  hello world\n") == "hello world"


def test_trim_stops_idempotent():
    from harness.f0.run_f0 import _trim_stops
    assert _trim_stops("abc</s>def") == "abc"
    assert _trim_stops("plain") == "plain"


# ---------------------------------------------------------------------------
# Windowed entropy aggregation
# ---------------------------------------------------------------------------

def test_windowed_means_matches_window_size():
    from harness.f0.run_f0 import _windowed_means, ENTROPY_WINDOW
    vals = [float(i) for i in range(ENTROPY_WINDOW * 3 + 7)]
    out = _windowed_means(vals, ENTROPY_WINDOW)
    # 3 full windows + 1 partial
    assert len(out) == 4
    # first window mean = (0 + ... + W-1) / W
    expected_first = (ENTROPY_WINDOW - 1) / 2
    assert abs(out[0] - expected_first) < 1e-9


# ---------------------------------------------------------------------------
# Bundle imports are clean and unmodified
# ---------------------------------------------------------------------------

def test_bundle_modules_importable_and_pure():
    """The runner must import bundle modules without copying or mutating them."""
    import harness.f0.run_f0 as rf  # noqa: F401
    bench = REPO_ROOT / "proteus-bench-v1.0.2"
    # Bench dir must still exist as committed.
    assert (bench / "MANIFEST.json").exists()
    manifest = json.loads((bench / "MANIFEST.json").read_text())
    assert manifest["manifest_hash"] == (
        "3d14ac4b77deede20daae1b319bb5c370b71db83c58c693587651d9cf4856e58"
    )


# ---------------------------------------------------------------------------
# Resumability — partial output file is read, completed work skipped
# ---------------------------------------------------------------------------

def test_resumability_load_partial(tmp_path):
    from harness.f0.run_f0 import _load_partial, _atomic_write_json
    p = tmp_path / "partial.json"
    payload = {"records": [{"seed": 1, "episode_id": "ep-000", "turn": 0}]}
    _atomic_write_json(str(p), payload)
    got = _load_partial(str(p))
    assert got == payload


def test_resumability_load_missing_returns_none(tmp_path):
    from harness.f0.run_f0 import _load_partial
    assert _load_partial(str(tmp_path / "nope.json")) is None


# ---------------------------------------------------------------------------
# Full stub-model end-to-end (skipped without a model)
# ---------------------------------------------------------------------------

STUB_MODEL = os.environ.get("PROTEUS_F0_STUB_MODEL")
stub_required = pytest.mark.skipif(
    not STUB_MODEL or not pathlib.Path(os.path.expanduser(STUB_MODEL)).exists(),
    reason="PROTEUS_F0_STUB_MODEL unset — plumbing-only checks require a small GGUF.",
)


@stub_required
def test_calibration_pass_stub_writes_valid_artifact(tmp_path):
    from harness.f0.run_f0 import f0_calibration_pass, _file_sha256
    model = os.path.expanduser(STUB_MODEL)
    out = tmp_path / "f0_calibration_stub.json"
    payload = f0_calibration_pass(
        model_path=model,
        out_path=str(out),
        model_sha256=_file_sha256(model),
        n_threads=4,
        stub_validation=True,
        n_prompts=3,
    )
    assert payload["stub_validation"] is True
    assert payload["bundle_manifest_hash"] == (
        "3d14ac4b77deede20daae1b319bb5c370b71db83c58c693587651d9cf4856e58"
    )
    assert payload["summary"]["n_prompts"] == 3
    assert "fit_input" in payload


@stub_required
def test_t_can_baseline_stub_writes_valid_artifact(tmp_path):
    from harness.f0.run_f0 import f0_baseline_t_can, _file_sha256
    model = os.path.expanduser(STUB_MODEL)
    out = tmp_path / "f0_t_can_stub.json"
    payload = f0_baseline_t_can(
        model_path=model,
        out_path=str(out),
        model_sha256=_file_sha256(model),
        n_threads=4,
        stub_validation=True,
    )
    assert payload["stub_validation"] is True
    assert payload["suite"] == "T-CAN"
    assert payload["summary"]["n_tasks"] == 100
