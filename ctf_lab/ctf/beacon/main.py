"""beacon entry point — connect to the runner's sprite websocket and play.

Team is derived from the connection slot (even = red, odd = blue), matching the CTF
server's slot->team assignment. The websocket keepalive is disabled: beacon's decide
runs synchronously inside the async loop, so a slow frame could otherwise trip the
library's ping/pong timeout and drop the connection mid-game (a lesson from cady).
"""

from __future__ import annotations

import asyncio
import sys
from urllib.parse import parse_qs, urlsplit

from ctf.beacon.decide import build_decide
from ctf.beacon.types import Team
from players.player_sdk import env_ws_url, run_sprite_bridge


def _slot_from_url(url: str) -> int:
    try:
        return int(parse_qs(urlsplit(url).query).get("slot", ["0"])[0])
    except (ValueError, IndexError):
        return 0


def team_from_url(url: str) -> Team:
    """Even slot = red (left), odd slot = blue (right). Defaults to red."""
    return "red" if _slot_from_url(url) % 2 == 0 else "blue"


def seat_from_url(url: str) -> int:
    """Per-team seat 0..7 = slot // 2 (fixes the role and defender hold point)."""
    return min(_slot_from_url(url) // 2, 7)


def main() -> None:
    url = env_ws_url()
    team = team_from_url(url)
    seat = seat_from_url(url)
    print(f"beacon: team={team} seat={seat} url={url}", file=sys.stderr, flush=True)
    decide = build_decide(team, seat)
    asyncio.run(run_sprite_bridge(url, decide, ping_interval=None, max_size=None))


if __name__ == "__main__":
    main()
