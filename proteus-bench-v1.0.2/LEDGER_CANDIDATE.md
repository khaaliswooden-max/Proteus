# NOTE: v1.0.2 SUPERSEDES v1.0.1 — sign THIS bundle, not v1.0.1.
# v1.0.1 carries the F-B2 reproducibility defect (calibration artifact not regenerated); see DELTA_v1.0.2.md.

# LEDGER ENTRY CANDIDATE — proteus-bench v1.0.2 (PROTEUS-003)
## ZCS-6 Phase 4 Commit Package — SIGNATURE PENDING

---

## ⚠ CHAIN SEQUENCING COLLISION — RESOLVE BEFORE SIGNING

**LEDGER #0004 is already reserved by another candidate.** The Caduceus session declared CADUCEUS-004 (caduceus-bench v1.2.1, manifest hash `0fe3b32db5522db65dda8dbc46b1aa9fcc40c418a21cc8abb2df7340a528f874`) as the LEDGER #0004 candidate, deliberately held for your confirmation pending five Category A tightenings and practitioner review.

**Resolution rule:** whichever bundle you sign first takes #0004 on the authoritative chain; the other becomes #0005 with its `prev_ledger_hash` pointing at the first. The payload below uses `<ENTRY_NUMBER>` placeholders accordingly. Both orderings are valid; what is invalid is two entries claiming the same number. Decide at signing time, not here.

---

## Commit facts (computed this session, machine-verifiable)

