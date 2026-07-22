"""Attend Meeting / Report Body / Accuse mode tests (design §7.1)."""

from __future__ import annotations

from crewrift.crewborg.action import BTN_A, BTN_DOWN, resolve_action
from crewrift.crewborg.modes import AccuseMode, AttendMeetingMode, ReportBodyMode
from crewrift.crewborg.perception.entities import VoteCandidate, VoteDot, VotingState
from crewrift.crewborg.strategy.meeting import MeetingDecision, MeetingLLMResult
from crewrift.crewborg.strategy.meeting.context import VOTE_TIMER_TICKS
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
                MeetingLLMOutcome(
                    request_id=request.request_id, trigger=request.trigger, error=repr(exc), latency_ms=1.0
                )
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
    assert chat.kind == "chat" and chat.text == "red sus: saw them vent. vote red"  # accuse, citing evidence

    vote = mode.decide(belief, ActionState())
    assert vote.kind == "vote" and vote.target_color == "red"  # votes whom it accused
    assert mode.decide(belief, ActionState()).kind == "vote"


def test_meeting_never_votes_self_even_if_self_is_top_suspect(monkeypatch) -> None:
    # The crew-loss bug: our own colour saturated suspicion and we voted ourself out.
    monkeypatch.setenv("CREWBORG_HONOR_SOCIETY", "0")  # isolate the vote path from the HS announce
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


def test_attend_meeting_invalid_llm_decision_falls_back_without_double_chat() -> None:
    """With a bar-clearing, evidence-cited suspect the first-mover accusation now goes
    out on tick one (before the LLM call); a later invalid LLM decision falls back to
    the deterministic path, which must NOT chat a second time — it votes the accused."""

    client = _FakeMeetingClient([MeetingDecision(action="send_chat", chat_text="vote green", vote_target="green")])
    mode = _llm_mode(client)
    belief = _meeting_belief(tick=0)  # suspicion {"red": 0.95} ⇒ red the clear suspect
    belief.roster["red"].events.append(PlayerEvent(kind="vent_use", start_tick=2, end_tick=2))

    first = mode.decide(belief, ActionState())
    assert first.kind == "chat"
    assert first.text == "red sus: saw them vent. vote red"  # first-mover accusation
    assert mode.decide(belief, ActionState()).kind == "idle"  # LLM call in flight
    intent = mode.decide(belief, ActionState())  # invalid decision -> deterministic fallback
    assert intent.kind == "vote"
    assert intent.target_color == "red"  # votes whom we accused; no second chat


def test_attend_meeting_deadline_prompt_wins_over_late_chat() -> None:
    client = _FakeMeetingClient([MeetingDecision(action="wait"), MeetingDecision(action="wait")])
    mode = _llm_mode(client)

    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"  # call in flight
    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"  # wait applied
    # Just inside the deadline-prompt window but still a safe start (the boundary is
    # timeout-derived: 1200 - (48 + ceil(timeout*24) + 12 + 1) with the 6.0s default).
    deadline_tick = VOTE_TIMER_TICKS - mode._deadline_prompt_remaining_ticks()
    belief = _meeting_belief(tick=deadline_tick)
    belief.chat_log = [ChatEvent(tick=deadline_tick - 7, speaker_color="red", text="blue sus")]

    assert mode.decide(belief, ActionState()).kind == "idle"
    assert [trigger for trigger, _ in client.calls] == ["meeting_start", "deadline"]


def test_attend_meeting_late_chat_in_danger_window_does_not_call_llm() -> None:
    client = _FakeMeetingClient(
        [MeetingDecision(action="wait"), MeetingDecision(action="send_chat", chat_text="too late")]
    )
    mode = _llm_mode(client)

    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"  # call in flight
    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"  # wait applied
    # One tick past the latest safe start: an answer could no longer beat auto-submit.
    danger_tick = VOTE_TIMER_TICKS - mode._latest_safe_llm_start_remaining_ticks()
    belief = _meeting_belief(tick=danger_tick)
    belief.chat_log = [ChatEvent(tick=danger_tick - 8, speaker_color="red", text="blue sus")]

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


def test_attend_meeting_llm_call_interval_env_tunable(monkeypatch) -> None:
    """CREWBORG_LLM_MIN_CALL_INTERVAL_TICKS overrides the 120-tick default (cadence sweeps)."""
    monkeypatch.setenv("CREWBORG_LLM_MIN_CALL_INTERVAL_TICKS", "300")
    client = _FakeMeetingClient([MeetingDecision(action="wait"), MeetingDecision(action="wait")])
    mode = _llm_mode(client)

    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"  # meeting_start
    assert mode.decide(_meeting_belief(tick=0), ActionState()).kind == "idle"  # wait applied

    belief = _meeting_belief(tick=200)  # past the default 120 but inside the overridden 300
    belief.chat_log = [ChatEvent(tick=150, speaker_color="red", text="hm")]
    assert mode.decide(belief, ActionState()).kind == "idle"
    assert [trigger for trigger, _ in client.calls] == ["meeting_start"]

    belief = _meeting_belief(tick=310)  # overridden interval elapsed
    belief.chat_log = [ChatEvent(tick=150, speaker_color="red", text="hm")]
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


