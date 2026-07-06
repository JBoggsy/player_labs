"""Social-evidence counters: chat stances, attributed votes, watched completions.

These feed the fitted suspicion model's public features (strategy/social_evidence.py;
offline mirror: crewrift_lab/suspicion_lab/tools/features.py).
"""

from __future__ import annotations

import pytest

from crewrift.crewborg.perception.entities import VoteCandidate, VoteDot, VotingState
from crewrift.crewborg.strategy.meeting import chat_nlp
from crewrift.crewborg.strategy.social_evidence import (
    SKIP_VOTE_TARGET,
    WATCHED_DWELL_MIN_TICKS,
    update_social_evidence,
)
from crewrift.crewborg.types import Belief, ChatEvent, PlayerEvent, PlayerRecord, VoteCast


@pytest.fixture(autouse=True, scope="module")
def _chat_nlp_model_loaded():
    """Chat-stance counting now goes through chat_evidence.parse_claims, which needs
    a loaded spaCy model (chat_nlp.get_model()). Production code loads it via a
    background thread (chat_nlp.ensure_loading()) so gameplay never blocks on it, but
    tests need it deterministically ready — so load it synchronously here and inject
    it, same approach as test_chat_evidence.py's ``nlp_model`` fixture."""

    try:
        import spacy

        model = spacy.load("en_core_web_sm", disable=["ner"])
    except Exception:
        yield
        return
    saved = chat_nlp._model
    chat_nlp._model = model
    yield
    chat_nlp._model = saved


def _belief(**kwargs) -> Belief:
    kwargs.setdefault("self_role", "crewmate")
    kwargs.setdefault("self_color", "red")
    belief = Belief(**kwargs)
    for color in ("red", "blue", "green", "yellow"):
        belief.roster[color] = PlayerRecord(color=color, life_status="alive")
    return belief


# --- chat stances ---------------------------------------------------------------


def test_an_accusation_counts_for_speaker_and_target() -> None:
    belief = _belief()
    belief.chat_log.append(ChatEvent(tick=100, speaker_color="blue", text="green sus: lurking on a vent"))
    update_social_evidence(belief)
    assert belief.roster["blue"].accusations_made == 1
    assert belief.roster["green"].times_accused == 1


def test_a_defense_counts_for_the_target() -> None:
    belief = _belief()
    belief.chat_log.append(ChatEvent(tick=100, speaker_color="blue", text="green is clear, was with me"))
    update_social_evidence(belief)
    assert belief.roster["green"].times_defended == 1
    assert belief.roster["blue"].accusations_made == 0


def test_chat_lines_count_once_across_ticks_and_meetings() -> None:
    belief = _belief()
    # Only one mention of "green" (not "vote green") — the dependency parse yields one
    # accusation claim per color mention, so repeating the color name would legitimately
    # parse as two separate accusations; this test is about the (tick, speaker, text)
    # dedup, not about how many mentions a single message can carry.
    belief.chat_log.append(ChatEvent(tick=100, speaker_color="blue", text="green sus, vote them"))
    update_social_evidence(belief)
    update_social_evidence(belief)          # same line still in the log
    belief.chat_log.clear()                  # meeting ended
    update_social_evidence(belief)
    assert belief.roster["blue"].accusations_made == 1


def test_unparseable_chat_is_dropped() -> None:
    belief = _belief()
    belief.chat_log.append(ChatEvent(tick=100, speaker_color="blue", text="no read, skipping"))
    belief.chat_log.append(ChatEvent(tick=101, speaker_color="green", text="just resetting imposter cool downs"))
    update_social_evidence(belief)
    assert all(
        r.accusations_made == 0 and r.times_accused == 0 and r.times_defended == 0
        for r in belief.roster.values()
    )


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


# --- vote tallies -----------------------------------------------------------------


def _stage_meeting(belief: Belief, dots: list[VoteDot], start_tick: int = 500) -> None:
    belief.phase = "Voting"
    belief.phase_start_tick = start_tick
    belief.voting = VotingState(
        dots=tuple(dots),
        candidates=(
            VoteCandidate(slot=0, color="red", alive=True),
            VoteCandidate(slot=1, color="blue", alive=True),
            VoteCandidate(slot=2, color="green", alive=True),
            VoteCandidate(slot=3, color="yellow", alive=True),
        ),
    )
    update_social_evidence(belief)  # stages
    belief.phase = "Playing"
    belief.voting = VotingState()   # UI gone
    update_social_evidence(belief)  # commits once


