"""F0 baseline results schema — single source of truth.

A result file is REJECTED if `bundle_manifest_hash` is not the v1.0.2 hash
`3d14ac4b77deede20daae1b319bb5c370b71db83c58c693587651d9cf4856e58` (the Loop B
B1a chain-integrity discipline applied to results artifacts).

`harness/results/schema.json` is regenerated from this module by `python -m
harness.results.schema --emit-json`. Treat the .py as canonical and the .json
as a derived artifact.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

BUNDLE_MANIFEST_HASH_V1_0_2 = (
    "3d14ac4b77deede20daae1b319bb5c370b71db83c58c693587651d9cf4856e58"
)
BUNDLE_LEDGER_ENTRY = 4

SUITE_NAMES = ("T-PA", "T-PR", "T-DS", "T-CAN")


class HardwareTag(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cpu_model: str
    ram_gb: int
    gpu_model_or_none: str | None
    os: str
    threads_used: int


class DecodingParams(BaseModel):
    """Frozen by BENCHMARK §2. The runner echoes these; it never sets them."""
    model_config = ConfigDict(extra="forbid")
    temperature_task: float = 0.7
    top_p_task: float = 0.95
    temperature_canary: float = 0.0
    n_ctx: int = 8192
    scaffold_max_tokens_per_turn: int = 1024
    entropy_window: int = 64


class CalibrationBand(BaseModel):
    """Fitted by proteus-bench-v1.0.2/calibration/fit_band.py over windowed entropies."""
    model_config = ConfigDict(extra="forbid")
    theta_lo: float
    theta_hi: float
    n_windows: int
    definition: str


class TurnRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seed: int
    episode_id: str
    turn: int
    correct: bool | None = None
    score: float | None = None
    mean_entropy: float | None = None
    extra: dict | None = None


class F0SuiteResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    suite: Literal["T-PA", "T-PR", "T-DS", "T-CAN"]
    n_episodes: int
    n_turns: int
    per_turn: list[TurnRecord] = Field(default_factory=list)
    summary: dict


class F0Results(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    schema_version: Literal["proteus-f0-results-v1"]
    bundle_manifest_hash: str
    bundle_ledger_entry: int
    llama_cpp_build_hash: str
    model_sha256: str
    hardware_tag: HardwareTag
    decoding: DecodingParams
    calibration: CalibrationBand | None
    f0_scores: dict[str, F0SuiteResult]
    seeds: list[int]
    ts_run_start_utc: datetime
    ts_run_end_utc: datetime
    tokens_generated: int
    stub_validation: bool = False
    notes: str | None = None

    @field_validator("bundle_manifest_hash")
    @classmethod
    def _check_manifest_hash(cls, v: str) -> str:
        if v != BUNDLE_MANIFEST_HASH_V1_0_2:
            raise ValueError(
                f"bundle_manifest_hash {v!r} != committed v1.0.2 hash "
                f"{BUNDLE_MANIFEST_HASH_V1_0_2!r}; result rejected (B1a discipline)."
            )
        return v

    @field_validator("bundle_ledger_entry")
    @classmethod
    def _check_ledger_entry(cls, v: int) -> int:
        if v != BUNDLE_LEDGER_ENTRY:
            raise ValueError(
                f"bundle_ledger_entry {v} != {BUNDLE_LEDGER_ENTRY} (LEDGER #0004)."
            )
        return v


def validate_file(path: str) -> F0Results:
    """Parse and validate a results JSON file. Raises pydantic.ValidationError on failure."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return F0Results.model_validate(data)


def _emit_json_schema() -> str:
    return json.dumps(F0Results.model_json_schema(), indent=2, sort_keys=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit-json", action="store_true",
                    help="Print JSON Schema for F0Results to stdout.")
    ap.add_argument("--validate", help="Validate a results JSON file.")
    a = ap.parse_args()
    if a.emit_json:
        print(_emit_json_schema())
    elif a.validate:
        try:
            r = validate_file(a.validate)
            print(f"OK: {a.validate} validates as proteus-f0-results-v1 "
                  f"({len(r.f0_scores)} suites, stub={r.stub_validation})")
        except Exception as e:
            print(f"REJECTED: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        ap.print_help()
