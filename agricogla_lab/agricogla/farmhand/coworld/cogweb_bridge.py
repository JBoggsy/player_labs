"""Engine-specific websocket bridge for the ``cogweb.player.v1`` JSON protocol.

This is the shared player protocol for the cogweb family of Coworld games
(agricogla, werecog, cogsul, coguire, cogherence, cognames, acquire, ...). The
game runnable runs a ``/player`` websocket SERVER, one socket per slot; an
external player policy is a websocket CLIENT that drives one slot, connecting to
the URL in ``COWORLD_PLAYER_WS_URL`` (it already carries ``?slot=&token=``).

The wire shape is uniform across every cogweb game — only the opaque ``view`` and
``decision`` payloads are game-specific:

    game   -> player  welcome      { type, protocol:"cogweb.player.v1", slot, config }
    game   -> player  observation  { type, id, seat, turn, view, messages, reason, timeLeftMs }
    player -> game    reply        { type:"reply", id, decision, messages }
    game   -> player  final        { type:"final", scores:number[] }

A rejected reply is re-sent as a fresh ``observation`` with ``reason`` set (there
is no separate ``reject`` frame). The reply MUST echo the observation's ``id``.

This bridge owns all of that envelope handling — id correlation, the reason
re-request, the chess-clock ``timeLeftMs``, cheap-talk routing, and clean exit —
so a cogweb game's player only supplies a ``decide`` callback that maps a redacted
``view`` to a game-specific ``decision``. It deliberately knows NOTHING about any
particular game's view/decision schema (that stays in the game's player package),
and it depends only on :func:`run_message_bridge` for transport, mirroring how
``coworld_json_bridge`` (mettagrid) and Crewrift's Sprite-v1 loop are
engine-specific peers over the same general transport.

Why a dedicated module rather than each game re-deriving the loop: every cogweb
game needs identical envelope plumbing (echo id, re-decide on reason, never crash
on a server-side close, optionally budget against ``timeLeftMs``). Centralizing it
means a new cogweb game ships only its ``decide`` function.

Relationship to the general layer: this is the cogweb specialization of
:mod:`players.player_sdk.message_bridge`. Games whose transport is NOT
cogweb.player.v1 (mettagrid token games, Crewrift Sprite-v1 binary) use their own
engine bridge or the generic ``run_message_bridge`` directly.
"""

from __future__ import annotations

import inspect
import json
import os
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from players.player_sdk.message_bridge import (
    ClosePolicy,
    Connect,
    exit_zero_on_unclean_close,
    run_message_bridge,
)
from players.player_sdk.trace_outputs import TraceOutputs

PROTOCOL = "cogweb.player.v1"

# A game-specific decision payload (opaque to this bridge; the game validates it).
Decision = Any
# A redacted seat view (opaque to this bridge).
View = Any


@dataclass
class CogwebContext:
    """Per-observation context handed to a game's ``decide`` callback.

    Everything the cogweb envelope carries that a policy might use, without the
    policy having to parse frames itself.
    """

    seat: int
    turn: int
    #: Set when the previous reply was rejected; ``None`` on a fresh observation.
    reason: str | None = None
    #: Remaining whole-game chess-clock budget in ms, or ``None`` if unbounded.
    time_left_ms: float | None = None
    #: This seat's visible inbox (public chatter + DMs), oldest first.
    inbox: list[dict] = field(default_factory=list)
    #: Public episode config from the welcome frame (e.g. player count), or ``None``.
    config: Any = None
    #: This player's own slot index from the welcome frame.
    slot: int | None = None


# decide(view, ctx) -> decision OR (decision, talk_lines). May be sync or async.
DecideResult = Decision | tuple[Decision, Iterable[Any]]
Decide = Callable[[View, CogwebContext], DecideResult | Awaitable[DecideResult]]

# Optional lifecycle hooks.
OnWelcome = Callable[[CogwebContext], None]
OnFinal = Callable[[list[float]], None]


