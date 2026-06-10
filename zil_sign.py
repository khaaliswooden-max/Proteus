#!/usr/bin/env python3
"""zil_sign.py — Aletheia ledger signing tool (Zuup Innovation Lab).

Commands
--------
  keygen   Generate an Ed25519 signing identity (operator-only; prompts for a
           passphrase twice). Run in ~/zil-keys, never inside a git repo.
  sign     Verify a bundle's manifest hash, construct an
           `aletheia-ledger-entry-v1` payload, canonicalize it (RFC 8785 JCS),
           sign it (operator-only; prompts for the passphrase), and write
           LEDGER_NNNN.json.
  verify   Verify a ledger entry against a public key. Prints VALID (exit 0)
           or INVALID with a reason (exit 1). Needs no private material.

Schema: aletheia-ledger-entry-v1
--------------------------------
The signed payload is a JSON object with exactly these fields:

  author                   str   document author
  commit_date_tai          str   ISO 8601 UTC with explicit Z, set at signing
  commit_methodology       str   e.g. "ZCS-6 Phase 4"
  document_id              str   e.g. "PROTEUS-002"
  document_revision        str   e.g. "A"
  document_title           str
  ledger_entry_number      int   position on the authoritative chain
  manifest_byte_count      int   total bytes of the hashed bundle files
  manifest_hash            str   sha256 over sorted "rel_path:sha256" lines
  manifest_hash_algorithm  str   "SHA-256"
  predecessor_documents    list  [{"document_id": ..., "version": ...}, ...]
  prev_ledger_hash         str   payload_sha256 of the previous entry, or
                                 "GENESIS" for the first entry on the chain
  prev_ledger_number       int   ledger_entry_number minus 1 (0 at genesis)
  schema_version           str   "aletheia-ledger-entry-v1"
  signing_algorithm        str   "Ed25519"
  signing_key_identifier   str   e.g. "visionblox-release-key-v1"

The signature is Ed25519 over the JCS-canonical UTF-8 bytes of the payload.
`prev_ledger_hash` is the SHA-256 of the previous entry's canonical payload
(independent of its signature), so forward chain linkage holds even before
historical entries are retro-signed.

The entry file on disk wraps the payload:

  {
    "schema_version": "aletheia-ledger-entry-v1",
    "payload": { ... },
    "payload_sha256": "<sha256 hex of canonical payload bytes>",
    "signature": {
      "algorithm": "Ed25519",
      "key_identifier": "<signing key id>",
      "public_key_fingerprint": "<first 16 hex of sha256 over the .pub file>",
      "signature_base64": "<base64>"
    }
  }
"""

import argparse
import base64
import getpass
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

DEFAULT_KEY_ID = "visionblox-release-key-v1"
DEFAULT_KEY_DIR = Path.home() / "zil-keys"
SCHEMA_VERSION = "aletheia-ledger-entry-v1"

# Files excluded from the bundle manifest because they describe or anchor the
# bundle rather than belong to it (same construction as VBX-ISPS LEDGER #0003).
SKIP_NAMES = {
    "MANIFEST.json",
    "BUNDLE_HASH.txt",
    "BUNDLE_HASH.txt.ots",
    "LEDGER_CANDIDATE.md",
    "LEDGER_0004_CANDIDATE.md",
}

PAYLOAD_FIELDS = [
    "author",
    "commit_date_tai",
    "commit_methodology",
    "document_id",
    "document_revision",
    "document_title",
    "ledger_entry_number",
    "manifest_byte_count",
    "manifest_hash",
    "manifest_hash_algorithm",
    "predecessor_documents",
    "prev_ledger_hash",
    "prev_ledger_number",
    "schema_version",
    "signing_algorithm",
    "signing_key_identifier",
]


# ---------------------------------------------------------------- bundle hash

def _bundle_files(root: Path) -> list:
    return [
        p
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.name not in SKIP_NAMES and "__pycache__" not in str(p)
    ]


def bundle_manifest_lines(root: Path) -> str:
    root = Path(root)
    return "\n".join(
        f"{p.relative_to(root)}:{hashlib.sha256(p.read_bytes()).hexdigest()}"
        for p in _bundle_files(root)
    )


def bundle_hash(root: Path) -> str:
    """SHA-256 over sorted `rel_path:sha256` lines of the bundle files."""
    return hashlib.sha256(bundle_manifest_lines(Path(root)).encode()).hexdigest()


def bundle_byte_count(root: Path) -> int:
    """Total bytes of the hashed bundle files (matches MANIFEST total_bytes)."""
    return sum(p.stat().st_size for p in _bundle_files(Path(root)))


# ------------------------------------------------------------- canonical JSON

