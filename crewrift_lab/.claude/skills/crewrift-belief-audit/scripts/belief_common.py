"""Shared plumbing for the crewrift-belief-audit scripts.

Joins two datasets that describe the same episodes:
  - the event warehouse (objective replay ground truth; DuckDB/Parquet), and
  - crewborg's own policy-artifact telemetry (subjective beliefs; telemetry.jsonl
    inside artifacts/policy_artifact_<slot>.zip in each fetched episode dir).

The join key is (episode_id, tick): telemetry `tick` is the SERVER tick (the
bridge reads the engine's tick-marker sprite — crewborg/docs/trace-logs.md), so
belief events align directly to warehouse `ts`. Identity is joined per episode
via color<->slot maps from the replay's `player_manifest` events (crewborg
speaks colors; the warehouse speaks slots).
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

EREQ = re.compile(r"ereq_[0-9a-f-]+")

# Belief-relevant domain.* events extracted by default. decision_snapshot /
# suspicion_tick / viewer_* / meeting_context_serialized are deliberately out
# (huge; add via --include if a dig needs them).
BELIEF_EVENTS = (
    "domain.phase_change",
    "domain.role_resolved",
    "domain.teammate_belief_changed",
    "domain.body_sighted",
    "domain.player_died",
    "domain.player_event",
    "domain.imposter_confirmed",
    "domain.believed_changed",
    "domain.suspicion_snapshot",
    "domain.meeting_decision",
    "domain.meeting_vote_selected",
    "domain.meeting_chat_selected",
    "domain.meeting_llm_decision",
    "domain.meeting_llm_fallback",
    "domain.chat_sent",
    "domain.chat_received",
    "domain.vote_cast",
    "domain.kill_attempted",
    "domain.kill_landed",
    "domain.report_attempted",
    "domain.vent_attempted",
    "domain.task_started",
    "domain.task_completed",
    "domain.chat_evidence_applied",
    "domain.honor_claim",
    "domain.honor_known_member",
    "domain.honor_liar",
    "domain.honor_distrusted_announce",
    "domain.occupancy_reacquired",
)


def belief_key(event_name: str) -> str:
    """domain.suspicion_snapshot -> belief_suspicion_snapshot (the warehouse partition key)."""
    return "belief_" + event_name.removeprefix("domain.")


def events_glob(warehouse: Path, key: str) -> str:
    return str(warehouse / "events" / f"key={key}" / "*.parquet")


def connect(warehouse: Path) -> duckdb.DuckDBPyConnection:
    return duckdb.connect()


def normalize_role(role: str | None) -> str | None:
    """'crewmate' (crewborg) and 'crew' (replay/results) are the same role."""
    if role is None:
        return None
    return "crew" if role in ("crew", "crewmate") else role


# ---------------------------------------------------------------------------
# Ground-truth identity: color <-> slot <-> role per episode
# ---------------------------------------------------------------------------


@dataclass
class EpisodeIdentity:
    color_to_slot: dict[str, int] = field(default_factory=dict)
    slot_to_color: dict[int, str] = field(default_factory=dict)
    slot_role: dict[int, str] = field(default_factory=dict)  # normalized: crew/imposter

    @property
    def true_imposter_colors(self) -> set[str]:
        return {c for c, s in self.color_to_slot.items() if self.slot_role.get(s) == "imposter"}


def episode_identities(con: duckdb.DuckDBPyConnection, warehouse: Path) -> dict[str, EpisodeIdentity]:
    """Per-episode color/slot/role maps from the replay's player_manifest events
    (value.color + value.role are ground truth; source='replay' rows only —
    the reporter variant has neither)."""
    import glob as _glob

    if not _glob.glob(events_glob(warehouse, "player_manifest")):
        return {}
    rows = con.execute(
        f"SELECT episode_id, slot, "
        f"  lower(json_extract_string(value,'$.color')) AS color, "
        f"  json_extract_string(value,'$.role') AS role "
        f"FROM read_parquet('{events_glob(warehouse, 'player_manifest')}') "
        f"WHERE json_extract_string(value,'$.source') = 'replay' AND slot >= 0"
    ).fetchall()
    out: dict[str, EpisodeIdentity] = {}
    for ep, slot, color, role in rows:
        ident = out.setdefault(ep, EpisodeIdentity())
        if color:
            ident.color_to_slot[color] = slot
            ident.slot_to_color[slot] = color
        ident.slot_role[slot] = normalize_role(role)
    return out


# ---------------------------------------------------------------------------
# Subject (crewborg) seats + their artifact telemetry
# ---------------------------------------------------------------------------


@dataclass
class SubjectSeat:
    episode_id: str
    slot: int
    policy_name: str
    policy_version: str | None
    role: str | None  # warehouse ground-truth role for the seat
    zip_path: Path


def subject_slots(
    con: duckdb.DuckDBPyConnection, warehouse: Path, policies: set[str]
) -> dict[str, list[tuple[int, str, str | None, str | None]]]:
    """{episode_id: [(slot, policy_name, policy_version, role)]} for the subject policies,
    from the warehouse's episode_players dimension (identity already resolved)."""
    rows = con.execute(
        f"SELECT episode_id, slot, policy_name, policy_version, role "
        f"FROM read_parquet('{warehouse}/episode_players.parquet')"
    ).fetchall()
    out: dict[str, list[tuple[int, str, str | None, str | None]]] = {}
    for ep, slot, name, version, role in rows:
        if name in policies:
            out.setdefault(ep, []).append((slot, name, version, normalize_role(role)))
    return out


