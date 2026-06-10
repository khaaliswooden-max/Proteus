# Proteus — Plasticity Substrate for Frozen-Weight LLMs

**Online state adaptation under deterministic governance, without weight updates.**

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Methodology](https://img.shields.io/badge/methodology-ZCS--6-green.svg)](docs/METHODOLOGY.md)
[![Status](https://img.shields.io/badge/status-Phase%204%20commit%20pending-orange.svg)](LEDGER_CHAIN.md)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)

Proteus is the sixth-Road candidate in the [Five Preverbal Roads](docs/SIXTH_ROAD.md) framework — the substrate carrying lawful, provenance-bound mutation of a cognitive system's internal state within and across activation windows.

Concretely: a frozen-weight LLM (Mistral-7B-Instruct-v0.3 in the reference profile) wrapped in a three-loop architecture that gives it sustained engagement without retraining.

## What this repo contains

| Path | Purpose |
|---|---|
| `proteus-bench-v1.0.2/` | Frozen benchmark bundle (PROTEUS-003; OTS stamp pending operator action). Specification, task generators, canary set, independent auditor, hostile-review delta, delta records. Manifest hash `3d14ac4b…`. |
| `loop_a/` | Reference implementation of Loop A (per-turn micro-calibration) and Loop B (signed episodic state). Validated end-to-end against real model logits. |
| `docs/` | Architecture (`ARCHITECTURE.md`), methodology (`METHODOLOGY.md`), sixth-Road argument (`SIXTH_ROAD.md`), epistemic framework (`EPISTEMIC_FRAMEWORK.md`). |
| `keys/` | Public verification key (`visionblox-release-key-v1.pub`) and fingerprint. |
| `LEDGER_*.json` | Signed ledger entries (Aletheia provenance chain). |
| `LEDGER_CHAIN.md` | Human-readable index of the chain. |

## The three-loop architecture (one paragraph)

A frozen LLM has no plasticity — same prompt today, same prompt next year, identical response. Proteus adds three nested loops at three timescales. **Loop A** (per turn) reads the model's own pre-sampling token entropy as a *challenge* signal, an Adaptive Conformal Inference band width as a *skill* signal, and steers a banded controller that holds challenge slightly above calibrated skill — the Csikszentmihalyi flow condition, applied to a transformer. Its actuators are retrieval depth, control-vector gain, and scaffold density. **Loop B** (per episode) records every state transition to a SQLite chain with Ed25519 signatures and SHA-256 linkage — a portable, auditable provenance trail. **Loop C** (offline) mines episodes for new control vectors and LoRA adapters, promoted only through a hard canary gate and human approval.

Detail: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Why this is a substrate, not a feature

The Five Preverbal Roads frame minimal substrate kinds for a cognitive system: energy, representation, intent, world-coupling, and trust/provenance. None of them carries *plasticity* as substrate — they specify what is, not what changes. A system can have all five and be frozen. Proteus argues plasticity belongs as Road VI, with the same first-class architectural status. [`docs/SIXTH_ROAD.md`](docs/SIXTH_ROAD.md).

## What's verified vs. what isn't

Following the project's [epistemic discipline](docs/EPISTEMIC_FRAMEWORK.md):

- **VERIFIED:** the integration is buildable on open-source components; the signed chain is verifiable by independent auditor (test demonstrated: clean chain exit 0, tampered row exit 1); benchmark hashes recomputable from public code; sign/verify round-trip works against the public key alone.
- **PLAUSIBLE:** the three-loop architecture produces functional flow analogs; entropy correlates usefully with task difficulty; the controller can hold the band better than a frozen baseline (synthetic: +16.7 pt occupancy, 5/5 paired seeds; live dev-model: mechanics confirmed, accuracy floor expected for 0.5B model).
- **SPECULATIVE:** whether any of this produces phenomenology; whether Proteus generalizes beyond text; whether Loop C consolidation reaches benchmark-passing without weight-level methods.

The benchmark exists to convert PLAUSIBLE claims into VERIFIED or FALSIFIED ones. It was committed and OTS-stamped before any Loop A code was written. The discipline matters: any solution that subsequently passes does so against a contract it could not have shaped.

## ZCS-6 ordering — why benchmark before solution

This project follows the **Zuup Creative Stack** (ZCS-6): find whitespace → commit falsifiable benchmark cryptographically → attack the benchmark → defend deterministically → build solution → attack until vertically integrated. Committing the benchmark before any solution exists prevents Goodhart's Law — you cannot tune thresholds to flatter results you don't yet have.

Evidence the discipline works: the *first* hostile review of v1.0 found two critical defects (F1: gameable relative-gain framing; F2: drift gate fails on sampling noise) and ten total findings. The *first live run* of Loop A found the controller's own saturation bug (the committed auditor caught it, exit 4) and a defect in the committed benchmark itself (F-B1, instruction ambiguity on 50/60 tasks). v1.0 → v1.0.1 was a legal versioned update with full delta record. See [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

## Quick verification (anyone, no install of project deps required)

```bash
# Verify the benchmark bundle hash independently:
python3 - <<'PY'
import hashlib
from pathlib import Path
root = Path("proteus-bench-v1.0.2")
skip = {"MANIFEST.json","BUNDLE_HASH.txt","BUNDLE_HASH.txt.ots","LEDGER_CANDIDATE.md"}
files = [p for p in sorted(root.rglob("*"))
         if p.is_file() and p.name not in skip and "__pycache__" not in str(p)]
lines = "\n".join(f"{p.relative_to(root)}:{hashlib.sha256(p.read_bytes()).hexdigest()}" for p in files)
print(hashlib.sha256(lines.encode()).hexdigest())
# expect: 3d14ac4b77deede20daae1b319bb5c370b71db83c58c693587651d9cf4856e58
PY

# Verify the calibration artifact reproduces from its committed generator (F-B2 regression):
cd proteus-bench-v1.0.2/calibration && python3 fit_band.py --emit-prompts | diff - calibration_prompts.json && cd ../..

# Verify the OTS stamp of the superseded v1.0.1 bundle (v1.0.2's stamp pending operator action):
ots upgrade archive/proteus-bench-v1.0.1/BUNDLE_HASH.txt.ots
ots verify  archive/proteus-bench-v1.0.1/BUNDLE_HASH.txt.ots

# Verify the Ed25519 signature on the ledger entry:
python3 zil_sign.py verify --entry LEDGER_0004.json   # expects: VALID
```

## Running Loop A (developers)

```bash
pip install cryptography llama-cpp-python
# Place a GGUF model at models/qwen2.5-0.5b-instruct-q4_k_m.gguf or point
# PROTEUS_DEV_MODEL at one (dev: any small instruct model;
# benchmark: Mistral-7B-Instruct-v0.3 Q4_K_M per protocol).
python3 loop_a/run_synthetic.py    # closed-loop simulator, ~seconds
python3 loop_a/run_live.py         # real-model integration, minutes
```

The committed auditor (`proteus-bench-v1.0.2/auditor/verify_chain.py`) validates the chain produced by either run. **Measured benchmark assertions (B1–B6)** require the protocol model, pinned llama.cpp build, and the full 5-seed × 10-episode harness — this repo does not gate that behind tooling, the integrity comes from the signed bundle, not from us running it.

## Status and roadmap

- ZCS-6 **Phase 4** (deterministic defense): **COMPLETE** — LEDGER #0004 signed 2026-06-10 ([`LEDGER_0004.json`](LEDGER_0004.json), verifies against [`keys/visionblox-release-key-v1.pub`](keys/visionblox-release-key-v1.pub)); Loop A validated end-to-end. Remaining housekeeping: OTS stamp over the v1.0.2 bundle hash — see [`LEDGER_CHAIN.md`](LEDGER_CHAIN.md).
- ZCS-6 **Phase 5** (solution build): F0 baseline on Mistral-7B → full Loop A v0.2 with graded nonconformity (F-A3) → Loop C consolidation. See [`ROADMAP.md`](ROADMAP.md).

## Authorship and provenance

Author: **A. Khaalis Wooden, Sr.** (MBA; MSIT Candidate, Southern New Hampshire University), Visionblox LLC / Zuup Innovation Lab. Citation metadata in [`CITATION.cff`](CITATION.cff).

## License

Apache 2.0 — see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE). The Apache 2.0 patent grant is intentional: this repo serves as defensive disclosure for the governed-plasticity integration.

## Contributing, conduct, security

[`CONTRIBUTING.md`](CONTRIBUTING.md) · [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) · [`SECURITY.md`](SECURITY.md) · [`GOVERNANCE.md`](GOVERNANCE.md)
