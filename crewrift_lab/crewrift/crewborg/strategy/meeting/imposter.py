"""Imposter meeting tactics: who to bandwagon onto (design §10.4).

The imposter never targets a teammate. When it has no strong real deflection of its
own (``top_suspect`` over non-teammates, see ``suspicion.py``), it waits and watches
for a crewmate to take **heat** — a vote cast against them (the reliable signal, read
from the vote tally) or a chat accusation (the additive ``chat_evidence`` signal) — then
piles on. This module turns those signals into a single bandwagon target.
"""

from __future__ import annotations

from crewrift.crewborg.types import Belief

# A cast vote is a stronger "heat" signal than a single chat accusation.
VOTE_WEIGHT = 2
CHAT_WEIGHT = 1


def votes_against(belief: Belief) -> dict[str, int]:
    """Count of votes cast against each candidate color, by players other than us
    (skip votes and our own ballot excluded)."""

    candidates = belief.voting.candidates
    slot_to_color = {c.slot: c.color for c in candidates}
    self_color = belief.voting.self_marker_color
    self_slot = next((c.slot for c in candidates if c.color == self_color), None)

    tally: dict[str, int] = {}
    for dot in belief.voting.dots:
        if dot.is_skip or dot.voter == self_slot:
            continue
        color = slot_to_color.get(dot.target)
        if color is not None:
            tally[color] = tally.get(color, 0) + 1
    return tally


def bandwagon_target(belief: Belief, chat_accusers: dict[str, int] | None = None) -> str | None:
    """The non-teammate crewmate under the most heat that we can pile onto, or ``None``.

    Heat = votes·``VOTE_WEIGHT`` + distinct chat accusers·``CHAT_WEIGHT``. Excludes
    teammates, self, the dead, and skip. Any heat at all makes a crewmate eligible
    ("someone has sussed or voted for them"); the most-heated one wins ties by votes.
    """

    accusers = chat_accusers or {}
    tally = votes_against(belief)
    self_color = belief.voting.self_marker_color
    alive_colors = {c.color for c in belief.voting.candidates if c.alive}

    best: tuple[str, int] | None = None
    for color in set(tally) | set(accusers):
        if color in belief.teammate_colors or color == self_color:
            continue
        if alive_colors and color not in alive_colors:
            continue  # can't eject the dead (skip the filter when the grid is unknown)
        heat = tally.get(color, 0) * VOTE_WEIGHT + accusers.get(color, 0) * CHAT_WEIGHT
        if heat <= 0:
            continue
        if best is None or heat > best[1]:
            best = (color, heat)
    return best[0] if best is not None else None


def heat_on_self(belief: Belief, self_accusers: set[str] | None = None) -> int:
    """How much heat OUR seat is taking this meeting: votes cast on our slot
    (weighted like any other heat) + distinct chat accusers of our color.

    The bandwagon/parity tallies exclude self by design, so an imposter whose only
    meeting heat is on itself sees no target and idles to a silent skip — the
    measured 62%-ejected-after-witnessed-kill path. This is the trigger for the
    counter-accusation response (design 2026-07-21-imposter-kill-to-win)."""

    self_color = belief.voting.self_marker_color or belief.self_color
    if self_color is None:
        return 0
    self_slot = next((c.slot for c in belief.voting.candidates if c.color == self_color), None)
    votes_on_self = sum(
        1 for dot in belief.voting.dots if not dot.is_skip and dot.target == self_slot and dot.voter != self_slot
    )
    accusers = self_accusers or set()
    return votes_on_self * VOTE_WEIGHT + len(accusers) * CHAT_WEIGHT


