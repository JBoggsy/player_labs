"""L0 — the local mover: one executor move, verified and supervised.

Responsibilities (and nothing more):
- issue `move` selections toward ONE destination until 3D-arrived,
- classify each settlement into progress / detour / stall using position history
  (detects A↔B oscillation, which displacement-only checks cannot — v13 lesson),
- run the unstick ladder on stalls (recommended action → escalate),
- report an honest typed result upward; the caller owns re-planning and budgets.

Constants here are EXECUTOR FACTS (chunk size, arrival radius convention) or structural
(history window), never zone calibration — the codex-audit rule.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from wowborg.nav.world_model import Point

# Executor facts (measured across 9 hosted batches, zone-independent):
# a settlement advances one Detour chunk; arrival radius 3.0 is the wire convention.
ARRIVAL_RADIUS_YARDS = 8.0        # our acceptance (2-3 chunks of slop over the wire 3.0)
STAGE_ARRIVAL_RADIUS_YARDS = 35.0  # corridor-grade acceptance for intermediate points
PROGRESS_EPSILON_YARDS = 3.0
OSCILLATION_HISTORY = 8            # settled positions remembered
OSCILLATION_REVISIT_YARDS = 6.0    # returning within this of a prior position = revisit
MAX_STALLS = 4                     # consecutive stalled settlements before failing
UNSTICK_AFTER_STALLS = 2
SETTLE_TIMEOUT_SECONDS = 30.0
FRAME_TIMEOUT_SECONDS = 60.0
# Run-through-combat: v26 hosted evidence — stopping to fight every road aggro made a
# 2000yd haul cost >533s (0.86 yd/s effective vs ~3 yd/s walking). While healthy we
# keep MOVING through combat; only a real threat (health below this fraction) or a
# combat-caused stall (executor keeps interrupting the move) yields to the fight.
COMBAT_HEALTH_FLOOR = 0.5


class LocalMoveStatus(Enum):
    ARRIVED = "arrived"
    STALLED = "stalled"            # no progress + unstick exhausted
    OSCILLATING = "oscillating"    # position-history revisit loop
    COMBAT = "combat"              # in_combat observed — caller decides
    DEAD = "dead"                  # died mid-move — caller decides
    MAP_CHANGED = "map_changed"    # teleport/portal — caller re-plans
    NO_FRAME = "no_frame"          # controller stopped offering frames
    DEADLINE = "deadline"          # caller's deadline expired


@dataclass
class LocalMoveResult:
    status: LocalMoveStatus
    end: Point | None
    moves: int
    seconds: float
    detail: str = ""


@dataclass
class LocalMover:
    """Stateless between calls; all supervision state is per-move_to invocation."""

    tracer: object | None = None

    def _trace(self, kind: str, **payload) -> None:
        if self.tracer is not None:
            self.tracer.emit(kind, **payload)

    @staticmethod
    def _combat_needs_attention(obs, stalls: int) -> bool:
        """Run through trivial road aggro; yield to combat only when it is actually
        winning: health under the floor, or the fight keeps interrupting the move
        (stall streak while in combat)."""
        low_health = (
            obs.max_health > 0 and obs.health / obs.max_health < COMBAT_HEALTH_FLOOR
        )
        return low_health or stalls >= UNSTICK_AFTER_STALLS

    def move_to(
        self,
        bridge,
        target: Point,
        *,
        arrival_radius: float = ARRIVAL_RADIUS_YARDS,
        until: float,
        arrival_target: Point | None = None,
    ) -> LocalMoveResult:
        """Drive toward ``target`` until 3D-arrived or a typed non-arrival status.

        ``arrival_target``: verify arrival against this point instead of ``target``
        (route layer passes the Detour-projected target when the raw one is off-mesh).
        Pauses are NOT handled here: combat/death return immediately with the typed
        status; the route layer owns those transitions and the budget clock.
        """
        check = arrival_target or target
        started = time.monotonic()
        moves = 0
        stalls = 0
        best_distance: float | None = None
        history: list[tuple[Point, float]] = []  # (position, goal distance there)
        # Baseline before the first wait: frame starvation on the FIRST poll
        # (a prior action still walking) must compare against something, or the
        # fallback below misfires into NO_FRAME while we are visibly moving
        # (codex audit #7).
        baseline = _observe(bridge)
        if baseline is not None:
            history.append((baseline, baseline.distance(check)))

        while True:
            if time.monotonic() >= until:
                return LocalMoveResult(LocalMoveStatus.DEADLINE, _last(history), moves,
                                       time.monotonic() - started)
            frame = bridge.wait_for_frame(
                timeout_s=min(FRAME_TIMEOUT_SECONDS, max(0.5, until - time.monotonic()))
            )
            if frame is None:
                # Frame starvation ≠ failure while the executor is WALKING (v23: long
                # Detour chunks keep action_ready false >60s mid-route). If observe()
                # shows movement since our last sample, keep waiting.
                position = _observe(bridge)
                if position is not None and history and position.distance(history[-1][0]) > PROGRESS_EPSILON_YARDS:
                    history.append((position, position.distance(check)))
                    del history[:-OSCILLATION_HISTORY]
                    continue
                return LocalMoveResult(LocalMoveStatus.NO_FRAME, _last(history), moves,
                                       time.monotonic() - started)

            obs = frame.observation
            here = Point(obs.location.map_id, obs.location.x, obs.location.y, obs.location.z)

            # Typed interruptions — surface immediately, caller owns the transition.
            if obs.is_dead or obs.is_ghost:
                return LocalMoveResult(LocalMoveStatus.DEAD, here, moves,
                                       time.monotonic() - started)
            if here.map_id != target.map_id:
                return LocalMoveResult(LocalMoveStatus.MAP_CHANGED, here, moves,
                                       time.monotonic() - started)
            if obs.in_combat and self._combat_needs_attention(obs, stalls):
                return LocalMoveResult(LocalMoveStatus.COMBAT, here, moves,
                                       time.monotonic() - started)

            # 3D arrival (the audit's core fix: z counts).
            if here.distance(check) <= arrival_radius:
                return LocalMoveResult(LocalMoveStatus.ARRIVED, here, moves,
                                       time.monotonic() - started)

            # Oscillation: back within revisit range of a non-adjacent prior position
            # WITHOUT goal progress since that visit. The progress condition matters:
            # legitimate switchback routes (mesa ramps, v29 sarkoth evidence) revisit
            # positions laterally while the goal distance keeps improving.
            if _is_revisit(history, here, here.distance(check)):
                self._trace("nav_oscillation", at=[here.x, here.y, here.z])
                return LocalMoveResult(LocalMoveStatus.OSCILLATING, here, moves,
                                       time.monotonic() - started,
                                       detail="position-history revisit loop")
            history.append((here, here.distance(check)))
            del history[:-OSCILLATION_HISTORY]

            # Progress bookkeeping: goal distance improved OR real displacement.
            distance_now = here.distance(check)
            displaced = (
                len(history) >= 2
                and history[-2][0].distance(here) > PROGRESS_EPSILON_YARDS
            )
            if best_distance is None or distance_now < best_distance - PROGRESS_EPSILON_YARDS:
                best_distance = distance_now
                stalls = 0
            elif displaced:
                stalls = 0
            else:
                stalls += 1

            if stalls >= MAX_STALLS:
                return LocalMoveResult(LocalMoveStatus.STALLED, here, moves,
                                       time.monotonic() - started,
                                       detail=f"{stalls} stalled settlements")

            # Unstick ladder before re-issuing: Stuck (spell 7355, the sanctioned
            # relocation for exhausted source projections — v27: the executor
            # refused every move AND the recommended move with
            # "no physically admissible local source projection") → recommended.
            if stalls >= UNSTICK_AFTER_STALLS:
                self._trace("nav_unstick", stalls=stalls)
                request_id = None
                if hasattr(bridge, "select_stuck"):
                    request_id = bridge.select_stuck(frame)
                if request_id is None and frame.recommended_action is not None:
                    request_id = bridge.select_recommended(frame)
                if request_id is not None:
                    bridge.wait_for_settlement(frame.frame_id, timeout_s=SETTLE_TIMEOUT_SECONDS)
                    continue

            moves += 1
            request_id = bridge.select_move_to(frame, target.x, target.y, target.z, target.map_id)
            if request_id is None:
                # Mask refused the destination — treat like a stall step.
                stalls += 1
                request_id = bridge.select_recommended(frame)
                if request_id is None:
                    continue
            bridge.wait_for_settlement(
                frame.frame_id,
                timeout_s=min(SETTLE_TIMEOUT_SECONDS, max(0.5, until - time.monotonic())),
            )


def _last(history: list[tuple[Point, float]]) -> Point | None:
    return history[-1][0] if history else None


def _observe(bridge) -> Point | None:
    obs = bridge.observe()
    if obs is None:
        return None
    return Point(obs.map_id, obs.position.x, obs.position.y, obs.position.z)


def _is_revisit(
    history: list[tuple[Point, float]], here: Point, goal_distance: float
) -> bool:
    """True when we LEFT a position and came back NO CLOSER to the goal — a real
    A→B→A loop, not a switchback.

    Requires an excursion (some position between the prior visit and now beyond the
    revisit radius — standing still is a STALL, not an oscillation) AND no goal
    progress since the prior visit (switchback ramps legitimately revisit positions
    laterally while goal distance improves — v29 sarkoth-mesa evidence).
    """
    for i, (prior, prior_goal_distance) in enumerate(history[:-1]):
        if prior.distance(here) <= OSCILLATION_REVISIT_YARDS:
            if goal_distance < prior_goal_distance - PROGRESS_EPSILON_YARDS:
                continue
            between = history[i + 1:]
            if any(p.distance(here) > OSCILLATION_REVISIT_YARDS for p, _ in between):
                return True
    return False
