---
name: Bug report
about: A defect in Proteus code or documentation
title: "[BUG] "
labels: bug
---

## Where is the bug

- [ ] Loop A / Loop B implementation (`loop_a/`)
- [ ] Committed benchmark bundle (`proteus-bench-v1.0.2/`) — *see note below*
- [ ] Auditor / chain integrity
- [ ] Documentation
- [ ] Build / install / dependencies
- [ ] Other:

**Note on benchmark bugs:** Defects in an OTS-stamped bundle cannot be fixed in place — they require a versioned re-commit (v1.0.1 → v1.0.2) with a `DELTA_v1.0.2.md` justification. Please flag these explicitly so they get the right handling. See `CONTRIBUTING.md` §1.

## Reproduction

**Environment:**
- OS:
- Python version:
- `llama-cpp-python` version (if applicable):
- llama.cpp build hash (if known):
- Model (path / name / quantization):

**Exact command:**
```
```

**Observed output (paste verbatim, include hash mismatches in full):**
```
```

**Expected output:**
```
```

## Severity

- [ ] Critical — chain integrity, signature bypass, hash collision
- [ ] High — auditor false negative, benchmark cheat, canary leakage
- [ ] Medium — controller misbehavior, latency violation, replay failure
- [ ] Low — cosmetic, documentation, edge case

## Additional context

Logs, screenshots, related issues, etc. **Do not paste private keys, passphrases, or any `.pem` content.** If you suspect a security issue, follow [`SECURITY.md`](../SECURITY.md) instead of opening a public issue.
