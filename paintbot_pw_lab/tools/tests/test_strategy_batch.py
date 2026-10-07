"""Compact message evidence keeps payloads, ordering and physical byte accounting."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pw_intent
import strategy_audit
import strategy_comms as cm


@pytest.fixture
def mapping():
    return {
        "comms": {"version": 1, "keys": list(cm.DEFAULT_KEYS),
                  "messages": {str(i): f"COM.m{i}" for i in range(9)}},
        "codes": {"message": {f"COM.m{i}": i + 1 for i in range(9)},
                  "rule": {}, "capability": {}, "situation": {}, "knowledge": {}},
        "rules": [], "flag_words": 1,
        "components": {f"COM.m{i}": {"log_fields": [{"name": "packet", "cells": 2}]}
                       for i in range(9)},
    }


def batch(tick=1):
    messages = [cm.Message(0, seat, 0, 0, 123) for seat in range(0, 16, 2)]
    messages.append(cm.Message(2, 0, 24, 0, 456))
    records = [cm.batch_record(m, tick, 1 if i == 8 else 2) for i, m in enumerate(messages)]
    return f"PWC v=3 t={tick} b=" + "".join(records)


def test_expands_all_payloads(mapping):
    events = pw_intent.parse_telemetry_line(batch(), mapping)
    assert len(events) == 9
    assert [e["w"] for e in events] == list(range(0, 16, 2)) + [0]
    assert [e["s"] for e in events] == [2] * 8 + [1]
    for e in events:
        decoded = cm.unpack(*e["d"], 1 - (e["s"] == 2))
        assert decoded.sender == e["w"]
        assert decoded.kind + 1 == e["m"]


@pytest.mark.parametrize("change", [
    lambda s: s.replace("t=1", "t=-1"),
    lambda s: s.replace("t=1", "t=2147483648"),
    lambda s: s + "0",
    lambda s: s.replace("b=", "unexpected="),
    lambda s: s.replace("b=1", "b=3"),
])
def test_rejects_bad_batch(mapping, change):
    with pytest.raises(pw_intent.IntentError):
        pw_intent.parse_telemetry_line(change(batch()), mapping)


def test_rejects_unmapped_or_undeclared_codec(mapping):
    mapping["comms"]["messages"].pop("2")
    with pytest.raises(pw_intent.IntentError):
        pw_intent.parse_telemetry_line(batch(), mapping)
    mapping.pop("comms")
    with pytest.raises(pw_intent.IntentError):
        pw_intent.parse_telemetry_line(batch(), mapping)


def test_audit_restores_only_batch_logical_order(tmp_path, mapping):
    pwd = "PWD v=2 t=1 r=0 c=0 i=0,0,0 h=0 p=0 f=0"
    path = tmp_path / "player-0.log"
    path.write_text(pwd + "\n" + batch() + "\n")
    events, issues, _ = strategy_audit.read_log(tmp_path, 0, mapping)
    assert not issues
    assert [e["kind"] for e in events] == ["PWC"] * 9 + ["PWD"]
    assert [e["line"] for e in events] == [2] * 9 + [1]
    path.write_text(batch() + "\n" + pwd + "\n")
    _, issues, _ = strategy_audit.read_log(tmp_path, 0, mapping)
    assert "phase order" in issues[0]["detail"]
    path.write_text(batch() + "\n" + batch() + "\n")
    _, issues, _ = strategy_audit.read_log(tmp_path, 0, mapping)
    assert "duplicate compact batch" in issues[0]["detail"]


def test_g5_counts_physical_bytes_once(tmp_path, mapping):
    (tmp_path / "episode.meta.json").write_text(json.dumps({"a_side": 0}))
    pwd = "PWD v=2 t=1 r=0 c=0 i=0,0,0 h=0 p=0 f=0"
    text = pwd + "\n" + batch() + "\n"
    for seat in range(0, 16, 2):
        messages = [cm.Message(0, sender, 0, 0, 123) for sender in range(0, 16, 2) if sender != seat]
        messages.append(cm.Message(0, (seat + 2) % 16, 0, 0, 123))
        records = [cm.batch_record(m, 1, 2) for m in messages]
        records.append(cm.batch_record(cm.Message(2, seat, 24, 0, 456), 1, 1))
        seat_text = pwd + "\nPWC v=3 t=1 b=" + "".join(records) + "\n"
        (tmp_path / f"player-{seat}.log").write_text(seat_text)
    result = pw_intent.validate_v2_logs(tmp_path, mapping)
    assert all(s["peak_bytes"] == len(text.encode()) for s in result["seats"])
    assert all(s["lines"] == 2 and s["kinds"]["PWC"] == 9 for s in result["seats"])
    # Rare types remain explicitly unexercised; their absence is not a wire failure.
    assert result["passed"]
    assert "COM.m7" in result["coverage"]["unexercised_message_types"]


def test_transport_audit_matches_delivery_and_detects_missing_record():
    packet = cm.Message(0, 2, 0, 0, 123)
    a, b = cm.payloads(packet, 4)
    shout = {"t": 5, "seat": 2, "text": cm.encode(packet, 4), "heard_by": [0, 1]}
    event = {"kind": "PWC", "t": 5, "s": 2, "w": 2, "d": [a, b]}
    result = cm.audit_transport([shout], [event], 0, {5})
    assert result["status"] == "pass" and result["eligible_decode_rate"] == 1
    assert cm.audit_transport([shout], [], 0, {5})["status"] == "fail"
    # Delivery while alive at t-1 does not mean a dead cog runs a receiver at t.
    result = cm.audit_transport([shout], [], 0, set())
    assert result["status"] == "pass" and result["eligible_decode_rate"] is None


def test_transport_audit_reports_capacity_and_forged_identity():
    packet = cm.Message(0, 2, 0, 0, 123)
    a, b = cm.payloads(packet, 4)
    rows = [{"t": 5, "seat": 2, "text": cm.encode(packet, 4), "heard_by": [0]} for _ in range(9)]
    events = [{"kind": "PWC", "t": 5, "s": 2, "w": 2, "d": [a, b]} for _ in range(8)]
    result = cm.audit_transport(rows, events, 0, {5})
    assert result["status"] == "pass"
    assert result["counts"]["teammate_capacity_excluded"] == 1
    assert result["counts"]["eligible_teammate_deliveries"] == 8
    rows[0]["seat"] = 1
    result = cm.audit_transport(rows, events, 0, {5})
    assert result["counts"]["accepted_sender_claim_mismatch"] == 1


def test_transport_audit_send_offset_and_missing_actual_shout():
    packet = cm.Message(2, 0, 24, 0, 123)
    a, b = cm.payloads(packet, 4)
    row = {"t": 5, "seat": 0, "text": cm.encode(packet, 4), "heard_by": []}
    event = {"kind": "PWC", "t": 4, "s": 1, "w": 0, "d": [a, b]}
    assert cm.audit_transport([row], [event], 0, {4})["status"] == "pass"
    row["t"] = 4
    assert cm.audit_transport([row], [event], 0, {4})["status"] == "fail"
    assert cm.audit_transport([], [event], 0, {4})["status"] == "fail"


@pytest.mark.parametrize("direction,missing", [(1, "received"), (2, "sent")])
def test_g5_requires_both_transport_paths(tmp_path, mapping, direction, missing):
    (tmp_path / "episode.meta.json").write_text(json.dumps({"a_side": 0}))
    for seat in range(0, 16, 2):
        sender = seat if direction == 1 else (seat + 2) % 16
        record = cm.batch_record(cm.Message(0, sender, 0, 0, 123), 1, direction)
        (tmp_path / f"player-{seat}.log").write_text(
            "PWD v=2 t=1 r=0 c=0 i=0,0,0 h=0 p=0 f=0\nPWC v=3 t=1 b=" + record + "\n")
    result = pw_intent.validate_v2_logs(tmp_path, mapping)
    assert not result["passed"]
    assert any(missing + " path not exercised" in f["message"] for f in result["failures"])


def test_g5_still_requires_each_seat_unconditional_fields(tmp_path, mapping):
    test_g5_counts_physical_bytes_once(tmp_path, mapping)
    path = tmp_path / "player-0.log"
    path.write_text("\n".join(path.read_text().splitlines()[1:]) + "\n")
    result = pw_intent.validate_v2_logs(tmp_path, mapping)
    assert not result["passed"]
    assert any("PWD.t" in f.get("fields", []) for f in result["failures"])


def test_g5_rejects_wrong_outgoing_speaker(tmp_path, mapping):
    test_g5_counts_physical_bytes_once(tmp_path, mapping)
    text = (tmp_path / "player-2.log").read_text()
    (tmp_path / "player-0.log").write_text(text)
    result = pw_intent.validate_v2_logs(tmp_path, mapping)
    assert not result["passed"]
    assert any("speaker does not match" in f["message"] for f in result["failures"])
