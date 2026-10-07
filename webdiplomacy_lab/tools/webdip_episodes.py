"""Load downloaded webDiplomacy episodes into per-seat records (the lab's one parser).

Input: directories written by the root `coworld-episode-artifacts` fetcher (one per
episode: episode.json, results.json, replay.json, logs/policy_agent_<slot>.log) or by
`coworld run-episode` (results.json, replay, logs/). Every seat becomes one `Seat`
record keyed by its power, because country assignment is random per episode and the
seven powers differ a lot in strength: always stratify by `power`.

Format facts (webdiplomacy 0.7.7, verified on hosted + local artifacts):
- results.json: `scores`/`countries` are slot-ordered; `members[].countryID` is a
  string; `outcome` is drawn|won|cancelled with `reason` (end_year, ...).
- replay: JSON array of public frames; the last frame's `history.phases[]` has per-phase
  `units`, `centers` (all owned territories, not only supply centres) and adjudicated
  `orders` with `success`/`dislodged`. Its final `Finished` entry shows stale
  (pre-final-autumn) centre ownership; results.json `members` is authoritative.
- hosted seat logs can arrive as a Python bytes literal (`b'...'`); decoded here.
"""

from __future__ import annotations

import ast
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

POWERS = {1: "England", 2: "France", 3: "Italy", 4: "Germany", 5: "Austria", 6: "Turkey", 7: "Russia"}
SOLO_CENTERS = 18


@dataclass
class Seat:
    episode_id: str
    slot: int
    policy: str  # "name:vN" (hosted) or "local"
    power: str
    score: float
    final_centers: int | None
    survived: bool | None
    solo: bool
    outcome: str
    final_year: int | None
    centers_by_year: dict[int, int] = field(default_factory=dict)  # after each autumn
    orders: int = 0
    orders_failed: int = 0  # adjudicated unsuccessful (bounced/cut), from public history
    dislodged: int = 0
    log: dict = field(default_factory=dict)  # our policy's telemetry, when the seat log exists


def read_log(path: Path) -> list[dict]:
    if not path.exists():
        return []
    text = path.read_text(errors="replace")
    if text.startswith(("b'", 'b"')):
        text = ast.literal_eval(text).decode(errors="replace")
    rows = []
    for line in text.splitlines():
        if line.startswith("{"):
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    return rows


def summarize_log(rows: list[dict]) -> dict:
    """Aggregate our bot's stdout telemetry (decision events + activation counters)."""
    decisions = [r for r in rows if r.get("event") == "decision"]
    legacy = [r for r in rows if r.get("event") == "orders_saved"]  # bundled random bot
    trace = Counter()
    for d in decisions:
        trace.update(d.get("trace") or {})
    return {
        "decisions": len(decisions) or len(legacy),
        "rejected": sum(d.get("rejected", 0) for d in decisions + legacy),
        "exceptions": sum(r.get("event") == "exception" for r in rows),
        "http_errors": sum(r.get("event") == "http_error" for r in rows),
        "max_compute_ms": max((d.get("compute_ms", 0) for d in decisions), default=None),
        "trace": dict(trace),
    }


def _replay(ep: Path) -> list | None:
    for name in ("replay.json", "replay"):
        p = ep / name
        if p.exists():
            try:
                return json.loads(p.read_text())
            except ValueError:
                return None
    return None


def _policies(episode: dict) -> dict[int, str]:
    out = {}
    for p in episode.get("participants") or []:
        out[p["position"]] = f'{p.get("policy_name")}:v{p.get("version")}'
    for p in episode.get("policy_results") or []:
        pol = p.get("policy") or {}
        out[p["position"]] = f'{pol.get("name")}:v{pol.get("version")}'
    return out


def load_episode(ep: Path) -> tuple[list[Seat], dict]:
    """Return (seats, status) for one episode directory. status records coverage gaps."""
    episode = json.loads((ep / "episode.json").read_text()) if (ep / "episode.json").exists() else {}
    status = {"dir": ep.name, "episode_status": episode.get("status", "local"), "missing": []}
    if not (ep / "results.json").exists():
        status["missing"].append("results")
        return [], status
    results = json.loads((ep / "results.json").read_text())
    replay = _replay(ep)
    if replay is None:
        status["missing"].append("replay")
    eid = episode.get("id") or ep.name
    policies = _policies(episode)
    members = {int(m["countryID"]): m for m in results.get("members") or []}
    final_turn = (results.get("final_state") or {}).get("turn")
    # Year of the last completed autumn: play can stop at autumn (turn 19) or be observed
    # one phase later in the next spring (turn 20); both mean 1910 was the last year.
    final_year = 1901 + (int(final_turn) - 1) // 2 if final_turn is not None else None
    outcome = results.get("outcome", "")

    history = replay[-1]["history"]["phases"] if replay else []
    supply = set()
    if replay:
        supply = {t["id"] for t in replay[-1]["variant"]["territories"] if t["supply"] and t["coast"] != "Child"}
    centers_by_year: dict[int, Counter] = {}
    order_stats: dict[int, Counter] = {}
    for ph in history:
        if ph["phase"] == "Diplomacy":
            for o in ph.get("orders") or []:
                c = order_stats.setdefault(o["countryID"], Counter())
                c["orders"] += 1
                c["failed"] += o["type"] != "Hold" and not o.get("success")
                c["dislodged"] += bool(o.get("dislodged"))
        # Ownership changes at the end of each autumn. The phase entries that show the
        # post-autumn position are that winter's Builds or the next spring's Diplomacy.
        # The final "Finished" entry still shows the PRE-final-autumn ownership (verified
        # 0.7.7), so the final year comes from results.members instead (below).
        turn, phase = ph["turn"], ph["phase"]
        if phase == "Builds":
            year = 1901 + turn // 2
        elif phase == "Diplomacy" and turn % 2 == 0 and turn > 0:
            year = 1901 + turn // 2 - 1
        else:
            continue
        centers_by_year[year] = Counter(c["countryID"] for c in ph.get("centers") or [] if c["terrID"] in supply)

    seats = []
    for slot, country in enumerate(results.get("countries") or []):
        country = int(country)
        member = members.get(country, {})
        finals = int(member["supplyCenterNo"]) if "supplyCenterNo" in member else None
        score = (results.get("scores") or [None] * 7)[slot]
        stats = order_stats.get(country, Counter())
        seat = Seat(
            episode_id=eid,
            slot=slot,
            policy=policies.get(slot, "local"),
            power=POWERS[country],
            score=float(score) if score is not None else 0.0,
            final_centers=finals,
            survived=(finals > 0) if finals is not None else None,
            solo=outcome == "won" and (finals or 0) >= SOLO_CENTERS,
            outcome=outcome,
            final_year=final_year,
            centers_by_year={
                **{y: c.get(country, 0) for y, c in sorted(centers_by_year.items())},
                **({final_year: finals} if final_year and finals is not None else {}),
            },
            orders=stats["orders"],
            orders_failed=stats["failed"],
            dislodged=stats["dislodged"],
        )
        log_rows = read_log(ep / "logs" / f"policy_agent_{slot}.log")
        if log_rows:
            seat.log = summarize_log(log_rows)
        seats.append(seat)
    return seats, status


def load_dirs(roots: list[Path]) -> tuple[list[Seat], list[dict]]:
    seats, statuses = [], []
    for root in roots:
        eps = [root] if (root / "results.json").exists() or (root / "episode.json").exists() else sorted(
            p for p in root.iterdir() if p.is_dir()
        )
        for ep in eps:
            s, st = load_episode(ep)
            seats.extend(s)
            statuses.append(st)
    return seats, statuses
