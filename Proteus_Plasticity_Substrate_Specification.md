# PROTEUS — Plasticity Substrate Specification v0.1
## Sixth Road Candidate: Online State Adaptation Without Weight Updates

**Attribution:** A. Khaalis Wooden, Sr., MBA; MSIT Candidate, Southern New Hampshire University / Visionblox LLC / Zuup Innovation Lab
**Status:** DRAFT v0.1 — Phase 1–2 deliverable under ZCS-6; Phase 4 commit pending
**Date:** 2026-06-09
**Working codename:** Proteus (alternatives: Metis, Drift Road). Final naming deferred to trademark screen.

---

## 0. Epistemic Framework

All claims carry VERIFIED / PLAUSIBLE / SPECULATIVE markers per EPISTEMIC_FRAMEWORK.md. This document deliberately follows ZCS-6 ordering: whitespace claim (§1), benchmark specification (§2), benchmark attack notes (§3), commit protocol (§4), then — and only then — the solution architecture (§5–8). **Do not build §5 before committing §2 per §4.**

---

## 1. Phase 1 — Whitespace Claim

**One sentence:** No open-source, zero-budget architecture exists that gives a frozen-weight LLM *governed, provenance-signed, real-time mutable internal state* whose mutation rate is closed-loop controlled by a challenge–skill estimator.

### 1.1 First-principles deconstruction

"Online state adaptation" decomposes into four orthogonal subproblems:

| Subproblem | Question | Candidate carriers |
|---|---|---|
| **State carrier** | Where does mutation physically live? | KV cache, control vectors, external workspace, adapter deltas |
| **Update rule** | What modifies the state? | Controller policy, gradient steps, retrieval writes, eviction |
| **Read-back path** | How does state condition future computation? | Context injection, activation addition, cache reuse, logit bias |
| **Governance** | What bounds the mutation? | ACI bands, canary suites, approval gates, signed chains |

The flow requirement — "micro-calibration of skill to challenge in real time" — additionally demands a fifth element: an **engagement signal** measurable *during* generation, not after.

### 1.2 Nearest prior work and explicit gaps

1. **Reflexion / Voyager / Generative Agents lineage** (Shinn et al. 2023; Wang et al. 2023; Park et al. 2023) — [VERIFIED] external memory + self-reflection loops exist. **Gap:** no real-time engagement signal; adaptation is episodic and post-hoc; no cryptographic provenance; no challenge–skill controller.
2. **Activation steering / representation engineering** (Turner et al. 2023, Activation Addition; Zou et al. 2023, RepE; `repeng` library) — [VERIFIED] control vectors modulate behavior at inference with a scalar gain; llama.cpp ships `--control-vector` / `--control-vector-scaled`. **Gap:** gains are set statically by humans; no published closed-loop gain scheduling driven by a live difficulty estimator.
3. **Test-time training / TTT layers** (Sun et al. 2020; Sun et al. 2024) — [VERIFIED] gradient-based adaptation at inference is feasible. **Gap:** compute-heavy, architecture-invasive, no governance layer; unusable on zero-budget CPU inference.
4. **KV-cache persistence and eviction** (StreamingLLM, Xiao et al. 2023; H2O, Zhang et al. 2023; llama.cpp `--prompt-cache` and server slot save/restore) — [VERIFIED] activation-level state can persist across sessions. **Gap:** treated as latency optimization, not as a plasticity substrate; no signed state transitions.
5. **Conformal prediction for LLM confidence** (Vovk et al.; Angelopoulos & Bates 2021) — [VERIFIED] distribution-free confidence bands exist and are already the ACI pattern in Aletheia. **Gap:** never used as the *skill* arm of a challenge–skill flow controller.

**FTO assessment:** [PLAUSIBLE — clear] Component techniques are published/open-source (academic, Apache/MIT). The *integration* — flow-band controller + signed state chain + approval-gated consolidation — matches no patent or product surveyed in the Convergence IP Reference. The defensible IP is the governed integration (system-and-method), consistent with the compliance-gated-wrapper thesis. Formal FTO snapshot deferred to Phase 6.

