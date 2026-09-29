"""PWI intent line contract: the BASIC module and the parser must agree, and nothing is dropped."""
import json
import re
import sys
from pathlib import Path

import pandas as pd
import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import pw_intent  # noqa: E402

MODULE = TOOLS.parent / "reference" / "intent_telemetry.bas"


def test_parse_line_types_every_field():
    row = pw_intent.parse_line("PWI v=1 t=2453 m=5 h=-1 s=11 r=7 e=3 c=0")
    assert row == {"version": 1, "t": 2453, "mode": 5, "heart": -1, "target": 11, "reason": 7,
                   "seen": 3, "changed": 0}


@pytest.mark.parametrize("line, message", [
    ("PWI v=1 t=5 m=1 h=2 s=-1 r=1 e=0", "missing keys"),
    ("PWI v=2 t=5 m=1 h=2 s=-1 r=1 e=0 c=1", "version"),
    ("PWI v=1 t=x m=1 h=2 s=-1 r=1 e=0 c=1", "not an integer"),
    ("PWI v=1 t=5 m=1 h=2 s=-1 r=1 e=0 c=2", "0/1"),
    ("hello", "not a PWI line"),
])
def test_parse_line_rejects_malformed(line, message):
    with pytest.raises(pw_intent.IntentError, match=message):
        pw_intent.parse_line(line)


def test_reference_module_prints_exactly_the_parsed_keys():
    source = MODULE.read_text()
    prints = [line for line in source.splitlines() if line.strip().startswith("print ")]
    assert len(prints) == 1, "the module must print one line per decision"
    literals = "".join(re.findall(r'"([^"]*)"', prints[0]))
    keys = re.findall(r"(\w)=", literals)
    assert keys == list(pw_intent.FIELDS), "print keys and pw_intent.FIELDS must match, in order"
    assert '"PWI v=1 t="' in prints[0] and pw_intent.INTENT_VERSION == 1


def test_reference_module_mode_table_matches_parser():
    table = dict(re.findall(r"^'\s+(\d) (\w+)\s{2,}", MODULE.read_text(), re.MULTILINE))
    assert {int(k): v for k, v in table.items()} == pw_intent.MODE_NAMES


class FakeEpisode:
    episode_id = "local:test"

    def __init__(self, log_rows):
        self.tables = {
            "policy_log": pd.DataFrame(log_rows, columns=["episode_id", "seat", "t", "line_kind", "raw", "fields", "file", "line_no"]),
            "seats": pd.DataFrame({"seat": [0, 1], "policy_key": ["local:a.bas", "local:b.bas"]}),
        }

    def __getitem__(self, name):
        return self.tables[name]


def log_row(seat, kind, line="", line_no=1):
    fields = {}
    if kind == "intent":
        fields = dict(item.split("=", 1) for item in line[4:].split() if "=" in item)
    return {"episode_id": "local:test", "seat": seat, "t": None, "line_kind": kind, "raw": line,
            "fields": json.dumps(fields), "file": f"player-{seat}.log", "line_no": line_no}


def test_intents_keep_malformed_lines_and_summary_separates_no_log_from_no_lines():
    ep = FakeEpisode([
        log_row(0, "log_present", line_no=0),
        log_row(0, "intent", "PWI v=1 t=0 m=1 h=4 s=-1 r=1 e=0 c=1", 2),
        log_row(0, "intent", "PWI v=1 t=24 m=1 h=6 s=-1 r=1 e=0 c=1", 3),
        log_row(0, "intent", "PWI v=1 t=30 m=9", 4),
        log_row(0, "vm_error", "BASIC error: BASIC print byte limit exceeded", 5),
    ])
    frame = pw_intent.intents(ep)
    assert len(frame) == 3
    assert frame["parse_error"].notna().sum() == 1
    assert list(frame.loc[frame["parse_error"].isna(), "heart"]) == [4, 6]
    summary = pw_intent.intent_summary(ep, frame)
    # Seat 1 has no log: absent (unknown), not a row of zeros.
    assert list(summary["seat"]) == [0]
    row = summary.iloc[0]
    assert (row["intent_lines"], row["bad_lines"], row["vm_errors"], row["heart_switches"]) == (2, 1, 1, 1)
    assert row["mode_share_heart"] == 1.0


# ---------------------------------------------------------------- audit: disguise and tick alignment

def test_observed_view_mirrors_body_for_seat():
    positions = {0: (0, 0), 1: (100, 0), 2: (500, 0), 3: (300, 0), 5: (900, 0)}
    # Body 3 (team 1) is disguised: it answers to 2, a team-0 seat. Body 2 is also visible and
    # farther away, so identity 2 resolves to the nearer body 3, as bots.nim bodyForSeat does.
    view = pw_intent.observed_view(0, {1, 2, 3, 5}, {1: False, 2: False, 3: True, 5: False}, positions, 16)
    assert view == {1: 1, 2: 3, 5: 5}
    # A disguise that would land on the observer's own seat moves on by two seats.
    view = pw_intent.observed_view(0, {1}, {1: True}, positions, 16)
    assert view == {2: 1}
    # Before rules 27 a uniform changes nothing.
    assert pw_intent.observed_view(0, {3}, {3: True}, positions, 16, disguise_rules=False) == {3: 3}


