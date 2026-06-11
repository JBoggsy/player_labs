"""Build a crewmate's meeting accusation from the suspect's event log.

When the deterministic meeting path votes a clear leading suspect (``top_suspect``),
it announces *why* — ``"<color> sus: <reason 1>, <reason 2>"`` — instead of a generic
opener. Each reason is a short template for one kind of evidence the suspicion model
weighs, and they are ordered by how much that evidence moved the posterior, so the
chat leads with the most important point.

This is the presentation layer over the suspicion model: it reuses the per-event
log-LR functions (``suspicion.py``) to *rank* a suspect's evidence, then maps each
winning cue to a human phrase. Keep the phrasing here; keep the scoring in
``suspicion.py``.
"""

from __future__ import annotations

from crewrift.crewborg.strategy.meeting.schema import CHAT_MAX_CHARS
from crewrift.crewborg.strategy.suspicion import (
    WITNESSED_LOG_LR,
    _body_proximity_log_lr,
    _follow_log_lr,
    _tailing_self_log_lr,
    _vent_dwell_log_lr,
)
from crewrift.crewborg.types import Belief, PlayerEvent

# Cite at most this many reasons — the strongest cues — so the line stays readable.
MAX_REASONS = 3


def build_accusation(belief: Belief, color: str) -> str | None:
    """``"<color> sus: reason, reason"`` ranked strongest-first, or ``None`` when the
    suspect's log carries no citable evidence (so the caller stays silent)."""

    reasons = _ranked_reasons(belief, color)
    if not reasons:
        return None
    line = f"{color} sus: {', '.join(reasons[:MAX_REASONS])}"
    return line[:CHAT_MAX_CHARS]


def _ranked_reasons(belief: Belief, color: str) -> list[str]:
    """The suspect's evidence as phrases, ordered by each cue's log-LR (descending).

    One phrase per evidence *type* (its most-suspicious instance), mirroring how the
    posterior aggregates with ``max`` per type — so the chat doesn't repeat a cue.
    """

    record = belief.roster.get(color)
    if record is None:
        return []

    scored: list[tuple[float, str]] = []
    _add_witnessed(scored, record.events)
    _add_strongest(scored, record.events, "tailing_self", lambda e: _tailing_self_log_lr(e), _phrase_tail)
    _add_strongest(scored, record.events, "proximity", lambda e: _follow_log_lr(e, belief), _phrase_follow)
    _add_strongest(scored, record.events, "near_body", _body_proximity_log_lr, _phrase_near_body)
    _add_strongest(scored, record.events, "vent", _vent_dwell_log_lr, _phrase_vent_dwell)

    scored.sort(key=lambda item: item[0], reverse=True)
    return [phrase for _, phrase in scored]


def _add_witnessed(scored: list[tuple[float, str]], events: list[PlayerEvent]) -> None:
    """A witnessed catch is the strongest cue; cite the kill (with victim) or vent."""

    if any(e.kind == "kill" for e in events):
        victim = next(e.target_color for e in events if e.kind == "kill")
        scored.append((WITNESSED_LOG_LR + 1.0, f"saw them kill {victim}"))
    if any(e.kind == "vent_use" for e in events):
        scored.append((WITNESSED_LOG_LR, "saw them vent"))


def _add_strongest(scored, events, kind, log_lr, phrase) -> None:
    """Add the single most-suspicious instance of ``kind`` (if any cleared 0 log-LR)."""

    best: tuple[float, PlayerEvent] | None = None
    for event in events:
        if event.kind != kind:
            continue
        lr = log_lr(event)
        if lr > 0.0 and (best is None or lr > best[0]):
            best = (lr, event)
    if best is not None:
        scored.append((best[0], phrase(best[1])))


def _phrase_tail(event: PlayerEvent) -> str:
    return "they were tailing me"


def _phrase_follow(event: PlayerEvent) -> str:
    return f"followed {event.target_color} before they died"


def _phrase_near_body(event: PlayerEvent) -> str:
    return f"next to {event.target_color}'s body"


def _phrase_vent_dwell(event: PlayerEvent) -> str:
    return "lurking on a vent"
