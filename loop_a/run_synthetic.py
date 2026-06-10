#!/usr/bin/env python3
"""Loop A synthetic validation — controller ON vs OFF, paired difficulty traces.

NOT a benchmark run. Purpose: validate closed-loop mechanics end-to-end
(signal -> ACI -> controller -> actuators -> signed chain -> committed auditor)
before any model is in the loop. The plant is a simulator whose entropy and
task quality respond to difficulty and to the actuators; the controller has
no access to simulator internals — only to the entropy stream and task
outcomes, exactly as it will see a real model.

Plant model (synthetic, declared):
  level L(t): 12-level staircase over 60 turns (mirrors T-DS)
  effective difficulty: d = L - 0.8k - 0.5s - 0.3g   (actuator relief)
  token entropy ~ N(0.8 + 0.22*d, 0.18), 64 tokens/turn, clipped to [0, 6]
  task quality  q = clip(1 - 0.085*d + N(0, 0.05), 0, 1); nonconformity = 1 - q

Pairing: identical RNG seeds for ON and OFF runs -> identical noise draws.
"""
import datetime
import json
import random
import statistics
import subprocess
import sys

sys.path.insert(0, "/home/claude/proteus/loop_a")
from loop_a import EntropySignal, ACISkill, FlowBandController, WINDOW  # noqa: E402
from chain import StateChain, generate_test_keypair  # noqa: E402

TURNS, LEVELS, STEP = 60, 12, 5


def level(t):
    return min(t // STEP, LEVELS - 1)


def simulate_turn(rng, lvl, k, g, s):
    d = max(lvl - 0.8 * k - 0.5 * s - 0.3 * g, 0.0)
    ents = [min(max(rng.gauss(0.8 + 0.22 * d, 0.18), 0.0), 6.0) for _ in range(WINDOW)]
    q = min(max(1.0 - 0.085 * d + rng.gauss(0, 0.05), 0.0), 1.0)
    return ents, q


def calibration_distribution(seed=999, n=300):
    """Mixed-difficulty, no-actuator entropy distribution (mirrors the
    committed fit_band.py IQR construction)."""
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        lvl = rng.randrange(LEVELS)
        ents, _ = simulate_turn(rng, lvl, 0, 0, 0)
        out.append(statistics.mean(ents))
    return out


def run(seed: int, controlled: bool, db_path: str, priv):
    rng = random.Random(seed)
    cal = calibration_distribution()
    sig = EntropySignal(cal)
    aci = ACISkill()
    ctl = FlowBandController()
    chain = StateChain(db_path, priv)
    state = {"episode_seed": seed, "mode": "controlled" if controlled else "frozen",
             "actuators": {"k": 0, "g": 0, "s": 0}}
    occupancy, gaps, qualities = 0, [], []

    for t in range(TURNS):
        k, g, s = (ctl.k, ctl.g, ctl.s) if controlled else (0, 0, 0)
        ents, q = simulate_turn(rng, level(t), k, g, s)
        for e in ents:
            sig.push(e)
        c_t = sig.challenge()
        skill_t = aci.skill()
        step = ctl.step(c_t, skill_t)
        aci.update(1.0 - q)
        qualities.append(q)
        gaps.append(step["gap"])
        if step["in_band"]:
            occupancy += 1
        if controlled and step["adaptation_event"]:
            state["actuators"] = {"k": ctl.k, "g": ctl.g, "s": ctl.s}
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        chain.append(state, {"c_t": round(c_t, 4), "skill_t": round(skill_t, 4),
                             "gap": round(step["gap"], 4), "k": k, "g": g, "s": s,
                             "adaptation_event": bool(controlled and step["adaptation_event"])}, ts)
    lat = chain.latency_stats()
    chain.close()
    return {"seed": seed, "mode": "ON" if controlled else "OFF",
            "band_occupancy_pct": 100.0 * occupancy / TURNS,
            "mean_quality": round(statistics.mean(qualities), 4),
            "mean_abs_gap": round(statistics.mean(abs(x) for x in gaps), 4),
            "latency": lat}


def main():
    priv = generate_test_keypair("/tmp/loop_a_test.pub")
    seeds = [1, 2, 3, 5, 8]
    results = {"ON": [], "OFF": []}
    for sd in seeds:
        results["OFF"].append(run(sd, False, f"/tmp/ep_off_{sd}.sqlite", priv))
        results["ON"].append(run(sd, True, f"/tmp/ep_on_{sd}.sqlite", priv))

    def agg(rows, key):
        return round(statistics.mean(r[key] for r in rows), 2)

    summary = {
        "occupancy_ON_pct": agg(results["ON"], "band_occupancy_pct"),
        "occupancy_OFF_pct": agg(results["OFF"], "band_occupancy_pct"),
        "quality_ON": agg(results["ON"], "mean_quality"),
        "quality_OFF": agg(results["OFF"], "mean_quality"),
        "per_seed": results,
        "controller_overhead": results["ON"][-1]["latency"],
    }
    print(json.dumps(summary, indent=1))

    # Run the COMMITTED auditor (frozen bundle) against a controlled-run chain
    audit = subprocess.run(
        ["python3", "/home/claude/proteus-bench-v1.0/auditor/verify_chain.py",
         "--db", "/tmp/ep_on_8.sqlite", "--pubkey", "/tmp/loop_a_test.pub"],
        capture_output=True, text=True)
    print("COMMITTED-AUDITOR EXIT:", audit.returncode)
    print(audit.stdout)


if __name__ == "__main__":
    main()
