#!/usr/bin/env python3
"""Analysis lenses for agricogla replays — the observability search space.

A lens reads a cogweb.replay.v1 replay (zlib JSON: {protocol, frames}) and emits a
*finding* — an actionable claim about why a seat won/lost. Which lenses are worth
running is itself an experiment (see docs/LENS_EXPERIMENTS.md): each finding is
logged with the lens that produced it, so we can score lenses by downstream
diagnostic yield (did the finding -> a beam mutation -> a win).

Replay structure (verified against a real farmhand episode):
  frames[]: type in {lobby, snapshot, status, actPrompt, event}
  event frame: {type:"event", event:{seat, kind, text, turn}}
    kind taxonomy: take plow sow bake cook renovate family breed build fences
                   occupation improvement pass starting field feed begging
                   release phase harvest reveal scheduled card end
  snapshot frame: {type:"snapshot", snapshot:{turn, generation, state}}

Usage:
  python lenses.py <replay.json|->            # run all lenses, print findings JSON
  python lenses.py --lens begging_by_harvest <replay.json>
"""
from __future__ import annotations

import json
import sys
import zlib
from collections import defaultdict

HARVEST_ROUNDS = {4, 7, 9, 11, 13, 14}


def load_replay(path: str) -> dict:
    raw = sys.stdin.buffer.read() if path == "-" else open(path, "rb").read()
    try:
        return json.loads(zlib.decompress(raw))
    except zlib.error:
        return json.loads(raw)


def events(replay: dict) -> list[dict]:
    return [f["event"] for f in replay.get("frames", []) if f.get("type") == "event"]


def seat_names(replay: dict) -> dict[int, str]:
    """Map seat -> name from feed/begging event text (first occurrence)."""
    names: dict[int, str] = {}
    for e in events(replay):
        s = e.get("seat")
        if s is not None and s not in names and e.get("text"):
            # "<name> feeds the family ..." / "<name> is short ..."
            t = e["text"]
            for sep in (" feeds", " is short", " takes", " plays", " grows", " builds"):
                if sep in t:
                    names[s] = t.split(sep)[0]
                    break
    return names


# ---- LENSES -----------------------------------------------------------------
# Each returns {lens, finding (str), signals (dict), per_seat (dict)}.

def lens_begging_by_harvest(replay: dict, me_seat: int | None = None) -> dict:
    """Which seats went short at which harvests, and by how much (−3 pts/food)."""
    beg = defaultdict(list)  # seat -> [(round, short)]
    for e in events(replay):
        if e.get("kind") == "begging":
            short = _int_after(e.get("text", ""), "short ")
            beg[e.get("seat")].append((e.get("turn"), short))
    names = seat_names(replay)
    per_seat = {names.get(s, f"seat{s}"): {"begs": v, "total_food_short": sum(x[1] for x in v),
                                           "pts_lost": -3 * sum(x[1] for x in v)} for s, v in beg.items()}
    worst = min(per_seat.items(), key=lambda kv: kv[1]["pts_lost"], default=(None, None))
    finding = "no begging this game" if not per_seat else \
        f"{worst[0]} bled {worst[1]['pts_lost']} pts to begging ({worst[1]['total_food_short']} food short across {len(worst[1]['begs'])} harvests)"
    return {"lens": "begging_by_harvest", "finding": finding, "signals": {"begging": dict(per_seat)}}


def lens_family_timeline(replay: dict, me_seat: int | None = None) -> dict:
    """When each seat grew, and whether growth was followed by begging (the §1.2 trap)."""
    grows = defaultdict(list)  # seat -> [round]
    begs = defaultdict(set)
    for e in events(replay):
        if e.get("kind") == "family":
            grows[e.get("seat")].append(e.get("turn"))
        if e.get("kind") == "begging":
            begs[e.get("seat")].add(e.get("turn"))
    names = seat_names(replay)
    per_seat = {}
    uncosted = []
    for s, rounds in grows.items():
        nm = names.get(s, f"seat{s}")
        # a grow is "uncosted" if the seat begged at or after a harvest following it
        bad = any(any(b >= g for b in begs[s]) for g in rounds) and bool(begs[s])
        per_seat[nm] = {"grew_rounds": rounds, "begged_rounds": sorted(begs[s]), "uncosted_growth": bad}
        if bad:
            uncosted.append(nm)
    finding = (f"uncosted growth (grew then starved): {', '.join(uncosted)}" if uncosted
               else "all family growth was fed (no uncosted growth)")
    return {"lens": "family_timeline", "finding": finding, "signals": {"family": per_seat}}


