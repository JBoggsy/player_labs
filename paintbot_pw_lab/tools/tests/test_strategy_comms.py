"""Wire arithmetic qualification against the actual pinned BASIC engine."""
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import strategy_comms as cm

RUNTIME = Path(__file__).resolve().parents[2] / "strategy/compiler/runtime/comms.bas"


def vectors():
    limits = ((2303, 255), (255, 0), (24, 0), (143, 3), (720, 0),
              (255, 720), (4095, 0), (15, 255), (15, 0))
    for kind, (a, b) in enumerate(limits):
        for tick in (0, 9972, 9973, 30010, 30011, 2147483647):
            yield tick, cm.Message(kind, 15, a, b, 0 if kind in (3, 8) else 65535)


def test_catalogue_roundtrip_and_int32_bounds():
    for tick, message in vectors():
        text = cm.encode(message, tick)
        assert len(text) == 20 and text[0] == text[10] == "1"
        assert cm.decode(text, tick) == message
        a, b = cm.payloads(message, tick)
        assert 2_000_000_000 + a <= 2147483647
        assert a + cm.mask(tick, 0) <= 2147483647
        assert b + cm.mask(tick, 1) <= 2147483647


def test_random_roundtrip():
    rng = random.Random(1701)
    for _ in range(1000):
        m = cm.Message(0, rng.randrange(16), rng.randrange(2304),
                       rng.randrange(256), rng.randrange(65536))
        tick = rng.randrange(28800)
        assert cm.decode(cm.encode(m, tick), tick) == m


@pytest.mark.parametrize("text", ["", "1", "1" * 19, "1" * 21, "2" + "1" * 19,
                                  "1" * 10 + "2" + "1" * 9, "1" * 19 + "x",
                                  "1" + "０" * 9 + "1" * 10])
def test_malformed_wire(text):
    with pytest.raises(ValueError):
        cm.decode(text, 7)


def test_invalid_catalogue_and_stale_message():
    for message in (cm.Message(9, 0, 0, 0, 0), cm.Message(0, 16, 0, 0, 0),
                    cm.Message(0, 0, 2304, 0, 0), cm.Message(6, 0, 4096, 0, 0),
                    cm.Message(8, 0, 0, 0, 1), cm.Message(5, 0, 0, 721, 0)):
        with pytest.raises(ValueError):
            cm.encode(message, 0)
    text = cm.encode(cm.Message(0, 2, 100, 3, 400), 42)
    with pytest.raises(ValueError):
        cm.decode(text, 43)


def test_lossless_batch_order_and_capacity():
    received = [(2, cm.Message(i, i, 0, 0, 0)) for i in range(8)]
    outgoing = (1, cm.Message(8, 0, 1, 0, 0))
    batch = "".join(cm.batch_record(m, 72, direction) for direction, m in received + [outgoing])
    assert len(batch) == 180
    assert cm.decode_batch(batch, 72) == received + [outgoing]
    for invalid in (batch + batch[:20], batch[-20:] + batch[:20], batch[:-1], ""):
        with pytest.raises(ValueError):
            cm.decode_batch(invalid, 72)


def test_codec_in_pinned_basic_engine(tmp_path):
    import pw_cli
    import pw_intent
    try:
        pw_intent._handoff(pw_intent.pe.DEFAULT_TAG)
    except pw_cli.EnvironmentMissing:
        pytest.skip("build the pinned handoff engine")
    code = [RUNTIME.read_text(), "SUB st__decoded()", "END SUB"]
    code += [f"cm__keys({i}) = {k}" for i, k in enumerate(cm.DEFAULT_KEYS)]
    expected = []
    for index, (tick, m) in enumerate(vectors()):
        text = cm.encode(m, tick)
        expected.append((index, 1, m.kind, m.sender, m.fields_a, m.fields_b, m.cell))
        code += [f"IF worldTick = {index} THEN",
                 f"cm__encode({m.kind}, {m.sender}, {m.fields_a}, {m.fields_b}, {m.cell}, {tick})",
                 f'IF cm__block_a <> {text[:10]} OR cm__block_b <> {text[10:]} THEN',
                 "cm__ok = 0", "ELSE",
                 "test__h = strFromInt(cm__block_a)",
                 "test__h = strCatInt(test__h, cm__block_b)",
                 f"cm__decode(test__h, {tick})", "END IF",
                 'PRINT "CHECK "; worldTick; " "; cm__ok; " "; cm__type; " "; cm__speaker; " "; cm__fa; " "; cm__fb; " "; cm__cell',
                 "END IF"]
    index = len(expected)
    for text in ("", "1", "1" * 19, "1" * 21, "1" * 19 + "x"):
        code += [f"IF worldTick = {index} THEN",
                 f'cm__decode(strNew("{text}"), 7)',
                 'PRINT "BAD "; worldTick; " "; cm__ok', "END IF"]
        index += 1
    policy = tmp_path / "codec.bas"
    policy.write_text("\n".join(code) + "\n")
    pw_intent.record_episode(policy, policy, 5, 0, tmp_path / "record", ticks=index)
    log = (tmp_path / "record/player-0.log").read_text()
    assert "BASIC error" not in log and "disabled" not in log
    actual = [tuple(map(int, line.split()[1:])) for line in log.splitlines() if line.startswith("CHECK ")]
    assert actual == expected
    bad = [line for line in log.splitlines() if line.startswith("BAD ")]
    assert len(bad) == 5 and all(line.endswith(" 0") for line in bad)


