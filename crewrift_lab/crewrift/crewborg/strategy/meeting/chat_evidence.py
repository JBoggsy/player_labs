"""Unified chat & meeting-behavior evidence extraction (design:
docs/designs/chat-evidence.md).

Replaces two systems that used to disagree: chat_read.py's proper spaCy
dependency parse (kept here) and social_evidence.py's cruder regex tally
(deleted; social_evidence.py now calls parse_claims() below instead).

The target vocabulary is a closed set of player colors, which the dependency
parse exploits the same way chat_read.py did: gate cheaply on a color + a cue
word, then parse only the messages that pass. Free chat also mentions rooms
and vents by name (belief.map), which the same gate-then-parse shape extends
to naturally.
"""

from __future__ import annotations

from typing import Any

from crewrift.crewborg.strategy.meeting import chat_nlp
from crewrift.crewborg.types import Belief, ChatClaim, ChatEvent, ClaimType

# Cues that an utterance is an accusation. Closed, tunable; inflections included so we
# can match on the lowercase token without depending on the lemmatizer.
SUS_WORDS = frozenset({
    "sus", "suspicious", "vent", "vented", "venting", "vents", "kill", "killed", "kills",
    "body", "dead", "died", "vote", "votes", "voting", "imp", "imposter", "impostor",
    "fake", "faking", "faked", "follow", "following", "followed", "lying", "lie", "lied",
    "did", "saw", "report",
})
# Negation cues — checked against the dependency tree, not bare presence.
NEG_WORDS = frozenset({"not", "n't", "no", "never", "isnt", "dont", "doesnt", "cant", "aint"})
# Defense/clearing cues that govern a color's clause flip it to "not accused" (and,
# newly, register as a positive "defends" claim rather than just a non-accusation).
DEFENSE_WORDS = frozenset({"innocent", "clear", "cleared", "vouch", "trust", "safe", "good", "sure", "with"})
# A victim cue adjacent to a color marks it as the *victim*, not the suspect.
VICTIM_WORDS = frozenset({"died", "dead", "body", "killed"})
# Cues a message is claiming a LOCATION (a room/vent/task-station name is present).
VENT_CLAIM_WORDS = frozenset({"vent", "vented", "venting", "vents"})
TASK_CLAIM_WORDS = frozenset({"task", "tasks", "wire", "wires", "fuel", "fueling"})
# First-person cues for a self-alibi ("I was in X") — a player states their OWN
# location/vent/task without naming their own color (nobody names themselves).
FIRST_PERSON_WORDS = frozenset({"i", "i'm", "im", "ive", "i've", "my", "myself"})


