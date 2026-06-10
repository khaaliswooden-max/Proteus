#!/usr/bin/env python3
"""T-PA convention pool generator — PROTEUS-Bench v1.0.

Deterministically generates the 500-item convention pool and per-episode
draws for the Personalization Adherence suite. Pool contents are a function
of POOL_SEED only; episode draws are a function of (episode_seed, episode_id).

Convention types:
  SUB    — terminology substitution: always write TERM_B instead of TERM_A
  BAN    — prohibited token: never use TOKEN
  FMT    — formatting rule: structural constraint checkable by regex
  PROC   — named procedure: ordered steps, invoked by name (T-PR mode)

Checker contract: check(convention, text) -> bool (adhered / violated),
deterministic, no model in the loop.
"""
import hashlib
import json
import random
import re
import sys

POOL_SEED = 412906  # frozen at commit; changing it changes the benchmark identity

_TERMS = [
    ("car", "vehicle"), ("house", "dwelling"), ("dog", "canine"), ("city", "municipality"),
    ("money", "funds"), ("job", "occupation"), ("food", "provisions"), ("book", "volume"),
    ("idea", "notion"), ("problem", "challenge"), ("answer", "resolution"), ("start", "commence"),
    ("end", "conclude"), ("big", "substantial"), ("small", "minimal"), ("fast", "rapid"),
    ("slow", "gradual"), ("good", "favorable"), ("bad", "adverse"), ("new", "novel"),
    ("old", "legacy"), ("buy", "procure"), ("sell", "divest"), ("help", "assist"),
    ("show", "demonstrate"), ("use", "utilize"), ("make", "fabricate"), ("need", "require"),
    ("plan", "blueprint"), ("team", "cohort"), ("goal", "objective"), ("rule", "stipulation"),
    ("test", "evaluation"), ("error", "defect"), ("change", "modification"), ("result", "outcome"),
    ("report", "brief"), ("meeting", "session"), ("question", "inquiry"), ("list", "register"),
]

_BANNED = [
    "basically", "actually", "very", "really", "just", "simply", "obviously", "clearly",
    "certainly", "definitely", "literally", "honestly", "quite", "rather", "somewhat",
    "perhaps", "maybe", "probably", "essentially", "fundamentally", "ultimately",
    "interestingly", "importantly", "notably", "significantly", "absolutely",
    "totally", "completely", "extremely", "incredibly",
]

