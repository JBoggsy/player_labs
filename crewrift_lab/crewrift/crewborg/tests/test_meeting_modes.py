"""Attend Meeting / Report Body / Accuse mode tests (design §7.1)."""

from __future__ import annotations

from crewrift.crewborg.action import BTN_A, BTN_DOWN, resolve_action
from crewrift.crewborg.modes import AccuseMode, AttendMeetingMode, ReportBodyMode
from crewrift.crewborg.perception.entities import VoteCandidate, VotingState
from crewrift.crewborg.strategy.meeting import MeetingDecision, MeetingLLMResult
from crewrift.crewborg.strategy.meeting.worker import MeetingLLMOutcome, MeetingLLMRequest
from crewrift.crewborg.types import ActionState, Belief, BodyEntry, ChatEvent, PlayerEvent, PlayerRecord
from players.player_sdk import OverwriteBuffer


class _FakeMeetingClient:
    enabled = True
    disabled_reason = None

    def __init__(self, decisions: list[MeetingDecision], *, timeout_seconds: float | None = None) -> None:
        self.decisions = list(decisions)
        self.timeout_seconds = timeout_seconds
        self.calls: list[tuple[str, dict]] = []

    def decide(self, context: dict, *, trigger: str) -> MeetingLLMResult:
        self.calls.append((trigger, context))
        return MeetingLLMResult(
            decision=self.decisions.pop(0),
            model="fake-haiku",
            latency_ms=1.5,
        )


class _InlineMeetingWorker:
    """Deterministic stand-in for ``MeetingLLMWorker``: runs the call synchronously on
    publish, but the mode still picks the outcome up on a later tick, matching the real
    async flow (submit tick returns idle; a following tick applies the decision)."""

    class _Requests:
        def __init__(self, worker: "_InlineMeetingWorker") -> None:
            self._worker = worker

        def publish(self, request: MeetingLLMRequest) -> None:
            self._worker._execute(request)

    def __init__(self, client: _FakeMeetingClient) -> None:
        self._client = client
        self.requests = _InlineMeetingWorker._Requests(self)
        self.results: OverwriteBuffer[MeetingLLMOutcome] = OverwriteBuffer()

    def start(self) -> None:
        pass

    def close(self) -> None:
        pass

    def _execute(self, request: MeetingLLMRequest) -> None:
        try:
            result = self._client.decide(request.context, trigger=request.trigger)
        except Exception as exc:
            self.results.publish(
                MeetingLLMOutcome(request_id=request.request_id, trigger=request.trigger, error=repr(exc))
            )
            return
        self.results.publish(
            MeetingLLMOutcome(request_id=request.request_id, trigger=request.trigger, result=result)
        )


def _llm_mode(client: _FakeMeetingClient) -> AttendMeetingMode:
    return AttendMeetingMode(llm_client=client, llm_worker_factory=_InlineMeetingWorker)


def _meeting_belief(*, tick: int = 0, start_tick: int = 0) -> Belief:
    belief = Belief(phase="Voting", phase_start_tick=start_tick, last_tick=tick, total_player_count=2)
    belief.voting = VotingState(
        timer_present=True,
        self_marker_color="blue",
        candidates=(
            VoteCandidate(slot=0, color="red", alive=True),
            VoteCandidate(slot=1, color="blue", alive=True),
        ),
        cursor_slot=0,
    )
    belief.roster["red"] = PlayerRecord(color="red", life_status="alive", last_seen_tick=1)
    belief.roster["blue"] = PlayerRecord(color="blue", life_status="alive", last_seen_tick=1)
    belief.suspicion = {"red": 0.95}
    return belief


def test_attend_meeting_accuses_a_clear_suspect_then_votes_them() -> None:
    mode = AttendMeetingMode()
    belief = Belief(phase="Voting")
    belief.roster["red"] = PlayerRecord(
        color="red", life_status="alive", events=[PlayerEvent(kind="vent_use", start_tick=4, end_tick=4)]
    )
    belief.suspicion = {"red": 0.95, "blue": 0.2}  # red a clear leading suspect

    chat = mode.decide(belief, ActionState())
    assert chat.kind == "chat" and chat.text == "red sus: saw them vent"  # accuse, citing evidence

    vote = mode.decide(belief, ActionState())
    assert vote.kind == "vote" and vote.target_color == "red"  # votes whom it accused
    assert mode.decide(belief, ActionState()).kind == "vote"


