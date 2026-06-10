# Ledger Chain — Aletheia Provenance

This file is the human-readable index of the cryptographic ledger. Each row corresponds to a `LEDGER_NNNN.json` file in the repository root. Authoritative truth is the JSON entries and their Ed25519 signatures, not this file — if they disagree, **trust the cryptography**.

Verification key: [`keys/visionblox-release-key-v1.pub`](keys/visionblox-release-key-v1.pub).
Fingerprint (first 16 hex of SHA-256 of the `.pub` file): *recorded in `keys/README.md` after key ceremony.*

## Chain

| # | Document ID | Title | Manifest hash (first 16) | Date | Status |
|---|---|---|---|---|---|
| 0004 | PROTEUS-002 | proteus-bench v1.0.1 — Online State Adaptation Benchmark | `03e27b6284405adb` | *pending signature* | **awaiting signing ceremony** |

## #0004/#0005 collision note

`PROTEUS-002` and `CADUCEUS-004` (held pending five Category A tightenings and patent practitioner review) both claimed entry #0004 in preparation. **Resolution:** whichever is signed first takes #0004 on the authoritative chain; the other becomes #0005 with its `prev_ledger_hash` pointing at the first. Proteus is signing-ready *now*; Caduceus is held. The default ordering applied here is Proteus → #0004, Caduceus → #0005 when its review completes.

**Decision record (ZCS-6 Phase 4, Task 2, 2026-06-10):** default resolution applied — **PROTEUS-002 takes #0004** (manifest `03e27b6284405adb3dcdae5587be7f58cdb28677a2556105f710284cb4355bb6`); CADUCEUS-004 becomes #0005 when its five Category A tightenings and practitioner review complete. Rationale: Proteus is signing-ready; Caduceus is deliberately held. Operator may override at signing time, in which case this record and the table above must be amended in the same commit as the signature.

## Payload corrections vs. LEDGER_CANDIDATE.md

The candidate's draft payload lists `manifest_byte_count: 85318`. That figure is the hashed-file byte total of the **superseded v1.0 bundle** (9 files, verified against `archive/proteus-bench-v1.0/`) and was carried over stale. The correct v1.0.1 value is **88137** (10 hashed files, matching `MANIFEST.json` `total_bytes`). `zil_sign.py` computes this field from the bundle at signing time, so the signed payload will carry 88137. The candidate's per-file hash table is likewise the stale v1.0 list; `MANIFEST.json` (verified file-by-file against the bundle) is authoritative. The manifest *hash* `03e27b62…` is unaffected — it recomputes correctly from the v1.0.1 bundle.

## Pre-history (unsigned predecessors)

The following hashes exist in prior work and may be retroactively signed and incorporated into this chain as entries #0001–#0003. If they are, this section becomes the second canonical chain segment. If they are not, they remain documented attestations without cryptographic chain authority.

| Document | Manifest hash | Origin |
|---|---|---|
| VBX-EPHEMERIS substrate v0.2-α benchmark | *to be retrieved from project archive* | LEDGER #0005 candidate (per project notes) |
| VBX-ISPS substrate benchmark v1.2 (CADUCEUS-003) | *as recorded in source project* | LEDGER #0003 candidate (per project notes) |
| Aletheia DAC substrate v0.1 | *as recorded in source project* | earlier substrate |

Retroactive signing is *recommended* for chain end-to-end authority but is *not a Phase 5 blocker*. Forward-chain linkage from #0004 onward is intact regardless, because `prev_ledger_hash` is computed over the previous entry's *payload*, not its signature — and the payload exists once committed.

## Verification

```bash
# Verify a single signed entry against the public key:
python3 zil_sign.py verify --entry LEDGER_0004.json   # expects: VALID

# Independently recompute the bundle hash referenced by an entry:
python3 - <<'PY'
import hashlib
from pathlib import Path
root = Path("proteus-bench-v1.0.1")
skip = {"MANIFEST.json","BUNDLE_HASH.txt","BUNDLE_HASH.txt.ots","LEDGER_CANDIDATE.md"}
files = [p for p in sorted(root.rglob("*"))
         if p.is_file() and p.name not in skip and "__pycache__" not in str(p)]
print(hashlib.sha256("\n".join(
    f"{p.relative_to(root)}:{hashlib.sha256(p.read_bytes()).hexdigest()}"
    for p in files).encode()).hexdigest())
PY

# Verify the OpenTimestamps proof (after ~24h post-stamp for Bitcoin confirmation):
ots upgrade proteus-bench-v1.0.1/BUNDLE_HASH.txt.ots
ots verify  proteus-bench-v1.0.1/BUNDLE_HASH.txt.ots
```

Three independent confirmations: cryptographic signature (who), bundle hash (what), OpenTimestamps anchor (when). All three must hold for a chain entry to be authoritative.

## Why this file exists alongside the JSON

The signed JSON entries are machine-truth. This file is human-truth: at-a-glance chain state, decision context (the #0004/#0005 note), and verification examples. Future readers should treat this file as orientation and the JSON entries as ground.
