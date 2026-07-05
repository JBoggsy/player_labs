"""Meeting chat-NLP: dependency-parse accusation detection + the lifecycle flag."""

from __future__ import annotations

import pytest

from crewrift.crewborg.map.types import MapData, MapPoint, MapRect, Room
from crewrift.crewborg.modes import AttendMeetingMode
from crewrift.crewborg.perception.entities import VoteCandidate, VotingState
from crewrift.crewborg.strategy.meeting import chat_nlp, chat_evidence
from crewrift.crewborg.strategy.meeting.chat_evidence import parse_claims, verify_claim
from crewrift.crewborg.types import ActionState, Belief, ChatClaim, ChatEvent, PlayerEvent, PlayerRecord

_COLORS = ("red", "blue", "green", "yellow", "orange", "purple")


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


@pytest.fixture(scope="module")
def nlp_model():
    """Load the real model once and inject it (bypassing the async loader)."""

    import spacy

    model = spacy.load("en_core_web_sm", disable=["ner"])
    saved = chat_nlp._model
    chat_nlp._model = model
    yield model
    chat_nlp._model = saved


def _belief_with_chat(messages, *, self_color="orange", teammates=()) -> Belief:
    belief = Belief(self_role="imposter", teammate_colors=set(teammates))
    belief.voting = VotingState(self_marker_color=self_color)
    for color in _COLORS:
        belief.roster[color] = PlayerRecord(color=color, life_status="alive")
    belief.chat_log = [ChatEvent(tick=i, speaker_color=s, text=t) for i, (s, t) in enumerate(messages)]
    return belief


# --- lifecycle / flag -------------------------------------------------------


def test_disabled_flag_turns_chat_nlp_off(monkeypatch) -> None:
    monkeypatch.setenv("CREWBORG_CHAT_NLP", "0")
    assert chat_nlp.is_enabled() is False
    monkeypatch.setenv("CREWBORG_CHAT_NLP", "1")
    assert chat_nlp.is_enabled() is True


def test_no_model_means_no_chat_signal() -> None:
    # Without a loaded model (disabled / still loading), there is no chat signal at all.
    saved = chat_nlp._model
    chat_nlp._model = None
    try:
        belief = _belief_with_chat([("blue", "red sus")])
        assert chat_evidence.chat_accusers(belief) == {}
    finally:
        chat_nlp._model = saved


# --- accusation detection ---------------------------------------------------


def test_a_plain_accusation_is_detected(nlp_model) -> None:
    assert chat_evidence.chat_accusers(_belief_with_chat([("blue", "red sus")])) == {"red": 1}


def test_negated_accusation_is_not_counted(nlp_model) -> None:
    assert chat_evidence.chat_accusers(_belief_with_chat([("blue", "red isn't sus")])) == {}
    assert chat_evidence.chat_accusers(_belief_with_chat([("blue", "i don't think red did it")])) == {}


def test_a_teammate_is_never_counted_as_accused(nlp_model) -> None:
    belief = _belief_with_chat([("blue", "red sus")], teammates=["red"])
    assert chat_evidence.chat_accusers(belief) == {}


def test_our_own_chat_is_ignored(nlp_model) -> None:
    # self (orange) accusing red is not a bandwagon signal for us.
    assert chat_evidence.chat_accusers(_belief_with_chat([("orange", "red sus")])) == {}


def test_distinct_accusers_are_counted(nlp_model) -> None:
    belief = _belief_with_chat([("blue", "red sus"), ("green", "vote red")])
    assert chat_evidence.chat_accusers(belief) == {"red": 2}


def test_the_same_speaker_counts_once(nlp_model) -> None:
    belief = _belief_with_chat([("blue", "red sus"), ("blue", "red vented for sure")])
    assert chat_evidence.chat_accusers(belief) == {"red": 1}


