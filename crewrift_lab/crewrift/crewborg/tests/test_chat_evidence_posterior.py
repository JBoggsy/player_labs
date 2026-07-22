"""Chat-provided evidence → suspicion posterior, weighted by speaker trust.

Design: crewrift_lab/docs/designs/2026-07-22-chat-evidence-incorporation.md.

Covers: the deterministic template extraction (kill/vent/accusation, no spaCy),
the trust-weighted log-LR term (HS full weight, suspicion-scaled strangers,
witnessed-imposter zero), the trust FLOOR (default 0.9: HS-verified + near-cleared
speakers only — the chatev:v2 variant; floor 0 reproduces chatev:v1), fabricated-
accusation resistance (spam dedup + the cap), the witnessed/HS-pin overrides, the
feature flags, and the counterfactual tracer.
"""

from __future__ import annotations

import math

import pytest

from crewrift.crewborg.strategy import suspicion as suspicion_module
from crewrift.crewborg.strategy.meeting import chat_nlp, chat_evidence
from crewrift.crewborg.strategy.suspicion import (
    CHAT_ACCUSATION_LOG_LR,
    CHAT_EVIDENCE_LR_MAX,
    CHAT_KILL_LOG_LR,
    chat_evidence_contributions,
    chat_evidence_log_lr,
    counterfactual_top_suspect_no_chat,
    top_suspect,
    update_suspicion,
)
from crewrift.crewborg.types import Belief, ChatClaim, ChatEvent, PerceptionFrame, PlayerEvent, PlayerRecord

_COLORS = ("red", "blue", "green", "yellow", "orange", "purple", "cyan", "pink")


@pytest.fixture(autouse=True)
def _chat_evidence_on():
    """Feature ON at the DEFAULT trust floor (0.9) — the chatev:v2 shipping shape.
    Tests exercising the un-floored (chatev:v1) weighting pin trust_floor=0.0."""

    suspicion_module.set_chat_evidence_for_tests(
        True, trust_floor=suspicion_module.CHAT_EVIDENCE_TRUST_FLOOR_DEFAULT
    )
    yield
    suspicion_module.set_chat_evidence_for_tests(None)


def _unfloored() -> None:
    suspicion_module.set_chat_evidence_for_tests(True, trust_floor=0.0)


@pytest.fixture(autouse=True)
def _legacy_hand_model():
    """Most assertions here are path-independent, but pin the legacy model so the
    numbers are stable; the fitted-path test re-enables the vendored weights."""

    saved = suspicion_module._WEIGHTS
    suspicion_module.set_weights(None)
    yield
    suspicion_module.set_weights(saved)


def _belief(*, self_color: str = "orange", role: str = "crewmate") -> Belief:
    frame = PerceptionFrame(tick=1, camera_x=0, camera_y=0, players={}, bodies={}, visible_mask=None)
    belief = Belief(last_tick=1, self_role=role, self_color=self_color, recent_frames=[frame, frame])
    belief.total_player_count = len(_COLORS)
    for color in _COLORS:
        belief.roster[color] = PlayerRecord(color=color, life_status="alive")
    return belief


def _claim(speaker: str, target: str, claim_type: str, **kwargs) -> ChatClaim:
    return ChatClaim(tick=1, speaker_color=speaker, target_color=target, claim_type=claim_type, **kwargs)


# --- deterministic template extraction (no spaCy) -----------------------------


@pytest.fixture()
def _no_nlp():
    saved = chat_nlp._model
    chat_nlp._model = None
    yield
    chat_nlp._model = saved


def _parse(text: str, speaker: str = "green") -> list[ChatClaim]:
    belief = _belief()
    return chat_evidence.parse_claims(belief, ChatEvent(tick=1, speaker_color=speaker, text=text))


