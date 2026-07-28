#!/usr/bin/env python3
"""Scan a belief-synced warehouse for crewborg belief-vs-ground-truth divergences.

Input: a warehouse that build_belief_log.py has extended with belief_* partitions
(each belief row already carries `truth_roles` — the ground-truth role of every
color the payload mentions — plus self_color/self_slot). This scans those
partitions with a fixed battery of detectors and emits every divergence as one
row: (episode_id, slot, ts, kind, severity, detail).

Detectors (kind -> meaning):
  confirmed_crew        witnessed-set entry whose color is truly crew — a witness
                        false positive (the class behind the HS liar-ledger gate).
  believed_crew         the over-the-flee-bar set gained a truly-crew color.
  teammate_wrong        imposter teammate belief includes a truly-crew color.
  teammate_incomplete   imposter never completed its teammate identification.
  ranking_top_crew      a meeting snapshot ranked a truly-crew color #1 with
                        p >= --confident-bar while a true imposter was ranked lower.
  imposter_unranked     a live true imposter absent from a meeting ranking.
  death_belief_lag      belief noticed a death > --death-lag-tol ticks after the
                        replay kill/eject (slow perception).
  phantom_death         belief recorded a death the replay never shows.
  vote_crew_over_imposter  voted a truly-crew target while its OWN ranking put a
                        true imposter at or above the same posterior.
  role_mismatch         role_resolved disagrees with the seat's ground-truth role
                        (catastrophic self-state failure).
  clock_desync          the build's phase-alignment check flagged this seat
                        (belief ticks off the server timeline — reconnect/stall).

Usage:
    uv run python crewrift_lab/.claude/skills/crewrift-belief-audit/scripts/scan_divergences.py \
        --warehouse /tmp/wh [--out /tmp/divergences.jsonl] [--policy crewborg]

Prints a per-kind, per-role summary with rates (per seat and per meeting) and
worst examples; writes the full row set as JSONL for downstream analysis.
"""

from __future__ import annotations

import argparse
import glob as _glob
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from belief_common import connect, events_glob, normalize_role  # noqa: E402

# A "confident" posterior — flagging a crew-topped ranking only above this keeps
# the scan about *wrong beliefs*, not diffuse uncertainty (the fitted posterior
# is bimodal; non-witnessed tops max ~0.74 — see WORKING_CONTEXT W2).
DEFAULT_CONFIDENT_BAR = 0.5
# Ticks of belief-after-truth death delay considered "lagged perception".
DEFAULT_DEATH_LAG_TOL = 240  # ~10s


def q(con, sql: str) -> list[tuple]:
    return con.execute(sql).fetchall()


def part_exists(warehouse: Path, key: str) -> bool:
    return bool(_glob.glob(events_glob(warehouse, key)))


def read_belief(con, warehouse: Path, key: str) -> list[tuple]:
    """(episode_id, slot, ts, role, value_dict) for one belief partition."""
    if not part_exists(warehouse, key):
        return []
    rows = q(con, f"SELECT episode_id, slot, ts, role, value FROM read_parquet('{events_glob(warehouse, key)}')")
    return [(ep, slot, ts, role, json.loads(v)) for ep, slot, ts, role, v in rows]


class Scan:
    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.counts: Counter = Counter()

    def add(self, episode_id: str, slot: int, ts: int, role: str | None,
            kind: str, severity: str, detail: dict) -> None:
        self.rows.append({
            "episode_id": episode_id, "slot": slot, "ts": ts, "role": role,
            "kind": kind, "severity": severity, "detail": detail,
        })
        self.counts[(kind, role or "?")] += 1


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------


def scan_confirmed_and_believed(con, wh: Path, scan: Scan) -> None:
    for ep, slot, ts, role, v in read_belief(con, wh, "belief_imposter_confirmed"):
        color = (v.get("color") or "").lower()
        if v.get("truth_roles", {}).get(color) == "crew":
            scan.add(ep, slot, ts, role, "confirmed_crew", "high",
                     {"color": color, "p": v.get("p")})
    for ep, slot, ts, role, v in read_belief(con, wh, "belief_believed_changed"):
        truth = v.get("truth_roles", {})
        for color in v.get("added") or []:
            if truth.get(str(color).lower()) == "crew":
                scan.add(ep, slot, ts, role, "believed_crew", "medium", {"color": color})


