#!/usr/bin/env python3
"""Proteus Loop B chain writer — Ed25519-signed, hash-chained state transitions.

Schema is byte-compatible with the committed auditor
(proteus-bench-v1.0/auditor/verify_chain.py):
  hash = sha256(prev_hash + state_json + signals_json + ts)
  sig  = Ed25519(hash-as-utf8), hex

Captures per-turn controller overhead (signal + controller + serialize +
sign + insert) for the B6 latency assertion.
"""
import hashlib
import json
import sqlite3
import time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization


class StateChain:
    def __init__(self, db_path: str, private_key: Ed25519PrivateKey):
        self.key = private_key
        self.con = sqlite3.connect(db_path)
        self.con.execute(
            "CREATE TABLE IF NOT EXISTS state_chain ("
            " turn_id INTEGER PRIMARY KEY, ts TEXT NOT NULL,"
            " state_json TEXT NOT NULL, signals_json TEXT NOT NULL,"
            " prev_hash TEXT NOT NULL, hash TEXT NOT NULL, sig TEXT NOT NULL)")
        row = self.con.execute(
            "SELECT hash FROM state_chain ORDER BY turn_id DESC LIMIT 1").fetchone()
        self.prev = row[0] if row else "GENESIS"
        self.turn = self.con.execute(
            "SELECT COALESCE(MAX(turn_id), -1) FROM state_chain").fetchone()[0] + 1
        self.latencies_ms: list[float] = []

    def append(self, state: dict, signals: dict, ts: str) -> str:
        t0 = time.perf_counter()
        sj = json.dumps(state, sort_keys=True)
        gj = json.dumps(signals, sort_keys=True)
        h = hashlib.sha256((self.prev + sj + gj + ts).encode()).hexdigest()
        sig = self.key.sign(h.encode()).hex()
        self.con.execute("INSERT INTO state_chain VALUES (?,?,?,?,?,?,?)",
                         (self.turn, ts, sj, gj, self.prev, h, sig))
        self.con.commit()
        self.prev = h
        self.turn += 1
        self.latencies_ms.append((time.perf_counter() - t0) * 1000.0)
        return h

    def latency_stats(self) -> dict:
        if not self.latencies_ms:
            return {}
        xs = sorted(self.latencies_ms)
        n = len(xs)
        return {"median_ms": xs[n // 2],
                "p95_ms": xs[min(int(n * 0.95), n - 1)],
                "max_ms": xs[-1], "n": n}

    def close(self):
        self.con.close()


def generate_test_keypair(pub_path: str):
    """TEST-ONLY ephemeral keypair for development runs. Zero provenance
    weight; measured benchmark runs sign with a key under Khaalis's custody."""
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo)
    with open(pub_path, "wb") as f:
        f.write(pub)
    return priv
