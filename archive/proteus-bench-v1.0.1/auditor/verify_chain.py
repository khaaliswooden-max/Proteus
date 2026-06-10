#!/usr/bin/env python3
"""Independent chain auditor — PROTEUS-Bench v1.0.

Implements:
  B1a  Chain integrity: recompute every hash, verify every Ed25519 signature,
       verify linkage (prev_hash) across the full state chain.
  B5   Provenance completeness + semantic non-degeneracy (>= 60% non-empty
       state diffs on turns flagged as adaptation events).
  F10  Canary isolation: no canary task_id appears in any consolidation trace.

Usage:
  verify_chain.py --db episode.sqlite --pubkey zil_release.pub [--check-canary-isolation canary.json --traces traces/]

Exit 0 = all checks pass. Non-zero = failure (codes below).
This script must remain solution-independent: it reads only the SQLite chain,
the public key, and (optionally) trace files. It imports nothing from the
solution repository.
"""
import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.hazmat.primitives import serialization
except ImportError:
    print("FATAL: python 'cryptography' package required", file=sys.stderr)
    sys.exit(9)

EXIT_OK = 0
EXIT_HASH = 1
EXIT_SIG = 2
EXIT_LINK = 3
EXIT_DEGENERATE = 4
EXIT_CANARY = 5


def row_hash(prev_hash: str, state_json: str, signals_json: str, ts: str) -> str:
    return hashlib.sha256((prev_hash + state_json + signals_json + ts).encode()).hexdigest()


def load_pubkey(path: str) -> Ed25519PublicKey:
    data = Path(path).read_bytes()
    return serialization.load_pem_public_key(data)


def audit_chain(db_path: str, pubkey_path: str) -> dict:
    pub = load_pubkey(pubkey_path)
    con = sqlite3.connect(db_path)
    rows = con.execute(
        "SELECT turn_id, ts, state_json, signals_json, prev_hash, hash, sig "
        "FROM state_chain ORDER BY turn_id ASC").fetchall()
    con.close()
    if not rows:
        return {"ok": False, "exit": EXIT_LINK, "reason": "empty chain"}

    prev = "GENESIS"
    n_adapt, n_nonempty = 0, 0
    last_state = None
    for (turn_id, ts, state_json, signals_json, prev_hash, h, sig) in rows:
        if prev_hash != prev:
            return {"ok": False, "exit": EXIT_LINK,
                    "reason": f"turn {turn_id}: linkage break (expected prev {prev[:12]}, got {prev_hash[:12]})"}
        expect = row_hash(prev_hash, state_json, signals_json, ts)
        if expect != h:
            return {"ok": False, "exit": EXIT_HASH,
                    "reason": f"turn {turn_id}: hash mismatch"}
        try:
            pub.verify(bytes.fromhex(sig), h.encode())
        except Exception:
            return {"ok": False, "exit": EXIT_SIG,
                    "reason": f"turn {turn_id}: signature invalid"}
        signals = json.loads(signals_json)
        if signals.get("adaptation_event", False):
            n_adapt += 1
            if last_state is not None and state_json != last_state:
                n_nonempty += 1
            elif last_state is None:
                n_nonempty += 1
        last_state = state_json
        prev = h

    degeneracy_ok = (n_adapt == 0) or (n_nonempty / n_adapt >= 0.60)
    if not degeneracy_ok:
        return {"ok": False, "exit": EXIT_DEGENERATE,
                "reason": f"non-degeneracy {n_nonempty}/{n_adapt} < 60%"}
    return {"ok": True, "exit": EXIT_OK, "turns": len(rows),
            "adaptation_events": n_adapt, "nonempty_diffs": n_nonempty}


def check_canary_isolation(canary_path: str, traces_dir: str) -> dict:
    canary = json.loads(Path(canary_path).read_text())
    ids = {t["task_id"] for t in canary["tasks"]}
    prompts = {t["prompt"][:60] for t in canary["tasks"]}
    hits = []
    for p in sorted(Path(traces_dir).rglob("*.json*")):
        text = p.read_text(errors="replace")
        for tid in ids:
            if tid in text:
                hits.append((str(p), tid))
        for snip in prompts:
            if snip in text:
                hits.append((str(p), f"prompt-snippet:{snip[:30]}..."))
    if hits:
        return {"ok": False, "exit": EXIT_CANARY, "hits": hits[:10],
                "reason": f"{len(hits)} canary leakage hit(s) in consolidation traces"}
    return {"ok": True, "exit": EXIT_OK, "files_scanned": len(list(Path(traces_dir).rglob('*.json*')))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--pubkey", required=True)
    ap.add_argument("--check-canary-isolation", dest="canary")
    ap.add_argument("--traces")
    args = ap.parse_args()

    result = audit_chain(args.db, args.pubkey)
    print(json.dumps({"chain_audit": result}, indent=1))
    if not result["ok"]:
        sys.exit(result["exit"])

    if args.canary:
        if not args.traces:
            print("FATAL: --traces required with --check-canary-isolation", file=sys.stderr)
            sys.exit(9)
        iso = check_canary_isolation(args.canary, args.traces)
        print(json.dumps({"canary_isolation": iso}, indent=1))
        if not iso["ok"]:
            sys.exit(iso["exit"])
    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