def lens_food_engine(replay: dict, me_seat: int | None = None) -> dict:
    """Sow vs bake vs cook vs beg — did each seat build a food engine (§1.3)?"""
    agg = defaultdict(lambda: {"sow": 0, "bake": 0, "cook": 0, "beg": 0, "first_cook": None})
    for e in events(replay):
        s, k = e.get("seat"), e.get("kind")
        if s is None:
            continue
        if k == "sow":
            agg[s]["sow"] += 1
        elif k == "bake":
            agg[s]["bake"] += 1
        elif k == "cook":
            agg[s]["cook"] += 1
            if agg[s]["first_cook"] is None:
                agg[s]["first_cook"] = e.get("turn")
        elif k == "begging":
            agg[s]["beg"] += 1
    names = seat_names(replay)
    per_seat = {names.get(s, f"seat{s}"): v for s, v in agg.items()}
    starvers = [n for n, v in per_seat.items() if v["beg"] and v["first_cook"] in (None,) ]
    finding = (f"seats with no cooker yet begging: {', '.join(starvers)}" if starvers
               else "food engines present where needed")
    return {"lens": "food_engine", "finding": finding, "signals": {"food_engine": per_seat}}


def lens_card_timing(replay: dict, me_seat: int | None = None) -> dict:
    """When each seat played occupations/improvements (card tempo)."""
    cards = defaultdict(list)
    for e in events(replay):
        if e.get("kind") in ("occupation", "improvement", "card"):
            cards[e.get("seat")].append((e.get("turn"), e.get("kind")))
    names = seat_names(replay)
    per_seat = {names.get(s, f"seat{s}"): {"plays": v, "count": len(v),
                                           "first": (v[0][0] if v else None)} for s, v in cards.items()}
    finding = "card play tempo: " + "; ".join(f"{n}:{d['count']}@r{d['first']}" for n, d in per_seat.items()) if per_seat else "no cards played"
    return {"lens": "card_timing", "finding": finding, "signals": {"cards": per_seat}}


def lens_contention(replay: dict, me_seat: int | None = None) -> dict:
    """Which action spaces were taken first each round (proxy for beaten-to-a-spot)."""
    # take events carry the space title in text "... (Forest)" — count who took what first.
    first_taker = {}  # (round, space) -> seat
    space_counts = defaultdict(lambda: defaultdict(int))
    for e in events(replay):
        if e.get("kind") == "take":
            sp = _paren(e.get("text", ""))
            if sp:
                space_counts[sp][e.get("seat")] += 1
    hot = sorted(space_counts.items(), key=lambda kv: -sum(kv[1].values()))[:5]
    finding = "most-taken spaces: " + ", ".join(f"{sp}({sum(c.values())})" for sp, c in hot)
    return {"lens": "contention", "finding": finding, "signals": {"space_takes": {k: dict(v) for k, v in space_counts.items()}}}


LENSES = {
    "begging_by_harvest": lens_begging_by_harvest,
    "family_timeline": lens_family_timeline,
    "food_engine": lens_food_engine,
    "card_timing": lens_card_timing,
    "contention": lens_contention,
}


def _int_after(text: str, marker: str) -> int:
    try:
        return int(text.split(marker)[1].split()[0])
    except (IndexError, ValueError):
        return 0


def _paren(text: str) -> str | None:
    if "(" in text and ")" in text:
        return text[text.rfind("(") + 1:text.rfind(")")]
    return None


def main():
    args = sys.argv[1:]
    only = None
    if args and args[0] == "--lens":
        only = args[1]
        args = args[2:]
    path = args[0] if args else "-"
    replay = load_replay(path)
    out = []
    for name, fn in LENSES.items():
        if only and name != only:
            continue
        try:
            out.append(fn(replay))
        except Exception as e:  # a broken lens shouldn't kill the pass
            out.append({"lens": name, "error": f"{type(e).__name__}: {e}"})
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
