# Ledger Chain — Aletheia Provenance

This file is the human-readable index of the cryptographic ledger. Each row corresponds to a `LEDGER_NNNN.json` file in the repository root. Authoritative truth is the JSON entries and their Ed25519 signatures, not this file — if they disagree, **trust the cryptography**.

Verification key: [`keys/visionblox-release-key-v1.pub`](keys/visionblox-release-key-v1.pub).
Fingerprint (first 16 hex of SHA-256 of the `.pub` file): `768834d6e7dc525e`.

## Chain

| # | Document ID | Title | Manifest hash (first 16) | Date | Status |
|---|---|---|---|---|---|
| 0004 | PROTEUS-003 | proteus-bench v1.0.2 — Online State Adaptation Benchmark | `3d14ac4b77deede2` | 2026-06-10 | **signed** ([`LEDGER_0004.json`](LEDGER_0004.json)) |

LEDGER #0004 payload hash (full, becomes `prev_ledger_hash` for #0005):
`0217ae85687ea7620ef4ead6fb5c42e02e787c3aff5b5a3d4523ccd864793be9`.
`prev_ledger_hash` of #0004 is `GENESIS` — pre-history entries #0001–#0003 remain unsigned (see below). The OTS stamp over `proteus-bench-v1.0.2/BUNDLE_HASH.txt` remains a pending operator action; the signature's "when" is currently anchored by the v1.0/v1.0.1 stamps plus the signed `commit_date_tai`.

Superseded candidates (never signed): PROTEUS-002 / v1.0.1 (`03e27b6284405adb`, OTS-stamped, superseded per `proteus-bench-v1.0.2/DELTA_v1.0.2.md`); PROTEUS-001 / v1.0 (`a802d7e0f2e92d0b`, OTS-stamped, superseded per `DELTA_v1.0.1.md`). Both remain under `archive/`.

## #0004/#0005 collision note

`PROTEUS-002/003` and `CADUCEUS-004` (held pending five Category A tightenings and patent practitioner review) both claimed entry #0004 in preparation. **Resolved 2026-06-10:** Proteus (PROTEUS-003) signed first and holds #0004 on the authoritative chain. Caduceus becomes #0005 when its review completes, with `prev_ledger_hash` = `0217ae85…793be9` (the #0004 payload hash above).

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
root = Path("proteus-bench-v1.0.2")
skip = {"MANIFEST.json","BUNDLE_HASH.txt","BUNDLE_HASH.txt.ots","LEDGER_CANDIDATE.md"}
files = [p for p in sorted(root.rglob("*"))
         if p.is_file() and p.name not in skip and "__pycache__" not in str(p)]
print(hashlib.sha256("\n".join(
    f"{p.relative_to(root)}:{hashlib.sha256(p.read_bytes()).hexdigest()}"
    for p in files).encode()).hexdigest())
PY

# Verify the OpenTimestamps proof (v1.0.2 stamp pending operator action; superseded
# v1.0.1 stamp remains verifiable, after ~24h post-stamp for Bitcoin confirmation):
ots upgrade archive/proteus-bench-v1.0.1/BUNDLE_HASH.txt.ots
ots verify  archive/proteus-bench-v1.0.1/BUNDLE_HASH.txt.ots
```

Three independent confirmations: cryptographic signature (who), bundle hash (what), OpenTimestamps anchor (when). All three must hold for a chain entry to be authoritative.

## Why this file exists alongside the JSON

The signed JSON entries are machine-truth. This file is human-truth: at-a-glance chain state, decision context (the #0004/#0005 note), and verification examples. Future readers should treat this file as orientation and the JSON entries as ground.
