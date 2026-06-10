# Changelog

All notable changes to Proteus are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [Semantic Versioning](https://semver.org/) for code and benchmark major/minor/patch for committed bundles. Each entry referencing a benchmark version also points to the relevant `DELTA_*.md`.

## [Unreleased]

### Phase 5 work in progress
- F-A3 — graded nonconformity for ACI skill proxy (planned).
- F0 baseline on Mistral-7B-Instruct-v0.3 (planned; pins llama.cpp build hash).

## [0.1.0] — 2026-06-09 — Initial public release

### Added
- **Repository structure** under Apache 2.0 with full document suite (README, NOTICE, CITATION.cff, SECURITY, CONTRIBUTING, CODE_OF_CONDUCT, GOVERNANCE, ROADMAP, EPISTEMIC_FRAMEWORK, ARCHITECTURE, METHODOLOGY, SIXTH_ROAD).
- **`proteus-bench-v1.0.1/`** — committable benchmark bundle (PROTEUS-002). 10 files. Manifest hash `03e27b6284405adb3dcdae5587be7f58cdb28677a2556105f710284cb4355bb6`. OpenTimestamps-stamped 2026-06-10T03:30Z (Bitcoin attestation pending block confirmation).
- **`loop_a/`** — reference implementation:
  - `loop_a.py` — `EntropySignal` (windowed pre-sampling entropy, calibration-percentile challenge proxy), `ACISkill` (corrected-sign Adaptive Conformal Inference skill proxy), `FlowBandController` (banded controller with hysteresis, m=3).
  - `chain.py` — `StateChain` writer matching the committed auditor schema (SQLite, SHA-256 linkage, Ed25519 signatures).
  - `run_synthetic.py` — closed-loop validation on declared synthetic plant; 5 paired seeds × 60 turns.
  - `run_live.py` — real-model integration using exact full-vocab logit entropy.
- **`LOOP_A_RUN_REPORT.md`** — first-run findings, scope statements, residual gaps.
- **`CLAUDE_ledger_commit_runbook.md`** — operational runbook for completing Phase 4 in Claude Code / Cursor with explicit human-only signing boundaries.
- **`zil_sign.py`** — local signing ceremony script (keygen, sign, verify). Runs entirely on the operator's machine; private key never leaves.

### Methodology milestones
- Hostile review of benchmark v1.0 → 12 findings (2 critical), all addressed in v1.0.1. See `proteus-bench-v1.0.1/HOSTILE_REVIEW_DELTA.md`.
- First Loop A run found:
  - **F-A1** — controller saturation produced signed no-op adaptation events; caught by the committed auditor (exit 4) at first contact. Fixed in `loop_a.py`.
  - **F-B1** — committed staircase prompts named two contradictory evaluation orders (50/60 task divergence). Versioned-update repair: v1.0 → v1.0.1, wording-only, zero answers changed. See `proteus-bench-v1.0.1/DELTA_v1.0.1.md`.
  - **F-A2** — dev harness stop-token handling for Qwen chat template; fixed in `run_live.py`.
  - **F-A3** — ACI skill proxy saturates at competence floor with binary outcomes; open, scheduled for v0.2.

### Provenance
- Benchmark v1.0 (PROTEUS-001), manifest `a802d7e0…d3ff2331`, OTS-stamped, **superseded** by v1.0.1 with documented defect.
- LEDGER #0004 signing **pending operator action** (see `CLAUDE_ledger_commit_runbook.md`).

## Versioning policy

- **Bundle versions** (`proteus-bench-vX.Y.Z`) are append-only and OTS-stamped; defects produce a superseding version with a `DELTA_vX.Y.Z.md` record. No in-place edits, ever.
- **Code versions** (`loop_a`, etc.) follow SemVer. Public API stability begins at v1.0.0 (not yet reached).
- **Repository tags** of the form `bench-v1.0.1` mark the commit that introduced a bundle; never moved.
