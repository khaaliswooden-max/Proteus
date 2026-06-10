# DELTA RECORD — zil_sign.py v0.1 → v0.2

**Scope:** signing-ceremony tooling only. No benchmark bundle, no frozen artifact, and no signed payload is affected — this is solution-side (SemVer) versioning per the CHANGELOG policy, not a bundle re-freeze.

**Trigger:** First hostile use — the actual LEDGER #0004 signing ceremony (2026-06-10), run cross-platform — surfaced two bugs in `bundle_hash()`, the function that independently recomputes the manifest hash before signing.

## Defects

| ID | Defect | Effect |
|---|---|---|
| F-S1 | Relative paths interpolated via `str(Path)`, which uses backslash separators on Windows | Manifest lines read `generators\t_pa_pool.py:…` instead of the canonical `generators/t_pa_pool.py:…` → different SHA-256 |
| F-S2 | File list sorted as `Path` objects; `Path` ordering is case-folded on Windows (`_str_normcase`) but byte-order on POSIX | Line *order* differs across platforms whenever upper/lowercase names interleave (e.g. `BENCHMARK_…` vs `auditor/…`) → different SHA-256 |

Either defect makes a Windows recomputation disagree with the committed hash. **The failure mode was the designed one:** `sign` refuses on mismatch ("STOP: hash mismatch vs expected"), so no incorrect hash could ever be signed — the ceremony was blocked, not corrupted. That is the deterministic-defense gate doing its job; the cost was operator time, not integrity.

## Change

`bundle_hash()` now sorts **POSIX-style relative path strings** (`Path.relative_to(...).as_posix()`) in byte order and builds the manifest lines from those strings. This matches the construction used by `MANIFEST.json` ("sha256 over sorted rel_path:sha256 lines") and the verification snippets in `README.md` / `LEDGER_CHAIN.md`, on every platform.

Also in v0.2 (repo-layout accommodation, not a defect): `verify` gains an optional `--pubkey` argument and by default looks for the public key in both `.` and `keys/`, so `python3 zil_sign.py verify --entry LEDGER_0004.json` works from the repository root as documented.

## Verification

- `python3 zil_sign.py verify --entry LEDGER_0004.json` → `VALID` against `keys/visionblox-release-key-v1.pub` (fingerprint `768834d6e7dc525e`).
- v0.2 `bundle_hash("proteus-bench-v1.0.2")` recomputes `3d14ac4b77deede20daae1b319bb5c370b71db83c58c693587651d9cf4856e58` and 97,428 bytes over 11 files, matching both `MANIFEST.json` and the signed payload of LEDGER #0004.