class AuditEpisode:
    """Seat 1 (team 1) at the origin; seats 3 (its teammate), 2 and 4 (enemies) around it."""
    episode_id = "local:audit"

    def __init__(self, lines, sees, disguised, dead=()):
        ticks = sorted({t for t, _ in sees} | {t for t, _ in disguised})
        positions = {1: (0, 0), 2: (1000, 0), 3: (400, 0), 4: (0, 800)}
        states = [{"t": t, "seat": s, "x": x, "z": z, "hp": 0 if (t, s) in dead else 3,
                   "alive": (t, s) not in dead, "disguised": (t, s) in disguised}
                  for t in ticks for s, (x, z) in positions.items()]
        self.tables = {
            "policy_log": pd.DataFrame([log_row(1, "log_present", line_no=0)] +
                                       [log_row(1, "intent", line, i + 1) for i, line in enumerate(lines)]),
            "seats": pd.DataFrame({"seat": [1, 2, 3, 4], "team": [1, 0, 1, 0], "policy_key": ["local:a.bas"] * 4}),
            "states": pd.DataFrame(states),
            "visibility": pd.DataFrame([{"t": t, "seat": seat, "sees": sorted(bodies)} for (t, seat), bodies in sees.items()]),
            "episodes": pd.DataFrame({"rules": [48]}),
        }
        self.meta = {"hearts": [{"idx": 0, "pos": [5000, 5000]}]}

    def __getitem__(self, name):
        return self.tables[name]


def _divergent(ep) -> dict:
    divergences, checks = pw_intent.audit(ep)
    return dict(zip(checks["rule"], checks["divergent"]))


def test_audit_models_disguise_as_belief_not_as_inconsistency():
    # t=10: teammate 3 is disguised (answers to 2, an enemy seat) and enemy 4 is in view.
    # The policy, reading BASIC, sees two "enemies" (2 and 4) and targets 2: consistent with
    # its view (no consistency divergence) but fooled by the disguise (target_is_ally, seen_fooled).
    ep = AuditEpisode(["PWI v=1 t=10 m=5 h=-1 s=2 r=0 e=2 c=1"], sees={(10, 1): {3, 4}}, disguised={(10, 3)})
    found = _divergent(ep)
    assert (found["target_not_visible"], found["target_dead"], found["seen_mismatch"]) == (0, 0, 0)
    assert (found["target_is_ally"], found["seen_fooled"]) == (1, 1)


def test_audit_joins_a_line_to_the_world_at_its_own_tick():
    # The world at t=10 (what the policy decided from) shows enemy 2; by t=11 it has gone out of view.
    # Joined at t the line is consistent; a t+1 join would call the target invisible.
    ep = AuditEpisode(["PWI v=1 t=10 m=5 h=-1 s=2 r=0 e=1 c=1"],
                      sees={(10, 1): {2}, (11, 1): set()}, disguised=set())
    assert sum(_divergent(ep).values()) == 0
    shifted = pw_intent.intents(ep)
    shifted["t"] = shifted["t"] + 1
    divergences, _ = pw_intent.audit(ep, shifted)
    assert set(divergences["rule"]) == {"target_not_visible", "seen_mismatch"}


def test_audit_flags_a_stale_target_and_a_miscount():
    # Enemy 2 is dead and out of view at t=10, yet the policy still names it and counts one enemy.
    ep = AuditEpisode(["PWI v=1 t=10 m=6 h=-1 s=2 r=0 e=1 c=1"], sees={(10, 1): {3}}, disguised=set(),
                      dead={(10, 2)})
    found = _divergent(ep)
    assert (found["target_not_visible"], found["target_dead"], found["seen_mismatch"]) == (1, 1, 1)
    assert (found["target_is_ally"], found["seen_fooled"]) == (0, 0)


# ---------------------------------------------------------------- CLI contract

def _envelope(capsys):
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 1, "--json prints exactly one line to stdout"
    return json.loads(out[0])


def test_cli_unknown_side_is_a_usage_error_listing_valid_values(tmp_path, capsys):
    a = tmp_path / "a.bas"
    a.write_text("x = 1\n")
    code = pw_intent.main(["record", str(a), str(a), "--sides", "2", "--json"])
    envelope = _envelope(capsys)
    assert code == 2 and envelope["ok"] is False and envelope["tool"] == "pw_intent"
    assert envelope["result"]["valid"] == ["0", "1", "0,1"]
    assert set(envelope) >= {"release_tag", "inputs", "outputs", "counts", "failures", "next"}


def test_cli_missing_build_is_exit_3_naming_the_fix(tmp_path, capsys):
    code = pw_intent.main(["audit", str(tmp_path), "--tag", "coworld-v0.0.0", "--json"])
    envelope = _envelope(capsys)
    assert code == 3
    assert envelope["next"] == ["paintbot_pw_lab/tools/build_tools.sh coworld-v0.0.0"]


def test_cli_missing_root_is_a_usage_error(tmp_path, capsys):
    assert pw_intent.main(["show", str(tmp_path / "nope"), "--json"]) == 2
    assert "no such episode root" in _envelope(capsys)["failures"][0]["message"]
