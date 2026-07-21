"""T0 policy: navigate to random nearby points, one settled leg at a time.

Each leg: pick a point 10–20 yd away at a uniform random angle (current z; the executor's
Detour projection corrects height because the bridge sends ``target_z_known=False``), emit
one ``move``, wait for its typed settlement, log it, repeat until the deadline. The logged
``settlement_kind`` tally is the smoke-test metric: legs ``reached_target`` vs otherwise.
"""

from __future__ import annotations

import math
import os
import random
import time

from wowborg.types import SUCCESS_SETTLEMENT_KINDS

MIN_LEG_YARDS = 10.0
MAX_LEG_YARDS = 20.0
ARRIVAL_RADIUS_YARDS = 3.0
LEG_TIMEOUT_SECONDS = 90.0
OBSERVE_RETRY_SECONDS = 1.0

# /say breadcrumb verbosity. Artifact-bundle + policy-log retention is confirmed working
# (session 5), so chat is no longer a load-bearing evidence channel — default to the
# quiet mode and keep "verbose" for runs where the replay must self-narrate.
#   off      — no says at all
#   minimal  — session start, death, final summary (3 says/episode)
#   verbose  — plus one say per settled leg (the original smoke behavior)
BREADCRUMBS_ENV = "WOWBORG_BREADCRUMBS"
DEFAULT_BREADCRUMBS = "minimal"


def log(message: str) -> None:
    print(f"WOWBORG-POLICY {message}", flush=True)


class RandomWalkPolicy:
    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
        self.legs_attempted = 0
        self.legs_reached = 0

    def next_destination(self, x: float, y: float) -> tuple[float, float]:
        angle = self._rng.uniform(0.0, 2.0 * math.pi)
        distance = self._rng.uniform(MIN_LEG_YARDS, MAX_LEG_YARDS)
        return x + distance * math.cos(angle), y + distance * math.sin(angle)

    def summary(self) -> dict:
        return {"legs_attempted": self.legs_attempted, "legs_reached": self.legs_reached}

    def run(self, bridge, *, until: float) -> None:
        mode = os.environ.get(BREADCRUMBS_ENV, DEFAULT_BREADCRUMBS)
        bridge_say = getattr(bridge, "say", lambda _text: None)
        say = bridge_say if mode != "off" else (lambda _text: None)
        say_leg = bridge_say if mode == "verbose" else (lambda _text: None)
        say("wowborg random_walk starting")
        while time.monotonic() < until:
            observation = bridge.observe()
            if observation is None:
                time.sleep(OBSERVE_RETRY_SECONDS)
                continue
            if observation.is_dead or observation.is_ghost:
                # Death recovery is T1; a dead random-walker just reports and stops.
                log("character is dead/ghost — stopping (death recovery is out of T0 scope)")
                say("wowborg died — stopping")
                return

            pos = observation.position
            dest_x, dest_y = self.next_destination(pos.x, pos.y)
            self.legs_attempted += 1
            log(
                f"leg {self.legs_attempted}: from ({pos.x:.1f},{pos.y:.1f},{pos.z:.1f}) "
                f"to ({dest_x:.1f},{dest_y:.1f})"
            )
            request_id = bridge.move_to(
                dest_x, dest_y, pos.z, observation.map_id, arrival_radius=ARRIVAL_RADIUS_YARDS
            )
            remaining = until - time.monotonic()
            if remaining <= 0:
                log("deadline reached mid-leg; stopping")
                break
            outcome = bridge.wait_for_result(
                request_id, timeout_s=min(LEG_TIMEOUT_SECONDS, remaining)
            )
            if outcome is None:
                log(f"leg {self.legs_attempted}: TIMEOUT waiting for settlement")
                continue
            if outcome.settlement_kind in SUCCESS_SETTLEMENT_KINDS:
                self.legs_reached += 1
            log(
                f"leg {self.legs_attempted}: settled kind={outcome.settlement_kind} "
                f"success={outcome.success} displacement={outcome.displacement_yards} "
                f"detail={outcome.detail!r}"
            )
            # Replay-visible breadcrumb (verbose mode only; rate-limited in the bridge).
            say_leg(
                f"wowborg leg {self.legs_attempted}: {outcome.settlement_kind} "
                f"({self.legs_reached} reached)"
            )
        log(
            f"done: {self.legs_reached}/{self.legs_attempted} legs settled successfully"
        )
        say(f"wowborg done: {self.legs_reached}/{self.legs_attempted} legs reached")
