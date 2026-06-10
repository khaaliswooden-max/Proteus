# Loop B fragility audit (v0.3)

Scope: the signed-state chain implemented in `loop_a/chain.py` and the
committed auditor at `proteus-bench-v1.0.2/auditor/verify_chain.py`. This
document enumerates the **prefix invariants** that B1a (chain integrity)
and B1b (replay determinism) rely on, and the failure modes the property
tests in `harness/tests/test_loop_b_chain.py` actively probe.

The audit is solution-side. It does not modify the auditor, which is
frozen by `BUNDLE_HASH.txt` and OTS-stamped — solution-side checks bind
us to the auditor's pre-image without renegotiating it.

## 1. Hash pre-image (the invariant the chain rests on)

For every turn the chain computes:

```
h = sha256( prev_hash ‖ state_json ‖ signals_json ‖ ts ).hexdigest()
sig = Ed25519.sign(h.encode("utf-8"))
```

Concatenation is naïve string-append (no length prefix, no separator).
Determinism therefore requires that **each of the four components is
exactly reproducible byte-for-byte** at audit time. The auditor
recomputes `h` from `(prev_hash, state_json, signals_json, ts)` as stored
in SQLite — so as long as the stored strings round-trip, hashes match.

### 1.1 `state_json` and `signals_json`

Both serialized via `json.dumps(x, sort_keys=True)`. This pins:

- **Key order**: independent of dict insertion order (sorted ASCII).
- **Default separators**: `", "` and `": "`. Any change to `separators=` would
  fork the chain.
- **`ensure_ascii=True` (default)**: non-ASCII characters are `\uXXXX`-
  escaped, so the resulting `state_json` byte sequence is pure ASCII and
  invariant under any UTF-8-vs-Latin-1 re-encoding upstream.
- **Float formatting**: Python's `repr` rules apply. Property tests pin
  this by round-tripping arbitrary float-bearing signal dicts.

**Fragility surfaces tested:** key-order independence; nested-dict
canonicalization; non-ASCII-safe payloads; bool/None/int/float mix;
non-`str` keys are rejected (TypeError surfaces at append time, not at
audit time — fail-loud).

### 1.2 `ts`

A free-form caller-supplied string. The chain does not normalize it; the
auditor does not parse it. **It is therefore a raw chain input.** Two
appends with the same `(state, signals)` but different `ts` produce
different hashes; this is by design (turns are not assumed monotonic in
real time, only in `turn_id`).

### 1.3 `prev_hash`

- Genesis sentinel is the literal string `"GENESIS"` (7 bytes). The
  auditor hard-codes the same sentinel; any drift forks the chain.
- After turn 0, `prev_hash` is the hex digest of the previous turn — 64
  lowercase ASCII characters. Property tests assert this.

### 1.4 Signature

`Ed25519.sign(h.encode("utf-8"))` over the 64-character hex digest. The
signed payload is therefore deterministic in `h`; Ed25519 itself is
deterministic. The keypair is the only externality.

## 2. KV-cache reuse — when prefix reuse is and is not safe

The committed Loop A live runner (`loop_a/run_live.py`) does **not** use
`--prompt-cache` today: every turn calls `llm.reset()` and re-eval's the
full prompt. KV-cache reuse is therefore an *optional optimization* for
v0.3, not a load-bearing dependency. This audit pins the conditions
under which it would remain safe to switch on, so the test suite
documents the contract before any caller relies on it.

### 2.1 Conditions under which prompt-cache reuse is valid

A prompt-cache snapshot taken at the end of turn *t–1* is safe to reuse
as the prefix of turn *t* iff **all** of the following hold:

1. **Tokenizer/build invariance.** The `llama.cpp` build hash that
   produced the cached KV tensors is byte-identical to the runtime
   build hash. Cross-build reuse is undefined behavior.
2. **Strict-prefix property.** The turn-*t* prompt begins with the exact
   token sequence whose KV state was cached. This is **not** preserved
   when scaffold density `s` changes (the scaffold suffix is appended
   to the prompt, not the conversation tail), nor when retrieval depth
   `k` changes (worked examples are inserted *before* the task prompt,
   invalidating any cached state past the system header).
3. **No re-ordering of solved examples.** `solved[-k:]` slicing means
   any pop/insert into `solved` between turns silently invalidates the
   cache. Append-only mutation is the only safe pattern.
4. **Decoding parameters unchanged.** Cheat C3 (decoding-param tuning)
   is forbidden by the protocol, so this is automatically held under
   measurement, but a debug run that flips temperature mid-episode
   would invalidate the cache.

### 2.2 Fallback — regenerate from the canonical signed state

When any precondition above is violated, the controller must drop the
cache and re-eval from the start of the prompt. The signed chain row at
turn *t–1* is the canonical record of what was actually run; the cache
is by definition advisory. The test suite asserts that **the chain hash
does not depend on whether the prompt was served from cache or
re-eval'd** — both paths must produce the same `(state, signals, ts)`
tuple at append time, because the chain is computed over outputs and
controller decisions, not over how the prompt was tokenized.

## 3. Replay-determinism contract (B1b)

Given a recorded sequence of triples
`[(state_i, signals_i, ts_i) for i in 0..N)]`, replaying the appends in
order against any fresh database with the same private key MUST
produce:

- byte-identical `state_json`, `signals_json` at each turn,
- byte-identical `prev_hash` chain rooted at `"GENESIS"`,
- byte-identical `hash` at each turn,
- a valid Ed25519 signature on each `hash` (Ed25519 is deterministic so
  signatures are also byte-identical for the same key).

The property tests draw thousands of random episode prefixes
(Hypothesis-generated state/signal dicts, randomized append order
across multiple chain instances, randomized reopen-and-resume points)
and assert all four properties.

## 4. Tamper-detection contract (B1a)

Any single-byte mutation of `state_json`, `signals_json`, `ts`,
`prev_hash`, `hash`, or `sig` in any row MUST cause
`verify_chain.audit_chain` to exit non-zero. The property tests
parametrize the tamper site and assert the specific exit code:

| Tamper site                        | Expected auditor exit            |
|------------------------------------|----------------------------------|
| `state_json` / `signals_json` / `ts` | `EXIT_HASH` (1)                  |
| `hash` (recomputed mismatch)       | `EXIT_HASH` (1)                  |
| `sig`                              | `EXIT_SIG` (2)                   |
| `prev_hash`                        | `EXIT_LINK` (3)                  |
| row deletion mid-chain             | `EXIT_LINK` (3)                  |
| empty chain                        | `EXIT_LINK` (3)                  |
| wrong pubkey                       | `EXIT_SIG` (2)                   |

The C5 degeneracy case (signed no-op adaptation events) is covered by
the `EXIT_DEGENERATE` branch and is regression-tested directly.

## 5. Test location

`harness/tests/test_loop_b_chain.py`. Run with:

```
python -m pytest harness/tests/test_loop_b_chain.py -v
```

The Hypothesis-driven properties default to ~200 examples per test;
override with `--hypothesis-seed=N` or the `PROTEUS_HYPOTHESIS_MAX`
environment variable when running an extended audit.
