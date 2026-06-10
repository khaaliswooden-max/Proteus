# Epistemic Framework

Every substantive claim in this repository carries one of three markers. This document defines them, the rules for upgrading and downgrading, and the failure modes the discipline exists to prevent.

## The three markers

### VERIFIED
The claim is grounded in (a) cited published work, (b) cryptographically verifiable evidence in this repository, or (c) a deterministic test that any reader can rerun and observe the same result. VERIFIED claims do not require qualification when stated.

**Examples:**
- "llama.cpp CPU inference is deterministic per build hash and seed" — VERIFIED, referenced in protocol documentation and demonstrated by B1b's existence as a falsifiable assertion.
- "Ed25519 is a deterministic signature scheme suitable for chain provenance" — VERIFIED, cryptographic standard.
- "The committed auditor rejects tampered chains" — VERIFIED, demonstrated in-session (clean exit 0, tampered exit 1).

### PLAUSIBLE
The claim is logically supported by VERIFIED components but not itself directly tested under protocol conditions. PLAUSIBLE claims advance to VERIFIED when the protocol test runs and confirms; they drop to FALSIFIED if the test runs and disconfirms; they remain PLAUSIBLE if untested or partially tested.

**Examples:**
- "The Proteus controller can hold the flow band better than a frozen baseline on a real model" — PLAUSIBLE. Synthetic evidence: +16.7 pt occupancy, 5/5 paired seeds. Live dev-model evidence: mechanics confirmed at 0.5B scale. Protocol test on Mistral-7B has not been run.
- "Entropy correlates usefully with task difficulty for control purposes" — PLAUSIBLE. The accuracy non-inferiority clause in B3 exists precisely because this correlation has known confounds.

### SPECULATIVE
The claim is internally coherent and worth pursuing, but lacks empirical grounding and/or sits outside the falsifiable surface of the current benchmark.

**Examples:**
- "Plasticity deserves substrate-level status as a sixth Preverbal Road" — SPECULATIVE, pending the canonical Joule Road definition check.
- "Functional flow architecture produces phenomenology" — permanently SPECULATIVE; the hard problem is not in scope.
- "Layer 5+ empirical grounding is achievable from current methods" — SPECULATIVE; explicitly flagged in the RCA project.

## Upgrade rules

A claim is upgraded from SPECULATIVE → PLAUSIBLE when:
- Cited or reproducible evidence appears for the mechanism, even if not yet the integrated claim.
- A first-principles argument is constructible from VERIFIED components.

A claim is upgraded from PLAUSIBLE → VERIFIED when:
- A protocol-bound test runs and confirms.
- An independent reviewer (not the author) reproduces the result.
- For cryptographic claims, a deterministic check exists and runs clean.

Upgrades are documented in the relevant file (often the CHANGELOG, sometimes in commit messages).

## Downgrade rules

A claim is downgraded:
- From VERIFIED → PLAUSIBLE when an independent attempt to reproduce yields a different result; the discrepancy must be investigated.
- From VERIFIED → FALSIFIED when a deterministic test that previously confirmed now disconfirms (e.g., a defect was hidden in the test, fixed, and the claim fails the corrected test).
- From PLAUSIBLE → FALSIFIED when the protocol test runs and disconfirms.
- From any marker → withdrawn when the claim is shown to be incoherent or based on a definitional confusion.

**Downgrades are never silent.** A downgraded claim's prior status is preserved in the CHANGELOG and the document where it appeared. The first hostile review of benchmark v1.0 functionally downgraded six threshold claims from PLAUSIBLE to FALSIFIED-as-stated; rather than soften them, they were redefined in v1.0.1 with the prior versions preserved in the OTS-stamped v1.0 bundle.

## Failure modes the discipline prevents

1. **Goodhart's Law / bench-maxing.** Without epistemic markers, a system that *passes a benchmark* gets reported as *capable of the underlying construct*. With markers, "passes B3" stays VERIFIED while "produces flow" stays PLAUSIBLE — the gap is preserved in the documentation.
2. **Confidence inflation.** First-principles arguments and synthetic results creep toward sounding like protocol results unless held apart. The marker forces the distinction every time the claim appears.
3. **Sunk-cost defense.** When a downgrade is required, the discipline says: name the prior status, name the new status, document why. Defensive framing of bad outcomes is anti-methodology.
4. **Honest self-correction failure.** The maintainer has a track record of revising claims downward when evidence warrants (this is documented). The framework exists so that record is structural, not personality-dependent.

## On the markers themselves

These markers do not encode confidence in a Bayesian sense. They encode the *kind of evidence* behind a claim. A SPECULATIVE claim may be more *useful* than a VERIFIED one (the sixth-Road argument is more important than the fact that SHA-256 is deterministic). They are about epistemic provenance, not value.

## Sister documents

- [`METHODOLOGY.md`](METHODOLOGY.md) — ZCS-6, the procedural counterpart to this framework.
- [`SIXTH_ROAD.md`](SIXTH_ROAD.md) — the longest-running SPECULATIVE claim in the project.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — where markers cluster densely; useful to read for examples.