def parse_claims(belief: Belief, event: ChatEvent) -> list[ChatClaim]:
    """All claims one chat message makes: accusations, defenses, and any
    location/vent/task claim (self-alibi or third-party) it names a place for.

    Empty when the NLP model is disabled or still loading — no crude fallback (a
    deliberate choice inherited from chat_read.py: false positives here are worse
    than no signal).
    """

    nlp = chat_nlp.get_model()
    if nlp is None:
        return []
    colors = set(belief.roster)
    claims: list[ChatClaim] = []
    lowered_words = set(event.text.lower().replace(",", " ").split())

    if _gate(event.text, colors):
        doc = nlp(event.text)
        for tok in doc:
            if tok.lower_ not in colors:
                continue
            chain = _head_chain(tok)
            clause = {t for c in chain for t in c.subtree}
            clause_words = {t.lower_ for t in clause}
            has_sus_cue = bool(clause_words & SUS_WORDS)
            is_victim = any(t.lower_ in VICTIM_WORDS and abs(t.i - tok.i) <= 2 for t in doc)
            negated_or_defended = _negated(doc, chain, clause)
            place_name = _match_place_name(belief, event.text)

            if has_sus_cue and not is_victim:
                if negated_or_defended:
                    claims.append(_claim(event, tok.lower_, "defense"))
                else:
                    claims.append(_claim(event, tok.lower_, "accusation"))
            elif negated_or_defended and any(t.lower_ in DEFENSE_WORDS for t in clause):
                claims.append(_claim(event, tok.lower_, "defense"))

            if clause_words & VENT_CLAIM_WORDS:
                # Vents have no chat-nameable identity (only a synthetic group:index),
                # so a vent claim never carries a place_name — see ChatClaim's docstring.
                claims.append(_claim(event, tok.lower_, "vent"))
            elif place_name is not None:
                claim_type: ClaimType = "task" if clause_words & TASK_CLAIM_WORDS else "location"
                claims.append(_claim(event, tok.lower_, claim_type, place_name=place_name))

    # Self-alibi: independent of the color-mention gate above, since a
    # first-person statement usually never names the speaker's own color. Only
    # fires when the message names NO known color at all — if it names one,
    # the per-color-token loop above already handled it (correctly attributed
    # to whoever was named, e.g. "I saw red vent in reactor" attaches to red,
    # not to the speaker), so there is nothing left for this path to add.
    if (
        event.speaker_color is not None
        and lowered_words & FIRST_PERSON_WORDS
        and not (lowered_words & colors)
    ):
        if lowered_words & VENT_CLAIM_WORDS:
            claims.append(_claim(event, event.speaker_color, "vent"))
        else:
            place_name = _match_place_name(belief, event.text)
            if place_name is not None:
                claim_type: ClaimType = "task" if lowered_words & TASK_CLAIM_WORDS else "location"
                claims.append(_claim(event, event.speaker_color, claim_type, place_name=place_name))
    return claims


def verify_claim(belief: Belief, claim: ChatClaim) -> ChatClaim:
    """Fill in ``.verification`` for a location/vent/task claim by checking it
    against what we actually witnessed of ``claim.target_color``. Accusation/defense
    claims (not verifiable facts) are returned unchanged. LLM-sourced claims are
    also returned unchanged — the LLM's own credibility/note IS its judgment;
    running this check on top would score the same thing twice, two different ways.

    Absence of a matching event is `unconfirmed`, never `contradicted` — our
    visibility is partial, so "we didn't see it" is not evidence against it.

    Vent claims are a deliberately narrower check than location/task: since a vent
    has no chat-nameable identity, we can only ask "did we ever witness THIS player
    vent at all" (confirmed/unconfirmed) — there's no named place to contradict
    against, so vent claims never resolve to `contradicted`.
    """

    if claim.claim_type not in ("location", "vent", "task") or claim.source == "llm":
        return claim
    record = belief.roster.get(claim.target_color)
    if record is None:
        return claim
    if claim.claim_type == "vent":
        # "vent_use" is the witnessed ACT of venting — distinct from the "vent"
        # PlayerEventKind (dwelling near a vent region), same distinction
        # suspicion.py's own witnessed-kill/vent counter already relies on.
        witnessed_any_vent = any(e.kind == "vent_use" for e in record.events)
        return claim.model_copy(update={"verification": "confirmed" if witnessed_any_vent else "unconfirmed"})
    if belief.map is None:
        return claim
    kind = "task" if claim.claim_type == "task" else "room"
    same_kind_places = {
        _place_name_for(belief, e.kind, e.region_index)
        for e in record.events
        if e.kind == kind and e.region_index is not None
    }
    same_kind_places.discard(None)
    if claim.place_name in same_kind_places:
        return claim.model_copy(update={"verification": "confirmed"})
    if same_kind_places:
        return claim.model_copy(update={"verification": "contradicted"})
    return claim.model_copy(update={"verification": "unconfirmed"})


