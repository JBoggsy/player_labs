"""Meeting-context serialization for LLM chat/vote decisions."""

from __future__ import annotations

from collections import Counter
from typing import Any

from crewrift.crewborg.perception.entities import SKIP_VOTE_TARGET
from crewrift.crewborg.strategy.meeting.schema import CHAT_MAX_CHARS, SCHEMA_VERSION, VOTE_SKIP
from crewrift.crewborg.strategy.suspicion import (
    _body_proximity_log_lr,
    _follow_log_lr,
    _prior_imposter_p,
    _tailing_self_log_lr,
    _vent_dwell_log_lr,
    active_vote_probability_bar,
    top_suspect,
    witnessed_imposters,
)
from crewrift.crewborg.types import Belief, PlayerEvent, PlayerRecord

# Cap events sent per player in the LLM context. recent_events was ~93% of the (large) player
# payload and blew the per-episode Bedrock spend limit; we keep the N events that most move the
# read — the most INCRIMINATING and most EXONERATING — not just the most recent, so the LLM still
# sees both sides of the case on a compact budget. See chat_study / the token-cost investigation.
MAX_EVENTS_PER_PLAYER = 10

# The game's voting-phase length. Was 240 (10s); coworld-crewrift b78e400 (merged
# 2026-06-29) raised the live game to voteTimerTicks=1200 — with the old constant
# crewborg auto-submitted ~16% into the meeting and stopped listening for the rest.
VOTE_TIMER_TICKS = 1200
# Min ticks between our own chats. Kept well under VOTE_TIMER_TICKS so a proactive
# meeting voice can speak more than once (share a read, then react/follow up).
CHAT_COOLDOWN_TICKS = 60


def serialize_meeting_context(
    belief: Belief,
    *,
    trigger: str,
    tentative_vote: str | None = None,
    sent_chat_texts: set[str] | None = None,
    last_chat_tick: int | None = None,
) -> dict[str, Any]:
    """Serialize belief into the compact, explicit context the meeting LLM sees."""

    sent_chat_texts = sent_chat_texts or set()
    age_ticks = max(0, belief.last_tick - belief.phase_start_tick)
    remaining_ticks = max(0, VOTE_TIMER_TICKS - age_ticks)
    legal_targets = sorted(valid_vote_targets(belief))
    fallback_vote = _fallback_vote_target(belief)
    return {
        "schema_version": SCHEMA_VERSION,
        "trigger": trigger,
        "meeting": {
            "id": belief.phase_start_tick,
            "phase": belief.phase,
            "tick": belief.last_tick,
            "age_ticks": age_ticks,
            "estimated_remaining_ticks": remaining_ticks,
            "vote_timer_ticks": VOTE_TIMER_TICKS,
        },
        "self": {
            "color": belief.voting.self_marker_color,
            "role": belief.self_role,
            "teammates": sorted(belief.teammate_colors),
        },
        "constraints": {
            "actions": ["send_chat", "set_tentative_vote", "submit_vote", "wait"],
            "valid_vote_targets": [*legal_targets, VOTE_SKIP],
            "skip_vote_target": VOTE_SKIP,
            "chat_max_chars": CHAT_MAX_CHARS,
            "chat_must_be_printable_ascii": True,
            "chat_cooldown_ticks": CHAT_COOLDOWN_TICKS,
            "chat_cooldown_ready": _chat_ready(belief, last_chat_tick),
        },
        "state": {
            "tentative_vote": tentative_vote,
            "fallback_vote": fallback_vote,
            "fallback_vote_reason": _fallback_vote_reason(belief, fallback_vote),
        },
        "voting": _voting_payload(belief),
        "chat": _chat_payload(belief, sent_chat_texts),
        # players is rendered as terse PROSE lines, not JSON objects: it's ~65% of the context and
        # JSON key/brace overhead was ~5x the content (measured — one player ~1670 tk of JSON vs
        # ~357 tk of prose, 79% smaller). The LLM reads the lines fine; this is the main lever on
        # the per-episode token/spend budget. See the token-cost investigation.
        "players": _players_prose(belief),
        "suspicion": _suspicion_payload(belief, fallback_vote),
    }


