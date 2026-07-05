# Unified Chat & Meeting-Behavior Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace crewborg's two disagreeing chat parsers (`chat_read.py`'s spaCy parser, `social_evidence.py`'s regex tally) with one unified extractor that also captures claim-typing (location/vent/task), verification against our own witnessed events, vote-timing, and speaking order — plus an optional LLM-bundled enrichment riding the existing meeting-decision call.

**Architecture:** `types.py` gains the new data shapes (`ChatClaim`, `VoteCast`) since `PlayerRecord` — which lives there — holds lists of them (avoids a circular import: `strategy/*` already imports from `types.py`, never the reverse). `strategy/meeting/chat_evidence.py` (new) is the pure parser + verifier, replacing `chat_read.py`. `strategy/social_evidence.py` (kept) becomes the orchestrator that calls it and folds output into `PlayerRecord`, and gains vote-order diffing + speaking-order tracking. `strategy/meeting/schema.py` gains the LLM's optional enrichment field.

**Tech Stack:** Python, pydantic v2, spaCy (existing `chat_nlp` module), pytest.

**Design doc:** `crewrift_lab/crewrift/crewborg/docs/designs/chat-evidence.md` — read this first; it has the full rationale. This plan implements it, with one correction the design doc doesn't spell out: `ChatClaim`/`VoteCast` are defined in `types.py`, not `chat_evidence.py`, per the import-direction constraint above.

## Global Constraints

- **No test-first ceremony as a routine step** (`AGENTS.md`, speed-first process): write the implementation, add a *targeted* unit test only where it's the fastest way to confirm a specific pure-function behavior (matches the existing `test_suspicion.py`/`test_meeting_context.py` style), then verify with the full suite (`uv run pytest crewrift_lab/crewrift/crewborg/tests -q`, ~6s) before committing. Do not write a failing-test-first RED step for every change.
- **All new pydantic models**: `model_config = ConfigDict(frozen=True, extra="forbid")`, matching every sibling model in `types.py` (`ChatEvent`, `PlayerEvent`, `VoteDot`).
- **Never let malformed LLM output break the whole decision.** Any new LLM-facing validation must degrade per-item (drop the bad item, keep going), never raise and reject the entire `MeetingDecision`.
- **Verification defaults to `unconfirmed`, never `contradicted`, on absence of data.** `contradicted` requires a positive conflicting observation.
- Run `uv run pytest crewrift_lab/crewrift/crewborg/tests -q` after every task; all tests must stay green (610+ passing, same skips as before) before moving to the next task.

---

### Task 1: New data shapes in `types.py`

