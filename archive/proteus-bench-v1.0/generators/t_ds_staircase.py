#!/usr/bin/env python3
"""T-DS difficulty staircase generator — PROTEUS-Bench v1.0.

60 turns, 12 difficulty levels, step every 5 turns. Difficulty axes:
arithmetic chain depth, constraint count, distractor load. Every task has
a deterministic exact-match answer; checker normalizes whitespace/case.
Parameterized so that eval draws use unseen parameter combinations (cheat C6).
"""
import hashlib
import json
import random
import sys

TURNS = 60
LEVELS = 12
STEP_EVERY = 5


def _level(turn: int) -> int:
    return min(turn // STEP_EVERY, LEVELS - 1)


def _arith_chain(rng, depth):
    val = rng.randint(2, 9)
    expr = str(val)
    for _ in range(depth):
        op = rng.choice(["+", "-", "*"])
        n = rng.randint(2, 9)
        if op == "+":
            val += n
        elif op == "-":
            val -= n
        else:
            val *= n
        expr += f" {op} {n}"
    return expr, val


def make_task(rng, level: int):
    depth = 2 + level            # arithmetic chain depth 2..13
    distractors = level // 2     # irrelevant numeric facts 0..5
    constraints = 1 + level // 4 # answer-format constraints 1..3

    expr, val = _arith_chain(rng, depth)
    lines = []
    for _ in range(distractors):
        lines.append(f"Note (irrelevant): the value {rng.randint(10, 99)} appears in record {rng.randint(100, 999)}.")
    lines.append(f"Compute, left to right with standard precedence: {expr}")
    fmt = ["Answer with the number only."]
    if constraints >= 2:
        fmt.append("Prefix the answer with 'RESULT: '.")
    if constraints >= 3:
        fmt.append("Append ' /end' after the number.")
    prompt = "\n".join(lines + fmt)

    ans = str(val)
    if constraints >= 2:
        ans = "RESULT: " + ans
    if constraints >= 3:
        ans = ans + " /end"
    return {"prompt": prompt, "answer": ans, "level": level,
            "axes": {"depth": depth, "distractors": distractors, "constraints": constraints}}


def generate_episode(episode_seed: int, episode_id: str):
    h = hashlib.sha256(f"{episode_seed}|{episode_id}|TDS-v1.0".encode()).hexdigest()
    rng = random.Random(int(h[:16], 16))
    return [dict(turn=t, **make_task(rng, _level(t))) for t in range(TURNS)]


def check(task: dict, text: str) -> bool:
    return " ".join(text.split()).strip().lower() == " ".join(task["answer"].split()).strip().lower()


if __name__ == "__main__":
    ep = generate_episode(int(sys.argv[1]) if len(sys.argv) > 1 else 1, "demo")
    print(json.dumps(ep[:3], indent=1))
    print(f"... {TURNS} turns, levels 0..{LEVELS-1}")
