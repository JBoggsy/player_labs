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
    trajectory_yards: float = 0.0
    forward_spans: int = 0
    boundary_only_stops: int = 0
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

    @property
    def continuous_prefix(self) -> bool:
        """True when the stream reads as intentional journeys, not per-segment churn.

        The bar from the retest plan: one initial start, no boundary-only stops, and
        one final stop per journey — i.e. every forward span is closed by a stop the
        policy meant to send.
        """
        return (
            self.forward_spans > 0
            and self.boundary_only_stops == 0
            and not self.unterminated_final_span
        )


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
    move_outcomes = [
        r for r in records if r.get("kind") == "outcome" and r.get("action_kind") == "move"
    ]
    failures = [r for r in move_outcomes if not r.get("success")]
    report.move_actions = sum(
        1
        for r in records
        if r.get("kind") == "intent" and (r.get("action") or {}).get("kind") == "move"
    )
    report.movement_failures = len(failures)
    report.stale_frame_rejections = sum(1 for r in records if r.get("kind") == "frame_refresh")
    report.observations = sum(1 for r in records if r.get("kind") == "observation")
    report.progress_reports = sum(1 for r in records if r.get("kind") == "player_progress")
    details: dict[str, int] = {}
    for failure in failures:
        key = (failure.get("detail") or "<no detail>")[:70]
        details[key] = details.get(key, 0) + 1
    report.failure_details = details


def _report_member(path: Path, member) -> MovementReport:
    report = MovementReport(replay=path.name, member=member.name)
    previous_xy: tuple[float, float] | None = None

    # Forward-span state: when a START_FORWARD opens a span we accumulate until its STOP.
    span_open_ms: int | None = None
    span_heartbeats = 0
    # Position at the last STOP, held until forward motion resumes, so we can tell a
    # stand-still restart (boundary-only) from a stop the character moved away from.
    stop_xy: tuple[float, float] | None = None

    for packet in member.packets:
        if not packet.from_client or packet.opcode not in MOVE_OPCODES_CLIENT:
            continue
        report.movement_packets += 1

        info = _movement_info(packet)
        if info is not None:
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
            stop_xy = None
            span_open_ms = packet.server_ms
            span_heartbeats = 0
        elif opcode == STOP:
            report.forward_stops += 1
            stop_xy = previous_xy
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
        elif opcode == STOP_TURN:
            report.turn_stops += 1
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
    ("trajectory yards", "trajectory_yards"),
    ("forward spans", "forward_spans"),
    ("boundary-only stops", "boundary_only_stops"),
]
LOG_ROWS = [
    ("move actions", "move_actions"),
    ("movement failures", "movement_failures"),
    ("stale-frame rejections", "stale_frame_rejections"),
    ("observations", "observations"),
    ("progress reports", "progress_reports"),
]
ROWS = REPLAY_ROWS + LOG_ROWS


def _rows_for(*reports: MovementReport) -> list[tuple[str, str]]:
    """Drop the log rows when no report being printed had a policy log."""
    if any(r.move_actions >= 0 for r in reports):
        return ROWS
    return REPLAY_ROWS


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