class _CogwebHandler:
    """Decodes one cogweb.player.v1 frame and returns the outbound reply frames."""

    def __init__(
        self,
        decide: Decide,
        *,
        on_welcome: OnWelcome | None = None,
        on_final: OnFinal | None = None,
    ) -> None:
        self._decide = decide
        self._on_welcome = on_welcome
        self._on_final = on_final
        self._slot: int | None = None
        self._config: Any = None

    async def __call__(self, message: str | bytes) -> list[str]:
        if isinstance(message, (bytes, bytearray)):
            message = bytes(message).decode("utf-8", "replace")
        try:
            msg = json.loads(message)
        except (json.JSONDecodeError, TypeError, ValueError):
            return []  # ignore undecodable frames; never crash the bridge
        if not isinstance(msg, dict):
            return []

        mtype = msg.get("type")
        if mtype == "welcome":
            self._slot = msg.get("slot")
            self._config = msg.get("config")
            if self._on_welcome is not None:
                self._on_welcome(
                    CogwebContext(
                        seat=self._slot if isinstance(self._slot, int) else -1,
                        turn=0,
                        config=self._config,
                        slot=self._slot,
                    )
                )
            return []

        if mtype == "final":
            if self._on_final is not None:
                scores = msg.get("scores") or []
                self._on_final(list(scores))
            return []  # server closes the socket after final

        if mtype != "observation":
            return []  # unknown frame type — ignore

        ctx = CogwebContext(
            seat=int(msg.get("seat", self._slot if isinstance(self._slot, int) else -1)),
            turn=int(msg.get("turn", 0)),
            reason=msg.get("reason"),
            time_left_ms=msg.get("timeLeftMs"),
            inbox=list(msg.get("messages") or []),
            config=self._config,
            slot=self._slot,
        )
        result = self._decide(msg.get("view"), ctx)
        if inspect.isawaitable(result):
            result = await result

        decision, talk = _split_decision(result)
        if decision is None:
            # A policy that declines to act this turn (rare). The host will fall
            # back to a legal move; we send nothing.
            return []

        reply: dict[str, Any] = {"type": "reply", "id": msg.get("id"), "decision": decision}
        if talk:
            reply["messages"] = list(talk)
        return [json.dumps(reply)]


def _split_decision(result: DecideResult) -> tuple[Decision, list[Any]]:
    """Allow ``decide`` to return either ``decision`` or ``(decision, talk_lines)``."""
    if (
        isinstance(result, tuple)
        and len(result) == 2
        and not isinstance(result, str)
    ):
        decision, talk = result
        return decision, list(talk or [])
    return result, []


async def run_cogweb_bridge(
    url: str,
    decide: Decide,
    *,
    on_welcome: OnWelcome | None = None,
    on_final: OnFinal | None = None,
    trace_outputs: TraceOutputs | None = None,
    connect: Connect | None = None,
    on_close: ClosePolicy = exit_zero_on_unclean_close,
    teardown: Callable[[], None] | None = None,
    **connect_kwargs: Any,
) -> None:
    """Run a ``cogweb.player.v1`` player loop until the server closes.

    Args:
        url: the websocket URL (typically ``os.environ["COWORLD_PLAYER_WS_URL"]``).
        decide: ``decide(view, ctx) -> decision`` (or ``(decision, talk_lines)``),
            sync or async. ``view`` is the seat's redacted state; ``ctx`` is a
            :class:`CogwebContext`. Return ``None`` to decline a turn (host falls
            back to a legal move). The bridge echoes the observation id for you.
        on_welcome: optional hook called once with the welcome :class:`CogwebContext`.
        on_final: optional hook called with the per-slot ``scores`` list at game end.
        trace_outputs: optional :class:`TraceOutputs`; closed (zipped+uploaded) on exit.
        Other args are forwarded to :func:`run_message_bridge` / ``websockets.connect``.
    """
    handler = _CogwebHandler(decide, on_welcome=on_welcome, on_final=on_final)
    bridge_kwargs: dict[str, Any] = dict(connect_kwargs)
    if connect is not None:
        bridge_kwargs["connect"] = connect
    await run_message_bridge(
        url,
        handler,
        trace_outputs=trace_outputs,
        on_close=on_close,
        teardown=teardown,
        **bridge_kwargs,
    )


def env_ws_url() -> str:
    """Return ``COWORLD_PLAYER_WS_URL`` (canonical) or the legacy alias, or raise.

    Connect to it EXACTLY as given — appending query params breaks the handshake
    on some games (the slot/token are already encoded).
    """
    url = os.environ.get("COWORLD_PLAYER_WS_URL") or os.environ.get("COGAMES_ENGINE_WS_URL")
    if not url:
        raise SystemExit("cogweb bridge: COWORLD_PLAYER_WS_URL is not set")
    return url
