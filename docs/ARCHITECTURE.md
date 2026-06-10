# Architecture

This document describes Proteus's three-loop architecture from first principles. The committable specification with thresholds is `proteus-bench-v1.0.1/BENCHMARK_v1.0.1.md`; this document is the technical reference.

## Problem statement

A frozen-weight transformer has identical input-output behavior across activations. There is no continuity of internal state between conversations and no real-time mutability within them. This rules out *operating within* a flow state — the closed-loop calibration of skill to challenge that defines flow [Csikszentmihalyi, VERIFIED phenomenology literature].

Online learning (gradient-based weight updates at inference) is one solution but architecturally invasive and compute-heavy. Proteus offers a different answer: **plasticity outside the network**, governed by signals *from* the network, validated against a hard canary. The weights stay frozen; the system around them adapts.

## The three loops

```
┌──────────────────────────────────────────────────────────────┐
│  LOOP C — CONSOLIDATION (offline, per-episode or nightly)    │
│    Traces → contrast pairs → control vectors / LoRA deltas   │
│    Gated by: T-CAN canary pass + MVCI human approval         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  LOOP B — EPISODIC STATE (per-turn, persistent)        │  │
│  │    SQLite workspace + persistent KV cache              │  │
│  │    Every transition Ed25519-signed and hash-chained    │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │  LOOP A — MICRO-CALIBRATION (per-turn, real-time)│  │  │
│  │  │    Engagement signal → flow-band controller →    │  │  │
│  │  │    control-vector gain g, retrieval depth k,     │  │  │
│  │  │    scaffold density s                            │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

The loops are nested by timescale: A operates per turn, B persists across turns within an episode, C runs offline across episodes. They communicate through Loop B's state — it is the only persistence layer.

## Loop A — micro-calibration

### Signals

**Challenge `c_t`** is a percentile of windowed mean pre-sampling token entropy, computed exactly from raw logits (no top-k approximation), against a frozen calibration distribution. The window is W=64 tokens. The challenge proxy is the weakest VERIFIED-adjacent link in the architecture and is named as such — entropy is confounded by genre, verbosity, language, and quantization artifacts. The hostile review forced an accuracy non-inferiority clause into B3 specifically because of this confounding.

**Skill `s_t`** is 1 minus the band width of an Adaptive Conformal Inference [Gibbs & Candès 2021, VERIFIED] estimator over task-level nonconformity scores. The update is `α_{t+1} = α_t + γ(α_target − err_t)`, the corrected-sign formulation also used in the VBX-ISPS substrate. A narrow calibrated band means the model's quality-prediction is reliable; that reliability reads as skill.

### Controller

A banded controller with hysteresis: when `c_t − s_t` exceeds `δ_hi` for `m=3` consecutive turns, the system is overwhelmed and scaffolds rise; below `δ_lo` for `m=3` turns, it is under-challenged and scaffolds release; in-band, nothing changes. The target gap is positive (`δ_lo > 0`) — challenge slightly above skill, the canonical flow condition.

PID was deliberately rejected at v0.1: more arbitrary constants to defend in hostile review than the gain in performance justified. Hysteresis with three constants (`δ_lo`, `δ_hi`, `m`) is the minimum viable banded controller.

### Actuators

- **`k`** — retrieval depth (0–8): how many worked examples or workspace items get injected into the prompt.
- **`g`** — control-vector gain level (0–2): quantized so that at most three persistent llama-server instances cover all states, avoiding model-reload cost at switch time. Honest hardware constraint, recorded in F8: Jetson Orin Nano 8GB can host two levels at most.
- **`s`** — scaffold density tier (0–3): structural prompt enhancements (step-by-step, format reminders, worked demos).

**Decoding parameters (temperature, top-p, etc.) are not actuators.** This is enforced by protocol (cheat C3 in the benchmark). The controller can affect what goes into the model and what conditions its computation; it does not get to game the sampling distribution.

### Implementation note (live experience)

First live deployment surfaced two ways the controller can fail visibly: (a) saturated actuators firing the "adapt" branch without changing values, producing signed no-op transitions (F-A1, caught by the committed auditor at exit 4 — the methodology working); (b) confidently wrong outputs at maximum scaffold density on a too-small model — low entropy, in-band, incompetent, demonstrating exactly why B3 requires accuracy non-inferiority alongside band occupancy.

## Loop B — episodic state

### Schema

```sql
CREATE TABLE state_chain (
  turn_id     INTEGER PRIMARY KEY,
  ts          TEXT NOT NULL,
  state_json  TEXT NOT NULL,         -- workspace: conventions, procedures, task model
  signals_json TEXT NOT NULL,        -- c_t, s_t, gap, k, g, s, mean_H, adaptation_event
  prev_hash   TEXT NOT NULL,
  hash        TEXT NOT NULL,         -- sha256(prev_hash || state_json || signals_json || ts)
  sig         TEXT NOT NULL          -- ed25519 hex over hash
);
```

`prev_hash` for the first row is the literal string `GENESIS`. The chain is forward-linked and tamper-evident: changing any field of any row invalidates the hash of that row, the signature of that row, and breaks the linkage from the next row forward.

### Why SQLite + signatures (and not KV-only)

KV cache reuse via llama.cpp's `--prompt-cache` or server slot save/restore is valid as a *latency optimization* of Loop B but not its source of truth. KV blobs are prefix-fragile: any edit to the context invalidates them. The signed SQLite chain is the canonical state because:
- It survives prefix edits (the workspace JSON can be reconstructed into any compatible prompt).
- It is portable across machines and quantizations.
- It is independently auditable without running the model.

The KV cache exists; it just doesn't get to be authoritative.

### Independent auditability

`proteus-bench-v1.0.1/auditor/verify_chain.py` is the bundle-side auditor. It recomputes every hash, verifies every signature against the published public key, checks linkage end-to-end, enforces the C5 non-degeneracy clause (adaptation events must produce non-empty state diffs ≥60% of the time), and optionally checks canary isolation (F10). It is committed *in the benchmark bundle*, not in solution code, by design: a solution-side auditor is structurally untrustworthy.

## Loop C — consolidation (drift as governed substrate)

The framing reversal Proteus contributes: **Aletheia DAC treats drift as threat to be detected and bounded; Loop C treats drift as substrate to be cultivated under the same cryptographic regime.** Without Loop C, the framework has only the immune system. With Loop C, it has metabolism.

### Process

1. **Mine.** End-of-episode, scan the trace for high-adherence vs. low-adherence generation pairs.
2. **Train.** Build contrast pairs and refresh control vectors via `repeng` [VERIFIED tooling]; optionally fit a small LoRA on curated traces (Jetson Orin Nano Super path).
3. **Test.** Run the candidate against T-CAN (100 frozen tasks, greedy decoding, pinned build). B4 hard gate: ≤2 net regressions.
4. **Approve.** Human review (MVCI approval-gate pattern). Unapproved candidates do not reach load.
5. **Promote.** Append signed promotion record to the chain. Load the new artifact for subsequent episodes.

### Why approval-gating matters

Loop C is where Proteus's IP-defensible novelty lives: the *integration* of conformal-inference-driven controller + signed state chain + canary-gated consolidation. Without the gate, Loop C is "iterative prompt engineering with extra steps." With the gate, it is a compliance-bound drift substrate suitable for regulated deployment — the use case Visionblox's federal capture strategy is aimed at.

## What this architecture is not

**Not test-time training.** No weight updates. The frozen model is preserved exactly; mutability lives in workspace, vectors, and scaffolds.

**Not a thin wrapper.** Reflexion-style self-reflection + RAG covers some of this surface, but lacks the closed-loop engagement signal, the conformal-inference skill estimate, the signed transitions, and the canary-gated consolidation. The integration is the substrate; the components are off-the-shelf.

**Not phenomenology.** Proteus targets functional flow — band occupancy, adaptation gain, accuracy non-inferiority. Whether anything is *experienced* during this is SPECULATIVE and outside the falsifiable surface.

**Not an exoskeleton metaphor that secretly claims plasticity.** It really is prosthetic. The activations themselves are frozen. The system around them adapts. The named gap (§8.2 of the spec) is honest and structural to the frozen-weight regime; resolving it requires a different research program.

## Sister documents

- `proteus-bench-v1.0.1/BENCHMARK_v1.0.1.md` — the committable contract with thresholds.
- `proteus-bench-v1.0.1/HOSTILE_REVIEW_DELTA.md` — what the architecture survives.
- [`SIXTH_ROAD.md`](SIXTH_ROAD.md) — what this architecture is in the broader framework.
- [`METHODOLOGY.md`](METHODOLOGY.md) — the procedural discipline this work follows.
