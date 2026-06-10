# F0 Baseline Results — Artifact Schema

**Schema version:** `proteus-f0-results-v1`
**Canonical source:** `harness/results/schema.py` (Pydantic).
**Derived JSON Schema:** `harness/results/schema.json` (regenerate with
`python -m harness.results.schema --emit-json > harness/results/schema.json`).
**Validator:** `python -m harness.results.schema --validate <file>`.

This is the structure that Proteus v0.2 measured results will eventually be
compared against, per BENCHMARK §4 (B2/B3/B4 use F0 as their reference).

## Why this exists

The benchmark protocol (BENCHMARK §2) names every externality that affects an F0
number: model, build hash, decoding params, seeds, hardware envelope. A results
artifact that omits any of these is unfalsifiable — there is no way for an
outside party to know what was measured against what. The schema enforces that
nothing slips past undeclared.

The B1a chain-integrity discipline (BENCHMARK §4) is re-applied to results
artifacts in two places:

1. `bundle_manifest_hash` MUST equal
   `3d14ac4b77deede20daae1b319bb5c370b71db83c58c693587651d9cf4856e58`. Anything
   else is a result against a *different* benchmark and is rejected by the
   validator.
2. `bundle_ledger_entry` MUST equal `4` (LEDGER #0004, which signed v1.0.2 into
   the chain). Future versioned re-commits will get new entry numbers; this is
   the only seam where the schema-version of results bumps.

## Top-level fields

| Field | Type | Provenance |
|---|---|---|
| `schema_version` | `"proteus-f0-results-v1"` | Pinned by this schema. Bump when artifact shape changes. |
| `bundle_manifest_hash` | hex sha256 | MUST equal the v1.0.2 manifest hash. |
| `bundle_ledger_entry` | int (=4) | Identifies which LEDGER entry committed the bundle. |
| `llama_cpp_build_hash` | str | Upstream commit hash of the llama.cpp build (ENVIRONMENT.md §1). |
| `model_sha256` | hex sha256 | SHA-256 of the actual GGUF used. CLI refuses to run on mismatch. |
| `hardware_tag` | `HardwareTag` | `{cpu_model, ram_gb, gpu_model_or_none, os, threads_used}`. |
| `decoding` | `DecodingParams` | Echoes BENCHMARK §2 frozen decoding constants. |
| `calibration` | `CalibrationBand \| null` | `{theta_lo, theta_hi, n_windows, definition}`. Null for non-calibration runs. |
| `f0_scores` | `dict[str, F0SuiteResult]` | Keyed by suite name (`"T-PA"`, `"T-PR"`, `"T-DS"`, `"T-CAN"`). |
| `seeds` | `list[int]` | The exact seed set used; for a measured run this MUST be `[1, 2, 3, 5, 8]`. |
| `ts_run_start_utc` | ISO-8601 datetime | Wall-clock start. |
| `ts_run_end_utc` | ISO-8601 datetime | Wall-clock end. |
| `tokens_generated` | int | Total tokens generated across the run. Sanity check on §2's ~1.2–1.5M estimate. |
| `stub_validation` | bool | `true` when the run used a stub model (TinyLlama / Qwen 0.5B / etc.). MUST be `false` for any artifact claiming to be a measured F0 result. |
| `notes` | str \| null | Free-form notes from the operator. |

## Suite result (`F0SuiteResult`)

```
{
  "suite": "T-PA" | "T-PR" | "T-DS" | "T-CAN",
  "n_episodes": int,
  "n_turns": int,
  "per_turn": [TurnRecord, ...],
  "summary": { ... suite-specific aggregates ... }
}
```

`TurnRecord` carries `seed`, `episode_id`, `turn`, plus suite-specific fields
(`correct`, `score`, `mean_entropy`, and a free `extra` dict for anything the
suite needs to log but the schema does not yet name).

The `summary` dict is suite-specific. Recommended (not enforced) shapes:

- **T-PA / T-PR:** `{"adherence_rate": float, "adherence_rate_turns_20_40": float}`
  — the turns 20–40 window is the one B2 evaluates.
- **T-DS:** `{"accuracy": float, "accuracy_per_level": {int: float}, "band_occupancy_dev": float}`
  — band occupancy here is informational only; the canonical B3 occupancy comes
  from solution runs against this F0.
- **T-CAN:** `{"correctness": float, "correct_count": int, "n_tasks": int}` — for
  B4 to subtract from later.

## Validator behavior

The validator (`schema.py --validate <file>`) is intentionally strict:

- Unknown top-level fields are rejected (`extra="forbid"`).
- `bundle_manifest_hash` and `bundle_ledger_entry` are checked against the
  committed v1.0.2 values.
- Numeric ranges and string formats fall through pydantic's defaults.

The validator does NOT compute statistics, score the run, or compare against
thresholds. Threshold comparisons happen at PR review time, against the
committed BENCHMARK §4 table.

## Reproducibility chain

```
LEDGER #0004 signed
   └─> proteus-bench-v1.0.2/MANIFEST.json
        └─> bundle_manifest_hash 3d14ac4b... (this schema enforces equality)
             └─> llama_cpp_build_hash (locked at first F0 run, ENVIRONMENT.md §1)
                  └─> model_sha256 (locked at first download, ENVIRONMENT.md §3)
                       └─> hardware_tag + decoding (logged per run)
                            └─> calibration + f0_scores (the deliverable)
```

If any link in this chain is missing or wrong, the artifact does not validate.
That is the entire point of the schema.