**Files:**
- Modify: `crewrift_lab/crewrift/crewborg/types.py`
- Test: `crewrift_lab/crewrift/crewborg/tests/test_types.py` (create if it doesn't exist — check first with `find crewrift_lab/crewrift/crewborg/tests -iname "test_types.py"`; if it exists, add to it)

**Interfaces:**
- Produces: `ClaimType` (`Literal["accusation", "defense", "location", "vent", "task"]`), `VerificationStatus` (`Literal["confirmed", "contradicted", "unconfirmed"]`), `ChatClaim` (pydantic model), `VoteCast` (pydantic model), `PlayerRecord.claims: list[ChatClaim]`, `PlayerRecord.spoke_first_count: int`, `PlayerRecord.vote_history: list[VoteCast]`, `Belief.social_vote_order: list[tuple[int, int, int]]`.

- [ ] **Step 1: Read the existing `ChatEvent` and `PlayerRecord` definitions**

Run: `grep -n "class ChatEvent\|class PlayerRecord" -A 5 crewrift_lab/crewrift/crewborg/types.py`

This confirms the exact style to match (frozen models use `ConfigDict(frozen=True, extra="forbid")`; `PlayerRecord` uses `ConfigDict(extra="forbid")` without frozen since it's mutated in place).

- [ ] **Step 2: Add `ClaimType`, `VerificationStatus`, `ChatClaim`, `VoteCast` right after the `ChatEvent` class** (around line 256, immediately after `ChatEvent`'s closing line and before the `RECENT_FRAMES_MAX` comment)

```python
ClaimType = Literal["accusation", "defense", "location", "vent", "task"]
VerificationStatus = Literal["confirmed", "contradicted", "unconfirmed"]


class ChatClaim(BaseModel):
    """One claim extracted from a chat message (design: docs/designs/chat-evidence.md).

    ``target_color`` is who the claim is ABOUT — equal to ``speaker_color`` for a
    self-alibi. ``place_name`` is the matched room/task-station name, set only for
    ``location``/``task`` claims — ``vent`` claims never carry one: crewrift vents
    have no chat-nameable identity (only a synthetic ``group:group_index``, which no
    real message would say, especially post the tick/coordinate-avoidance prompt
    rule). ``verification`` is set for all three of location/vent/task (accusation/
    defense are suspicion stances, not checkable facts) and stays ``None`` until
    ``chat_evidence.verify_claim`` runs. ``source`` distinguishes the always-on spaCy
    extraction from optional LLM-bundled enrichment — both land in the same list on
    the same shape.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    tick: int
    speaker_color: str | None
    target_color: str
    claim_type: ClaimType
    place_name: str | None = None
    verification: VerificationStatus | None = None
    source: Literal["spacy", "llm"] = "spacy"


class VoteCast(BaseModel):
    """One player's vote, timestamped, for bandwagon-timing analysis (design:
    docs/designs/chat-evidence.md). ``rank`` is 1-indexed among a meeting's non-skip
    votes (1 = first to vote); skip votes are not timing-interesting and are not
    recorded here (see ``PlayerRecord.votes_skipped`` for the existing skip count).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    meeting_tick: int
    ticks_after_meeting_start: int
    target_color: str
    rank: int
```

You'll need `Literal` imported — check the top of the file with `grep -n "^from typing" crewrift_lab/crewrift/crewborg/types.py`; add `Literal` to that import if it isn't already there.

- [ ] **Step 3: Add the three new fields to `PlayerRecord`** — immediately after the existing `button_calls_made: int = 0` line (part of the "Cumulative social/public-evidence counters" block)

```python
    button_calls_made: int = 0
    # Chat claims made ABOUT this player (target_color == this color), spaCy- or
    # LLM-sourced; raw structured log, same pattern as `events` above — aggregated
    # by whoever needs a number later rather than pre-committed scalar counters.
    claims: list[ChatClaim] = Field(default_factory=list)
    # How many meetings this player was the first (non-us) speaker in.
    spoke_first_count: int = 0
    # Per-meeting vote timing (rank + ticks-after-meeting-start), one entry per
    # non-skip vote this player cast, across the whole episode.
    vote_history: list[VoteCast] = Field(default_factory=list)
```

- [ ] **Step 4: Add vote-order staging state to `Belief`** — immediately after the existing `social_banked_meeting_tick: int | None = None` line

```python
    social_banked_meeting_tick: int | None = None
    # Order-preserving staging for vote-timing (chat-evidence design): appended once
    # per (tick, voter_slot, target_slot) the FIRST time that pair is observed this
    # meeting; cleared when social_evidence commits the meeting (mirrors
    # social_staged_votes' lifecycle, but keeps order instead of discarding it).
    social_vote_order: list[tuple[int, int, int]] = Field(default_factory=list)
```

- [ ] **Step 5: Run the full test suite**

Run: `uv run pytest crewrift_lab/crewrift/crewborg/tests -q`
Expected: PASS, same count as before (this step only adds unused fields/models so far — nothing consumes them yet).

- [ ] **Step 6: Add a minimal test confirming the new shapes' defaults and frozen-ness**

Check whether `crewrift_lab/crewrift/crewborg/tests/test_types.py` exists (`find crewrift_lab/crewrift/crewborg/tests -iname "test_types.py"`). If not, create it:

```python
"""Tests for the new chat-evidence data shapes on types.py."""

from __future__ import annotations

import pytest

from crewrift.crewborg.types import Belief, ChatClaim, PlayerRecord, VoteCast


def test_chat_claim_is_frozen_and_defaults_to_spacy_source() -> None:
    claim = ChatClaim(tick=10, speaker_color="red", target_color="blue", claim_type="accusation")
    assert claim.source == "spacy"
    assert claim.verification is None
    with pytest.raises(Exception):
        claim.tick = 20  # frozen


def test_vote_cast_is_frozen() -> None:
    cast = VoteCast(meeting_tick=0, ticks_after_meeting_start=50, target_color="red", rank=1)
    with pytest.raises(Exception):
        cast.rank = 2  # frozen


def test_player_record_defaults_new_fields_empty() -> None:
    record = PlayerRecord(color="red")
    assert record.claims == []
    assert record.vote_history == []
    assert record.spoke_first_count == 0


def test_belief_defaults_vote_order_empty() -> None:
    assert Belief().social_vote_order == []
```

- [ ] **Step 7: Run the new test file**

Run: `uv run pytest crewrift_lab/crewrift/crewborg/tests/test_types.py -v`
Expected: 4 passed.

- [ ] **Step 8: Run the full suite, then commit**

Run: `uv run pytest crewrift_lab/crewrift/crewborg/tests -q`
Expected: all green.

```bash
git add crewrift_lab/crewrift/crewborg/types.py crewrift_lab/crewrift/crewborg/tests/test_types.py
git commit -m "feat(crewborg): add ChatClaim/VoteCast data shapes for unified chat evidence

Part 1/6 of the chat-evidence design (docs/designs/chat-evidence.md).
Defined in types.py, not chat_evidence.py, since PlayerRecord holds
lists of them and strategy/* imports from types.py, never the reverse."
```

---

### Task 2: `chat_evidence.py` — the unified parser + verifier (replaces `chat_read.py`)

**Files:**
- Create: `crewrift_lab/crewrift/crewborg/strategy/meeting/chat_evidence.py`
- Delete: `crewrift_lab/crewrift/crewborg/strategy/meeting/chat_read.py` (after confirming nothing outside this task's changes still imports it — Task 3 handles the two remaining call sites)
- Test: rename `crewrift_lab/crewrift/crewborg/tests/test_chat_read.py` → `crewrift_lab/crewrift/crewborg/tests/test_chat_evidence.py`, update its imports, add new tests

**Interfaces:**
- Consumes: `crewrift.crewborg.types.Belief, ChatClaim, ClaimType, PlayerEvent` (Task 1); `crewrift.crewborg.strategy.meeting.chat_nlp.get_model()` (existing, unchanged).
- Produces: `parse_claims(belief: Belief, event: "ChatEvent") -> list[ChatClaim]`, `verify_claim(belief: Belief, claim: ChatClaim) -> ChatClaim`, and the two API-compatible wrappers existing code depends on: `chat_accusers(belief: Belief, *, cache: dict[str, set[str]] | None = None) -> dict[str, int]` and `accused_colors(text: str, colors: set[str]) -> set[str]` (same names/signatures/return shapes as `chat_read.py` had — Task 3's consumers change only their import line).

- [ ] **Step 1: Read the current `chat_read.py` in full**

Run: `cat crewrift_lab/crewrift/crewborg/strategy/meeting/chat_read.py`

You're keeping its `_gate`, `_extract`, `_head_chain`, `_negated` logic essentially as-is (it's the good dependency-parse version) and extending `_extract` to also report *defends* (not just accuses), plus adding location/vent/task claim detection and verification alongside it.

- [ ] **Step 2: Write `chat_evidence.py`**

```python
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
    if not _gate(event.text, colors):
        return []
    doc = nlp(event.text)
    claims: list[ChatClaim] = []
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
    """Cheap filter: the message names a color and carries a sus cue — else skip spaCy."""

    tokens = set(text.lower().replace(",", " ").split())
    return bool(tokens & colors) and bool(tokens & SUS_WORDS)


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
```

- [ ] **Step 3: Delete `chat_read.py`**

Run: `rm crewrift_lab/crewrift/crewborg/strategy/meeting/chat_read.py`

(Task 3 fixes the two remaining importers; don't run the full suite yet, it will fail until Task 3 lands — that's expected and fine within this one task's scope since Steps 4-5 below only run the *new* test file, not the full suite.)

- [ ] **Step 4: Migrate the test file**

Run: `git mv crewrift_lab/crewrift/crewborg/tests/test_chat_read.py crewrift_lab/crewrift/crewborg/tests/test_chat_evidence.py`

Open it and change its import line from `from crewrift.crewborg.strategy.meeting.chat_read import ...` to `from crewrift.crewborg.strategy.meeting.chat_evidence import ...` (same function names, so only the module path changes). Then append these new tests to the bottom of the file:

```python
def test_parse_claims_detects_a_defense() -> None:
    belief = _belief_with_roster({"red", "blue"})
    event = ChatEvent(tick=5, speaker_color="red", text="blue is clear, trust them")
    claims = parse_claims(belief, event)
    assert any(c.target_color == "blue" and c.claim_type == "defense" for c in claims)


def test_parse_claims_detects_a_location_claim() -> None:
    belief = _belief_with_roster({"red"})
    belief.map = _map_with_room("Reactor")
    event = ChatEvent(tick=5, speaker_color="red", text="I was in reactor the whole time")
    claims = parse_claims(belief, event)
    location = [c for c in claims if c.claim_type == "location"]
    assert location and location[0].target_color == "red" and location[0].place_name == "Reactor"


def test_verify_claim_confirms_a_witnessed_room_visit() -> None:
    # duration_ticks is a computed @property (end_tick - start_tick + 1), not a
    # constructor field — never pass it to PlayerEvent(...).
    belief = _belief_with_roster({"red"})
    belief.map = _map_with_room("Reactor")
    belief.roster["red"].events.append(
        PlayerEvent(kind="room", start_tick=0, end_tick=10, region_index=0)
    )
    claim = ChatClaim(tick=20, speaker_color="red", target_color="red", claim_type="location", place_name="Reactor")
    assert verify_claim(belief, claim).verification == "confirmed"


def test_verify_claim_stays_unconfirmed_with_no_matching_event() -> None:
    belief = _belief_with_roster({"red"})
    belief.map = _map_with_room("Reactor")
    claim = ChatClaim(tick=20, speaker_color="red", target_color="red", claim_type="location", place_name="Reactor")
    assert verify_claim(belief, claim).verification == "unconfirmed"


def test_verify_claim_contradicts_on_a_different_witnessed_room() -> None:
    belief = _belief_with_roster({"red"})
    belief.map = _map_with_room("Reactor", "Bridge")
    belief.roster["red"].events.append(
        PlayerEvent(kind="room", start_tick=0, end_tick=10, region_index=1)  # Bridge
    )
    claim = ChatClaim(tick=20, speaker_color="red", target_color="red", claim_type="location", place_name="Reactor")
    assert verify_claim(belief, claim).verification == "contradicted"


def test_verify_claim_skips_llm_sourced_claims() -> None:
    belief = _belief_with_roster({"red"})
    belief.map = _map_with_room("Reactor")
    claim = ChatClaim(
        tick=20, speaker_color="red", target_color="red", claim_type="location",
        place_name="Reactor", source="llm",
    )
    assert verify_claim(belief, claim).verification is None


def test_verify_claim_confirms_a_vent_claim_from_any_witnessed_vent_use() -> None:
    # "vent_use" (the witnessed ACT of venting) is a different PlayerEventKind than
    # "room"/"task"/"vent" (dwelling-in-a-region kinds) — confirmed against
    # types.py's PlayerEventKind literal and suspicion.py's own witnessed-kill/vent
    # counter, which reads the same "vent_use" kind.
    belief = _belief_with_roster({"red"})
    belief.roster["red"].events.append(
        PlayerEvent(kind="vent_use", start_tick=0, end_tick=5)
    )
    claim = ChatClaim(tick=20, speaker_color="blue", target_color="red", claim_type="vent")
    assert verify_claim(belief, claim).verification == "confirmed"


def test_verify_claim_vent_stays_unconfirmed_never_contradicted() -> None:
    belief = _belief_with_roster({"red"})
    claim = ChatClaim(tick=20, speaker_color="blue", target_color="red", claim_type="vent")
    assert verify_claim(belief, claim).verification == "unconfirmed"
```

You'll need two small helpers at the top of the test file (check first whether the existing file already has an equivalent `_belief_with_roster`-style fixture before adding a duplicate):

```python
from crewrift.crewborg.map.types import MapData, MapPoint, MapRect, Room
from crewrift.crewborg.types import ChatClaim, ChatEvent, PlayerEvent, PlayerRecord


def _belief_with_roster(colors: set[str]) -> Belief:
    belief = Belief()
    for color in colors:
        belief.roster[color] = PlayerRecord(color=color)
    return belief


def _map_with_room(*room_names: str) -> MapData:
    # Room/TaskStation/Vent are all FLAT rects (name/x/y/w/h, no nested MapRect) —
    # confirmed against map/types.py; only MapData's own `button` field takes a
    # MapRect. Vent is intentionally left empty here: it has no `name` field at
    # all (only group/group_index), so no test in this file needs to construct one.
    return MapData(
        width=100, height=100,
        tasks=(), vents=(),
        rooms=tuple(Room(name=n, x=0, y=0, w=10, h=10) for n in room_names),
        button=MapRect(x=0, y=0, w=1, h=1), home=MapPoint(x=0, y=0),
    )
```

- [ ] **Step 5: Run the new test file only** (the full suite still fails until Task 3)

Run: `uv run pytest crewrift_lab/crewrift/crewborg/tests/test_chat_evidence.py -v`
Expected: all pass, including the pre-existing (migrated) tests and the 6 new ones above.

- [ ] **Step 6: Commit**

```bash
git add crewrift_lab/crewrift/crewborg/strategy/meeting/chat_evidence.py \
        crewrift_lab/crewrift/crewborg/tests/test_chat_evidence.py
git rm crewrift_lab/crewrift/crewborg/strategy/meeting/chat_read.py
git commit -m "feat(crewborg): chat_evidence.py — unified parser replacing chat_read.py

Part 2/6. Keeps chat_read.py's dependency-parse accuse/defend logic,
adds location/vent/task claim detection (belief.map name matching) and
verify_claim() (fuzzy witnessed-event cross-check, never contradicts
on absence of data). chat_accusers/accused_colors keep their exact
signatures so Task 3's import-path fix is the only change needed at
their call sites. Full suite intentionally red until Task 3 lands."
```

---

### Task 3: Repoint the two remaining `chat_read` importers

**Files:**
- Modify: `crewrift_lab/crewrift/crewborg/strategy/meeting/imposter.py`
- Modify: `crewrift_lab/crewrift/crewborg/modes/attend_meeting.py`

**Interfaces:**
- Consumes: `chat_accusers`, `accused_colors` from `chat_evidence.py` (Task 2) — identical names/signatures to what `chat_read.py` had.

- [ ] **Step 1: Find every remaining reference to `chat_read`**

Run: `grep -rn "chat_read" crewrift_lab/crewrift/crewborg/ --include="*.py"`

Expected: two import lines (one in `imposter.py`, one in `attend_meeting.py`) — if there are more, update those too, following the same pattern below.

- [ ] **Step 2: Update `imposter.py`'s import**

Find (likely near the top, check with `grep -n "chat_read" crewrift_lab/crewrift/crewborg/strategy/meeting/imposter.py`):
```python
from crewrift.crewborg.strategy.meeting import chat_read
```
or a `from ... import chat_accusers` style line — match whichever form is actually there and change `chat_read` to `chat_evidence` (module name only; if the file does `chat_read.chat_accusers(...)`, change the call site to `chat_evidence.chat_accusers(...)` too).

- [ ] **Step 3: Update `attend_meeting.py`'s import**

From the earlier investigation: `attend_meeting.py` does `from crewrift.crewborg.strategy.meeting import chat_nlp, chat_read` and calls `chat_read.chat_accusers(...)` / `chat_read.accused_colors(...)`. Change to:
```python
from crewrift.crewborg.strategy.meeting import chat_evidence, chat_nlp
```
and update every `chat_read.` call site in that file to `chat_evidence.` (run `grep -n "chat_read\." crewrift_lab/crewrift/crewborg/modes/attend_meeting.py` to find them all).

- [ ] **Step 4: Run the full test suite**

Run: `uv run pytest crewrift_lab/crewrift/crewborg/tests -q`
Expected: all green — this is the point where the whole suite goes back to passing (Task 2 left it red on purpose).

- [ ] **Step 5: Commit**

```bash
git add crewrift_lab/crewrift/crewborg/strategy/meeting/imposter.py \
        crewrift_lab/crewrift/crewborg/modes/attend_meeting.py
git commit -m "refactor(crewborg): repoint chat_read imports to chat_evidence

Part 3/6. Mechanical import-path change only — chat_accusers/
accused_colors kept identical signatures in Task 2 specifically so
this step needs no logic changes. Full suite green again."
```

---

### Task 4: `social_evidence.py` — route chat-stance counting through `chat_evidence.py`

**Files:**
- Modify: `crewrift_lab/crewrift/crewborg/strategy/social_evidence.py`
- Test: `crewrift_lab/crewrift/crewborg/tests/test_social_evidence.py`

**Interfaces:**
- Consumes: `chat_evidence.parse_claims(belief, event)`, `chat_evidence.verify_claim(belief, claim)` (Task 2).
- Produces: unchanged legacy counter behavior (`accusations_made`/`times_accused`/`times_defended` still increment — the trained model's `_fitted_features()` reads these by name and this task does not touch that model), plus `PlayerRecord.claims` now populated for real.

- [ ] **Step 1: Read the current `_count_chat_stances` and its regex helpers**

Run: `sed -n '1,105p' crewrift_lab/crewrift/crewborg/strategy/social_evidence.py`

You're deleting `ACCUSE_HINT`, `DEFEND_HINT`, `_color_pattern`, and the body of `_count_chat_stances`, replacing them with calls into `chat_evidence.py`.

- [ ] **Step 2: Replace the chat-stances section**

Delete the `ACCUSE_HINT`/`DEFEND_HINT` regex constants and the `_color_pattern`/`_count_chat_stances` functions. Replace with:

```python
from crewrift.crewborg.strategy.meeting import chat_evidence


def _count_chat_stances(belief: Belief) -> None:
    if not belief.chat_log:
        return
    for event in belief.chat_log:
        key = (event.tick, event.speaker_color, event.text)
        if key in belief.social_counted_chats:
            continue
        belief.social_counted_chats.add(key)
        for claim in chat_evidence.parse_claims(belief, event):
            if claim.claim_type in ("location", "vent", "task"):
                claim = chat_evidence.verify_claim(belief, claim)
            target = belief.roster.get(claim.target_color)
            speaker = belief.roster.get(claim.speaker_color) if claim.speaker_color else None
            if target is not None:
                target.claims.append(claim)
            if claim.claim_type == "accusation":
                if speaker is not None:
                    speaker.accusations_made += 1
                if target is not None:
                    target.times_accused += 1
            elif claim.claim_type == "defense" and target is not None:
                target.times_defended += 1
```

Note this preserves the exact same `accusations_made`/`times_accused`/`times_defended` semantics as before (still fed by chat, still bumped once per parsed claim) — only the parser underneath changed from regex to the dependency parse, and claims are now also retained on `target.claims`.

- [ ] **Step 3: Add the import at the top of the file**

Add near the other imports: `from crewrift.crewborg.strategy.meeting import chat_evidence` (if you didn't already put it inline above — move it to the top-of-file import block instead, matching the file's existing style).

- [ ] **Step 4: Update the existing chat-stance tests**

Run: `grep -n "ACCUSE_HINT\|DEFEND_HINT\|_color_pattern\|_count_chat_stances" crewrift_lab/crewrift/crewborg/tests/test_social_evidence.py`

Any test referencing the deleted regex constants directly needs its assertions changed to go through `_count_chat_stances`/`update_social_evidence` behaviorally instead (i.e., set up a `Belief` with a `chat_log` entry and a populated `belief.roster` with real colors, call `update_social_evidence(belief)`, then assert on the resulting `PlayerRecord.accusations_made`/`.claims`) — the test's *intent* (does an accusing message bump the right counters) is unchanged, only how it's driven changes from calling the regex helper directly to calling the public entry point.

- [ ] **Step 5: Add a test confirming claims land on `PlayerRecord.claims`**

Append to `test_social_evidence.py`:

```python
def test_accusation_chat_lands_a_claim_on_the_target(monkeypatch) -> None:
    import crewrift.crewborg.strategy.meeting.chat_nlp as chat_nlp_module
    belief = Belief()
    belief.roster["red"] = PlayerRecord(color="red")
    belief.roster["blue"] = PlayerRecord(color="blue")
    belief.chat_log = [ChatEvent(tick=5, speaker_color="red", text="blue is sus, saw them vent")]
    if chat_nlp_module.get_model() is None:
        pytest.skip("spaCy model not available in this environment")
    update_social_evidence(belief)
    claims = belief.roster["blue"].claims
    assert any(c.claim_type == "accusation" and c.speaker_color == "red" for c in claims)
    assert belief.roster["blue"].times_accused == 1
    assert belief.roster["red"].accusations_made == 1
```

Check the file's existing imports (`ChatEvent`, `PlayerRecord`, `pytest` likely already imported) and add any missing ones.

- [ ] **Step 6: Run the test file, then the full suite**

Run: `uv run pytest crewrift_lab/crewrift/crewborg/tests/test_social_evidence.py -v`
Expected: all pass (or skip, if spaCy isn't loaded in this environment — that's an acceptable pre-existing condition, not a regression).

Run: `uv run pytest crewrift_lab/crewrift/crewborg/tests -q`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add crewrift_lab/crewrift/crewborg/strategy/social_evidence.py \
        crewrift_lab/crewrift/crewborg/tests/test_social_evidence.py
git commit -m "feat(crewborg): social_evidence routes chat stances through chat_evidence.py

Part 4/6. Deletes the crude ACCUSE_HINT/DEFEND_HINT regex tally;
accusations_made/times_accused/times_defended now fed by the proper
dependency parse instead, and claims land on PlayerRecord.claims for
the first time. Trained-model feature names unchanged."
```

---

### Task 5: Vote-order diffing + speaking-order tracking

**Files:**
- Modify: `crewrift_lab/crewrift/crewborg/strategy/social_evidence.py`
- Test: `crewrift_lab/crewrift/crewborg/tests/test_social_evidence.py`

**Interfaces:**
- Consumes: `Belief.social_vote_order` (Task 1), `belief.voting.dots`/`belief.voting.candidates` (existing).
- Produces: `PlayerRecord.vote_history` entries at meeting-end; `PlayerRecord.spoke_first_count` increments.

- [ ] **Step 1: Read `_track_meeting_votes` in full**

Run: `grep -n "_track_meeting_votes" -A 35 crewrift_lab/crewrift/crewborg/strategy/social_evidence.py`

You're adding a diff step inside the "staging" branch (where it currently just overwrites `belief.social_staged_votes`) and a finalize step inside the "commit" branch (where it currently just increments `votes_cast`/`votes_skipped`/etc.).

- [ ] **Step 2: Add the diff step** — inside `_track_meeting_votes`, in the branch that currently does `if voting.dots and voting.candidates:` (the staging branch), add the order-tracking line right after `belief.social_staged_votes = {(d.voter, d.target) for d in voting.dots}`:

```python
        # social_staged_votes holds (voter, target) pairs (the current full snapshot,
        # overwritten every tick above); social_vote_order accumulates (tick, voter,
        # target) — diff against every pair already recorded, so each pair's tick is
        # stamped exactly once, the first time it's observed.
        already_seen = {(voter, target) for _, voter, target in belief.social_vote_order}
        for voter, target in belief.social_staged_votes - already_seen:
            belief.social_vote_order.append((belief.last_tick, voter, target))
```

- [ ] **Step 3: Add the finalize step** — inside the "commit" branch (after the existing loop that increments `votes_cast`/`votes_skipped`/`voted_against_me`/`vote_agreed_with_me`, but before `belief.social_staged_votes = set()` at the end), add:

```python
    meeting_tick = belief.social_staged_meeting_tick or 0
    non_skip_order = [
        (tick, voter, target) for tick, voter, target in belief.social_vote_order if target != SKIP_VOTE_TARGET
    ]
    non_skip_order.sort(key=lambda row: row[0])
    for rank, (tick, voter, target) in enumerate(non_skip_order, start=1):
        color = slots.get(voter)
        target_color = slots.get(target)
        record = belief.roster.get(color or "")
        if record is None or target_color is None:
            continue
        record.vote_history.append(
            VoteCast(
                meeting_tick=meeting_tick,
                ticks_after_meeting_start=tick - meeting_tick,
                target_color=target_color,
                rank=rank,
            )
        )
    belief.social_vote_order = []
```

- [ ] **Step 4: Add the imports**

At the top of `social_evidence.py`, add `VoteCast` to the existing `from crewrift.crewborg.types import Belief` line (make it `from crewrift.crewborg.types import Belief, VoteCast`).

- [ ] **Step 5: Add `_track_speaking_order` and wire it into `update_social_evidence`**

Read `update_social_evidence`'s current body first (`grep -n "def update_social_evidence" -A 8 crewrift_lab/crewrift/crewborg/strategy/social_evidence.py`), then add a new function near `_track_meeting_votes`:

```python
def _track_speaking_order(belief: Belief) -> None:
    """Credit whoever was the first non-us speaker in a meeting, once per meeting."""

    if belief.phase != "Voting" or not belief.chat_log:
        return
    meeting_tick = belief.phase_start_tick
    if belief.social_spoke_first_banked_tick == meeting_tick:
        return
    self_color = belief.self_color or belief.voting.self_marker_color
    meeting_messages = [e for e in belief.chat_log if e.tick >= meeting_tick]
    first_other = next((e for e in meeting_messages if e.speaker_color and e.speaker_color != self_color), None)
    if first_other is None:
        return
    record = belief.roster.get(first_other.speaker_color)
    if record is not None:
        record.spoke_first_count += 1
    belief.social_spoke_first_banked_tick = meeting_tick
```

and add the call inside `update_social_evidence`'s body, alongside the existing `_count_chat_stances(belief)` / `_track_meeting_votes(belief)` calls:

```python
    _track_speaking_order(belief)
```

This needs one more piece of staging state on `Belief` — go back to `types.py` and add, right next to `social_caller_banked_tick: int | None = None`:

```python
    social_spoke_first_banked_tick: int | None = None
```

- [ ] **Step 6: Write tests for both**

Append to `test_social_evidence.py`:

```python
def test_vote_history_records_rank_and_timing_in_cast_order() -> None:
    from crewrift.crewborg.perception.entities import VoteCandidate, VoteDot, VotingState

    belief = Belief(phase="Voting", phase_start_tick=100, last_tick=100)
    belief.roster["red"] = PlayerRecord(color="red")
    belief.roster["blue"] = PlayerRecord(color="blue")
    belief.voting = VotingState(
        candidates=(VoteCandidate(slot=0, color="red", alive=True), VoteCandidate(slot=1, color="blue", alive=True)),
        dots=(VoteDot(voter=0, target=1),),
    )
    update_social_evidence(belief)  # red votes for blue at tick 100

    belief.last_tick = 140
    belief.voting = VotingState(
        candidates=belief.voting.candidates,
        dots=(VoteDot(voter=0, target=1), VoteDot(voter=1, target=0)),
    )
    update_social_evidence(belief)  # blue votes for red at tick 140 (later)

    belief.phase = "Playing"  # meeting ends -> commit
    belief.voting = VotingState()
    update_social_evidence(belief)

    assert belief.roster["red"].vote_history == [
        VoteCast(meeting_tick=100, ticks_after_meeting_start=0, target_color="blue", rank=1)
    ]
    assert belief.roster["blue"].vote_history == [
        VoteCast(meeting_tick=100, ticks_after_meeting_start=40, target_color="red", rank=2)
    ]


def test_spoke_first_count_credits_the_first_non_self_speaker() -> None:
    belief = Belief(phase="Voting", phase_start_tick=50, last_tick=60, self_color="green")
    belief.roster["red"] = PlayerRecord(color="red")
    belief.roster["blue"] = PlayerRecord(color="blue")
    belief.chat_log = [
        ChatEvent(tick=52, speaker_color="blue", text="hello"),
        ChatEvent(tick=55, speaker_color="red", text="hi"),
    ]
    update_social_evidence(belief)
    assert belief.roster["blue"].spoke_first_count == 1
    assert belief.roster["red"].spoke_first_count == 0
```

Check `Belief`'s actual field name for "our own color" (`self_color` was referenced in `_note_own_accusation` earlier — confirm with `grep -n "self_color" crewrift_lab/crewrift/crewborg/types.py | head -3`) and adjust the test if the constructor doesn't accept it directly.

- [ ] **Step 7: Run the test file, then the full suite**

Run: `uv run pytest crewrift_lab/crewrift/crewborg/tests/test_social_evidence.py -v`
Expected: all pass — if the vote-order test fails on rank/timing, re-check Step 2's diffing logic against the actual tick sequence you fed it (this is exactly the kind of pure-function bug a quick test is the fastest way to catch, per the Global Constraints).

Run: `uv run pytest crewrift_lab/crewrift/crewborg/tests -q`
Expected: all green.

- [ ] **Step 8: Commit**

```bash
git add crewrift_lab/crewrift/crewborg/strategy/social_evidence.py \
        crewrift_lab/crewrift/crewborg/types.py \
        crewrift_lab/crewrift/crewborg/tests/test_social_evidence.py
git commit -m "feat(crewborg): vote-order diffing + speaking-order tracking

Part 5/6. PlayerRecord.vote_history now records rank + ticks-after-
meeting-start per non-skip vote (bandwagon-timing signal); spoke_first_count
credits the first non-self meeting speaker. Both purely additive —
existing votes_cast/votes_skipped/voted_against_me counters untouched."
```

---

### Task 6: LLM enrichment schema — `ChatEvidenceTag` + `MeetingDecision.chat_evidence`

**Files:**
- Modify: `crewrift_lab/crewrift/crewborg/strategy/meeting/schema.py`
- Modify: `crewrift_lab/crewrift/crewborg/strategy/meeting/chat_evidence.py` (add the application function)
- Test: `crewrift_lab/crewrift/crewborg/tests/test_meeting_llm.py` (schema-level) and `crewrift_lab/crewrift/crewborg/tests/test_chat_evidence.py` (application-level)

**Interfaces:**
- Produces: `ChatEvidenceTag` (pydantic model, in `schema.py`), `MeetingDecision.chat_evidence: list[dict[str, Any]]` (deliberately loose at the pydantic level — see Step 1 for why), `chat_evidence.apply_llm_tags(belief: Belief, raw_tags: list[dict[str, Any]]) -> None`.

- [ ] **Step 1: Why `chat_evidence` is typed loosely on `MeetingDecision` — read this before writing code**

The design doc says a malformed tag should degrade *per-tag*, not break the whole decision. If `MeetingDecision.chat_evidence` were typed as `list[ChatEvidenceTag]` directly, pydantic would raise on the WHOLE `MeetingDecision` the moment any single tag has a bad `claim_type` or missing field — exactly the per-decision failure the design doc rules out. So: `MeetingDecision.chat_evidence` stays `list[dict[str, Any]]` (loose) at the schema level, and a separate function tries to construct `ChatEvidenceTag` from each dict one at a time, skipping the ones that fail.

- [ ] **Step 2: Add `ChatEvidenceTag` and the `chat_evidence` field to `schema.py`**

In `crewrift_lab/crewrift/crewborg/strategy/meeting/schema.py`, add near `MeetingDecision`:

```python
class ChatEvidenceTag(BaseModel):
    """The LLM's own read on a chat message's stance/credibility (design:
    docs/designs/chat-evidence.md). Validated per-tag by chat_evidence.apply_llm_tags,
    never as part of MeetingDecision's own validation — a malformed tag must never
    block the chat/vote action it rode in on."""

    model_config = ConfigDict(extra="forbid")

    speaker_color: str
    target_color: str
    stance: Literal["accuse", "defend", "neutral"]
    claim_type: Literal["accusation", "defense", "location", "vent", "task"]
    credibility: float | None = Field(default=None, ge=0.0, le=1.0)
    note: str | None = None
```

Add `Any` to the `typing` import at the top (`from typing import Any, Literal`), and add this field to `MeetingDecision`, right after `confidence`:

```python
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    # Optional LLM-bundled chat enrichment (Approach B) — deliberately loose (raw
    # dicts, not list[ChatEvidenceTag]) so one malformed tag can't fail the whole
    # decision's validation. chat_evidence.apply_llm_tags validates each one.
    chat_evidence: list[dict[str, Any]] = Field(default_factory=list)
```

- [ ] **Step 3: Add `apply_llm_tags` to `chat_evidence.py`**

```python
from crewrift.crewborg.strategy.meeting.schema import ChatEvidenceTag
from crewrift.crewborg.types import ChatClaim


def apply_llm_tags(belief: Belief, raw_tags: list[dict]) -> None:
    """Validate the LLM's chat_evidence tags one at a time, converting each valid
    one into a ChatClaim(source="llm") appended to its target's claims. An invalid
    tag (unknown color, bad claim_type, missing field) is silently dropped — never
    raised — per the design doc's per-tag degradation rule."""

    colors = set(belief.roster)
    for raw in raw_tags:
        try:
            tag = ChatEvidenceTag(**raw)
        except Exception:
            continue
        if tag.speaker_color not in colors or tag.target_color not in colors:
            continue
        claim = ChatClaim(
            tick=belief.last_tick,
            speaker_color=tag.speaker_color,
            target_color=tag.target_color,
            claim_type=tag.claim_type,
            source="llm",
        )
        record = belief.roster.get(tag.target_color)
        if record is not None:
            record.claims.append(claim)
```

- [ ] **Step 4: Write tests**

Append to `test_chat_evidence.py`:

```python
def test_apply_llm_tags_lands_a_valid_tag_as_an_llm_sourced_claim() -> None:
    belief = _belief_with_roster({"red", "blue"})
    belief.last_tick = 42
    apply_llm_tags(belief, [
        {"speaker_color": "red", "target_color": "blue", "stance": "accuse", "claim_type": "accusation", "credibility": 0.8}
    ])
    claims = belief.roster["blue"].claims
    assert len(claims) == 1
    assert claims[0].source == "llm" and claims[0].speaker_color == "red"


def test_apply_llm_tags_drops_a_tag_with_an_unknown_color() -> None:
    belief = _belief_with_roster({"red", "blue"})
    apply_llm_tags(belief, [
        {"speaker_color": "red", "target_color": "purple", "stance": "accuse", "claim_type": "accusation"}
    ])
    assert belief.roster["blue"].claims == []


def test_apply_llm_tags_drops_a_malformed_tag_without_raising() -> None:
    belief = _belief_with_roster({"red", "blue"})
    apply_llm_tags(belief, [{"speaker_color": "red", "claim_type": "not-a-real-type"}])  # missing fields, bad enum
    assert belief.roster["red"].claims == [] and belief.roster["blue"].claims == []
```

Append to `test_meeting_llm.py` (schema-level check that a malformed tag doesn't break `MeetingDecision` construction itself):

```python
def test_meeting_decision_accepts_chat_evidence_as_loose_dicts() -> None:
    decision = MeetingDecision(
        action="wait",
        chat_evidence=[{"speaker_color": "red", "claim_type": "not-a-real-type"}],  # malformed, but MeetingDecision itself must still construct
    )
    assert decision.chat_evidence == [{"speaker_color": "red", "claim_type": "not-a-real-type"}]
```

(Check the file's existing imports for `MeetingDecision` before adding this — it's almost certainly already imported.)

- [ ] **Step 5: Run both test files, then the full suite**

Run: `uv run pytest crewrift_lab/crewrift/crewborg/tests/test_chat_evidence.py crewrift_lab/crewrift/crewborg/tests/test_meeting_llm.py -v`
Expected: all pass.

Run: `uv run pytest crewrift_lab/crewrift/crewborg/tests -q`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add crewrift_lab/crewrift/crewborg/strategy/meeting/schema.py \
        crewrift_lab/crewrift/crewborg/strategy/meeting/chat_evidence.py \
        crewrift_lab/crewrift/crewborg/tests/test_chat_evidence.py \
        crewrift_lab/crewrift/crewborg/tests/test_meeting_llm.py
git commit -m "feat(crewborg): LLM chat-evidence enrichment schema (Approach B)

Part 6/6. MeetingDecision.chat_evidence is deliberately typed as loose
dicts (not list[ChatEvidenceTag]) so one malformed LLM tag degrades
per-tag via apply_llm_tags(), never breaking the whole decision's
validation. Not yet wired into attend_meeting.py's decision-apply path
(next task)."
```

---

### Task 7: Wire LLM enrichment into the meeting-decision apply path

**Files:**
- Modify: `crewrift_lab/crewrift/crewborg/modes/attend_meeting.py`

**Interfaces:**
- Consumes: `chat_evidence.apply_llm_tags(belief, decision.chat_evidence)` (Task 6, already unit-tested there in isolation).

**No new test file for this task.** Confirmed by search (`find crewrift_lab/crewrift/crewborg/tests -iname "*attend_meeting*"` returns nothing, and `grep -rln "_apply_decision\|class AttendMeeting" crewrift_lab/crewrift/crewborg/tests/*.py` matches nothing): `AttendMeetingMode` has no existing unit test file or construction fixture anywhere in this codebase — it's exercised only through the hosted-eval loop. This task is a one-line call to an already-tested function (`apply_llm_tags`, covered in Task 6); inventing a new integration-test harness for a mode class the codebase has never unit-tested is exactly the kind of test scaffolding `AGENTS.md`'s speed-first process rules out for a change this size. Verification is the full suite staying green (regression safety) plus the next experience-request eval (the real test, per the loop).

- [ ] **Step 1: Read `_apply_decision`**

Run: `grep -n "_apply_decision" -A 30 crewrift_lab/crewrift/crewborg/modes/attend_meeting.py`

- [ ] **Step 2: Call `apply_llm_tags` at the top of `_apply_decision`**

Add as the first line inside `_apply_decision`, before `self._maybe_arm_instant_vote(belief, decision)`:

```python
        chat_evidence.apply_llm_tags(belief, decision.chat_evidence)
```

(`chat_evidence` should already be imported from Task 3's changes to this file — confirm with `grep -n "^from crewrift.crewborg.strategy.meeting import" crewrift_lab/crewrift/crewborg/modes/attend_meeting.py`.)

- [ ] **Step 3: Run the full test suite**

Run: `uv run pytest crewrift_lab/crewrift/crewborg/tests -q`
Expected: all green — this is the final task, so this is the last full-suite check for the whole feature.

- [ ] **Step 4: Commit**

```bash
git add crewrift_lab/crewrift/crewborg/modes/attend_meeting.py
git commit -m "feat(crewborg): wire LLM chat-evidence tags into the decision-apply path

Final task of the chat-evidence design (docs/designs/chat-evidence.md).
Every meeting decision now applies its optional chat_evidence tags
(if any) alongside the existing chat/vote handling — spaCy's own pass
over the same messages already ran independently in social_evidence.py,
so coverage never depends on the LLM tagging anything."
```

---

## After all 7 tasks

Run the full suite one more time (`uv run pytest crewrift_lab/crewrift/crewborg/tests -q`) and confirm the count is 610 + (new tests added across tasks 1, 2, 4, 5, 6, 7). This feature is now ready for the same build-and-upload → experience-request evaluation loop as everything else in this lab — per `AGENTS.md`, no additional pre-upload gate beyond the tests already run task-by-task above.
