# Roadmap

This roadmap is dated and PLAUSIBLE — dates slip; the ZCS-6 phase ordering does not.

## Current phase: ZCS-6 Phase 4 → Phase 5 transition

**Phase 4 (deterministic defense)** is complete except for the operator's Ed25519 signature on `LEDGER_0004.json`. Hash computed, OTS-stamped, payload prepared, runbook in [`CLAUDE_ledger_commit_runbook.md`](CLAUDE_ledger_commit_runbook.md). See [`LEDGER_CHAIN.md`](LEDGER_CHAIN.md) for chain state.

## Phase 5 — Solution build

The benchmark contract is fixed; the next work is making a system that passes it honestly.

### v0.2 (Loop A maturation)

- **F-A3 — Graded nonconformity for ACI skill proxy.** Replace binary success/failure scoring with a graded distance metric so the skill estimate stays informative below the competence floor. Without this, low-capability models saturate the proxy at zero skill, degenerating the flow gap to challenge alone.
- **F0 baseline on Mistral-7B-Instruct-v0.3 Q4_K_M.** First measured run. Pins the llama.cpp build hash that B1b (generation replay) and the calibration band bind to. The build hash is the *unique* externality between bundle commit and protocol run; once recorded it is immutable.
- **Calibration band fit.** Run `proteus-bench-v1.0.1/calibration/fit_band.py` on the F0 entropy log; record `[θ_lo, θ_hi]` alongside the build hash in the results artifact.

### v0.3 (Loop B robustness)

- **KV-cache fragility audit.** Document the exact prefix conditions under which `--prompt-cache` reuse remains valid; build a fallback path that regenerates from the canonical signed state when reuse is unsafe.
- **Replay determinism property test.** Random walks through the state space, asserting B1b across thousands of episode prefixes.

### v0.4 (Loop C activation)

- **Control-vector training from traces.** `repeng`-based contrast-pair extraction from successful vs. unsuccessful adherence in T-PA; first promotion candidate.
- **Promotion gate harness.** T-CAN runner with greedy decoding on the pinned build; integration with the auditor's canary-isolation check.
- **Optional LoRA path.** Tested on Jetson Orin Nano Super ($249 reference device). This is the "second payload" path noted in the spec; v0.4 only validates that the path exists, not that it consistently beats control-vectors-only.

### v1.0 (first protocol-conformant run)

- Full benchmark, all six assertions, 5 seeds × 10 episodes per suite. Pre-registered: failure attribution protocol runs once on rented compute if B2 fails, per spec §7.
- Public results artifact: pinned build hash, calibration constants, per-assertion outcomes, raw chain available for independent re-verification.

## Phase 6 — Hostile review of solution

Per ZCS-6: attack the solution until vertically integrated. Activities:

- **Internal red-team** against passing solution: try to recover the cheats that the v1.0 hostile review pre-registered, and add new ones discovered in build.
- **External review** of v1.0 results by at least one outside party with relevant background (test-time adaptation, conformal prediction, or compliance-bound ML systems).
- **Convergence vector validation** — if v1.0 passes, formal evaluation of the governed integration as IP-defensible novelty, with patent practitioner engagement.

## Beyond Phase 6

- **Sixth Road formalization.** Whether Proteus is a true sixth Road or a horizontal binding across Roads I–V depends on the canonical Joule Road definition check still flagged in the architecture doc. Resolved in writing in [`docs/SIXTH_ROAD.md`](docs/SIXTH_ROAD.md) once that check completes.
- **Cross-substrate integration.** ACI skill proxy already shared with Ephemeris; Aletheia provenance pattern already shared with the chain. Next: harmonize the MVCI approval-gate API across Civium and Proteus Loop C.
- **Larger models.** Mistral-7B is the protocol target *for cost reasons*, not because the architecture is size-limited. Replication on larger models is interesting but does not move the benchmark surface — it is a separate research question and explicitly out of scope for the committed contract.

## What this roadmap is not

It is not a marketing plan. It is not a guarantee. It is the ordered queue of technical work that follows from the methodology. Items are dropped or reordered as findings warrant; when that happens, the change is documented in commits or DELTA records.