def test_meeting_never_votes_self_even_if_self_is_top_suspect() -> None:
    # The crew-loss bug: our own colour saturated suspicion and we voted ourself out.
    mode = AttendMeetingMode()
    belief = Belief(phase="Voting", self_role="crewmate", self_color="red")
    belief.voting = VotingState(
        timer_present=True, self_marker_color="red",
        candidates=(VoteCandidate(slot=0, color="red", alive=True), VoteCandidate(slot=1, color="blue", alive=True)),
    )
    belief.suspicion = {"red": 0.99}  # self forced as the only/top suspect

    intent = mode.decide(belief, ActionState())
    assert intent.kind == "vote" and intent.target_color is None  # skip — never red (self)


def test_attend_meeting_stays_silent_and_skips_a_flat_field() -> None:
    mode = AttendMeetingMode()
    belief = Belief(phase="Voting")
    belief.suspicion = {"red": 0.4, "blue": 0.2}  # no clear leader — flat/low field

    intent = mode.decide(belief, ActionState())
    assert intent.kind == "vote" and intent.target_color is None  # silent skip, no chat opener


def test_attend_meeting_stays_idle_after_vote_confirmation() -> None:
    mode = AttendMeetingMode()
    belief = Belief(phase="Voting")  # no suspicion ⇒ silent skip, the vote is the first decision
    belief.voting = VotingState(skip_cursor_present=True)
    action_state = ActionState()

    vote = mode.decide(belief, action_state)
    command = resolve_action(vote, belief, action_state)
    assert command.held_mask == BTN_A and action_state.vote_confirmed

    idle = mode.decide(belief, action_state)
    resolve_action(idle, belief, action_state)  # intent change resets action_state.vote_confirmed
    assert mode.decide(belief, action_state).kind == "idle"


def test_attend_meeting_llm_sends_multiple_chats_after_new_chat_and_cooldown() -> None:
    client = _FakeMeetingClient(
        [
            MeetingDecision(action="send_chat", chat_text="red, where were you?", vote_target="red"),
            MeetingDecision(action="send_chat", chat_text="that route does not clear red"),
        ]
    )
    mode = _llm_mode(client)

    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"  # call in flight
    first = mode.decide(_meeting_belief(tick=0), ActionState())
    assert first.kind == "chat"
    assert first.text == "red, where were you?"

    belief = _meeting_belief(tick=140)  # past the 120-tick call interval and chat cooldown
    belief.chat_log = [ChatEvent(tick=20, speaker_color="red", text="i was nav")]
    assert mode.decide(belief, ActionState()).kind == "idle"  # call in flight
    second = mode.decide(belief, ActionState())
    assert second.kind == "chat"
    assert second.text == "that route does not clear red"
    assert [trigger for trigger, _ in client.calls] == ["meeting_start", "new_chat"]


def test_attend_meeting_llm_tentative_vote_auto_submits_near_deadline() -> None:
    client = _FakeMeetingClient([MeetingDecision(action="set_tentative_vote", vote_target="red")])
    mode = _llm_mode(client)

    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"  # call in flight
    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"  # tentative applied

    vote = mode.decide(_meeting_belief(tick=1153), ActionState())
    assert vote.kind == "vote"
    assert vote.target_color == "red"


def test_attend_meeting_llm_can_submit_vote_early() -> None:
    client = _FakeMeetingClient([MeetingDecision(action="submit_vote", vote_target="red")])
    mode = _llm_mode(client)

    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"  # call in flight
    vote = mode.decide(_meeting_belief(tick=0), ActionState())
    assert vote.kind == "vote"
    assert vote.target_color == "red"


def test_attend_meeting_llm_low_confidence_submit_still_votes() -> None:
    client = _FakeMeetingClient([MeetingDecision(action="submit_vote", vote_target="red", confidence=0.01)])
    mode = _llm_mode(client)

    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"  # call in flight
    vote = mode.decide(_meeting_belief(tick=0), ActionState())

    assert vote.kind == "vote"
    assert vote.target_color == "red"


