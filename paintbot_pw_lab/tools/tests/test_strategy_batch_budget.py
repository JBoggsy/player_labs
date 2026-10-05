"""comms-v1 opt-in, exact telemetry bounds, the folded PWD print and the compact batch budget
(strategy_basic), checked against the runtime texts and, when the handoff engine is built, a real
recording."""
import re
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "tests"))
import strategy_basic as sb  # noqa: E402
import strategy_comms as sc  # noqa: E402
import strategy_format as sf  # noqa: E402
from test_strategy_basic import RUNTIME, TRIVIAL, TRIVIAL_UNITS, build, unit_errors, write_strategy  # noqa: E402

# TRIVIAL without capability inputs, so the PWD inputs fold to the literal 0,0,0.
NO_INPUTS = TRIVIAL.replace("- Inputs: hold\n", "").replace("(hold=`C.idle`.speed)", "")
NO_INPUT_UNITS = dict(TRIVIAL_UNITS, **{"C.idle": TRIVIAL_UNITS["C.idle"].replace("c_idle__in_hold", "c_idle__speed")})


def codec_com(cid, wire, directions):
    return f"""### {cid}
- Summary: Comms-v1 message {wire}.
- Spec: Send or receive comms-v1 wire type {wire}.
- Encoding: comms-v1 {wire} -- strategy/comms.md
- Directions: {directions}
- Outputs:
  - packet[2] -- decoded payload blocks A and B
  - last -- fieldsA of the last message
- Log: packet
- Checks:
  - Acted: the message appears in the replay. Reads: replay
- Status: specified (2026-10-05)
"""


def with_coms(text, *sections):
    return text.replace("## Strategy", "## Communication\n\n" + "\n".join(sections) + "\n## Strategy")


CODEC = with_coms(NO_INPUTS, codec_com("COM.sighting", 0, "both"), codec_com("COM.grenade", 2, "send"))
CODEC_UNITS = dict(NO_INPUT_UNITS, **{
    "COM.sighting": """SUB com_sighting__send()
  cm__send(0, selfId, 0, 0, 0)
END SUB

SUB com_sighting__recv()
  com_sighting__last = cm__fa
END SUB
""",
    "COM.grenade": """SUB com_grenade__send()
  IF worldTick MOD 48 = 0 THEN
    cm__send(2, 3, 0, 100, 0)
  END IF
END SUB
"""})
LEGACY_COM = """### COM.shout
- Summary: A literal shout.
- Spec: Shout "Hi" every 100 ticks.
- Encoding: literal text
- Directions: send
- Checks:
  - Acted: the shout appears in the replay. Reads: replay
- Status: specified (2026-10-05)
"""


def parse(tmp_path, text):
    return sf.parse_strategy(write_strategy(tmp_path, text))


def codes(diags):
    return {d.code for d in diags}


# ---------------------------------------------------------------- opt-in and map

def test_codec_opt_in_mapping_and_catalogue_rules(tmp_path):
    assert sb.comms_plan(parse(tmp_path / "legacy", NO_INPUTS)) == (None, [])
    plan, diags = sb.comms_plan(parse(tmp_path / "codec", CODEC))
    assert plan == {0: "COM.sighting", 2: "COM.grenade"} and not diags
    dup = with_coms(NO_INPUTS, codec_com("COM.a", 4, "send"), codec_com("COM.b", 4, "send"))
    assert "comms-duplicate" in codes(sb.comms_plan(parse(tmp_path / "dup", dup))[1])
    wide = with_coms(NO_INPUTS, codec_com("COM.a", 9, "send"))
    assert "comms-wire-type" in codes(sb.comms_plan(parse(tmp_path / "wide", wide))[1])
    mixed = with_coms(NO_INPUTS, codec_com("COM.a", 1, "send"), LEGACY_COM)
    assert "comms-mixed" in codes(sb.comms_plan(parse(tmp_path / "mixed", mixed))[1])
    nopacket = with_coms(NO_INPUTS, codec_com("COM.a", 1, "send").replace("- Log: packet\n", "- Log: last\n"))
    assert "comms-packet" in codes(sb.comms_plan(parse(tmp_path / "np", nopacket))[1])
    with pytest.raises(sb.BuildError):
        build(tmp_path / "build-mixed", mixed, dict(NO_INPUT_UNITS, **{"COM.a": "SUB com_a__send()\nEND SUB\n"}))


