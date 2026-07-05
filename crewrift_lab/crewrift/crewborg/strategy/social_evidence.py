"""Social evidence: cumulative meeting-public + watched-completion counters.

Maintains the per-player counters behind the fitted suspicion model's "public"
features (design: ``crewrift_lab/suspicion_lab/README.md`` §5/§10; offline mirror:
``crewrift_lab/suspicion_lab/tools/features.py`` — keep definitions aligned):

- **Chat stances** — each meeting chat line is parsed via ``chat_evidence.parse_claims``
  (the shared dependency-parse extractor) into claims with
  ``claim_type ∈ {accusation, defense, location, vent, task}``; accusation/defense
  claims bump ``accusations_made`` on the speaker and ``times_accused`` /
  ``times_defended`` on the target, and every claim about a player is retained on
  their ``PlayerRecord.claims``. Unparseable lines are dropped, never guessed at.
- **Vote tallies** — the voting UI's dots attribute every vote (voter slot →
  target slot); at meeting end they are committed once into ``votes_cast`` /
  ``votes_skipped`` / ``voted_against_me`` / ``vote_agreed_with_me``.
- **Watched real-task completion** — the strongest exculpatory cue (imposters
  cannot complete tasks). Detected when the global ``crew_tasks_remaining`` HUD
  counter decrements by exactly one while exactly one visible, living player is
  finishing a near-full task-site dwell. A fake task hold (Pretend) never
  decrements the counter, so it can't trigger this. Stricter than the offline
  truth (completion-while-visible): we must watch most of the dwell — the
  undercount only pulls posteriors toward the prior, never past it.

Counters are cumulative for the whole episode (evidence never resets at meetings)
and live on ``PlayerRecord``; ``suspicion._fitted_features`` reads them.
"""

from __future__ import annotations

from crewrift.crewborg.strategy.meeting import chat_evidence
from crewrift.crewborg.types import Belief

# A real task completion requires TaskCompleteTicks (72) of standing at the site.
# We credit a watched completion only if we observed most of that dwell — slack
# for sampling jitter and the event log's merge grace.
TASK_COMPLETE_TICKS = 72
WATCHED_DWELL_MIN_TICKS = 56
# The dwell interval must still be "live" at the decrement tick (within the event
# log's merge grace) to be the completing dwell.
DWELL_END_GRACE_TICKS = 4

SKIP_VOTE_TARGET = -2  # perception.entities.VoteDot sentinel


def update_social_evidence(belief: Belief) -> None:
    """Fold this tick's public/social observations into the roster counters.

    Runs in the fast loop after ``update_event_log`` (it reads the task-dwell
    intervals that logger maintains) and before ``update_suspicion``.
    """

    _count_chat_stances(belief)
    _track_meeting_votes(belief)
    _bank_meeting_caller(belief)
    _detect_watched_completions(belief)


# --- chat stances -------------------------------------------------------------


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


# --- vote tallies ---------------------------------------------------------------


def _track_meeting_votes(belief: Belief) -> None:
    """Stage the voting UI's dots while the meeting runs; commit once when it ends."""

    voting = belief.voting
    if voting.dots and voting.candidates:
        # Stage (overwrite) — dots are cumulative within a meeting, and the meeting
        # is identified by when its Voting phase opened.
        belief.social_staged_votes = {(d.voter, d.target) for d in voting.dots}
        belief.social_staged_slots = {c.slot: c.color for c in voting.candidates}
        belief.social_staged_meeting_tick = belief.phase_start_tick if belief.phase == "Voting" else (
            belief.social_staged_meeting_tick or belief.phase_start_tick
        )
        return

    # No dots on screen: if a staged meeting is pending and the meeting is over,
    # commit it exactly once.
    if not belief.social_staged_votes or belief.phase == "Voting":
        return
    if belief.social_staged_meeting_tick == belief.social_banked_meeting_tick:
        belief.social_staged_votes = set()
        return

    slots = belief.social_staged_slots
    my_target: int | None = None
    my_slot: int | None = None
    for slot, color in slots.items():
        if color == belief.self_color:
            my_slot = slot
            break
    for voter, target in belief.social_staged_votes:
        if voter == my_slot:
            my_target = target
            break
    for voter, target in belief.social_staged_votes:
        if voter == my_slot:
            continue
        record = belief.roster.get(slots.get(voter, ""))
        if record is None:
            continue
        if target == SKIP_VOTE_TARGET:
            record.votes_skipped += 1
            continue
        record.votes_cast += 1
        if slots.get(target) == belief.self_color:
            record.voted_against_me += 1
        if my_target is not None and my_target != SKIP_VOTE_TARGET and target == my_target:
            record.vote_agreed_with_me += 1

    belief.social_banked_meeting_tick = belief.social_staged_meeting_tick
    belief.social_staged_votes = set()
    belief.social_staged_slots = {}


# --- meeting caller (the MeetingCall interstitial, game 4b9297d) -------------------


def _bank_meeting_caller(belief: Belief) -> None:
    """Credit the meeting caller once per interstitial sighting.

    ``update_belief`` latches (caller, kind, seen_tick) while the interstitial is
    up and clears it when play resumes; the seen-tick is the dedup key. Reporting
    a body and pressing the button are separate (both exculpatory-leaning) cues.
    """

    if belief.meeting_caller_color is None or belief.meeting_call_seen_tick is None:
        return
    if belief.social_caller_banked_tick == belief.meeting_call_seen_tick:
        return
    record = belief.roster.get(belief.meeting_caller_color)
    if record is None:
        return  # "Someone"/unknown display name — not a roster color; ignore
    if belief.meeting_call_kind == "body":
        record.reported_bodies += 1
    elif belief.meeting_call_kind == "button":
        record.button_calls_made += 1
    belief.social_caller_banked_tick = belief.meeting_call_seen_tick


# --- watched real-task completion -------------------------------------------------


def _detect_watched_completions(belief: Belief) -> None:
    remaining = belief.crew_tasks_remaining
    prev = belief.social_prev_tasks_remaining
    belief.social_prev_tasks_remaining = remaining
    if remaining is None or prev is None:
        return
    if remaining != prev - 1:
        return  # no decrement, or an ambiguous multi-completion tick

    tick = belief.last_tick
    candidates = []
    for color, record in belief.roster.items():
        if color == belief.self_color or record.life_status == "dead":
            continue
        if record.last_seen_tick != tick:
            continue  # must be watching them right now
        for event in reversed(record.events):
            if event.kind != "task":
                continue
            if tick - event.end_tick <= DWELL_END_GRACE_TICKS and event.duration_ticks >= WATCHED_DWELL_MIN_TICKS:
                candidates.append(record)
            break  # only the most recent task dwell can be the completing one
    if len(candidates) == 1:
        candidates[0].tasks_completed_watched += 1
