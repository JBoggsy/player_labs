#!/usr/bin/env python3
"""CTF A/B adapter — the game-specific half of a `ctf-ab` skill.

The CTF *adapter* for the game-agnostic `coworld-ab` engine (crewrift's compare.py is
the reference). It owns everything CTF-specific — reading a CTF results.json/episode.json,
CTF's metrics (win/draw/loss, captures, kills/deaths, team kills from the replay-event
warehouse when present), and a single "all" group (CTF is team-symmetric; every beacon
appearance is the same policy) — and delegates ALL statistics, verdicts, and rendering
to `ab_stats`.

CTF specifics vs crewrift:
- Scores are +1 win / -1 loss / -1 timeout draw (GameVersion 21): a draw and a loss are
  indistinguishable in scores, so `draw_rate` is derived from the episode having NO
  winner (all scores equal) rather than from the score value.
- results.json kills/deaths are NULL at 0.7.69+ league episodes (WORKING_CONTEXT watch
  item); they ARE populated for experience-request episodes, which is what A/Bs run on.
- Team kills aren't in results.json at all. If a warehouse (`wh/warehouse.duckdb`, built
  by ctf-event-warehouse) exists under the batch dir, per-appearance team-kill counts
  and stacked-pair counts are pulled from it; otherwise those metrics are skipped.

CRITICAL — the two batches must be FRESH + MATCHED (same window, same roster, same
count); see the coworld-ab SKILL.md.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

# Import the shared engine from the root `coworld-ab` skill. Repo root is parents[5]:
# scripts -> ctf-ab -> skills -> .claude -> ctf_lab -> <repo root>.
_REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(_REPO / ".claude" / "skills" / "coworld-ab" / "scripts"))
import ab_stats  # noqa: E402


@dataclass
class Rec:
    win: bool
    draw: bool
    score: int
    captures: int
    kills: int
    deaths: int
    team_kills: int | None  # from the warehouse; None = no warehouse for this batch
    stacked_ticks: int | None  # pos snapshots with a teammate <25px (warehouse)
    ops_fail: bool


def parse_spec(spec: str) -> tuple[str, int | None]:
    """'beacon:v25' -> ('beacon', 25); 'beacon' -> ('beacon', None)."""
    if ":v" in spec:
        name, v = spec.split(":v", 1)
        return name, int(v)
    return spec, None


def slot_entries(episode: dict) -> list[tuple[int, str | None, int | None]]:
    """(position, policy_name, version) per slot — xreq `participants` shape first."""
    out: list[tuple[int, str | None, int | None]] = []
    for entry in episode.get("participants") or []:
        if entry.get("position") is not None:
            out.append((entry["position"], entry.get("policy_name"), entry.get("version")))
    if out:
        return out
    for entry in episode.get("policy_results") or []:
        pol = entry.get("policy") or {}
        if entry.get("position") is not None:
            out.append((entry["position"], pol.get("name"), pol.get("version")))
    return out


def _warehouse_lookups(root: Path) -> tuple[dict, dict]:
    """(episode_id, slot) -> team_kills and -> stacked_ticks, from `wh/warehouse.duckdb`
    under the batch dir if present; empty dicts otherwise."""
    db = root / "wh" / "warehouse.duckdb"
    if not db.exists():
        return {}, {}
    try:
        import duckdb
    except ImportError:
        return {}, {}
    con = duckdb.connect(str(db), read_only=True)
    tk = {
        (eid, slot): n
        for eid, slot, n in con.execute(
            """
            SELECT episode_id, actor_slot, count(*)
            FROM replay_events
            WHERE key='kill'
              AND CAST(json_extract(value_json,'$.victim_slot') AS INT) % 2 = actor_slot % 2
            GROUP BY 1, 2
            """
        ).fetchall()
    }
    stacked = {
        (eid, slot): n
        for eid, slot, n in con.execute(
            """
            WITH pos AS (
              SELECT episode_id, tick, actor_slot,
                     CAST(json_extract(value_json,'$.x') AS INT) x,
                     CAST(json_extract(value_json,'$.y') AS INT) y
              FROM replay_events
              WHERE key='pos' AND CAST(json_extract(value_json,'$.alive') AS BOOLEAN)
            )
            SELECT a.episode_id, a.actor_slot, count(*)
            FROM pos a JOIN pos b
              ON a.episode_id=b.episode_id AND a.tick=b.tick
             AND a.actor_slot <> b.actor_slot AND a.actor_slot % 2 = b.actor_slot % 2
            WHERE sqrt(pow(a.x-b.x,2)+pow(a.y-b.y,2)) < 25
            GROUP BY 1, 2
            """
        ).fetchall()
    }
    con.close()
    return tk, stacked


def load_batch(root: Path, policy: str, version: int | None) -> list[Rec]:
    """Every appearance of (policy[:version]) across the episode dirs in `root`."""
    tk_map, stacked_map = _warehouse_lookups(root)
    have_wh = bool(tk_map or stacked_map)
    recs: list[Rec] = []
    for ep in sorted(p for p in root.iterdir() if p.is_dir() and p.name != "wh"):
        ej, rj = ep / "episode.json", ep / "results.json"
        if not (ej.exists() and rj.exists()):
            continue
        try:
            episode, results = json.loads(ej.read_text()), json.loads(rj.read_text())
        except json.JSONDecodeError:
            continue
        eid = episode.get("id") or ep.name
        slots = [pos for pos, name, ver in slot_entries(episode)
                 if name == policy and (version is None or ver == version)]
        for slot in slots:
            rec = _record(results, slot, episode)
            if rec is None:
                continue
            if have_wh:
                rec.team_kills = tk_map.get((eid, slot), 0)
                rec.stacked_ticks = stacked_map.get((eid, slot), 0)
            recs.append(rec)
    return recs


def _record(results: dict, slot: int, episode: dict) -> Rec | None:
    scores = results.get("scores") or []
    if slot is None or slot >= len(scores):
        return None

    def col(k, default=0):
        a = results.get(k) or []
        return a[slot] if slot < len(a) else default

    win = bool(col("win"))
    # GV21: a decisive game has winners (+1) and losers (-1); a timeout draw scores
    # everyone -1 with NO win flags — so "nobody won" identifies the draw.
    draw = not any(results.get("win") or [])
    return Rec(
        win=win,
        draw=draw,
        score=int(col("scores")),
        captures=int(col("captures") or 0),
        kills=int(col("kills") or 0),
        deaths=int(col("deaths") or 0),
        team_kills=None,
        stacked_ticks=None,
        ops_fail=bool(episode.get("error")),
    )


# --- metrics: (key, higher_is_better, kind, applies_to_group) ------------------------

METRICS = [
    ("win_rate",        True,  "rate", None),
    ("draw_rate",       False, "rate", None),
    ("loss_rate",       False, "rate", None),
    ("score_mean",      True,  "mean", None),
    ("captures_mean",   True,  "mean", None),
    ("kills_mean",      True,  "mean", None),
    ("deaths_mean",     False, "mean", None),
    ("team_kills_mean", False, "mean", None),
    ("stacked_ticks_mean", False, "mean", None),
    ("ops_fail_rate",   False, "rate", None),
]
GROUPS = ["all"]


def metric_value(recs: list[Rec], key: str) -> tuple[float, int] | None:
    """(value, n) for a metric over a group's records, or None if N/A."""
    if not recs:
        return None
    n = len(recs)
    if key == "win_rate":
        return sum(r.win for r in recs) / n, n
    if key == "draw_rate":
        return sum(r.draw for r in recs) / n, n
    if key == "loss_rate":
        return sum((not r.win) and (not r.draw) for r in recs) / n, n
    if key == "score_mean":
        return statistics.mean(r.score for r in recs), n
    if key == "captures_mean":
        return statistics.mean(r.captures for r in recs), n
    if key == "kills_mean":
        return statistics.mean(r.kills for r in recs), n
    if key == "deaths_mean":
        return statistics.mean(r.deaths for r in recs), n
    if key == "team_kills_mean":
        vals = [r.team_kills for r in recs if r.team_kills is not None]
        return (statistics.mean(vals), len(vals)) if vals else None
    if key == "stacked_ticks_mean":
        vals = [r.stacked_ticks for r in recs if r.stacked_ticks is not None]
        return (statistics.mean(vals), len(vals)) if vals else None
    if key == "ops_fail_rate":
        return sum(r.ops_fail for r in recs) / n, n
    return None