def test_codec_build_includes_runtime_and_map(tmp_path):
    _, out = build(tmp_path, CODEC, CODEC_UNITS)
    runtime = (RUNTIME / "comms.bas").read_text()
    assert out["units"]["runtime.comms"] == runtime
    policy = out["policy"]
    assert policy.index("' ==== runtime.lib ====") < policy.index("' ==== runtime.comms ====") \
        < policy.index("' ==== generated.tables ====")
    comms = out["map"]["comms"]
    assert comms["version"] == 1 and comms["keys"] == list(sc.DEFAULT_KEYS)
    assert comms["messages"] == {"0": "COM.sighting", "2": "COM.grenade"}
    assert comms["batch"]["header"] == "PWC v=3 t=" and comms["batch"]["receives"] == 8
    assert out["map"]["components"]["COM.sighting"]["log_fields"] == [{"name": "packet", "cells": 2}]
    assert set(out["map"]["runtime"]["files"]) == {"runtime.lib", "runtime.main", "runtime.comms"}
    tables = out["units"]["generated.tables"]
    for i, key in enumerate(sc.DEFAULT_KEYS):
        assert f"cm__keys({i}) = {key}" in tables
    assert "cm__max_decode = 8" in tables and "cm__min_gap = 6" in tables


def test_legacy_build_has_no_codec_references(tmp_path):
    _, out = build(tmp_path, NO_INPUTS, NO_INPUT_UNITS)
    assert "comms" not in out["map"] and "runtime.comms" not in out["units"]
    assert "cm__" not in out["policy"]
    assert "SUB st__flush()\nEND SUB" in out["units"]["generated.tables"]
    assert (RUNTIME / "main.bas").read_text().rstrip().endswith("rt__snapshot()\nst__flush()")


def test_generated_dispatch_order_and_packet_copies(tmp_path):
    _, out = build(tmp_path, CODEC, CODEC_UNITS)
    tables = out["units"]["generated.tables"]
    decoded = tables[tables.index("SUB st__decoded()"):tables.index("SUB st__knowledge()")]
    assert "IF cm__type = 0 THEN" in decoded and "com_sighting__packet(0) = cm__pa" in decoded
    assert "com_sighting__recv()" in decoded and "com_grenade__recv" not in decoded  # send-only
    send = tables[tables.index("SUB st__send()"):tables.index("SUB st__beliefs()")]
    assert send.index("com_grenade__send()") < send.index("com_sighting__send()")  # G (2) outranks E (0)
    assert send.count("IF cm__sent = 0 THEN") == 2 and "com_grenade__sent = cm__sent" in send
    receive = tables[tables.index("SUB st__receive()"):tables.index("SUB st__decoded()")]
    assert receive.index("com_sighting__got = 0") < receive.index("cm__receive()")
    assert "cm__flush()" in tables[tables.index("SUB st__flush()"):]


def test_codec_unit_permissions(tmp_path):
    strategy = parse(tmp_path / "codec", CODEC)
    ok = "SUB com_grenade__send()\n  com_grenade__x = cm__fa + cm__heard_t(3)\n  cm__send(2, 0, 0, 0, 0)\nEND SUB\n"
    assert unit_errors(strategy, "COM.grenade", ok) == set()
    assert "unit-namespace" in unit_errors(strategy, "COM.grenade",
                                           "SUB com_grenade__send()\n  cm__sent = 1\nEND SUB\n")
    assert "unit-namespace" in unit_errors(strategy, "COM.grenade",
                                           "SUB com_grenade__send()\n  com_grenade__packet(0) = 1\nEND SUB\n")
    legacy = parse(tmp_path / "legacy", with_coms(NO_INPUTS, LEGACY_COM))
    bad = "SUB com_shout__send()\n  com_shout__sent = cm__fa\nEND SUB\n"
    assert "unit-namespace" in unit_errors(legacy, "COM.shout", bad)


# ---------------------------------------------------------------- exact bounds

def render(items, worst=True):
    """The text PRINT writes for these items, with each value at its bound (worst) or 0."""
    return "".join(item[1] if item[0] == "lit" else ("9" * item[2] if worst else "0") for item in items) + "\n"


def test_folded_pwd_prints_the_v2_text(tmp_path):
    strategy = parse(tmp_path, NO_INPUTS)
    items = sb.pwd_items(strategy)
    assert sb._print_statement(items) == ('PRINT "PWD v=2 t="; worldTick; " r="; rt__rule; " c="; rt__cap; '
                                          '" i=0,0,0 h="; rt__held; " p=0 f="; rt__fw(0)')
    # The unfolded v2 statement with zero inputs and version prints the same characters.
    legacy = 'PWD v=2 t={t} r={r} c={c} i={a},{b},{d} h={h} p={p} f={f}\n'
    assert render(items, worst=False) == legacy.format(t=0, r=0, c=0, a=0, b=0, d=0, h=0, p=0, f=0)
    events, nbytes = sb.line_cost(items)
    assert (events, nbytes) == (11, len(render(items))) == (11, 50)
    _, out = build(tmp_path / "b", NO_INPUTS, NO_INPUT_UNITS)
    tables = out["units"]["generated.tables"]
    assert sb._print_statement(items) in tables and "rt__pe = rt__pe + 11" in tables and "rt__pb = rt__pb + 50" in tables
    assert 'PRINT "PWD' not in (RUNTIME / "lib.bas").read_text()


