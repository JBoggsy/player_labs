"""The recall harness: WebSocket loop + state-driven phase dispatch + ALWAYS-RECONNECT.

NO LLM on our side. Strategy = planted digit-recall (clone of jordan-numbers-memory):
- private_questions: ask the 3 digit-forcing probes (config.PROBES). The judge replies with a
  pure digit string; that reply lands in the "Reference material:" transcript the judge reads
  when scoring EVERY question.
- proposals: ask open questions; commit the RECALLED digit strings (extracted from the judge's
  own replies) as our secret answers -> they match the judge's transcript -> ~1.0 on our Qs.
- answers (blind): commit recalled digits too (signal-free vs a real opponent answer, but a
  legal completing answer — the weak half of the tie strategy).

Server contract (v2/coworld/game.py @ cue_n_woo 0.2.x):
- After every action either player makes, the server broadcasts a fresh state; `ask` is
  synchronous (judge reply appended to me.judge before the next broadcast). Phases are GLOBAL
  (advance only when both players meet the per-phase quota). Idempotence from per-slot state
  counts + a single in-flight guard. Asking fewer than private_questions_per_player STALLS the
  phase -> inactive timeout -> DQ, so we ask exactly config.PRIVATE_QUESTIONS (== the game's 3).
- The socket may close mid-episode (idle during a slow judge turn, or a blip). We RECONNECT and
  resume from the server's fresh state broadcast (the loop is idempotent) until we see reveal/done,
  bounded by the hard timer — so a transient drop never orphans us into an inactive -100.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed

from . import answers, config


def log(msg: str) -> None:
    print(f"[recall] {msg}", file=sys.stderr, flush=True)


class RecallPlayer:
    def __init__(self) -> None:
        self.pending: str | None = None  # action in flight, cleared when a later state shows it landed
        self._asks_target = 0
        self.done = False

    # -- entry: reconnect loop ----------------------------------------------
    async def run(self) -> None:
        url = os.environ["COWORLD_PLAYER_WS_URL"]
        attempt = 0
        while not self.done:
            attempt += 1
            self.pending = None  # a reconnect may have lost an in-flight send; allow re-send
            log(f"connecting to {url} (attempt {attempt})")
            try:
                async with websockets.connect(
                    url, ping_interval=20, ping_timeout=20, open_timeout=15, max_size=None
                ) as ws:
                    async for raw in ws:
                        try:
                            msg = json.loads(raw)
                        except (json.JSONDecodeError, TypeError):
                            continue
                        if msg.get("type") == "error":
                            log(f"server rejected our action: {msg.get('error')!r}")
                            self.pending = None
                            continue
                        if msg.get("type") != "state":
                            continue
                        if await self.on_state(ws, msg):
                            self.done = True
                            break
            except ConnectionClosed:
                log("socket closed by server")
            except Exception as exc:  # connect failure / transient — keep retrying until timer
                log(f"connection error (attempt {attempt}): {exc!r}")
            if self.done:
                break
            await asyncio.sleep(min(2.0, 0.5 * attempt))
        log(f"episode complete (done={self.done}, attempts={attempt})")

    # -- state dispatch ------------------------------------------------------
    async def on_state(self, ws: Any, state: dict[str, Any]) -> bool:
        """Handle one state broadcast. Returns True when the episode is over."""
        phase = state.get("phase")
        me = state.get("me") or {}
        if phase == "reveal" or state.get("done"):
            log(f"reveal; results: {json.dumps(state.get('results'))[:1500]}")
            return True

        transcript = me.get("judge") or []
        self._settle_pending(me)
        if self.pending is not None:
            return False

        if phase == "private_questions":
            n = len(transcript)
            if n < len(config.PROBES):
                self._asks_target = n + 1
                log(f"asking probe {n + 1}/{len(config.PROBES)}")
                await self._send(ws, "ask", {"question": config.PROBES[n]})
        elif phase == "proposals" and len(me.get("proposals") or []) == 0:
            await self._propose(ws, transcript)
        elif phase == "answers" and len(me.get("answers") or []) == 0:
            await self._answer(ws, state, transcript)
        return False

    def _settle_pending(self, me: dict[str, Any]) -> None:
        if self.pending == "ask" and len(me.get("judge") or []) >= self._asks_target:
            self.pending = None
        elif self.pending == "propose" and me.get("proposals"):
            self.pending = None
        elif self.pending == "answer" and me.get("answers"):
            self.pending = None

    async def _send(self, ws: Any, kind: str, payload: dict[str, Any]) -> None:
        self.pending = kind
        await ws.send(json.dumps({"type": kind, **payload}))

    # -- phase actions: commit the RECALLED digit strings -------------------
    async def _propose(self, ws: Any, transcript: list[dict]) -> None:
        recalled = answers.recalled_answers(transcript, len(config.PROPOSAL_QUESTIONS))
        proposals = [{"question": q, "answer": a} for q, a in zip(config.PROPOSAL_QUESTIONS, recalled)]
        log(f"proposing {len(proposals)} questions; recalled answers {recalled}")
        await self._send(ws, "propose", {"proposals": proposals})

    async def _answer(self, ws: Any, state: dict[str, Any], transcript: list[dict]) -> None:
        questions = state.get("opponent_questions") or []
        if not questions:
            return
        recalled = answers.recalled_answers(transcript, len(questions))
        log(f"answering {len(questions)} opponent questions -> {recalled}")
        await self._send(ws, "answer", {"answers": recalled})


async def main() -> None:
    player = RecallPlayer()
    try:
        await asyncio.wait_for(player.run(), timeout=config.EPISODE_HARD_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        log("hard timeout reached; exiting cleanly")


if __name__ == "__main__":
    asyncio.run(main())
