# NOTE: v1.0.1 SUPERSEDES v1.0 — sign THIS bundle, not v1.0.
# v1.0 carries the F-B1 instruction defect (50/60 task divergence); see DELTA_v1.0.1.md.

# LEDGER ENTRY CANDIDATE — proteus-bench v1.0.1 (PROTEUS-002)
## ZCS-6 Phase 4 Commit Package — SIGNATURE PENDING

---

## ⚠ CHAIN SEQUENCING COLLISION — RESOLVE BEFORE SIGNING

**LEDGER #0004 is already reserved by another candidate.** The Caduceus session declared CADUCEUS-004 (caduceus-bench v1.2.1, manifest hash `0fe3b32db5522db65dda8dbc46b1aa9fcc40c418a21cc8abb2df7340a528f874`) as the LEDGER #0004 candidate, deliberately held for your confirmation pending five Category A tightenings and practitioner review.

**Resolution rule:** whichever bundle you sign first takes #0004 on the authoritative chain; the other becomes #0005 with its `prev_ledger_hash` pointing at the first. The payload below uses `<ENTRY_NUMBER>` placeholders accordingly. Both orderings are valid; what is invalid is two entries claiming the same number. Decide at signing time, not here.

---

## Commit facts (computed this session, machine-verifiable)

| Field | Value |
|---|---|
| Bundle | `proteus-bench-v1.0/` (10 files (adds DELTA_v1.0.1.md)) |
| Manifest hash (SHA-256, Merkle-style sorted `rel_path:sha256` lines — same construction as VBX-ISPS LEDGER #0003) | `03e27b6284405adb3dcdae5587be7f58cdb28677a2556105f710284cb4355bb6` |
| OpenTimestamps | **STAMPED** — `BUNDLE_HASH.txt.ots` submitted to 4 calendar servers (a.pool.opentimestamps.org, b.pool.opentimestamps.org, a.pool.eternitywall.com, ots.btc.catallaxy.com) at 2026-06-10T03:24Z. Run `ots upgrade BUNDLE_HASH.txt.ots` after ~24h to embed the Bitcoin attestation, then `ots verify`. |
| Auditor validation | `verify_chain.py` end-to-end tested this session: clean synthetic chain → exit 0; tampered row → exit 1 with turn-level localization. Test keypair was ephemeral, used only to validate auditor logic, discarded, and **not** part of the bundle. |
| Frozen artifacts | canary set (100 tasks, sha256 `5c97256f…`), calibration prompts (200), convention pool generator (500 items: 160 SUB / 150 BAN / 90 FMT / 100 PROC), staircase generator (60 turns / 12 levels) |
| Predecessor documents | Proteus_Plasticity_Substrate_Specification.md v0.1 (superseded §2–3 by this bundle per HOSTILE_REVIEW_DELTA.md; §1, §5–9 remain the architecture reference) |

## Per-file hashes

```
BENCHMARK_v1.0.md                      4ca655910abeee44…
HOSTILE_REVIEW_DELTA.md                832041ee3d7a746a…
auditor/verify_chain.py                4e4926b165fb999e…
calibration/calibration_prompts.json   2e69fdf0c77e15ae…
calibration/fit_band.py                e4d77a1efaa1048b…
canary/t_can_tasks.json                5c97256fa9cfc350…
generators/t_can_generate.py           9f61293d8cd3f058…
generators/t_ds_staircase.py           a8fd7a7c60ff4d3b…
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
  "document_id": "PROTEUS-002",
  "document_revision": "A",
  "document_title": "PROTEUS-Bench v1.0.1 — Online State Adaptation Benchmark (Sixth Road Candidate)",
  "ledger_entry_number": "<ENTRY_NUMBER — 4 or 5 per collision resolution>",
  "manifest_byte_count": 85318,
  "manifest_hash": "03e27b6284405adb3dcdae5587be7f58cdb28677a2556105f710284cb4355bb6",
  "manifest_hash_algorithm": "SHA-256",
  "predecessor_documents": [
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

1. **Independent hash verification** at your machine: unzip the bundle, recompute — any mismatch, STOP and investigate line-ending normalization:
   ```bash
   cd proteus-bench-v1.0 && python3 - << 'EOF'
   import hashlib
   from pathlib import Path
   files = sorted(p for p in Path('.').rglob('*') if p.is_file()
                  and p.name not in ('MANIFEST.json','BUNDLE_HASH.txt','BUNDLE_HASH.txt.ots','LEDGER_0004_CANDIDATE.md'))
   lines = '\n'.join(f"{p}:{hashlib.sha256(p.read_bytes()).hexdigest()}" for p in files)
   print(hashlib.sha256(lines.encode()).hexdigest())
   # expect: 03e27b6284405adb3dcdae5587be7f58cdb28677a2556105f710284cb4355bb6
   EOF
   ```
2. Resolve the #0004/#0005 collision (sign order decides).
3. Retrieve `prev_ledger_hash` from the authoritative chain.
4. Fill payload, canonicalize (JCS), sign with the Visionblox release key, append.
5. After ~24h: `ots upgrade BUNDLE_HASH.txt.ots && ots verify BUNDLE_HASH.txt.ots`.

## Provenance honesty note

This session computed hashes and obtained the OTS calendar stamp; it did **not** and cannot Ed25519-sign — the release key never leaves your custody. Until step 4 completes, this is a candidate, not a chain entry. The OTS stamp independently proves the bundle existed in its exact byte form before signing, which preserves the benchmark-precedes-solution ordering even while the signature is pending.

## Post-commit gate

Per ZCS-6 and the user directive: **no Loop A code before the signature lands.** First permitted Phase 5 action after signing: Week-1 F0 baseline harness (records the pinned llama.cpp build hash that B1b and the calibration band bind to).