def scan_teammates(con, wh: Path, scan: Scan) -> None:
    # Last teammate_belief_changed per seat decides wrong/incomplete.
    latest: dict[tuple[str, int], tuple[int, str | None, dict]] = {}
    for ep, slot, ts, role, v in read_belief(con, wh, "belief_teammate_belief_changed"):
        key = (ep, slot)
        if key not in latest or ts >= latest[key][0]:
            latest[key] = (ts, role, v)
    for (ep, slot), (ts, role, v) in latest.items():
        truth = v.get("truth_roles", {})
        wrong = [c for c in (v.get("teammate_colors") or []) if truth.get(str(c).lower()) == "crew"]
        if wrong:
            scan.add(ep, slot, ts, role, "teammate_wrong", "high",
                     {"wrong_colors": wrong, "believed": v.get("teammate_colors")})
        if v.get("complete") is False:
            scan.add(ep, slot, ts, role, "teammate_incomplete", "low",
                     {"known": v.get("known_teammates"), "expected": v.get("expected_teammates")})


def ground_truth_maps(con, wh: Path) -> tuple[dict[str, dict[str, str]], dict[tuple[str, str], int]]:
    """({episode: {color: role}}, {(episode, color): earliest true death ts}) from
    the replay's player_manifest + kill/died partitions — the full-roster truth
    the enriched truth_roles (mention-scoped) can't provide."""
    roles: dict[str, dict[str, str]] = {}
    slot_color: dict[tuple[str, int], str] = {}
    if part_exists(wh, "player_manifest"):
        for ep, slot, color, role in q(con,
                f"SELECT episode_id, slot, lower(json_extract_string(value,'$.color')), "
                f"       json_extract_string(value,'$.role') "
                f"FROM read_parquet('{events_glob(wh, 'player_manifest')}') "
                f"WHERE json_extract_string(value,'$.source')='replay' AND slot >= 0"):
            if color:
                roles.setdefault(ep, {})[color] = normalize_role(role)
                slot_color[(ep, slot)] = color
    deaths: dict[tuple[str, str], int] = {}

    def note_death(ep: str, slot: int, ts: int) -> None:
        color = slot_color.get((ep, slot))
        if color is not None:
            key = (ep, color)
            deaths[key] = min(deaths.get(key, 1 << 60), int(ts))

    if part_exists(wh, "kill"):
        for ep, ts, vslot in q(con,
                f"SELECT episode_id, ts, json_extract(value,'$.victim_slot')::int "
                f"FROM read_parquet('{events_glob(wh, 'kill')}') WHERE slot >= 0"):
            if vslot is not None:
                note_death(ep, int(vslot), ts)
    if part_exists(wh, "died"):
        for ep, ts, slot in q(con,
                f"SELECT episode_id, ts, slot FROM read_parquet('{events_glob(wh, 'died')}') WHERE slot >= 0"):
            note_death(ep, int(slot), ts)
    return roles, deaths