def test_transport_arbitration_and_batch_in_engine(tmp_path):
    import pw_intent
    code = [RUNTIME.read_text(), "SUB st__decoded()", "END SUB"]
    code += [f"cm__keys({i}) = {k}" for i, k in enumerate(cm.DEFAULT_KEYS)]
    code += [
        "cm__max_decode = 8", "cm__min_gap = 6", "rt__pe = 0", "rt__pb = 0",
        "cm__receive()",
        "IF worldTick = 1 THEN", "cm__send(2, 24, 0, 123, 1)",
        "cm__send(8, 0, 0, 0, 1)", "END IF",
        "IF worldTick = 2 THEN", "cm__send(0, 0, 0, 123, 1)", "ELSE",
        "cm__send(0, 0, 0, 123, 0)", "END IF",
        "cm__flush()",
    ]
    policy = tmp_path / "transport.bas"
    policy.write_text("\n".join(code) + "\n")
    pw_intent.record_episode(policy, policy, 5, 0, tmp_path / "record", ticks=9)
    import pw_episodes as pe
    episode = pe.load_episode(pe.discover([tmp_path / "record"])[0],
                              options=pe.TraceOptions(state_every=1, vis_every=1))
    assert episode.summary["verified"]
    received = 0
    for seat in range(16):
        log = (tmp_path / f"record/player-{seat}.log").read_text()
        assert "BASIC error" not in log and "disabled" not in log
        sends = []
        logged_events = []
        for line in log.splitlines():
            if not line.startswith("PWC"):
                continue
            fields = dict(token.split("=", 1) for token in line.split()[1:])
            tick = int(fields["t"])
            events = cm.decode_batch(fields["b"], tick)
            assert len(events) <= 9
            for direction, message in events:
                a, b = cm.payloads(message, tick - (direction == 2))
                logged_events.append({"kind": "PWC", "t": tick, "s": direction,
                                      "w": message.sender, "d": [a, b]})
                assert message.sender % 2 == seat % 2
                if direction == 1:
                    assert message.sender == seat
                    sends.append((tick, message.kind))
                else:
                    assert message.sender != seat
                    received += 1
        assert sends == [(0, 0), (1, 2), (6, 0)]
        transport = cm.audit_transport(episode["shouts"].to_dict("records"), logged_events, seat, set(range(9)))
        assert transport["status"] == "pass", transport
        assert transport["eligible_decode_rate"] == 1
    assert received > 0


def test_telemetry_kill_switch_preserves_communication(tmp_path):
    import pw_episodes as pe
    import pw_intent
    code = [RUNTIME.read_text(), "SUB st__decoded()", "END SUB"]
    code += [f"cm__keys({i}) = {k}" for i, k in enumerate(cm.DEFAULT_KEYS)]
    code += ["telemetryOff = 1", "cm__max_decode = 8", "cm__min_gap = 6",
             "cm__receive()", "cm__send(0, 0, 0, 123, 0)", "cm__flush()"]
    policy = tmp_path / "silent.bas"
    policy.write_text("\n".join(code) + "\n")
    pw_intent.record_episode(policy, policy, 5, 0, tmp_path / "record", ticks=2)
    for seat in range(16):
        log = (tmp_path / f"record/player-{seat}.log").read_text()
        assert "PWC" not in log and "BASIC error" not in log and "disabled" not in log
    episode = pe.load_episode(pe.discover([tmp_path / "record"])[0])
    assert episode.summary["verified"] and len(episode["shouts"]) == 16


def test_transport_counts_bytes_not_characters_and_preserves_unknown_sends():
    msg = cm.Message(8, 2, 3, 0, 0)
    text = cm.encode(msg, 5)
    payload = list(cm.payloads(msg, 5))
    recv = {'kind': 'PWC', 't': 6, 's': 2, 'w': 2, 'd': payload}
    # Twenty characters, but 29 bytes: these must not consume the eight attempts.
    noise = {'t': 6, 'seat': 1, 'text': '1' + 'é' * 9 + '1' + 'x' * 9,
             'bytes': 29, 'heard_by': [4]}
    shout = {'t': 6, 'seat': 2, 'text': text, 'bytes': 20, 'heard_by': [4]}
    result = cm.audit_transport([noise] * 8 + [shout], [recv], 4, {6})
    assert result['status'] == 'pass'
    assert result['eligible_decode_rate'] == 1
    # A nondecimal ASCII shape does consume capacity.
    crowd = {**noise, 'text': '1' + 'x' * 9 + '1' + 'y' * 9, 'bytes': 20}
    result = cm.audit_transport([crowd] * 8 + [shout], [], 4, {6})
    assert result['status'] == 'pass'
    assert result['counts']['teammate_capacity_excluded'] == 1
    # A lossy export makes this receive tick unknown, not a false delivery failure.
    unknown = {**noise, 'text': 'bad', 'bytes': 20}
    result = cm.audit_transport([unknown, shout], [recv], 4, {6})
    assert result['status'] == 'unmeasurable'
    assert result['eligible_decode_rate'] is None
    assert result['issues'][0]['reason'] == 'unknown_message_shape'
    own = cm.Message(8, 4, 5, 0, 0)
    own_send = {'kind': 'PWC', 't': 6, 's': 1, 'w': 4, 'd': list(cm.payloads(own, 6))}
    result = cm.audit_transport([unknown, shout], [recv, own_send], 4, {6})
    assert result['status'] == 'fail'
    assert any(row['reason'] == 'send_mismatch' for row in result['failures'])