def test_votes_commit_once_with_attribution() -> None:
    belief = _belief()
    _stage_meeting(
        belief,
        dots=[
            VoteDot(voter=0, target=2),                 # me (red) votes green
            VoteDot(voter=1, target=2),                 # blue agrees with me
            VoteDot(voter=2, target=0),                 # green votes ME
            VoteDot(voter=3, target=SKIP_VOTE_TARGET),  # yellow skips
        ],
    )
    update_social_evidence(belief)  # extra ticks must not double-commit
    blue, green, yellow = belief.roster["blue"], belief.roster["green"], belief.roster["yellow"]
    assert blue.votes_cast == 1 and blue.vote_agreed_with_me == 1
    assert green.votes_cast == 1 and green.voted_against_me == 1
    assert yellow.votes_skipped == 1 and yellow.votes_cast == 0
    assert belief.roster["red"].votes_cast == 0  # never count ourselves


def test_two_meetings_accumulate() -> None:
    belief = _belief()
    _stage_meeting(belief, dots=[VoteDot(voter=1, target=2)], start_tick=500)
    _stage_meeting(belief, dots=[VoteDot(voter=1, target=2)], start_tick=900)
    assert belief.roster["blue"].votes_cast == 2


# --- watched completion -------------------------------------------------------------


def _full_dwell(end: int) -> PlayerEvent:
    return PlayerEvent(
        kind="task", start_tick=end - WATCHED_DWELL_MIN_TICKS - 4, end_tick=end, region_index=0
    )


def test_counter_decrement_with_one_full_dwell_credits_the_watcher() -> None:
    belief = _belief(last_tick=1000)
    belief.roster["green"].last_seen_tick = 1000
    belief.roster["green"].events.append(_full_dwell(end=999))
    belief.social_prev_tasks_remaining = 40
    belief.crew_tasks_remaining = 39
    update_social_evidence(belief)
    assert belief.roster["green"].tasks_completed_watched == 1


def test_no_credit_without_a_decrement_fake_task_hold() -> None:
    belief = _belief(last_tick=1000)
    belief.roster["green"].last_seen_tick = 1000
    belief.roster["green"].events.append(_full_dwell(end=999))   # a Pretend-style hold
    belief.social_prev_tasks_remaining = 40
    belief.crew_tasks_remaining = 40                              # counter never moved
    update_social_evidence(belief)
    assert belief.roster["green"].tasks_completed_watched == 0


def test_ambiguous_decrement_credits_no_one() -> None:
    belief = _belief(last_tick=1000)
    for color in ("green", "yellow"):
        belief.roster[color].last_seen_tick = 1000
        belief.roster[color].events.append(_full_dwell(end=999))
    belief.social_prev_tasks_remaining = 40
    belief.crew_tasks_remaining = 39
    update_social_evidence(belief)
    assert belief.roster["green"].tasks_completed_watched == 0
    assert belief.roster["yellow"].tasks_completed_watched == 0


def test_short_dwell_is_not_a_completion() -> None:
    belief = _belief(last_tick=1000)
    belief.roster["green"].last_seen_tick = 1000
    belief.roster["green"].events.append(
        PlayerEvent(kind="task", start_tick=980, end_tick=999, region_index=0)
    )
    belief.social_prev_tasks_remaining = 40
    belief.crew_tasks_remaining = 39   # someone ELSE (unseen) completed
    update_social_evidence(belief)
    assert belief.roster["green"].tasks_completed_watched == 0


# --- meeting caller (MeetingCall interstitial, game 4b9297d) ---------------------


def test_button_caller_banks_once_per_meeting() -> None:
    belief = _belief(last_tick=600)
    belief.meeting_caller_color = "green"
    belief.meeting_call_kind = "button"
    belief.meeting_call_seen_tick = 600
    update_social_evidence(belief)
    update_social_evidence(belief)  # interstitial persists ~3 s; still one credit
    assert belief.roster["green"].button_calls_made == 1

    belief.meeting_call_seen_tick = 1400  # a later, separate meeting
    update_social_evidence(belief)
    assert belief.roster["green"].button_calls_made == 2


def test_body_reporter_banks_reported_bodies() -> None:
    belief = _belief(last_tick=600)
    belief.meeting_caller_color = "blue"
    belief.meeting_call_kind = "body"
    belief.meeting_call_seen_tick = 600
    update_social_evidence(belief)
    assert belief.roster["blue"].reported_bodies == 1
    assert belief.roster["blue"].button_calls_made == 0