def test_attend_meeting_llm_self_target_never_votes_self() -> None:
    client = _FakeMeetingClient([MeetingDecision(action="submit_vote", vote_target="blue")])
    mode = _llm_mode(client)
    belief = _meeting_belief(tick=0)
    belief.suspicion = {}

    assert mode.decide(belief, ActionState()).kind == "idle"  # call in flight
    vote = mode.decide(belief, ActionState())

    assert vote.kind == "vote"
    assert vote.target_color is None


def test_attend_meeting_llm_submitted_vote_persists_until_confirmed() -> None:
    client = _FakeMeetingClient([MeetingDecision(action="submit_vote", vote_target="red")])
    mode = _llm_mode(client)
    belief = _meeting_belief(tick=0)
    action_state = ActionState()

    assert mode.decide(belief, action_state).kind == "idle"  # call in flight
    vote = mode.decide(belief, action_state)
    assert vote.kind == "vote" and vote.target_color == "red"
    command = resolve_action(vote, belief, action_state)
    assert command.held_mask == BTN_A and action_state.vote_confirmed

    idle = mode.decide(belief, action_state)
    resolve_action(idle, belief, action_state)
    assert mode.decide(belief, action_state).kind == "idle"
    assert len(client.calls) == 1


def test_attend_meeting_llm_submitted_vote_keeps_driving_cursor_until_confirmed() -> None:
    client = _FakeMeetingClient([MeetingDecision(action="submit_vote", vote_target="blue")])
    mode = _llm_mode(client)
    belief = _meeting_belief(tick=0)
    belief.voting = belief.voting.model_copy(update={"self_marker_color": "green"})
    action_state = ActionState()

    assert mode.decide(belief, action_state).kind == "idle"  # call in flight
    vote = mode.decide(belief, action_state)
    assert vote.kind == "vote" and vote.target_color == "blue"
    command = resolve_action(vote, belief, action_state)
    assert command.held_mask == BTN_DOWN and not action_state.vote_confirmed

    belief.voting = belief.voting.model_copy(update={"cursor_slot": 1})
    vote = mode.decide(belief, action_state)
    assert vote.kind == "vote" and vote.target_color == "blue"
    command = resolve_action(vote, belief, action_state)
    assert command.held_mask == BTN_A and action_state.vote_confirmed
    assert len(client.calls) == 1


def test_attend_meeting_invalid_llm_decision_falls_back_to_the_deterministic_accusation() -> None:
    client = _FakeMeetingClient([MeetingDecision(action="send_chat", chat_text="vote green", vote_target="green")])
    mode = _llm_mode(client)
    belief = _meeting_belief(tick=0)  # suspicion {"red": 0.95} ⇒ red the clear suspect
    belief.roster["red"].events.append(PlayerEvent(kind="vent_use", start_tick=2, end_tick=2))

    assert mode.decide(belief, ActionState()).kind == "idle"  # call in flight
    intent = mode.decide(belief, ActionState())
    assert intent.kind == "chat"
    assert intent.text == "red sus: saw them vent"  # fell back to the deterministic accusation


def test_attend_meeting_deadline_prompt_wins_over_late_chat() -> None:
    client = _FakeMeetingClient([MeetingDecision(action="wait"), MeetingDecision(action="wait")])
    mode = _llm_mode(client)

    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"  # call in flight
    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"  # wait applied
    belief = _meeting_belief(tick=1067)
    belief.chat_log = [ChatEvent(tick=1060, speaker_color="red", text="blue sus")]

    assert mode.decide(belief, ActionState()).kind == "idle"
    assert [trigger for trigger, _ in client.calls] == ["meeting_start", "deadline"]


def test_attend_meeting_late_chat_in_danger_window_does_not_call_llm() -> None:
    client = _FakeMeetingClient(
        [MeetingDecision(action="wait"), MeetingDecision(action="send_chat", chat_text="too late")]
    )
    mode = _llm_mode(client)

    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"  # call in flight
    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"  # wait applied
    belief = _meeting_belief(tick=1068)
    belief.chat_log = [ChatEvent(tick=1060, speaker_color="red", text="blue sus")]

    assert mode.decide(belief, ActionState()).kind == "idle"
    assert [trigger for trigger, _ in client.calls] == ["meeting_start"]


