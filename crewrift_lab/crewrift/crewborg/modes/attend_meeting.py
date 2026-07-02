"""Attend Meeting mode: conversational chat plus deadline-safe voting."""

from __future__ import annotations

import math
import os
from typing import Any, Callable

from crewrift.crewborg.strategy.meeting import (
    CHAT_MAX_CHARS,
    VOTE_SKIP,
    MeetingDecision,
    MeetingDecisionValidationError,
    MeetingLLMClient,
    build_meeting_llm_client_from_env,
    serialize_meeting_context,
    valid_vote_targets,
    validate_meeting_decision,
)
from crewrift.crewborg.strategy.meeting.accusation import build_accusation, fabricate_accusation
from crewrift.crewborg.strategy.meeting.context import (
    CHAT_COOLDOWN_TICKS,
    VOTE_TIMER_TICKS,
)
from crewrift.crewborg.strategy.meeting.imposter import (
    bandwagon_target,
    parity_closing_vote_target,
    votes_against,
)
from crewrift.crewborg.strategy.meeting import chat_nlp, chat_read
from crewrift.crewborg.strategy.meeting.schema import normalize_vote_target
from crewrift.crewborg.strategy.meeting.worker import MeetingLLMRequest, MeetingLLMWorker
from crewrift.crewborg.strategy.suspicion import chat_suspect, top_suspect, witnessed_imposters
from crewrift.crewborg.types import ActionState, Belief, ChatEvent, Intent
from players.player_sdk import EmptyModeParams, Mode

# Min ticks between LLM calls. 12 (one visual state) exploded into ~5x call volume at
# the 1200-tick meetings and exhausted the Bedrock daily token quota (v86: 800 429s);
# 120 (~5s) keeps a multi-turn conversation while staying inside the per-meeting budget.
LLM_MIN_CALL_INTERVAL_TICKS = 120
# Hard per-meeting call cap, on top of the interval (env-overridable).
LLM_CALL_BUDGET_ENV = "CREWBORG_LLM_MEETING_CALL_BUDGET"
DEFAULT_LLM_CALL_BUDGET = 5
DEADLINE_LLM_REMAINING_TICKS = 96
AUTO_SUBMIT_REMAINING_TICKS = 48
# The sim's real tick rate (24/s). Deliberately NOT derived from VOTE_TIMER_TICKS —
# the timer length changed (240→1200) but the tick rate did not; deriving it would
# corrupt the LLM latency-guard's seconds→ticks conversion.
MEETING_TICKS_PER_SECOND = 24
LLM_TIMEOUT_MARGIN_TICKS = 12
DEFAULT_LLM_TIMEOUT_SECONDS = 3.0
# Early-submit a tentative vote (LLM idle) once under half the believed time remains —
# the belief clock can lag real time, and a submitted vote can't be lost to vote_timeout.
EARLY_SUBMIT_REMAINING_FRACTION = 0.5