def valid_vote_targets(belief: Belief) -> set[str]:
    """Return live player colors the LLM may target, excluding self."""

    self_color = belief.voting.self_marker_color
    candidates = {
        candidate.color
        for candidate in belief.voting.candidates
        if candidate.alive and candidate.color != self_color
    }
    if candidates:
        return candidates
    return {
        color
        for color, record in belief.roster.items()
        if record.life_status == "alive" and color != self_color
    }


def _fallback_vote_target(belief: Belief) -> str:
    return top_suspect(belief) or VOTE_SKIP


def _fallback_vote_reason(belief: Belief, fallback_vote: str) -> str:
    if fallback_vote == VOTE_SKIP:
        bar = active_vote_probability_bar(belief.self_role)
        return f"no suspect at or above vote bar {bar}"
    p = belief.suspicion.get(fallback_vote)
    return f"top suspect {fallback_vote} at P(imposter)={p:.4f}" if p is not None else "top suspect"


def _chat_ready(belief: Belief, last_chat_tick: int | None) -> bool:
    return last_chat_tick is None or belief.last_tick - last_chat_tick >= CHAT_COOLDOWN_TICKS


def _voting_payload(belief: Belief) -> dict[str, Any]:
    voting = belief.voting
    slot_to_color = {candidate.slot: candidate.color for candidate in voting.candidates}
    dots = []
    tally: Counter[str] = Counter()
    for dot in voting.dots:
        target = VOTE_SKIP if dot.target == SKIP_VOTE_TARGET else slot_to_color.get(dot.target, str(dot.target))
        tally[target] += 1
        dots.append(
            {
                "voter_slot": dot.voter,
                "voter_color": slot_to_color.get(dot.voter),
                "target": target,
            }
        )
    return {
        "cursor_slot": voting.cursor_slot,
        "cursor_on_skip": voting.skip_cursor_present,
        "timer_present": voting.timer_present,
        "candidates": [
            {
                "slot": candidate.slot,
                "color": candidate.color,
                "alive": candidate.alive,
                "self": candidate.color == voting.self_marker_color,
                "teammate": candidate.color in belief.teammate_colors,
                "suspicion": _rounded(belief.suspicion.get(candidate.color)),
            }
            for candidate in voting.candidates
        ],
        "votes": dots,
        "tally": dict(sorted(tally.items())),
    }


def _chat_payload(belief: Belief, sent_chat_texts: set[str]) -> dict[str, Any]:
    self_color = belief.voting.self_marker_color
    return {
        "messages": [
            {
                "tick": event.tick,
                "speaker_color": event.speaker_color,
                "self": event.speaker_color == self_color or event.text in sent_chat_texts,
                "text": event.text,
            }
            for event in belief.chat_log
        ]
    }


def _players_prose(belief: Belief) -> str:
    """The roster as one terse prose line per player (see serialize_meeting_context for why).

    Each line: ``<color>: <alive|dead> [tags] sus <p> | <events>`` — tags flag self / teammate /
    confirmed-or-believed imposter; events are the compact ``_event_phrase`` list. Raw coordinates,
    last-seen ticks, and body xy are dropped (the LLM reasons over rooms + who/what, not px/ticks)."""
    witnessed = witnessed_imposters(belief)
    lines: list[str] = []
    for color, record in sorted(belief.roster.items()):
        tags: list[str] = []
        if color == belief.voting.self_marker_color:
            tags.append("me")
        if color in belief.teammate_colors:
            tags.append("teammate")
        if color in witnessed:
            tags.append("CONFIRMED-imposter")
        elif color in belief.believed_imposters:
            tags.append("believed-imposter")

        parts = [f"{color}: {record.life_status}"]
        if tags:
            parts.append("[" + ",".join(tags) + "]")
        sus = _rounded(belief.suspicion.get(color))
        if sus is not None:
            parts.append(f"sus {sus}")
        head = " ".join(parts)

        phrases = [_event_phrase(belief, e) for e in _relevant_events(belief, record)]
        if phrases:
            head += " | " + "; ".join(phrases)
        lines.append(head)
    return "\n".join(lines)


