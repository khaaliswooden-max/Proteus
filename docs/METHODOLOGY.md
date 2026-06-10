# Methodology — ZCS-6

The **Zuup Creative Stack** (ZCS-6) is a six-phase procedure for technical work whose central discipline is **commitment ordering**: the benchmark must be cryptographically committed before the solution exists. This document explains the procedure, why it differs from standard ML evaluation practice, and how it is enforced in this repository.

## The six phases

1. **Whitespace.** Establish that a real gap exists. Four conditions must all hold: structural demand, visible incumbent failure, real technical barrier, high re-entry cost. Documented in the relevant spec §1.
2. **Benchmark.** Define the falsifiable contract. Assertions, thresholds, task suites, statistical protocol, pre-registered cheats with countermeasures. Frozen as a bundle.
3. **Attack the benchmark.** Hostile-review the bundle. Every threshold defended against gameability, noise, Goodhart, hardware confounds, statistical fishing. Findings either fix the bundle or are pre-registered as accepted residuals.
4. **Defend deterministically.** Compute manifest hash; OpenTimestamps anchor; Ed25519 sign with a key whose public counterpart is published. The bundle is now cryptographically pinned — silent edits are impossible.
5. **Build the solution.** Now and only now, build the system intended to pass the benchmark. The contract cannot be moved.
6. **Attack until vertically integrated.** Hostile-review the *solution*. Try the pre-registered cheats. Look for new ones. Iterate until passing is not gameable.

Back-edges between phases are legal and expected. Phase 5 work that surfaces a benchmark defect triggers a **back-edge to Phase 2**: a versioned re-commit with a delta record. v1.0 → v1.0.1 was such a back-edge, triggered by the F-B1 finding on first contact between Loop A and a real model.

## Why this ordering

The dominant failure mode in capability research is **Goodhart's Law**: a measure becomes a target, and the target gets optimized in ways that do not advance the underlying construct. The standard ML response (held-out test sets, model cards, eval suites) addresses some of this but suffers from a structural problem: the test designer and the model trainer share interests when they share a paycheck.

ZCS-6's commitment ordering is the cryptographic analog of double-blind: not "we promise we didn't peek," but "we mathematically could not have peeked." If the bundle hash predates the solution, threshold-tuning to flatter the solution is provably impossible. The OpenTimestamps anchor makes that provability public — anyone can verify the ordering without trusting us.

This matters most where the author has commercial interests in the answer. The maintainer of this project does. See [`GOVERNANCE.md`](GOVERNANCE.md) §"Conflicts of interest." The methodology is the structural response to that reality.

## Comparison to common alternatives

| Practice | What it offers | What it doesn't |
|---|---|---|
| Held-out test set | Models can't see test labels at train time | Maintainers can edit thresholds post-hoc |
| Public leaderboards | Many eyes on the same task | Tasks evolve to favor incumbent approaches |
| Model cards | Documented training data and limits | No commitment ordering |
| Audit logs | After-the-fact reconstructability | No before-the-fact commitment |
| **ZCS-6** | **Cryptographic ordering of benchmark before solution** | More setup cost; requires discipline to honor back-edges |

ZCS-6 does not replace any of the above. It adds a layer they don't provide.

## How this repo enforces the methodology

- **Bundle hashes are recomputable** by anyone from public code. The `MANIFEST.json` is convenience; the *true* manifest hash construction is documented and reproducible.
- **OpenTimestamps proofs** are committed alongside bundles. After ~24h post-stamp, the Bitcoin attestation is embeddable and verifiable with `ots verify`.
- **The auditor (`verify_chain.py`) is committed in the bundle**, not in the solution code. A solution-side auditor would be untrustworthy by construction; the bundle-side auditor is part of the contract.
- **Threshold changes require versioned re-commit + delta record.** Silent edits are impossible by hash, and prohibited by policy on top of that.
- **The CHANGELOG records phase transitions and back-edges.** When a back-edge happens (Phase 5 → Phase 2 due to a benchmark defect), the trigger is recorded, the new bundle hash is recorded, and the old bundle remains visible as superseded.

## The first-contact test

A useful heuristic: a well-designed benchmark **finds defects in itself when first deployed against a real solution**, because no amount of dry analysis catches every confounded prompt or noise-fragile threshold. Proteus's v1.0 → v1.0.1 transition is an instance: the benchmark detected its own ambiguous instruction (F-B1) on first model contact. That is the methodology working as intended, not failing.

The hostile review prevents the easy problems. First contact prevents the rest.

## Sister documents

- [`EPISTEMIC_FRAMEWORK.md`](EPISTEMIC_FRAMEWORK.md) — claim markers, the static counterpart to ZCS-6's procedural discipline.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — what Phase 5 actually builds.
- [`SIXTH_ROAD.md`](SIXTH_ROAD.md) — the substrate-level argument the methodology serves.
