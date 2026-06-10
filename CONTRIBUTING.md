# Contributing to Proteus

Thank you for considering a contribution. This project is unusual in that its discipline is the product, not just its code. Reading this document fully is genuinely worth your time.

## The non-negotiables

1. **No benchmark threshold changes without a versioned re-commit.** The benchmark bundle is OTS-stamped; in-place modification is cryptographically impossible. If a threshold is wrong, the path is `v1.0.1 → v1.0.2` with a complete `DELTA_v1.0.2.md` justification. Silent edits are a class violation.
2. **Hostile-review before commit, not after.** Every proposal that touches the benchmark surface ships with its own pre-registered attack analysis. PRs without one will be closed with a link to [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).
3. **Provenance integrity.** Never commit `*.pem` or any file matching `*key*.pem`/`*private*`. The repo's `.gitignore` blocks these; do not weaken it.
4. **Epistemic markers required.** Any claim about Proteus's behavior carries VERIFIED, PLAUSIBLE, or SPECULATIVE in the contributing text. See [`docs/EPISTEMIC_FRAMEWORK.md`](docs/EPISTEMIC_FRAMEWORK.md).

## How to contribute

### Trivial fixes (typos, doc clarity, dead links)
Open a PR. Squash to a single commit. No issue required.

### Bug reports
Open an issue using the template. For bugs in the **solution** (Loop A/B code, dev harness), include: model, llama.cpp build hash, seed, exact command, observed output, expected output. For bugs in the **benchmark** (anything under `proteus-bench-v1.0.2/`), see §1 above — these are extraordinary events; we treat them like benchmark v1.0 → v1.0.1, which was a benchmark defect found at first contact with a real model.

### Feature proposals
Open an issue first; do not start coding. The bar:
- Does this advance a known open finding (F-A3 graded nonconformity, control-vector training loop, etc.)?
- If new: does it pass the four-condition whitespace test (structural demand + visible incumbent failure + real technical barrier + high re-entry cost)?
- What is the failure mode of the proposed approach, before its success mode?

### Benchmark contributions
- Proposing new assertions or task suites: open an issue, propose in writing, accept hostile review. Acceptable additions usually fill gaps explicitly flagged in the spec (e.g., the v1.1 safety-judged canary).
- Proposing threshold changes: requires demonstrating empirically that the current threshold is *wrong* (admits trivial passes, fails on noise, measures the wrong construct), not merely *tight*.

### Code style
- Python 3.10+, PEP 8, type hints encouraged on public functions.
- Determinism is a value. Functions that have hidden state, system clock dependence, or unseeded randomness need a justification comment.
- Tests for any cryptographic or chain-handling code. Round-trip tests preferred over mocks.

## Pull request checklist

- [ ] Tests pass locally.
- [ ] No new secrets, keys, or `.pem` files anywhere in the diff.
- [ ] Documentation updated if behavior changed.
- [ ] Epistemic markers applied to new claims.
- [ ] If touching the benchmark: linked DELTA record drafted.
- [ ] Commit message references the issue and uses the convention below.

### Commit message convention

```
<area>: <imperative summary>

<body explaining why, not what. Reference issue.>

Refs: #<issue>
```

Areas: `loop-a`, `loop-b`, `loop-c`, `bench`, `auditor`, `docs`, `chain`, `ci`, `deps`.

## Sign-off

We do not require DCO sign-off. We do require that contributions are yours to make under Apache 2.0. By opening a PR, you affirm this.

## Conflict of interest

This project's author is the founder of Visionblox LLC and Zuup Innovation Lab; commercial deployments and IP strategy are documented in [`GOVERNANCE.md`](GOVERNANCE.md). Methodology credibility depends on this transparency. Contributors with their own commercial interests touching the same space should disclose them in their PR description.

## Code of Conduct

By contributing, you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).
