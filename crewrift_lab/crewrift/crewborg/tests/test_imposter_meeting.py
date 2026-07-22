"""Imposter meeting tactics: deflection, bandwagoning, and safe fabrication (§10.4)."""

from __future__ import annotations

from crewrift.crewborg.modes import AttendMeetingMode
from crewrift.crewborg.perception.entities import VoteCandidate, VoteDot, VotingState
from crewrift.crewborg.strategy.meeting.accusation import build_accusation, fabricate_accusation
from crewrift.crewborg.strategy.meeting.imposter import (
    alive_imposter_count,
    bandwagon_target,
    counter_accusation_target,
    heat_on_self,
    parity_closing_vote_target,
    votes_against,
)
from crewrift.crewborg.types import ActionState, Belief, PlayerEvent, PlayerRecord
from players.player_sdk import EventEmitter, ListMetricsSink, ListTraceSink


def _voting(self_color="orange", **kwargs) -> VotingState:
    return VotingState(
        timer_present=True,
        self_marker_color=self_color,
        candidates=(
            VoteCandidate(slot=0, color="red", alive=True),
            VoteCandidate(slot=1, color="blue", alive=True),
            VoteCandidate(slot=2, color="yellow", alive=True),
        ),
        **kwargs,
    )


def _parity_voting(self_color="orange", teammate="green", crew=("red", "blue", "yellow"), **kwargs):
    """A census at the parity-closing board: us + one live teammate + ``crew`` crewmates,
    all alive (default 5 alive = 3 crew / 2 imposters, exactly one removal short)."""

    cells = [VoteCandidate(slot=0, color=self_color, alive=True),
             VoteCandidate(slot=1, color=teammate, alive=True)]
    cells += [VoteCandidate(slot=2 + i, color=c, alive=True) for i, c in enumerate(crew)]
    return VotingState(timer_present=True, self_marker_color=self_color, candidates=tuple(cells), **kwargs)


# --- vote tally read --------------------------------------------------------


def test_votes_against_counts_by_color_excluding_self_and_skip() -> None:
    belief = Belief(self_role="imposter")
    belief.voting = _voting(
        self_color="red",  # red is us (slot 0)
        dots=(
            VoteDot(voter=2, target=1),  # yellow -> blue
            VoteDot(voter=1, target=1),  # blue -> blue
            VoteDot(voter=0, target=1),  # us (red) -> blue: excluded
            VoteDot(voter=2, target=-2),  # yellow skip: excluded
        ),
    )
    assert votes_against(belief) == {"blue": 2}  # our own ballot and the skip don't count


# --- bandwagon target -------------------------------------------------------


def test_bandwagon_picks_the_most_voted_non_teammate() -> None:
    belief = Belief(self_role="imposter")
    belief.voting = _voting(dots=(VoteDot(voter=2, target=1),))  # yellow -> blue
    assert bandwagon_target(belief) == "blue"


def test_bandwagon_never_targets_a_teammate() -> None:
    belief = Belief(self_role="imposter", teammate_colors={"blue"})
    belief.voting = _voting(dots=(VoteDot(voter=2, target=1),))  # yellow -> blue (our teammate)
    assert bandwagon_target(belief) is None


def test_bandwagon_is_none_with_no_heat() -> None:
    belief = Belief(self_role="imposter")
    belief.voting = _voting()  # no dots, no chat
    assert bandwagon_target(belief) is None


def test_chat_accusers_make_a_crewmate_eligible() -> None:
    belief = Belief(self_role="imposter")
    belief.voting = _voting()
    assert bandwagon_target(belief, {"yellow": 2}) == "yellow"  # chat alone is enough


# --- safe fabrication -------------------------------------------------------


def test_fabrication_names_a_real_body_when_one_exists() -> None:
    belief = Belief(self_role="imposter")
    belief.roster["red"] = PlayerRecord(color="red", life_status="dead", death_seen_tick=40)
    line = fabricate_accusation(belief, "blue")
    assert line == "blue sus: next to red's body, lurking on a vent. vote blue"
    assert "kill" not in line  # never a bold, falsifiable witnessed claim


def test_fabrication_falls_back_to_a_tail_claim_without_a_body() -> None:
    belief = Belief(self_role="imposter")
    line = fabricate_accusation(belief, "blue")
    assert line == "blue sus: they were tailing me, lurking on a vent. vote blue"