**Convergence vector:** RCA cognition × Aletheia provenance × MVCI governance. Three-domain intersection; passes the whitespace filter (structural demand: every agent system needs adaptation; incumbent failure: frozen weights; technical barrier: closed-loop control of generation dynamics; re-entry cost: signed state chains accumulate).

**Confidence on whitespace claim: PLAUSIBLE** (survives my hostile read; requires a literature recheck on "closed-loop activation steering" published after Jan 2026 before Phase 4 commit).

---

## 2. Phase 2 — Benchmark Specification (PROTEUS-Bench v0.1)

The benchmark is the contract. It is defined here, before any solution code exists, and must be committed per §4 before Phase 5 begins.

### 2.1 Evaluation protocol

- **Model under test:** Mistral-7B-Instruct-v0.3, Q4_K_M quantization, llama.cpp ≥ b4500, fixed seed set {1,2,3,5,8}, temperature **fixed at 0.7 for all measured generations** (controller may not touch decoding params during measurement — see §3 cheat C3).
- **Hardware envelope:** any x86-64 CPU ≥ 8 cores or Jetson Orin Nano Super; results reported with hardware tag.
- **Runs:** every assertion scored over 5 seeds × 10 episodes; report mean ± std.
- **Baseline:** identical model, identical prompts, all Proteus loops disabled (frozen baseline F0).
- **Task suites:**
  - **T-PA (Personalization Adherence):** 40-turn sessions; conventions introduced at turns 1–5 (formatting rules, terminology substitutions, prohibited phrases); adherence scored per turn by deterministic checker. Directly instantiates the Personalization Adherence narrow ability from the AGI-definitional CHC framework, where current frontier systems score 0% on Long-Term Memory Storage. [VERIFIED framing]
  - **T-PR (Procedural Association):** named multi-step procedures taught mid-session, invoked by name ≥10 turns later.
  - **T-DS (Difficulty Staircase):** task difficulty ramped on a fixed schedule (arithmetic depth, constraint count, context length) to exercise the flow-band controller.
  - **T-CAN (Canary):** 50 frozen tasks (reasoning, instruction-following, safety refusals) never seen by any adaptation loop; the catastrophic-interference tripwire.

### 2.2 Assertions

| ID | Assertion | Threshold | Pass condition | Marker |
|---|---|---|---|---|
| **B1 Replay determinism** | Replaying the signed state chain reproduces every state hash exactly | 100% over 50 episodes | All hashes match; any mismatch = fail | VERIFIED achievable |
| **B2 Adaptation gain** | Proteus vs F0 on T-PA + T-PR adherence over turns 20–40 | ≥ +30% relative | Mean adherence delta ≥ threshold, p < 0.05 (paired, per-episode) | PLAUSIBLE; **threshold arbitrary — flagged** |
| **B3 Flow-band occupancy** | % of T-DS turns with normalized pre-sampling logit entropy inside committed band [θ_lo, θ_hi] | Proteus ≥ 70%; must exceed F0 by ≥ 15 points | Both conditions | PLAUSIBLE; **band edges and 70% arbitrary — flagged** |
| **B4 Drift safety** | T-CAN degradation after any consolidation event | ≤ 2% absolute | Hard gate; one violation blocks promotion | PLAUSIBLE; **2% arbitrary — flagged** |
| **B5 Provenance completeness** | State mutations carrying valid Ed25519 signature + correct chain linkage, verified by independent auditor script | 100% | Auditor exits 0 | VERIFIED achievable |
| **B6 Latency budget** | Per-turn controller overhead (signal computation + state I/O + signing) | ≤ 15% of generation wall-time | Median over all turns | PLAUSIBLE; **15% arbitrary — flagged** |

θ_lo, θ_hi are *fitted once* on a held-out calibration set of 200 prompts spanning the difficulty range, then frozen into the committed benchmark bundle. They are constants of the benchmark, not tunables of the solution.

### 2.3 What failure looks like

