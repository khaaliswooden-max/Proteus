# DELTA RECORD — proteus-bench v1.0 → v1.0.1 (PROTEUS-002)
## Versioned Benchmark Update — ZCS-6 Phase 5 → Phase 2 Back-Edge

**Trigger:** First live Loop A run (2026-06-09, dev model Qwen2.5-0.5B, real full-vocab logits, committed staircase tasks) returned 0.00 accuracy. Diagnosis isolated a defect in the committed bundle, distinct from dev-model weakness.

## Defect (F-B1)

`generators/t_ds_staircase.py` prompt line read: *"Compute, left to right with standard precedence: {expr}"* — naming **two contradictory evaluation orders** in one instruction. Ground truth was bound to strict left-to-right evaluation. Measured divergence: **50/60 tasks** in episode (seed 8, "live-dev") yield different answers under the two readings. A model correctly applying standard precedence — the more natural reading — is scored wrong on those 50 tasks. The assertion suite built on T-DS (B3 occupancy with accuracy non-inferiority) would have measured instruction-ambiguity tolerance, not difficulty calibration.

## Change

| File | Change | Answers affected |
|---|---|---|
| `generators/t_ds_staircase.py` | Prompt wording → *"Compute strictly left to right, ignoring standard operator precedence:"* | **None** — ground truth was already left-to-right; verified identical across all 5 committed seeds |
| `calibration/fit_band.py` | Structured calibration prompts given the same unambiguous wording (consistency; entropy-only, no ground truth) | None |

**No thresholds changed. No assertions changed. No task answers changed. No seeds changed.** This is a defect repair to the measurement instrument, not a goalpost move — the pass/fail surface is strictly clarified, not relaxed.

## Why this is the legal path

The v1.0 bundle is OTS-stamped (`a802d7e0…d3ff2331`); in-place modification is cryptographically impossible, which is the designed behavior. Per ZCS-6: *"Backward edges into Phase 2 require a versioned benchmark update, never a silent edit."* v1.0 remains on record with this defect documented; v1.0.1 supersedes it with this delta record inside the new bundle.

## Discovery provenance

The defect was found because Loop A was run against the committed generators and committed checker rather than ad-hoc test prompts — the benchmark-first ordering surfaced its own flaw at first contact with a real model, before any measured run. Companion solution-side findings from the same session (not part of this bundle): F-A1, controller saturation produced signed no-op adaptation events, caught by the committed auditor's C5 non-degeneracy check (exit 4) and fixed; F-A2, dev harness stop-token handling for the Qwen chat template, fixed in the solution repo.
