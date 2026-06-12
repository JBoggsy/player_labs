"""The mentalist harness: WebSocket loop + state-driven phase dispatch.

Server contract (verified against v2/coworld/game.py @ cue_n_woo 0.2.x):
- On connect the server sends our slot view; after EVERY action by EITHER
  player it broadcasts a fresh state to all clients (so every action we send
  is followed by at least one inbound message — no polling needed).
- `ask` is handled synchronously: the judge's generated answer is appended to
  `me.judge` before the post-action broadcast, so transcript length is the
  reliable "my ask landed" signal.
- Phases are global (gated on BOTH players), so we may receive many states for
  a phase we already acted in; all idempotence is derived from the counts in
  the state itself plus a single `pending` in-flight guard.
- The server closes the socket once the final action triggers scoring; for the
  last actor that close can race a recv — it is the end-of-game signal, not an
  error.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed

from . import config
from .classifier import StyleClassifier, StyleMatch
from .writer import BedrockWriter


def log(msg: str) -> None:
    print(f"[mentalist] {msg}", file=sys.stderr, flush=True)


class Mentalist:
    def __init__(self) -> None:
        self.classifier = StyleClassifier(featurizer=config.CLASSIFIER_FEATURIZER)
        self.writer = BedrockWriter()
        self.pending: str | None = None  # action type in flight, cleared by counts/error
        self._asks_target = 0  # transcript length that confirms our latest ask landed
        self.style_matches: list[StyleMatch] | None = None
        self.last_error: str | None = None
        self.llm_rejections = {"propose": 0, "answer": 0}

    # -- entry ---------------------------------------------------------------

    async def run(self) -> None:
        url = os.environ["COWORLD_PLAYER_WS_URL"]
        log(f"connecting to {url}")
        try:
            async with websockets.connect(url, ping_interval=None, max_size=None) as ws:
                async for raw in ws:
                    msg = json.loads(raw)
                    if msg.get("type") == "error":
                        self.last_error = msg.get("error", "unknown validation error")
                        log(f"server rejected our action: {self.last_error}")
                        if self.pending in self.llm_rejections:
                            self.llm_rejections[self.pending] += 1
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
            if n < len(config.PRIVATE_QUESTIONS):
                question = config.PRIVATE_QUESTIONS[n]
                log(f"asking private question {n + 1}/3")
                self._asks_target = n + 1
                await self._send(ws, "ask", {"question": question})
        elif phase == "proposals" and len(me.get("proposals") or []) == 0:
            await self._propose(ws, state, transcript)
        elif phase == "answers" and len(me.get("answers") or []) == 0:
            await self._answer(ws, state, transcript)
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

    # -- phase actions ---------------------------------------------------------

    def _classify(self, transcript: list[dict[str, str]]) -> list[StyleMatch]:
        if self.style_matches is None:
            answers = [t.get("answer", "") for t in transcript]
            self.style_matches = self.classifier.classify(answers, top_n=3)
            pretty = " | ".join(f"{m.style[:50]!r}={m.score:.3f}" for m in self.style_matches)
            log(f"classified style: {pretty}")
        return self.style_matches

    async def _propose(self, ws: Any, state: dict[str, Any], transcript: list[dict[str, str]]) -> None:
        matches = self._classify(transcript)
        questions = list(config.PROPOSAL_QUESTIONS)
        if self._use_fallback("propose", state):
            answers = [self.writer.fallback_answer(q, matches) for q in questions]
        else:
            error = self.last_error
            self.last_error = None
            answers = await asyncio.to_thread(
                self.writer.proposal_answers, matches, transcript, questions, error
            )
        log(f"proposing; secret answers: {answers}")
        proposals = [{"question": q, "answer": a} for q, a in zip(questions, answers)]
        await self._send(ws, "propose", {"proposals": proposals})

    async def _answer(self, ws: Any, state: dict[str, Any], transcript: list[dict[str, str]]) -> None:
        matches = self._classify(transcript)
        questions = [q.get("question", "") for q in state.get("opponent_questions") or []]
        if not questions:
            return
        if self._use_fallback("answer", state):
            answers = [self.writer.fallback_answer(q, matches) for q in questions]
        else:
            error = self.last_error
            self.last_error = None
            answers = await asyncio.to_thread(
                self.writer.blind_answers, matches, transcript, questions, error
            )
        log(f"answering opponent questions {questions} -> {answers}")
        await self._send(ws, "answer", {"answers": answers})

    def _use_fallback(self, kind: str, state: dict[str, Any]) -> bool:
        if self.llm_rejections[kind] > config.LLM_VALIDATION_RETRIES:
            log(f"{kind}: too many server rejections; using deterministic fallback")
            return True
        remaining = int(state.get("remaining_seconds") or 0)
        if remaining < config.LOW_TIME_FALLBACK_SECONDS:
            log(f"{kind}: only {remaining}s left; skipping LLM, using fallback")
            return True
        return False


async def main() -> None:
    player = Mentalist()
    try:
        await asyncio.wait_for(player.run(), timeout=config.EPISODE_HARD_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        log("hard timeout reached; exiting cleanly")


if __name__ == "__main__":
    asyncio.run(main())
