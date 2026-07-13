"""Tests for the CTF event-warehouse helpers (parsing + slot re-keying)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import event_warehouse as w


def test_slot_team_seat_role():
    assert w._team_for_slot(0) == "red" and w._team_for_slot(1) == "blue"
    assert w._seat_for_slot(14) == 7 and w._seat_for_slot(15) == 7
    assert w._role_for_seat(0, 3) == "defender" and w._role_for_seat(3, 3) == "attacker"


def test_beacon_defender_count_by_version():
    assert w._beacon_defender_count("beacon", 4) == 5
    assert w._beacon_defender_count("beacon", 5) == 3
    assert w._beacon_defender_count("ctf-baseline-16", 4) is None


def test_decode_bytes_repr_log():
    # The fetcher sometimes stores logs as a Python bytes-repr string.
    raw = b"b'beacon: team=red url=ws://h/player?slot=2&x\\nCTF_DIAG objective {\"tick\":5,\"to\":\"steal\"}'"
    text = w._decode_log(raw)
    assert text.startswith("beacon:")
    assert "\n" in text  # real newline after unescape
    assert w._slot_from_log_header(text) == 2


def test_parse_trace_line_stderr_form():
    rec = w._parse_trace_line('CTF_DIAG snapshot {"tick":42,"role":"defender","i_carry":false}')
    assert rec == {"tick": 42, "name": "snapshot", "data": {"role": "defender", "i_carry": False}}


def test_parse_trace_line_structured_form():
    rec = w._parse_trace_line('{"kind":"trace","tick":7,"name":"engage","data":{"n_enemies":2}}')
    assert rec == {"tick": 7, "name": "engage", "data": {"n_enemies": 2}}


def test_parse_trace_line_ignores_noise():
    assert w._parse_trace_line("some random log line") is None
