"""Crewrift Honor Society tests (strategy/honor_society.py + the meeting hooks).

The safety contract under test, per docs/designs/honor-society.md: flag off => no
behaviour change; crew announces once (never imposters, never dead); valid claims
become trusted crew the vote/accuse paths spare; witnessed evidence overrides trust;
liars are ledgered.
"""

from __future__ import annotations

import base64

import pytest

from crewrift.crewborg.modes import AttendMeetingMode
from crewrift.crewborg.strategy import honor_society
from crewrift.crewborg.types import ActionState, Belief, ChatEvent, PlayerEvent, PlayerRecord


SEED_B64 = base64.urlsafe_b64encode(b"\x01" * 32).decode()


@pytest.fixture()
def society_on(monkeypatch):
    monkeypatch.setenv(honor_society.ENV_FLAG, "1")
    monkeypatch.setenv(honor_society.ENV_SEED, SEED_B64)
    honor_society.reset_identity_for_tests()
    yield
    honor_society.reset_identity_for_tests()


class _Emit:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []
        self.counters: list[str] = []

    def event(self, name: str, data: dict | None = None) -> None:
        self.events.append((name, data or {}))

    def counter(self, name: str, value: int = 1) -> None:
        self.counters.append(name)


def _other_member_announce(color: str) -> tuple[str, str]:
    """A second member's (pub_b64, announce text) built with an independent key."""

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    key = Ed25519PrivateKey.generate()
    pub = base64.urlsafe_b64encode(
        key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    ).decode().rstrip("=")
    sig = base64.urlsafe_b64encode(
        key.sign(f"{honor_society.PREFIX}|crew|{color}".encode())
    ).decode().rstrip("=")
    return pub, f"{honor_society.PREFIX} iam {pub} crew {sig}"


def _crew_belief(**kw) -> Belief:
    belief = Belief(phase="Voting", self_role="crewmate", self_color="blue", self_alive=True, **kw)
    belief.roster["red"] = PlayerRecord(color="red", life_status="alive", last_seen_tick=1)
    belief.roster["green"] = PlayerRecord(color="green", life_status="alive", last_seen_tick=1)
    return belief


# --- gating ---------------------------------------------------------------------


def test_disabled_without_flag(monkeypatch) -> None:
    monkeypatch.delenv(honor_society.ENV_FLAG, raising=False)
    honor_society.reset_identity_for_tests()
    assert not honor_society.enabled()
    assert not honor_society.vote_veto(_crew_belief(), "red")


def test_flag_off_meeting_behaviour_unchanged(monkeypatch) -> None:
    monkeypatch.delenv(honor_society.ENV_FLAG, raising=False)
    honor_society.reset_identity_for_tests()
    mode = AttendMeetingMode()
    belief = _crew_belief()
    belief.suspicion = {"red": 0.95}
    belief.roster["red"].events = [PlayerEvent(kind="vent_use", start_tick=4, end_tick=4)]
    chat = mode.decide(belief, ActionState())
    assert chat.kind == "chat" and "CHS1" not in (chat.text or "")  # normal accusation, no announce


# --- protocol -------------------------------------------------------------------


def test_announce_roundtrip_and_tamper_rejection(society_on) -> None:
    text = honor_society.announce_text("blue")
    assert len(text) <= 160  # fits crewborg's own chat cap
    msg = honor_society.parse(text)
    assert msg is not None and msg[0] == "iam"
    _, pub, sig = msg
    assert honor_society.verify_announce(pub, sig, "blue")
    assert not honor_society.verify_announce(pub, sig, "red")  # bound to the claimed color
    assert not honor_society.verify_announce(pub, sig[:-2] + "AA", "blue")


def test_challenge_response_roundtrip(society_on) -> None:
    nonce = "bm9uY2Vub25jZQ"
    text = honor_society.response_text(nonce, "blue")
    msg = honor_society.parse(text)
    assert msg == ("resp", nonce, msg[2])
    pub = honor_society.public_key_b64()
    assert honor_society.verify_response(pub, msg[2], nonce, "blue")
    assert not honor_society.verify_response(pub, msg[2], "othernonce", "blue")


def test_parse_rejects_junk(society_on) -> None:
    for junk in ("", "hello", "CHS1", "CHS1 iam onlytwo", "CHS2 iam a crew b", "red sus: saw them vent"):
        assert honor_society.parse(junk) is None


# --- listening ------------------------------------------------------------------


def test_valid_claim_becomes_trusted_and_invalid_is_ignored(society_on) -> None:
    belief = _crew_belief()
    pub, announce = _other_member_announce("green")
    belief.chat_log.append(ChatEvent(tick=5, speaker_color="green", text=announce))
    # red replays green's announce verbatim: signature is bound to green, not red.
    belief.chat_log.append(ChatEvent(tick=6, speaker_color="red", text=announce))
    emit = _Emit()
    honor_society.process_chats(belief, emit)
    assert belief.society_trusted == {"green"}
    assert belief.society_claims == {"green": pub}
    assert any(name == "honor_invalid_sig" for name, _ in emit.events)