_FMT_RULES = [
    {"name": "no_exclamation", "desc": "Never use exclamation marks.", "regex": r"!", "violates_if_match": True},
    {"name": "sentences_max_20w", "desc": "Keep every sentence at 20 words or fewer.", "regex": None, "checker": "max_sentence_words:20"},
    {"name": "numbers_as_digits", "desc": "Always write numbers as digits, never spelled out (one..ten).", "regex": r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\b", "violates_if_match": True},
    {"name": "no_first_person_plural", "desc": "Never use 'we' or 'our'.", "regex": r"\b([Ww]e|[Oo]ur)\b", "violates_if_match": True},
    {"name": "end_with_period", "desc": "Every response must end with a period.", "regex": r"\.\s*$", "violates_if_match": False},
    {"name": "no_semicolons", "desc": "Never use semicolons.", "regex": r";", "violates_if_match": True},
    {"name": "no_parentheses", "desc": "Never use parentheses.", "regex": r"[()]", "violates_if_match": True},
    {"name": "single_paragraph", "desc": "Respond in exactly one paragraph (no blank lines).", "regex": r"\n\s*\n", "violates_if_match": True},
    {"name": "no_questions_back", "desc": "Never end a response with a question mark.", "regex": r"\?\s*$", "violates_if_match": True},
    {"name": "uppercase_acronyms_spelled", "desc": "On first use, expand any acronym in parentheses-free prose as 'ACRONYM, that is, expansion'.", "regex": None, "checker": "manual_v1_1"},
]

_PROC_VERBS = ["summarize", "rank", "tag", "translate-style", "audit", "rewrite", "score", "extract"]
_PROC_STEPS = [
    "restate the input in one sentence",
    "list exactly three key points",
    "flag any number present in the input",
    "give a one-word verdict in capitals",
    "append the marker [DONE]",
    "count the words in your own answer and report the count",
    "name the most important noun in the input",
    "give a confidence from 0 to 10",
]


def build_pool():
    rng = random.Random(POOL_SEED)
    pool = []
    # 160 substitutions (both directions of 40 pairs, x2 contextual variants)
    for a, b in _TERMS:
        pool.append({"type": "SUB", "from": a, "to": b,
                     "desc": f"Always write '{b}' instead of '{a}'."})
        pool.append({"type": "SUB", "from": b, "to": a,
                     "desc": f"Always write '{a}' instead of '{b}'."})
    # pad substitutions with adjective intensifier swaps
    while sum(1 for c in pool if c["type"] == "SUB") < 160:
        a, b = rng.sample(_BANNED, 2)
        pool.append({"type": "SUB", "from": a, "to": b,
                     "desc": f"Always write '{b}' instead of '{a}'."})
    # 150 bans (words and bigrams)
    for w in _BANNED:
        pool.append({"type": "BAN", "token": w, "desc": f"Never use the word '{w}'."})
    while sum(1 for c in pool if c["type"] == "BAN") < 150:
        w1, w2 = rng.sample(_BANNED, 2)
        pool.append({"type": "BAN", "token": f"{w1} {w2}",
                     "desc": f"Never use the phrase '{w1} {w2}'."})
    # 90 formatting rules (10 base x parameter variants)
    for fr in _FMT_RULES:
        pool.append({"type": "FMT", **fr})
    for n in (12, 15, 18, 25, 30):
        pool.append({"type": "FMT", "name": f"sentences_max_{n}w",
                     "desc": f"Keep every sentence at {n} words or fewer.",
                     "regex": None, "checker": f"max_sentence_words:{n}"})
    while sum(1 for c in pool if c["type"] == "FMT") < 90:
        w = rng.choice(_BANNED)
        pool.append({"type": "FMT", "name": f"must_include_{w}_never",
                     "desc": f"Never begin a sentence with '{w.capitalize()}'.",
                     "regex": rf"(^|[.!?]\s+){w.capitalize()}\b", "violates_if_match": True})
    # 100 named procedures (T-PR mode)
    pid = 0
    while sum(1 for c in pool if c["type"] == "PROC") < 100:
        verb = rng.choice(_PROC_VERBS)
        steps = rng.sample(_PROC_STEPS, rng.randint(3, 5))
        pid += 1
        pool.append({"type": "PROC", "name": f"{verb}-protocol-{pid}",
                     "steps": steps,
                     "desc": f"Procedure '{verb}-protocol-{pid}': " + "; then ".join(steps) + "."})
    pool = pool[:500]
    assert len(pool) == 500, f"pool size {len(pool)} != 500"
    for i, c in enumerate(pool):
        c["conv_id"] = f"PA-{i:03d}"
    return pool


def draw_episode(pool, episode_seed: int, episode_id: str, n: int = 5):
    """Deterministic per-episode convention draw."""
    h = hashlib.sha256(f"{episode_seed}|{episode_id}|PROTEUS-v1.0".encode()).hexdigest()
    rng = random.Random(int(h[:16], 16))
    return rng.sample(pool, n)


def _max_sentence_words(text: str, limit: int) -> bool:
    sentences = re.split(r"[.!?]+\s+", text.strip())
    return all(len(s.split()) <= limit for s in sentences if s)


def check(convention: dict, text: str) -> bool:
    """True = adhered. Deterministic; no model in the loop."""
    t = convention["type"]
    if t == "SUB":
        return re.search(rf"\b{re.escape(convention['from'])}\b", text, re.I) is None
    if t == "BAN":
        return re.search(rf"\b{re.escape(convention['token'])}\b", text, re.I) is None
    if t == "FMT":
        chk = convention.get("checker")
        if chk and chk.startswith("max_sentence_words:"):
            return _max_sentence_words(text, int(chk.split(":")[1]))
        if chk == "manual_v1_1":
            return True  # excluded from scoring in v1.0; counted in v1.1 (flagged)
        m = re.search(convention["regex"], text, re.M) is not None
        return (not m) if convention["violates_if_match"] else m
    if t == "PROC":
        # Scored only on invocation turns: every step's signature must appear in order.
        idx = -1
        for step in convention["steps"]:
            key = step.split()[0]  # leading verb as anchor; full check in harness
            j = text.lower().find(key.lower(), idx + 1)
            if j < 0:
                return False
            idx = j
        return True
    raise ValueError(f"unknown convention type {t}")


if __name__ == "__main__":
    pool = build_pool()
    out = {"pool_seed": POOL_SEED, "size": len(pool), "pool": pool}
    blob = json.dumps(out, sort_keys=True, indent=1)
    print(hashlib.sha256(blob.encode()).hexdigest() if "--hash" in sys.argv else blob)
