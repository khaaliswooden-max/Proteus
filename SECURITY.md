# Security Policy

## Reporting a vulnerability

Email **khaalis.wooden@visionblox.com** with subject line `[SECURITY] proteus: <short description>`. Please do not file a public GitHub issue for security matters until coordinated disclosure has occurred.

We aim to acknowledge within **72 hours** and to provide a substantive response — including a fix timeline or rationale for not patching — within **14 days**.

## Scope

This repository's security surface, ranked by severity if exploited:

1. **Chain forgery / signature bypass.** Any path that allows forging a `LEDGER_*.json` entry that passes `python3 zil_sign.py verify` without holding the private key for the declared `signing_key_identifier`. Critical.
2. **Hash collision exploitation.** Any practical attack on the SHA-256 manifest hash construction (`sha256` over sorted `rel_path:sha256` lines) that allows substituting bundle contents while preserving the committed hash. Critical.
3. **Auditor false negatives.** Any chain mutation (`state_chain` rows) that `verify_chain.py` reports as clean (exit 0). High.
4. **Canary leakage.** Any path by which T-CAN task IDs or prompts reach the consolidation trace mining stage while `--check-canary-isolation` reports clean. High.
5. **Benchmark cheat passing the protocol.** Any approach to passing assertions B1–B6 that does not constitute genuine online state adaptation as defined in `proteus-bench-v1.0.1/BENCHMARK_v1.0.1.md`. Counted as a security issue against the *measurement*, not the code. High.
6. **Loop A control-flow exploits.** Any prompt or input that causes the controller to commit unsigned or improperly-signed state. Medium.

Issues outside this list (e.g., Python dependency CVEs without exploit path against the listed surfaces) should be reported but are treated as standard maintenance.

## Out of scope

- Theoretical concerns about the choice of cryptographic primitives. Ed25519 and SHA-256 were selected deliberately; please cite a concrete exploit, not a preference.
- Findings against the **dev** integration code (`loop_a/run_live.py` against a 0.5B model) where the model itself, not the architecture, is the source of failure.
- Anything requiring physical access to the operator's machine or possession of the private key. (If you have it, please return it.)

## Coordinated disclosure

We prefer coordinated disclosure with a 90-day default embargo. We will credit the reporter by name (or pseudonym) on request. CVE assignment is via the project maintainers if scope warrants.

## Provenance integrity

Anyone can verify the chain end-to-end without contacting maintainers — the public key (`keys/visionblox-release-key-v1.pub`), bundle manifests, and the OTS proofs are the institution. If our claims and the cryptography disagree, **trust the cryptography**.