def test_fabrication_never_names_a_teammate_body() -> None:
    belief = Belief(self_role="imposter", teammate_colors={"red"})
    belief.roster["red"] = PlayerRecord(color="red", life_status="dead", death_seen_tick=40)
    line = fabricate_accusation(belief, "blue")
    assert line == "blue sus: they were tailing me, lurking on a vent. vote blue"  # red (teammate) not cited


def test_fabricated_and_real_accusations_share_the_format() -> None:
    # Identical surface format is the anti-tell — both "<color> sus: a, b".
    real_belief = Belief(self_role="crewmate")
    real_belief.roster["red"] = PlayerRecord(
        color="red", life_status="alive",
        events=[PlayerEvent(kind="vent", start_tick=1, end_tick=20, region_index=0)],
    )
    real = build_accusation(real_belief, "red")
    fake = fabricate_accusation(Belief(self_role="imposter"), "red")
    assert real == "red sus: lurking on a vent. vote red"
    assert fake.startswith("red sus: ") and real.startswith("red sus: ")


# --- imposter meeting flow --------------------------------------------------


def test_imposter_proactively_accuses_a_sus_crewmate_with_real_evidence() -> None:
    mode = AttendMeetingMode()
    belief = Belief(phase="Voting", self_role="imposter", teammate_colors={"green"})
    belief.roster["red"] = PlayerRecord(
        color="red", life_status="alive",
        events=[PlayerEvent(kind="vent", start_tick=1, end_tick=20, region_index=0)],
    )
    belief.suspicion = {"red": 0.85}  # red a clear leading non-teammate suspect

    chat = mode.decide(belief, ActionState())
    assert chat.kind == "chat" and chat.text == "red sus: lurking on a vent. vote red"  # real evidence
    vote = mode.decide(belief, ActionState())
    assert vote.kind == "vote" and vote.target_color == "red"


def test_imposter_bandwagons_with_fabrication_when_it_has_no_real_lead() -> None:
    mode = AttendMeetingMode()
    belief = Belief(phase="Voting", self_role="imposter", teammate_colors={"green"})
    belief.suspicion = {"red": 0.3, "blue": 0.3}  # flat — no real deflection
    belief.voting = _voting(dots=(VoteDot(voter=2, target=1),))  # yellow voted blue
    belief.roster["blue"] = PlayerRecord(color="blue", life_status="alive")

    chat = mode.decide(belief, ActionState())
    assert chat.kind == "chat" and chat.text.startswith("blue sus:")  # fabricated, same format
    vote = mode.decide(belief, ActionState())
    assert vote.kind == "vote" and vote.target_color == "blue"


def test_imposter_stays_quiet_when_only_a_teammate_takes_heat() -> None:
    mode = AttendMeetingMode()
    belief = Belief(phase="Voting", self_role="imposter", teammate_colors={"blue"}, last_tick=0)
    belief.suspicion = {"red": 0.3}
    belief.voting = _voting(dots=(VoteDot(voter=2, target=1),))  # yellow voted blue (teammate)

    assert mode.decide(belief, ActionState()).kind == "idle"  # don't help eject our own


def test_meeting_decision_trace_captures_the_bandwagon_and_its_heat() -> None:
    sink = ListTraceSink()
    mode = AttendMeetingMode()
    mode.emit = EventEmitter(sink, ListMetricsSink())
    belief = Belief(phase="Voting", self_role="imposter", teammate_colors={"green"})
    belief.suspicion = {"red": 0.3, "blue": 0.3}  # no real lead
    belief.voting = _voting(dots=(VoteDot(voter=2, target=1),))  # yellow voted blue
    belief.roster["blue"] = PlayerRecord(color="blue", life_status="alive")

    mode.decide(belief, ActionState())

    [event] = [e for e in sink.events if e.name == "domain.meeting_decision"]
    assert event.data["role"] == "imposter"
    assert event.data["path"] == "bandwagon"
    assert event.data["target"] == "blue"
    assert event.data["fabricated"] is True
    assert event.data["votes"] == {"blue": 1}  # the heat that drove it is recorded
    assert "chat_accusers" in event.data and "nlp" in event.data