def test_processing_is_idempotent_across_ticks(society_on) -> None:
    belief = _crew_belief()
    _, announce = _other_member_announce("green")
    belief.chat_log.append(ChatEvent(tick=5, speaker_color="green", text=announce))
    emit = _Emit()
    honor_society.process_chats(belief, emit)
    honor_society.process_chats(belief, emit)
    assert sum(1 for name, _ in emit.events if name == "honor_claim") == 1


def test_challenge_naming_us_is_queued(society_on) -> None:
    belief = _crew_belief()
    belief.chat_log.append(ChatEvent(tick=5, speaker_color="green", text="CHS1 chal blue bm9uY2U"))
    belief.chat_log.append(ChatEvent(tick=6, speaker_color="green", text="CHS1 chal red b3RoZXI"))
    honor_society.process_chats(belief, _Emit())
    assert belief.society_challenges_due == ["bm9uY2U"]  # only the one naming OUR color


def test_witnessed_claimant_is_ledgered_as_liar(society_on) -> None:
    belief = _crew_belief()
    pub, announce = _other_member_announce("green")
    belief.chat_log.append(ChatEvent(tick=5, speaker_color="green", text=announce))
    # We saw green kill: definitional imposter -> the crew claim was a lie.
    belief.roster["green"].events = [PlayerEvent(kind="kill", start_tick=4, end_tick=4)]
    emit = _Emit()
    honor_society.process_chats(belief, emit)
    assert "green" not in belief.society_trusted
    assert pub in belief.society_liar_keys
    assert any(name == "honor_liar" for name, _ in emit.events)


# --- sending (mode hook) ----------------------------------------------------------


def test_crew_announces_once_at_first_meeting_then_plays_normally(society_on) -> None:
    mode = AttendMeetingMode()
    belief = _crew_belief()
    belief.society_meeting_no = 1
    belief.suspicion = {"red": 0.95}
    belief.roster["red"].events = [PlayerEvent(kind="vent_use", start_tick=4, end_tick=4)]
    first = mode.decide(belief, ActionState())
    assert first.kind == "chat" and first.text.startswith("CHS1 iam ")
    assert belief.society_announced
    # Cooldown passed: the normal accusation still happens; the announce is not repeated.
    belief.last_tick = 400
    second = mode.decide(belief, ActionState())
    assert second.kind == "chat" and "CHS1" not in second.text


def test_imposter_never_announces(society_on) -> None:
    mode = AttendMeetingMode()
    belief = Belief(phase="Voting", self_role="imposter", self_color="blue", self_alive=True)
    intent = mode.decide(belief, ActionState())
    assert intent.kind != "chat" or "CHS1" not in (intent.text or "")
    assert not belief.society_announced


def test_dead_crew_does_not_announce(society_on) -> None:
    mode = AttendMeetingMode()
    belief = _crew_belief()
    belief.self_alive = False
    intent = mode.decide(belief, ActionState())
    assert intent.kind != "chat"
    assert not belief.society_announced


def test_queued_challenge_response_is_sent(society_on) -> None:
    mode = AttendMeetingMode()
    belief = _crew_belief()
    belief.society_announced = True
    belief.society_challenges_due.append("bm9uY2U")
    intent = mode.decide(belief, ActionState())
    assert intent.kind == "chat" and intent.text.startswith("CHS1 resp bm9uY2U ")
    assert belief.society_challenges_due == []


# --- vote / accuse vetoes ---------------------------------------------------------


def test_trusted_member_vote_becomes_skip(society_on) -> None:
    mode = AttendMeetingMode()
    belief = _crew_belief()
    belief.society_announced = True
    belief.society_trusted.add("red")
    belief.suspicion = {"red": 0.95}  # posterior says vote red; trust says spare them
    belief.roster["red"].events = [PlayerEvent(kind="tailing_self", start_tick=4, end_tick=40)]
    intents = [mode.decide(belief, ActionState()) for _ in range(3)]
    votes = [i for i in intents if i.kind == "vote"]
    assert votes and all(v.target_color is None for v in votes)  # skip, not red


def test_witnessed_kill_overrides_trust(society_on) -> None:
    mode = AttendMeetingMode()
    belief = _crew_belief()
    belief.society_announced = True
    belief.society_trusted.add("red")
    belief.suspicion = {"red": 0.99}
    belief.roster["red"].events = [PlayerEvent(kind="kill", start_tick=4, end_tick=4)]
    intents = [mode.decide(belief, ActionState()) for _ in range(3)]
    votes = [i for i in intents if i.kind == "vote"]
    assert votes and votes[0].target_color == "red"
