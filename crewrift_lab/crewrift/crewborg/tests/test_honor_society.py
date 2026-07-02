"""Crewrift Honor Society tests (strategy/honor_society.py + the meeting hooks).

The safety contract under test, per docs/designs/honor-society.md: flag off => no
behaviour change; crew announces the HS1 line once (never imposters, never dead);
valid claims become trusted crew the vote/accuse paths spare; witnessed evidence
overrides trust; replays and stale/tampered announcements are rejected; liars are
ledgered.
"""

from __future__ import annotations

import base64
import time

import pytest

from crewrift.crewborg.modes import AttendMeetingMode
from crewrift.crewborg.strategy import honor_society
from crewrift.crewborg.types import ActionState, Belief, ChatEvent, PlayerEvent, PlayerRecord


SEED_B64 = base64.b64encode(b"\x01" * 32).decode()


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


def _other_member_announce(color: str, *, now: float | None = None) -> tuple[str, str]:
    """A second member's (pub_b64, HS1 announce text) built with an independent key."""

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    key = Ed25519PrivateKey.generate()
    pub = base64.b64encode(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()
    ts = int(now if now is not None else time.time())
    nonce = base64.b64encode(b"\x02" * 6).decode()
    sig = base64.b64encode(key.sign(f"HS1|{ts}|{nonce}|{color.lower()}".encode())).decode()
    return pub, f"HS1 {ts} {nonce} {pub} {sig}"


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
    assert chat.kind == "chat" and "HS1" not in (chat.text or "")  # normal accusation, no announce


# --- HS1 protocol -----------------------------------------------------------------


def test_announce_is_exactly_157_chars_and_verifies(society_on) -> None:
    text = honor_society.announce_text("blue")
    assert len(text) == 157  # the HS1 budget: 4+10+1+8+1+44+1+88
    msg = honor_society.parse(text)
    assert msg is not None
    ts, nonce, pub, sig = msg
    assert honor_society.verify_announce(ts, nonce, pub, sig, "blue") == "ok"
    # Bound to the announcer's color: a re-broadcast from another seat fails.
    assert honor_society.verify_announce(ts, nonce, pub, sig, "red") == "bad_sig"
    # Tampered signature fails.
    bad_sig = sig[:-3] + ("AA=" if not sig.endswith("AA=") else "BB=")
    assert honor_society.verify_announce(ts, nonce, pub, bad_sig, "blue") == "bad_sig"


def test_stale_announce_is_rejected(society_on) -> None:
    now = time.time()
    text = honor_society.announce_text("blue", now=now - 100)
    ts, nonce, pub, sig = honor_society.parse(text)
    assert honor_society.verify_announce(ts, nonce, pub, sig, "blue", receipt_time=now) == "stale"
    assert honor_society.verify_announce(ts, nonce, pub, sig, "blue", receipt_time=now - 95) == "ok"


def test_parse_rejects_junk(society_on) -> None:
    for junk in ("", "hello", "HS1", "HS1 123 n p s", "HS2 1751470000 nonce pub sig",
                 "red sus: saw them vent", "HS1 notatime aaaaaaaa pub sig"):
        assert honor_society.parse(junk) is None


# --- listening ------------------------------------------------------------------


def test_valid_claim_becomes_trusted_and_rebroadcast_is_rejected(society_on) -> None:
    belief = _crew_belief()
    now = time.time()
    pub, announce = _other_member_announce("green", now=now)
    belief.chat_log.append(ChatEvent(tick=5, speaker_color="green", text=announce))
    # red re-broadcasts green's announce verbatim: the signature binds green's color.
    belief.chat_log.append(ChatEvent(tick=6, speaker_color="red", text=announce))
    emit = _Emit()
    honor_society.process_chats(belief, emit, receipt_time=now)
    assert belief.society_trusted == {"green"}
    assert belief.society_claims == {"green": pub}
    # green's key is already bound, so red's copy dies as a suspected replay
    # (first-poster-wins) before signature verification even matters.
    assert any(name == "honor_replay_suspected" for name, _ in emit.events)


def test_processing_is_idempotent_across_ticks(society_on) -> None:
    belief = _crew_belief()
    now = time.time()
    _, announce = _other_member_announce("green", now=now)
    belief.chat_log.append(ChatEvent(tick=5, speaker_color="green", text=announce))
    emit = _Emit()
    honor_society.process_chats(belief, emit, receipt_time=now)
    honor_society.process_chats(belief, emit, receipt_time=now)
    assert sum(1 for name, _ in emit.events if name == "honor_claim") == 1


def test_stale_incoming_claim_is_not_trusted(society_on) -> None:
    belief = _crew_belief()
    now = time.time()
    _, announce = _other_member_announce("green", now=now - 60)
    belief.chat_log.append(ChatEvent(tick=5, speaker_color="green", text=announce))
    emit = _Emit()
    honor_society.process_chats(belief, emit, receipt_time=now)
    assert belief.society_trusted == set()
    assert any(name == "honor_invalid_announce" and d.get("why") == "stale" for name, d in emit.events)


def test_witnessed_claimant_is_ledgered_as_liar(society_on) -> None:
    belief = _crew_belief()
    now = time.time()
    pub, announce = _other_member_announce("green", now=now)
    belief.chat_log.append(ChatEvent(tick=5, speaker_color="green", text=announce))
    # We saw green kill: definitional imposter -> the crew claim was a lie.
    belief.roster["green"].events = [PlayerEvent(kind="kill", start_tick=4, end_tick=4)]
    emit = _Emit()
    honor_society.process_chats(belief, emit, receipt_time=now)
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
    assert first.kind == "chat" and first.text.startswith("HS1 ")
    assert belief.society_announced
    # Cooldown passed: the normal accusation still happens; the announce is not repeated.
    belief.last_tick = 400
    second = mode.decide(belief, ActionState())
    assert second.kind == "chat" and "HS1" not in second.text


def test_imposter_never_announces(society_on) -> None:
    mode = AttendMeetingMode()
    belief = Belief(phase="Voting", self_role="imposter", self_color="blue", self_alive=True)
    intent = mode.decide(belief, ActionState())
    assert intent.kind != "chat" or "HS1" not in (intent.text or "")
    assert not belief.society_announced


def test_dead_crew_does_not_announce(society_on) -> None:
    mode = AttendMeetingMode()
    belief = _crew_belief()
    belief.self_alive = False
    intent = mode.decide(belief, ActionState())
    assert intent.kind != "chat"
    assert not belief.society_announced


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


def test_accepts_base64url_member_announce(society_on) -> None:
    # A real member implementation emits unpadded base64url (spec text says standard
    # b64) — receiver accepts both. This is that member's actual example message,
    # signed as color "red"; freshness pinned to its canned timestamp.
    msg = ("HS1 1782000000 aQ8-Zr2K WxWJy6ZOjtSAPzoLBSGSgMIe0uC2b7mYke-7LRUJnf8 "
           "9e3plbO9Y-3z2q6NpbK3W6U6YtarOnl8d7uN17mZhbOgZ3YLhY7QW2Nn_5su3Qy4mUaZMfF2OszHdYmeV5p_Dg")
    parsed = honor_society.parse(msg)
    assert parsed is not None
    ts, nonce, pub, sig = parsed
    assert honor_society.verify_announce(ts, nonce, pub, sig, "red", receipt_time=ts) == "ok"
    assert honor_society.verify_announce(ts, nonce, pub, sig, "blue", receipt_time=ts) == "bad_sig"


def test_known_member_registry_recognizes_alex_in_either_encoding(society_on) -> None:
    honor_society.reset_members_for_tests()
    urlsafe = "WxWJy6ZOjtSAPzoLBSGSgMIe0uC2b7mYke-7LRUJnf8"
    standard = base64.b64encode(base64.urlsafe_b64decode(urlsafe + "=")).decode()
    assert honor_society.known_member_label(urlsafe) == "alex-smith"
    assert honor_society.known_member_label(standard) == "alex-smith"
    assert honor_society.known_member_label(base64.b64encode(b"\x09" * 32).decode()) is None


def test_known_member_claim_lands_in_society_known(society_on, monkeypatch, tmp_path) -> None:
    # Registry override naming the TEST identity's key as a known member.
    import json
    pub = honor_society.public_key_b64()
    reg = tmp_path / "members.json"
    reg.write_text(json.dumps({
        "schema": "crewborg-honor-members/v1",
        "members": [{"pub": pub, "label": "test-member"}],
    }))
    monkeypatch.setenv(honor_society.ENV_MEMBERS, str(reg))
    honor_society.reset_members_for_tests()
    try:
        belief = _crew_belief()
        now = time.time()
        emit = _Emit()
        # Unknown fresh key: trusted but NOT known.
        _, announce = _other_member_announce("green", now=now)
        belief.chat_log.append(ChatEvent(tick=5, speaker_color="green", text=announce))
        honor_society.process_chats(belief, emit, receipt_time=now)
        assert "green" in belief.society_trusted and "green" not in belief.society_known
        # The registry key (distinct color) -> known with its label.
        nonce = base64.b64encode(b"\x03" * 6).decode()
        sig = honor_society._sign(f"HS1|{int(now)}|{nonce}|red")
        belief.chat_log.append(ChatEvent(tick=6, speaker_color="red", text=f"HS1 {int(now)} {nonce} {pub} {sig}"))
        honor_society.process_chats(belief, emit, receipt_time=now)
        assert belief.society_known.get("red") == "test-member"
        assert any(name == "honor_known_member" for name, _ in emit.events)
    finally:
        honor_society.reset_members_for_tests()
