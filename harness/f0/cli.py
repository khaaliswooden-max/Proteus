"""F0 baseline harness — CLI entry point.

Subcommands:

  calibrate  --model <path> --out harness/results/f0_calibration.json
  band       --entropies <calib.json> --out harness/results/f0_band.json
  baseline   --suite {T-PA, T-DS, T-CAN} --model <path> [--seeds 1,2,3,5,8]
             [--episodes 10] --out <path>

Every subcommand that touches a model validates the file's SHA-256 against
`harness/ENVIRONMENT.md` before any inference. A hash mismatch is a hard refuse:
the harness will not produce a results artifact against an unrecognized model.

If the recorded hash is the placeholder `HASH PENDING` (or `--stub` is passed),
the run proceeds but all outputs are tagged `"stub_validation": true`.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import time

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from harness.f0 import run_f0  # noqa: E402

ENV_PATH = REPO_ROOT / "harness" / "ENVIRONMENT.md"

DEFAULT_SEEDS = [1, 2, 3, 5, 8]
DEFAULT_EPISODES = 10


def _parse_seeds(s: str) -> list[int]:
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def _read_recorded_hash() -> str | None:
    """Read the model SHA-256 currently recorded in ENVIRONMENT.md.

    Returns `None` if ENVIRONMENT.md doesn't exist; returns the literal string
    `"HASH PENDING"` until the operator locks in the real hash.
    """
    if not ENV_PATH.exists():
        return None
    text = ENV_PATH.read_text(encoding="utf-8")
    m = re.search(r"\*\*SHA-256:\*\*\s*([0-9a-fA-F]{64})", text)
    if m:
        return m.group(1).lower()
    if "HASH PENDING" in text:
        return "HASH PENDING"
    return None


def _verify_model(model_path: str, stub: bool) -> tuple[str, bool]:
    """Return (sha256, is_stub). Refuses to run on hash mismatch."""
    recorded = _read_recorded_hash()
    expected = None if stub else recorded
    actual = run_f0.verify_model_sha256(model_path, expected)
    is_stub = stub or (recorded == "HASH PENDING") or (recorded is None)
    return actual, is_stub


def _timed(label: str, fn, *args, **kwargs):
    t0 = time.time()
    out = fn(*args, **kwargs)
    print(f"{label}: {time.time() - t0:.1f}s elapsed", file=sys.stderr)
    return out


def cmd_calibrate(args: argparse.Namespace) -> int:
    sha, is_stub = _verify_model(args.model, args.stub)
    _timed(
        "calibrate",
        run_f0.f0_calibration_pass,
        args.model, args.out,
        model_sha256=sha, n_threads=args.threads,
        stub_validation=is_stub,
        n_prompts=args.n_prompts,
    )
    print(f"wrote {args.out} (stub_validation={is_stub})")
    return 0


def cmd_band(args: argparse.Namespace) -> int:
    out = run_f0.fit_band_from_calibration(args.entropies, args.out)
    print(json.dumps(out["band"], indent=2))
    print(f"wrote {args.out}")
    return 0


def cmd_baseline(args: argparse.Namespace) -> int:
    sha, is_stub = _verify_model(args.model, args.stub)
    if args.suite == "T-PA":
        _timed(
            "baseline T-PA",
            run_f0.f0_baseline_t_pa,
            args.model, args.seeds, args.episodes, args.out,
            model_sha256=sha, n_threads=args.threads,
            stub_validation=is_stub,
        )
    elif args.suite == "T-DS":
        _timed(
            "baseline T-DS",
            run_f0.f0_baseline_t_ds,
            args.model, args.seeds, args.episodes, args.out,
            model_sha256=sha, n_threads=args.threads,
            stub_validation=is_stub,
        )
    elif args.suite == "T-CAN":
        _timed(
            "baseline T-CAN",
            run_f0.f0_baseline_t_can,
            args.model, args.out,
            model_sha256=sha, n_threads=args.threads,
            stub_validation=is_stub,
        )
    else:
        print(f"unknown suite {args.suite!r}", file=sys.stderr)
        return 2
    print(f"wrote {args.out} (stub_validation={is_stub})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="harness.f0.cli", description=__doc__)
    sp = ap.add_subparsers(dest="cmd", required=True)

    p_cal = sp.add_parser("calibrate", help="Run the 200-prompt calibration pass.")
    p_cal.add_argument("--model", required=True)
    p_cal.add_argument("--out", required=True)
    p_cal.add_argument("--threads", type=int, default=8)
    p_cal.add_argument("--stub", action="store_true",
                       help="Tag this run as stub validation (no fingerprint enforcement).")
    p_cal.add_argument("--n-prompts", type=int, default=None,
                       help="Limit prompt count (engineering / test only).")
    p_cal.set_defaults(func=cmd_calibrate)

    p_band = sp.add_parser("band", help="Fit [theta_lo, theta_hi] from a calibration file.")
    p_band.add_argument("--entropies", required=True)
    p_band.add_argument("--out", required=True)
    p_band.set_defaults(func=cmd_band)

    p_bl = sp.add_parser("baseline", help="Run an F0 baseline suite.")
    p_bl.add_argument("--suite", required=True, choices=["T-PA", "T-DS", "T-CAN"])
    p_bl.add_argument("--model", required=True)
    p_bl.add_argument("--out", required=True)
    p_bl.add_argument("--seeds", type=_parse_seeds, default=DEFAULT_SEEDS,
                      help="Comma-separated seed list. Default: 1,2,3,5,8 (BENCHMARK §2).")
    p_bl.add_argument("--episodes", type=int, default=DEFAULT_EPISODES)
    p_bl.add_argument("--threads", type=int, default=8)
    p_bl.add_argument("--stub", action="store_true")
    p_bl.set_defaults(func=cmd_baseline)

    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