def test_imposter_skips_at_the_deadline_when_no_crewmate_takes_heat() -> None:
    mode = AttendMeetingMode()
    belief = Belief(phase="Voting", self_role="imposter", phase_start_tick=0, last_tick=0)
    belief.voting = _voting()

    assert mode.decide(belief, ActionState()).kind == "idle"  # early: wait
    belief.last_tick = 1160  # within the auto-submit window (1200-tick timer)
    vote = mode.decide(belief, ActionState())
    assert vote.kind == "vote" and vote.target_color is None  # skip


# --- parity-closing push (one removal from a win) ---------------------------


def test_alive_imposter_count_is_self_plus_live_known_teammates() -> None:
    belief = Belief(self_role="imposter", teammate_colors={"green"})
    belief.voting = _parity_voting(teammate="green")
    assert alive_imposter_count(belief) == 2  # us + the live teammate
    # An unknown teammate doesn't count, and is the conservative (1) self-gate value.
    assert alive_imposter_count(Belief(self_role="imposter")) == 1


def test_parity_push_manufactures_a_target_when_one_removal_from_parity() -> None:
    # 3 crew / 2 imposters, no heat anywhere: pick the lowest-slot crewmate (the shared
    # deterministic key both imposters compute, so their ballots stack).
    belief = Belief(self_role="imposter", teammate_colors={"green"})
    belief.voting = _parity_voting()  # red(2) blue(3) yellow(4)
    assert parity_closing_vote_target(belief) == "red"


def test_parity_push_prefers_a_crewmate_already_drawing_votes() -> None:
    belief = Belief(self_role="imposter", teammate_colors={"green"})
    belief.voting = _parity_voting(dots=(VoteDot(voter=2, target=3),))  # red -> blue
    assert parity_closing_vote_target(belief) == "blue"  # join the visible pile


def test_parity_push_never_targets_a_teammate_even_when_the_team_draws_heat() -> None:
    belief = Belief(self_role="imposter", teammate_colors={"green"})
    belief.voting = _parity_voting(dots=(VoteDot(voter=2, target=1),))  # red -> green (teammate)
    assert parity_closing_vote_target(belief) == "red"  # teammate excluded; cold pick


def test_parity_push_is_silent_without_a_known_live_teammate() -> None:
    # Team unknown (reveal missed) ⇒ we can't trust the arithmetic or the exclusion,
    # so we never push (no regression, and never risk voting our own teammate).
    belief = Belief(self_role="imposter")  # no teammate_colors
    belief.voting = _parity_voting(teammate="green")
    assert parity_closing_vote_target(belief) is None


def test_parity_push_does_not_fire_two_removals_from_parity() -> None:
    belief = Belief(self_role="imposter", teammate_colors={"green"})
    belief.voting = _parity_voting(crew=("red", "blue", "yellow", "pink"))  # 4 crew / 2 imp
    assert parity_closing_vote_target(belief) is None


def test_imposter_parity_pushes_instead_of_skipping_one_removal_short() -> None:
    mode = AttendMeetingMode()
    belief = Belief(phase="Voting", self_role="imposter", teammate_colors={"green"}, last_tick=0)
    belief.suspicion = {"red": 0.3, "blue": 0.3, "yellow": 0.3}  # flat — no real lead
    belief.voting = _parity_voting()  # 3 crew / 2 imp, no heat → would otherwise skip
    belief.roster["red"] = PlayerRecord(color="red", life_status="alive")

    chat = mode.decide(belief, ActionState())
    assert chat.kind == "chat" and chat.text.startswith("red sus:")  # manufactured pile
    vote = mode.decide(belief, ActionState())
    assert vote.kind == "vote" and vote.target_color == "red"


# --- counter-accuse when accused (design 2026-07-21-imposter-kill-to-win) ---


def test_heat_on_self_counts_votes_on_our_slot_and_chat_accusers() -> None:
    belief = Belief(self_role="imposter")
    belief.voting = _voting(self_color="red", dots=(VoteDot(voter=1, target=0),))  # blue -> us (red)
    assert heat_on_self(belief) == 2  # one vote, VOTE_WEIGHT=2
    assert heat_on_self(belief, {"yellow"}) == 3  # + one chat accuser
    assert heat_on_self(Belief(self_role="imposter")) == 0  # no marker -> no heat known