class AttendMeetingMode(Mode[Belief, ActionState, Intent]):
    name = "attend_meeting"
    params_type = EmptyModeParams

    def __init__(
        self,
        params=None,
        *,
        llm_client: MeetingLLMClient | None = None,
        llm_worker_factory: Callable[[MeetingLLMClient], MeetingLLMWorker] | None = None,
    ) -> None:
        super().__init__(params)
        self._llm_client = llm_client if llm_client is not None else build_meeting_llm_client_from_env()
        self._llm_worker_factory = llm_worker_factory if llm_worker_factory is not None else MeetingLLMWorker
        self._worker: MeetingLLMWorker | None = None
        self._llm_request_id = 0  # monotonic across meetings so stale deliveries are dropped
        self._llm_pending: MeetingLLMRequest | None = None
        self._llm_calls_used = 0
        self._llm_call_budget = _llm_call_budget_from_env()
        self._chat_accused: str | None = None
        self._meeting_id: int | None = None
        self._deterministic_chatted = False
        self._disabled_traced = False
        self._sent_chat_texts: set[str] = set()
        self._pending_chat_text: str | None = None
        self._last_chat_tick: int | None = None
        self._last_llm_call_tick: int | None = None
        self._last_external_chat_signature: tuple[tuple[int, str | None, str], ...] = ()
        self._last_cooldown_prompt_chat_tick: int | None = None
        self._deadline_prompted = False
        self._tentative_vote: str | None = None
        # Targets the LLM itself named in a *submit_vote* decision — the only
        # LLM-sourced corroboration for the fallback vote gate (v89). v88 counted any
        # LLM-named target (set_tentative_vote / a vote_target riding on a chat), but
        # the prompt rides vote_target on ~every chat, so that gate never fired
        # (0/35 eps) and the LLM-named-tentative clause fed 10 wrong vs 3 right votes.
        self._llm_submitted_vote_targets: set[str] = set()
        self._active_vote_target: str | None = None
        self._active_vote_reason: str = ""
        self._vote_submitted = False
        self._dead_mute_traced = False
        self._chat_parse_cache: dict[str, set[str]] = {}
        self._decision_traced = False

    def is_legal(self, belief: Belief) -> bool:
        return belief.phase == "Voting"

    def decide(self, belief: Belief, action_state: ActionState) -> Intent:
        self._reset_for_meeting_if_needed(belief)
        if action_state.vote_confirmed:
            self._vote_submitted = True
            self._active_vote_target = None
            self._active_vote_reason = ""
        if self._vote_submitted:
            return Intent(kind="idle", reason="vote already confirmed")
        if self._active_vote_target is not None:
            return self._vote_intent(self._active_vote_target, reason=self._active_vote_reason)

        if not self._llm_client.enabled:
            return self._decide_deterministic(belief, trace_disabled=True)

        if not belief.self_alive:
            # Dead seats' meeting inputs are ignored by the sim (0 post-death vote_cast
            # across the v87 league replays), yet dead crewborg seats burned ~23% of
            # meeting-LLM call volume — pure Bedrock rate pressure on the live seats.
            # Mute everything: no LLM calls, no chats, no vote submits; idle through
            # the meeting. The deterministic (LLM-off) branch above is untouched.
            if not self._dead_mute_traced:
                self._dead_mute_traced = True
                self.emit.event("meeting_dead_mute", {"tick": belief.last_tick})
                self.emit.counter("meeting_dead_mute")
            return Intent(kind="idle", reason="dead: meeting inputs ignored, LLM muted")

        intent = self._collect_llm_outcome(belief)
        if intent is not None:
            return intent

        if self._should_auto_submit(belief):
            return self._submit_vote_intent(belief, reason="meeting deadline: auto-submit tentative vote")

        if self._pending_chat_text is not None and self._chat_cooldown_ready(belief):
            return self._send_chat_intent(belief, self._pending_chat_text, reason="sending pending LLM chat")

        if self._should_early_submit(belief):
            return self._submit_vote_intent(belief, reason="early submit: tentative vote, LLM idle")

        if self._llm_pending is not None:
            return Intent(kind="idle", reason="waiting for meeting LLM result")

        trigger = self._next_llm_trigger(belief)
        if trigger is None:
            return Intent(kind="idle", reason="waiting during meeting")

        context = serialize_meeting_context(
            belief,
            trigger=trigger,
            tentative_vote=self._tentative_vote,
            sent_chat_texts=self._sent_chat_texts,
            last_chat_tick=self._last_chat_tick,
        )
        self.emit.event("meeting_context_serialized", {"trigger": trigger, "context": context})
        self._submit_llm_request(context, trigger=trigger)
        return Intent(kind="idle", reason=f"meeting LLM call in flight ({trigger})")

    def on_exit(self, belief: Belief, action_state: ActionState, next_directive) -> None:
        if self._worker is not None:
            self._worker.close()
            self._worker = None

    # --- deterministic fallback ------------------------------------------

    def _decide_deterministic(self, belief: Belief, *, trace_disabled: bool) -> Intent:
        """No default-firing chat; chat and vote are always coupled (accuse exactly who
        we vote — the anti-tell). The two roles diverge here (design §10.4)."""

        if trace_disabled and not self._disabled_traced:
            self._disabled_traced = True
            self.emit.event(
                "meeting_llm_fallback",
                {"reason": "llm_disabled", "detail": self._llm_client.disabled_reason},
            )
        if belief.self_role == "imposter":
            return self._decide_imposter(belief)
        return self._decide_crewmate(belief)

    def _decide_crewmate(self, belief: Belief) -> Intent:
        """Accuse + vote a clear leading suspect; else SHARE a read on a softer suspect
        (chat only, no vote) rather than going silent — vote restraint is unchanged."""

        if not self._deterministic_chatted:
            self._deterministic_chatted = True
            target = top_suspect(belief)  # the clear leading suspect, or None (flat field)
            if target is not None:
                self._tentative_vote = target  # couple the vote to whoever we accuse
                accusation = build_accusation(belief, target)
                if accusation is not None:
                    self._trace_meeting_decision(belief, role="crewmate", path="accuse", target=target)
                    return self._send_chat_intent(belief, accusation, reason="accusing clear suspect")
                self._trace_meeting_decision(belief, role="crewmate", path="vote_no_chat", target=target)
            else:
                # No clear suspect to VOTE — but voice an evidence-cited read instead of
                # going silent (chat only; we still skip the vote on a thin field).
                soft = chat_suspect(belief)
                read = build_accusation(belief, soft) if soft is not None else None
                if read is not None:
                    self._trace_meeting_decision(belief, role="crewmate", path="share_read", target=soft)
                    return self._send_chat_intent(belief, read, reason="sharing read (no vote)")
                self._trace_meeting_decision(belief, role="crewmate", path="silent_skip", target=None)
        return self._submit_vote_intent(belief, reason="deterministic meeting vote")

    def _decide_imposter(self, belief: Belief) -> Intent:
        """Deflect onto crewmates, never teammates. Prefer a **real** accusation against
        a non-teammate who genuinely looks sus; otherwise wait and **bandwagon** onto a
        crewmate others are sussing/voting, with *fabricated* (safe) evidence in the
        identical format; if nobody takes heat, skip at the deadline."""

        # Already accused someone ⇒ stay coupled: vote exactly them.
        if self._deterministic_chatted and self._tentative_vote is not None:
            return self._submit_vote_intent(belief, reason="imposter: vote whom we accused")

        # 1. Proactive deflection — a non-teammate with strong, real citable evidence.
        target = top_suspect(belief)
        if target is not None:
            accusation = build_accusation(belief, target)
            if accusation is not None:
                self._tentative_vote = target
                self._deterministic_chatted = True
                self._trace_meeting_decision(belief, role="imposter", path="proactive", target=target)
                return self._send_chat_intent(belief, accusation, reason="imposter deflect: real evidence")

        # 2. Reactive bandwagon — a crewmate already taking heat (votes + chat).
        accusers = self._chat_accusers(belief)
        bandwagon = bandwagon_target(belief, accusers)
        if bandwagon is not None:
            self._tentative_vote = bandwagon
            self._deterministic_chatted = True
            fabricated = fabricate_accusation(belief, bandwagon)
            self._trace_meeting_decision(
                belief, role="imposter", path="bandwagon", target=bandwagon,
                fabricated=fabricated is not None, accusers=accusers,
            )
            if fabricated is not None:
                return self._send_chat_intent(belief, fabricated, reason="imposter bandwagon: fabricated")
            return self._submit_vote_intent(belief, reason="imposter bandwagon vote")

        # 3. Parity-closing push — one removal from a win and no crewmate is taking
        #    heat on their own, so MANUFACTURE the pile instead of skipping it away
        #    (the dominant imposter loss is stalling at 3-crew/2-imp; design §10.4).
        parity_target = parity_closing_vote_target(belief, accusers)
        if parity_target is not None:
            self._tentative_vote = parity_target
            self._deterministic_chatted = True
            fabricated = fabricate_accusation(belief, parity_target)
            self._trace_meeting_decision(
                belief, role="imposter", path="parity_push", target=parity_target,
                fabricated=fabricated is not None, accusers=accusers,
            )
            if fabricated is not None:
                return self._send_chat_intent(belief, fabricated, reason="imposter parity push: fabricated")
            return self._submit_vote_intent(belief, reason="imposter parity push vote")

        # 4. No one to deflect onto yet — wait, then skip at the deadline.
        if self._should_auto_submit(belief):
            self._trace_meeting_decision(belief, role="imposter", path="skip", target=None, accusers=accusers)
            return self._submit_vote_intent(belief, reason="imposter deadline: no deflection, skip")
        return Intent(kind="idle", reason="imposter waiting for a crewmate to take heat")

    def _trace_meeting_decision(
        self,
        belief: Belief,
        *,
        role: str,
        path: str,
        target: str | None,
        fabricated: bool = False,
        accusers: dict[str, int] | None = None,
    ) -> None:
        """One structured record of the deterministic meeting decision, fired once when
        we commit. The headline diagnostic for the new meeting modes: which path
        (accuse / silent_skip · proactive / bandwagon / skip), the target, real vs
        fabricated, and — for an imposter — the heat that drove it (vote tally + chat
        accusers) and the chat-NLP state, so a replay explains *why* it did what it did."""

        if self._decision_traced:
            return
        self._decision_traced = True
        data: dict[str, Any] = {
            "role": role,
            "path": path,
            "target": target,
            "fabricated": fabricated,
            "top_suspect": top_suspect(belief),
        }
        if role == "imposter":
            data["votes"] = votes_against(belief)
            data["chat_accusers"] = accusers if accusers is not None else {}
            data["nlp"] = chat_nlp.state()
        self.emit.event("meeting_decision", data)
        self.emit.counter("meeting_decision", tags={"role": role, "path": path})

    def _chat_accusers(self, belief: Belief) -> dict[str, int]:
        """Per-color count of *other players* who have accused them in chat — the
        additive bandwagon signal (empty when the chat-NLP model is off / still
        loading). The per-meeting cache avoids re-parsing the same messages each tick."""

        return chat_read.chat_accusers(belief, cache=self._chat_parse_cache)

    # --- LLM call cadence -------------------------------------------------

    def _next_llm_trigger(self, belief: Belief) -> str | None:
        tick = belief.last_tick
        if self._llm_calls_used >= self._llm_call_budget:
            return None
        if self._last_llm_call_tick is not None and tick - self._last_llm_call_tick < LLM_MIN_CALL_INTERVAL_TICKS:
            return None
        if not self._can_start_llm_call(belief):
            return None
        if self._deadline_prompted:
            return None
        if self._last_llm_call_tick is None:
            return "meeting_start"

        if self._remaining_ticks(belief) <= self._deadline_prompt_remaining_ticks():
            return "deadline"

        signature = self._external_chat_signature(belief)
        if signature != self._last_external_chat_signature:
            return "new_chat"

        if (
            self._last_chat_tick is not None
            and self._chat_cooldown_ready(belief)
            and self._last_cooldown_prompt_chat_tick != self._last_chat_tick
        ):
            return "chat_cooldown_ready"

        return None

    def _submit_llm_request(self, context: dict[str, Any], *, trigger: str) -> None:
        """Hand the call to the background worker and return immediately.

        The blocking call is the v86 root cause (each ~3s call stalled the loop, lagged
        the belief clock, and lost selected votes to vote_timeout); the mode now only
        submits here and picks the outcome up in ``_collect_llm_outcome`` on a later tick.
        """

        self._last_llm_call_tick = int(context["meeting"]["tick"])
        self._last_external_chat_signature = tuple(
            (event["tick"], event["speaker_color"], event["text"])
            for event in context["chat"]["messages"]
            if not event["self"]
        )
        if trigger == "deadline":
            self._deadline_prompted = True
        if trigger == "chat_cooldown_ready":
            self._last_cooldown_prompt_chat_tick = self._last_chat_tick
        self._llm_calls_used += 1
        self._llm_request_id += 1
        request = MeetingLLMRequest(request_id=self._llm_request_id, trigger=trigger, context=context)
        self._llm_pending = request
        self.emit.event(
            "meeting_llm_call",
            {
                "trigger": trigger,
                "request_id": request.request_id,
                "calls_used": self._llm_calls_used,
                "call_budget": self._llm_call_budget,
            },
        )
        if self._llm_calls_used >= self._llm_call_budget:
            self.emit.event("meeting_llm_budget_exhausted", {"call_budget": self._llm_call_budget})
        self._ensure_worker().requests.publish(request)

    def _collect_llm_outcome(self, belief: Belief) -> Intent | None:
        """Non-blocking pickup of the pending call's outcome; ``None`` = nothing yet."""

        if self._worker is None or self._llm_pending is None:
            return None
        outcome = self._worker.results.take()
        if outcome is None:
            return None
        if outcome.request_id != self._llm_pending.request_id:
            return None  # stale delivery (earlier meeting/request) — drop, keep waiting
        trigger = outcome.trigger
        self._llm_pending = None
        if outcome.error is not None or outcome.result is None:
            self.emit.event(
                "meeting_llm_fallback",
                {"reason": "llm_call_failed", "trigger": trigger, "error": outcome.error},
            )
            return self._decide_after_llm_failure(belief, trigger)
        result = outcome.result
        self.emit.histogram("meeting_llm.latency_ms", result.latency_ms, tags={"model": result.model, "trigger": trigger})
        decision = self._validate_decision(belief, result.decision)
        if decision is None:
            return self._decide_after_llm_failure(belief, trigger)
        self._trace_decision(trigger, decision, result)
        return self._apply_decision(belief, decision)

    def _ensure_worker(self) -> MeetingLLMWorker:
        if self._worker is None:
            self._worker = self._llm_worker_factory(self._llm_client)
            self._worker.start()
        return self._worker

    def _validate_decision(self, belief: Belief, decision: MeetingDecision) -> MeetingDecision | None:
        try:
            validated = validate_meeting_decision(
                decision,
                alive_vote_targets=valid_vote_targets(belief),
                current_tentative=self._tentative_vote,
                fallback_vote=self._fallback_vote_target(belief),
            )
            # Only a target the LLM itself named in a submit_vote counts as LLM-decided
            # for the vote gate (v89). A submit_vote with no target gets the
            # tentative/fallback backfilled by validation, and that backfill is NOT
            # corroboration; nor is a tentative or a vote_target riding on a chat —
            # the prompt attaches one to ~every chat, which made the v88 gate a no-op.
            if (
                decision.action == "submit_vote"
                and normalize_vote_target(decision.vote_target) is not None
                and validated.vote_target not in (None, VOTE_SKIP)
            ):
                self._llm_submitted_vote_targets.add(validated.vote_target)
            return validated
        except MeetingDecisionValidationError as exc:
            self.emit.event(
                "meeting_llm_fallback",
                {"reason": "invalid_meeting_decision", "error": str(exc), "decision": decision.model_dump(mode="json")},
            )
            return None

    def _trace_decision(self, trigger: str, decision: MeetingDecision, result: Any) -> None:
        self.emit.event(
            "meeting_llm_decision",
            {
                "trigger": trigger,
                "model": result.model,
                "latency_ms": round(result.latency_ms, 2),
                "usage": result.usage,
                "decision": decision.model_dump(mode="json"),
            },
        )
        if result.raw_request is not None or result.raw_response is not None:
            self.emit.event(
                "meeting_llm_debug",
                {"request": result.raw_request, "response": result.raw_response},
            )

    # --- decision application --------------------------------------------

    def _apply_decision(self, belief: Belief, decision: MeetingDecision) -> Intent:
        if decision.vote_target is not None:
            self._tentative_vote = decision.vote_target
            self.emit.event(
                "meeting_tentative_vote",
                {"target": self._tentative_vote, "reason": decision.reason, "confidence": decision.confidence},
            )

        if decision.action == "send_chat":
            assert decision.chat_text is not None
            if decision.chat_text in self._sent_chat_texts:
                self.emit.event("meeting_llm_fallback", {"reason": "duplicate_chat_suppressed", "text": decision.chat_text})
                return Intent(kind="idle", reason="duplicate LLM chat suppressed")
            if self._chat_cooldown_ready(belief):
                return self._send_chat_intent(belief, decision.chat_text, reason=decision.reason or "LLM meeting chat")
            self._pending_chat_text = decision.chat_text[:CHAT_MAX_CHARS]
            self.emit.event(
                "meeting_llm_fallback",
                {"reason": "chat_cooldown_pending", "text": self._pending_chat_text},
            )
            return Intent(kind="idle", reason="waiting for chat cooldown")

        if decision.action == "submit_vote":
            return self._submit_vote_intent(belief, reason=decision.reason or "LLM submitted vote")

        if decision.action == "set_tentative_vote":
            return Intent(kind="idle", reason=decision.reason or "LLM set tentative vote")

        return Intent(kind="idle", reason=decision.reason or "LLM waits")

    def _send_chat_intent(self, belief: Belief, text: str, *, reason: str) -> Intent:
        self._pending_chat_text = None
        self._sent_chat_texts.add(text)
        self._last_chat_tick = belief.last_tick
        if self._llm_client.enabled:  # keep the LLM-off path byte-identical
            self._note_own_accusation(belief, text)
        self.emit.event("meeting_chat_selected", {"text": text, "reason": reason})
        return Intent(kind="chat", text=text, reason=reason)

    def _note_own_accusation(self, belief: Belief, text: str) -> None:
        """Track whom our own chat accused: the chat-implied fallback vote.

        v86's headline crew failure was confident-chat-then-skip — the LLM accused a
        color in chat, the follow-up vote call failed (429/timeout), and the fallback
        collapsed to the 0.9-gate skip. If we said it, we should vote it."""

        accused = chat_read.accused_colors(text, set(belief.roster))
        self_color = belief.self_color or belief.voting.self_marker_color
        accused -= belief.teammate_colors | {self_color}
        if not accused:
            return
        self._chat_accused = max(accused, key=lambda color: belief.suspicion.get(color, 0.0))
        self.emit.event("meeting_chat_implied_vote", {"target": self._chat_accused, "text": text})

    def _submit_vote_intent(self, belief: Belief, *, reason: str) -> Intent:
        vote_target = self._resolved_vote_target(belief)
        if self._llm_client.enabled and not self._vote_target_corroborated(belief, vote_target):
            # Confidence gate on fallback-sourced crew PLAYER votes (v88, tightened
            # v89). Pooled v87+v88 leagues: fallback-resolved crew votes hit imposters
            # 7/34 (21%) vs LLM-submitted 28/37 (76%), Fisher p=4e-6 — active friendly
            # fire. An uncorroborated fallback guess becomes a neutral skip; the vote
            # still submits, so timeouts stay at 0. NOT a global 0.9 re-gate: targets
            # the LLM explicitly submit_vote'd pass via _llm_submitted_vote_targets.
            self.emit.event("meeting_vote_gated", {"target": vote_target, "reason": reason})
            self.emit.counter("meeting_vote_gated")
            vote_target = VOTE_SKIP
        # Hard guard: the agent can never vote itself out, whatever suspicion says.
        self_color = belief.self_color or belief.voting.self_marker_color
        if self_color is not None and vote_target == self_color:
            vote_target = VOTE_SKIP
        self._active_vote_target = vote_target
        self._active_vote_reason = reason
        self.emit.event("meeting_vote_selected", {"target": vote_target, "reason": reason})
        return self._vote_intent(vote_target, reason=reason)

    def _vote_intent(self, vote_target: str, *, reason: str) -> Intent:
        if vote_target == VOTE_SKIP:
            return Intent(kind="vote", reason=reason)
        return Intent(kind="vote", target_color=vote_target, reason=reason)

    def _decide_after_llm_failure(self, belief: Belief, trigger: str) -> Intent:
        if trigger == "deadline":
            return self._submit_vote_intent(belief, reason=f"LLM fallback after {trigger}")
        if trigger == "meeting_start":
            return self._decide_deterministic(belief, trace_disabled=False)
        return Intent(kind="idle", reason=f"LLM fallback after {trigger}")

    # --- state helpers ----------------------------------------------------

    def _reset_for_meeting_if_needed(self, belief: Belief) -> None:
        meeting_id = belief.phase_start_tick
        if meeting_id == self._meeting_id:
            return
        self._meeting_id = meeting_id
        # A still-running call from the previous meeting delivers against a stale
        # request_id and is dropped in _collect_llm_outcome; the id itself never resets.
        self._llm_pending = None
        self._llm_calls_used = 0
        self._chat_accused = None
        self._deterministic_chatted = False
        self._disabled_traced = False
        self._sent_chat_texts.clear()
        self._pending_chat_text = None
        self._last_chat_tick = None
        self._last_llm_call_tick = None
        self._last_external_chat_signature = self._external_chat_signature(belief)
        self._last_cooldown_prompt_chat_tick = None
        self._deadline_prompted = False
        self._tentative_vote = None
        self._llm_submitted_vote_targets = set()
        self._active_vote_target = None
        self._active_vote_reason = ""
        self._vote_submitted = False
        self._dead_mute_traced = False
        self._chat_parse_cache = {}
        self._decision_traced = False

    def _external_chat_signature(self, belief: Belief) -> tuple[tuple[int, str | None, str], ...]:
        self_color = belief.voting.self_marker_color
        return tuple(
            (event.tick, event.speaker_color, event.text)
            for event in belief.chat_log
            if self._is_external_chat(event, self_color)
        )

    def _is_external_chat(self, event: ChatEvent, self_color: str | None) -> bool:
        if event.speaker_color is not None and event.speaker_color == self_color:
            return False
        return event.text not in self._sent_chat_texts

    def _chat_cooldown_ready(self, belief: Belief) -> bool:
        return self._last_chat_tick is None or belief.last_tick - self._last_chat_tick >= CHAT_COOLDOWN_TICKS

    def _remaining_ticks(self, belief: Belief) -> int:
        return max(0, VOTE_TIMER_TICKS - max(0, belief.last_tick - belief.phase_start_tick))

    def _should_auto_submit(self, belief: Belief) -> bool:
        return not self._vote_submitted and self._remaining_ticks(belief) <= AUTO_SUBMIT_REMAINING_TICKS

    def _should_early_submit(self, belief: Belief) -> bool:
        """Submit a tentative vote early instead of holding it for the believed-clock
        deadline: the belief clock can lag, and a submitted vote can't be lost to
        vote_timeout. Only once the LLM can no longer usefully revise it — call budget
        spent, or under half the believed time remains — and never over a pending chat
        (send that first; the vote ends our participation) or a bare skip (submitting
        skip early gains nothing and forfeits a later real vote)."""

        if self._tentative_vote is None or self._tentative_vote == VOTE_SKIP:
            return False
        if not self._vote_target_corroborated(belief, self._tentative_vote):
            # The gate would turn this into a skip; early-submitting a skip forfeits
            # a later real vote (same rule as a tentative skip). Hold — the deadline
            # auto-submit still fires and gates it there, so timeouts stay 0.
            return False
        if self._llm_pending is not None or self._pending_chat_text is not None:
            return False
        return (
            self._llm_calls_used >= self._llm_call_budget
            or self._remaining_ticks(belief) < VOTE_TIMER_TICKS * EARLY_SUBMIT_REMAINING_FRACTION
        )

    def _can_start_llm_call(self, belief: Belief) -> bool:
        """Whether a call started now can still deliver before auto-submit. Calls never
        block the loop anymore; this only avoids spending budget on an answer that
        would arrive after the fallback vote is already in."""

        return self._remaining_ticks(belief) > self._latest_safe_llm_start_remaining_ticks()

    def _deadline_prompt_remaining_ticks(self) -> int:
        return max(DEADLINE_LLM_REMAINING_TICKS, self._latest_safe_llm_start_remaining_ticks() + 1)

    def _latest_safe_llm_start_remaining_ticks(self) -> int:
        timeout_ticks = math.ceil(self._llm_timeout_seconds() * MEETING_TICKS_PER_SECOND)
        return AUTO_SUBMIT_REMAINING_TICKS + timeout_ticks + LLM_TIMEOUT_MARGIN_TICKS

    def _llm_timeout_seconds(self) -> float:
        value = getattr(self._llm_client, "timeout_seconds", DEFAULT_LLM_TIMEOUT_SECONDS)
        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            return DEFAULT_LLM_TIMEOUT_SECONDS

    def _vote_target_corroborated(self, belief: Belief, target: str) -> bool:
        """Whether a resolved vote target is safe to submit on the LLM-enabled path.

        Crew only: an imposter's fallback deflection votes (bandwagon / parity push)
        mis-eject crew ON PURPOSE, and suspicion is empty for imposters anyway.
        A crew player-vote needs one of: we witnessed them kill/vent, the fitted
        posterior clears the vote bar (``top_suspect``), or the LLM itself issued a
        submit_vote naming them. A chat-implied guess, an LLM tentative / chat-riding
        vote_target, or a backfilled tentative fails all three and is converted to
        skip by the caller (v89: the wider LLM-named arm fed 10 wrong vs 3 right).
        """

        if target == VOTE_SKIP or belief.self_role == "imposter":
            return True
        if target in self._llm_submitted_vote_targets:
            return True
        if target in witnessed_imposters(belief):
            return True
        return top_suspect(belief) == target

    def _resolved_vote_target(self, belief: Belief) -> str:
        tentative = self._tentative_vote
        if tentative is not None and (tentative == VOTE_SKIP or tentative in valid_vote_targets(belief)):
            return tentative
        return self._fallback_vote_target(belief)

    def _fallback_vote_target(self, belief: Belief) -> str:
        """Prefer whom we accused in our own chat this meeting (never chat-then-skip),
        then the suspicion vote bar, then skip. ``_chat_accused`` is only ever set on
        the LLM path, so the deterministic (LLM-off) vote is unchanged."""

        if self._chat_accused is not None and self._chat_accused in valid_vote_targets(belief):
            return self._chat_accused
        return top_suspect(belief) or VOTE_SKIP


def _llm_call_budget_from_env() -> int:
    raw = os.environ.get(LLM_CALL_BUDGET_ENV)
    if raw is None:
        return DEFAULT_LLM_CALL_BUDGET
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_LLM_CALL_BUDGET