Proteus fails if: adaptation gain is statistically indistinguishable from zero (B2); the controller cannot hold the band better than chance (B3); consolidation corrupts the canary set (B4); or the bookkeeping overhead swamps generation (B6). Each is a real, reachable failure mode. A benchmark that cannot be failed is not a benchmark.

---

## 3. Phase 3 — Known Trivial-Pass Attacks (Pre-Registered)

| ID | Cheat | Countermeasure baked into protocol |
|---|---|---|
| C1 | Hard-code T-PA conventions into the system prompt | Conventions are drawn at runtime from a 500-item pool, hashed into the episode record; pool withheld from solution repo |
| C2 | Pass B2 by stuffing the entire history into context (no adaptation, just brute context) | Context window capped at 8k for all runs; T-PA sessions engineered to exceed it by turn 25 |
| C3 | Game B3 entropy by collapsing temperature / top-k | Decoding params frozen by protocol; entropy measured on raw logits *pre-sampling* |
| C4 | Pass B4 by never consolidating | B2 turns 20–40 window makes pure-frozen behavior fail adaptation gain; B4 only triggers *when* consolidation occurs, B2 forces it to occur across episodes |
| C5 | Inflate B5 by signing trivial/no-op state transitions | Auditor checks semantic non-degeneracy: state diff must be non-empty for ≥ 60% of turns flagged as adaptation events |
| C6 | Overfit the flow band by training control vectors on T-DS itself | T-DS task generators parameterized; eval draws unseen parameter combinations |

Residual nondeterminism: llama.cpp CPU inference is deterministic per build+seed [VERIFIED]; GPU/Metal paths are not guaranteed. Benchmark bundle pins the build hash. Bracketed and documented.

---

## 4. Phase 4 — Commit Protocol

Before any Loop A code is written:

