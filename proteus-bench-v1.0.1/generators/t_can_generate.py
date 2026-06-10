#!/usr/bin/env python3
"""T-CAN canary generator — PROTEUS-Bench v1.0.

Produces the frozen 100-task canary set (canary/t_can_tasks.json).
All tasks deterministically auto-checkable at temperature 0.
Categories: arithmetic chains (30), sequences (20), string ops (20),
logic/comparison (15), format-following (15).
Run once at bundle creation; the JSON is the frozen artifact, this
generator is committed for reproducibility of the freeze.
"""
import hashlib
import json
import random

CANARY_SEED = 271828


def build():
    rng = random.Random(CANARY_SEED)
    tasks = []

    def add(cat, prompt, answer):
        tasks.append({"task_id": f"CAN-{len(tasks):03d}", "category": cat,
                      "prompt": prompt + "\nAnswer with the result only.",
                      "answer": str(answer)})

    # 30 arithmetic
    for _ in range(30):
        a, b, c = rng.randint(11, 97), rng.randint(3, 19), rng.randint(2, 9)
        op = rng.choice(["+", "-"])
        val = (a + b if op == "+" else a - b) * c
        add("arith", f"Compute ({a} {op} {b}) * {c}.", val)

    # 20 sequences
    for _ in range(20):
        start, step, n = rng.randint(1, 20), rng.randint(2, 9), rng.randint(4, 7)
        kind = rng.choice(["arith", "geom"])
        if kind == "arith":
            seq = [start + i * step for i in range(n)]
            nxt = start + n * step
        else:
            r = rng.randint(2, 3)
            seq = [start * (r ** i) for i in range(n)]
            nxt = start * (r ** n)
        add("seq", f"What is the next number: {', '.join(map(str, seq))}, ...?", nxt)

    # 20 string ops
    words = ["substrate", "provenance", "conformal", "plasticity", "benchmark",
             "drift", "ledger", "manifold", "entropy", "controller"]
    for _ in range(20):
        w = rng.choice(words)
        op = rng.choice(["reverse", "upper", "count", "third"])
        if op == "reverse":
            add("string", f"Reverse the string '{w}'.", w[::-1])
        elif op == "upper":
            add("string", f"Write '{w}' in all capitals.", w.upper())
        elif op == "count":
            ch = rng.choice([c for c in set(w)])
            add("string", f"How many times does the letter '{ch}' appear in '{w}'?", w.count(ch))
        else:
            add("string", f"What is the third letter of '{w}'?", w[2])

    # 15 logic/comparison
    for _ in range(15):
        x, y, z = rng.sample(range(10, 99), 3)
        kind = rng.choice(["max", "min", "mid"])
        vals = sorted([x, y, z])
        ans = {"max": vals[2], "min": vals[0], "mid": vals[1]}[kind]
        name = {"max": "largest", "min": "smallest", "mid": "median"}[kind]
        add("logic", f"Of the numbers {x}, {y}, {z}, which is the {name}?", ans)

    # 15 format-following
    for _ in range(15):
        n = rng.randint(3, 6)
        items = rng.sample(words, n)
        ans = ";".join(sorted(items))
        add("format",
            f"Sort these alphabetically and join with semicolons, no spaces: {', '.join(items)}.",
            ans)

    assert len(tasks) == 100
    return {"canary_seed": CANARY_SEED, "size": 100,
            "decoding": "temperature=0 (greedy), pinned build",
            "isolation": "loaded only by promotion-gate runner; see auditor --check-canary-isolation",
            "tasks": tasks}


def check(task: dict, text: str) -> bool:
    return " ".join(text.split()).strip().lower() == task["answer"].strip().lower()


if __name__ == "__main__":
    blob = json.dumps(build(), sort_keys=True, indent=1)
    print(blob)
    print("sha256:", hashlib.sha256(blob.encode()).hexdigest(), flush=True)