def test_attend_meeting_llm_call_does_not_block_decide_and_applies_late() -> None:
    """The v86 root cause: synchronous meeting calls stalled the loop ~3s each. With the
    real background worker, decide() must return immediately and apply the decision on a
    later tick once the slow call delivers."""

    import time

    class _SlowClient(_FakeMeetingClient):
        def decide(self, context: dict, *, trigger: str) -> MeetingLLMResult:
            time.sleep(0.15)
            return super().decide(context, trigger=trigger)

    client = _SlowClient([MeetingDecision(action="send_chat", chat_text="red vented", vote_target="red")])
    mode = AttendMeetingMode(llm_client=client)  # default factory = real MeetingLLMWorker
    belief = _meeting_belief(tick=0)
    try:
        started = time.perf_counter()
        first = mode.decide(belief, ActionState())
        elapsed = time.perf_counter() - started
        assert first.kind == "idle"
        assert elapsed < 0.1  # never blocked on the 0.15s call

        deadline = time.monotonic() + 2.0
        intent = first
        while intent.kind == "idle" and time.monotonic() < deadline:
            time.sleep(0.01)
            intent = mode.decide(belief, ActionState())
        assert intent.kind == "chat"
        assert intent.text == "red vented"
    finally:
        mode.on_exit(belief, ActionState(), None)


def test_attend_meeting_llm_call_interval_throttles_new_chat() -> None:
    client = _FakeMeetingClient([MeetingDecision(action="wait"), MeetingDecision(action="wait")])
    mode = _llm_mode(client)

    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"  # meeting_start
    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"  # wait applied

    belief = _meeting_belief(tick=60)  # new chat inside the 120-tick call interval
    belief.chat_log = [ChatEvent(tick=30, speaker_color="red", text="hm")]
    assert mode.decide(belief, ActionState()).kind == "idle"
    assert [trigger for trigger, _ in client.calls] == ["meeting_start"]

    belief = _meeting_belief(tick=120)  # interval elapsed
    belief.chat_log = [ChatEvent(tick=30, speaker_color="red", text="hm")]
    assert mode.decide(belief, ActionState()).kind == "idle"
    assert [trigger for trigger, _ in client.calls] == ["meeting_start", "new_chat"]


def test_attend_meeting_llm_call_budget_capped(monkeypatch) -> None:
    monkeypatch.setenv("CREWBORG_LLM_MEETING_CALL_BUDGET", "2")
    client = _FakeMeetingClient([MeetingDecision(action="wait")] * 3)
    mode = _llm_mode(client)

    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"  # call 1
    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"

    belief = _meeting_belief(tick=200)
    belief.chat_log = [ChatEvent(tick=150, speaker_color="red", text="hm")]
    assert mode.decide(belief, ActionState()).kind == "idle"  # call 2 (budget now spent)
    assert mode.decide(belief, ActionState()).kind == "idle"

    belief = _meeting_belief(tick=400)
    belief.chat_log = [
        ChatEvent(tick=150, speaker_color="red", text="hm"),
        ChatEvent(tick=350, speaker_color="red", text="hm2"),
    ]
    assert mode.decide(belief, ActionState()).kind == "idle"  # budget blocks call 3
    assert [trigger for trigger, _ in client.calls] == ["meeting_start", "new_chat"]


def test_attend_meeting_chat_implied_fallback_vote_beats_suspicion_gate_skip(monkeypatch) -> None:
    """v86 confident-chat-then-skip: the LLM accused a color in chat (no vote_target),
    later calls failed, and the fallback collapsed to the 0.9-gate skip. If we said it,
    we vote it."""

    from crewrift.crewborg.strategy.meeting import chat_read

    monkeypatch.setattr(
        chat_read,
        "accused_colors",
        lambda text, colors: {"red"} if "red" in text else set(),
    )
    client = _FakeMeetingClient(
        [MeetingDecision(action="send_chat", chat_text="red is sus, saw them fake a task")]
    )
    mode = _llm_mode(client)
    belief = _meeting_belief(tick=0)
    belief.suspicion = {"red": 0.4}  # under every vote bar -> top_suspect() is None

    assert mode.decide(belief, ActionState()).kind == "idle"
    assert mode.decide(belief, ActionState()).kind == "chat"

    late = _meeting_belief(tick=1153)  # auto-submit window, no more LLM decisions
    late.suspicion = {"red": 0.4}
    vote = mode.decide(late, ActionState())
    assert vote.kind == "vote"
    assert vote.target_color == "red"  # chat-implied vote, not the gate skip


