"""Attend Meeting mode: conversational chat plus deadline-safe voting."""

from __future__ import annotations

import math
import os
import re
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
from crewrift.crewborg.strategy.meeting import chat_evidence, chat_nlp, spend
from crewrift.crewborg.strategy import honor_society, llm_spend
from crewrift.crewborg.strategy.meeting.schema import normalize_vote_target
from crewrift.crewborg.strategy.meeting.worker import MeetingLLMRequest, MeetingLLMWorker
from crewrift.crewborg.strategy.suspicion import (
    chat_evidence_contributions,
    chat_evidence_enabled,
    chat_suspect,
    counterfactual_top_suspect_no_chat,
    top_suspect,
    warm_anchor_suspect,
    witnessed_imposters,
)
from crewrift.crewborg.types import ActionState, Belief, ChatEvent, Intent
from players.player_sdk import EmptyModeParams, Mode

# Min ticks between LLM calls. 12 (one visual state) exploded into ~5x call volume at
# the 1200-tick meetings and exhausted the Bedrock daily token quota (v86: 800 429s);
# 120 (~5s) keeps a multi-turn conversation while staying inside the per-meeting budget.
# Env-tunable (CREWBORG_LLM_MIN_CALL_INTERVAL_TICKS) for cadence sweeps: the 2026-07-21
# v110 league arms showed 74.5% of calls 429ing on the shared daily-token pool with
# 3.1 calls/meeting — interval is one of the two levers (with the call budget).
LLM_MIN_CALL_INTERVAL_TICKS = 120
LLM_MIN_CALL_INTERVAL_ENV = "CREWBORG_LLM_MIN_CALL_INTERVAL_TICKS"
# Hard per-meeting call cap, on top of the interval (env-overridable).
LLM_CALL_BUDGET_ENV = "CREWBORG_LLM_MEETING_CALL_BUDGET"
DEFAULT_LLM_CALL_BUDGET = 5
# Rough per-call cost estimate (USD) for the spend guard: ~1.3K input + ~0.5K output on Haiku ≈
# a fraction of a cent; we keep this conservative so we stop BEFORE the sidecar 429s. When the
# sidecar reports a per-episode spend limit, we only issue a follow-up call if the remaining
# budget comfortably covers another one (RESERVE × estimate) — but we ALWAYS allow the first
# ("meeting_start") call of a meeting so we never go fully silent. Env-overridable.
LLM_CALL_COST_ESTIMATE_ENV = "CREWBORG_LLM_CALL_COST_USD"
DEFAULT_LLM_CALL_COST_USD = 0.004
LLM_SPEND_RESERVE_FACTOR = 1.5
DEADLINE_LLM_REMAINING_TICKS = 96
# 48 → 96 (2026-07-21 vote_timeout dig): the belief clock is stamped from QUEUED frames,
# so when meeting ticks run over the ~42ms frame budget the client falls behind the
# server and "48 ticks left" can be zero real ticks. 15/16 alive-seat timeouts across
# the anchor A/B warehouses fired the auto-submit on time by the belief clock and still
# missed the server tally (measured lag +54..+689 frames at meeting end). Doubling the
# margin absorbs the residual lag left after the per-tick /spend read fix below.
AUTO_SUBMIT_REMAINING_TICKS = 96
# Re-read the sidecar /spend at most this often (ticks). Spend only changes when WE
# make a call, so a 1s cache is safe; the blocking loopback GET measured 20-40ms —
# reading it every meeting tick was the main per-tick budget breaker (see above).
SPEND_READ_CACHE_TICKS = 24
# The sim's real tick rate (24/s). Deliberately NOT derived from VOTE_TIMER_TICKS —
# the timer length changed (240→1200) but the tick rate did not; deriving it would
# corrupt the LLM latency-guard's seconds→ticks conversion.
MEETING_TICKS_PER_SECOND = 24
LLM_TIMEOUT_MARGIN_TICKS = 12
# Fallback for clients without a ``timeout_seconds`` attribute; the real default lives in
# strategy/meeting/llm.py (DEFAULT_MEETING_TIMEOUT_SECONDS = 6.0 — the deadline geometry
# derives from the client's actual timeout, so keep this aligned).
DEFAULT_LLM_TIMEOUT_SECONDS = 6.0
# Early-submit a tentative vote (LLM idle) once under half the believed time remains —
# the belief clock can lag real time, and a submitted vote can't be lost to vote_timeout.
EARLY_SUBMIT_REMAINING_FRACTION = 0.5
# Warm first-mover anchors (the social-rule eligibility route, suspicion.
# warm_anchor_suspect; design crewrift_lab/docs/designs/2026-07-22-warm-anchor-design.md)
# default ON; kill switch for A/B isolation and emergency rollback.
WARM_ANCHOR_ENV = "CREWBORG_WARM_ANCHOR"
# Vote-coordination levers (2026-07-24 wave-2 mining: our correct crew ballots convert to
# ejections at 31.9% vs the top converters' 61-71%; we vote earliest — votes_before_ours
# 1.71, lowest in the corpus — and alone — pile_before 0.12 vs field 0.7-1.6; the target
# ends ~2.6 total votes vs the ~3.4 an ejection needs). Both default OFF; recipe-enabled
# separately for the A/B arms (design 2026-07-24-vote-coordination-prereg.md).
#
# CHAT_PUSH: re-send our accusation once, mid-meeting, if our target has drawn no votes —
# the second call for the pile. Top converters' accusations pull ~1.7-2.3 followers when
# cue-first and terse; ours pull 1.1-1.5 with one send.
CHAT_PUSH_ENV = "CREWBORG_VOTE_CHAT_PUSH"
CHAT_PUSH_REMAINING_TICKS = 480  # re-push when under this remaining and target vote-less
# BALLOT_RETIME: hold the deterministic crew ballot back from the first decide tick;
# cast it once ANY other vote lands on our target (join the pile we seeded), or at the
# early-submit point otherwise. The chat still goes out first-tick (anchoring is right —
# the top converters chat FIRST but vote 2-3 votes IN; we currently do both first).
BALLOT_RETIME_ENV = "CREWBORG_VOTE_BALLOT_RETIME"


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
        self._llm_min_call_interval_ticks = _llm_min_call_interval_from_env()
        self._llm_call_cost_usd = _env_float(os.environ, LLM_CALL_COST_ESTIMATE_ENV, DEFAULT_LLM_CALL_COST_USD)
        self._spend_checked_tick: int | None = None  # cache /spend read within a meeting-tick
        self._spend_remaining_usd: float | None = None  # last read; None = no limit / unknown
        self._spend_last_read_usd: float | None = None  # last sidecar spend_usd (llm_spend cross-check)
        # Instant suss-vote (CREWBORG_LLM_SUSS_INSTANT_VOTE, default off): when the
        # meeting LLM NAMES a suspect — a chat accusation or a tentative vote_target —
        # the crew seat votes them on the next tick instead of holding to the
        # early-submit/deadline gates. James's directive 2026-07-02; NOTE the prior
        # evidence cuts the other way (LLM-named-not-submitted targets measured
        # 22-50% precise vs 76% for explicit submit_vote; v90 deadline pass-through
        # A/B-refuted) — ship only on a fresh LLM-on A/B.
        self._instant_vote_enabled = (
            os.environ.get("CREWBORG_LLM_SUSS_INSTANT_VOTE", "").strip().lower()
            in ("1", "true", "yes", "on")
        )
        self._instant_vote_pending: str | None = None
        # Warm first-mover anchor (default on; CREWBORG_WARM_ANCHOR=0 disables).
        self._warm_anchor_enabled = (
            os.environ.get(WARM_ANCHOR_ENV, "").strip().lower() not in ("0", "false", "no", "off")
        )
        self._warm_anchor_target: str | None = None
        # Vote-coordination levers (default OFF; see module constants above).
        self._chat_push_enabled = (
            os.environ.get(CHAT_PUSH_ENV, "").strip().lower() in ("1", "true", "yes", "on")
        )
        self._chat_pushed = False
        self._ballot_retime_enabled = (
            os.environ.get(BALLOT_RETIME_ENV, "").strip().lower() in ("1", "true", "yes", "on")
        )
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
        self._chat_evidence_traced = False

    def is_legal(self, belief: Belief) -> bool:
        return belief.phase == "Voting"

    def decide(self, belief: Belief, action_state: ActionState) -> Intent:
        self._reset_for_meeting_if_needed(belief)
        if action_state.vote_confirmed:
            self._vote_submitted = True
            self._active_vote_target = None
            self._active_vote_reason = ""
        if honor_society.enabled():
            # Listen every meeting tick (both roles, even after our vote is in);
            # inert when the flag is off (design docs/designs/honor-society.md).
            honor_society.process_chats(belief, self.emit)
        if self._vote_submitted:
            # The chat-push lever still speaks after our ballot is in — persuasion
            # is exactly the post-vote channel (our vote can't change; the pile can).
            push = self._post_vote_chat_push_intent(belief)
            if push is not None:
                return push
            return Intent(kind="idle", reason="vote already confirmed")
        if self._active_vote_target is not None:
            return self._vote_intent(self._active_vote_target, reason=self._active_vote_reason)
        first_mover = self._first_mover_accusation_intent(belief)
        if first_mover is not None:
            return first_mover
        society_intent = self._society_chat_intent(belief)
        if society_intent is not None:
            return society_intent
        if (
            self._instant_vote_pending is not None
            and belief.self_alive
            and self._pending_chat_text is None  # let the accusing chat go out first
        ):
            # Instant suss-vote: the LLM named this target; its chat is out, so vote
            # them now instead of holding to the early-submit/deadline gates.
            target = self._instant_vote_pending
            self._instant_vote_pending = None
            self._tentative_vote = target
            return self._submit_vote_intent(belief, reason="LLM named suss: instant vote")

        if not self._llm_client.enabled:
            return self._decide_deterministic(belief, trace_disabled=True)

        if not belief.self_alive:
            # Dead seats' meeting inputs are ignored by the sim (0 post-death vote_cast
            # across the v87 league replays), yet dead crewborg seats burned ~23% of
            # meeting-LLM call volume — pure Bedrock rate pressure on the live seats.
            # Mute the EXPENSIVE parts: no LLM calls, no chats. The deterministic
            # (LLM-off) branch above is untouched.
            if not self._dead_mute_traced:
                self._dead_mute_traced = True
                self.emit.event("meeting_dead_mute", {"tick": belief.last_tick})
                self.emit.counter("meeting_dead_mute")
            # BUT still cast a terminal SKIP at the deadline (idling-is-dangerous): the
            # dead-mute fires on belief.self_alive, which can be WRONGLY False — the v105
            # self_color one-shot latch can stick a neighbour's colour, so the meeting
            # census (types.update_belief) flips self_alive off when that neighbour dies
            # while we're actually alive. A muted-but-alive seat that never votes draws the
            # game's "-10 for failing to vote or skip" penalty (measured: v105 vote_timeout
            # 0%→~10%, v100 had none). A skip is harmless if we really are dead (the sim
            # ignores dead inputs) and saves the penalty if we're not. No LLM/chat spend:
            # this is one vote intent at the very end, nothing more.
            if self._should_auto_submit(belief) and not self._vote_submitted:
                return self._vote_intent(VOTE_SKIP, reason="dead-mute deadline: safety skip")
            return Intent(kind="idle", reason="dead: LLM/chat muted (skip at deadline)")

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

    # --- first-mover anchoring --------------------------------------------

    def _first_mover_accusation_intent(self, belief: Belief) -> Intent | None:
        """Crew with a vote-bar-clearing suspect at meeting start: accuse IMMEDIATELY
        (first chat slot), before the meeting_start LLM round-trip.

        The 2026-07-02 chat study found conversion (same-meeting ejection of the
        accused) tracks speaking FIRST: the first named target anchors the pile
        (premise re-verified on 199 live episodes: P(ejected|named first) 28.7% vs
        12.5% later, z=5.8; crewborg's median first chat lands 55 ticks in — the LLM
        latency — vs tick 1 for the top converters). Design:
        crewrift_lab/docs/designs/2026-07-21-first-mover-anchor-design.md.

        LLM path only — the deterministic (LLM-off) path already accuses on its
        first decide tick. Fires at most once per meeting, before the first LLM
        call; sets ``_deterministic_chatted`` so an LLM-failure fallback can't chat
        twice, and routes through ``_send_chat_intent`` so a duplicate later LLM
        chat is suppressed by the existing gate.

        Two eligibility routes (design 2026-07-22-warm-anchor-design.md):
        the HARD bar (``top_suspect`` — witnessed-catch territory), whose coupled
        tentative vote passes ``_vote_target_corroborated`` by construction; and
        the WARM social rule (``warm_anchor_suspect``, ~89% measured precision),
        whose tentative vote is deliberately NOT corroborated — it becomes a real
        ballot only via the warm pile clause or a later independent corroboration,
        else the deadline gate converts it to skip.
        """

        if not self._llm_client.enabled:
            return None
        if belief.self_role == "imposter" or not belief.self_alive:
            return None
        if self._deterministic_chatted or self._last_chat_tick is not None:
            return None
        if self._last_llm_call_tick is not None:
            return None  # the meeting_start call is already out — too late to anchor
        warm = False
        target = top_suspect(belief)
        if target is None and self._warm_anchor_enabled:
            # Warm eligibility (the W2 lever): the fitted posterior is bimodal —
            # non-witnessed tops max out ~0.74, so the hard bar only ever fires on
            # witnessed catches (~0.18/ep). The social rule adds ~0.12/ep at ~89%
            # measured precision. CHAT-only: the vote stays behind the existing
            # corroboration gate plus the warm pile clause (see
            # _vote_target_corroborated) — a lone warm ballot is never cast.
            target = warm_anchor_suspect(belief)
            warm = target is not None
        if target is None or honor_society.vote_veto(belief, target):
            return None
        accusation = build_accusation(belief, target)
        if accusation is None:
            return None  # no citable evidence — never bare-accuse
        self._deterministic_chatted = True
        self._tentative_vote = target
        if warm:
            self._warm_anchor_target = target
            self.emit.counter("meeting_warm_anchor")
        self.emit.event(
            "meeting_first_mover_accusation",
            {"target": target, "tick": belief.last_tick, "warm": warm},
        )
        self.emit.counter("meeting_first_mover_accusation")
        path = "first_mover_accuse_warm" if warm else "first_mover_accuse"
        self._trace_meeting_decision(belief, role="crewmate", path=path, target=target)
        return self._send_chat_intent(belief, accusation, reason="first-mover: anchor the pile")

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
            if target is not None and honor_society.vote_veto(belief, target):
                target = None  # society-trusted (and unwitnessed): accuse no one instead
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
                if soft is not None and honor_society.vote_veto(belief, soft):
                    soft = None  # don't voice reads against society-trusted members either
                read = build_accusation(belief, soft) if soft is not None else None
                if read is not None:
                    self._trace_meeting_decision(belief, role="crewmate", path="share_read", target=soft)
                    return self._send_chat_intent(belief, read, reason="sharing read (no vote)")
                self._trace_meeting_decision(belief, role="crewmate", path="silent_skip", target=None)
        retime = self._ballot_retime_intent(belief)
        if retime is not None:
            return retime
        return self._submit_vote_intent(belief, reason="deterministic meeting vote")

    def _ballot_retime_intent(self, belief: Belief) -> Intent | None:
        """BALLOT_RETIME lever (2026-07-24 mining; flag default OFF): instead of
        submitting our crew ballot on the tick after the accusation — the
        corpus-earliest vote (votes_before_ours 1.71 vs the top converters' 2.5-3.5)
        — hold it while the pile forms: cast once ANY other vote lands on our
        target (join the pile we seeded), or once under the early-submit fraction /
        at the deadline otherwise, so vote_timeouts stay 0. Returning None falls
        through to the normal immediate submit."""

        target = self._tentative_vote
        if (
            not self._ballot_retime_enabled
            or target is None
            or target == VOTE_SKIP
            or belief.self_role == "imposter"
            or self._should_auto_submit(belief)
        ):
            return None
        if votes_against(belief).get(target, 0) > 0:
            self.emit.counter("meeting_retime_join")
            return self._submit_vote_intent(belief, reason="retime: joining pile on our target")
        if self._remaining_ticks(belief) >= VOTE_TIMER_TICKS * EARLY_SUBMIT_REMAINING_FRACTION:
            return Intent(kind="idle", reason="retime: holding ballot while pile forms")
        self.emit.counter("meeting_retime_expire")
        return self._submit_vote_intent(belief, reason="retime: no pile formed, casting")

    def _post_vote_chat_push_intent(self, belief: Belief) -> Intent | None:
        """CHAT_PUSH lever (2026-07-24 mining; flag default OFF): our accusation and
        ballot are in, but the target has drawn no other votes and the meeting is
        aging — send ONE more explicit call for the pile ("vote X. <evidence>").
        Fires after our vote is confirmed, so ballot timing is untouched — this
        tests the persuasion channel in isolation. The dedupe gate in
        _send_chat_intent suppresses identical texts, so the push leads with the
        vote call instead of repeating the accusation verbatim."""

        if (
            not self._chat_push_enabled
            or self._chat_pushed
            or belief.self_role == "imposter"
            or not belief.self_alive
        ):
            return None
        target = self._tentative_vote
        if target is None or target == VOTE_SKIP:
            return None
        if self._remaining_ticks(belief) > CHAT_PUSH_REMAINING_TICKS:
            return None
        if votes_against(belief).get(target, 0) > 0:
            return None  # the pile formed on its own; no push needed
        if not self._chat_cooldown_ready(belief):
            return None
        self._chat_pushed = True
        push = f"vote {target}. {build_accusation(belief, target) or f'{target} sus'}"
        self.emit.counter("meeting_chat_push")
        return self._send_chat_intent(
            belief, push[:CHAT_MAX_CHARS], reason="chat-push: second call for the pile"
        )

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

        return chat_evidence.chat_accusers(belief, cache=self._chat_parse_cache)

    # --- LLM call cadence -------------------------------------------------

    def _next_llm_trigger(self, belief: Belief) -> str | None:
        tick = belief.last_tick
        if self._llm_calls_used >= self._llm_call_budget:
            return None
        if (
            self._last_llm_call_tick is not None
            and tick - self._last_llm_call_tick < self._llm_min_call_interval_ticks
        ):
            return None
        if not self._can_start_llm_call(belief):
            return None
        if self._deadline_prompted:
            return None
        if self._last_llm_call_tick is None:
            # ALWAYS allow the first call of a meeting (the highest-value one) — we never go
            # fully silent, even when the episode budget is nearly spent.
            return "meeting_start"

        # Follow-up calls are gated on the per-episode LLM spend budget: if the sidecar reports we
        # can't comfortably afford another call, stop here rather than burning budget into a 429.
        if not self._spend_allows_followup(belief):
            return None

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

    def _spend_allows_followup(self, belief: Belief) -> bool:
        """Can we afford another (follow-up) LLM call under the per-episode spend limit?

        Reads the sidecar's ``GET /spend``, cached for SPEND_READ_CACHE_TICKS (~1s). The read is
        a blocking loopback HTTP GET measured at 20-40ms — reading it every meeting tick pushed
        the tick loop over the ~42ms frame budget, queueing frames and lagging the belief clock
        behind the server (the 2026-07-21 vote_timeout root cause). Spend only changes when we
        ourselves complete a call, so a ~1s cache costs nothing. Returns True when there's no
        configured limit or no sidecar (nothing to budget against), or when the remaining budget
        comfortably covers another call (RESERVE × per-call estimate). Traces the reading so the
        budget is visible per meeting."""
        tick = belief.last_tick
        if self._spend_checked_tick is None or abs(tick - self._spend_checked_tick) >= SPEND_READ_CACHE_TICKS:
            self._spend_checked_tick = tick
            status = spend.read_spend()
            self._spend_remaining_usd = status.remaining_usd if status is not None else None
            if status is not None:
                self._spend_last_read_usd = status.spend_usd
                self.emit.event(
                    "meeting_spend",
                    {
                        "spend_usd": round(status.spend_usd, 6),
                        "remaining_usd": None if status.remaining_usd is None else round(status.remaining_usd, 6),
                        "limit_usd": status.spend_limit_usd,
                    },
                )
        if self._spend_remaining_usd is None:
            return True  # no limit configured (or unreadable) → the call-count budget governs
        allowed = self._spend_remaining_usd >= LLM_SPEND_RESERVE_FACTOR * self._llm_call_cost_usd
        if not allowed:
            self.emit.counter("meeting_llm_spend_gated")
        return allowed

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
            self._emit_llm_spend(
                belief,
                llm_spend.EPISODE_LEDGER.failure_event(
                    surface="meeting",
                    trigger=trigger,
                    model=getattr(getattr(self._llm_client, "config", None), "model", None),
                    latency_ms=outcome.latency_ms,
                    error=outcome.error,
                ),
            )
            return self._decide_after_llm_failure(belief, trigger)
        result = outcome.result
        self._emit_llm_spend(
            belief,
            llm_spend.EPISODE_LEDGER.success_event(
                surface="meeting",
                trigger=trigger,
                model=result.model,
                latency_ms=result.latency_ms,
                usage=result.usage,
            ),
        )
        self.emit.histogram("meeting_llm.latency_ms", result.latency_ms, tags={"model": result.model, "trigger": trigger})
        decision = self._validate_decision(belief, result.decision)
        if decision is None:
            return self._decide_after_llm_failure(belief, trigger)
        self._trace_decision(trigger, decision, result)
        return self._apply_decision(belief, decision)

    def _emit_llm_spend(self, belief: Belief, payload: dict[str, Any]) -> None:
        """Emit the per-call ``domain.llm_spend`` attribution event (W4 spend telemetry).

        Enriches the ledger payload with the meeting/role context the budget analysis
        keys on, plus the CACHED sidecar spend reading as a cross-check — never a fresh
        HTTP read here (the per-tick /spend GET was the 2026-07-21 vote_timeout root
        cause; the cache is owned by ``_spend_allows_followup``).
        """
        # Ordinal from the process-wide ledger, not an instance counter: the mode is
        # recreated per meeting, so an instance counter reads 0 forever (measured on the
        # spendtrace probe).
        meeting_id = self._meeting_id if self._meeting_id is not None else belief.phase_start_tick
        payload["meeting_index"] = llm_spend.EPISODE_LEDGER.meeting_ordinal(meeting_id)
        payload["role"] = belief.self_role
        payload["calls_used"] = self._llm_calls_used
        payload["sidecar_spend_usd"] = self._spend_last_read_usd
        self.emit.event("llm_spend", payload)
        self.emit.counter(
            "llm_spend_calls",
            tags={"surface": "meeting", "ok": str(payload["ok"]).lower(), "error_class": payload["error_class"] or ""},
        )

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

    def _maybe_arm_instant_vote(self, belief: Belief, decision: MeetingDecision) -> None:
        """Instant suss-vote arming: the LLM NAMED someone — a tentative vote_target
        or a color accused in its chat — so queue an immediate vote for them.

        Crew-and-alive only; explicit submit_vote decisions already vote at once, so
        arming there is a harmless no-op (the pending clears when the vote submits).
        The named target is treated as LLM-corroborated by James's rule; the
        self-guard and the Honor-Society trust veto still apply at submit time.
        """

        if not self._instant_vote_enabled or belief.self_role == "imposter" or not belief.self_alive:
            return
        target = decision.vote_target
        if (target is None or target == VOTE_SKIP) and decision.chat_text:
            self_color = belief.self_color or belief.voting.self_marker_color
            colors = set(belief.roster)
            accused = chat_evidence.accused_colors(decision.chat_text, colors) - {self_color}
            if not accused:
                # accused_colors needs the (optional) spaCy model; the LLM literally
                # naming a color in its own outgoing chat is enough here — plain
                # word-boundary match as the NLP-off fallback.
                words = re.findall(r"[a-z]+", decision.chat_text.lower())
                accused = {c for c in colors if c in words} - {self_color}
            if accused:
                target = max(accused, key=lambda color: belief.suspicion.get(color, 0.0))
        if target is None or target == VOTE_SKIP:
            return
        self._instant_vote_pending = target
        self._llm_submitted_vote_targets.add(target)
        self.emit.event("meeting_instant_vote_armed", {"target": target, "action": decision.action})
        self.emit.counter("meeting_instant_vote_armed")

    def _apply_decision(self, belief: Belief, decision: MeetingDecision) -> Intent:
        chat_evidence.apply_llm_tags(belief, decision.chat_evidence)
        self._maybe_arm_instant_vote(belief, decision)
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

    def _society_chat_intent(self, belief: Belief) -> Intent | None:
        """The Honor Society's once-per-game HS1 crew announce (design
        docs/designs/honor-society.md).

        Strictly lower priority than voting: never fires from a dead seat, over a
        submitted vote, or inside the deadline auto-submit window, and it obeys the
        normal chat cooldown — worst case it costs one chat slot per game.
        Imposters stay entirely silent (claiming crew is forbidden; silence is not).
        """

        if not honor_society.enabled():
            return None
        if belief.self_role != "crewmate" or not belief.self_alive:
            return None
        if self._vote_submitted or self._should_auto_submit(belief):
            return None
        if not self._chat_cooldown_ready(belief):
            return None
        self_color = belief.self_color or belief.voting.self_marker_color
        if self_color is None:
            return None
        if not belief.society_announced:
            belief.society_announced = True
            text = honor_society.announce_text(self_color)
            return self._send_chat_intent(belief, text, reason="society: crew announce", society=True)
        return None

    def _send_chat_intent(self, belief: Belief, text: str, *, reason: str, society: bool = False) -> Intent:
        self._pending_chat_text = None
        self._sent_chat_texts.add(text)
        self._last_chat_tick = belief.last_tick
        # Society lines carry no color words, but bypass the accusation reader
        # explicitly — a CHS message must never set a chat-implied vote.
        if self._llm_client.enabled and not society:  # keep the LLM-off path byte-identical
            self._note_own_accusation(belief, text)
        self.emit.event("meeting_chat_selected", {"text": text, "reason": reason})
        return Intent(kind="chat", text=text, reason=reason)

    def _note_own_accusation(self, belief: Belief, text: str) -> None:
        """Track whom our own chat accused: the chat-implied fallback vote.

        v86's headline crew failure was confident-chat-then-skip — the LLM accused a
        color in chat, the follow-up vote call failed (429/timeout), and the fallback
        collapsed to the 0.9-gate skip. If we said it, we should vote it."""

        accused = chat_evidence.accused_colors(text, set(belief.roster))
        self_color = belief.self_color or belief.voting.self_marker_color
        accused -= belief.teammate_colors | {self_color}
        if not accused:
            return
        self._chat_accused = max(accused, key=lambda color: belief.suspicion.get(color, 0.0))
        self.emit.event("meeting_chat_implied_vote", {"target": self._chat_accused, "text": text})

    def _submit_vote_intent(self, belief: Belief, *, reason: str) -> Intent:
        vote_target = self._resolved_vote_target(belief)
        # Honor Society: spare trusted claimed-crew members from posterior-driven
        # votes (witnessed evidence overrides trust inside vote_veto). Skip-only:
        # this can remove a vote, never invent one. Inert with the flag off.
        if vote_target != VOTE_SKIP and honor_society.vote_veto(belief, vote_target):
            self.emit.event("meeting_vote_society_veto", {"target": vote_target, "reason": reason})
            self.emit.counter("meeting_vote_society_veto")
            vote_target = VOTE_SKIP
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
        self._trace_chat_evidence(belief, vote_target)
        self._active_vote_target = vote_target
        self._active_vote_reason = reason
        self.emit.event("meeting_vote_selected", {"target": vote_target, "reason": reason})
        return self._vote_intent(vote_target, reason=reason)

    def _trace_chat_evidence(self, belief: Belief, vote_target: str) -> None:
        """Once per meeting, at vote-submit: the chat-evidence mechanism record —
        each live target's chat log-LR term, the actual suspicion vote, and the
        no-chat-evidence counterfactual (the A/B's "did chat change our vote?"
        metric; design 2026-07-22-chat-evidence-incorporation.md §2.6). Crew-side
        only (an imposter's deflection reads are not beliefs); skipped entirely
        with the feature off."""

        if self._chat_evidence_traced or not chat_evidence_enabled() or belief.self_role == "imposter":
            return
        self._chat_evidence_traced = True
        contributions = {c: round(v, 4) for c, v in chat_evidence_contributions(belief).items() if v != 0.0}
        with_chat = top_suspect(belief)
        without_chat = counterfactual_top_suspect_no_chat(belief)
        self.emit.event(
            "chat_evidence_applied",
            {
                "vote_target": vote_target,
                "top_suspect_with_chat": with_chat,
                "top_suspect_without_chat": without_chat,
                "changed_top_suspect": with_chat != without_chat,
                "contributions": contributions,
            },
        )
        if with_chat != without_chat:
            self.emit.counter("chat_evidence_changed_vote")

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
        self._instant_vote_pending = None
        self._warm_anchor_target = None
        self._chat_pushed = False
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
        self._chat_evidence_traced = False

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
        if top_suspect(belief) == target:
            return True
        return self._warm_pile_formed(belief, target)

    def _warm_pile_formed(self, belief: Belief, target: str) -> bool:
        """The warm anchor's vote-escalation clause: our warm-anchored target has
        drawn independent heat this meeting — another player cast a vote against
        them or accused them in chat (both signals already exclude our own ballot
        and our own chats). The anchoring premise is that the first-named target
        collects the pile; if others joined, our ballot is pivotal exactly when it
        can convert, and a LONE warm ballot (~89% measured precision, below the
        hard bar's 97-100%) is never cast — the deadline gate skips it instead
        (design 2026-07-22-warm-anchor-design.md)."""

        if target != self._warm_anchor_target:
            return False
        if votes_against(belief).get(target, 0) > 0:
            return True
        # Chat heat, from EXTERNAL messages only. _chat_accusers would count an
        # unattributed (speaker_color None) copy of our own anchor accusation as
        # an accuser — self-corroboration; _is_external_chat also excludes texts
        # we sent. Same parse + cache contents as chat_evidence.chat_accusers.
        self_color = belief.voting.self_marker_color
        for event in belief.chat_log:
            if not self._is_external_chat(event, self_color):
                continue
            if event.text not in self._chat_parse_cache:
                self._chat_parse_cache[event.text] = {
                    claim.target_color
                    for claim in chat_evidence.parse_claims(belief, event)
                    if claim.claim_type == "accusation"
                }
            if target in self._chat_parse_cache[event.text]:
                return True
        return False

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


def _llm_min_call_interval_from_env() -> int:
    raw = os.environ.get(LLM_MIN_CALL_INTERVAL_ENV)
    if raw is None:
        return LLM_MIN_CALL_INTERVAL_TICKS
    try:
        return max(0, int(raw))
    except ValueError:
        return LLM_MIN_CALL_INTERVAL_TICKS


def _env_float(env: dict[str, str], name: str, default: float) -> float:
    try:
        return float(env.get(name, default))
    except (TypeError, ValueError):
        return default