def scan_rankings(con, wh: Path, scan: Scan, confident_bar: float,
                  truth_roles_by_ep: dict[str, dict[str, str]],
                  truth_deaths: dict[tuple[str, str], int]) -> tuple[int, dict]:
    """Snapshot-level detectors. Returns (n_snapshots, snapshot_index) where
    snapshot_index maps (episode, slot, meeting-ts) -> (ranking, truth_roles)
    for the vote check (the vote row's own truth_roles only covers colors the
    vote payload mentions — the snapshot's covers the whole ranking)."""
    snaps = read_belief(con, wh, "belief_suspicion_snapshot")
    index: dict[tuple[str, int, int], tuple[list[dict], dict]] = {}
    for ep, slot, ts, role, v in snaps:
        if normalize_role(v.get("role")) != "crew":
            continue  # imposter snapshots are deflection views, not genuine belief
        ranking = v.get("ranking") or []
        truth = v.get("truth_roles", {})
        index[(ep, slot, ts)] = (ranking, truth)
        imposter_ps = [e.get("p") or 0.0 for e in ranking
                       if truth.get(str(e.get("color", "")).lower()) == "imposter"]
        ranked_colors = {str(e.get("color", "")).lower() for e in ranking}
        # Full-roster truth (not mention-scoped), imposters still ALIVE at the
        # snapshot — a dead imposter legitimately drops out of the ranking.
        live_imposters = {
            c for c, r in truth_roles_by_ep.get(ep, {}).items()
            if r == "imposter" and truth_deaths.get((ep, c), 1 << 60) > ts
        }
        if ranking:
            top = ranking[0]
            top_color = str(top.get("color", "")).lower()
            top_p = top.get("p") or 0.0
            if truth.get(top_color) == "crew" and top_p >= confident_bar and imposter_ps:
                scan.add(ep, slot, ts, role, "ranking_top_crew", "high", {
                    "top_color": top_color, "top_p": top_p,
                    "best_imposter_p": max(imposter_ps),
                })
        missing = live_imposters - ranked_colors
        if missing:
            scan.add(ep, slot, ts, role, "imposter_unranked", "medium",
                     {"missing_imposters": sorted(missing), "ranked_n": len(ranking)})
    return len(snaps), index


def scan_deaths(con, wh: Path, scan: Scan, lag_tol: int,
                truth_roles_by_ep: dict[str, dict[str, str]],
                truth_deaths: dict[tuple[str, str], int]) -> None:
    """Belief player_died vs the replay kill/died timeline, per (episode, color)."""
    for ep, slot, ts, role, v in read_belief(con, wh, "belief_player_died"):
        color = str(v.get("color") or "").lower()
        if color not in truth_roles_by_ep.get(ep, {}):
            continue  # not a real color in this episode
        t_true = truth_deaths.get((ep, color))
        believed_at = v.get("death_tick") or ts
        if t_true is None:
            scan.add(ep, slot, ts, role, "phantom_death", "high",
                     {"color": color, "believed_death_tick": believed_at, "source": v.get("source")})
        elif believed_at - t_true > lag_tol:
            scan.add(ep, slot, ts, role, "death_belief_lag", "low", {
                "color": color, "true_death_ts": t_true,
                "believed_death_tick": believed_at, "lag_ticks": believed_at - t_true,
                "source": v.get("source"),
            })


def scan_votes(con, wh: Path, scan: Scan,
               snapshot_index: dict[tuple[str, int, int], list[dict]]) -> None:
    """Voted truly-crew while own same-meeting ranking had a true imposter at >= that p."""
    votes = read_belief(con, wh, "belief_meeting_vote_selected")
    snap_ts_by_seat: dict[tuple[str, int], list[int]] = {}
    for ep, slot, ts in snapshot_index:
        snap_ts_by_seat.setdefault((ep, slot), []).append(ts)
    for ep, slot, ts, role, v in votes:
        if normalize_role(role) != "crew":
            continue
        target = str(v.get("target") or "").lower()
        truth = v.get("truth_roles", {})
        if truth.get(target) != "crew":
            continue
        candidates = snap_ts_by_seat.get((ep, slot), [])
        prior = [s for s in candidates if s <= ts]
        if not prior:
            continue
        ranking, snap_truth = snapshot_index[(ep, slot, max(prior))]
        target_p = next((e.get("p") or 0.0 for e in ranking
                         if str(e.get("color", "")).lower() == target), None)
        imp = [(str(e.get("color", "")).lower(), e.get("p") or 0.0) for e in ranking
               if snap_truth.get(str(e.get("color", "")).lower()) == "imposter"]
        best_imp = max(imp, key=lambda x: x[1], default=None)
        if best_imp and target_p is not None and best_imp[1] >= target_p:
            scan.add(ep, slot, ts, role, "vote_crew_over_imposter", "high", {
                "voted": target, "voted_p": target_p,
                "imposter": best_imp[0], "imposter_p": best_imp[1],
                "reason": v.get("reason"),
            })


