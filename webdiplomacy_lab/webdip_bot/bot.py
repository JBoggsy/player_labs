"""webDiplomacy DumbBot player: the launcher's child process (see docs/webdiplomacy-gameplay.md).

Per phase: read context + public files, choose orders with DumbBot, save with Ready,
diff the saved orders against the request (upstream silently drops invalid ones),
and print one JSON `decision` line to stdout with activation counts.
"""

import json
import os
import random
import time
import traceback
from urllib.error import HTTPError, URLError

from players.api import WebDiplomacy, order_difference

from webdip_bot.dumbbot import DumbBot

POLICY = "dumbbot"


def emit(**fields):
    print(json.dumps({"policy": POLICY, **fields}), flush=True)


def play_phase(api, context, seed):
    game = context["game"]
    board = api.file(context["files"]["game"])
    if (board["turn"], board["phase"]) != (game["turn"], game["phase"]):
        return False  # The phase changed while reading its public file.
    variant = api.file(context["files"]["variant"])
    started = time.monotonic()
    rng = random.Random(f"{seed}:{api.country_id}:{game['turn']}:{game['phase']}")
    bot = DumbBot(variant, board, api.country_id, game["phase"], int(game["turn"]), rng)
    slots = context["orders"]["orders"]
    requested = bot.choose(slots)
    compute_ms = round((time.monotonic() - started) * 1000, 1)
    saved = api.orders(context, requested) if requested else []
    latest = api.context()["game"]
    if (latest["turn"], latest["phase"]) != (game["turn"], game["phase"]):
        return True  # Phase advanced already; our saved orders were adjudicated.
    difference = order_difference(requested, saved, len(slots)) if requested else {"missing": [], "unexpected": []}
    emit(
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


def main():
    api = WebDiplomacy(
        os.environ["WEBDIP_URL"],
        os.environ["WEBDIP_API_KEY"],
        os.environ["WEBDIP_GAME_ID"],
        os.environ["WEBDIP_COUNTRY_ID"],
    )
    seed = int(os.environ.get("WEBDIP_SEED", "0"))
    emit(event="start", country=api.country_id, seed=seed)
    previous = None
    while True:
        phase = None
        try:
            context = api.context()
            game = context["game"]
            phase = (game["turn"], game["phase"])
            if game["phase"] == "Finished":
                emit(event="finished")
                return
            if game["phase"] != "Pre-game" and phase != previous and context.get("orders"):
                if play_phase(api, context, seed):
                    previous = phase
        except HTTPError as error:
            if error.code == 404:
                return  # Upstream erases cancelled games.
            emit(event="http_error", code=error.code)
        except (URLError, TimeoutError):
            pass
        except Exception as error:  # A crashed child leaves the seat silent for the rest of the game.
            emit(event="exception", error=repr(error)[:300], where=traceback.format_exc()[-1200:])
            previous = phase
        time.sleep(0.2)


if __name__ == "__main__":
    main()