def value_fn(recs: list[Rec], key: str) -> list[float]:
    """Per-appearance values for a metric (for the continuous significance test)."""
    if key == "score_mean":    return [float(r.score) for r in recs]
    if key == "captures_mean": return [float(r.captures) for r in recs]
    if key == "kills_mean":    return [float(r.kills) for r in recs]
    if key == "deaths_mean":   return [float(r.deaths) for r in recs]
    if key == "team_kills_mean":
        return [float(r.team_kills) for r in recs if r.team_kills is not None]
    if key == "stacked_ticks_mean":
        return [float(r.stacked_ticks) for r in recs if r.stacked_ticks is not None]
    return []


def by_group(recs: list[Rec]) -> dict[str, list[Rec]]:
    return {"all": list(recs)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("baseline_dir", help="Episodes dir for the BASELINE version (matched, fresh).")
    ap.add_argument("candidate_dir", help="Episodes dir for the CANDIDATE version (matched, fresh).")
    ap.add_argument("--baseline", required=True, help="Baseline policy as NAME or NAME:vN.")
    ap.add_argument("--candidate", required=True, help="Candidate policy as NAME or NAME:vN.")
    ap.add_argument("--target", help="Lead metric (e.g. win_rate, team_kills_mean).")
    ap.add_argument("--json", help="Also write the structured diff here.")
    args = ap.parse_args()

    bname, bver = parse_spec(args.baseline)
    cname, cver = parse_spec(args.candidate)
    base_recs = load_batch(Path(args.baseline_dir), bname, bver)
    cand_recs = load_batch(Path(args.candidate_dir), cname, cver)
    if not base_recs:
        raise SystemExit(f"no '{args.baseline}' appearances in {args.baseline_dir}")
    if not cand_recs:
        raise SystemExit(f"no '{args.candidate}' appearances in {args.candidate_dir}")

    base, cand = by_group(base_recs), by_group(cand_recs)
    deltas = ab_stats.build_deltas(base, cand, METRICS, metric_value, value_fn, GROUPS)
    print(ab_stats.render_markdown(args.baseline, args.candidate, base, cand,
                                   deltas, args.target, GROUPS, METRICS))

    if args.json:
        Path(args.json).write_text(json.dumps(
            ab_stats.emit_json(args.baseline, args.candidate, args.target, deltas), indent=2))
        print(f"\n[wrote JSON: {args.json}]")


if __name__ == "__main__":
    main()
