"""crewrift-belief-audit scripts — build_belief_log.py + scan_divergences.py.

Contract: build_belief_log extracts crewborg's belief-relevant domain.* trace
events from policy-artifact zips, enriches each with ground-truth roles for
every color mentioned (from the warehouse player_manifest), verifies the
belief clock against the replay phase timeline, and writes native belief_*
warehouse partitions. scan_divergences then reads ONLY the warehouse (never
the zips) and flags belief-vs-truth divergences with the documented kinds.

The fixture is one synthetic episode: crewborg (slot 0, red, crew) with
- a confirmed-imposter event naming a truly-CREW color   -> confirmed_crew
- a meeting ranking topping that crew color at p=0.9
  while the true imposter sits lower                     -> ranking_top_crew
- a vote for the crew color                              -> vote_crew_over_imposter
- a believed death the replay never shows                -> phantom_death
- aligned phase_change ticks                             -> sync_ok
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

SCRIPTS = Path(__file__).resolve().parents[1].parent / ".claude/skills/crewrift-belief-audit/scripts"
sys.path.insert(0, str(SCRIPTS))

from build_belief_log import EVENTS_SCHEMA, main as build_main  # noqa: E402
from scan_divergences import main as scan_main  # noqa: E402

EP = "ereq_deadbeef01"
# slot 0 = red (crewborg, crew), slot 1 = blue (crew), slot 2 = green (imposter)
MANIFEST = [
    (0, "red", "crew"), (1, "blue", "crew"), (2, "green", "imposter"),
]


def _write_events(wh: Path, key: str, rows: list[dict]) -> None:
    cols = {c: [] for c in ("ts", "episode_id", "slot", "policy_version",
                            "policy_name", "role", "key", "value")}
    for r in rows:
        cols["ts"].append(r["ts"])
        cols["episode_id"].append(EP)
        cols["slot"].append(r.get("slot", -1))
        cols["policy_version"].append(r.get("policy_version"))
        cols["policy_name"].append(r.get("policy_name"))
        cols["role"].append(r.get("role"))
        cols["key"].append(key)
        cols["value"].append(json.dumps(r["value"]))
    out = wh / "events" / f"key={key}"
    out.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(cols, schema=EVENTS_SCHEMA), out / f"{EP}.parquet")


def _make_warehouse(wh: Path) -> None:
    _write_events(wh, "player_manifest", [
        {"ts": 0, "slot": s, "role": role,
         "value": {"source": "replay", "label": f"{color}(P{s})", "color": color, "role": role}}
        for s, color, role in MANIFEST
    ])
    _write_events(wh, "phase", [
        {"ts": t, "value": {"source": "replay", "phase": p}}
        for t, p in [(0, "Lobby"), (100, "RoleReveal"), (200, "Playing"), (1000, "Voting")]
    ])
    # ground truth: green kills blue at t=900; no other deaths.
    _write_events(wh, "kill", [
        {"ts": 900, "slot": 2, "role": "imposter",
         "value": {"source": "replay", "victim_slot": 1, "victim_label": "blue(P1)"}},
    ])
    players = pa.table({
        "episode_id": [EP] * 3,
        "slot": pa.array([s for s, _, _ in MANIFEST], pa.int32()),
        "policy_version": ["pv0", "pv1", "pv2"],
        "policy_name": ["crewborg", "other", "other"],
        "role": [r for _, _, r in MANIFEST],
        "score": [1.0, 1.0, 1.0],
        "win": [False, False, True],
        "tasks": pa.array([3, 3, 0], pa.int32()),
        "kills": pa.array([0, 0, 1], pa.int32()),
        "identity_source": ["request.player_id"] * 3,
    })
    pq.write_table(players, wh / "episode_players.parquet")


def _telemetry_lines() -> list[str]:
    def tr(tick: int, event: str, data: dict) -> str:
        return json.dumps({"kind": "trace", "tick": tick, "event": event, "name": event, "data": data})

    return [
        tr(100, "domain.phase_change", {"from": "Lobby", "to": "RoleReveal"}),
        tr(102, "domain.role_resolved", {"role": "crewmate"}),
        tr(201, "domain.phase_change", {"from": "RoleReveal", "to": "Playing"}),
        # WRONG confirmed: blue is truly crew
        tr(500, "domain.imposter_confirmed", {"color": "blue", "p": 0.98}),
        # phantom death: belief says green died at 700; the replay has no such death
        tr(700, "domain.player_died", {"color": "green", "source": "body", "death_tick": 700, "body_xy": [1, 2]}),
        tr(1002, "domain.phase_change", {"from": "Playing", "to": "Voting"}),
        # meeting snapshot: crew color blue topped at 0.9, true imposter green at 0.4
        tr(1005, "domain.suspicion_snapshot", {
            "role": "crewmate", "prior": 0.28,
            "ranking": [{"color": "blue", "p": 0.9, "confirmed": True, "events": []},
                        {"color": "green", "p": 0.4, "confirmed": False, "events": []}],
            "confirmed": ["blue"], "believed": ["blue"],
            "would_vote": "blue", "would_vote_p": 0.9, "vote_bar": 0.5,
        }),
        tr(1050, "domain.meeting_vote_selected", {"target": "blue", "reason": "top_suspect"}),
        # second meeting: belief now ranks the TRUE imposter on top, but the vote
        # still goes to crew blue -> vote_crew_over_imposter (vote against own belief)
        tr(2005, "domain.suspicion_snapshot", {
            "role": "crewmate", "prior": 0.28,
            "ranking": [{"color": "green", "p": 0.9, "confirmed": False, "events": []},
                        {"color": "blue", "p": 0.85, "confirmed": False, "events": []}],
            "confirmed": [], "believed": ["green"],
            "would_vote": "green", "would_vote_p": 0.9, "vote_bar": 0.5,
        }),
        tr(2050, "domain.meeting_vote_selected", {"target": "blue", "reason": "llm_override"}),
        # metric line (no tick) must be skipped, not crash
        json.dumps({"kind": "metric", "metric_kind": "counter", "name": "vote_cast", "value": 1.0, "tags": {}}),
    ]


def _make_episode_dir(root: Path) -> None:
    d = root / f"20260728T000000_{EP}"
    (d / "artifacts").mkdir(parents=True)
    (d / "episode.json").write_text(json.dumps({
        "id": EP,
        "participants": [
            {"position": 0, "policy_name": "crewborg", "version": 116, "policy_version_id": "pv0"},
            {"position": 1, "policy_name": "other", "version": 1, "policy_version_id": "pv1"},
            {"position": 2, "policy_name": "other", "version": 1, "policy_version_id": "pv2"},
        ],
    }))
    (d / "results.json").write_text("{}")
    with zipfile.ZipFile(d / "artifacts" / "policy_artifact_0.zip", "w") as zf:
        zf.writestr("telemetry.jsonl", "\n".join(_telemetry_lines()) + "\n")


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    wh = tmp_path / "wh"
    eps = tmp_path / "eps"
    eps.mkdir()
    _make_warehouse(wh)
    _make_episode_dir(eps)
    return wh, eps


def test_build_writes_enriched_partitions_and_sync_report(tmp_path: Path) -> None:
    wh, eps = _setup(tmp_path)
    assert build_main(["--warehouse", str(wh), "--episodes", str(eps)]) == 0

    snap = pq.read_table(wh / "events/key=belief_suspicion_snapshot").to_pylist()
    assert len(snap) == 2  # one per fixture meeting
    row = min(snap, key=lambda r: r["ts"])
    assert row["episode_id"] == EP and row["slot"] == 0
    assert row["policy_name"] == "crewborg" and row["role"] == "crew"
    v = json.loads(row["value"])
    # enrichment: truth roles for every mentioned color + self identity
    assert v["truth_roles"]["blue"] == "crew" and v["truth_roles"]["green"] == "imposter"
    assert v["self_slot"] == 0 and v["self_color"] == "red"

    sync = json.loads((wh / "belief_sync_report.json").read_text())
    # phase offsets: RoleReveal 0, Playing 1, Voting 2 -> median 1
    assert sync == [{"episode_id": EP, "slot": 0, "phase_offset_ticks": 1, "sync_ok": True}]


def test_scan_flags_the_planted_divergences(tmp_path: Path) -> None:
    wh, eps = _setup(tmp_path)
    build_main(["--warehouse", str(wh), "--episodes", str(eps)])
    out = tmp_path / "div.jsonl"
    assert scan_main(["--warehouse", str(wh), "--out", str(out)]) == 0

    rows = [json.loads(line) for line in out.read_text().splitlines()]
    kinds = {r["kind"] for r in rows}
    assert kinds >= {"confirmed_crew", "ranking_top_crew", "vote_crew_over_imposter", "phantom_death"}

    confirmed = next(r for r in rows if r["kind"] == "confirmed_crew")
    assert confirmed["detail"]["color"] == "blue" and confirmed["severity"] == "high"

    top = next(r for r in rows if r["kind"] == "ranking_top_crew")
    assert top["detail"]["top_color"] == "blue" and top["detail"]["best_imposter_p"] == 0.4

    vote = next(r for r in rows if r["kind"] == "vote_crew_over_imposter")
    assert vote["detail"]["voted"] == "blue"

    phantom = next(r for r in rows if r["kind"] == "phantom_death")
    assert phantom["detail"]["color"] == "green"

    # true-positive guards: no role_mismatch (belief crewmate == truth crew),
    # no clock_desync (phases aligned), no death lag rows (blue's death unseen).
    assert not {"role_mismatch", "clock_desync", "death_belief_lag"} & kinds