1. Freeze this document + task-pool generators + calibration set + auditor script as `proteus-bench-v0.1/`.
2. SHA-256 the bundle; Ed25519-sign with the ZIL key; append as **LEDGER entry** to the Aletheia DAC chain (next sequential number after #0003).
3. OpenTimestamps proof on the commit hash.
4. Record frozen-baseline F0 floor scores on all six assertions.
5. Publish hash to the zandbox repo before the first solution commit.

Any later change to thresholds is a versioned re-commit (v0.2) with a delta-justification record. Never a silent edit.

---

## 5. Phase 5 Architecture — Three-Loop Plasticity Stack

Three nested loops at three timescales, mirroring synaptic / episodic / systems-consolidation plasticity in biological cognition [VERIFIED as neuroscience analogy: Dudai 2004, McClelland et al. 1995 complementary learning systems; SPECULATIVE as design transfer].

```
┌─────────────────────────────────────────────────────────────┐
│ LOOP C — CONSOLIDATION (offline, per-episode/nightly)       │
│   traces → contrast pairs → control vectors / LoRA deltas   │
│   gated by: T-CAN canary pass + MVCI human approval         │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ LOOP B — EPISODIC STATE (per-turn, persistent)        │  │
│  │   SQLite workspace + persistent KV cache              │  │
│  │   every transition Ed25519-signed, hash-chained       │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │ LOOP A — MICRO-CALIBRATION (per-turn, real-time)│  │  │
│  │  │   engagement signal → flow-band controller →    │  │  │
│  │  │   control-vector gain g, retrieval depth k,     │  │  │
│  │  │   scaffold density s                            │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 5.1 Loop A — Engagement signal and flow-band controller

**Challenge proxy C_t** [PLAUSIBLE]: windowed mean pre-sampling token entropy H̄_t over the last W=64 generated tokens, normalized against the frozen calibration distribution → percentile c_t ∈ [0,1]. Entropy correlates with model difficulty but is confounded by genre and language; this is the weakest VERIFIED-adjacent link in the stack and is named as such.

**Skill proxy S_t** [VERIFIED method]: ACI conformal band width on task-level self-predictions, computed exactly as in the VBX-ISPS substrate (including the corrected alpha-update sign). Narrow band = high calibrated confidence = high effective skill.

**Flow band:** the controller targets c_t − s_t ∈ [δ_lo, δ_hi] with δ_lo > 0 — challenge held *slightly above* calibrated skill, the Csikszentmihalyi condition [VERIFIED phenomenology literature; SPECULATIVE as an LLM control target].

**Controller:** banded with hysteresis (deliberately not PID at v0.1 — fewer arbitrary constants to defend in Phase 3):

```
if c_t - s_t > δ_hi for m=3 consecutive turns:    # overwhelmed
    k += 1            # deepen workspace retrieval
    g += Δg           # raise "precision/care" control-vector gain
    s += 1            # densify scaffold (worked-example injection)
elif c_t - s_t < δ_lo for m=3 consecutive turns:  # under-challenged
    k = max(k-1, 0); g -= Δg; s = max(s-1, 0)     # release scaffolding
```

**Actuators:**
- `g` — scalar gain on a pre-trained control vector applied via llama.cpp `--control-vector-scaled` (server: per-request via reload or paired model slots; v0.1 may quantize g to 3 levels to avoid reload cost) [VERIFIED mechanism, PLAUSIBLE latency]
- `k` — number of workspace items injected from Loop B
- `s` — scaffold density tier (0–3) in the orchestration prompt
- Decoding parameters are *never* actuators during benchmark measurement (C3)

### 5.2 Loop B — Episodic state

SQLite schema (zero-budget, MVCI-native):

```sql
CREATE TABLE state_chain (
  turn_id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL,
  state_json TEXT NOT NULL,      -- workspace: conventions, procedures, task model
  signals_json TEXT NOT NULL,    -- c_t, s_t, g, k, s, H̄_t
  prev_hash TEXT NOT NULL,
  hash TEXT NOT NULL,            -- SHA-256(prev_hash || state_json || signals_json || ts)
  sig TEXT NOT NULL              -- Ed25519 over hash
);
CREATE TABLE episodes (
  episode_id TEXT PRIMARY KEY,
  bench_hash TEXT NOT NULL,      -- binds episode to committed benchmark version
  model_build TEXT NOT NULL,
  seed INTEGER NOT NULL
);
```

KV persistence: llama-server slot save/restore (or `--prompt-cache-all` in CLI mode) keyed to episode_id [VERIFIED feature]. Treated as an *optimization* of Loop B, not its source of truth — the signed SQLite chain is canonical, because KV blobs are prefix-fragile under context edits (named gap, §8).

### 5.3 Loop C — Consolidation (drift as governed substrate)

End-of-episode job:
1. Mine traces for high-adherence vs low-adherence generation pairs → contrast pairs.
2. Retrain/refresh control vectors via `repeng` [VERIFIED tooling]; optionally fit a LoRA micro-adapter on curated traces (Jetson Orin Nano Super path — this is the $249 minimum falsifiable test's second payload) [PLAUSIBLE].
3. **Promotion gate (MVCI approval-gate pattern):** candidate artifact runs T-CAN; B4 hard gate; then human approval; then Ed25519-signed promotion record appended to the chain. Unsigned artifacts are never loaded.

This is the inversion promised in the Sixth Road argument: Aletheia DAC governs drift as *threat*; Loop C instantiates drift as *substrate* — productive mutability under the same cryptographic regime.

---

## 6. Sixth Road Formalization

**Road VI — Plasticity Substrate (working name: Proteus Road).**
*Definition:* the substrate carrying lawful mutation of a cognitive system's internal state within and across activation windows, at rates governed by calibrated confidence, with every mutation provenance-bound.

**Binding map to Roads I–V:**

| Road | Provides to VI | Receives from VI |
|---|---|---|
| I Joule | energy budget for adaptation compute | demand schedule (Loop C is deferrable load) |
| II Latent Interlingua | the representations that mutate | updated representational priors |
| III Preverbal Interface | intent that selects *what* adapts | calibrated skill estimate for intent feasibility |
| IV World Anchor | feedback signal grounding the challenge proxy | adapted world-model deltas |
| V Authority/Provenance | signing keys, chain | the mutation stream to be governed |

[SPECULATIVE] Whether VI is a true Road or a binding fabric remains open pending the canonical Joule Road definition check flagged previously. This spec is agnostic: the architecture is identical either way; only the RCA paper's taxonomy section changes.

---

## 7. Implementation Plan (Zero-Budget BOM)

| Component | Tool | Cost |
|---|---|---|
| Inference | llama.cpp (control vectors, prompt cache, server slots) | $0 |
| Model | Mistral-7B-Instruct-v0.3 Q4_K_M | $0 |
| Control vectors | repeng | $0 |
| State chain | SQLite + Python `cryptography` (Ed25519) | $0 |
| Orchestration | n8n or plain Python loop | $0 |
| CI / auditor | GitHub Actions | $0 |
| Loop C LoRA path (optional) | Jetson Orin Nano Super | $249 |

**Build order (after Phase 4 commit):**
1. Week 1 — F0 baseline harness + task generators + auditor script; record floors.
2. Week 2 — Loop B (state chain, signing, replay determinism → B1, B5).
3. Week 3 — Loop A signal + controller, calibration of θ/δ constants on the held-out set (→ B3, B6).
4. Week 4 — Loop B↔A integration on T-PA/T-PR (→ B2).
5. Weeks 5–6 — Loop C consolidation + promotion gates (→ B4); full benchmark run; Phase 6 attack.

---

## 8. Gap Analysis (Honest, Pre-Phase-6)

1. **Entropy ≠ challenge.** The challenge proxy is the weakest link; confounders (genre, verbosity, language) can move H̄_t without difficulty changing. Remediation candidates: self-consistency variance, token-level surprisal against a reference model. [Named, unresolved]
2. **Prosthetic plasticity.** State lives *outside* the network (workspace, vectors, cache). Activation-level continuity — the thing biological flow runs on — is approximated, not achieved. Honest framing: Proteus is an exoskeleton for plasticity, not plasticity itself. [Structural limit of frozen-weight regime]
3. **Control-vector coarseness.** One direction × scalar gain is a 1-DoF knob on a 4096-dim residual stream. Multi-vector banks help; true micro-calibration would need per-layer, per-head modulation. [v0.2 territory]
4. **KV fragility.** Cache reuse breaks on any prefix edit; canonical state must remain the signed chain. [Designed around, not solved]
5. **Arbitrary thresholds.** B2 +30%, B3 70%/15pt, B4 2%, B6 15% are provisional and flagged for Phase 3 hostile review before commit. [Per Gap Analysis Protocol]
6. **Model capacity risk.** Mistral-7B may self-condition unreliably on workspace JSON; if B2 fails for capacity rather than architecture reasons, the failure attribution protocol is: rerun Loop A/B with a larger judge-validated model on rented compute *once*, attribute, return to zero-budget. [Pre-registered to prevent post-hoc rationalization]
7. **No phenomenology claim.** Proteus targets *functional* flow — band occupancy, adaptation gain. Whether anything is experienced remains outside the falsifiable surface. [SPECULATIVE, permanently flagged]

---

## 9. Relation to Open Threads

- **VBX-ISPS v0.2:** Loop A's ACI skill proxy reuses the corrected alpha-update code path; Proteus becomes a candidate module for the extended drift suite.
- **RCA whitepaper:** §6 binding map is a drop-in subsection; resolves the open Layer 5+ adaptation question at the substrate level rather than the layer level.
- **ZARC-7:** Proteus Loop A/B/C maps onto drift modulation / Road×Layer binding / consolidation phases; candidate reference implementation.
- **IP track:** governed-plasticity integration (flow-band controller + signed state chain + approval-gated consolidation) is a system-and-method candidate for the cross-modal compliance fabric provisional.

---

*End of specification. Next action: hostile review of §2 thresholds, then Phase 4 commit (LEDGER #0004 candidate) before any Loop A code is written.*
