"""Sugarscape policy that turns local resource abundance into longer runways."""

from __future__ import annotations

import json
import os
import time
from collections import Counter
from typing import Any, Callable

from websockets.sync.client import connect


REPORT_INTERVAL = 250


def _number(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def choose_candidate(observation: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Choose the destination that buys the most metabolism-adjusted runway."""
    candidates = observation["candidates"]
    agent = observation["agent"]
    sugar_metabolism = max(1.0, _number(agent.get("sugarMetabolism")))
    spice_metabolism = max(1.0, _number(agent.get("spiceMetabolism")))

    criteria: list[tuple[str, Callable[[dict[str, Any]], float]]] = [
        (
            "runway",
            lambda candidate: (
                _number(candidate.get("sugar")) / sugar_metabolism
                + _number(candidate.get("spice")) / spice_metabolism
            ),
        ),
        (
            "raw_harvest",
            lambda candidate: _number(candidate.get("sugar"))
            + _number(candidate.get("spice")),
        ),
        ("cleaner_cell", lambda candidate: -_number(candidate.get("pollution"))),
        ("shorter_trip", lambda candidate: -_number(candidate.get("distance"))),
        ("welfare_tiebreak", lambda candidate: _number(candidate.get("welfare"))),
        ("stable_cell_tiebreak", lambda candidate: -_number(candidate.get("cell"))),
    ]

    finalists = list(candidates)
    reason = "stable_cell_tiebreak"
    for name, value in criteria:
        best_value = max(value(candidate) for candidate in finalists)
        narrowed = [candidate for candidate in finalists if value(candidate) == best_value]
        if len(narrowed) < len(finalists):
            reason = name
        finalists = narrowed
        if len(finalists) == 1:
            break
    return finalists[0], reason


def report(counters: Counter[str], event: str) -> None:
    payload = {"policy": "abundance", "event": event, **dict(sorted(counters.items()))}
    print(json.dumps(payload, separators=(",", ":")), flush=True)


def run(endpoint: str) -> None:
    connected = False
    counters: Counter[str] = Counter()

    while True:
        try:
            with connect(endpoint, open_timeout=5, ping_interval=None) as socket:
                connected = True
                print('{"policy":"abundance","event":"connected"}', flush=True)

                for raw_message in socket:
                    try:
                        observation = json.loads(raw_message)
                    except (json.JSONDecodeError, TypeError):
                        counters["ignored_messages"] += 1
                        continue

                    if (
                        not isinstance(observation, dict)
                        or observation.get("type") != "observation"
                        or not isinstance(observation.get("requestId"), int)
                        or not isinstance(observation.get("agent"), dict)
                        or not isinstance(observation.get("candidates"), list)
                        or not observation["candidates"]
                    ):
                        counters["ignored_messages"] += 1
                        continue

                    candidate, reason = choose_candidate(observation)
                    counters["decisions"] += 1
                    counters[f"reason_{reason}"] += 1
                    if candidate["cell"] != observation["candidates"][0]["cell"]:
                        counters["non_default_choices"] += 1

                    socket.send(
                        json.dumps(
                            {
                                "type": "action",
                                "requestId": observation["requestId"],
                                "cell": candidate["cell"],
                            },
                            separators=(",", ":"),
                        )
                    )
                    if counters["decisions"] % REPORT_INTERVAL == 0:
                        report(counters, "progress")

            report(counters, "episode_ended")
            return
        except Exception as error:
            if connected:
                counters["connection_end_errors"] += 1
                report(counters, "episode_ended")
                print(f"abundance episode connection ended: {error}", flush=True)
                return
            print(f"abundance connection retry: {error}", flush=True)
            time.sleep(0.25)


if __name__ == "__main__":
    player_url = os.environ.get("COWORLD_PLAYER_WS_URL") or os.environ.get(
        "COGAMES_ENGINE_WS_URL"
    )
    if not player_url:
        raise SystemExit("COWORLD_PLAYER_WS_URL is required")
    run(player_url)