def test_template_kill_report_targets_killer_not_victim(_no_nlp) -> None:
    for text in ("saw red kill blue", "red killed blue", "RED killed him", "i saw red kill blue in reactor"):
        claims = _parse(text)
        kills = [c for c in claims if c.claim_type == "kill"]
        assert [c.target_color for c in kills] == ["red"], text
        assert all(c.target_color != "blue" or c.claim_type != "accusation" for c in claims), text
        assert kills[0].source == "template"


def test_template_vent_and_accusation(_no_nlp) -> None:
    assert [(c.target_color, c.claim_type) for c in _parse("red vented")] == [("red", "vent")]
    assert ("red", "accusation") in [(c.target_color, c.claim_type) for c in _parse("vote red")]
    assert ("red", "accusation") in [(c.target_color, c.claim_type) for c in _parse("red is sus")]
    assert ("red", "accusation") in [(c.target_color, c.claim_type) for c in _parse("red sus")]


def test_template_negation_and_questions_are_skipped(_no_nlp) -> None:
    assert _parse("red didn't vent") == []
    assert _parse("not red, red is fine") == []
    assert _parse("who killed blue?") == []
    assert _parse("did red vent?") == []


def test_template_needs_the_template_shape(_no_nlp) -> None:
    # A color + keyword scattered in a line must NOT fire (the old crude-tally bug).
    assert _parse("someone should vent about how red the sky is") == []
    assert _parse("blue found the body, red was with me") == []
    # "kill" with no explicit victim shape must not fire either.
    assert _parse("red kills it every game") == []


def test_spacy_duplicates_are_deduped_against_template_claims() -> None:
    spacy = pytest.importorskip("spacy")
    model = spacy.load("en_core_web_sm", disable=["ner"])
    saved = chat_nlp._model
    chat_nlp._model = model
    try:
        claims = _parse("saw red kill blue")
        # template kill(red); spaCy would also read an accusation(red) — allowed —
        # but its spurious accusation(blue) (victim) must be suppressed.
        assert ("red", "kill") in [(c.target_color, c.claim_type) for c in claims]
        assert ("blue", "accusation") not in [(c.target_color, c.claim_type) for c in claims]
    finally:
        chat_nlp._model = saved


# --- the trust-weighted posterior term ----------------------------------------


def test_hs_member_kill_report_clears_the_vote_bar() -> None:
    belief = _belief()
    belief.society_trusted.add("green")
    belief.roster["red"].claims.append(_claim("green", "red", "kill"))
    update_suspicion(belief)
    assert belief.suspicion["red"] >= 0.9
    assert top_suspect(belief) == "red"


def test_hs_member_bare_accusation_moves_but_does_not_convict() -> None:
    belief = _belief()
    belief.society_trusted.add("green")
    belief.roster["red"].claims.append(_claim("green", "red", "accusation"))
    update_suspicion(belief)
    prior = suspicion_module._prior_imposter_p(belief)
    assert belief.suspicion["red"] > prior
    assert top_suspect(belief) is None  # a single "X sus" is not a conviction


def test_stranger_testimony_is_scaled_by_their_own_suspicion() -> None:
    """The chatev:v1 (un-floored) weighting, kept testable via trust_floor=0."""

    _unfloored()
    belief = _belief()
    update_suspicion(belief)  # establish the prior-tick posterior for the speaker
    belief.roster["red"].claims.append(_claim("green", "red", "kill"))
    stranger_lr = chat_evidence_log_lr(belief, "red", belief.roster["red"])
    prior = suspicion_module._prior_imposter_p(belief)
    assert stranger_lr == pytest.approx((1.0 - prior) * CHAT_KILL_LOG_LR)
    # The same report from a fully-trusted HS member carries strictly more weight.
    belief.society_trusted.add("green")
    assert chat_evidence_log_lr(belief, "red", belief.roster["red"]) == pytest.approx(CHAT_KILL_LOG_LR)


# --- the trust FLOOR (chatev:v2) --------------------------------------------------