def episode_dirs_by_id(episodes_root: Path) -> dict[str, Path]:
    """Map warehouse episode_id -> fetched episode dir. The id is episode.json's
    `id`; fall back to the ereq_… key embedded in the dir name."""
    out: dict[str, Path] = {}
    if not episodes_root.is_dir():
        return out
    for d in sorted(episodes_root.iterdir()):
        if not d.is_dir():
            continue
        eid = None
        ep_json = d / "episode.json"
        if ep_json.exists():
            try:
                eid = json.loads(ep_json.read_text()).get("id")
            except (OSError, json.JSONDecodeError):
                eid = None
        if not eid:
            m = EREQ.search(d.name)
            eid = m.group(0) if m else None
        if eid:
            out[eid] = d
    return out


def find_subject_seats(
    warehouse: Path, episodes_root: Path, policies: set[str], stats: Counter | None = None
) -> list[SubjectSeat]:
    """Every (episode, slot) seat of a subject policy that has a policy-artifact zip."""
    st = stats if stats is not None else Counter()
    con = connect(warehouse)
    slots = subject_slots(con, warehouse, policies)
    dirs = episode_dirs_by_id(episodes_root)
    seats: list[SubjectSeat] = []
    for ep, entries in sorted(slots.items()):
        d = dirs.get(ep)
        if d is None:
            st["no_episode_dir"] += 1
            continue
        for slot, name, version, role in entries:
            zp = d / "artifacts" / f"policy_artifact_{slot}.zip"
            if not zp.exists():
                st["no_artifact_zip"] += 1
                continue
            seats.append(SubjectSeat(ep, slot, name, version, role, zp))
            st["seats"] += 1
    return seats


def iter_telemetry(zip_path: Path, events: set[str] | None = None):
    """Yield (tick, event_name, data) trace lines from a policy artifact zip.
    Metric lines (no tick/event) are skipped; `events`=None yields every trace event."""
    with zipfile.ZipFile(zip_path) as zf:
        if "telemetry.jsonl" not in zf.namelist():
            return
        with zf.open("telemetry.jsonl") as f:
            for line in io.TextIOWrapper(f, errors="replace"):
                if not line.startswith("{"):
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                name = rec.get("event") or rec.get("name")
                tick = rec.get("tick")
                if name is None or tick is None:
                    continue  # metric line or malformed
                if events is not None and name not in events:
                    continue
                yield int(tick), name, rec.get("data") or {}
