"""Crewrift Honor Society tests (strategy/honor_society.py + the meeting hooks).

The safety contract under test, per docs/designs/honor-society.md: flag off => no
behaviour change; crew announces the compact HS1 line once (never imposters, never
dead); valid claims from KNOWN members become trusted crew the vote/accuse paths
spare; witnessed evidence overrides trust; stale/tampered/cross-seat announcements
are rejected; liars are ledgered.

Wire format is the real HS1 protocol (verified against the live sasmith champion,
2026-07-21): compact ``HS1 <sig>`` over ``HS1|<ts5>|<color>``; legacy
``HS1 <ts> <nonce> <pub> <sig>`` over ``HS1|<ts>|<nonce>|<color>`` still accepted.
"""

from __future__ import annotations

import base64
import json
import time

import pytest

from crewrift.crewborg.modes import AttendMeetingMode
from crewrift.crewborg.strategy import honor_society
from crewrift.crewborg.types import ActionState, Belief, ChatEvent, PlayerEvent, PlayerRecord


SEED_B64 = base64.b64encode(b"\x01" * 32).decode()

# Alex Smith's real registered public key (data/honor_members.json), unpadded b64url.
ALEX_PUB = "WxWJy6ZOjtSAPzoLBSGSgMIe0uC2b7mYke-7LRUJnf8"


@pytest.fixture()
def society_on(monkeypatch):
    monkeypatch.setenv(honor_society.ENV_FLAG, "1")
    monkeypatch.setenv(honor_society.ENV_SECRET, SEED_B64)
    monkeypatch.delenv(honor_society.ENV_SEED, raising=False)
    honor_society.reset_identity_for_tests()
    honor_society.reset_members_for_tests()
    honor_society.reset_distrust_for_tests()
    yield
    honor_society.reset_identity_for_tests()
    honor_society.reset_members_for_tests()
    honor_society.reset_distrust_for_tests()


class _Emit:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []
        self.counters: list[str] = []

    def event(self, name: str, data: dict | None = None) -> None:
        self.events.append((name, data or {}))

    def counter(self, name: str, value: int = 1) -> None:
        self.counters.append(name)


def _member_key():
    """A fresh Ed25519 (signing_key, canonical_pub_b64url) pair for a test member."""

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    key = Ed25519PrivateKey.generate()
    pub_raw = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return key, base64.urlsafe_b64encode(pub_raw).decode().rstrip("=")