def test_floor_zeroes_stranger_testimony() -> None:
    """At the default 0.9 floor a stranger at the prior (trust ≈ 0.71 at 8p/2imp)
    contributes NOTHING — even a kill report (the class the field fabricates)."""

    belief = _belief()
    update_suspicion(belief)
    belief.roster["red"].claims.append(_claim("green", "red", "kill"))
    belief.roster["red"].claims.append(_claim("blue", "red", "accusation"))
    assert chat_evidence_log_lr(belief, "red", belief.roster["red"]) == 0.0
    update_suspicion(belief)
    prior = suspicion_module._prior_imposter_p(belief)
    assert belief.suspicion["red"] == pytest.approx(prior)
    assert top_suspect(belief) is None


def test_floor_passes_hs_member_testimony_in_full() -> None:
    belief = _belief()
    belief.society_trusted.add("green")
    belief.roster["red"].claims.append(_claim("green", "red", "kill"))
    assert chat_evidence_log_lr(belief, "red", belief.roster["red"]) == pytest.approx(CHAT_KILL_LOG_LR)
    update_suspicion(belief)
    assert belief.suspicion["red"] >= 0.9  # HS kill report still clears the vote bar


def test_floor_passes_near_cleared_speaker_at_their_trust_value() -> None:
    belief = _belief()
    belief.suspicion["green"] = 0.05  # near-cleared: trust 0.95 ≥ the 0.9 floor
    belief.roster["red"].claims.append(_claim("green", "red", "kill"))
    assert chat_evidence_log_lr(belief, "red", belief.roster["red"]) == pytest.approx(0.95 * CHAT_KILL_LOG_LR)
    # Just below the floor: zero, not scaled-down.
    belief.suspicion["green"] = 0.11
    assert chat_evidence_log_lr(belief, "red", belief.roster["red"]) == 0.0


def test_floor_does_not_gate_the_contradicted_self_alibi() -> None:
    """Caught-in-a-lie weight is our own observation, not testimony — un-floored."""

    belief = _belief()
    belief.suspicion["red"] = 0.5  # red is well below the trust floor
    belief.roster["red"].claims.append(
        _claim("red", "red", "location", place_name="Reactor", verification="contradicted")
    )
    assert chat_evidence_log_lr(belief, "red", belief.roster["red"]) == pytest.approx(
        suspicion_module.CHAT_CONTRADICTED_ALIBI_LOG_LR
    )


def test_floor_env_parsing(monkeypatch) -> None:
    monkeypatch.delenv("CREWBORG_CHAT_EVIDENCE_TRUST_FLOOR", raising=False)
    assert suspicion_module._chat_evidence_trust_floor_from_env() == pytest.approx(
        suspicion_module.CHAT_EVIDENCE_TRUST_FLOOR_DEFAULT
    )
    monkeypatch.setenv("CREWBORG_CHAT_EVIDENCE_TRUST_FLOOR", "0.5")
    assert suspicion_module._chat_evidence_trust_floor_from_env() == pytest.approx(0.5)
    monkeypatch.setenv("CREWBORG_CHAT_EVIDENCE_TRUST_FLOOR", "0")
    assert suspicion_module._chat_evidence_trust_floor_from_env() == 0.0  # chatev:v1 shape
    monkeypatch.setenv("CREWBORG_CHAT_EVIDENCE_TRUST_FLOOR", "1.5")
    assert suspicion_module._chat_evidence_trust_floor_from_env() == 1.0  # clamped
    monkeypatch.setenv("CREWBORG_CHAT_EVIDENCE_TRUST_FLOOR", "nonsense")
    assert suspicion_module._chat_evidence_trust_floor_from_env() == pytest.approx(
        suspicion_module.CHAT_EVIDENCE_TRUST_FLOOR_DEFAULT
    )


def test_witnessed_imposter_speaker_carries_zero_weight() -> None:
    _unfloored()  # so the zero comes from the witnessed check, not the floor
    belief = _belief()
    belief.roster["green"].events.append(PlayerEvent(kind="kill", start_tick=1, end_tick=1, target_color="cyan"))
    belief.roster["red"].claims.append(_claim("green", "red", "kill"))
    belief.roster["red"].claims.append(_claim("green", "red", "accusation"))
    assert chat_evidence_log_lr(belief, "red", belief.roster["red"]) == 0.0


