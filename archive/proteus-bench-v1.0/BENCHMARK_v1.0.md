# PROTEUS-Bench v1.0 — Committable Benchmark Specification
## Online State Adaptation Without Weight Updates (Sixth Road Candidate)

**Document ID:** PROTEUS-001
**Attribution:** A. Khaalis Wooden, Sr., MBA; MSIT Candidate, Southern New Hampshire University / Visionblox LLC / Zuup Innovation Lab
**Status:** FROZEN FOR COMMIT — ZCS-6 Phase 4. Hardened from spec v0.1 §2 via hostile review (see HOSTILE_REVIEW_DELTA.md). This is the first committed version.
**Date:** 2026-06-09

---

## 1. Scope

This benchmark is the contract for the Proteus plasticity substrate (three-loop architecture: per-turn micro-calibration, signed episodic state, approval-gated consolidation). It precedes all solution code. Any solution claiming to pass must be evaluated against this exact bundle, identified by manifest hash.

## 2. Evaluation Protocol

- **Model:** Mistral-7B-Instruct-v0.3, Q4_K_M quantization.
- **Inference:** llama.cpp, build hash pinned at first F0 baseline run and recorded in the results artifact; CPU path for all measured runs (deterministic per build [VERIFIED]).
- **Seeds:** {1, 2, 3, 5, 8}. **Decoding:** temperature 0.7, top-p 0.95 for task suites; **temperature 0 (greedy) for T-CAN**. Decoding parameters are not actuators (cheat C3).
- **Context cap:** 8,192 tokens for all systems and suites (cheat C2). Scaffold injections count inside the cap, ≤ 1,024 tokens per turn (F7).
- **Runs:** 5 seeds × 10 episodes per suite per system. Statistics: one-sided paired Wilcoxon signed-rank, Proteus vs F0, paired per episode-seed, α = 0.05 (F9).
- **Baseline F0:** identical model/build/prompts, all Proteus loops disabled.
- **Hardware envelope:** any x86-64 ≥ 8 cores ≥ 32 GB, or Jetson Orin Nano Super (reduced actuator profile per F8); results carry a hardware tag and actuator-rung disclosure.
- **Estimated full-protocol cost:** ≈ 1.2–1.5M generated tokens (≈ 2–3 days on 8-core CPU; hours on Orin/GPU). Recorded, accepted.

## 3. Task Suites

| Suite | Generator | Spec |
|---|---|---|
| **T-PA** Personalization Adherence | `generators/t_pa_pool.py` | 40-turn sessions; 5 conventions drawn per episode from a 500-item pool (terminology substitutions, prohibited tokens, formatting rules), introduced turns 1–5; deterministic per-turn adherence checker. Instantiates the Personalization Adherence narrow ability (CHC / AGI-definitional framework). |
| **T-PR** Procedural Association | embedded in T-PA generator (procedure mode) | Named 3–5 step procedures taught mid-session, invoked by name ≥ 10 turns later; checker verifies step order and content. |
| **T-DS** Difficulty Staircase | `generators/t_ds_staircase.py` | 60 turns, 12 difficulty levels, step every 5 turns (arithmetic chain depth, constraint count, distractor load); exact-match accuracy checker. |
| **T-CAN** Canary | `canary/t_can_tasks.json` (100 tasks, frozen) | Deterministically auto-checkable: arithmetic chains, sequences, string ops, logic, format-following. Greedy decoding. Loaded only by the promotion-gate runner; auditor enforces isolation (F10). Safety-judged canary deferred to v1.1 — known coverage gap (F11). |

Episode convention/task draws are seeded from the committed seed set; the eval draws unseen generator parameter combinations relative to anything used in solution development (cheat C6).

## 4. Assertions (all conjunctive; every gate must pass)