def test_attend_meeting_spend_guard_allows_first_call_but_gates_followups(monkeypatch) -> None:
    """Per-episode Bedrock spend budget: the FIRST (meeting_start) call is always allowed so we
    never go silent, but follow-up calls stop once the remaining budget can't afford another —
    rather than firing into a 429. No configured limit (remaining_usd=None) => no gating."""
    from crewrift.crewborg.strategy.meeting import spend
    from crewrift.crewborg.modes import attend_meeting as am

    client = _FakeMeetingClient([MeetingDecision(action="wait")] * 4)

    def status(remaining):
        return spend.SpendStatus(spend_usd=0.0, spend_limit_usd=1.0, remaining_usd=remaining)

    # 1) budget nearly gone: first call still allowed, follow-up gated.
    monkeypatch.setattr(spend, "read_spend", lambda env=None: status(0.0001))
    mode = _llm_mode(client)
    assert mode._next_llm_trigger(_meeting_belief(tick=0)) == "meeting_start"  # always allowed
    mode._last_llm_call_tick = 0  # simulate the first call having gone out
    b = _meeting_belief(tick=400)
    b.chat_log = [ChatEvent(tick=350, speaker_color="red", text="hm")]  # a new_chat trigger exists
    assert mode._next_llm_trigger(b) is None  # follow-up gated by spend

    # 2) ample budget: the same follow-up trigger fires.
    monkeypatch.setattr(spend, "read_spend", lambda env=None: status(1.0))
    mode2 = _llm_mode(client)
    mode2._last_llm_call_tick = 0
    assert mode2._next_llm_trigger(b) == "new_chat"

    # 3) no configured limit → never gated.
    monkeypatch.setattr(spend, "read_spend", lambda env=None: status(None))
    mode3 = _llm_mode(client)
    mode3._last_llm_call_tick = 0
    assert mode3._next_llm_trigger(b) == "new_chat"


def test_attend_meeting_spend_read_is_cached_across_ticks(monkeypatch) -> None:
    """REGRESSION (2026-07-21 alive-seat vote_timeout dig): the /spend sidecar read is a
    blocking loopback HTTP GET (~20-40ms measured) — issuing it EVERY meeting tick pushed
    the ~42ms tick budget over, queued frames, and lagged the belief clock behind the
    server so the deadline auto-submit fired too late for the tally. The read must be
    cached for SPEND_READ_CACHE_TICKS, not re-issued per tick."""

    from crewrift.crewborg.strategy.meeting import spend
    from crewrift.crewborg.modes.attend_meeting import SPEND_READ_CACHE_TICKS

    calls = 0

    def counting_read(env=None):
        nonlocal calls
        calls += 1
        return spend.SpendStatus(spend_usd=0.0, spend_limit_usd=1.0, remaining_usd=1.0)

    monkeypatch.setattr(spend, "read_spend", counting_read)
    mode = _llm_mode(_FakeMeetingClient([MeetingDecision(action="wait")] * 4))
    mode._last_llm_call_tick = 0  # follow-up territory: the spend guard is consulted

    for tick in range(200, 200 + SPEND_READ_CACHE_TICKS):  # one cache window of ticks
        mode._spend_allows_followup(_meeting_belief(tick=tick))
    assert calls == 1  # cached — NOT one blocking GET per tick

    mode._spend_allows_followup(_meeting_belief(tick=200 + SPEND_READ_CACHE_TICKS))
    assert calls == 2  # refreshed after the cache window


