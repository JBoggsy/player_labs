#!/usr/bin/env python
"""Stage 2 — LLM semantic labels for every distinct chat text (Bedrock Haiku).

Chat is heavily templated, so we classify each DISTINCT text ONCE and cache
(``dataset/llm_cache.json``). Each text gets a small set of interpretable semantic
flags plus the accused target color (which stage 3 needs for the persuasion label):

  - accuses      : casts suspicion on / accuses a specific other player
  - target       : the accused player's COLOR (or null) — for the persuasion label
  - provides_evidence : cites a concrete observation (a vent, a body, proximity, a task, a route)
  - defends_self : denies suspicion of the speaker / deflects heat off themselves ("not me")
  - asks_question: asks another player to account for themselves
  - vouches      : clears / vouches for another player
  - bandwagons   : agrees with / piles onto an accusation someone else already made

Deterministic (temperature 0), batched. Idempotent: re-run reuses the cache; ``--refresh``
re-labels everything.

Output: ``dataset/llm_cache.json`` ({text -> {flags}}) and ``dataset/chats_labeled.parquet``
(chats.parquet joined to its per-text labels).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
REGION = "us-east-1"
BATCH = 25

FLAGS = ["accuses", "provides_evidence", "defends_self", "asks_question", "vouches", "bandwagons"]

INSTRUCTION = (
    "You label MEETING chat from a social-deduction game (Among Us style). For each numbered "
    "message, return a JSON object with these fields:\n"
    '  "i": <index>,\n'
    '  "accuses": true/false  — does it cast suspicion on / accuse a specific OTHER player?\n'
    '  "target": "<color|none>" — if it accuses, the accused player\'s COLOR, else "none". '
    "Colors: red blue green yellow orange pink purple cyan white black lime brown.\n"
    '  "provides_evidence": true/false — cites a concrete observation (a vent, a body, being '
    "near someone, a task, a route, a timing) rather than a bare opinion?\n"
    '  "defends_self": true/false — denies suspicion of THE SPEAKER or deflects heat off '
    'themselves (e.g. "not me", "I was doing tasks")?\n'
    '  "asks_question": true/false — asks another player to account for themselves?\n'
    '  "vouches": true/false — clears or vouches FOR another player?\n'
    '  "bandwagons": true/false — agrees with or piles onto an accusation someone else '
    "already made?\n"
    "Reply with ONLY a JSON array of these objects, one per message."
)


def _parse_json_array(text: str) -> list[dict]:
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end < 0:
        return []
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []


def classify(texts: list[str]) -> dict[str, dict]:
    """Distinct texts -> label dicts. Missing/unparseable default to all-false/none."""
    import boto3

    br = boto3.client("bedrock-runtime", region_name=REGION)
    out: dict[str, dict] = {}
    for start in range(0, len(texts), BATCH):
        chunk = texts[start : start + BATCH]
        listing = "\n".join(f"{i}: {t!r}" for i, t in enumerate(chunk))
        try:
            resp = br.converse(
                modelId=MODEL_ID,
                messages=[{"role": "user", "content": [{"text": INSTRUCTION + "\n\n" + listing}]}],
                inferenceConfig={"maxTokens": 4000, "temperature": 0},
            )
            parsed = _parse_json_array(resp["output"]["message"]["content"][0]["text"])
        except Exception as exc:  # noqa: BLE001 — one bad batch shouldn't sink the run
            print(f"  batch {start//BATCH} failed: {exc}")
            parsed = []
        for obj in parsed:
            try:
                i = int(obj["i"])
            except (KeyError, ValueError, TypeError):
                continue
            if not (0 <= i < len(chunk)):
                continue
            tgt = str(obj.get("target", "none")).strip().lower()
            out[chunk[i]] = {
                **{f: bool(obj.get(f, False)) for f in FLAGS},
                "target": None if tgt in ("none", "", "null") else tgt,
            }
        print(f"  labeled {min(start+BATCH, len(texts))}/{len(texts)}", flush=True)
    for t in texts:
        out.setdefault(t, {**{f: False for f in FLAGS}, "target": None})
    return out


def build(ds_dir: Path, *, refresh: bool) -> None:
    chats = pd.read_parquet(ds_dir / "chats.parquet")
    texts = sorted(chats["text"].dropna().unique().tolist())
    cache_path = ds_dir / "llm_cache.json"
    cache: dict[str, dict] = {}
    if cache_path.exists() and not refresh:
        cache = json.loads(cache_path.read_text())
    missing = [t for t in texts if t not in cache]
    print(f"{len(texts)} distinct chat texts ({len(missing)} new to label via {MODEL_ID})")
    if missing:
        cache.update(classify(missing))
        cache_path.write_text(json.dumps(cache, indent=0))

    # join labels onto every chat row
    def lab(t: str, field: str):
        return cache.get(t, {}).get(field)

    for f in FLAGS:
        chats[f"s_{f}"] = chats["text"].map(lambda t: int(bool(lab(t, f))))
    chats["accused_color"] = chats["text"].map(lambda t: lab(t, "target"))
    chats.to_parquet(ds_dir / "chats_labeled.parquet")
    print(f"wrote {len(chats)} labeled rows -> {ds_dir/'chats_labeled.parquet'}")
    for f in FLAGS:
        print(f"  s_{f}: {int(chats[f's_{f}'].sum())} ({100*chats[f's_{f}'].mean():.0f}%)")
    print(f"  accused_color set: {int(chats['accused_color'].notna().sum())} "
          f"({100*chats['accused_color'].notna().mean():.0f}%)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, default=Path(__file__).parent / "dataset")
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    build(args.dataset, refresh=args.refresh)


if __name__ == "__main__":
    main()