def scan_role_and_sync(con, wh: Path, scan: Scan) -> None:
    for ep, slot, ts, role, v in read_belief(con, wh, "belief_role_resolved"):
        believed = normalize_role(v.get("role"))
        truth = normalize_role(role)  # the seat's warehouse ground-truth role
        if believed and truth and believed not in (truth, "dead") and truth != "dead":
            scan.add(ep, slot, ts, role, "role_mismatch", "high",
                     {"believed_role": v.get("role"), "true_role": role})
    report = wh / "belief_sync_report.json"
    if report.exists():
        for r in json.loads(report.read_text()):
            if not r.get("sync_ok"):
                scan.add(r["episode_id"], r["slot"], 0, None, "clock_desync", "medium",
                         {"phase_offset_ticks": r.get("phase_offset_ticks")})


# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--warehouse", type=Path, required=True,
                    help="Warehouse extended by build_belief_log.py.")
    ap.add_argument("--out", type=Path, default=None,
                    help="JSONL output path (default <warehouse>/belief_divergences.jsonl).")
    ap.add_argument("--confident-bar", type=float, default=DEFAULT_CONFIDENT_BAR)
    ap.add_argument("--death-lag-tol", type=int, default=DEFAULT_DEATH_LAG_TOL)
    args = ap.parse_args(argv)
    wh = args.warehouse
    out = args.out or (wh / "belief_divergences.jsonl")

    if not part_exists(wh, "belief_suspicion_snapshot") and not part_exists(wh, "belief_role_resolved"):
        print("no belief_* partitions in this warehouse — run build_belief_log.py first", file=sys.stderr)
        return 1

    con = connect(wh)
    scan = Scan()

    truth_roles_by_ep, truth_deaths = ground_truth_maps(con, wh)
    scan_confirmed_and_believed(con, wh, scan)
    scan_teammates(con, wh, scan)
    n_snapshots, snapshot_index = scan_rankings(con, wh, scan, args.confident_bar,
                                                truth_roles_by_ep, truth_deaths)
    scan_deaths(con, wh, scan, args.death_lag_tol, truth_roles_by_ep, truth_deaths)
    scan_votes(con, wh, scan, snapshot_index)
    scan_role_and_sync(con, wh, scan)

    # denominators for rates
    seats = q(con, f"SELECT count(DISTINCT episode_id || '/' || slot) "
                   f"FROM read_parquet('{events_glob(wh, 'belief_role_resolved')}')") \
        if part_exists(wh, "belief_role_resolved") else [(0,)]
    n_seats = seats[0][0] or 1

    with out.open("w") as f:
        for row in sorted(scan.rows, key=lambda r: (r["kind"], r["episode_id"], r["ts"])):
            f.write(json.dumps(row) + "\n")

    print(f"scanned {n_seats} seats, {n_snapshots} meeting snapshots -> "
          f"{len(scan.rows)} divergences -> {out}\n")
    print(f"{'kind':<26} {'role':<10} {'count':>6} {'per-seat':>9}")
    for (kind, role), n in sorted(scan.counts.items(), key=lambda kv: -kv[1]):
        print(f"{kind:<26} {role:<10} {n:>6} {n / n_seats:>9.3f}")

    # worst examples: highest-severity kinds first, 3 each
    by_kind: dict[str, list[dict]] = {}
    for r in scan.rows:
        by_kind.setdefault(r["kind"], []).append(r)
    print("\nexamples:")
    for kind in sorted(by_kind, key=lambda k: ({"high": 0, "medium": 1, "low": 2}
                                               [by_kind[k][0]["severity"]], k)):
        for r in by_kind[kind][:3]:
            print(f"  {kind}: {r['episode_id']} slot {r['slot']} t={r['ts']} {json.dumps(r['detail'])[:140]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
