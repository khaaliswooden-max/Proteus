# Governance

This document describes how the Proteus project is governed, who decides what, and the conflicts of interest that motivate the discipline this repo enforces. Methodology credibility depends on this transparency.

## Project structure

Proteus is one of several research substrates produced by **Zuup Innovation Lab (ZIL)**, the IP/R&D arm of **Visionblox LLC**. Visionblox is the commercial and federal-delivery vehicle; ZIL is the research vehicle. They share a founder.

## Roles

### Maintainer (single, at present)

- **A. Khaalis Wooden, Sr.** (Visionblox LLC / ZIL) — primary author, sole maintainer as of repository publication. Holds the `visionblox-release-key-v1` Ed25519 private key. Responsible for: ledger commits, benchmark version increments, security advisories, and final say on architectural direction.

### Contributors

Anyone who opens an accepted PR. Contributors do not hold signing authority over the chain; they participate in code, documentation, hostile review, and proposals.

### External reviewers

Engaged ad-hoc for hostile review of pre-commit benchmark bundles (see [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) §3). The current pre-commit hostile review (recorded in `proteus-bench-v1.0.2/HOSTILE_REVIEW_DELTA.md`) was performed in-session prior to publication; subsequent benchmark versions will seek at least one outside reviewer prior to commit.

## Decision-making

1. **Ledger commits** (benchmark versions, signed entries) — Maintainer decision, executed only by the holder of the signing key. Documented in `LEDGER_CHAIN.md`.
2. **Code merges** — Maintainer reviews and merges. PRs from new contributors get explicit acknowledgment of the methodology rules before merge.
3. **Methodology changes** (ZCS-6 application, epistemic framework, governance) — Maintainer, with the constraint that already-committed claims and chain entries cannot be retroactively re-categorized.
4. **Disputes** — Open an issue tagged `governance`. Maintainer responds in writing. There is no appeal layer above the maintainer at this stage of the project; this is acknowledged as a limitation and will be revisited if a second maintainer joins.

## Conflicts of interest (required disclosure)

The maintainer has the following declared interests in subjects touching this repository:

- **Founder, Visionblox LLC** — commercial deployment vehicle for federal/SLED engagements; Proteus and related substrates may be incorporated into Visionblox products under Apache 2.0's terms.
- **Founder, Zuup Innovation Lab** — IP/R&D entity; holds IP rights consistent with the NOTICE file. The Apache 2.0 patent grant is irrevocable as to the disclosed integration; reservations apply only to undisclosed future work.
- **Convergent IP portfolio** — the maintainer is developing related substrates (Ephemeris, Caduceus, Aletheia, Civium, Mercury, MVCI, RCA framework). Proteus shares the Aletheia-style provenance pattern, the ACI signal from Ephemeris, and the MVCI approval-gate from the Visionblox compliance stack. Cross-substrate reuse is intentional and not concealed.
- **No outside funding** of this work to date, beyond the founder's personal time and the zero-budget infrastructure documented in the BOM. Disclosures will be updated if this changes.

## Why this matters operationally

The benchmark-first methodology (ZCS-6) is designed precisely to keep founder-author conflicts from corrupting capability claims. When the same person designs the test and builds the solution, the test must be committed cryptographically before the solution exists. That is the structural answer to this governance reality.

If you find behavior that *appears* to contradict these disclosures (e.g., undisclosed funding, hidden licensing, threshold edits without delta records), report it via `SECURITY.md` channels.

## Joining as a maintainer

Currently single-maintainer. A second maintainer with chain-signing authority would require:
- Sustained, substantive contributions (typically multiple merged PRs over 3+ months).
- Demonstrated alignment with the ZCS-6 discipline (hostile review, epistemic markers, refusal to soften thresholds).
- Generation of an independent `visionblox-release-key-v2-<name>` keypair; the chain would document multi-signer attestation from that point forward.

## Sunsetting

If the project becomes inactive, the maintainer will mark the repo archived and publish a final ledger entry noting the freeze. The cryptographic record stands regardless of project activity status.