def test_imposter_spam_cannot_drag_the_posterior(_no_nlp) -> None:
    """Fabricated-accusation resistance: one speaker spamming 'X sus' counts once
    (asserted at the un-floored chatev:v1 weighting — at the default floor the
    spammer contributes zero outright, covered by the floor tests above)."""

    _unfloored()
    belief = _belief()
    update_suspicion(belief)
    for _ in range(10):
        belief.roster["red"].claims.append(_claim("green", "red", "accusation"))
    prior = suspicion_module._prior_imposter_p(belief)
    lr = chat_evidence_log_lr(belief, "red", belief.roster["red"])
    assert lr <= (1.0 - prior) * CHAT_ACCUSATION_LOG_LR + 1e-9  # deduped to one instance
    update_suspicion(belief)
    assert belief.suspicion["red"] < 0.5
    assert top_suspect(belief) is None


def test_many_speakers_stack_but_the_cap_holds() -> None:
    belief = _belief()
    for speaker in ("blue", "green", "yellow", "purple", "cyan", "pink"):
        belief.society_trusted.add(speaker)  # floor-passing speakers (HS-verified)
        belief.roster["red"].claims.append(_claim(speaker, "red", "kill"))
    lr = chat_evidence_log_lr(belief, "red", belief.roster["red"])
    assert lr == pytest.approx(CHAT_EVIDENCE_LR_MAX)
    # Even at the cap, chat alone stays below witnessed certainty.
    update_suspicion(belief)
    assert belief.suspicion["red"] < 0.99


def test_kill_report_subsumes_the_same_speakers_accusation() -> None:
    belief = _belief()
    belief.society_trusted.add("green")
    belief.roster["red"].claims.append(_claim("green", "red", "kill"))
    belief.roster["red"].claims.append(_claim("green", "red", "accusation"))
    assert chat_evidence_log_lr(belief, "red", belief.roster["red"]) == pytest.approx(CHAT_KILL_LOG_LR)


def test_defense_lowers_and_the_negative_cap_holds() -> None:
    belief = _belief()
    belief.society_trusted.add("green")
    belief.roster["red"].claims.append(_claim("green", "red", "defense"))
    lr = chat_evidence_log_lr(belief, "red", belief.roster["red"])
    assert lr == pytest.approx(-math.log(2.0))
    for speaker in ("blue", "yellow", "purple", "cyan", "pink"):
        belief.society_trusted.add(speaker)
        belief.roster["red"].claims.append(_claim(speaker, "red", "defense"))
    assert chat_evidence_log_lr(belief, "red", belief.roster["red"]) >= suspicion_module.CHAT_EVIDENCE_LR_MIN - 1e-9


def test_contradicted_self_alibi_adds_caught_in_a_lie_weight() -> None:
    belief = _belief()
    belief.roster["red"].claims.append(
        _claim("red", "red", "location", place_name="Reactor", verification="contradicted")
    )
    assert chat_evidence_log_lr(belief, "red", belief.roster["red"]) == pytest.approx(
        suspicion_module.CHAT_CONTRADICTED_ALIBI_LOG_LR
    )


def test_self_targeted_stances_carry_no_testimony_weight() -> None:
    # "I'm sus of red" said BY red about red (or defensive self-vouching) is not testimony.
    belief = _belief()
    belief.roster["red"].claims.append(_claim("red", "red", "defense"))
    assert chat_evidence_log_lr(belief, "red", belief.roster["red"]) == 0.0


def test_our_own_chat_is_not_evidence() -> None:
    belief = _belief()
    belief.roster["red"].claims.append(_claim("orange", "red", "kill"))  # orange == self
    assert chat_evidence_log_lr(belief, "red", belief.roster["red"]) == 0.0