def _compact_announce(key, color: str, *, now: float | None = None) -> str:
    """A member's compact ``HS1 <sig>`` line signed with ``key`` over ts5|color."""

    ts5 = (int(now if now is not None else time.time()) // honor_society.QUANTUM_SECONDS) * honor_society.QUANTUM_SECONDS
    sig = base64.urlsafe_b64encode(key.sign(f"HS1|{ts5}|{color.lower()}".encode())).decode().rstrip("=")
    return f"HS1 {sig}"


def _legacy_announce(key, pub_b64: str, color: str, *, now: float | None = None) -> str:
    ts = int(now if now is not None else time.time())
    nonce = base64.urlsafe_b64encode(b"\x02" * 6).decode().rstrip("=")
    sig = base64.urlsafe_b64encode(key.sign(f"HS1|{ts}|{nonce}|{color.lower()}".encode())).decode().rstrip("=")
    return f"HS1 {ts} {nonce} {pub_b64} {sig}"


def _registry(tmp_path, members) -> str:
    reg = tmp_path / "members.json"
    reg.write_text(json.dumps({"schema": honor_society.MEMBERS_SCHEMA, "members": members}))
    return str(reg)


def _crew_belief(**kw) -> Belief:
    belief = Belief(phase="Voting", self_role="crewmate", self_color="blue", self_alive=True, **kw)
    belief.roster["red"] = PlayerRecord(color="red", life_status="alive", last_seen_tick=1)
    belief.roster["green"] = PlayerRecord(color="green", life_status="alive", last_seen_tick=1)
    return belief


# --- gating ---------------------------------------------------------------------


def test_flag_default_on(monkeypatch) -> None:
    # HS defaults ON: no flag set => enabled (receive-always). Explicit false disables.
    monkeypatch.delenv(honor_society.ENV_FLAG, raising=False)
    monkeypatch.setenv(honor_society.ENV_SECRET, SEED_B64)
    honor_society.reset_identity_for_tests()
    assert honor_society.enabled()
    for off in ("0", "false", "no", "off"):
        monkeypatch.setenv(honor_society.ENV_FLAG, off)
        honor_society.reset_identity_for_tests()
        assert not honor_society.enabled()


def test_disabled_when_flag_false(monkeypatch) -> None:
    monkeypatch.setenv(honor_society.ENV_FLAG, "0")
    honor_society.reset_identity_for_tests()
    assert not honor_society.enabled()
    assert not honor_society.vote_veto(_crew_belief(), "red")


def test_flag_off_meeting_behaviour_unchanged(monkeypatch) -> None:
    monkeypatch.setenv(honor_society.ENV_FLAG, "0")
    honor_society.reset_identity_for_tests()
    mode = AttendMeetingMode()
    belief = _crew_belief()
    belief.suspicion = {"red": 0.95}
    belief.roster["red"].events = [PlayerEvent(kind="vent_use", start_tick=4, end_tick=4)]
    chat = mode.decide(belief, ActionState())
    assert chat.kind == "chat" and "HS1" not in (chat.text or "")  # normal accusation, no announce


# --- HS1 protocol: our own compact announce -------------------------------------


def test_compact_announce_is_two_tokens_and_self_verifies(society_on, tmp_path, monkeypatch) -> None:
    # Register our own test key so the compact brute-force can verify it.
    pub = honor_society.public_key_b64()
    monkeypatch.setenv(honor_society.ENV_MEMBERS, _registry(tmp_path, [{"pub": pub, "label": "self-test"}]))
    honor_society.reset_members_for_tests()
    now = time.time()
    text = honor_society.announce_text("blue", now=now)
    parts = text.split()
    assert parts[0] == "HS1" and len(parts) == 2      # compact: HS1 <sig>
    assert 88 <= len(text) <= 92                       # ~90 chars
    parsed = honor_society.parse(text)
    assert parsed is not None and parsed.form == "compact"
    verdict, vpub = honor_society.verify(parsed, "blue", receipt_time=now)
    assert verdict == "ok" and vpub == pub
    # Bound to the announcer's color: verifying it as another seat's color fails.
    assert honor_society.verify(parsed, "red", receipt_time=now)[0] == "bad_sig"


def test_compact_freshness_window(society_on, tmp_path, monkeypatch) -> None:
    pub = honor_society.public_key_b64()
    monkeypatch.setenv(honor_society.ENV_MEMBERS, _registry(tmp_path, [{"pub": pub, "label": "self-test"}]))
    honor_society.reset_members_for_tests()
    now = time.time()
    parsed = honor_society.parse(honor_society.announce_text("blue", now=now))
    assert honor_society.verify(parsed, "blue", receipt_time=now)[0] == "ok"
    assert honor_society.verify(parsed, "blue", receipt_time=now + 5)[0] == "ok"      # within window
    assert honor_society.verify(parsed, "blue", receipt_time=now + 100)[0] == "bad_sig"  # stale => no match


def test_parse_rejects_junk(society_on) -> None:
    for junk in ("", "hello", "HS1", "red sus: saw them vent",
                 "HS1 a b c", "HS2 sig", "HS1 1 2 3 4 5 6"):
        assert honor_society.parse(junk) is None
    # A well-formed compact shell parses but fails verification (no matching key).
    parsed = honor_society.parse("HS1 " + base64.urlsafe_b64encode(b"\x00" * 64).decode().rstrip("="))
    assert parsed is not None and honor_society.verify(parsed, "red")[0] == "bad_sig"


# --- listening: known members become trusted ------------------------------------


def test_known_member_compact_claim_becomes_trusted(society_on, tmp_path, monkeypatch) -> None:
    key, pub = _member_key()
    monkeypatch.setenv(honor_society.ENV_MEMBERS, _registry(tmp_path, [{"pub": pub, "label": "peer"}]))
    honor_society.reset_members_for_tests()
    belief = _crew_belief()
    now = time.time()
    belief.chat_log.append(ChatEvent(tick=5, speaker_color="green", text=_compact_announce(key, "green", now=now)))
    emit = _Emit()
    honor_society.process_chats(belief, emit, receipt_time=now)
    assert belief.society_trusted == {"green"}
    assert belief.society_known.get("green") == "peer"
    assert belief.society_claims.get("green") == pub
    assert any(name == "honor_known_member" for name, _ in emit.events)


def test_real_sasmith_signature_verifies(society_on) -> None:
    """A REAL compact announcement captured from a live game (2026-07-21), signed
    by sasmith as 'cyan' at ts5=1784664095. Proves the vendored registry + verify
    path accept the actual champion's wire format end-to-end."""

    honor_society.reset_members_for_tests()  # use the vendored data/honor_members.json (has alex-smith)
    real_sig = "ya3nvOOQUpAQGzYdkvnliyPZ_pdi3ufxtzghEkAOWgiCLoPooMc6QIbwxLn9K7FctvFc7SnU2IIboQqU2z9SBw"
    parsed = honor_society.parse(f"HS1 {real_sig}")
    assert parsed is not None and parsed.form == "compact"
    ts5 = 1784664095
    verdict, pub = honor_society.verify(parsed, "cyan", receipt_time=ts5)
    assert verdict == "ok"
    assert honor_society.known_member_label(pub) == "alex-smith"
    # Signed for cyan: verifying as another color must fail.
    assert honor_society.verify(parsed, "purple", receipt_time=ts5)[0] == "bad_sig"


def test_unknown_key_compact_is_not_verifiable(society_on, tmp_path, monkeypatch) -> None:
    # Compact has no pubkey on the wire, so a NON-registered member cannot be
    # verified at all (fail-closed): recorded as invalid, never trusted.
    monkeypatch.setenv(honor_society.ENV_MEMBERS, _registry(tmp_path, []))  # empty ledger
    honor_society.reset_members_for_tests()
    key, _pub = _member_key()
    belief = _crew_belief()
    now = time.time()
    belief.chat_log.append(ChatEvent(tick=5, speaker_color="green", text=_compact_announce(key, "green", now=now)))
    emit = _Emit()
    honor_society.process_chats(belief, emit, receipt_time=now)
    assert belief.society_trusted == set()
    assert any(name == "honor_invalid_announce" for name, _ in emit.events)


def test_legacy_form_still_accepted(society_on, tmp_path, monkeypatch) -> None:
    # Legacy self-describing form verifies from the wire pubkey; a KNOWN key trusts.
    key, pub = _member_key()
    monkeypatch.setenv(honor_society.ENV_MEMBERS, _registry(tmp_path, [{"pub": pub, "label": "peer"}]))
    honor_society.reset_members_for_tests()
    belief = _crew_belief()
    now = time.time()
    belief.chat_log.append(ChatEvent(tick=5, speaker_color="green", text=_legacy_announce(key, pub, "green", now=now)))
    emit = _Emit()
    honor_society.process_chats(belief, emit, receipt_time=now)
    assert "green" in belief.society_trusted


def test_processing_is_idempotent_across_ticks(society_on, tmp_path, monkeypatch) -> None:
    key, pub = _member_key()
    monkeypatch.setenv(honor_society.ENV_MEMBERS, _registry(tmp_path, [{"pub": pub, "label": "peer"}]))
    honor_society.reset_members_for_tests()
    belief = _crew_belief()
    now = time.time()
    belief.chat_log.append(ChatEvent(tick=5, speaker_color="green", text=_compact_announce(key, "green", now=now)))
    emit = _Emit()
    honor_society.process_chats(belief, emit, receipt_time=now)
    honor_society.process_chats(belief, emit, receipt_time=now)
    assert sum(1 for name, _ in emit.events if name == "honor_claim") == 1


def test_stale_incoming_compact_claim_is_not_trusted(society_on, tmp_path, monkeypatch) -> None:
    key, pub = _member_key()
    monkeypatch.setenv(honor_society.ENV_MEMBERS, _registry(tmp_path, [{"pub": pub, "label": "peer"}]))
    honor_society.reset_members_for_tests()
    belief = _crew_belief()
    now = time.time()
    belief.chat_log.append(ChatEvent(tick=5, speaker_color="green", text=_compact_announce(key, "green", now=now - 60)))
    emit = _Emit()
    honor_society.process_chats(belief, emit, receipt_time=now)
    assert belief.society_trusted == set()
    assert any(name == "honor_invalid_announce" for name, _ in emit.events)


def test_cross_seat_rebroadcast_fails(society_on, tmp_path, monkeypatch) -> None:
    # green's compact announce copied verbatim by red: the sig binds green's color,
    # so verifying it against red's observed color fails (no trust for red).
    key, pub = _member_key()
    monkeypatch.setenv(honor_society.ENV_MEMBERS, _registry(tmp_path, [{"pub": pub, "label": "peer"}]))
    honor_society.reset_members_for_tests()
    belief = _crew_belief()
    now = time.time()
    line = _compact_announce(key, "green", now=now)
    belief.chat_log.append(ChatEvent(tick=5, speaker_color="green", text=line))
    belief.chat_log.append(ChatEvent(tick=6, speaker_color="red", text=line))
    emit = _Emit()
    honor_society.process_chats(belief, emit, receipt_time=now)
    assert belief.society_trusted == {"green"}  # red's copy rejected


def test_distrusted_key_announcement_is_never_trusted(society_on, tmp_path, monkeypatch) -> None:
    # The harvested cross-game distrust list (harvest_liars.py output): a KNOWN
    # member whose key is on it gets no trust from a valid announce, from the
    # first meeting — no need to re-witness the lie this episode.
    key, pub = _member_key()
    monkeypatch.setenv(honor_society.ENV_MEMBERS, _registry(tmp_path, [{"pub": pub, "label": "peer"}]))
    distrust = tmp_path / "distrust.json"
    distrust.write_text(json.dumps({
        "schema": honor_society.DISTRUST_SCHEMA,
        "liars": [{"pub": pub, "lie_events": 2}],
    }))
    monkeypatch.setenv(honor_society.ENV_DISTRUST, str(distrust))
    honor_society.reset_members_for_tests()
    honor_society.reset_distrust_for_tests()
    belief = _crew_belief()
    now = time.time()
    belief.chat_log.append(ChatEvent(tick=5, speaker_color="green", text=_compact_announce(key, "green", now=now)))
    emit = _Emit()
    honor_society.process_chats(belief, emit, receipt_time=now)
    assert belief.society_trusted == set()                 # never trusted
    assert pub in belief.society_liar_keys                 # pre-ledgered
    assert belief.society_known.get("green") == "peer"     # identity still bound
    assert any(name == "honor_distrusted_announce" for name, _ in emit.events)
    assert not honor_society.vote_veto(belief, "green")    # veto never fires for them


def test_distrust_list_missing_or_disabled_is_harmless(society_on, tmp_path, monkeypatch) -> None:
    # "0" disables; a bad/missing file is an empty list — either way a known
    # member still trusts normally.
    key, pub = _member_key()
    monkeypatch.setenv(honor_society.ENV_MEMBERS, _registry(tmp_path, [{"pub": pub, "label": "peer"}]))
    for distrust_env in ("0", str(tmp_path / "nonexistent.json")):
        monkeypatch.setenv(honor_society.ENV_DISTRUST, distrust_env)
        honor_society.reset_members_for_tests()
        honor_society.reset_distrust_for_tests()
        belief = _crew_belief()
        now = time.time()
        belief.chat_log.append(ChatEvent(tick=5, speaker_color="green", text=_compact_announce(key, "green", now=now)))
        honor_society.process_chats(belief, _Emit(), receipt_time=now)
        assert belief.society_trusted == {"green"}


def test_vendored_distrust_file_loads_and_is_empty(society_on, monkeypatch) -> None:
    # The shipped data/honor_distrust.json parses under the real loader and is
    # currently empty (no liar observed yet) — nobody is distrusted by default.
    monkeypatch.delenv(honor_society.ENV_DISTRUST, raising=False)
    honor_society.reset_distrust_for_tests()
    assert not honor_society.is_distrusted(ALEX_PUB)
    assert honor_society._load_distrust() == set()


def test_witnessed_claimant_is_ledgered_as_liar(society_on, tmp_path, monkeypatch) -> None:
    key, pub = _member_key()
    monkeypatch.setenv(honor_society.ENV_MEMBERS, _registry(tmp_path, [{"pub": pub, "label": "peer"}]))
    honor_society.reset_members_for_tests()
    belief = _crew_belief()
    now = time.time()
    belief.chat_log.append(ChatEvent(tick=5, speaker_color="green", text=_compact_announce(key, "green", now=now)))
    # We saw green kill: definitional imposter -> the crew claim was a lie.
    belief.roster["green"].events = [PlayerEvent(kind="kill", start_tick=4, end_tick=4)]
    emit = _Emit()
    honor_society.process_chats(belief, emit, receipt_time=now)
    assert "green" not in belief.society_trusted
    assert pub in belief.society_liar_keys
    assert any(name == "honor_liar" for name, _ in emit.events)


# --- sending (mode hook) ----------------------------------------------------------


def test_crew_announces_once_at_first_meeting_then_plays_normally(society_on) -> None:
    # Ordering contract since 2026-07-29 (loop-alpha L3): the ACCUSATION takes the
    # first chat slot — the server's MessageCooldownTicks=100 silently drops the
    # second chat, and the accusation is the persuasion payload — then the
    # once-per-game HS1 announce follows after the cooldown.
    mode = AttendMeetingMode()
    belief = _crew_belief()
    belief.society_meeting_no = 1
    belief.suspicion = {"red": 0.95}
    belief.roster["red"].events = [PlayerEvent(kind="vent_use", start_tick=4, end_tick=4)]
    first = mode.decide(belief, ActionState())
    assert first.kind == "chat" and "HS1" not in first.text  # the accusation goes first
    assert not belief.society_announced
    # Cooldown passed: the announce follows; not repeated afterwards.
    belief.last_tick = 400
    second = mode.decide(belief, ActionState())
    assert second.kind == "chat" and second.text.startswith("HS1 ") and len(second.text.split()) == 2
    assert belief.society_announced


def test_crew_announce_falls_back_when_no_accusation(society_on) -> None:
    # A silent-skip meeting (nothing to accuse) still announces once the meeting
    # ages past the deferral window — the announce is not lost.
    mode = AttendMeetingMode()
    belief = _crew_belief()
    belief.society_meeting_no = 1
    belief.suspicion = {}
    belief.last_tick = 300  # >= PREVOTE_PUSH_DELAY_TICKS
    intent = mode.decide(belief, ActionState())
    assert intent.kind == "chat" and intent.text.startswith("HS1 ")
    assert belief.society_announced


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


def test_known_member_registry_recognizes_alex_in_either_encoding(society_on) -> None:
    honor_society.reset_members_for_tests()
    urlsafe = ALEX_PUB
    standard = base64.b64encode(base64.urlsafe_b64decode(urlsafe + "=")).decode()
    assert honor_society.known_member_label(urlsafe) == "alex-smith"
    assert honor_society.known_member_label(standard) == "alex-smith"
    assert honor_society.known_member_label(base64.b64encode(b"\x09" * 32).decode()) is None


def test_role_reveal_trust_pins_suspicion_near_zero(society_on) -> None:
    from crewrift.crewborg.strategy.suspicion import update_suspicion
    belief = _crew_belief()
    belief.phase = "Playing"
    belief.roster["red"].events = [PlayerEvent(kind="tailing_self", start_tick=4, end_tick=200, min_dist=10)]
    update_suspicion(belief)
    hot = belief.suspicion.get("red", 0.0)
    belief.society_trusted.add("red")
    update_suspicion(belief)
    pinned = belief.suspicion.get("red", 1.0)
    assert pinned < 0.05 and pinned < hot  # revealed crew: posterior collapses
    assert "red" not in belief.believed_imposters


def test_role_reveal_trust_never_overrides_witnessed(society_on) -> None:
    from crewrift.crewborg.strategy.suspicion import update_suspicion
    belief = _crew_belief()
    belief.phase = "Playing"
    belief.society_trusted.add("red")
    belief.roster["red"].events = [PlayerEvent(kind="kill", start_tick=4, end_tick=4)]
    update_suspicion(belief)
    assert belief.suspicion.get("red", 0.0) > 0.9  # caught in the act: trust loses


def test_vote_veto_applies_in_role_limbo(society_on) -> None:
    # A missed role reveal (self_role None) must not silently disable the trust
    # veto — the seat plays crew paths and the veto is skip-only/safe.
    belief = _crew_belief()
    belief.self_role = None
    belief.society_trusted.add("red")
    assert honor_society.vote_veto(belief, "red")
