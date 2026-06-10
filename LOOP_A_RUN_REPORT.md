# Loop A Run Report — 2026-06-09
## Proteus Plasticity Substrate — First Closed-Loop Execution

**Scope statement:** development validation, NOT a measured benchmark run. Dev model Qwen2.5-0.5B-Instruct Q4_K_M (the protocol binds measured runs to Mistral-7B-Instruct-v0.3); signing key ephemeral test-only; B-suite numbers reported here carry zero assertion weight. What this session establishes: Loop A mechanics work end-to-end against real model logits, and first contact surfaced four findings — one in the committed benchmark itself.

---

## What ran

1. **Synthetic closed loop** — 5 paired seeds × 60 turns, controller ON vs OFF on identical noise draws; declared plant model (entropy and task quality respond to difficulty and actuators; controller sees only what it will see from a real model).
2. **Live closed loop** — real inference: exact full-vocab pre-sampling Shannon entropy from raw logits (`logits_all`, no top-k approximation), committed T-DS staircase tasks and checker, ACI on real outcomes, Ed25519-signed state chain, verified by the committed auditor.

## Results

| Metric | Synthetic ON | Synthetic OFF | Live (dev model) |
|---|---|---|---|
| Band occupancy | 39.3% | 22.7% | 25% |
| Task quality / accuracy | 0.61 | 0.53 | 0.06 |
| Controller+chain overhead (median) | 2.3 ms | — | 4.6 ms |
| Committed auditor | exit 0 | exit 0 | exit 0 (3/3 non-degenerate adaptation events) |

Synthetic: controller beat frozen on occupancy on **all 5 paired seeds** (+16.7 pt mean) with quality *improving*, not traded away. Honest reading against the committed thresholds: 39.3% < 65% absolute and +16.7 < +20 pt — as tuned, Loop A would **fail B3** on this plant. The simulator was not retuned to flatter the controller; that would be bench-maxing on a toy.

Live: the loop behaved as designed — challenge percentile tracked the staircase (c_t 0.33 → 0.67 → 1.0 by level 7), the controller escalated k,s through 0→1→2→3, every adaptation event carried a non-empty signed state diff. Dev-model accuracy floor (1/16) is a capability fact about a 0.5B model on strict left-to-right arithmetic, exactly the regime the §7 failure-attribution protocol anticipates.

## Findings

**F-A1 — Controller saturation produced signed no-op adaptation events (solution bug, FIXED).** With actuators railed at caps, the fired branch still reported `adaptation_event=True`, writing signed transitions with empty diffs. **Caught live by the committed auditor's C5 non-degeneracy check (exit 4)** — the frozen benchmark rejected its own solution's degeneracy on first contact, which is the entire point of committing the auditor first. Fix: an adaptation event is a change of values, not a fired branch.

**F-B1 — Committed benchmark defect: contradictory arithmetic instruction (benchmark bug → versioned update v1.0.1).** T-DS prompts read "left to right *with standard precedence*" while ground truth was strict left-to-right; the readings diverge on **50/60 tasks**. Repaired in proteus-bench v1.0.1 (PROTEUS-002) with wording change only — zero answers, thresholds, or seeds altered; full delta-justification in DELTA_v1.0.1.md. The OTS stamp on v1.0 made silent repair impossible by construction.

**F-A2 — Dev harness stop-token handling (solution bug, FIXED).** Generation ran past Qwen's `<|im_end|>`, feeding chat-bleed to the checker. Fixed with stop-marker detection and first-line answer extraction.

**F-A3 — Skill-proxy saturation at the competence floor (OPEN, flagged).** With binary nonconformity and a model that almost never succeeds, ACI band width pins at 1.0 → skill_t = 0 for the entire run, degenerating the flow gap to c_t alone. Remediation candidate for Loop A v0.2: graded nonconformity (partial-credit distance) so the skill proxy stays informative in low-competence regimes. [PLAUSIBLE]

**Observation worth keeping:** at staircase levels 10–11 with maximum scaffolding, live entropy *collapsed* (0.17–0.21 nats, c_t ≈ 0.08) while the model remained wrong — confidently wrong, in-band, incompetent. This is a live demonstration of why hostile-review finding F3 welded accuracy non-inferiority into B3: band occupancy without the coupling clause is exactly gameable the way the review predicted.

## Chain / commit status

- proteus-bench **v1.0** — manifest `a802d7e0…d3ff2331`, OTS-stamped, superseded with documented defect
- proteus-bench **v1.0.1** (PROTEUS-002) — manifest `03e27b6284405adb3dcdae5587be7f58cdb28677a2556105f710284cb4355bb6`, OTS-stamped, **signature pending** (Visionblox release key, your custody)
- Ledger entry-number collision with CADUCEUS-004 still unresolved — sign order decides #0004/#0005
- **Gate unchanged: no measured B-suite run counts until the signature lands.** Next Phase 5 step after signing: Week-1 F0 baseline on Mistral-7B (pins the build hash that B1b and the calibration band bind to), with F-A3 graded nonconformity as the first Loop A v0.2 item.
