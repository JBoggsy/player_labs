"""T0 policy: navigate to random nearby points, one settled leg at a time (0.1.31).

Frame-driven loop: wait for the Nim controller to OFFER a decision frame, select a
``move`` with a random destination 10–20 yd away (executor plans the Detour route and
corrects z server-side), wait for that frame's settlement, repeat until the deadline.
When the environment rejects a move (for example, a destination is off-mesh), yield
one step so the next observation can drive a new attempt.
"""

from __future__ import annotations

import math
import os
import random
import time

MIN_LEG_YARDS = 10.0
MAX_LEG_YARDS = 20.0
FRAME_TIMEOUT_SECONDS = 60.0
LEG_TIMEOUT_SECONDS = 90.0

# /say breadcrumb verbosity. Chat is a bonus channel at 0.1.31 (bounded admitted
# vocabulary — arbitrary strings may not be expressible); evidence lives in the trace
# and artifact bundle. off | minimal (default) | verbose.
BREADCRUMBS_ENV = "WOWBORG_BREADCRUMBS"
DEFAULT_BREADCRUMBS = "minimal"


def log(message: str) -> None:
    print(f"WOWBORG-POLICY {message}", flush=True)


class RandomWalkPolicy:
    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
        self.legs_attempted = 0
        self.legs_reached = 0
        self.legs_fallback = 0  # moves rejected by the environment

    def next_destination(self, x: float, y: float) -> tuple[float, float]:
        angle = self._rng.uniform(0.0, 2.0 * math.pi)
        distance = self._rng.uniform(MIN_LEG_YARDS, MAX_LEG_YARDS)
        return x + distance * math.cos(angle), y + distance * math.sin(angle)

    def summary(self) -> dict:
        return {
            "legs_attempted": self.legs_attempted,
            "legs_reached": self.legs_reached,
            "legs_fallback": self.legs_fallback,
        }

    def run(self, bridge, *, until: float) -> None:
        mode = os.environ.get(BREADCRUMBS_ENV, DEFAULT_BREADCRUMBS)
        bridge_say = getattr(bridge, "say", lambda _text: None)
        say = bridge_say if mode != "off" else (lambda _text: None)
        say("wowborg random_walk starting")

        while time.monotonic() < until:
            remaining = until - time.monotonic()
            frame = bridge.wait_for_frame(timeout_s=min(FRAME_TIMEOUT_SECONDS, remaining))
            if frame is None:
                if getattr(bridge, "finished", False):
                    break
                log("no decision frame offered before timeout; retrying")
                continue

            obs = frame
            if obs.is_dead or obs.is_ghost:
                # Death recovery is T1; defer to the planner's recommendation (it knows
                # release/reclaim) instead of stopping cold.
                log("character dead/ghost — yielding for explicit recovery")
                request_id = bridge.select_wait(frame)
                if request_id is not None:
                    bridge.wait_for_settlement(frame.frame_id, timeout_s=LEG_TIMEOUT_SECONDS)
                continue

            loc = obs.location
            dest_x, dest_y = self.next_destination(loc.x, loc.y)
            self.legs_attempted += 1
            log(
                f"leg {self.legs_attempted}: from ({loc.x:.1f},{loc.y:.1f},{loc.z:.1f}) "
                f"to ({dest_x:.1f},{dest_y:.1f}) [frame {frame.frame_id}]"
            )
            request_id = bridge.select_move_to(frame, dest_x, dest_y, loc.z, loc.map_id)
            if request_id is None:
                # Mask refused our destination — take the recommendation to keep moving.
                self.legs_fallback += 1
                log(f"leg {self.legs_attempted}: move rejected; yielding one step")
                request_id = bridge.select_wait(frame)
                if request_id is None:
                    continue

            remaining = until - time.monotonic()
            if remaining <= 0:
                log("deadline reached mid-leg; stopping")
                break
            outcome = bridge.wait_for_settlement(
                frame.frame_id, timeout_s=min(LEG_TIMEOUT_SECONDS, remaining)
            )
            if outcome is None:
                log(f"leg {self.legs_attempted}: TIMEOUT waiting for settlement")
                continue
            if outcome.success:
                self.legs_reached += 1
            log(
                f"leg {self.legs_attempted}: settled kind={outcome.kind} "
                f"success={outcome.success} detail={outcome.detail!r}"
            )

        log(
            f"done: {self.legs_reached}/{self.legs_attempted} legs settled successfully "
            f"({self.legs_fallback} rejected moves)"
        )
        say("wowborg random_walk done")