def canonical_json(obj) -> bytes:
    """RFC 8785 (JCS) canonicalization for the ledger payload subset.

    The schema uses only objects, arrays, strings, and integers, for which
    JCS reduces to: lexicographically sorted keys, no whitespace, UTF-8.
    Floats are rejected rather than risk a non-canonical serialization.
    """

    def reject_floats(o):
        if isinstance(o, float):
            raise ValueError("floats are not permitted in ledger payloads")
        if isinstance(o, dict):
            for v in o.values():
                reject_floats(v)
        elif isinstance(o, list):
            for v in o:
                reject_floats(v)

    reject_floats(obj)
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def payload_sha256(payload: dict) -> str:
    return hashlib.sha256(canonical_json(payload)).hexdigest()


def pub_fingerprint(pub_path: Path) -> str:
    return hashlib.sha256(Path(pub_path).read_bytes()).hexdigest()[:16]


# -------------------------------------------------------------------- signing

def build_payload(
    *,
    bundle: Path,
    entry_number: int,
    prev_hash: str,
    doc_id: str,
    title: str,
    author: str,
    methodology: str,
    revision: str,
    predecessors: list,
    key_id: str,
    commit_date: str = None,
) -> dict:
    payload = {
        "author": author,
        "commit_date_tai": commit_date
        or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit_methodology": methodology,
        "document_id": doc_id,
        "document_revision": revision,
        "document_title": title,
        "ledger_entry_number": int(entry_number),
        "manifest_byte_count": bundle_byte_count(bundle),
        "manifest_hash": bundle_hash(bundle),
        "manifest_hash_algorithm": "SHA-256",
        "predecessor_documents": predecessors,
        "prev_ledger_hash": prev_hash,
        "prev_ledger_number": max(int(entry_number) - 1, 0),
        "schema_version": SCHEMA_VERSION,
        "signing_algorithm": "Ed25519",
        "signing_key_identifier": key_id,
    }
    assert sorted(payload) == sorted(PAYLOAD_FIELDS)
    return payload


def sign_payload(payload: dict, private_key: Ed25519PrivateKey) -> bytes:
    return private_key.sign(canonical_json(payload))


def make_entry(payload: dict, signature: bytes, key_id: str, fingerprint: str) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "payload": payload,
        "payload_sha256": payload_sha256(payload),
        "signature": {
            "algorithm": "Ed25519",
            "key_identifier": key_id,
            "public_key_fingerprint": fingerprint,
            "signature_base64": base64.b64encode(signature).decode("ascii"),
        },
    }


def verify_entry(entry: dict, public_key: Ed25519PublicKey) -> str:
    """Return 'VALID' or raise ValueError with the reason."""
    if entry.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unknown schema_version {entry.get('schema_version')!r}")
    payload = entry.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("missing payload")
    missing = [f for f in PAYLOAD_FIELDS if f not in payload]
    extra = [f for f in payload if f not in PAYLOAD_FIELDS]
    if missing or extra:
        raise ValueError(f"payload fields mismatch (missing={missing}, extra={extra})")
    recomputed = payload_sha256(payload)
    if recomputed != entry.get("payload_sha256"):
        raise ValueError(
            f"payload_sha256 mismatch: recorded {entry.get('payload_sha256')}, "
            f"recomputed {recomputed}"
        )
    sig = base64.b64decode(entry["signature"]["signature_base64"])
    try:
        public_key.verify(sig, canonical_json(payload))
    except Exception:
        raise ValueError("Ed25519 signature does not verify against this public key")
    return "VALID"


# ------------------------------------------------------------------- key I/O

def load_private_key(path: Path, passphrase: bytes) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(Path(path).read_bytes(), passphrase)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError(f"{path} is not an Ed25519 private key")
    return key