def test_attend_meeting_early_submits_tentative_once_llm_idle_past_half_time() -> None:
    client = _FakeMeetingClient(
        [
            MeetingDecision(action="send_chat", chat_text="red vented", vote_target="red"),
            MeetingDecision(action="wait"),
        ]
    )
    mode = _llm_mode(client)

    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"
    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "chat"  # tentative=red rides along

    assert mode.decide(_meeting_belief(tick=400), ActionState()).kind == "idle"  # >50% left: keep updating
    assert mode.decide(_meeting_belief(tick=400), ActionState()).kind == "idle"

    vote = mode.decide(_meeting_belief(tick=601), ActionState())  # <50% believed time remains
    assert vote.kind == "vote"
    assert vote.target_color == "red"


def test_attend_meeting_early_submits_tentative_when_budget_spent(monkeypatch) -> None:
    monkeypatch.setenv("CREWBORG_LLM_MEETING_CALL_BUDGET", "1")
    client = _FakeMeetingClient([MeetingDecision(action="set_tentative_vote", vote_target="red")])
    mode = _llm_mode(client)

    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"  # the only budgeted call
    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"  # tentative applied

    vote = mode.decide(_meeting_belief(tick=1), ActionState())
    assert vote.kind == "vote"
    assert vote.target_color == "red"  # budget spent -> lock the vote in


def test_attend_meeting_does_not_early_submit_a_tentative_skip(monkeypatch) -> None:
    monkeypatch.setenv("CREWBORG_LLM_MEETING_CALL_BUDGET", "1")
    client = _FakeMeetingClient([MeetingDecision(action="set_tentative_vote", vote_target="skip")])
    mode = _llm_mode(client)

    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"
    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"

    # Submitting skip early gains nothing and forfeits a later real vote: hold it.
    assert mode.decide(_meeting_belief(tick=700), ActionState()).kind == "idle"


def test_attend_meeting_drops_stale_llm_outcome() -> None:
    client = _FakeMeetingClient([MeetingDecision(action="wait")])
    mode = _llm_mode(client)

    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"
    # Overwrite the pending delivery with one from an older request id (e.g. a call
    # that outlived its meeting): it must be dropped, not applied.
    mode._worker.results.publish(
        MeetingLLMOutcome(
            request_id=0,
            trigger="meeting_start",
            result=MeetingLLMResult(
                decision=MeetingDecision(action="submit_vote", vote_target="red"),
                model="fake-haiku",
                latency_ms=1.0,
            ),
        )
    )
    intent = mode.decide(_meeting_belief(tick=1), ActionState())
    assert intent.kind == "idle"  # stale decision not applied; still waiting


def test_report_body_targets_nearest_visible_body() -> None:
    belief = Belief(self_world_x=100, self_world_y=100, visible_body_ids={2001, 2005})
    belief.bodies[2001] = BodyEntry(object_id=2001, color="red", world_x=400, world_y=400, first_seen_tick=1)
    belief.bodies[2005] = BodyEntry(object_id=2005, color="blue", world_x=110, world_y=100, first_seen_tick=1)
    intent = ReportBodyMode().decide(belief, ActionState())
    assert intent.kind == "report" and intent.target_id == 2005  # the nearer body


def test_report_body_idles_with_no_body_in_view() -> None:
    assert ReportBodyMode().decide(Belief(), ActionState()).kind == "idle"


def test_accuse_mode_calls_a_meeting_naming_the_active_tail() -> None:
    belief = Belief(self_world_x=100, self_world_y=100, last_tick=40)
    belief.roster["red"] = PlayerRecord(
        color="red", world_x=120, world_y=100, last_seen_tick=40, life_status="alive",
        events=[PlayerEvent(kind="tailing_self", start_tick=1, end_tick=40, target_color=None)],
    )
    belief.suspicion = {"red": 0.95}  # convictable: the player the meeting would vote out
    intent = AccuseMode().decide(belief, ActionState())
    assert intent.kind == "call_meeting" and intent.target_color == "red"