| Field | Value |
|---|---|
| Bundle | `proteus-bench-v1.0.2/` (11 hashed files (adds DELTA_v1.0.2.md)) |
| Manifest hash (SHA-256, Merkle-style sorted `rel_path:sha256` lines — same construction as VBX-ISPS LEDGER #0003) | `3d14ac4b77deede20daae1b319bb5c370b71db83c58c693587651d9cf4856e58` |
| OpenTimestamps | **NOT YET STAMPED** — the session that built this bundle had no `ots` client. Operator action before signing: `ots stamp proteus-bench-v1.0.2/BUNDLE_HASH.txt`, commit the resulting `BUNDLE_HASH.txt.ots`, then after ~24h `ots upgrade` + `ots verify`. (v1.0.1's stamp over `03e27b62…4355bb6` remains valid for the superseded bundle in `archive/`.) |
| Auditor validation | `auditor/verify_chain.py` is byte-identical to the v1.0/v1.0.1 auditor (sha256 `4e4926b1…`), end-to-end tested in the v1.0 session: clean synthetic chain → exit 0; tampered row → exit 1 with turn-level localization. |
| Frozen artifacts | canary set (100 tasks, sha256 `5c97256f…`), calibration prompts (200, **regenerated** — sha256 `bc113ea4…`, reproduces exactly from `fit_band.py --emit-prompts`), convention pool generator (500 items: 160 SUB / 150 BAN / 90 FMT / 100 PROC), staircase generator (60 turns / 12 levels) |
| Predecessor documents | PROTEUS-002 (proteus-bench v1.0.1, superseded per DELTA_v1.0.2.md); PROTEUS-001 (proteus-bench v1.0, superseded per DELTA_v1.0.1.md) |

## Per-file hashes

```
BENCHMARK_v1.0.2.md                    d14a6a05795544bc…
DELTA_v1.0.1.md                        45ff5c52e7969dc2…
DELTA_v1.0.2.md                        f41c57d598b2000e…
HOSTILE_REVIEW_DELTA.md                832041ee3d7a746a…
auditor/verify_chain.py                4e4926b165fb999e…
calibration/calibration_prompts.json   bc113ea4bfd081c6…
calibration/fit_band.py                5880a0e493aa9a98…
canary/t_can_tasks.json                5c97256fa9cfc350…
generators/t_can_generate.py           9f61293d8cd3f058…
generators/t_ds_staircase.py           7a730748ad86b85d…
generators/t_pa_pool.py                630491c4c651fc7b…
```

Full 64-char digests in `MANIFEST.json`.

---

## Canonical signed payload (aletheia-ledger-entry-v1, RFC 8785 JCS)

Construct, canonicalize, sign with `visionblox-release-key-v1`, append to chain:

```json
{
  "author": "A. Khaalis Wooden, Sr.",
  "commit_date_tai": "<TO_BE_FILLED_AT_SIGNING — ISO 8601 with explicit Z>",
  "commit_methodology": "ZCS-6 Phase 4",
  "document_id": "PROTEUS-003",
  "document_revision": "A",
  "document_title": "PROTEUS-Bench v1.0.2 — Online State Adaptation Benchmark (Sixth Road Candidate)",
  "ledger_entry_number": "<ENTRY_NUMBER — 4 or 5 per collision resolution>",
  "manifest_byte_count": 97428,
  "manifest_hash": "3d14ac4b77deede20daae1b319bb5c370b71db83c58c693587651d9cf4856e58",
  "manifest_hash_algorithm": "SHA-256",
  "predecessor_documents": [
    {
      "document_id": "PROTEUS-002",
      "version": "proteus-bench v1.0.1 (manifest 03e27b6284405adb3dcdae5587be7f58cdb28677a2556105f710284cb4355bb6, OTS-stamped, superseded per DELTA_v1.0.2.md)"
    },
    {
      "document_id": "PROTEUS-001",
      "version": "proteus-bench v1.0 (manifest a802d7e0f2e92d0b8e67eb91fb88d335c444e63db30d89edd647ae01d3ff2331, OTS-stamped, superseded per DELTA_v1.0.1.md)"
    }
  ],
  "prev_ledger_hash": "<PREV_LEDGER_HASH_FROM_AUTHORITATIVE_CHAIN>",
  "prev_ledger_number": "<ENTRY_NUMBER minus 1>",
  "schema_version": "aletheia-ledger-entry-v1",
  "signing_algorithm": "Ed25519",
  "signing_key_identifier": "visionblox-release-key-v1"
}
```

## Signing steps

1. **Independent hash verification** at your machine — any mismatch, STOP and investigate line-ending normalization:
   ```bash
   cd proteus-bench-v1.0.2 && python3 - << 'EOF'
   import hashlib
   from pathlib import Path
   skip = {'MANIFEST.json','BUNDLE_HASH.txt','BUNDLE_HASH.txt.ots','LEDGER_CANDIDATE.md'}
   files = sorted(p for p in Path('.').rglob('*') if p.is_file()
                  and p.name not in skip and '__pycache__' not in str(p))
   lines = '\n'.join(f"{p}:{hashlib.sha256(p.read_bytes()).hexdigest()}" for p in files)
   print(hashlib.sha256(lines.encode()).hexdigest())
   # expect: 3d14ac4b77deede20daae1b319bb5c370b71db83c58c693587651d9cf4856e58
   EOF
   ```
2. **Reproducibility check (F-B2 regression):** `cd calibration && python3 fit_band.py --emit-prompts | diff - calibration_prompts.json` — must be empty.
3. **OTS stamp** (not yet done — see Commit facts): `ots stamp BUNDLE_HASH.txt`, commit the `.ots`.
4. Resolve the #0004/#0005 collision (sign order decides).
5. Retrieve `prev_ledger_hash` from the authoritative chain.
6. Fill payload, canonicalize (JCS), sign with the Visionblox release key, append.
7. After ~24h: `ots upgrade BUNDLE_HASH.txt.ots && ots verify BUNDLE_HASH.txt.ots`.

## Provenance honesty note

This session computed hashes; it did **not** obtain an OTS stamp (no client/network) and did **not** and cannot Ed25519-sign — the release key never leaves your custody. Until the stamp and signature land, this is a candidate, not a chain entry. Because v1.0.1 was never signed, v1.0.2 simply replaces it as the #0004/#0005 candidate; the benchmark-precedes-solution ordering is preserved by v1.0's and v1.0.1's existing OTS stamps plus the wording-only nature of both deltas.

## Post-commit gate

Per ZCS-6 and the user directive: **no measured Phase 5 runs before the signature lands.** First permitted Phase 5 action after signing: Week-1 F0 baseline harness (records the pinned llama.cpp build hash that B1b and the calibration band bind to).
