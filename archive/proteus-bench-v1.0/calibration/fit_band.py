#!/usr/bin/env python3
"""Calibration band fitter — PROTEUS-Bench v1.0.

Defines [theta_lo, theta_hi] as the interquartile range [Q1, Q3] of windowed
pre-sampling logit entropy over the committed 200-prompt calibration set.
Deterministic: no fitting objective, no tuning freedom (hostile review F3).

Also emits the 200-prompt calibration set itself, generated deterministically
from CAL_SEED across the same difficulty axes as T-DS plus open-ended prose
prompts, so the calibration distribution spans the difficulty range.

Workflow:
  1. fit_band.py --emit-prompts > calibration_prompts.json   (committed in bundle)
  2. At F0 baseline time: run model over prompts, log per-token entropies
     (window W=64) to entropies.json
  3. fit_band.py --fit entropies.json  -> {"theta_lo": Q1, "theta_hi": Q3}
     Result recorded in the results artifact next to the build hash.
"""
import argparse
import hashlib
import json
import random
import statistics
import sys

CAL_SEED = 161803
N_PROMPTS = 200
WINDOW = 64

_TOPICS = ["water systems", "supply chains", "orbital mechanics", "bread baking",
           "graph theory", "soil chemistry", "maritime law", "typography",
           "battery storage", "bird migration"]


def emit_prompts():
    rng = random.Random(CAL_SEED)
    prompts = []
    # 100 structured (staircase-style, all 12 levels represented)
    sys.path.insert(0, ".")
    for i in range(100):
        level = i % 12
        depth = 2 + level
        val = rng.randint(2, 9)
        expr = str(val)
        for _ in range(depth):
            expr += f" {rng.choice(['+', '-', '*'])} {rng.randint(2, 9)}"
        prompts.append({"cal_id": f"CAL-{i:03d}", "kind": "structured",
                        "prompt": f"Compute: {expr}. Answer with the number only."})
    # 100 open-ended prose at varied lengths
    for i in range(100, 200):
        topic = rng.choice(_TOPICS)
        words = rng.choice([30, 60, 120, 200])
        prompts.append({"cal_id": f"CAL-{i:03d}", "kind": "open",
                        "prompt": f"In about {words} words, explain one practical aspect of {topic}."})
    return {"cal_seed": CAL_SEED, "n": N_PROMPTS, "window": WINDOW, "prompts": prompts}


def fit(entropy_file: str):
    """entropies.json: list of per-prompt lists of windowed mean entropies."""
    data = json.loads(open(entropy_file).read())
    flat = [w for prompt_windows in data for w in prompt_windows]
    if len(flat) < 100:
        print("FATAL: insufficient entropy samples", file=sys.stderr)
        sys.exit(1)
    qs = statistics.quantiles(flat, n=4, method="inclusive")
    return {"theta_lo": qs[0], "theta_hi": qs[2], "n_windows": len(flat),
            "definition": "IQR [Q1,Q3], inclusive method, frozen per build hash"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit-prompts", action="store_true")
    ap.add_argument("--fit")
    a = ap.parse_args()
    if a.emit_prompts:
        blob = json.dumps(emit_prompts(), sort_keys=True, indent=1)
        print(blob)
    elif a.fit:
        print(json.dumps(fit(a.fit), indent=1))
    else:
        ap.print_help()