def test_counter_accusation_targets_the_voter_who_accused_us() -> None:
    belief = Belief(self_role="imposter")
    belief.voting = _voting(self_color="red", dots=(VoteDot(voter=1, target=0),))  # blue -> us
    assert counter_accusation_target(belief) == "blue"


def test_counter_accusation_prefers_a_chat_accuser_already_drawing_votes() -> None:
    belief = Belief(self_role="imposter")
    belief.voting = _voting(
        self_color="red",
        dots=(VoteDot(voter=1, target=2),),  # blue -> yellow: yellow already has a pile
    )
    # Both blue and yellow accused us in chat; yellow is the better deflection (piled).
    assert counter_accusation_target(belief, {"blue", "yellow"}) == "yellow"


def test_counter_accusation_never_targets_a_teammate_or_self() -> None:
    belief = Belief(self_role="imposter", teammate_colors={"blue"})
    belief.voting = _voting(self_color="red", dots=(VoteDot(voter=1, target=0),))  # teammate voted us
    assert counter_accusation_target(belief) is None  # never expose the team
    assert counter_accusation_target(belief, {"red"}) is None  # self never eligible


def test_imposter_counter_accuses_its_accuser_instead_of_idling() -> None:
    # The witnessed-kill scenario: the only heat in the meeting is on US (blue voted
    # for us). Bandwagon/parity see nothing (they exclude self) — the old path idled
    # to a silent skip; now we counter-accuse blue with fabricated-safe evidence.
    mode = AttendMeetingMode()
    belief = Belief(phase="Voting", self_role="imposter", last_tick=0)
    belief.suspicion = {"blue": 0.3, "yellow": 0.3}  # flat — no real lead
    belief.voting = _voting(self_color="red", dots=(VoteDot(voter=1, target=0),))  # blue -> us
    belief.roster["blue"] = PlayerRecord(color="blue", life_status="alive")

    chat = mode.decide(belief, ActionState())
    assert chat.kind == "chat" and chat.text.startswith("blue sus:")  # deflect, never "not me"
    assert "not me" not in chat.text and "innocent" not in chat.text
    vote = mode.decide(belief, ActionState())
    assert vote.kind == "vote" and vote.target_color == "blue"  # coupled: vote whom we accused


def test_imposter_counter_accuse_is_traced_as_its_own_path() -> None:
    sink = ListTraceSink()
    mode = AttendMeetingMode()
    mode.emit = EventEmitter(sink, ListMetricsSink())
    belief = Belief(phase="Voting", self_role="imposter", last_tick=0)
    belief.suspicion = {}
    belief.voting = _voting(self_color="red", dots=(VoteDot(voter=1, target=0),))  # blue -> us
    belief.roster["blue"] = PlayerRecord(color="blue", life_status="alive")

    mode.decide(belief, ActionState())

    [event] = [e for e in sink.events if e.name == "domain.meeting_decision"]
    assert event.data["path"] == "counter_accuse"
    assert event.data["target"] == "blue"
    assert event.data["fabricated"] is True


def test_imposter_still_skips_when_the_only_accuser_is_a_teammate() -> None:
    mode = AttendMeetingMode()
    belief = Belief(phase="Voting", self_role="imposter", teammate_colors={"blue"}, phase_start_tick=0, last_tick=0)
    belief.suspicion = {}
    belief.voting = _voting(self_color="red", dots=(VoteDot(voter=1, target=0),))  # teammate -> us

    assert mode.decide(belief, ActionState()).kind == "idle"  # no safe counter-target
    belief.last_tick = 1160
    vote = mode.decide(belief, ActionState())
    assert vote.kind == "vote" and vote.target_color is None  # deadline skip unchanged


def test_imposter_without_a_known_teammate_still_skips_a_flat_endgame() -> None:
    mode = AttendMeetingMode()
    belief = Belief(phase="Voting", self_role="imposter", phase_start_tick=0, last_tick=0)
    belief.suspicion = {"red": 0.3, "blue": 0.3, "yellow": 0.3}
    belief.voting = _parity_voting(teammate="green")  # green present but not known as ours

    assert mode.decide(belief, ActionState()).kind == "idle"  # no push without a known team
    belief.last_tick = 1160
    vote = mode.decide(belief, ActionState())
    assert vote.kind == "vote" and vote.target_color is None  # falls back to skip