def test_attend_meeting_uncorroborated_chat_implied_fallback_gated_to_skip(monkeypatch) -> None:
    """v88 confidence gate: a bare chat-implied guess (LLM accused a color in chat with
    no vote_target, later calls never landed) is NOT corroboration — on the v87 league
    the fallback-sourced player votes hit imposters 4/24 (17%). Not witnessed, posterior
    under the vote bar, never LLM-named => the auto-submit votes SKIP, never red."""

    from crewrift.crewborg.strategy.meeting import chat_evidence

    monkeypatch.setattr(
        chat_evidence,
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
    assert vote.target_color is None  # gated to skip: uncorroborated chat-implied guess


def test_attend_meeting_witnessed_chat_implied_fallback_still_votes(monkeypatch) -> None:
    """The gate's witnessed arm: same chat-implied fallback, but we caught red venting
    (suspicion.witnessed_imposters) — the fallback vote goes through."""

    from crewrift.crewborg.strategy.meeting import chat_evidence

    monkeypatch.setattr(
        chat_evidence,
        "accused_colors",
        lambda text, colors: {"red"} if "red" in text else set(),
    )
    client = _FakeMeetingClient(
        [MeetingDecision(action="send_chat", chat_text="red is sus, saw them fake a task")]
    )
    mode = _llm_mode(client)
    belief = _meeting_belief(tick=0)
    belief.suspicion = {"red": 0.4}

    assert mode.decide(belief, ActionState()).kind == "idle"
    assert mode.decide(belief, ActionState()).kind == "chat"

    late = _meeting_belief(tick=1153)
    late.suspicion = {"red": 0.4}
    late.roster["red"].events.append(PlayerEvent(kind="vent_use", start_tick=5, end_tick=5))
    vote = mode.decide(late, ActionState())
    assert vote.kind == "vote"
    assert vote.target_color == "red"  # witnessed => corroborated, vote lands


def test_attend_meeting_llm_named_tentative_alone_held_then_gated_to_skip() -> None:
    """v89 tightening: an LLM set_tentative_vote is no longer corroboration. In v88 this
    clause fed 10 wrong vs 3 right crew votes (and 4 crew mis-ejections) — so a target
    the LLM only *tentatively* named, with the posterior under every vote bar and
    nothing witnessed, is held at the early-submit window and gated to SKIP by the
    deadline auto-submit (the vote still submits: timeouts stay 0)."""

    client = _FakeMeetingClient([MeetingDecision(action="set_tentative_vote", vote_target="red")])
    mode = _llm_mode(client)
    belief = _meeting_belief(tick=0)
    belief.suspicion = {"red": 0.4}  # top_suspect() None, nothing witnessed

    assert mode.decide(belief, ActionState()).kind == "idle"  # call in flight
    assert mode.decide(belief, ActionState()).kind == "idle"  # tentative applied

    mid = _meeting_belief(tick=700)  # <50% believed time remains, LLM idle
    mid.suspicion = {"red": 0.4}
    assert mode.decide(mid, ActionState()).kind == "idle"  # held, not early-submitted

    late = _meeting_belief(tick=1153)  # auto-submit window
    late.suspicion = {"red": 0.4}
    vote = mode.decide(late, ActionState())
    assert vote.kind == "vote"
    assert vote.target_color is None  # LLM-named tentative alone: gated to skip


def test_attend_meeting_chat_riding_vote_target_gated_to_skip_at_low_posterior() -> None:
    """v89: the prompt rides a vote_target on ~every chat, which made the v88 gate a
    no-op (0/35 eps fired). A vote_target that only rode along on a send_chat is not
    corroboration — under the vote bar and unwitnessed, the auto-submit votes SKIP."""

    client = _FakeMeetingClient(
        [MeetingDecision(action="send_chat", chat_text="feels like red maybe", vote_target="red")]
    )
    mode = _llm_mode(client)
    belief = _meeting_belief(tick=0)
    belief.suspicion = {"red": 0.4}

    assert mode.decide(belief, ActionState()).kind == "idle"  # call in flight
    assert mode.decide(belief, ActionState()).kind == "chat"  # chat sent, tentative=red rides

    late = _meeting_belief(tick=1153)  # auto-submit window
    late.suspicion = {"red": 0.4}
    vote = mode.decide(late, ActionState())
    assert vote.kind == "vote"
    assert vote.target_color is None  # chat-riding target alone: gated to skip


def test_attend_meeting_llm_submit_vote_named_target_passes_gate_at_low_posterior() -> None:
    """The one LLM-sourced corroboration that survives v89: an explicit submit_vote
    naming the target. Pooled v87+v88, LLM-submitted votes hit imposters 28/37 (76%)
    — that arm votes even with the posterior under every bar and nothing witnessed."""

    client = _FakeMeetingClient([MeetingDecision(action="submit_vote", vote_target="red")])
    mode = _llm_mode(client)
    belief = _meeting_belief(tick=0)
    belief.suspicion = {"red": 0.4}  # top_suspect() None, nothing witnessed

    assert mode.decide(belief, ActionState()).kind == "idle"  # call in flight
    vote = mode.decide(belief, ActionState())
    assert vote.kind == "vote"
    assert vote.target_color == "red"  # LLM's own submit_vote: corroborated


def test_attend_meeting_llm_submit_with_backfilled_target_gated_to_skip() -> None:
    """A submit_vote WITHOUT a target gets the fallback backfilled by validation —
    that backfill is not an LLM-named target and must not pass the gate."""

    client = _FakeMeetingClient(
        [MeetingDecision(action="submit_vote")]  # no vote_target: backfilled fallback
    )
    mode = _llm_mode(client)
    belief = _meeting_belief(tick=0)
    belief.suspicion = {"red": 0.4}  # fallback resolves under every vote bar

    assert mode.decide(belief, ActionState()).kind == "idle"  # call in flight
    vote = mode.decide(belief, ActionState())  # LLM submit with backfilled target
    assert vote.kind == "vote"
    assert vote.target_color is None  # backfill is not corroboration: skip


def test_attend_meeting_uncorroborated_tentative_held_then_gated_at_deadline() -> None:
    """An uncorroborated fallback tentative (e.g. the posterior drifted back under the
    bar after a deterministic accusation) would be gated to a skip; early-submitting a
    skip forfeits a later real vote, so hold it — the deadline auto-submit still fires
    (vote timeouts stay 0) and gates it to skip there."""

    client = _FakeMeetingClient([MeetingDecision(action="wait")])
    mode = _llm_mode(client)
    belief = _meeting_belief(tick=0)
    belief.suspicion = {"red": 0.4}

    assert mode.decide(belief, ActionState()).kind == "idle"  # call in flight
    assert mode.decide(belief, ActionState()).kind == "idle"  # wait applied
    mode._tentative_vote = "red"  # uncorroborated fallback tentative (posterior drift)

    mid = _meeting_belief(tick=700)  # <50% believed time remains, LLM idle
    mid.suspicion = {"red": 0.4}
    assert mode.decide(mid, ActionState()).kind == "idle"  # held, not early-submitted

    late = _meeting_belief(tick=1153)  # auto-submit window
    late.suspicion = {"red": 0.4}
    vote = mode.decide(late, ActionState())
    assert vote.kind == "vote"
    assert vote.target_color is None  # gated to skip at the deadline


def test_attend_meeting_dead_seat_mutes_llm_and_chat_then_skips_at_deadline() -> None:
    """v88 dead-seat mute: dead inputs are skipped by the sim but dead seats burned ~23%
    of meeting-LLM call volume, so we mute the expensive parts (no LLM requests, no chats).
    v105 fix: still cast ONE terminal SKIP at the deadline — the mute keys off
    belief.self_alive, which can be wrongly False (self_color mis-latch → census flips it
    off while we're alive), and a muted-but-alive seat that never votes draws the game's
    '-10 for failing to vote' penalty. A skip is inert if truly dead, saves the penalty if not."""

    client = _FakeMeetingClient([MeetingDecision(action="submit_vote", vote_target="red")])
    mode = _llm_mode(client)

    for tick in (0, 200, 700, 1100):  # start .. mid-meeting — all before the auto-submit window
        belief = _meeting_belief(tick=tick)
        belief.self_alive = False
        assert mode.decide(belief, ActionState()).kind == "idle"

    deadline = _meeting_belief(tick=1160)  # inside the auto-submit window (<=96 ticks left of 1200)
    deadline.self_alive = False
    intent = mode.decide(deadline, ActionState())
    assert intent.kind == "vote" and intent.target_color is None  # a bare SKIP, never a player
    assert client.calls == []  # still zero LLM submissions


def test_attend_meeting_wrongly_dead_seat_still_skips_and_does_not_time_out() -> None:
    """REGRESSION (v105 vote_timeout 0%→~10%, v100 had none): belief.self_alive can be
    WRONGLY False — the v105 one-shot self_color latch stuck a neighbour's colour, so the
    meeting census flipped self_alive off when THAT colour died while our seat was still
    alive and owed a vote. The old dead-mute idled the whole meeting → the game charged
    '-10 for failing to vote or skip'. The seat must reach the deadline and submit a skip
    so no vote_timeout penalty lands, even when it (wrongly) believes it is dead."""

    mode = _llm_mode(_FakeMeetingClient([]))
    # Whole meeting believed-dead, driven tick by tick as the real loop does.
    for tick in (0, 300, 700, 1100):
        b = _meeting_belief(tick=tick)
        b.self_alive = False
        assert mode.decide(b, ActionState()).kind == "idle"  # muted, holding for the deadline

    late = _meeting_belief(tick=1180)  # auto-submit window (<= AUTO_SUBMIT_REMAINING_TICKS left)
    late.self_alive = False
    intent = mode.decide(late, ActionState())
    assert intent.kind == "vote" and intent.target_color is None  # skip lands → no timeout


def test_attend_meeting_kill_to_meeting_death_lag_stays_muted() -> None:
    """The v88 mute leak (ep 422637ce: killed t=1070, meeting t=1142, 4 LLM calls): the
    ghost icon never rendered between the kill and the vote screen, so belief.self_alive
    lagged our own death across the kill→meeting transition. v89: the meeting census
    (our own dead candidate cell) flips self_alive in update_belief — which runs before
    mode.decide — so the dead-seat mute catches the very first meeting tick."""

    from crewrift.crewborg.perception.entities import CensusEntry, ResolvedScene
    from crewrift.crewborg.types import Percept, update_belief

    client = _FakeMeetingClient([MeetingDecision(action="submit_vote", vote_target="red")])
    mode = _llm_mode(client)

    belief = Belief(phase="Playing", last_tick=1070, self_role="crewmate", self_color="blue")
    assert belief.self_alive  # ghost icon never seen: still believed alive at the meeting

    # The meeting opens at t=1142; the vote-screen census shows our own cell dead.
    resolved = ResolvedScene(
        tick=1142, camera_ready=False, camera_x=0, camera_y=0,
        voting=VotingState(
            timer_present=True,
            self_marker_color="blue",
            candidates=(
                VoteCandidate(slot=0, color="red", alive=True),
                VoteCandidate(slot=1, color="blue", alive=False),
            ),
        ),
        census=(CensusEntry(color="red", alive=True), CensusEntry(color="blue", alive=False)),
    )
    update_belief(belief, Percept(tick=1142, messages_applied=1142, resolved=resolved))
    assert belief.phase == "Voting"
    assert belief.self_alive is False  # census caught the lagged death

    for _ in range(3):
        assert mode.decide(belief, ActionState()).kind == "idle"
    assert client.calls == []  # zero dead-seat LLM calls, including the lag case


def test_attend_meeting_dead_mute_does_not_touch_deterministic_path() -> None:
    """LLM off: the deterministic (fallback) meeting behavior is byte-identical even
    when dead — the mute lives on the LLM-enabled path only."""

    mode = AttendMeetingMode()
    belief = Belief(phase="Voting")
    belief.self_alive = False
    belief.roster["red"] = PlayerRecord(
        color="red", life_status="alive", events=[PlayerEvent(kind="vent_use", start_tick=4, end_tick=4)]
    )
    belief.suspicion = {"red": 0.95, "blue": 0.2}

    chat = mode.decide(belief, ActionState())
    assert chat.kind == "chat" and chat.text == "red sus: saw them vent. vote red"
    vote = mode.decide(belief, ActionState())
    assert vote.kind == "vote" and vote.target_color == "red"


def test_attend_meeting_imposter_fallback_votes_exempt_from_gate() -> None:
    """The gate is crew-only: an imposter's fallback deflection votes mis-eject crew on
    purpose (and suspicion is empty for imposters). An LLM-failure fallback onto the
    deterministic imposter path must still land its bandwagon vote."""

    class _FailingClient(_FakeMeetingClient):
        def decide(self, context: dict, *, trigger: str) -> MeetingLLMResult:
            self.calls.append((trigger, context))
            raise RuntimeError("bedrock 429")

    client = _FailingClient([])
    mode = _llm_mode(client)
    belief = _meeting_belief(tick=0)
    belief.self_role = "imposter"
    belief.suspicion = {}
    # red is taking heat: green's cast vote against red drives the bandwagon.
    belief.voting = belief.voting.model_copy(
        update={
            "candidates": (
                VoteCandidate(slot=0, color="red", alive=True),
                VoteCandidate(slot=1, color="blue", alive=True),
                VoteCandidate(slot=2, color="green", alive=True),
            ),
            "dots": (VoteDot(voter=2, target=0),),  # green -> red
        }
    )

    assert mode.decide(belief, ActionState()).kind == "idle"  # call in flight
    intent = mode.decide(belief, ActionState())  # failure -> deterministic imposter
    # bandwagon: chat (fabricated) or a direct vote for red — never a gated skip.
    if intent.kind == "chat":
        late = belief.model_copy(update={"last_tick": 601})  # early-submit window
        intent = mode.decide(late, ActionState())
    assert intent.kind == "vote"
    assert intent.target_color == "red"


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


# --- instant suss-vote (CREWBORG_LLM_SUSS_INSTANT_VOTE) ---------------------------


def _drive_until(mode, belief, kinds, n=6):
    seen = []
    for _ in range(n):
        intent = mode.decide(belief, ActionState())
        seen.append(intent)
        if intent.kind in kinds:
            return intent, seen
    return None, seen


def test_instant_vote_fires_on_llm_tentative(monkeypatch) -> None:
    monkeypatch.setenv("CREWBORG_LLM_SUSS_INSTANT_VOTE", "1")
    client = _FakeMeetingClient([MeetingDecision(action="set_tentative_vote", vote_target="red", reason="sus")])
    mode = _llm_mode(client)
    belief = _meeting_belief(tick=10)
    belief.self_role = "crewmate"
    belief.self_alive = True
    vote, seen = _drive_until(mode, belief, {"vote"})
    assert vote is not None and vote.target_color == "red"  # named -> voted, no deadline hold


def test_instant_vote_fires_after_llm_chat_accusation(monkeypatch) -> None:
    monkeypatch.setenv("CREWBORG_LLM_SUSS_INSTANT_VOTE", "1")
    monkeypatch.setenv("CREWBORG_HONOR_SOCIETY", "0")  # the HS announce would take the first chat slot
    client = _FakeMeetingClient(
        [MeetingDecision(action="send_chat", chat_text="red sus: saw them vent", reason="accuse")]
    )
    mode = _llm_mode(client)
    belief = _meeting_belief(tick=10)
    belief.self_role = "crewmate"
    belief.self_alive = True
    chat, _ = _drive_until(mode, belief, {"chat"})
    assert chat is not None and "red" in chat.text  # the accusation goes out first
    vote, _ = _drive_until(mode, belief, {"vote"})
    assert vote is not None and vote.target_color == "red"


def test_instant_vote_off_by_default(monkeypatch) -> None:
    monkeypatch.delenv("CREWBORG_LLM_SUSS_INSTANT_VOTE", raising=False)
    client = _FakeMeetingClient([MeetingDecision(action="set_tentative_vote", vote_target="red", reason="sus")])
    mode = _llm_mode(client)
    belief = _meeting_belief(tick=10)
    belief.self_role = "crewmate"
    belief.self_alive = True
    vote, seen = _drive_until(mode, belief, {"vote"}, n=4)
    assert vote is None  # tentative held for early-submit/deadline gates, unchanged


def test_instant_vote_never_arms_for_imposter(monkeypatch) -> None:
    monkeypatch.setenv("CREWBORG_LLM_SUSS_INSTANT_VOTE", "1")
    client = _FakeMeetingClient([MeetingDecision(action="set_tentative_vote", vote_target="red", reason="deflect")])
    mode = _llm_mode(client)
    belief = _meeting_belief(tick=10)
    belief.self_role = "imposter"
    belief.self_alive = True
    vote, _ = _drive_until(mode, belief, {"vote"}, n=4)
    assert vote is None  # imposter deflection timing unchanged


def test_instant_vote_respects_society_trust_veto(monkeypatch) -> None:
    import base64
    from crewrift.crewborg.strategy import honor_society
    monkeypatch.setenv("CREWBORG_LLM_SUSS_INSTANT_VOTE", "1")
    monkeypatch.setenv(honor_society.ENV_FLAG, "1")
    monkeypatch.setenv(honor_society.ENV_SEED, base64.b64encode(b"\x07" * 32).decode())
    honor_society.reset_identity_for_tests()
    try:
        client = _FakeMeetingClient([MeetingDecision(action="set_tentative_vote", vote_target="red", reason="sus")])
        mode = _llm_mode(client)
        belief = _meeting_belief(tick=10)
        belief.self_role = "crewmate"
        belief.self_alive = True
        belief.society_announced = True
        belief.society_trusted.add("red")  # trusted member, not witnessed
        vote, _ = _drive_until(mode, belief, {"vote"})
        assert vote is not None and vote.target_color is None  # veto converts to skip
    finally:
        honor_society.reset_identity_for_tests()


# --- first-mover anchoring accusation (design: 2026-07-21-first-mover-anchor) ---


def _anchor_belief(*, tick: int = 0) -> Belief:
    """Crew seat with a bar-clearing, evidence-cited suspect at meeting start."""

    belief = _meeting_belief(tick=tick)
    belief.self_role = "crewmate"
    belief.self_alive = True
    belief.roster["red"].events.append(PlayerEvent(kind="vent_use", start_tick=4, end_tick=4))
    return belief


def test_first_mover_accusation_fires_before_the_llm_call(monkeypatch) -> None:
    monkeypatch.setenv("CREWBORG_HONOR_SOCIETY", "0")  # isolate from the HS announce chat
    client = _FakeMeetingClient([MeetingDecision(action="wait")])
    mode = _llm_mode(client)

    first = mode.decide(_anchor_belief(), ActionState())
    assert first.kind == "chat"
    assert first.text == "red sus: saw them vent. vote red"
    assert client.calls == []  # the chat went out before any LLM round-trip

    # The meeting_start LLM call still happens afterwards, exactly once.
    assert mode.decide(_anchor_belief(), ActionState()).kind == "idle"
    assert [trigger for trigger, _ in client.calls] == ["meeting_start"]


def test_first_mover_accusation_fires_once_and_votes_the_accused(monkeypatch) -> None:
    monkeypatch.setenv("CREWBORG_HONOR_SOCIETY", "0")  # isolate from the HS announce chat
    client = _FakeMeetingClient([MeetingDecision(action="wait")])
    mode = _llm_mode(client)

    assert mode.decide(_anchor_belief(), ActionState()).kind == "chat"
    assert mode.decide(_anchor_belief(), ActionState()).kind == "idle"  # call in flight
    assert mode.decide(_anchor_belief(), ActionState()).kind == "idle"  # wait applied

    vote = mode.decide(_anchor_belief(tick=700), ActionState())  # early-submit window
    assert vote.kind == "vote"
    assert vote.target_color == "red"  # coupled: vote exactly whom we accused


def test_first_mover_suppresses_duplicate_llm_chat() -> None:
    client = _FakeMeetingClient(
        [MeetingDecision(action="send_chat", chat_text="red sus: saw them vent. vote red")]
    )
    mode = _llm_mode(client)

    assert mode.decide(_anchor_belief(), ActionState()).kind == "chat"
    assert mode.decide(_anchor_belief(), ActionState()).kind == "idle"  # call in flight
    intent = mode.decide(_anchor_belief(), ActionState())  # LLM echoes the same accusation
    assert intent.kind == "idle"  # duplicate suppressed by _sent_chat_texts


def test_first_mover_needs_a_bar_clearing_suspect(monkeypatch) -> None:
    monkeypatch.setenv("CREWBORG_HONOR_SOCIETY", "0")  # isolate from the HS announce chat
    client = _FakeMeetingClient([MeetingDecision(action="wait")])
    mode = _llm_mode(client)
    belief = _anchor_belief()
    belief.suspicion = {"red": 0.4}  # under the vote bar -> top_suspect() None

    assert mode.decide(belief, ActionState()).kind == "idle"  # no anchor; LLM call instead
    assert [trigger for trigger, _ in client.calls] == ["meeting_start"]


def test_first_mover_needs_citable_evidence(monkeypatch) -> None:
    monkeypatch.setenv("CREWBORG_HONOR_SOCIETY", "0")  # isolate from the HS announce chat
    client = _FakeMeetingClient([MeetingDecision(action="wait")])
    mode = _llm_mode(client)
    belief = _meeting_belief()  # bar-clearing suspect but an empty event log
    belief.self_role = "crewmate"

    assert mode.decide(belief, ActionState()).kind == "idle"  # never bare-accuse
    assert [trigger for trigger, _ in client.calls] == ["meeting_start"]


def test_first_mover_never_fires_for_imposter_or_dead_seat() -> None:
    for role, alive in (("imposter", True), ("crewmate", False)):
        client = _FakeMeetingClient([MeetingDecision(action="wait")])
        mode = _llm_mode(client)
        belief = _anchor_belief()
        belief.self_role = role
        belief.self_alive = alive

        intent = mode.decide(belief, ActionState())
        assert intent.kind == "idle", (role, alive)


def test_first_mover_respects_society_trust_veto(monkeypatch) -> None:
    import base64
    from crewrift.crewborg.strategy import honor_society

    monkeypatch.setenv(honor_society.ENV_FLAG, "1")
    monkeypatch.setenv(honor_society.ENV_SEED, base64.b64encode(b"\x07" * 32).decode())
    honor_society.reset_identity_for_tests()
    try:
        client = _FakeMeetingClient([MeetingDecision(action="wait")])
        mode = _llm_mode(client)
        belief = _meeting_belief()
        belief.self_role = "crewmate"
        # Citable but UNWITNESSED evidence (a long tail) — witnessed kill/vent
        # evidence would correctly override society trust inside vote_veto.
        belief.roster["red"].events.append(
            PlayerEvent(kind="tailing_self", start_tick=1, end_tick=40, target_color=None)
        )
        belief.society_announced = True
        belief.society_trusted.add("red")  # trusted member, not witnessed

        intent = mode.decide(belief, ActionState())
        assert intent.kind == "idle"  # no anchor against a trusted member
    finally:
        honor_society.reset_identity_for_tests()


def test_attend_meeting_emits_llm_spend_on_success() -> None:
    """W4 spend telemetry: every delivered meeting call emits one domain.llm_spend event
    with tokens, estimated USD, and meeting/role attribution."""
    from players.player_sdk import EventEmitter, ListMetricsSink, ListTraceSink
    from crewrift.crewborg.strategy import llm_spend

    llm_spend.EPISODE_LEDGER.reset()

    class _UsageClient(_FakeMeetingClient):
        def decide(self, context: dict, *, trigger: str) -> MeetingLLMResult:
            self.calls.append((trigger, context))
            return MeetingLLMResult(
                decision=self.decisions.pop(0),
                model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
                latency_ms=2500.0,
                usage={"input_tokens": 2000, "output_tokens": 100},
            )

    sink = ListTraceSink()
    mode = _llm_mode(_UsageClient([MeetingDecision(action="wait")]))
    mode.emit = EventEmitter(sink, ListMetricsSink())

    mode.decide(_meeting_belief(tick=0), ActionState())  # submit
    mode.decide(_meeting_belief(tick=1), ActionState())  # collect

    [event] = [e for e in sink.events if e.name == "domain.llm_spend"]
    assert event.data["surface"] == "meeting"
    assert event.data["ok"] is True
    assert event.data["trigger"] == "meeting_start"
    assert event.data["input_tokens"] == 2000 and event.data["output_tokens"] == 100
    assert abs(event.data["est_cost_usd"] - 0.0025) < 1e-9
    assert event.data["meeting_index"] == 0
    assert event.data["calls_used"] == 1


def test_llm_spend_meeting_index_survives_mode_recreation() -> None:
    """REGRESSION (spendtrace probe): AttendMeetingMode is recreated per meeting, so an
    instance-level meeting counter read 0 forever. The ordinal lives on the process
    ledger, keyed by meeting id (phase_start_tick)."""
    from players.player_sdk import EventEmitter, ListMetricsSink, ListTraceSink
    from crewrift.crewborg.strategy import llm_spend

    llm_spend.EPISODE_LEDGER.reset()

    def run_meeting(start_tick: int) -> int:
        client = _FakeMeetingClient([MeetingDecision(action="wait")])
        sink = ListTraceSink()
        mode = _llm_mode(client)  # a FRESH mode instance, as the runtime creates per meeting
        mode.emit = EventEmitter(sink, ListMetricsSink())
        mode.decide(_meeting_belief(tick=start_tick, start_tick=start_tick), ActionState())
        mode.decide(_meeting_belief(tick=start_tick + 1, start_tick=start_tick), ActionState())
        [event] = [e for e in sink.events if e.name == "domain.llm_spend"]
        return event.data["meeting_index"]

    assert run_meeting(100) == 0
    assert run_meeting(3000) == 1  # a later meeting, a new mode instance
    assert run_meeting(3000) == 1  # same meeting id → same ordinal


def test_attend_meeting_emits_llm_spend_on_failure_with_free_429() -> None:
    """A 429-failed call still emits llm_spend — attributed, but at $0 (measured: the
    sidecar rejects throttled calls pre-inference)."""
    from players.player_sdk import EventEmitter, ListMetricsSink, ListTraceSink
    from crewrift.crewborg.strategy import llm_spend

    llm_spend.EPISODE_LEDGER.reset()

    class _ThrottledClient(_FakeMeetingClient):
        def decide(self, context: dict, *, trigger: str) -> MeetingLLMResult:
            raise RuntimeError("RateLimitError: Error code: 429 - Too many tokens per day")

    sink = ListTraceSink()
    mode = _llm_mode(_ThrottledClient([]))
    mode.emit = EventEmitter(sink, ListMetricsSink())

    mode.decide(_meeting_belief(tick=0), ActionState())  # submit
    mode.decide(_meeting_belief(tick=1), ActionState())  # collect the failure

    [event] = [e for e in sink.events if e.name == "domain.llm_spend"]
    assert event.data["ok"] is False
    assert event.data["error_class"] == "throttle_429"
    assert event.data["est_cost_usd"] == 0.0
    assert event.data["latency_ms"] is not None  # the worker timed the failed attempt
    # The failure fallback path also still fires.
    assert any(
        e.name == "domain.meeting_llm_fallback" and e.data.get("reason") == "llm_call_failed" for e in sink.events
    )


# --- warm first-mover anchor (design: 2026-07-22-warm-anchor) -------------------


def _warm_belief(*, tick: int = 0) -> Belief:
    """Crew seat with a warm-eligible (below-bar, social-rule-passing) top suspect."""

    belief = _meeting_belief(tick=tick)
    belief.self_role = "crewmate"
    belief.self_alive = True
    belief.suspicion = {"red": 0.5}  # below the hard bar -> top_suspect() None
    red = belief.roster["red"]
    red.events.append(PlayerEvent(kind="tailing_self", start_tick=0, end_tick=96))
    red.times_accused = 1
    red.votes_cast = 1
    return belief


def test_warm_anchor_fires_below_the_hard_bar(monkeypatch) -> None:
    monkeypatch.setenv("CREWBORG_HONOR_SOCIETY", "0")
    client = _FakeMeetingClient([MeetingDecision(action="wait")])
    mode = _llm_mode(client)

    first = mode.decide(_warm_belief(), ActionState())
    assert first.kind == "chat"
    assert first.text.startswith("red sus:")
    assert client.calls == []  # out before the LLM round-trip, like the hard anchor


def test_warm_anchor_vote_skips_without_a_pile(monkeypatch) -> None:
    monkeypatch.setenv("CREWBORG_HONOR_SOCIETY", "0")
    client = _FakeMeetingClient([MeetingDecision(action="wait")])
    mode = _llm_mode(client)

    assert mode.decide(_warm_belief(), ActionState()).kind == "chat"
    assert mode.decide(_warm_belief(), ActionState()).kind == "idle"  # call in flight
    assert mode.decide(_warm_belief(), ActionState()).kind == "idle"  # wait applied

    vote = mode.decide(_warm_belief(tick=1150), ActionState())  # deadline auto-submit
    assert vote.kind == "vote"
    assert vote.target_color is None  # lone warm ballot converted to skip


def test_warm_anchor_vote_fires_when_the_pile_forms(monkeypatch) -> None:
    monkeypatch.setenv("CREWBORG_HONOR_SOCIETY", "0")
    client = _FakeMeetingClient([MeetingDecision(action="wait")])
    mode = _llm_mode(client)

    assert mode.decide(_warm_belief(), ActionState()).kind == "chat"
    assert mode.decide(_warm_belief(), ActionState()).kind == "idle"
    assert mode.decide(_warm_belief(), ActionState()).kind == "idle"

    piled = _warm_belief(tick=1150)  # deadline window; another player voted red
    piled.voting = piled.voting.model_copy(update={"dots": (VoteDot(voter=0, target=0),)})
    vote = mode.decide(piled, ActionState())
    assert vote.kind == "vote"
    assert vote.target_color == "red"  # pile formed -> the coupled ballot is cast


def test_warm_anchor_needs_the_social_rule(monkeypatch) -> None:
    monkeypatch.setenv("CREWBORG_HONOR_SOCIETY", "0")
    for breaker in (
        lambda r: setattr(r, "times_accused", 0),
        lambda r: setattr(r, "votes_cast", 0),
        lambda r: setattr(r, "button_calls_made", 1),
        lambda r: setattr(r, "reported_bodies", 1),
        lambda r: setattr(r, "tasks_completed_watched", 1),
    ):
        client = _FakeMeetingClient([MeetingDecision(action="wait")])
        mode = _llm_mode(client)
        belief = _warm_belief()
        breaker(belief.roster["red"])
        assert mode.decide(belief, ActionState()).kind == "idle"  # no warm anchor
        assert [t for t, _ in client.calls] == ["meeting_start"]


def test_warm_anchor_needs_a_long_tail(monkeypatch) -> None:
    monkeypatch.setenv("CREWBORG_HONOR_SOCIETY", "0")
    client = _FakeMeetingClient([MeetingDecision(action="wait")])
    mode = _llm_mode(client)
    belief = _warm_belief()
    belief.roster["red"].events.clear()
    belief.roster["red"].events.append(
        PlayerEvent(kind="tailing_self", start_tick=0, end_tick=40)  # < 96 ticks
    )
    assert mode.decide(belief, ActionState()).kind == "idle"


def test_warm_anchor_kill_switch(monkeypatch) -> None:
    monkeypatch.setenv("CREWBORG_HONOR_SOCIETY", "0")
    monkeypatch.setenv("CREWBORG_WARM_ANCHOR", "0")
    client = _FakeMeetingClient([MeetingDecision(action="wait")])
    mode = _llm_mode(client)
    assert mode.decide(_warm_belief(), ActionState()).kind == "idle"  # disabled
    assert [t for t, _ in client.calls] == ["meeting_start"]


def test_warm_anchor_hard_bar_still_takes_priority(monkeypatch) -> None:
    monkeypatch.setenv("CREWBORG_HONOR_SOCIETY", "0")
    client = _FakeMeetingClient([MeetingDecision(action="wait")])
    mode = _llm_mode(client)
    belief = _warm_belief()
    belief.suspicion = {"red": 0.95}  # clears the hard bar too
    belief.roster["red"].events.append(PlayerEvent(kind="vent_use", start_tick=4, end_tick=4))

    assert mode.decide(belief, ActionState()).kind == "chat"
    # Hard-bar route: the vote is corroborated (top_suspect) even with no pile.
    vote = mode.decide(_replay_hard(belief, tick=1150), ActionState())
    assert vote.kind == "vote"
    assert vote.target_color == "red"


def _replay_hard(belief: Belief, *, tick: int) -> Belief:
    later = belief.model_copy(deep=True)
    later.last_tick = tick
    return later