def counter_accusation_target(belief: Belief, self_accusers: set[str] | None = None) -> str | None:
    """The accuser to counter-accuse when we are taking heat, or ``None``.

    Accusers = the chat accusers of our color plus anyone whose ballot targets our
    slot (heat can be votes-only, with no chat line to answer). Never a teammate,
    never self, never the dead. Prefers the accuser who ALSO leads the general
    votes-against tally (their eviction both removes the witness-claimer and joins
    any existing pile), ties broken by lowest slot so two imposters under fire
    converge. Deflection only — the chat-study rule stands: never answer an
    accusation with "not me"."""

    self_color = belief.voting.self_marker_color or belief.self_color
    candidates = belief.voting.candidates
    slot_by_color = {c.slot: c.color for c in candidates}
    self_slot = next((c.slot for c in candidates if c.color == self_color), None)
    accusers = set(self_accusers or set())
    if self_slot is not None:
        for dot in belief.voting.dots:
            if not dot.is_skip and dot.target == self_slot and dot.voter != self_slot:
                voter_color = slot_by_color.get(dot.voter)
                if voter_color is not None:
                    accusers.add(voter_color)
    if not accusers:
        return None
    alive_colors = {c.color for c in candidates if c.alive}
    slot_of = {c.color: c.slot for c in candidates}
    tally = votes_against(belief)

    eligible = [
        color
        for color in accusers
        if color != self_color
        and color not in belief.teammate_colors
        and (not alive_colors or color in alive_colors)
    ]
    if not eligible:
        return None
    return max(eligible, key=lambda color: (tally.get(color, 0), -slot_of.get(color, 99)))


def alive_imposter_count(belief: Belief) -> int:
    """How many imposters are alive *that we can account for* — ourself plus every
    known teammate the meeting census still lists alive. Self-gating value: it is 1
    when we don't know a live teammate (no reveal captured), so callers that need
    the real imposter count stay conservative rather than acting on a wrong roster.
    """

    alive_colors = {c.color for c in belief.voting.candidates if c.alive}
    alive_teammates = {c for c in belief.teammate_colors if c in alive_colors}
    return 1 + len(alive_teammates)


def parity_closing_vote_target(
    belief: Belief, chat_accusers: dict[str, int] | None = None
) -> str | None:
    """The non-teammate crewmate to **manufacture** a vote against to reach parity
    this meeting, or ``None``.

    Imposters win at parity (#imposters alive ≥ #crew alive). After the usual ~3 kills
    the board sits at 3 crew / 2 imposters — *one removal short* — and a single crew
    ejection wins the game outright. The deterministic meeting path otherwise **skips**
    when no crewmate is already taking heat, parking the team one step short (the
    dominant crewborg imposter loss; warehouse 2026-06-30). This picks a scapegoat to
    pile onto even with no pre-existing heat, but only at the exact parity-closing
    moment so it never over-extends into the "vote aggression raises ejection" trap.

    Two safety gates make it sound without perfect teammate knowledge:
    - **Known live teammate** (``alive_imposter_count >= 2``): otherwise we can't trust
      the parity arithmetic *or* the teammate exclusion, so we don't fire (no regression
      — falls back to the prior skip — and never risks voting our own teammate).
    - **Exactly one removal from parity** (``alive_crew - alive_imp == 1``): a successful
      vote reaches parity and ends the game, bounding the exposure to this one meeting.

    Target ranking is a **shared, deterministic** function (existing votes, then lowest
    slot) so both imposters converge on the *same* crewmate and their ballots stack into
    a plurality, rather than splitting across two targets.
    """

    candidates = belief.voting.candidates
    if not candidates:
        return None  # vote grid not yet rendered this meeting
    self_color = belief.voting.self_marker_color or belief.self_color
    alive_imp = alive_imposter_count(belief)
    if alive_imp < 2:
        return None  # team unknown / no live teammate → unsafe to push

    # Crew = alive candidates that are neither us nor a known teammate. Counting the
    # pool directly (rather than total − imposters) keeps the arithmetic correct even
    # if the census happens not to list our own marker this frame.
    crew = [
        c
        for c in candidates
        if c.alive and c.color != self_color and c.color not in belief.teammate_colors
    ]
    if not crew:
        return None
    if len(crew) - alive_imp != 1:
        return None  # only at the exact parity-closing moment

    accusers = chat_accusers or {}
    tally = votes_against(belief)

    def rank(candidate) -> tuple[int, int]:
        heat = tally.get(candidate.color, 0) * VOTE_WEIGHT + accusers.get(candidate.color, 0) * CHAT_WEIGHT
        return (heat, -candidate.slot)  # shared deterministic key → both imposters agree

    return max(crew, key=rank).color