def test_unattributed_speaker_carries_no_weight() -> None:
    belief = _belief()
    belief.roster["red"].claims.append(_claim(None, "red", "kill"))
    assert chat_evidence_log_lr(belief, "red", belief.roster["red"]) == 0.0


# --- overrides & consistency ----------------------------------------------------


def test_chat_never_overrides_a_witnessed_catch() -> None:
    belief = _belief()
    belief.roster["red"].events.append(PlayerEvent(kind="kill", start_tick=1, end_tick=1, target_color="cyan"))
    for speaker in ("blue", "green", "yellow", "purple", "cyan", "pink"):
        belief.society_trusted.add(speaker)
        belief.roster["red"].claims.append(_claim(speaker, "red", "defense"))
    update_suspicion(belief)
    assert belief.suspicion["red"] > 0.99  # witnessed floor wins over exculpatory chat


def test_chat_never_overrides_the_hs_trust_pin() -> None:
    belief = _belief()
    belief.society_trusted.add("red")  # red is a verified member
    for speaker in ("blue", "green", "yellow"):
        belief.society_trusted.add(speaker)  # floor-passing accusers (HS-verified)
        belief.roster["red"].claims.append(_claim(speaker, "red", "kill"))
    update_suspicion(belief)
    assert belief.suspicion["red"] < 0.01  # the pin is applied after the chat term


def test_flag_off_reproduces_todays_behavior() -> None:
    belief = _belief()
    belief.society_trusted.add("green")
    belief.roster["red"].claims.append(_claim("green", "red", "kill"))
    suspicion_module.set_chat_evidence_for_tests(False)
    update_suspicion(belief)
    prior = suspicion_module._prior_imposter_p(belief)
    assert belief.suspicion["red"] == pytest.approx(prior)


def test_same_mechanism_on_the_fitted_path() -> None:
    weights = suspicion_module._load_weights()
    if weights is None:
        pytest.skip("no vendored weights")
    suspicion_module.set_weights(weights)
    belief = _belief()
    belief.society_trusted.add("green")
    belief.roster["red"].claims.append(_claim("green", "red", "kill"))
    update_suspicion(belief)
    baseline = {c: p for c, p in belief.suspicion.items() if c != "red"}
    assert belief.suspicion["red"] > max(baseline.values())
    assert belief.suspicion["red"] > 0.8  # actionable on the fitted path too


def test_env_flag_parsing(monkeypatch) -> None:
    monkeypatch.setenv("CREWBORG_CHAT_EVIDENCE", "1")
    assert suspicion_module._chat_evidence_enabled_from_env() is True
    monkeypatch.setenv("CREWBORG_CHAT_EVIDENCE", "0")
    assert suspicion_module._chat_evidence_enabled_from_env() is False
    # Default OFF: the 2026-07-22 A/B refuted the current calibration (design doc).
    monkeypatch.delenv("CREWBORG_CHAT_EVIDENCE")
    assert suspicion_module._chat_evidence_enabled_from_env() is False


# --- tracing surfaces -----------------------------------------------------------


def test_counterfactual_reports_the_chat_free_vote_and_restores_state() -> None:
    belief = _belief()
    belief.society_trusted.add("green")
    belief.roster["red"].claims.append(_claim("green", "red", "kill"))
    update_suspicion(belief)
    live = dict(belief.suspicion)
    assert top_suspect(belief) == "red"
    assert counterfactual_top_suspect_no_chat(belief) is None  # no vote without the chat term
    assert belief.suspicion == live  # posterior restored
    assert suspicion_module.chat_evidence_enabled() is True


def test_contributions_cover_only_scored_targets() -> None:
    belief = _belief()
    belief.society_trusted.add("green")
    belief.roster["red"].claims.append(_claim("green", "red", "kill"))
    belief.roster["blue"].life_status = "dead"
    contributions = chat_evidence_contributions(belief)
    assert contributions["red"] == pytest.approx(CHAT_KILL_LOG_LR)
    assert "blue" not in contributions and "orange" not in contributions
