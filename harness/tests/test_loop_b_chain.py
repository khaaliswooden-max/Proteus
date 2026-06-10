"""Loop B chain — robustness, replay determinism, and tamper detection.

Tests in this module bind the chain writer (`loop_a/chain.py`) to the
committed auditor (`proteus-bench-v1.0.2/auditor/verify_chain.py`).

Coverage map (cf. docs/LOOP_B_FRAGILITY_AUDIT.md):

  - §1.1  Canonical JSON pre-image — sort_keys invariance, key-order
          independence, nested dicts, ASCII-escaping.
  - §1.3  Genesis sentinel pin.
  - §2    KV-cache fragility surfaces — chain hash is independent of
          *how* the prompt was served (cache vs re-eval), depending only
          on (state, signals, ts) at append time.
  - §3    B1b replay determinism — Hypothesis property tests over
          random episode prefixes, including chain reopen and resume.
  - §4    B1a tamper detection — parametrized mutation × auditor exit.
  - §5    C5 degeneracy regression — signed no-op adaptation events
          must trip EXIT_DEGENERATE.

The auditor module is imported by path (the directory contains dots and
dashes, blocking normal `import`). The chain module is imported from
`loop_a/` via sys.path injection. Both are imported *as committed*.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import sqlite3
import sys
import tempfile

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "loop_a"))

from chain import StateChain, generate_test_keypair  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import (  # noqa: E402
    Ed25519PrivateKey,
)


def _load_auditor():
    path = REPO_ROOT / "proteus-bench-v1.0.2" / "auditor" / "verify_chain.py"
    spec = importlib.util.spec_from_file_location("verify_chain", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


VC = _load_auditor()

# Hypothesis ergonomics: SQLite + ed25519 sign are not free; cap examples
# globally so a clean run is bounded, override for extended audits.
HYPOTHESIS_MAX = int(os.environ.get("PROTEUS_HYPOTHESIS_MAX", "200"))
property_settings = settings(
    max_examples=HYPOTHESIS_MAX,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)


# ---------------------------------------------------------------------------
# Strategies — shapes that match what Loop A actually puts in the chain.
# ---------------------------------------------------------------------------

_safe_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),  # exclude surrogates
    max_size=24,
)

_leaf = st.one_of(
    st.booleans(),
    st.none(),
    st.integers(min_value=-(2 ** 31), max_value=2 ** 31),
    st.floats(allow_nan=False, allow_infinity=False, width=32),
    _safe_text,
)

_state_dict = st.dictionaries(
    keys=st.sampled_from(["mode", "actuators", "model", "episode_seed", "phase"]),
    values=st.one_of(_leaf, st.dictionaries(keys=_safe_text, values=_leaf, max_size=4)),
    max_size=5,
)

_signals_dict = st.dictionaries(
    keys=st.sampled_from(
        ["c_t", "skill_t", "gap", "k", "g", "s", "correct", "level",
         "mean_H", "adaptation_event"]
    ),
    values=_leaf,
    max_size=8,
)

# ISO-ish timestamps as opaque strings — the chain treats `ts` as raw bytes.
_ts = st.from_regex(
    r"\A20[2-3][0-9]-[01][0-9]-[0-3][0-9]T[0-2][0-9]:[0-5][0-9]:[0-5][0-9]\.[0-9]{6}Z\Z",
    fullmatch=True,
)

_triple = st.tuples(_state_dict, _signals_dict, _ts)
_episode = st.lists(_triple, min_size=1, max_size=12)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def keypair(tmp_path):
    pub = tmp_path / "pub.pem"
    priv = generate_test_keypair(str(pub))
    return priv, str(pub)


def _scratch_dir():
    """Per-example scratch directory.

    Pytest's `tmp_path` is function-scoped, so Hypothesis reuses one
    directory across all examples in a single test — the second example
    would otherwise resume a chain left behind by the first. Each
    property-test example builds its DB under a fresh mkdtemp so chains
    start from `GENESIS` every time.
    """
    return pathlib.Path(tempfile.mkdtemp(prefix="proteus_loop_b_"))


@pytest.fixture
def fresh_chain(tmp_path, keypair):
    priv, pub_path = keypair
    db = tmp_path / "chain.sqlite"
    chain = StateChain(str(db), priv)
    yield chain, str(db), pub_path
    chain.close()


def _build_chain(db_path: str, priv: Ed25519PrivateKey, episode):
    """Append an episode (list of (state, signals, ts) triples) to a fresh DB.

    Returns the ordered list of recorded turn hashes.
    """
    chain = StateChain(db_path, priv)
    hashes = [chain.append(state, signals, ts) for (state, signals, ts) in episode]
    chain.close()
    return hashes


def _audit_b1a_only(db_path: str, pub_path: str) -> dict:
    """B1a-only audit: hash recomputation, signature verification, linkage.

    This isolates B1a from B5 (semantic non-degeneracy) so the
    replay-determinism property tests can exercise arbitrary
    `adaptation_event` flags without colliding with the degeneracy gate.
    The reused `row_hash` and `load_pubkey` are the committed auditor's,
    so the integrity contract under test is identical to B1a in
    `verify_chain.audit_chain`.
    """
    pub = VC.load_pubkey(pub_path)
    con = sqlite3.connect(db_path)
    rows = con.execute(
        "SELECT turn_id, ts, state_json, signals_json, prev_hash, hash, sig "
        "FROM state_chain ORDER BY turn_id ASC"
    ).fetchall()
    con.close()
    if not rows:
        return {"ok": False, "exit": VC.EXIT_LINK, "reason": "empty chain"}
    prev = "GENESIS"
    for (turn_id, ts, state_json, signals_json, prev_hash, h, sig) in rows:
        if prev_hash != prev:
            return {"ok": False, "exit": VC.EXIT_LINK,
                    "reason": f"turn {turn_id}: linkage break"}
        if VC.row_hash(prev_hash, state_json, signals_json, ts) != h:
            return {"ok": False, "exit": VC.EXIT_HASH,
                    "reason": f"turn {turn_id}: hash mismatch"}
        try:
            pub.verify(bytes.fromhex(sig), h.encode())
        except Exception:
            return {"ok": False, "exit": VC.EXIT_SIG,
                    "reason": f"turn {turn_id}: bad sig"}
        prev = h
    return {"ok": True, "exit": VC.EXIT_OK, "turns": len(rows)}


# ---------------------------------------------------------------------------
# §1.1 — Canonical JSON pre-image: sort_keys invariance
# ---------------------------------------------------------------------------

@given(
    items=st.lists(
        st.tuples(_safe_text, _leaf),
        min_size=1, max_size=8, unique_by=lambda kv: kv[0]
    ),
)
@property_settings
def test_state_hash_invariant_under_key_insertion_order(keypair, items):
    """Two dicts that differ only in insertion order MUST produce the same hash."""
    priv, _ = keypair
    forward = dict(items)
    reverse = dict(reversed(items))
    ts = "2026-06-10T00:00:00.000000Z"
    td = _scratch_dir()
    h1 = _build_chain(str(td / "a.sqlite"), priv, [(forward, {"x": 1}, ts)])
    h2 = _build_chain(str(td / "b.sqlite"), priv, [(reverse, {"x": 1}, ts)])
    assert h1 == h2


# ---------------------------------------------------------------------------
# §1.3 — Genesis sentinel is the literal byte string "GENESIS".
# ---------------------------------------------------------------------------

def test_genesis_sentinel_is_literal_bytes(fresh_chain):
    chain, db, _ = fresh_chain
    ts = "2026-06-10T00:00:00.000000Z"
    state, signals = {"mode": "x"}, {"k": 0}
    recorded = chain.append(state, signals, ts)
    expect = hashlib.sha256(
        ("GENESIS"
         + json.dumps(state, sort_keys=True)
         + json.dumps(signals, sort_keys=True)
         + ts).encode()
    ).hexdigest()
    assert recorded == expect


# ---------------------------------------------------------------------------
# §3 — B1b replay determinism: random episode prefixes round-trip cleanly.
# ---------------------------------------------------------------------------

@given(episode=_episode)
@property_settings
def test_replay_is_byte_identical(keypair, episode):
    """B1b — two fresh builds of the same episode produce byte-identical
    hashes, and pass B1a (integrity + sig + linkage). B5 degeneracy is
    out of scope here — `adaptation_event` flags in the generated signals
    are arbitrary, and the gated test below covers that branch."""
    priv, pub = keypair
    td = _scratch_dir()
    h1 = _build_chain(str(td / "first.sqlite"), priv, episode)
    h2 = _build_chain(str(td / "second.sqlite"), priv, episode)
    assert h1 == h2
    assert _audit_b1a_only(str(td / "second.sqlite"), pub)["ok"]


@given(episode=_episode)
@property_settings
def test_reopen_resume_continues_chain(keypair, episode):
    """Closing the chain mid-episode and reopening it must produce a chain
    byte-identical to one that never closed. This is the on-disk replay
    invariant Loop A relies on for crash recovery."""
    if len(episode) < 2:
        return
    priv, pub = keypair
    split = len(episode) // 2
    td = _scratch_dir()

    db_a = td / "monolithic.sqlite"
    hashes_a = _build_chain(str(db_a), priv, episode)

    db_b = td / "split.sqlite"
    head = StateChain(str(db_b), priv)
    hashes_b = [head.append(s, g, t) for (s, g, t) in episode[:split]]
    head.close()
    tail = StateChain(str(db_b), priv)
    hashes_b += [tail.append(s, g, t) for (s, g, t) in episode[split:]]
    tail.close()

    assert hashes_a == hashes_b
    assert _audit_b1a_only(str(db_b), pub)["ok"]


@given(episode=_episode)
@property_settings
def test_chain_is_prefix_invariant(keypair, episode):
    """Appending more turns must not retroactively alter the hashes of
    earlier turns — the chain is a true append-only Merkle prefix."""
    if len(episode) < 2:
        return
    priv, pub = keypair
    split = len(episode) // 2
    td = _scratch_dir()
    full_hashes = _build_chain(str(td / "full.sqlite"), priv, episode)
    prefix_hashes = _build_chain(str(td / "prefix.sqlite"), priv, episode[:split])
    assert full_hashes[:split] == prefix_hashes
    # The prefix chain must also stand on its own under B1a.
    assert _audit_b1a_only(str(td / "prefix.sqlite"), pub)["ok"]


# ---------------------------------------------------------------------------
# §2 — KV-cache fragility surface: chain hash depends only on the chain
# inputs at append time, not on the path that produced the prompt.
# ---------------------------------------------------------------------------

def test_chain_hash_independent_of_latency_path(tmp_path, keypair):
    """Two appends with identical (state, signals, ts) but very different
    in-process timings (simulating cache hit vs cold re-eval) must produce
    byte-identical chain hashes. Latency is measured but not chained."""
    import time
    priv, _ = keypair
    triples = [({"mode": "x"}, {"k": 0}, "2026-06-10T00:00:00.000000Z"),
               ({"mode": "y"}, {"k": 1}, "2026-06-10T00:00:01.000000Z")]
    h_fast = _build_chain(str(tmp_path / "fast.sqlite"), priv, triples)
    # Slow path: inject delays between appends. Latency_ms differs; hashes don't.
    db_slow = tmp_path / "slow.sqlite"
    chain = StateChain(str(db_slow), priv)
    h_slow = []
    for s, g, t in triples:
        time.sleep(0.005)
        h_slow.append(chain.append(s, g, t))
    fast_stats_lat = chain.latencies_ms[:]
    chain.close()
    assert h_fast == h_slow
    # Latency was actually different — guard against the test being a tautology.
    assert max(fast_stats_lat) > 0.0


# ---------------------------------------------------------------------------
# §4 — Tamper detection: every chain field × auditor exit code.
# ---------------------------------------------------------------------------

def _populated_chain(tmp_path, priv, n=5):
    triples = [
        ({"mode": "x", "i": i}, {"k": i, "adaptation_event": True},
         f"2026-06-10T00:00:0{i}.000000Z")
        for i in range(n)
    ]
    db = tmp_path / "tampered.sqlite"
    # We want non-degenerate state diffs so EXIT_DEGENERATE doesn't fire
    # for the EXIT_HASH/EXIT_SIG/EXIT_LINK tests.
    _build_chain(str(db), priv, triples)
    return str(db)


@pytest.mark.parametrize("column,expected_exit", [
    ("state_json", VC.EXIT_HASH),
    ("signals_json", VC.EXIT_HASH),
    ("ts", VC.EXIT_HASH),
    ("hash", VC.EXIT_HASH),
    ("sig", VC.EXIT_SIG),
    ("prev_hash", VC.EXIT_LINK),
])
def test_tamper_any_column_breaks_audit(tmp_path, keypair, column, expected_exit):
    priv, pub = keypair
    db = _populated_chain(tmp_path, priv)

    con = sqlite3.connect(db)
    # Mutate the row at turn 2 — interior so linkage propagates.
    target_turn = 2
    if column in ("state_json", "signals_json", "ts"):
        original = con.execute(
            f"SELECT {column} FROM state_chain WHERE turn_id=?", (target_turn,)
        ).fetchone()[0]
        # Append a benign extra character — guaranteed payload change.
        con.execute(
            f"UPDATE state_chain SET {column}=? WHERE turn_id=?",
            (original + " ", target_turn),
        )
    elif column == "hash":
        # Flip one hex char — must still be 64-char hex so the auditor
        # doesn't reject it for non-cryptographic reasons.
        original = con.execute(
            "SELECT hash FROM state_chain WHERE turn_id=?", (target_turn,)
        ).fetchone()[0]
        flipped = ("f" if original[0] != "f" else "0") + original[1:]
        con.execute("UPDATE state_chain SET hash=? WHERE turn_id=?",
                    (flipped, target_turn))
    elif column == "sig":
        original = con.execute(
            "SELECT sig FROM state_chain WHERE turn_id=?", (target_turn,)
        ).fetchone()[0]
        # Flip the last byte (still valid hex, but cryptographically wrong).
        flipped = original[:-2] + ("ff" if original[-2:] != "ff" else "00")
        con.execute("UPDATE state_chain SET sig=? WHERE turn_id=?",
                    (flipped, target_turn))
    elif column == "prev_hash":
        con.execute(
            "UPDATE state_chain SET prev_hash=? WHERE turn_id=?",
            ("0" * 64, target_turn),
        )
    con.commit()
    con.close()

    result = VC.audit_chain(db, pub)
    assert not result["ok"]
    assert result["exit"] == expected_exit, result


def test_row_deletion_breaks_linkage(tmp_path, keypair):
    priv, pub = keypair
    db = _populated_chain(tmp_path, priv)
    con = sqlite3.connect(db)
    con.execute("DELETE FROM state_chain WHERE turn_id=2")
    con.commit()
    con.close()
    result = VC.audit_chain(db, pub)
    assert not result["ok"]
    assert result["exit"] == VC.EXIT_LINK


def test_empty_chain_rejected(tmp_path, keypair):
    priv, pub = keypair
    db = tmp_path / "empty.sqlite"
    chain = StateChain(str(db), priv)
    chain.close()  # creates schema, inserts nothing
    result = VC.audit_chain(str(db), pub)
    assert not result["ok"]
    assert result["exit"] == VC.EXIT_LINK


def test_wrong_pubkey_rejected(tmp_path, keypair):
    priv, _ = keypair
    db = _populated_chain(tmp_path, priv)
    wrong_pub = tmp_path / "wrong.pem"
    generate_test_keypair(str(wrong_pub))  # different keypair
    result = VC.audit_chain(db, str(wrong_pub))
    assert not result["ok"]
    assert result["exit"] == VC.EXIT_SIG


# ---------------------------------------------------------------------------
# §5 — C5 degeneracy regression: signed no-op adaptation events fail audit.
# ---------------------------------------------------------------------------

def test_signed_no_op_adaptation_trips_degeneracy(tmp_path, keypair):
    """Adaptation events that don't change `state_json` are exactly the
    C5 degeneracy the auditor caught on 2026-06-09. Regression-test it."""
    priv, pub = keypair
    db = tmp_path / "degen.sqlite"
    constant_state = {"mode": "x", "actuators": {"k": 0, "g": 0, "s": 0}}
    triples = [
        (constant_state, {"adaptation_event": True, "k": 0},
         f"2026-06-10T00:00:0{i}.000000Z")
        for i in range(5)
    ]
    _build_chain(str(db), priv, triples)
    result = VC.audit_chain(str(db), pub)
    assert not result["ok"]
    assert result["exit"] == VC.EXIT_DEGENERATE


def test_genuine_state_diffs_pass_audit(tmp_path, keypair):
    """The mirror of the above: when adaptation events DO produce state
    diffs, the audit passes."""
    priv, pub = keypair
    db = tmp_path / "ok.sqlite"
    triples = [
        ({"mode": "x", "actuators": {"k": i, "g": 0, "s": 0}},
         {"adaptation_event": True, "k": i},
         f"2026-06-10T00:00:0{i}.000000Z")
        for i in range(5)
    ]
    _build_chain(str(db), priv, triples)
    result = VC.audit_chain(str(db), pub)
    assert result["ok"], result
    assert result["adaptation_events"] == 5
    assert result["nonempty_diffs"] == 5


# ---------------------------------------------------------------------------
# §3 (extended) — Random walks across the actuator state space.
# ---------------------------------------------------------------------------

@given(
    walk=st.lists(
        st.tuples(
            st.integers(min_value=0, max_value=8),   # k
            st.integers(min_value=0, max_value=2),   # g
            st.integers(min_value=0, max_value=3),   # s
            st.booleans(),                            # adaptation_event flag
        ),
        min_size=1, max_size=20,
    ),
)
@property_settings
def test_actuator_state_walk_chain_replays(keypair, walk):
    """Random walks through the (k, g, s) actuator product space, with
    arbitrary adaptation_event flags, must produce chains that the
    auditor accepts on B1a (hash/sig/linkage) — degeneracy is judged
    only on the subset of walks that include genuine state changes, so
    the assertion is conditional."""
    priv, pub = keypair
    triples = []
    last_state_payload = None
    n_adapt = 0
    n_nonempty = 0
    for i, (k, g, s, adapt) in enumerate(walk):
        state = {"mode": "walk", "actuators": {"k": k, "g": g, "s": s}}
        signals = {"k": k, "g": g, "s": s, "adaptation_event": adapt}
        ts = f"2026-06-10T00:00:{i:02d}.000000Z"
        triples.append((state, signals, ts))
        payload = json.dumps(state, sort_keys=True)
        if adapt:
            n_adapt += 1
            if last_state_payload is None or payload != last_state_payload:
                n_nonempty += 1
        last_state_payload = payload

    db = _scratch_dir() / "walk.sqlite"
    _build_chain(str(db), priv, triples)
    result = VC.audit_chain(str(db), pub)

    if n_adapt == 0 or n_nonempty / n_adapt >= 0.60:
        assert result["ok"], result
    else:
        assert not result["ok"]
        assert result["exit"] == VC.EXIT_DEGENERATE
