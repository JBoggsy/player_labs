"""Sugarscape population policy that maximizes balanced resource runway."""

import json
import math
import os
import time
from collections import Counter

from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect


REPORT_EVERY = 1_000


def _runway(store: float, harvest: float, metabolism: float) -> float:
    if metabolism <= 0:
        return math.inf
    return (store + harvest - metabolism) / metabolism


def _candidate_key(agent: dict, candidate: dict) -> tuple[float, ...]:
    sugar_runway = _runway(
        float(agent["sugar"]),
        float(candidate["sugar"]),
        float(agent["sugarMetabolism"]),
    )
    spice_runway = _runway(
        float(agent["spice"]),
        float(candidate["spice"]),
        float(agent["spiceMetabolism"]),
    )
    survival_floor = min(sugar_runway, spice_runway)
    if math.isfinite(sugar_runway) and math.isfinite(spice_runway):
        balance = -abs(sugar_runway - spice_runway)
        combined_runway = sugar_runway + spice_runway
    else:
        balance = survival_floor
        combined_runway = survival_floor
    return (
        survival_floor,
        balance,
        combined_runway,
        float(candidate["welfare"]),
        -float(candidate["distance"]),
        -float(candidate["cell"]),
    )


def choose_candidate(observation: dict) -> tuple[dict, str, str]:
    agent = observation["agent"]
    candidates = observation["candidates"]
    choice = max(candidates, key=lambda candidate: _candidate_key(agent, candidate))

    sugar_now = _runway(
        float(agent["sugar"]), 0.0, float(agent["sugarMetabolism"])
    )
    spice_now = _runway(
        float(agent["spice"]), 0.0, float(agent["spiceMetabolism"])
    )
    if sugar_now < spice_now:
        scarce = "sugar"
    elif spice_now < sugar_now:
        scarce = "spice"
    else:
        scarce = "equal"

    greedy = candidates[0]
    if choice["cell"] == greedy["cell"]:
        reason = "greedy_already_balanced"
    else:
        choice_key = _candidate_key(agent, choice)
        greedy_key = _candidate_key(agent, greedy)
        if choice_key[0] > greedy_key[0]:
            reason = "raise_survival_floor"
        elif choice_key[1] > greedy_key[1]:
            reason = "tighten_balance"
        else:
            reason = "tie_break"
    return choice, scarce, reason


def _report(counters: Counter, final: bool = False) -> None:
    print(
        "longevity_stats "
        + json.dumps({"final": final, **dict(sorted(counters.items()))}),
        flush=True,
    )


def run(endpoint: str) -> None:
    counters = Counter()
    connected = False
    while not connected:
        try:
            socket = connect(
                endpoint,
                open_timeout=5,
                ping_interval=None,
                max_size=None,
            )
            connected = True
        except Exception as error:
            counters["connection_retries"] += 1
            print(f"connection retry: {error}", flush=True)
            time.sleep(0.25)

    try:
        with socket:
            while True:
                message = json.loads(socket.recv())
                if (
                    message.get("type") != "observation"
                    or "requestId" not in message
                    or not message.get("candidates")
                ):
                    continue
                choice, scarce, reason = choose_candidate(message)
                counters["observations"] += 1
                counters[f"scarce_{scarce}"] += 1
                counters[f"reason_{reason}"] += 1
                if choice["cell"] != message["candidates"][0]["cell"]:
                    counters["changed_from_greedy"] += 1
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
                if counters["observations"] % REPORT_EVERY == 0:
                    _report(counters)
    except ConnectionClosed as error:
        print(f"episode ended: {error}", flush=True)
    finally:
        _report(counters, final=True)


if __name__ == "__main__":
    player_endpoint = os.environ.get("COWORLD_PLAYER_WS_URL") or os.environ.get(
        "COGAMES_ENGINE_WS_URL"
    )
    if not player_endpoint:
        raise ValueError("COWORLD_PLAYER_WS_URL is required")
    run(player_endpoint)
