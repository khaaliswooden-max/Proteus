# Phase 5 — F0 Baseline Harness Environment

This file pins every externality between the committed `proteus-bench-v1.0.2/` bundle
(manifest `3d14ac4b77deede20daae1b319bb5c370b71db83c58c693587651d9cf4856e58`, LEDGER
entry #0004) and a measured F0 protocol run. Anything not pinned here is a hidden
actuator and a future replay defect.

Provenance markers in this document:
- **spec §** — value comes from `proteus-bench-v1.0.2/BENCHMARK_v1.0.2.md`. Not changeable here.
- **runbook** — value comes from `PHASE_5_WEEK_1_RUNBOOK.md`.
- **engineering choice** — value chosen for this harness; documented so it is auditable
  and reversible by a future PR (not a benchmark change).

## 1. llama.cpp build (HASH PENDING)

- **Upstream tag / release:** `b6500+` (engineering choice — recent stable tag at the
  time of first F0 run).
- **Upstream commit hash:** *HASH PENDING — to be locked by the operator at first F0
  run and recorded back here in the same PR that lands the first measured results.*
- **Why this build:** the first tagged release that contains the
  `logits_all`-compatible scoring path the runner needs for pre-sampling
  full-vocab Shannon entropy (see `harness/f0/run_f0.py`). Older builds lack the
  raw-logit surface that B3 requires.
- **Path / inference mode:** CPU only, per BENCHMARK §2 ("CPU path for all measured
  runs (deterministic per build [VERIFIED])"). GPU acceleration is **not** permitted
  for any result that will be compared against the committed thresholds.

Until the build hash is locked, every result produced by this harness is provisional
and MUST carry `"stub_validation": true` or an equivalent provenance flag.

## 2. Python and Python packages

- **Python:** 3.10+ (engineering choice — matches LEDGER #0004 toolchain).
- **Record exact `python --version` output here at first run:** *PENDING.*
- **Package pins:** see `harness/requirements.txt`. All pins use `==` (runbook §2),
  never `>=`, `~=`, or unconstrained.

## 3. Model fingerprint — Mistral-7B-Instruct-v0.3 Q4_K_M

- **Source:** Hugging Face repo `MaziyarPanahi/Mistral-7B-Instruct-v0.3-GGUF`,
  file `Mistral-7B-Instruct-v0.3.Q4_K_M.gguf`.
- **Revision:** *PENDING — pin to a specific commit / revision of the HF repo at
  first operator download. The HF "main" branch is not a fingerprint.*
- **Expected file size (bytes):** *PENDING — to be filled at first operator download.*
- **SHA-256:** **HASH PENDING** — populated at first operator download.
  Until this hash is locked, **every measured result is provisional**. The CLI
  refuses to run unless the model's actual SHA-256 matches the value recorded
  here (`cli.py --model` validates this before any inference; see runbook §4).

The model file lives outside the repo. The operator is expected to keep it at
`harness/model/Mistral-7B-Instruct-v0.3.Q4_K_M.gguf` or to supply `--model` to the
CLI. The path is **not** committed; only the hash is.

## 4. Decoding parameters (FROZEN by BENCHMARK §2 — never actuators)

These come directly from the benchmark spec. The harness echoes them into every
results artifact via `DecodingParams` in `harness/results/schema.py`. Any deviation
is a benchmark edit and out of scope for this runbook.

- **T-PA, T-PR, T-DS, calibration:** `temperature=0.7`, `top_p=0.95` (spec §2).
- **T-CAN:** `temperature=0` (greedy) (spec §2).
- **n_ctx:** `8192` (spec §2, cheat C2 — 8k cap).
- **Scaffold injections per turn:** `≤ 1024` tokens (spec §2, F7).
- **Seeds:** `{1, 2, 3, 5, 8}` (spec §2).
- **Episodes per suite per seed:** `10` (spec §2).
- **Entropy window (W):** `64` tokens (calibration/fit_band.py — frozen with the bundle).

The runner reads these constants from the schema, not from environment variables.
There is no `--temperature` flag on `cli.py` baseline subcommands.

## 5. Threading and hardware tags

- **n_threads:** engineering choice — recommended `n_threads = physical_cores`,
  recorded per run in `HardwareTag.threads_used`. Threading does **not** affect
  llama.cpp CPU determinism (per spec §2 VERIFIED claim), but it affects wall-time
  and must be logged for B6 latency interpretation.
- **Hardware tag schema:** `{cpu_model, ram_gb, gpu_model_or_none, os, threads_used}`
  — operator fills these from `/proc/cpuinfo`, `uname -a`, etc., at run time.
  Schema enforced by `HardwareTag` in `harness/results/schema.py`.

## 6. Output paths and idempotency

The CLI writes one self-contained JSON per suite under `harness/results/`:

| Subcommand | Default output path |
|---|---|
| `calibrate` | `harness/results/f0_calibration.json` |
| `band` | `harness/results/f0_band.json` |
| `baseline --suite T-PA` | `harness/results/f0_t_pa.json` |
| `baseline --suite T-DS` | `harness/results/f0_t_ds.json` |
| `baseline --suite T-CAN` | `harness/results/f0_t_can.json` |

Baseline suites are **idempotent and resumable**: if a partial output file exists,
completed `(seed, episode)` pairs are skipped. T-CAN runs the frozen 100-task set
in one pass; partial completion is supported at the task level.

## 7. Stub-model validation (not a measured run)

Plumbing is validated against any small GGUF (`TinyLlama`, `Qwen2.5-0.5B-Instruct`,
etc.) placed under `harness/tests/` or pointed at by `--model`. Stub outputs MUST
carry `"stub_validation": true` (set by the CLI when `--stub` is passed, also
detected by the schema validator when the model SHA-256 does not match the
Mistral-7B value in §3).

Stub runs validate plumbing, not capability. **They are not F0 results.**

## 8. What this file does not contain

- Any threshold from BENCHMARK §4. Those live in the spec, immutable.
- Any solution code parameters (Loop A actuators, ACI window, etc.). F0 means
  loops disabled; the harness imports the bundle generators and checker only.
- Any signing key material. Phase 5 results enter the record by PR review, not by
  signature, per runbook §0.