def _relevant_events(belief: Belief, record: PlayerRecord) -> list[PlayerEvent]:
    """The player's most decision-relevant events, newest-last. Keep the MAX_EVENTS_PER_PLAYER
    with the largest |suspicion| — the most incriminating (kill/vent/tail/near-body) AND the most
    exonerating (long tasking) — so the LLM sees both sides of the case on a compact budget."""
    events = record.events
    if len(events) > MAX_EVENTS_PER_PLAYER:
        ranked = sorted(events, key=lambda e: abs(_event_suspicion(belief, e)), reverse=True)
        kept = set(id(e) for e in ranked[:MAX_EVENTS_PER_PLAYER])
        events = [e for e in events if id(e) in kept]
    return events[-MAX_EVENTS_PER_PLAYER:]


def _event_suspicion(belief: Belief, event: PlayerEvent) -> float:
    """A signed relevance score for one event: positive = incriminating, negative = exonerating
    (long tasking reads as innocent crew). Reuses the suspicion model's per-event log-LRs so the
    kept set matches what actually drives the posterior."""
    if event.kind in ("kill", "vent_use"):
        return 10.0  # witnessed — always keep
    if event.kind == "tailing_self":
        return _tailing_self_log_lr(event)
    if event.kind == "proximity":
        return _follow_log_lr(event, belief)
    if event.kind == "near_body":
        return _body_proximity_log_lr(event)
    if event.kind == "vent":
        return _vent_dwell_log_lr(event)
    if event.kind == "task":
        return -float(event.duration_ticks)  # more tasking → more exonerating (negative)
    return 0.0


_EVENT_VERB = {
    "room": "in",
    "task": "tasked in",
    "vent": "vented in",
    "near_body": "by body of",
    "proximity": "near",
    "tailing_self": "tailed me",
    "kill": "killed",
    "vent_use": "vented",
}


def _event_phrase(belief: Belief, event: PlayerEvent) -> str:
    """One event as a terse phrase, e.g. 'in Bridge', 'near green', 'killed red', 'tailed me'.
    Only the kind, who it involved, and the room — no ticks/indices/distances."""
    verb = _EVENT_VERB.get(event.kind, event.kind)
    room = _region_name(belief, event) if (belief.map is not None and event.region_index is not None) else None
    parts = [verb]
    if event.target_color is not None:
        parts.append(event.target_color)
    if room is not None:
        # room-kinds already read "in <room>" via the verb; others append "in <room>"
        parts.append(room if event.kind in ("room", "task", "vent") else f"in {room}")
    return " ".join(parts)


def _region_name(belief: Belief, event: PlayerEvent) -> str | None:
    assert belief.map is not None
    if event.kind == "room" and 0 <= event.region_index < len(belief.map.rooms):
        return belief.map.rooms[event.region_index].name
    if event.kind == "task" and 0 <= event.region_index < len(belief.map.tasks):
        return belief.map.tasks[event.region_index].name
    if event.kind == "vent" and 0 <= event.region_index < len(belief.map.vents):
        vent = belief.map.vents[event.region_index]
        return f"vent {vent.group}:{vent.group_index}"
    return None


def _suspicion_payload(belief: Belief, fallback_vote: str) -> dict[str, Any]:
    return {
        "prior": _rounded(_prior_imposter_p(belief)),
        "vote_probability_threshold": active_vote_probability_bar(belief.self_role),
        "confirmed": sorted(witnessed_imposters(belief)),
        "believed": sorted(belief.believed_imposters),
        "ranking": [
            {"color": color, "p": _rounded(p)}
            for color, p in sorted(belief.suspicion.items(), key=lambda item: item[1], reverse=True)
        ],
        "would_vote": fallback_vote,
    }


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 4)
