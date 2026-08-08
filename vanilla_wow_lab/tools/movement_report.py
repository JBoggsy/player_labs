#!/usr/bin/env python3
"""Score a replay's client-side movement stream for continuity.

The question this answers: **does the character walk in continuous spans, or does it
stop and restart at every corridor boundary?** Before the environment-owned forward
continuation (game PR #7391), wowborg's executor emitted a fresh
`MSG_MOVE_START_FORWARD` / `MSG_MOVE_STOP` pair per corridor segment, so a single
journey cost hundreds of start/stop pairs and thousands of heartbeats. After it, one
journey should be one start, a run of heartbeats, and one stop.

Metrics come from the member's own **outbound** packets, which are plaintext in the
replay (see `cwreplay._movement_info`) — no stateful client reducer needed.

A second, independent instrument is the policy's own `WOWBORG-TRACE` stream in
`logs/policy_agent_N.log`: it carries what the policy *asked* for (move actions), what
the game said back (movement failures), and how often a submission lost the frame race
(stale-frame rejections). Pass an episode directory to score both at once.

On Vanilla WoW 0.1.208+, `game_logs.log` adds the environment-owned side: host
stall/rejection/detachment counters, death/ghost and terminal scoring-stop classification, and the exact
same-waypoint route-bearing disappearance signature. The episode-artifact downloader
retains this combined log automatically.

Usage:

    uv run python vanilla_wow_lab/tools/movement_report.py EPISODE_DIR_OR_REPLAY ...
    uv run python vanilla_wow_lab/tools/movement_report.py NEW_DIR --baseline OLD_DIR
    uv run python vanilla_wow_lab/tools/movement_report.py EPISODE_DIR --json
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cwreplay import MOVE_OPCODES_CLIENT, Replay, _movement_info, decode_replay

# Vanilla 1.12.1 client movement opcodes (see docs/recon/navigation-obs-actions-2026-07-14.md).
START_FORWARD = 181
START_BACKWARD = 182
STOP = 183
START_TURN_LEFT = 188
START_TURN_RIGHT = 189
STOP_TURN = 190
HEARTBEAT = 238

TURN_STARTS = (START_TURN_LEFT, START_TURN_RIGHT)

# MovementInfo flag bits (VMaNGOS 1.12). A falling character ignores forward input
# horizontally, so a high falling share explains "start_forward is flowing but x/y never
# changes" — the accelerated-wow 0.1.146 failure, where it was 100% against a 3.8% baseline.
MOVEFLAG_FALLING = 0x00002000

# A STOP is "boundary-only" when forward motion resumes afterwards and the character
# went nowhere in between: it halted, stood still, and started again, so the stop was
# pure executor overhead rather than an arrival.
#
# Displacement, not timing, is the discriminator. On the v59/0.1.124 baseline
# (ereq_422085f1) the pause *durations* span 3-91 s, but the displacement across every
# one of the 239 pauses is under 0.9 yd — the character never repositioned while
# stopped. 1.0 yd sits above that observed ceiling and far below any real move.
BOUNDARY_STOP_MAX_DISPLACEMENT_YARDS = 1.0


@dataclass
class MovementReport:
    """Movement-continuity metrics for one member of one replay."""

    replay: str
    member: str
    movement_packets: int = 0
    forward_starts: int = 0
    forward_stops: int = 0
    turn_starts: int = 0
    turn_stops: int = 0
    heartbeats: int = 0
    other_movement: int = 0
    falling_packets: int = 0
    trajectory_yards: float = 0.0
    forward_spans: int = 0
    boundary_only_stops: int = 0
    terminal_boundary_only_stops: int = -1
    life_state_boundary_only_stops: int = -1
    nonterminal_boundary_only_stops: int = -1
    turn_runs: int = 0
    short_turn_runs: int = 0
    direct_turn_reversals: int = 0
    route_bearing_disappearances: int = -1
    longest_span_ms: int = 0
    longest_span_heartbeats: int = 0
    unterminated_final_span: bool = False
    span_heartbeats: list[int] = field(default_factory=list, repr=False)

    # From the policy's own WOWBORG-TRACE log, when one is available (-1 = not read).
    move_actions: int = -1
    movement_failures: int = -1
    stale_frame_rejections: int = -1
    observations: int = -1
    progress_reports: int = -1
    failure_details: dict[str, int] = field(default_factory=dict, repr=False)
    host_stalls: int = -1
    host_rejected_requests: int = -1
    host_detached_frames: int = -1
    host_event_counts: dict[str, int] = field(default_factory=dict, repr=False)
    boundary_stop_times: list[int] = field(default_factory=list, repr=False)
    life_state_boundary_stop_times: list[int] = field(default_factory=list, repr=False)
    boundary_stop_records: list[dict[str, float | int]] = field(default_factory=list, repr=False)

    @property
    def falling_percent(self) -> float:
        """Share of movement packets flagged FALLING.

        The absolute count misleads: 0.1.146 sent FEWER falling packets than the baseline in
        total, but 100% of its movement was falling versus the baseline's 3.8%.
        """
        if not self.movement_packets:
            return 0.0
        return round(self.falling_packets / self.movement_packets * 100, 1)

    @property
    def continuous_prefix(self) -> bool:
        """True when the stream reads as intentional journeys, not per-segment churn.

        The bar from the retest plan: one initial start, no boundary-only stops, and
        one final stop per journey — i.e. every forward span is closed by a stop the
        policy meant to send.
        """
        effective_stops = (
            self.nonterminal_boundary_only_stops
            if self.nonterminal_boundary_only_stops >= 0
            else self.boundary_only_stops
        )
        return self.forward_starts > 0 and effective_stops == 0


def report_episode(path: Path) -> list[MovementReport]:
    """Score an episode directory (replay + policy log) or a bare replay file."""
    if path.is_dir():
        replay_path = path / "replay.json"
        if not replay_path.exists():
            raise SystemExit(f"{path}: no replay.json in episode directory")
        reports = report_replay(replay_path)
        for report in reports:
            report.replay = path.name
        log_path = next(iter(sorted((path / "logs").glob("policy_agent_*.log"))), None)
        if log_path is not None and reports:
            _add_log_metrics(reports[0], log_path)
        game_log_path = path / "game_logs.log"
        if game_log_path.exists() and reports:
            _add_host_metrics(reports[0], game_log_path)
        return reports
    return report_replay(path)


def report_replay(path: Path) -> list[MovementReport]:
    replay: Replay = decode_replay(path)
    return [_report_member(path, member) for member in replay.members]


def _read_trace(log_path: Path) -> list[dict]:
    """Parse the WOWBORG-TRACE JSONL records out of a policy log.

    The platform stores the log as a Python `bytes` repr (a single line with escaped
    newlines), so unwrap that before splitting when present.
    """
    raw = log_path.read_text()
    stripped = raw.lstrip()
    if stripped.startswith(("b'", 'b"')):
        raw = ast.literal_eval(stripped).decode("utf-8", "replace")
    records = []
    for line in raw.splitlines():
        if "WOWBORG-TRACE " not in line:
            continue
        try:
            records.append(json.loads(line.split("WOWBORG-TRACE ", 1)[1]))
        except json.JSONDecodeError:
            continue
    return records


def _add_log_metrics(report: MovementReport, log_path: Path) -> None:
    records = _read_trace(log_path)
    if not records:
        return
    movement_kinds = {"move", "move_to", "move_vector"}
    move_outcomes = [
        r
        for r in records
        if r.get("kind") == "outcome" and r.get("action_kind") in movement_kinds
    ]
    failures = [r for r in move_outcomes if not r.get("success")]
    report.move_actions = sum(
        1
        for r in records
        if r.get("kind") == "intent"
        and (r.get("action") or {}).get("kind") in movement_kinds
    )
    report.movement_failures = len(failures)
    report.stale_frame_rejections = sum(1 for r in records if r.get("kind") == "frame_refresh")
    report.observations = sum(1 for r in records if r.get("kind") == "observation")
    report.progress_reports = sum(1 for r in records if r.get("kind") == "player_progress")
    life_observations = [
        row
        for row in records
        if row.get("kind") == "observation" and (row.get("is_dead") or row.get("is_ghost"))
    ]
    report.life_state_boundary_stop_times = [
        int(stop["movement_time_ms"])
        for stop in report.boundary_stop_records
        if any(
            0 <= float(observation.get("ts", 0)) - float(stop["unix_s"]) <= 10
            and isinstance(observation.get("position"), list)
            and len(observation["position"]) >= 2
            and (
                (float(observation["position"][0]) - float(stop["x"])) ** 2
                + (float(observation["position"][1]) - float(stop["y"])) ** 2
            # The death packet can precede the next policy Observation while the
            # client finishes a few yards of already-issued movement.
            ) ** 0.5 <= 10.0
            for observation in life_observations
        )
    ]
    report.life_state_boundary_only_stops = len(report.life_state_boundary_stop_times)
    details: dict[str, int] = {}
    for failure in failures:
        key = (failure.get("detail") or "<no detail>")[:70]
        details[key] = details.get(key, 0) + 1
    report.failure_details = details


def _decoded_container_log(path: Path) -> str:
    """Expand the platform's per-container Python bytes reprs into real lines."""
    chunks: list[str] = []
    for line in path.read_text(errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith(("b'", 'b"')):
            try:
                chunks.append(ast.literal_eval(stripped).decode("utf-8", "replace"))
                continue
            except (SyntaxError, ValueError):
                pass
        chunks.append(line)
    return "\n".join(chunks)


def _host_trace(path: Path) -> list[dict]:
    marker = "Environment host telemetry "
    records: list[dict] = []
    for line in _decoded_container_log(path).splitlines():
        if marker not in line:
            continue
        try:
            record = json.loads(line.split(marker, 1)[1])
        except json.JSONDecodeError:
            continue
        if record.get("protocol") == "vanilla_wow.environment_host_trace":
            records.append(record)
    return sorted(records, key=lambda row: int(row.get("trace_sequence", 0)))


def _add_host_metrics(report: MovementReport, log_path: Path) -> None:
    events = _host_trace(log_path)
    if not events:
        return
    report.host_event_counts = dict(Counter(str(row.get("event")) for row in events))
    telemetry = events[-1].get("telemetry") or {}
    report.host_stalls = int(telemetry.get("stalls", 0))
    report.host_rejected_requests = int(telemetry.get("rejected_requests", 0))
    report.host_detached_frames = int(telemetry.get("detached_frames", 0))

    admissions = [int(row.get("trace_sequence", 0)) for row in events
                  if row.get("event") == "action_admitted"]
    last_admission = max(admissions, default=-1)
    scoring_closes = [int(row.get("trace_sequence", 0)) for row in events
                      if row.get("event") == "closed" and row.get("reason") == "scoring_logout"]
    stop_transitions = {
        int(details["movement_time_ms"]): int(row.get("trace_sequence", 0))
        for row in events
        if row.get("event") == "movement_control_transition"
        and (details := row.get("details") or {}).get("forward_was_held") is True
        and details.get("forward_held") is False
        and isinstance(details.get("movement_time_ms"), int)
    }
    terminal_times: set[int] = set()
    for movement_time in report.boundary_stop_times:
        sequence = stop_transitions.get(movement_time)
        if sequence is not None and sequence > last_admission and any(
            close_sequence > sequence for close_sequence in scoring_closes
        ):
            terminal_times.add(movement_time)
    life_state_times = set(report.life_state_boundary_stop_times) - terminal_times
    report.terminal_boundary_only_stops = len(terminal_times)
    report.life_state_boundary_only_stops = len(life_state_times)
    report.nonterminal_boundary_only_stops = (
        report.boundary_only_stops - len(terminal_times | life_state_times)
    )

    transitions = [row for row in events if row.get("event") == "movement_control_transition"]
    disappearances = 0
    for first, second in zip(transitions, transitions[1:]):
        a = first.get("details") or {}
        b = second.get("details") or {}
        if (
            a.get("opcode_id") in TURN_STARTS
            and b.get("opcode_id") == STOP_TURN
            and a.get("route_bearing_known") is True
            and b.get("route_bearing_known") is False
            and a.get("waypoint_index") == b.get("waypoint_index")
            and isinstance(a.get("movement_time_ms"), int)
            and isinstance(b.get("movement_time_ms"), int)
            and ((b["movement_time_ms"] - a["movement_time_ms"]) & 0xFFFFFFFF) <= 100
        ):
            disappearances += 1
    report.route_bearing_disappearances = disappearances


def _report_member(path: Path, member) -> MovementReport:
    report = MovementReport(replay=path.name, member=member.name)
    previous_xy: tuple[float, float] | None = None

    # Forward-span state: when a START_FORWARD opens a span we accumulate until its STOP.
    span_open_ms: int | None = None
    span_heartbeats = 0
    # Position at the last STOP, held until forward motion resumes, so we can tell a
    # stand-still restart (boundary-only) from a stop the character moved away from.
    stop_xy: tuple[float, float] | None = None
    stop_movement_time: int | None = None
    stop_record: dict[str, float | int] | None = None
    active_turn: int | None = None
    turn_started_at: int | None = None

    for packet in member.packets:
        if not packet.from_client or packet.opcode not in MOVE_OPCODES_CLIENT:
            continue
        report.movement_packets += 1

        info = _movement_info(packet)
        if info is not None:
            if info["move_flags"] & MOVEFLAG_FALLING:
                report.falling_packets += 1
            if previous_xy is not None:
                report.trajectory_yards += (
                    (info["x"] - previous_xy[0]) ** 2
                    + (info["y"] - previous_xy[1]) ** 2
                ) ** 0.5
            previous_xy = (info["x"], info["y"])

        opcode = packet.opcode
        if opcode == START_FORWARD:
            report.forward_starts += 1
            if stop_xy is not None and previous_xy is not None:
                travelled_while_stopped = (
                    (previous_xy[0] - stop_xy[0]) ** 2
                    + (previous_xy[1] - stop_xy[1]) ** 2
                ) ** 0.5
                if travelled_while_stopped <= BOUNDARY_STOP_MAX_DISPLACEMENT_YARDS:
                    report.boundary_only_stops += 1
                    if stop_movement_time is not None:
                        report.boundary_stop_times.append(stop_movement_time)
                    if stop_record is not None:
                        report.boundary_stop_records.append(stop_record)
            stop_xy = None
            stop_movement_time = None
            stop_record = None
            span_open_ms = packet.server_ms
            span_heartbeats = 0
        elif opcode == STOP:
            report.forward_stops += 1
            stop_xy = previous_xy
            stop_movement_time = None if info is None else info["move_time_ms"]
            stop_record = None if info is None else {
                "movement_time_ms": info["move_time_ms"],
                "unix_s": packet.unix_seconds,
                "x": info["x"],
                "y": info["y"],
            }
            if span_open_ms is not None:
                duration = packet.server_ms - span_open_ms
                report.forward_spans += 1
                report.span_heartbeats.append(span_heartbeats)
                if duration > report.longest_span_ms:
                    report.longest_span_ms = duration
                    report.longest_span_heartbeats = span_heartbeats
                span_open_ms = None
        elif opcode in TURN_STARTS:
            report.turn_starts += 1
            direction = -1 if opcode == START_TURN_LEFT else 1
            if active_turn is not None and active_turn != direction:
                report.direct_turn_reversals += 1
            active_turn = direction
            turn_started_at = None if info is None else info["move_time_ms"]
        elif opcode == STOP_TURN:
            report.turn_stops += 1
            if active_turn is not None and turn_started_at is not None and info is not None:
                duration = (info["move_time_ms"] - turn_started_at) & 0xFFFFFFFF
                report.turn_runs += 1
                if duration <= 100:
                    report.short_turn_runs += 1
            active_turn = None
            turn_started_at = None
        elif opcode == HEARTBEAT:
            report.heartbeats += 1
            if span_open_ms is not None:
                span_heartbeats += 1
        else:
            report.other_movement += 1

    report.unterminated_final_span = span_open_ms is not None
    report.trajectory_yards = round(report.trajectory_yards, 3)
    return report


def _delta(new: float, old: float) -> str:
    if old == 0:
        return "n/a" if new == 0 else "+inf"
    return f"{(new - old) / old * 100:+.1f}%"


REPLAY_ROWS = [
    ("movement packets", "movement_packets"),
    ("forward starts", "forward_starts"),
    ("forward stops", "forward_stops"),
    ("turn starts", "turn_starts"),
    ("turn stops", "turn_stops"),
    ("heartbeats", "heartbeats"),
    ("falling %", "falling_percent"),
    ("trajectory yards", "trajectory_yards"),
    ("forward spans", "forward_spans"),
    ("boundary-only stops", "boundary_only_stops"),
    ("turn runs", "turn_runs"),
    ("short turns <=100ms", "short_turn_runs"),
    ("direct reversals", "direct_turn_reversals"),
]
POLICY_LOG_ROWS = [
    ("move actions", "move_actions"),
    ("movement failures", "movement_failures"),
    ("stale-frame rejections", "stale_frame_rejections"),
    ("observations", "observations"),
    ("progress reports", "progress_reports"),
]
HOST_LOG_ROWS = [
    ("nonterminal stops", "nonterminal_boundary_only_stops"),
    ("death/ghost transitions", "life_state_boundary_only_stops"),
    ("terminal artifacts", "terminal_boundary_only_stops"),
    ("host stalls", "host_stalls"),
    ("host rejections", "host_rejected_requests"),
    ("host detached frames", "host_detached_frames"),
    ("bearing disappearances", "route_bearing_disappearances"),
]
def _rows_for(*reports: MovementReport) -> list[tuple[str, str]]:
    """Show optional rows only when their corresponding log was available."""
    rows = list(REPLAY_ROWS)
    if any(r.move_actions >= 0 for r in reports):
        rows.extend(POLICY_LOG_ROWS)
    if any(r.host_stalls >= 0 for r in reports):
        rows.extend(HOST_LOG_ROWS)
    return rows


def print_report(report: MovementReport) -> None:
    print(f"{report.replay}  member={report.member}")
    for label, attr in _rows_for(report):
        print(f"  {label:<22} {getattr(report, attr):>12}")
    print(f"  {'longest span':<22} {report.longest_span_ms / 1000:>9.1f}s "
          f"({report.longest_span_heartbeats} heartbeats)")
    print(f"  {'continuous prefix':<22} {'PASS' if report.continuous_prefix else 'FAIL':>12}")
    if report.unterminated_final_span:
        print("    ! final forward span never received a STOP")
    for detail, count in sorted(report.failure_details.items(), key=lambda kv: -kv[1]):
        print(f"    failure x{count}: {detail}")


def print_comparison(baseline: MovementReport, candidate: MovementReport) -> None:
    print(f"baseline : {baseline.replay} ({baseline.member})")
    print(f"candidate: {candidate.replay} ({candidate.member})")
    print(f"  {'metric':<22} {'baseline':>12} {'candidate':>12} {'delta':>10}")
    for label, attr in _rows_for(baseline, candidate):
        old, new = getattr(baseline, attr), getattr(candidate, attr)
        delta = "n/a" if old < 0 or new < 0 else _delta(new, old)
        print(f"  {label:<22} {old:>12} {new:>12} {delta:>10}")
    print(f"  {'continuous prefix':<22} "
          f"{'PASS' if baseline.continuous_prefix else 'FAIL':>12} "
          f"{'PASS' if candidate.continuous_prefix else 'FAIL':>12}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("episodes", type=Path, nargs="+",
                        help="episode directory (replay + logs) or bare replay.json")
    parser.add_argument("--baseline", type=Path,
                        help="score this episode too and print a before/after table")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = parser.parse_args(argv)

    candidates = [r for path in args.episodes for r in report_episode(path)]
    baselines = report_episode(args.baseline) if args.baseline else []

    if args.json:
        payload = {
            "candidates": [asdict(r) for r in candidates],
            "baselines": [asdict(r) for r in baselines],
        }
        print(json.dumps(payload, indent=2))
        return 0

    if baselines:
        for candidate in candidates:
            print_comparison(baselines[0], candidate)
            print()
        return 0

    for report in candidates:
        print_report(report)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
