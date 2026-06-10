#!/usr/bin/env python3
"""zil_sign.py v0.2 — Aletheia ledger signing ceremony (run LOCALLY, never in a chat/cloud session).

Requires: pip install cryptography

Usage:
  1. One-time key ceremony (creates visionblox-release-key-v1):
       python3 zil_sign.py keygen

  2. Sign a benchmark bundle (run from the directory CONTAINING the bundle dir):
       python3 zil_sign.py sign \
           --bundle proteus-bench-v1.0.2 \
           --expected-hash 3d14ac4b77deede20daae1b319bb5c370b71db83c58c693587651d9cf4856e58 \
           --entry-number 4 \
           --prev-hash <SHA256 of previous ledger entry payload, or GENESIS> \
           --doc-id PROTEUS-003 \
           --title "PROTEUS-Bench v1.0.2 — Online State Adaptation Benchmark (Sixth Road Candidate)"

  3. Anyone verifies with only the .pub file:
       python3 zil_sign.py verify --entry LEDGER_0004.json
     (looks for the .pub in . and keys/; override with --pubkey)

Custody rules:
  - visionblox-release-key-v1.pem (PRIVATE) stays on this machine + one offline backup.
    Never email it, never upload it, never paste it anywhere.
  - visionblox-release-key-v1.pub (PUBLIC) gets published (zandbox repo) so third
    parties can verify your chain.

v0.2 (see DELTA_zil_sign_v0.2.md): bundle_hash now sorts POSIX-style relative
path strings (byte order) instead of Path objects, fixing two cross-platform
hash divergences on Windows (backslash separators; case-folded Path sorting).
"""
import argparse
import datetime
import getpass
import hashlib
import json
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey)
from cryptography.hazmat.primitives import serialization

PRIV = Path("visionblox-release-key-v1.pem")
PUB = Path("visionblox-release-key-v1.pub")


def canonical(payload: dict) -> bytes:
    """Deterministic canonical JSON: sorted keys, minimal separators, UTF-8.
    (Practical JCS profile — sufficient for str/int payloads like ours.)"""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def keygen():
    if PRIV.exists():
        sys.exit(f"REFUSING: {PRIV} already exists. Key rotation = new -v2 identifier, not overwrite.")
    pw = getpass.getpass("Choose a passphrase for the private key: ").encode()
    pw2 = getpass.getpass("Repeat passphrase: ").encode()
    if pw != pw2 or not pw:
        sys.exit("Passphrase mismatch or empty. Aborted.")
    priv = Ed25519PrivateKey.generate()
    PRIV.write_bytes(priv.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(pw)))
    PRIV.chmod(0o600)
    PUB.write_bytes(priv.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    print(f"Created {PRIV} (KEEP PRIVATE, back up offline) and {PUB} (publish this).")
    print("Public key fingerprint:",
          hashlib.sha256(PUB.read_bytes()).hexdigest()[:16])


def bundle_hash(bundle_dir: Path) -> tuple[str, int, int]:
    """Recompute the Merkle-style manifest hash, independently of MANIFEST.json.

    The canonical construction sorts POSIX-style relative path STRINGS in byte
    order. Sorting Path objects is platform-dependent (case-folded on Windows)
    and str(Path) uses backslashes there — both diverge from the committed
    hashes (v0.1 bugs F-S1/F-S2)."""
    skip = {"MANIFEST.json", "BUNDLE_HASH.txt", "BUNDLE_HASH.txt.ots", "LEDGER_CANDIDATE.md"}
    rel = sorted(p.relative_to(bundle_dir).as_posix()
                 for p in bundle_dir.rglob("*")
                 if p.is_file() and p.name not in skip and "__pycache__" not in p.parts)
    lines = "\n".join(
        f"{r}:{hashlib.sha256((bundle_dir / r).read_bytes()).hexdigest()}" for r in rel)
    return (hashlib.sha256(lines.encode()).hexdigest(), len(rel),
            sum((bundle_dir / r).stat().st_size for r in rel))


def sign(args):
    if not PRIV.exists():
        sys.exit(f"{PRIV} not found. Run 'keygen' first.")
    bdir = Path(args.bundle)
    mh, n, total = bundle_hash(bdir)
    print(f"Recomputed manifest hash: {mh}  ({n} files, {total} bytes)")
    if mh != args.expected_hash:
        sys.exit("STOP: hash mismatch vs expected. Investigate (likely line-ending "
                 "normalization from git/editor) before signing ANYTHING.")
    print("Hash verified against expected value.")

    pw = getpass.getpass("Private key passphrase: ").encode()
    priv = serialization.load_pem_private_key(PRIV.read_bytes(), password=pw)

    payload = {
        "author": "A. Khaalis Wooden, Sr.",
        "commit_date_tai": datetime.datetime.now(datetime.timezone.utc)
                            .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit_methodology": "ZCS-6 Phase 4",
        "document_id": args.doc_id,
        "document_revision": "A",
        "document_title": args.title,
        "ledger_entry_number": args.entry_number,
        "manifest_byte_count": total,
        "manifest_hash": mh,
        "manifest_hash_algorithm": "SHA-256",
        "prev_ledger_hash": args.prev_hash,
        "prev_ledger_number": args.entry_number - 1,
        "schema_version": "aletheia-ledger-entry-v1",
        "signing_algorithm": "Ed25519",
        "signing_key_identifier": "visionblox-release-key-v1",
    }
    cbytes = canonical(payload)
    signature = priv.sign(cbytes).hex()
    entry = {"payload": payload,
             "payload_sha256": hashlib.sha256(cbytes).hexdigest(),
             "signature_ed25519_hex": signature}
    out = Path(f"LEDGER_{args.entry_number:04d}.json")
    out.write_text(json.dumps(entry, indent=1, sort_keys=True))
    print(f"\nSIGNED. Wrote {out}")
    print(f"This entry's hash (becomes the NEXT entry's prev_ledger_hash):")
    print(f"  {entry['payload_sha256']}")
    print("Next: commit the entry + the bundle + the .pub key to the zandbox repo.")


def find_pubkey(explicit) -> Path:
    if explicit:
        return Path(explicit)
    here = Path(__file__).resolve().parent
    for cand in (PUB, Path("keys") / PUB.name, here / "keys" / PUB.name):
        if cand.exists():
            return cand
    sys.exit(f"{PUB.name} not found in . or keys/. Pass --pubkey.")


def verify(args):
    pubpath = find_pubkey(args.pubkey)
    entry = json.loads(Path(args.entry).read_text())
    pub = serialization.load_pem_public_key(pubpath.read_bytes())
    cbytes = canonical(entry["payload"])
    assert hashlib.sha256(cbytes).hexdigest() == entry["payload_sha256"], "payload hash mismatch"
    pub.verify(bytes.fromhex(entry["signature_ed25519_hex"]), cbytes)
    print("VALID: signature verifies against", pubpath)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("keygen")
    s = sub.add_parser("sign")
    s.add_argument("--bundle", required=True)
    s.add_argument("--expected-hash", required=True)
    s.add_argument("--entry-number", type=int, required=True)
    s.add_argument("--prev-hash", required=True)
    s.add_argument("--doc-id", required=True)
    s.add_argument("--title", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--entry", required=True)
    v.add_argument("--pubkey")
    a = ap.parse_args()
    {"keygen": lambda: keygen(), "sign": lambda: sign(a),
     "verify": lambda: verify(a)}[a.cmd]()
