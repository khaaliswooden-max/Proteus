# `harness/` — Proteus Phase 5 F0 Baseline Harness

This directory is the **engineering** half of Phase 5. The **benchmark** half is
`proteus-bench-v1.0.2/`, sealed by LEDGER #0004 and OTS-anchored. The two stay
categorically apart on purpose: a bundle that measures itself is not a benchmark.

## Why `harness/` is separate from `proteus-bench-v1.0.2/`

`proteus-bench-v1.0.2/` is the contract. It is committed, hashed
(`MANIFEST.json` → `3d14ac4b…`), signed (LEDGER #0004), and OTS-stamped
(`BUNDLE_HASH.txt.ots`). Threshold changes after commit require a versioned
re-commit per ZCS-6 — never a silent edit (see `docs/METHODOLOGY.md` and
BENCHMARK §8).

`harness/` is the *solution-side* code that gets *measured against* that
contract. It imports the bundle modules unmodified, executes them, and emits
results in a schema designed to be falsifiable against the BENCHMARK §4
thresholds. Mixing the two would create exactly the silent-edit hazard ZCS-6
exists to prevent: a change to the contract masked as a change to the runner.

## Directory layout

```
harness/
├── ENVIRONMENT.md         # pinned externalities: build hash, model SHA, decoding
├── README.md              # this file
├── requirements.txt       # pinned Python deps (==, never >=)
├── f0/
│   ├── cli.py             # `python -m harness.f0.cli {calibrate,band,baseline}`
│   └── run_f0.py          # the four F0 functions (T-PA / T-DS / T-CAN + calibration)
├── model/                 # operator drops the GGUF here (not committed)
├── results/
│   ├── SCHEMA.md          # human-readable description of the artifact schema
│   ├── schema.py          # canonical Pydantic model (`F0Results`)
│   └── schema.json        # derived JSON Schema (emit with --emit-json)
└── tests/
    └── test_f0_stub.py    # unit tests (plumbing) + optional stub-model E2E
```

## Reproducibility chain

The whole point of this harness is to bind a measured number to a fingerprint
that an outside party can re-derive. The chain:

```
LEDGER #0004 signed (visionblox-release-key-v1)
  └─> proteus-bench-v1.0.2/MANIFEST.json
       └─> bundle_manifest_hash = 3d14ac4b77deede20daae1b319bb5c370b71db83c58c693587651d9cf4856e58
            └─> llama_cpp build hash (HASH PENDING — locked at first F0 run)
                 └─> model SHA-256 (HASH PENDING — locked at first download)
                      └─> hardware_tag + decoding params (logged per run)
                           └─> harness/results/f0_*.json (the deliverable)
```

The schema (`harness/results/schema.py`) enforces the first two links by
rejecting any result file whose `bundle_manifest_hash` or `bundle_ledger_entry`
disagrees with the committed v1.0.2 values. The CLI enforces the third by
refusing to run if the model file's actual SHA-256 disagrees with the value
in `ENVIRONMENT.md` (unless `--stub` is passed, in which case the artifact is
flagged accordingly).

## What is a *measured* F0 result vs. a *stub* validation run

A **measured F0 result** has, in this exact order:

1. A locked llama.cpp build hash recorded in `ENVIRONMENT.md`.
2. A locked Mistral-7B-Instruct-v0.3 Q4_K_M SHA-256 recorded in `ENVIRONMENT.md`.
3. A run on hardware that fits the BENCHMARK §2 envelope, with a `hardware_tag`
   logged in the results file.
4. Decoding params exactly matching `DecodingParams` defaults (frozen by §2).
5. Seeds `[1, 2, 3, 5, 8]` (no subset, no superset).
6. Episodes per suite per seed: 10 (T-PA, T-DS) or the full 100 (T-CAN).
7. `"stub_validation": false` in the artifact.

A **stub validation run** is anything else. The CLI tags it `stub_validation:
true` automatically when the recorded hash is `HASH PENDING`, when `--stub`
is passed, or when the model SHA-256 does not match the recorded value.

Stub runs validate **plumbing**, not capability. They are not F0 results and
must never be presented as such.

## How an outside party reproduces these results

1. `git clone` this repo, check out the commit/tag that landed the measured F0.
2. `cat proteus-bench-v1.0.2/BUNDLE_HASH.txt` and verify the OTS attestation:
   `ots verify proteus-bench-v1.0.2/BUNDLE_HASH.txt.ots`.
3. Verify LEDGER #0004 against `keys/visionblox_release_v1.pub` (use the
   committed `auditor/verify_chain.py` — it imports nothing from this repo's
   solution code, so it's not self-attesting).
4. Read `harness/ENVIRONMENT.md` for the locked llama.cpp build hash and model
   SHA-256.
5. Build llama.cpp at the recorded commit hash; `pip install -r
   harness/requirements.txt`.
6. Download Mistral-7B-Instruct-v0.3 Q4_K_M; verify its SHA-256.
7. `python -m harness.f0.cli calibrate --model … --out …` then
   `python -m harness.f0.cli band --entropies … --out …` then
   `python -m harness.f0.cli baseline --suite T-PA … --suite T-DS …
    --suite T-CAN …`.
8. Compare your results file to the committed one — per BENCHMARK §2, CPU
   inference is deterministic per build hash, so the comparison is exact, not
   statistical.

## References

- BENCHMARK §2 / §4 / §8 — `proteus-bench-v1.0.2/BENCHMARK_v1.0.2.md`.
- ZCS-6 Phase 5 — `docs/METHODOLOGY.md`.
- Epistemic markers (VERIFIED / PLAUSIBLE / SPECULATIVE) — `docs/EPISTEMIC_FRAMEWORK.md`.
- First closed-loop dev run (the source of F-A2, F-A3, F-B1) —
  `LOOP_A_RUN_REPORT.md`.
- Phase 5 Week 1 runbook — `PHASE_5_WEEK_1_RUNBOOK.md`.

## Status

**This PR adds scaffolding only.** No measured F0 runs are included.
Outputs in `harness/results/` from CI or stub validation are tagged
`"stub_validation": true`. The operator runs the harness on dedicated
hardware in a follow-up PR after this one merges, at which point the
llama.cpp build hash and model SHA-256 are locked in `ENVIRONMENT.md`.

## Markers

- **VERIFIED**: deterministic CPU inference per build hash; schema rejects
  non-matching manifest hashes; bundle imports succeed unmodified
  (`test_bundle_modules_importable_and_pure`).
- **PLAUSIBLE**: the harness will produce F0 floor numbers that B2/B3/B4 can
  later be compared against. This is a structural claim about the artifact
  shape; the numerical claim is PLAUSIBLE until the operator's measured run
  lands.
- **SPECULATIVE**: nothing in this PR. Speculative content belongs in
  `docs/SIXTH_ROAD.md` and downstream documents, not in the runner.