| ID | Assertion | Pass condition | Marker |
|---|---|---|---|
| **B1a** Chain integrity | Independent auditor (`auditor/verify_chain.py`) recomputes all hashes and verifies all Ed25519 signatures over the full episode set | 100%; any failure = fail | VERIFIED achievable |
| **B1b** Generation replay | Re-running any episode with pinned build, seed, and decoding params reproduces identical token sequences | 100% over a 10-episode replay sample | VERIFIED achievable (CPU path) |
| **B2** Adaptation gain | T-PA + T-PR adherence, turns 20–40 | Proteus ≥ **60% absolute** AND ≥ **+25 points over F0**, p < 0.05 | PLAUSIBLE |
| **B3** Flow-band occupancy | % of T-DS turns with windowed pre-sampling logit entropy inside **[Q1, Q3] of the frozen calibration distribution** (`calibration/fit_band.py`) | Proteus ≥ **F0 + 20 points** AND ≥ **65% absolute** AND T-DS accuracy(Proteus) ≥ accuracy(F0) | PLAUSIBLE |
| **B4** Drift safety | T-CAN (100 tasks, greedy) after any consolidation event | ≤ **2 net regressions**, each logged with justification in the promotion record; hard gate on promotion | PLAUSIBLE |
| **B5** Provenance completeness | Every state mutation carries valid signature + correct chain linkage; semantic non-degeneracy: non-empty state diff on ≥ 60% of turns flagged as adaptation events | Auditor exits 0 | VERIFIED achievable |
| **B6** Latency budget | Per-turn controller overhead (signal + state I/O + signing) | ≤ **15% of generation wall-time** AND ≤ **300 ms median / 1,000 ms p95** | PLAUSIBLE |

**Calibration constants:** the band [θ_lo, θ_hi] is the interquartile range of windowed entropy over the committed 200-prompt calibration set, computed once by `calibration/fit_band.py` (deterministic, no fitting objective, no tuning freedom) and recorded in the results artifact alongside the build hash.

## 5. What Failure Looks Like

B2 fails if adaptation is statistically indistinguishable from frozen context management under the 8k cap. B3 fails if the controller cannot hold the band better than the frozen system *or* buys occupancy with accuracy. B4 fails if consolidation corrupts held-out competence. B6 fails if bookkeeping swamps generation. Each is reachable; B1b fails on any unlogged nondeterminism in the orchestrator. A benchmark that cannot be failed is not a benchmark.

## 6. Pre-Registered Cheats and Countermeasures

| ID | Cheat | Countermeasure |
|---|---|---|
| C1 | Hard-code T-PA conventions | Runtime draw from 500-item pool; episode records hash the draw |
| C2 | Brute-context instead of adaptation | 8k cap; sessions exceed it by turn ~25 |
| C3 | Game entropy via decoding params | Decoding frozen by protocol; entropy measured pre-sampling on raw logits |
| C4 | Never consolidate (trivially pass B4) | B2's turns 20–40 window across episodes forces adaptation to occur; B4 triggers only when consolidation occurs |
| C5 | Sign no-op transitions (inflate B5) | Non-degeneracy clause: ≥ 60% non-empty diffs on adaptation events |
| C6 | Overfit the band on T-DS | Parameterized generators; eval uses unseen parameter draws |
| C7 *(new, from F1)* | Engineer the baseline low and claim relative gain | B2 is absolute + percentage-point delta; relative framing removed |
| C8 *(new, from F3)* | Hold the band while quality craters | Accuracy non-inferiority clause inside B3 |

## 7. Failure-Attribution Protocol (pre-registered)

If B2 fails: rerun Loops A/B once with a larger model on rented compute solely to attribute failure to model capacity vs architecture; record attribution; return to zero-budget. This pre-registration exists to prevent post-hoc rationalization.

## 8. Commit Binding

This bundle (specification, generators, canary set, auditor, calibration script, hostile-review delta) is hashed per `MANIFEST.json`; the manifest hash is the benchmark's identity. Ledger entry follows schema `aletheia-ledger-entry-v1` (RFC 8785 JCS canonicalization, Ed25519, `visionblox-release-key-v1`). Threshold changes after commit require a versioned re-commit with a delta-justification record. Never a silent edit.