def load_public_key(path: Path) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(Path(path).read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError(f"{path} is not an Ed25519 public key")
    return key


def _inside_git_repo(path: Path) -> bool:
    return any((p / ".git").exists() for p in [path, *path.parents])


# ----------------------------------------------------------------------- CLI

def cmd_keygen(args):
    out_dir = Path(args.out_dir).expanduser()
    if _inside_git_repo(out_dir.resolve()):
        sys.exit(
            "REFUSING keygen inside a git repository. Run from ~/zil-keys. "
            "Private keys must never be where a `git add` can reach them."
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    pem_path = out_dir / f"{args.key_id}.pem"
    pub_path = out_dir / f"{args.key_id}.pub"
    if pem_path.exists():
        sys.exit(f"REFUSING to overwrite existing key {pem_path}. "
                 f"Rotate to a new identifier instead (e.g. -v2).")
    p1 = getpass.getpass("Passphrase for new signing key: ")
    p2 = getpass.getpass("Repeat passphrase: ")
    if p1 != p2:
        sys.exit("Passphrases do not match; no key written.")
    if len(p1) < 8:
        sys.exit("Passphrase must be at least 8 characters; no key written.")
    key = Ed25519PrivateKey.generate()
    pem_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.BestAvailableEncryption(p1.encode()),
        )
    )
    pem_path.chmod(0o600)
    pub_path.write_bytes(
        key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    print(f"PRIVATE key (keep offline, never commit): {pem_path}")
    print(f"PUBLIC  key (copy into repo keys/):       {pub_path}")
    print(f"Fingerprint (first 16 hex of sha256 over .pub): {pub_fingerprint(pub_path)}")


def cmd_sign(args):
    bundle = Path(args.bundle)
    if not bundle.is_dir():
        sys.exit(f"Bundle directory not found: {bundle}")
    actual = bundle_hash(bundle)
    if actual != args.expected_hash:
        sys.exit(
            "MANIFEST HASH MISMATCH — STOPPING, nothing signed.\n"
            f"  expected: {args.expected_hash}\n"
            f"  actual:   {actual}\n"
            "Investigate (line endings? modified file?) before retrying."
        )
    try:
        predecessors = json.loads(args.predecessors)
        assert isinstance(predecessors, list)
    except Exception:
        sys.exit("--predecessors must be a JSON list")
    payload = build_payload(
        bundle=bundle,
        entry_number=args.entry_number,
        prev_hash=args.prev_hash,
        doc_id=args.doc_id,
        title=args.title,
        author=args.author,
        methodology=args.methodology,
        revision=args.revision,
        predecessors=predecessors,
        key_id=args.key_id,
    )
    key_path = Path(args.key).expanduser()
    pub_path = key_path.with_suffix(".pub")
    if not key_path.exists():
        sys.exit(f"Private key not found: {key_path} (run keygen first)")
    passphrase = getpass.getpass(f"Passphrase for {key_path.name}: ")
    private_key = load_private_key(key_path, passphrase.encode())
    signature = sign_payload(payload, private_key)
    fingerprint = pub_fingerprint(pub_path) if pub_path.exists() else ""
    entry = make_entry(payload, signature, args.key_id, fingerprint)
    # Self-check before writing: the entry must verify against the public key.
    verify_entry(entry, private_key.public_key())
    out = Path(args.out) if args.out else Path(f"LEDGER_{int(args.entry_number):04d}.json")
    out.write_text(json.dumps(entry, indent=1, ensure_ascii=False) + "\n")
    print(f"Wrote {out}")
    print(f"manifest_hash:       {payload['manifest_hash']}")
    print(f"manifest_byte_count: {payload['manifest_byte_count']}")
    print(f"payload_sha256:      {entry['payload_sha256']}")
    print("(the payload_sha256 above is the prev_ledger_hash for the NEXT entry)")


def cmd_verify(args):
    entry_path = Path(args.entry)
    entry = json.loads(entry_path.read_text())
    key_id = entry.get("signature", {}).get("key_identifier", DEFAULT_KEY_ID)
    if args.pubkey:
        candidates = [Path(args.pubkey).expanduser()]
    else:
        candidates = [
            entry_path.resolve().parent / "keys" / f"{key_id}.pub",
            Path("keys") / f"{key_id}.pub",
            DEFAULT_KEY_DIR / f"{key_id}.pub",
        ]
    pub_path = next((p for p in candidates if p.exists()), None)
    if pub_path is None:
        sys.exit(
            f"Public key {key_id}.pub not found (looked in: "
            + ", ".join(str(p) for p in candidates)
            + "). Pass --pubkey explicitly."
        )
    try:
        result = verify_entry(entry, load_public_key(pub_path))
    except ValueError as e:
        print(f"INVALID: {e}")
        sys.exit(1)
    print(result)
    print(f"verified against {pub_path} (fingerprint {pub_fingerprint(pub_path)})")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    kg = sub.add_parser("keygen", help="generate Ed25519 signing identity (operator-only)")
    kg.add_argument("--key-id", default=DEFAULT_KEY_ID)
    kg.add_argument("--out-dir", default=".", help="directory for the keypair (default: cwd)")
    kg.set_defaults(func=cmd_keygen)

    sg = sub.add_parser("sign", help="sign a bundle into a ledger entry (operator-only)")
    sg.add_argument("--bundle", required=True, help="path to the bundle directory")
    sg.add_argument("--expected-hash", required=True, help="manifest hash the bundle must match")
    sg.add_argument("--entry-number", required=True, type=int)
    sg.add_argument("--prev-hash", required=True,
                    help="payload_sha256 of the previous entry, or GENESIS")
    sg.add_argument("--doc-id", required=True)
    sg.add_argument("--title", required=True)
    sg.add_argument("--author", default="A. Khaalis Wooden, Sr.")
    sg.add_argument("--methodology", default="ZCS-6 Phase 4")
    sg.add_argument("--revision", default="A")
    sg.add_argument("--predecessors", default="[]",
                    help='JSON list, e.g. \'[{"document_id":"X","version":"y"}]\'')
    sg.add_argument("--key", default=str(DEFAULT_KEY_DIR / f"{DEFAULT_KEY_ID}.pem"))
    sg.add_argument("--key-id", default=DEFAULT_KEY_ID)
    sg.add_argument("--out", default=None, help="output path (default LEDGER_NNNN.json)")
    sg.set_defaults(func=cmd_sign)

    vf = sub.add_parser("verify", help="verify a ledger entry against the public key")
    vf.add_argument("--entry", required=True)
    vf.add_argument("--pubkey", default=None)
    vf.set_defaults(func=cmd_verify)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
