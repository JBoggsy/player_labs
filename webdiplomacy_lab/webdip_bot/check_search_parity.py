"""Capture exact search behavior in two images, then compare the JSONL records.

Run this same file mounted at /checks/check_search_parity.py in both images so
imports still come from /opt, including in the unchanged baseline image. Set
PYTHONPATH=/opt and PYTHONHASHSEED=0 in both containers:

    python /checks/check_search_parity.py capture /lab/webdip_bot/tests/golden.json > baseline.jsonl
    python /checks/check_search_parity.py compare baseline.jsonl candidate.jsonl

Captures full orders, RNG primitives/state, ordered score digests using float.hex,
non-timing traces, memory, samples, config restoration and scripted-clock calls.
The optional cases supplement, but never rewrite, the existing golden contract.
"""

import argparse
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random
import time


def exact(value):
    if isinstance(value, float):
        return {"float": value.hex()}
    if isinstance(value, dict):
        assert all(isinstance(k, str) for k in value), "unexpected non-string record key"
        return {k: exact(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [exact(v) for v in value]
    return value


def feed(digest, value):
    digest.update(json.dumps(exact(value), separators=(",", ":")).encode())
    digest.update(b"\n")


class RecordedRandom(random.Random):
    """Record the same primitives that Random's shuffle/choice/choices consume."""

    def __init__(self, seed):
        super().__init__(seed)
        self.digest = hashlib.sha256()
        self.calls = Counter()

    def random(self):
        value = super().random()
        self.calls["random"] += 1
        feed(self.digest, ("random", value))
        return value

    def getrandbits(self, k):
        value = super().getrandbits(k)
        self.calls["getrandbits"] += 1
        feed(self.digest, ("getrandbits", k, value))
        return value


class DecisionClock:
    def __init__(self, step):
        self.step = step
        self.calls = 0

    def __call__(self):
        value = self.calls * self.step
        self.calls += 1
        return value


@contextmanager
def record_scores():
    from webdip_bot.search import SearchBot

    digest = hashlib.sha256()
    counts = Counter()
    names = ("_score_fast", "_score", "_evaluate", "_diplomacy_adjust", "_spring_value", "_rollout",
             "_improve_for", "_dumb_share", "_update_beliefs", "_ascend", "_remember", "_joint_alternatives")
    originals = {name: getattr(SearchBot, name) for name in names}

    def wrap(name, method):
        def recorded(bot, *args, **kwargs):
            result = method(bot, *args, **kwargs)
            counts[name] += 1
            if name == "_joint_alternatives":
                feed(digest, (name, [[list(joint.items()) for joint in options] for options in result]))
            else:
                feed(digest, (name, result))
            if name == "_remember":
                feed(digest, args)
            if name == "_update_beliefs":
                feed(digest, bot.memory)
            return result
        return recorded

    try:
        for name, method in originals.items():
            setattr(SearchBot, name, wrap(name, method))
        yield digest, counts
    finally:
        for name, method in originals.items():
            setattr(SearchBot, name, method)


def scenarios(data, suite):
    if suite in ("all", "golden"):
        for i, case in enumerate(data["cases"]):
            for policy in data["policies"]:
                yield f"golden/{i}/{policy}", policy, case, {}, False, 0.0
    if suite == "golden":
        return
    movement = [c for c in data["cases"] if c["kind"] == "movement"]
    early = movement[0]
    later = next(c for c in movement if c["turn"] >= 8 and c["turn"] % 2 == 0)
    small = {"SEARCH_OPPONENT_SAMPLES": 2, "SEARCH_SEEDS": 2, "SEARCH_PASSES": 1}
    modes = [
        ("level2", "kissinger2", {}),
        ("level1-mixture", "kissinger", {"OPP_LEVEL1_SHARE": 0.5}),
        ("level1-disabled", "kissinger", {"OPP_LEVEL1_SHARE": 0.0}),
        ("fixed-dumbbot", "kissinger", {"OPP_MODEL": "dumbbot"}),
        ("mixed", "rasputin", {}),
        ("risk-share", "fabius", {"SEARCH_OBJECTIVE": "share"}),
        ("learned", "kutuzov", {"SEARCH_LEARNED_WEIGHT": 0.5}),
        ("learned-share-diplomacy", "castlereagh", {"SEARCH_EVAL": "learned", "SEARCH_LEARNED_WEIGHT": 0.5, "SEARCH_OBJECTIVE": "share"}),
        ("package", "kissinger", {"SEARCH_FAST_ADJ": 0}),
        ("package-learned-diplomacy", "castlereagh", {"SEARCH_FAST_ADJ": 0, "SEARCH_EVAL": "learned", "SEARCH_OBJECTIVE": "share"}),
        ("convoy-fallback", "kissinger", {"SEARCH_CONVOY_APPROX": 0}),
        ("rollout", "napoleon", {"SEARCH_ROLLOUT_SAMPLES": 2}),
        ("triples-restarts", "kissinger", {"SEARCH_TRIPLES": 1, "SEARCH_RESTARTS": 2}),
        ("nash", "nash", {"NASH_CANDIDATES": 2, "NASH_ITERS": 2, "NASH_EVAL_SAMPLES": 2}),
        ("legacy-string-values", "search", {"SEARCH_EVAL": "other", "OPP_MODEL": "other"}),
    ]
    for label, policy, overrides in modes:
        yield f"optional/{label}", policy, later, {**small, **overrides}, False, 0.0
    yield "optional/diplomacy-history", "castlereagh", later, small, True, 0.0
    yield "optional/dumbbot-history", "castlereagh", later, {**small, "OPP_LIKELIHOOD": "dumbbot"}, True, 0.0
    build_seen = set()
    for case in (c for c in data["cases"] if c["kind"] == "builds"):
        # One build and one disband, selected below by unit/centre counts.
        units = sum(u["countryID"] == case["country"] for u in case["units"])
        centers = sum(c["countryID"] == case["country"] for c in case["centers"])
        label = "disband" if units > centers else "build"
        if label not in build_seen:
            build_seen.add(label)
            yield f"optional/{label}", "kissinger", case, {"SEARCH_BUILDS": 1, "SEARCH_BUILD_CANDIDATES": 2}, False, 0.0
        if len(build_seen) == 2:
            break
    if "disband" not in build_seen:
        # The golden winter snapshots can contain only positive build balances.
        # Derive a removal case by taking one centre away from an opening position.
        disband = deepcopy(early)
        country = disband["country"]
        own_centers = [c for c in disband["centers"] if c["countryID"] == country]
        units = sum(u["countryID"] == country for u in disband["units"])
        disband["centers"] = [c for c in disband["centers"] if c["countryID"] != country] + own_centers[:units - 1]
        disband.update(kind="builds", phase="Builds", turn=1, slots=[{"unitID": None}], belief="prior")
        yield "optional/derived-disband", "kissinger", disband, {"SEARCH_BUILDS": 1, "SEARCH_BUILD_CANDIDATES": 2}, False, 0.0
    for label, policy, case, overrides in [
        ("ascent", "kissinger", early, small),
        ("nash", "nash", early, {**small, "NASH_CANDIDATES": 2}),
    ]:
        yield f"clock/{label}", policy, case, {**overrides, "SEARCH_TIME_BUDGET_S": 0.05}, False, 0.05


class History:
    def __init__(self, bot):
        pending = bot.memory["pending"]
        units = {str(u["terrID"]): u for u in bot.b.units}
        orders = []
        for territory, record in pending["units"].items():
            kind, to, origin = record["samples"][0]
            orders.append({"countryID": units[territory]["countryID"], "terrID": int(territory),
                           "type": kind, "toTerrID": to, "fromTerrID": origin})
        self.data = {"phases": [{"turn": pending["turn"], "phase": "Diplomacy", "orders": orders}]}

    def file(self, ref):
        assert ref == "history"
        return self.data


def decision(variant, case, policy, overrides, history, step, defaults):
    from webdip_bot import config
    from webdip_bot.bot import policy_class
    from webdip_bot.golden import BELIEFS, _board

    for key, value in defaults.items():
        setattr(config, key, deepcopy(value))
    cls = policy_class(policy)
    config.SEARCH_TIME_BUDGET_S = 1e9
    for key, value in overrides.items():
        setattr(config, key, value)
    before = {k: deepcopy(getattr(config, k)) for k in defaults}
    rng = RecordedRandom(case["seed"])
    clock = DecisionClock(step)
    original_clock = time.monotonic
    with record_scores() as (scores, score_calls):
        try:
            time.monotonic = clock
            bot = cls(variant, _board(variant, case["units"], case["centers"]),
                      case["country"], case["phase"], case["turn"], rng)
            lo = BELIEFS[case["belief"]]
            bot.memory = {"logodds": {str(c): lo for c in range(1, 8)} if lo is not None else {}, "pending": None}
            if history:
                bot.choose(case["slots"])
                api = History(bot)
                bot.memory["hostility"] = {"2": 1.25, "7": 0.5}
                state = {"search": bot.memory}
                bot = cls(variant, _board(variant, case["units"], case["centers"]),
                          case["country"], case["phase"], case["turn"] + 1, rng)
                bot.observe(api, {"files": {"history": "history"}}, state)
            orders = bot.choose(case["slots"])
        finally:
            time.monotonic = original_clock
    after = {k: getattr(config, k) for k in defaults}
    assert before == after, "search failed to restore config"
    return exact({
        "orders": orders, "rng_state": rng.getstate(), "rng_digest": rng.digest.hexdigest(),
        "rng_calls": dict(rng.calls), "scores": scores.hexdigest(), "score_calls": dict(score_calls),
        "trace": {k: v for k, v in bot.trace.items() if not k.endswith("_ms")},
        "memory": bot.memory, "opponents": getattr(bot, "opponents", None),
        "fast_samples": getattr(bot, "fast_samples", None), "clock_calls": clock.calls,
        "top_seen": getattr(bot, "top_seen", None),
        "config": after,
    })


def capture(path, suite):
    from webdip_bot import config
    from webdip_bot.golden import _signature

    data = json.loads(Path(path).read_text())
    defaults = {k: deepcopy(v) for k, v in vars(config).items() if k.isupper()}
    for label, policy, case, overrides, history, step in scenarios(data, suite):
        result = decision(data["variant"], case, policy, overrides, history, step, defaults)
        if label.startswith("golden/"):
            assert _signature(result["orders"]) == case["expected"][policy], label
        print(json.dumps({"case": label, "result": result}, separators=(",", ":")), flush=True)


def compare(baseline, candidate):
    a = [json.loads(line) for line in Path(baseline).read_text().splitlines()]
    b = [json.loads(line) for line in Path(candidate).read_text().splitlines()]
    mismatches = 0
    for i in range(max(len(a), len(b))):
        if i >= len(a) or i >= len(b) or a[i] != b[i]:
            mismatches += 1
            fields = [] if i >= min(len(a), len(b)) else [k for k in a[i]["result"] if a[i]["result"][k] != b[i]["result"].get(k)]
            print(json.dumps({"mismatch": i, "case": a[i]["case"] if i < len(a) else b[i]["case"], "fields": fields}))
    print(json.dumps({"checked": len(a), "mismatches": mismatches}))
    return int(mismatches != 0 or not a)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("capture")
    run.add_argument("golden")
    run.add_argument("--suite", choices=("all", "golden", "optional"), default="all")
    diff = sub.add_parser("compare")
    diff.add_argument("baseline")
    diff.add_argument("candidate")
    args = parser.parse_args()
    if args.command == "capture":
        capture(args.golden, args.suite)
    else:
        raise SystemExit(compare(args.baseline, args.candidate))
