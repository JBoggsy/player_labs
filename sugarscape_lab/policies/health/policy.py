"""Pollution-averse Sugarscape population policy."""

from __future__ import annotations

from collections import Counter
import json
import os
import sys
import time
from typing import Any

from websockets.sync.client import connect


HEALTHY_RUNWAY_FLOOR = 4.0
SICK_RUNWAY_FLOOR = 2.5
REPORT_INTERVAL = 500


def _runway(resource: float, harvest: float, metabolism: float) -> float:
    if metabolism <= 0:
        return float("inf")
    return (resource + harvest) / metabolism


def choose_candidate(observation: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Choose clean ground without crossing the weakest-resource safety floor."""

    agent = observation["agent"]
    candidates = observation["candidates"]
    sick = bool(agent["sick"])
    floor = SICK_RUNWAY_FLOOR if sick else HEALTHY_RUNWAY_FLOOR

    projected: list[tuple[dict[str, Any], float]] = []
    for candidate in candidates:
        sugar_runway = _runway(
            agent["sugar"], candidate["sugar"], agent["sugarMetabolism"]
        )
        spice_runway = _runway(
            agent["spice"], candidate["spice"], agent["spiceMetabolism"]
        )
        projected.append((candidate, min(sugar_runway, spice_runway)))

    safe = [(candidate, runway) for candidate, runway in projected if runway >= floor]
    if safe:
        # Sickness permits a smaller (but still explicit) reserve floor, making the
        # policy willing to sacrifice more resource utility for cleaner ground.
        choice, _ = min(
            safe,
            key=lambda item: (
                item[0]["pollution"],
                -item[1],
                -item[0]["welfare"],
                item[0]["distance"],
                item[0]["cell"],
            ),
        )
        return choice, "sick_clean" if sick else "clean_safe"

    # If every move breaches the floor, first repair the scarcer resource. Clean
    # ground remains the tie-breaker, so survival mode doesn't abandon health.
    choice, _ = min(
        projected,
        key=lambda item: (
            -item[1],
            item[0]["pollution"],
            -item[0]["welfare"],
            item[0]["distance"],
            item[0]["cell"],
        ),
    )
    return choice, "starvation_rescue"


def _report(counters: Counter[str], *, final: bool = False) -> None:
    payload = {"event": "health_policy_summary", "final": final, **counters}
    print(json.dumps(payload, sort_keys=True), file=sys.stderr, flush=True)


def run(endpoint: str) -> None:
    counters: Counter[str] = Counter()
    connected = False

    while True:
        try:
            with connect(
                endpoint,
                open_timeout=5,
                ping_interval=None,
                max_size=None,
            ) as socket:
                connected = True
                print("health policy connected", file=sys.stderr, flush=True)
                for raw in socket:
                    message = json.loads(raw)
                    if message.get("type") != "observation":
                        continue
                    candidates = message.get("candidates") or []
                    if not candidates:
                        continue

                    choice, reason = choose_candidate(message)
                    counters["decisions"] += 1
                    counters[f"reason_{reason}"] += 1
                    if message["agent"]["sick"]:
                        counters["sick_decisions"] += 1
                    if choice["cell"] != candidates[0]["cell"]:
                        counters["non_greedy_choices"] += 1
                    if choice["pollution"] < candidates[0]["pollution"]:
                        counters["cleaner_than_greedy"] += 1

                    socket.send(
                        json.dumps(
                            {
                                "type": "action",
                                "requestId": message["requestId"],
                                "cell": choice["cell"],
                            },
                            separators=(",", ":"),
                        )
                    )
                    if counters["decisions"] % REPORT_INTERVAL == 0:
                        _report(counters)
                return
        except Exception as error:
            if connected:
                print(f"episode ended: {error}", file=sys.stderr, flush=True)
                return
            counters["connection_retries"] += 1
            print(f"connection retry: {error}", file=sys.stderr, flush=True)
            time.sleep(0.25)
        finally:
            if connected:
                _report(counters, final=True)


def main() -> None:
    endpoint = os.environ.get("COWORLD_PLAYER_WS_URL") or os.environ.get(
        "COGAMES_ENGINE_WS_URL"
    )
    if not endpoint:
        raise SystemExit("COWORLD_PLAYER_WS_URL is required")
    run(endpoint)


if __name__ == "__main__":
    main()
