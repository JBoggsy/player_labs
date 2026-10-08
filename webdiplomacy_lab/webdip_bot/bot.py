"""webDiplomacy player: the launcher's child process (see docs/webdiplomacy-gameplay.md).

Per phase: read context + public files, choose orders with the selected policy, save
with Ready, diff the saved orders against the request (upstream silently drops invalid
ones), and print one JSON `decision` line to stdout with activation counts.

Policy selection: `WEBDIP_POLICY` (default: the current candidate, `POLICY`). The local
arena (`webdip_bot.arena`) runs a different policy per slot inside one image.
"""

import json
import os
import random
import time
import traceback
from urllib.error import HTTPError, URLError

from players.api import WebDiplomacy, order_difference

POLICY = "search"


def policy_class(name):
    """`name` or `name:KEY=VAL,KEY=VAL` (config overrides; used to screen variants locally).

    `name` may be a personality (personalities.py: base policy + overrides) or a base policy.
    Explicit overrides apply on top of a personality's own."""
    from webdip_bot import config
    from webdip_bot.personalities import resolve

    overrides = {}
    if ":" in name:
        name, extra = name.split(":", 1)
        for item in extra.split(","):
            key, value = item.split("=", 1)
            overrides[key] = value
    persona = resolve(name)
    if persona:
        name, base_overrides = persona
        overrides = {**base_overrides, **overrides}
    for key, value in overrides.items():
        current = getattr(config, key)
        if isinstance(value, str) and not isinstance(current, str):
            value = json.loads(value) if isinstance(current, list) else type(current)(value)
        setattr(config, key, value)
    if name == "dumbbot":
        from webdip_bot.dumbbot import DumbBot

        return DumbBot
    if name == "search":
        from webdip_bot.search import SearchBot

        return SearchBot
    if name == "nash":
        from webdip_bot.nash import NashBot

        return NashBot
    if name == "press":
        from webdip_bot.press.player import PressPlayer

        return PressPlayer
    if name == "random":
        from webdip_bot.field.random_legal import RandomLegal

        return RandomLegal
    if name == "dumbbot_v1":
        from webdip_bot.field.dumbbot_v1 import DumbBot

        return DumbBot
    raise ValueError(f"unknown policy {name}")


def emit(policy, **fields):
    print(json.dumps({"policy": policy, **fields}), flush=True)


def play_phase(api, context, seed, policy, cls, state):
    game = context["game"]
    board = api.file(context["files"]["game"])
    if (board["turn"], board["phase"]) != (game["turn"], game["phase"]):
        return False  # The phase changed while reading its public file.
    variant = state.get("variant") or api.file(context["files"]["variant"])
    state["variant"] = variant
    started = time.monotonic()
    rng = random.Random(f"{seed}:{api.country_id}:{game['turn']}:{game['phase']}")
    bot = cls(variant, board, api.country_id, game["phase"], int(game["turn"]), rng)
    if hasattr(bot, "observe"):
        bot.observe(api, context, state)
    slots = context["orders"]["orders"]
    requested = bot.choose(slots)
    compute_ms = round((time.monotonic() - started) * 1000, 1)
    saved = api.orders(context, requested) if requested else []
    latest = api.context()["game"]
    if (latest["turn"], latest["phase"]) != (game["turn"], game["phase"]):
        return True  # Phase advanced already; our saved orders were adjudicated.
    try:
        difference = order_difference(requested, saved, len(slots)) if requested else {"missing": [], "unexpected": []}
    except (TypeError, ValueError, KeyError):
        # Upstream can echo a saved build/destroy with a null territory; the orders are saved,
        # only the comparison fails. Record it instead of losing the decision log.
        difference = {"missing": [], "unexpected": [], "diff_error": True}
    emit(
        policy,
        event="decision",
        turn=int(game["turn"]),
        phase=game["phase"],
        country=api.country_id,
        units=len(slots),
        centers=bot.b.centers[api.country_id],
        compute_ms=compute_ms,
        trace=dict(bot.trace),
        rejected=len(difference["missing"]),
        difference=difference if any(difference.values()) else None,
    )
    return True


def main(policy=None):
    policy = policy or os.environ.get("WEBDIP_POLICY", POLICY)
    cls = policy_class(policy)
    if getattr(cls, "PRESS", False):
        from webdip_bot.press.player import main as press_main

        return press_main(policy)
    api = WebDiplomacy(
        os.environ["WEBDIP_URL"],
        os.environ["WEBDIP_API_KEY"],
        os.environ["WEBDIP_GAME_ID"],
        os.environ["WEBDIP_COUNTRY_ID"],
    )
    seed = int(os.environ.get("WEBDIP_SEED", "0"))
    from webdip_bot.personalities import PERSONALITIES

    motto = PERSONALITIES.get(policy.split(":")[0], {}).get("motto")
    emit(policy, event="start", country=api.country_id, seed=seed, motto=motto)
    previous = None
    state = {}
    while True:
        phase = None
        try:
            context = api.context()
            game = context["game"]
            phase = (game["turn"], game["phase"])
            if game["phase"] == "Finished":
                emit(policy, event="finished")
                return
            if game["phase"] != "Pre-game" and phase != previous and context.get("orders"):
                if play_phase(api, context, seed, policy, cls, state):
                    previous = phase
        except HTTPError as error:
            if error.code == 404:
                return  # Upstream erases cancelled games.
            emit(policy, event="http_error", code=error.code)
        except (URLError, TimeoutError):
            pass
        except Exception as error:  # A crashed child leaves the seat silent for the rest of the game.
            emit(policy, event="exception", error=repr(error)[:300], where=traceback.format_exc()[-1200:])
            previous = phase
        time.sleep(0.2)


if __name__ == "__main__":
    main()