def chat_accusers(belief: Belief, *, cache: dict[str, set[str]] | None = None) -> dict[str, int]:
    """Per non-teammate color, the count of *distinct other speakers* who accused
    them in chat. Same contract as the old chat_read.chat_accusers: used by the
    imposter's reactive bandwagon (strategy.meeting.imposter) to know who to pile
    onto before it hardens into a vote."""

    self_color = belief.voting.self_marker_color
    cache = cache if cache is not None else {}
    by_color: dict[str, set[str | None]] = {}
    for event in belief.chat_log:
        if event.speaker_color is not None and event.speaker_color == self_color:
            continue
        key = event.text
        if key not in cache:
            cache[key] = {
                claim.target_color
                for claim in parse_claims(belief, event)
                if claim.claim_type == "accusation"
            }
        for color in cache[key]:
            by_color.setdefault(color, set()).add(event.speaker_color)
    return {
        color: len(speakers)
        for color, speakers in by_color.items()
        if color not in belief.teammate_colors and color != self_color
    }


def accused_colors(text: str, colors: set[str]) -> set[str]:
    """The colors a single message accuses. Same contract as the old
    chat_read.accused_colors: used on crewborg's own outgoing chat to derive the
    chat-implied fallback vote (accuse-then-skip is a tell; vote whom we accused)."""

    nlp = chat_nlp.get_model()
    if nlp is None or not _gate(text, colors):
        return set()
    doc = nlp(text)
    accused: set[str] = set()
    for tok in doc:
        if tok.lower_ not in colors:
            continue
        chain = _head_chain(tok)
        clause = {t for c in chain for t in c.subtree}
        has_cue = any(t.lower_ in SUS_WORDS for t in clause)
        if not has_cue:
            continue
        is_victim = any(t.lower_ in VICTIM_WORDS and abs(t.i - tok.i) <= 2 for t in doc)
        if is_victim:
            continue
        if not _negated(doc, chain, clause):
            accused.add(tok.lower_)
    return accused


def _claim(event: ChatEvent, target_color: str, claim_type: ClaimType, *, place_name: str | None = None) -> ChatClaim:
    return ChatClaim(
        tick=event.tick,
        speaker_color=event.speaker_color,
        target_color=target_color,
        claim_type=claim_type,
        place_name=place_name,
    )


def _gate(text: str, colors: set[str]) -> bool:
    """Cheap filter: the message names a color and carries a sus OR defense cue — else skip spaCy."""

    tokens = set(text.lower().replace(",", " ").split())
    return bool(tokens & colors) and bool(tokens & (SUS_WORDS | DEFENSE_WORDS))


def _head_chain(tok: Any, depth: int = 6) -> list[Any]:
    chain = [tok]
    head = tok
    for _ in range(depth):
        if head.head == head:
            break
        head = head.head
        chain.append(head)
    return chain


def _negated(doc: Any, chain: list[Any], clause: set[Any]) -> bool:
    chainset = set(chain)
    return (
        any(child.dep_ == "neg" for c in chain for child in c.children)
        or any(t.lower_ in NEG_WORDS and t.head in chainset for t in doc)
        or any(t.lower_ in DEFENSE_WORDS and (t.head in chainset or t in clause) for t in doc)
    )


def _match_place_name(belief: Belief, text: str) -> str | None:
    """The first room or task-station name mentioned in ``text``, or None. Vents are
    deliberately excluded — crewrift's ``Vent`` model has no ``name`` field (only a
    synthetic ``group``/``group_index``), so there's no string a real chat message
    could plausibly contain to name one; see ``ChatClaim``'s docstring."""

    if belief.map is None:
        return None
    lowered = text.lower()
    for room in belief.map.rooms:
        if room.name.lower() in lowered:
            return room.name
    for task in belief.map.tasks:
        if task.name.lower() in lowered:
            return task.name
    return None


def _place_name_for(belief: Belief, kind: str, region_index: int) -> str | None:
    """Room/task name for a witnessed event's region — used only by verify_claim's
    location/task path. Never called for kind=="vent" (see verify_claim)."""

    assert belief.map is not None
    if kind == "room" and 0 <= region_index < len(belief.map.rooms):
        return belief.map.rooms[region_index].name
    if kind == "task" and 0 <= region_index < len(belief.map.tasks):
        return belief.map.tasks[region_index].name
    return None