def test_non_accusation_chatter_is_filtered_by_the_gate(nlp_model) -> None:
    # No color + sus-cue ⇒ the keyword gate skips it before spaCy.
    assert chat_evidence.chat_accusers(_belief_with_chat([("blue", "gg everyone nice game")])) == {}


# --- end-to-end: chat suss drives the imposter bandwagon --------------------


def test_imposter_bandwagons_on_chat_suss_alone(nlp_model) -> None:
    mode = AttendMeetingMode()
    belief = Belief(phase="Voting", self_role="imposter", teammate_colors={"green"})
    belief.voting = VotingState(
        timer_present=True, self_marker_color="orange",
        candidates=(VoteCandidate(slot=0, color="red", alive=True), VoteCandidate(slot=1, color="blue", alive=True)),
    )
    belief.roster["red"] = PlayerRecord(color="red", life_status="alive")
    belief.chat_log = [  # no votes cast yet — only chat heat on red
        ChatEvent(tick=1, speaker_color="yellow", text="red sus"),
        ChatEvent(tick=2, speaker_color="purple", text="vote red"),
    ]
    chat = mode.decide(belief, ActionState())
    assert chat.kind == "chat" and chat.text.startswith("red sus:")  # piled on via chat alone


# --- async loader -----------------------------------------------------------


def test_ensure_loading_loads_the_model_in_the_background() -> None:
    saved = (chat_nlp._model, chat_nlp._thread, chat_nlp._failed)
    chat_nlp._model = chat_nlp._thread = None
    chat_nlp._failed = False
    try:
        chat_nlp.ensure_loading()
        assert chat_nlp._thread is not None
        chat_nlp._thread.join(timeout=30)
        assert chat_nlp.get_model() is not None  # loaded off the hot path
    finally:
        chat_nlp._model, chat_nlp._thread, chat_nlp._failed = saved


def test_ensure_loading_is_a_noop_when_disabled(monkeypatch) -> None:
    monkeypatch.setenv("CREWBORG_CHAT_NLP", "0")
    saved = (chat_nlp._model, chat_nlp._thread, chat_nlp._failed)
    chat_nlp._model = chat_nlp._thread = None
    chat_nlp._failed = False
    try:
        chat_nlp.ensure_loading()
        assert chat_nlp._thread is None and chat_nlp.get_model() is None
    finally:
        chat_nlp._model, chat_nlp._thread, chat_nlp._failed = saved


# --- own-chat accusation parse (chat-implied fallback vote) ------------------


def test_accused_colors_parses_a_single_message(nlp_model) -> None:
    colors = set(_COLORS)
    assert chat_evidence.accused_colors("red is sus, saw them vent", colors) == {"red"}
    assert chat_evidence.accused_colors("i vouch for red, they are safe", colors) == set()
    assert chat_evidence.accused_colors("hello everyone", colors) == set()


def test_accused_colors_is_empty_without_a_model() -> None:
    saved = chat_nlp._model
    chat_nlp._model = None
    try:
        assert chat_evidence.accused_colors("red sus", {"red"}) == set()
    finally:
        chat_nlp._model = saved


# --- parse_claims: defense / location -----------------------------------------


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


def test_parse_claims_ignores_a_bare_location_mention_with_no_speaker_or_color_cue() -> None:
    belief = _belief_with_roster({"red"})
    belief.map = _map_with_room("Reactor")
    event = ChatEvent(tick=5, speaker_color=None, text="reactor is empty right now")
    assert parse_claims(belief, event) == []


def test_parse_claims_does_not_self_attribute_a_third_party_vent_report() -> None:
    belief = _belief_with_roster({"red", "blue"})
    belief.map = _map_with_room("Reactor")
    event = ChatEvent(tick=5, speaker_color="blue", text="I saw red vent in reactor")
    claims = parse_claims(belief, event)
    assert not any(c.target_color == "blue" for c in claims)
    assert any(c.target_color == "red" and c.claim_type == "vent" for c in claims)


# --- verify_claim: location/task/vent -----------------------------------------


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