def test_caller_banks_through_the_real_belief_fold() -> None:
    # End-to-end through update_belief, the path live games take: the interstitial
    # shows the caller while derive_phase still says "Playing" (no phase text, no
    # voting UI yet). The older tests set the latch fields directly and so never
    # caught the latch being cleared before social evidence ran.
    from crewrift.crewborg.perception.entities import ResolvedScene
    from crewrift.crewborg.types import Percept, update_belief

    belief = _belief(phase="Playing", phase_start_tick=0, last_tick=0)

    def fold(tick: int, **resolved_fields) -> None:
        resolved = ResolvedScene(
            tick=tick, camera_ready=True, camera_x=0, camera_y=0, **resolved_fields
        )
        update_belief(belief, Percept(tick=tick, messages_applied=tick, resolved=resolved))
        update_social_evidence(belief)

    for tick in (600, 601, 602):  # interstitial persists ~3 s
        fold(tick, meeting_caller_color="blue", meeting_call_kind="body", crew_tasks_remaining=5)
    assert belief.roster["blue"].reported_bodies == 1
    assert belief.roster["blue"].button_calls_made == 0


def test_unknown_caller_name_is_ignored() -> None:
    belief = _belief(last_tick=600)
    belief.meeting_caller_color = "someone"   # display fallback, not a roster color
    belief.meeting_call_kind = "button"
    belief.meeting_call_seen_tick = 600
    update_social_evidence(belief)
    assert all(r.button_calls_made == 0 for r in belief.roster.values())


# --- vote-order diffing + speaking order ------------------------------------------


def test_vote_history_records_rank_and_timing_in_cast_order() -> None:
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


def test_flicker_restage_after_commit_does_not_corrupt_next_meetings_vote_order() -> None:
    """The vote UI's dots can flicker back onto screen for one frame during the
    Voting -> VoteResult transition (the old dots still template-matched alongside
    the interstitial text), re-entering the staging branch with phase != "Voting"
    right after a meeting has already committed. This hits the "already committed"
    early-exit guard on the next tick (staged_meeting_tick == banked_meeting_tick) —
    which must clear social_vote_order alongside social_staged_votes, or a leaked
    (voter, target) pair with a stale, pre-flicker tick poisons `already_seen` for
    the next meeting that happens to reuse the same pair: the real vote is silently
    dropped from social_vote_order and the leaked entry is committed instead, under
    the *new* meeting's tick — producing a corrupted (even negative-offset)
    VoteCast.
    """

    belief = Belief(phase="Voting", phase_start_tick=100, last_tick=100)
    belief.roster["red"] = PlayerRecord(color="red")
    belief.roster["blue"] = PlayerRecord(color="blue")
    candidates = (
        VoteCandidate(slot=0, color="red", alive=True),
        VoteCandidate(slot=1, color="blue", alive=True),
    )

    # Meeting 1: red votes for blue at tick 100 (meeting opened at tick 100).
    belief.voting = VotingState(candidates=candidates, dots=(VoteDot(voter=0, target=1),))
    update_social_evidence(belief)  # stage

    belief.phase = "Playing"
    belief.voting = VotingState()
    update_social_evidence(belief)  # commit meeting 1

    assert belief.roster["red"].vote_history == [
        VoteCast(meeting_tick=100, ticks_after_meeting_start=0, target_color="blue", rank=1)
    ]

    # Flicker: one frame after the commit, the SAME (voter, target) pair reappears
    # (phase is "Playing", not "Voting") — this re-enters the staging branch and
    # restages the pair with a fresh, post-commit tick.
    belief.last_tick = 111
    belief.voting = VotingState(candidates=candidates, dots=(VoteDot(voter=0, target=1),))
    update_social_evidence(belief)

    # The flicker's dots vanish the next tick, tripping the "already committed"
    # early-exit guard (staged_meeting_tick still == banked_meeting_tick from
    # meeting 1) — this must clear social_vote_order, not just social_staged_votes.
    belief.last_tick = 112
    belief.voting = VotingState()
    update_social_evidence(belief)

    # Meeting 2: the same (voter, target) pair recurs at a real, much later tick.
    belief.phase = "Voting"
    belief.phase_start_tick = 500
    belief.last_tick = 500
    belief.voting = VotingState(candidates=candidates, dots=(VoteDot(voter=0, target=1),))
    update_social_evidence(belief)  # stage meeting 2

    belief.phase = "Playing"
    belief.voting = VotingState()
    update_social_evidence(belief)  # commit meeting 2

    assert belief.roster["red"].vote_history == [
        VoteCast(meeting_tick=100, ticks_after_meeting_start=0, target_color="blue", rank=1),
        VoteCast(meeting_tick=500, ticks_after_meeting_start=0, target_color="blue", rank=1),
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
