"""The cheater harness: WebSocket loop + state-driven phase dispatch.

Same server contract as mentalist (verified against v2/coworld/game.py @
cue_n_woo 0.2.x) — see ../mentalist/player.py for the full notes. The relevant
points:
- After EVERY action by either player the server broadcasts a fresh state, so
  every action we send is followed by an inbound message (no polling).
- `ask` is synchronous: the judge's answer is appended to `me.judge` before the
  post-action broadcast, so transcript length confirms our ask landed.
- Phases are global, so we may see many states for a phase we already acted in;
  idempotence comes from the counts in the state plus a single in-flight guard.
- The socket close after the final action is the end-of-game signal, not error.

cheater's policy is fixed and needs no classifier or LLM (mission + evidence in
config.py). The "daveey" approach — a short, plain, fixed answer everywhere:
- private_questions: ask the 3 DISTINCT goblin-promoting probes (config.PROBES).
  These land in the "Reference material:" block the judge reads when scoring EVERY
  question, priming it toward goblin. v4: 3 different probes (one naming our exact
  answer in an identity frame) beat 3 identical copies by a seed-robust multi-point
  margin (cue_n_woo_lab/probe/confirm_idfirst.py).
- proposals: ask open-ended questions; commit "The goblin" as each secret answer.
- answers: blind-answer the opponent's questions with "The goblin" too.
All six answers are config.ANSWER via answers.goblin_answer().
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
    print(f"[cheater] {msg}", file=sys.stderr, flush=True)


class Cheater:
    def __init__(self) -> None:
        # action type in flight, cleared once a later state shows it landed
        self.pending: str | None = None
        # transcript length that confirms our latest ask landed
        self._asks_target = 0

    # -- entry ---------------------------------------------------------------

    async def run(self) -> None:
        url = os.environ["COWORLD_PLAYER_WS_URL"]
        log(f"connecting to {url}")
        try:
            async with websockets.connect(url, ping_interval=None, max_size=None) as ws:
                async for raw in ws:
                    msg = json.loads(raw)
                    if msg.get("type") == "error":
                        # cheater submits only fixed, pre-validated answers, so a
                        # rejection is unexpected; log it and drop the guard so we
                        # retry on the next broadcast rather than wedging.
                        log(f"server rejected our action: {msg.get('error')!r}")
                        self.pending = None
                        continue
                    if msg.get("type") != "state":
                        continue
                    if await self.on_state(ws, msg):
                        return
        except ConnectionClosed:
            log("socket closed by server (end of episode)")

    # -- state dispatch ------------------------------------------------------

    async def on_state(self, ws: Any, state: dict[str, Any]) -> bool:
        """Handle one state broadcast. Returns True when the episode is over."""
        phase = state.get("phase")
        me = state.get("me") or {}
        if phase == "reveal" or state.get("done"):
            log(f"reveal; results: {json.dumps(state.get('results'))[:2000]}")
            return True

        transcript = me.get("judge") or []
        self._settle_pending(me)
        if self.pending is not None:
            return False

        if phase == "private_questions":
            n = len(transcript)
            if n < len(config.PROBES):
                log(f"asking probe {n + 1}/{len(config.PROBES)}")
                self._asks_target = n + 1
                await self._send(ws, "ask", {"question": config.PROBES[n]})
        elif phase == "proposals" and len(me.get("proposals") or []) == 0:
            await self._propose(ws)
        elif phase == "answers" and len(me.get("answers") or []) == 0:
            await self._answer(ws, state)
        return False

    def _settle_pending(self, me: dict[str, Any]) -> None:
        """Clear the in-flight guard once the state shows the action landed."""
        if self.pending == "ask" and len(me.get("judge") or []) >= self._asks_target:
            self.pending = None
        elif self.pending == "propose" and me.get("proposals"):
            self.pending = None
        elif self.pending == "answer" and me.get("answers"):
            self.pending = None

    async def _send(self, ws: Any, kind: str, payload: dict[str, Any]) -> None:
        self.pending = kind
        await ws.send(json.dumps({"type": kind, **payload}))

    # -- phase actions -------------------------------------------------------

    async def _propose(self, ws: Any) -> None:
        """Submit our challenge questions, committing "The goblin" as each secret."""
        answer = answers.goblin_answer()
        proposals = [{"question": q, "answer": answer} for q in config.PROPOSAL_QUESTIONS]
        log(f"proposing {len(proposals)} questions; secret answer {answer!r}")
        await self._send(ws, "propose", {"proposals": proposals})

    async def _answer(self, ws: Any, state: dict[str, Any]) -> None:
        """Blind-answer every opponent question with the fixed "The goblin"."""
        questions = state.get("opponent_questions") or []
        if not questions:
            return
        answer = answers.goblin_answer()
        replies = [answer] * len(questions)
        log(f"answering {len(questions)} opponent questions -> {answer!r}")
        await self._send(ws, "answer", {"answers": replies})


async def main() -> None:
    player = Cheater()
    try:
        await asyncio.wait_for(player.run(), timeout=config.EPISODE_HARD_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        log("hard timeout reached; exiting cleanly")


if __name__ == "__main__":
    asyncio.run(main())
