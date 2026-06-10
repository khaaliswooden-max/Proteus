# DELTA RECORD — proteus-bench v1.0.1 → v1.0.2 (PROTEUS-003)
## Versioned Benchmark Update — ZCS-6 Phase 5 → Phase 2 Back-Edge

**Trigger:** Automated review (Cursor Bugbot) on the repository's first public pull request (2026-06-10) flagged that `calibration/fit_band.py --emit-prompts` no longer reproduces the committed `calibration/calibration_prompts.json`. Verified: the artifact was carried into v1.0.1 byte-identical to v1.0 while its generator was reworded.

## Defect (F-B2)

The v1.0.1 repair of F-B1 reworded the structured prompts in **both** `generators/t_ds_staircase.py` and `calibration/fit_band.py`, but the frozen artifact `calibration/calibration_prompts.json` was not regenerated — it remained byte-identical to the v1.0 artifact, with the old ambiguous *"Compute: {expr}"* wording on all 100 structured prompts. Two consequences:

1. **Reproducibility invariant broken.** The committed workflow (`fit_band.py --emit-prompts > calibration_prompts.json`) no longer reproduces the committed artifact; an independent verifier following the bundle's own instructions gets a different file. In v1.0 the round-trip was exact (verified this session).
2. **Inconsistent wording.** The ambiguity removed from the task generators by v1.0.1 survived in the calibration set, so the calibration distribution would have been measured over prompts the task suite no longer uses.

## Change

| File | Change | Answers affected |
|---|---|---|
| `calibration/calibration_prompts.json` | Regenerated from the committed `fit_band.py --emit-prompts` (CAL_SEED 161803 unchanged, RNG draws identical). Exactly the 100 structured prompts change wording to *"Compute strictly left to right, ignoring standard operator precedence:"*; the 100 open prompts are byte-identical | **None** — calibration is entropy-only; no ground truth exists for calibration prompts |

**No thresholds changed. No assertions changed. No task answers changed. No seeds changed. No generator code changed.** The calibration *entropy distribution* may shift marginally under the clarified wording; no F0 baseline has been run against any bundle version, so no measured result is invalidated.

## Why this is the legal path

The v1.0.1 bundle is OTS-stamped (`03e27b62…4355bb6`); in-place modification is cryptographically impossible, which is the designed behavior. Per ZCS-6: *"Backward edges into Phase 2 require a versioned benchmark update, never a silent edit."* v1.0.1 remains on record with this defect documented; v1.0.2 supersedes it with this delta record inside the new bundle.

## Discovery provenance

The defect was found by automated hostile review at first public exposure of the repository — before any measured run, and before LEDGER #0004 was signed, so the superseding bundle simply replaces v1.0.1 as the signing candidate. This is the second instance of the benchmark surfacing its own defect on first contact with an adversarial reader (F-B1 being the first, at first contact with a real model); the ordering discipline (commit → attack → repair with delta) is doing its job.