def test_unfolded_when_inputs_or_adaptations_exist(tmp_path):
    items = sb.pwd_items(parse(tmp_path, TRIVIAL))  # C.idle has an input
    statement = sb._print_statement(items)
    assert "rt__in0" in statement and '" p=0 f="' in statement
    assert sb.line_cost(items) == (17, len(render(items)))


def test_runtime_line_bounds_match_lib(tmp_path):
    strategy = parse(tmp_path, NO_INPUTS)
    lib = (RUNTIME / "lib.bas").read_text()
    # PWE as runtime.lib prints it: every item is a literal or one of t, c, k.
    assert 'PRINT "PWE v=2 t="; worldTick; " c="; rt__pwe_c; " e=1 k=0"' in lib
    assert 'PRINT "PWE v=2 t="; worldTick; " c="; rt__end_c; " e=2 k="; rt__end_k' in lib
    plain, end = sb.pwe_costs(strategy)
    assert plain == (6, len("PWE v=2 t=") + 11 + len(" c=") + 1 + len(" e=1 k=0") + 1)
    assert end == (7, len("PWE v=2 t=") + 11 + len(" c=") + 1 + len(" e=2 k=") + 2 + 1)  # k may be -1


def test_batch_capacity_matches_runtime_reservation():
    assert sb.batch_cost() == (22, 205)
    comms = (RUNTIME / "comms.bas").read_text()
    head = re.search(r"IF cm__batch_count = 0 THEN\s+rt__pe = rt__pe \+ (\d+)\s+rt__pb = rt__pb \+ (\d+)", comms)
    record = re.search(r"END IF\s+rt__pe = rt__pe \+ (\d+)\s+rt__pb = rt__pb \+ (\d+)\s+cm__batch_a", comms)
    records = sb.BATCH_RECEIVES + sb.BATCH_SENDS
    assert (int(head[1]) + records * int(record[1]), int(head[2]) + records * int(record[2])) == sb.batch_cost()
    assert f'PRINT "{sb.BATCH_HEADER}"; worldTick; "{sb.BATCH_SEPARATOR}";' in comms
    assert "DIM cm__batch_a(8)" in comms and "DIM cm__batch_b(8)" in comms   # 9 records


def test_codec_worst_case_fits_half_limits(tmp_path):
    worst = sb.telemetry_worst_case(parse(tmp_path, CODEC))
    assert worst["lines"]["PWC"] == {"count": 1, "events": 22, "bytes": 205, "batch": True}
    assert worst["events"] == 11 + 19 + 7 + 22 == 59 and worst["bytes"] == 50 + 103 + 52 + 205 == 410
    assert worst["events"] <= 64 and worst["bytes"] <= 512


# ---------------------------------------------------------------- engine

def test_codec_batch_in_engine(tmp_path):
    import pw_cli
    import pw_intent
    try:
        pw_intent._handoff(pw_intent.pe.DEFAULT_TAG)
    except pw_cli.EnvironmentMissing:
        pytest.skip("handoff engine not built (paintbot_pw_lab/tools/build_tools.sh)")
    strategy, out = build(tmp_path / "src", CODEC, CODEC_UNITS)
    policy = tmp_path / "policy.bas"
    policy.write_text(out["policy"])
    pw_intent.record_episode(policy, policy, 5, 0, tmp_path / "rec", ticks=120)
    worst = out["budget"]["telemetry"]
    receives = sends = 0
    for seat in (0, 1):
        text = (tmp_path / "rec" / f"player-{seat}.log").read_text()
        assert "BASIC error" not in text
        per_tick: dict[int, int] = {}
        for line in text.splitlines():
            if not line.startswith("PW"):
                continue
            tick = int(re.search(r" t=(-?\d+)", line)[1])
            per_tick[tick] = per_tick.get(tick, 0) + len(line) + 1
            if line.startswith("PWD"):
                assert re.fullmatch(r"PWD v=2 t=\d+ r=\d c=\d i=0,0,0 h=[01] p=0 f=\d+", line), line
                pw_intent.parse_v2_line(line, out["map"])
            if line.startswith("PWC v=3"):
                header, records = line.split(" b=")
                assert len(line) + 1 <= sb.batch_cost()[1]
                for direction, message in sc.decode_batch(records, tick):
                    if direction == 1:
                        sends += 1
                        assert message.sender == seat
                    else:
                        receives += 1
                        assert message.sender % 2 == seat % 2 and message.sender != seat
        assert max(per_tick.values()) <= 512
        snapshot_ticks = {int(m[1]) for m in re.finditer(r"PWP v=2 t=(\d+) a=0", text)}
        assert all(n <= worst["bytes"] for t, n in per_tick.items() if t not in snapshot_ticks)
    assert sends > 0 and receives > 0
