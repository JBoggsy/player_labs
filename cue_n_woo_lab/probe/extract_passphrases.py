"""Extract passphrase plant->retrieve tables from downloaded Cue-n-Woo replays.

A passphrase round (design SS0): a player PLANTS a key=value in its PRIVATE interview
ask (which the judge sees in scoring context) and RETRIEVES it with a challenge question.
This script scans all replays under a rounds root and, per author policy, reports:

  * each distinct challenge question (the "key") and the committed secret answer(s),
  * the stable CORE of the answer (first clause, <=5 words),
  * PLANTED?: whether that committed answer text actually appears in the SAME player's
    private interview asks in that episode (the signature of a true passphrase, vs a
    persona-anchored question that merely leans on the style),
  * stability: modal-core share across episodes.

No network. Usage: uv run python extract_passphrases.py [rounds_root] [-o out.json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
from collections import Counter, defaultdict

CUE_RE = re.compile(r"CUE\s+(ONE|TWO|THREE)\s*[-:]\s*([a-z][a-z ]+?)\s*phrase", re.I)


def cue_key(question: str) -> str | None:
    m = CUE_RE.search(question or "")
    return f"{m.group(1).upper()} / {m.group(2).strip().lower()}" if m else None


def core(answer: str) -> str:
    a = (answer or "").split(",")[0].split(".")[0].strip()
    return " ".join(a.split()[:5])


def planted(answer_core: str, interview_asks: list[str]) -> bool:
    """Did this committed answer's core appear verbatim in the player's own asks?"""
    if not answer_core:
        return False
    blob = " ".join(interview_asks).lower()
    return answer_core.lower() in blob


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("rounds_root", nargs="?", default="/tmp/cnw_rounds")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()

    # author -> key -> {"cores": Counter, "planted": int, "total": int, "sample_q": str}
    tbl: dict[str, dict[str, dict]] = defaultdict(lambda: defaultdict(
        lambda: {"cores": Counter(), "planted": 0, "total": 0, "sample_q": ""}))
    episodes_scanned = 0

    for rp in sorted(glob.glob(os.path.join(args.rounds_root, "r*", "*", "replay.json"))):
        ep_dir = os.path.dirname(rp)
        try:
            meta = json.load(open(os.path.join(ep_dir, "episode.json")))
            replay = json.load(open(rp))
        except (OSError, json.JSONDecodeError):
            continue
        parts = {p["position"]: p["policy_name"] for p in meta.get("participants", [])}
        episodes_scanned += 1
        for slot, p in enumerate(replay.get("players", [])):
            author = parts.get(slot)
            if not author:
                continue
            asks = [t.get("question", "") for t in p.get("judge", [])]
            for pr in p.get("proposals", []):
                q, a = pr.get("question"), pr.get("answer")
                if not q or not a:
                    continue
                key = cue_key(q) or q.strip()[:55]
                c = core(a)
                rec = tbl[author][key]
                rec["cores"][c] += 1
                rec["total"] += 1
                rec["planted"] += int(planted(c, asks))
                if not rec["sample_q"]:
                    rec["sample_q"] = q.strip()[:120]

    # build report
    report: dict[str, dict] = {}
    for author, keys in tbl.items():
        author_total = sum(r["total"] for r in keys.values())
        if author_total < 6:
            continue
        entries = []
        for key, rec in keys.items():
            modal, modal_n = rec["cores"].most_common(1)[0]
            entries.append({
                "key": key,
                "core": modal,
                "modal_share": round(modal_n / rec["total"], 2),
                "n": rec["total"],
                "planted_rate": round(rec["planted"] / rec["total"], 2),
                "sample_q": rec["sample_q"],
            })
        entries.sort(key=lambda e: -e["n"])
        # is this author a passphrase author? high planted_rate on its main keys
        main = [e for e in entries if e["n"] >= 3]
        avg_plant = sum(e["planted_rate"] for e in main) / len(main) if main else 0.0
        report[author] = {
            "authored_total": author_total,
            "distinct_keys": len(keys),
            "passphrase_author": avg_plant >= 0.5,
            "avg_planted_rate": round(avg_plant, 2),
            "keys": entries,
        }

    # print summary
    print(f"episodes scanned: {episodes_scanned}\n")
    pp = {a: r for a, r in report.items() if r["passphrase_author"]}
    print(f"=== PASSPHRASE AUTHORS ({len(pp)}) — plant verified in their own interview ===")
    for author, r in sorted(pp.items(), key=lambda kv: -kv[1]["authored_total"]):
        print(f"\n### {author}  ({r['authored_total']} authored, {r['distinct_keys']} keys, "
              f"planted {r['avg_planted_rate']:.0%})")
        for e in r["keys"]:
            if e["n"] < 2:
                continue
            print(f"  {e['key']:<26} -> {e['core']!r}  "
                  f"(modal {e['modal_share']:.0%}, n={e['n']}, planted {e['planted_rate']:.0%})")
    print(f"\n=== NON-passphrase authors (persona/fingerprint, table doesn't apply) ===")
    for author, r in sorted(report.items(), key=lambda kv: -kv[1]["authored_total"]):
        if not r["passphrase_author"]:
            print(f"  {author:<26} {r['authored_total']:>4} authored, "
                  f"{r['distinct_keys']:>3} keys, planted {r['avg_planted_rate']:.0%}")

    if args.out:
        json.dump(report, open(args.out, "w"), indent=2)
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
