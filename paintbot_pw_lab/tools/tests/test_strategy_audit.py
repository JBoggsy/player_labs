"""Adversarial evidence tests: a working instrument must also reject false claims."""
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pw_cli
import strategy_audit as audit
import strategy_audit_baseline as baseline
from strategy_audit_runtime import reconstruct, rule_ok
import strategy_format as sf


@pytest.fixture
def build():
    return audit.load_build(audit.BASELINE)


def tape(build, n=8, flags=0):
    _, _, mapping, strategy = build
    rule = 5
    cap = mapping['codes']['capability']['C.default_goal']
    events = [{'kind': 'PWP', 't': 0, 'a': 0, 'r': r.code, 'o': r.priority, 'n': r.priority, 'p': 0}
              for r in strategy.rules]
    events += [{'kind': 'PWE', 't': 0, 'c': cap, 'e': 1, 'k': 0}]
    events += [{'kind': 'PWD', 't': t, 'r': rule, 'c': cap, 'h': int(t > 0), 'p': 0,
                'i': [0, 0, 0], 'f': [flags]} for t in range(n) if t in (0, 1) or t % 24 == 0]
    events.sort(key=lambda e: e['t'])
    states = {(t, 0): {'hp': 3} for t in range(n + 1)}
    return mapping, strategy, events, states


def test_valid_change_log_expands_every_living_tick(build):
    m, s, events, states = tape(build)
    result = reconstruct(s, m, events, states, 0, 8)
    assert len(result['ticks']) == 8
    assert all(row['status'] == 'pass' for row in result['ticks'])
    assert result['windows'] == [{'start': 0, 'end': 8, 'capability': 3, 'end_reason': 'truncated'}]


def test_wrong_rule_and_held_flag_are_findings(build):
    m, s, events, states = tape(build, flags=1)
    rows = reconstruct(s, m, events, states, 0, 8)['ticks']
    assert rows[0]['expected_rule'] == 1
    assert rows[0]['status'] == 'fail'
    m, s, events, states = tape(build)
    next(e for e in events if e['kind'] == 'PWD')['h'] = 1
    assert not reconstruct(s, m, events, states, 0, 8)['ticks'][0]['selection_ok']


def test_roles_and_file_order_ties(build):
    _, _, _, strategy = build
    take, cover = strategy.rules[2:4]
    flags = {'S.has_target_heart': True}
    assert rule_ok(take, strategy, 0, flags)
    assert not rule_ok(cover, strategy, 0, flags)
    assert rule_ok(cover, strategy, 4, flags)
    from strategy_basic import reference_select, SelectState
    assert reference_select(SelectState(), [False, True, True], [0, 100, 100], 0,
                            strategy.commitment).rule == 1


def test_missing_heartbeat_never_passes(build):
    m, s, events, states = tape(build, n=50)
    events = [e for e in events if e['t'] < 2]
    result = reconstruct(s, m, events, states, 0, 50)
    assert any(i['reason'] == 'telemetry_gap' for i in result['issues'])
    assert all(r['status'] == 'unmeasurable' for r in result['ticks'] if r['t'] >= 25)


def test_death_ends_at_replay_tick_and_reports_at_respawn(build):
    m, s, events, states = tape(build, n=8)
    for t in (3, 4, 5):
        states[t, 0]['hp'] = 0
    events += [{'kind': 'PWE', 't': 6, 'c': 3, 'e': e, 'k': 0} for e in (5, 1)]
    events += [{'kind': 'PWD', 't': t, 'r': 5, 'c': 3, 'h': int(t == 7), 'p': 0,
                'i': [0, 0, 0], 'f': [0]} for t in (6, 7)]
    result = reconstruct(s, m, events, states, 0, 8)
    assert not result['issues']
    assert all(r['status'] == 'pass' for r in result['ticks'])
    assert result['windows'][0]['end'] == 3
    assert result['windows'][0]['end_reason'] == 'died'
    assert result['windows'][1]['start'] == 6


def test_preemption_windows(build):
    m, s, events, states = tape(build)
    events += [{'kind': 'PWE', 't': 4, 'c': c, 'e': e, 'k': 0} for c, e in ((3, 4), (5, 1))]
    events += [{'kind': 'PWD', 't': t, 'r': 1, 'c': 5, 'h': int(t == 5), 'p': 0,
                'i': [0, 0, 0], 'f': [1]} for t in (4, 5)]
    result = reconstruct(s, m, events, states, 0, 8)
    assert all(r['status'] == 'pass' for r in result['ticks'])
    assert result['windows'][0]['end'] == result['windows'][1]['start'] == 4


def test_same_tick_start_done(build):
    m, s, events, states = tape(build, n=1)
    s.components['C.default_goal'].conditions = (sf.Condition('finished', 'done', 1, 'fixture'),)
    events.append({'kind': 'PWE', 't': 0, 'c': 3, 'e': 2, 'k': 1})
    result = reconstruct(s, m, events, states, 0, 1)
    assert result['ticks'][0]['status'] == 'pass'
    assert result['windows'][0]['end'] == 1
    assert result['windows'][0]['end_reason'] == 'done'


def test_delayed_snapshots_use_source_defaults(build):
    m, s, events, states = tape(build)
    for e in events:
        if e['kind'] == 'PWP':
            e['t'] = e['r'] - 1
    assert all(r['status'] == 'pass' for r in reconstruct(s, m, events, states, 0, 8)['ticks'])


def test_status_never_passes_partial_coverage(build):
    evidence = audit.Evidence(build[2])
    key = next(iter(evidence.checks))
    evidence.add(key, 'fixture', 0, 0, 'pass')
    evidence.add(key, 'fixture', 0, 1, 'unmeasurable', 'missing')
    assert evidence.summaries([key])[0]['status'] == 'unmeasurable'
    evidence.add(key, 'fixture', 0, 2, 'fail')
    assert evidence.summaries([key])[0]['status'] == 'fail'


def test_check_binding_includes_prose_not_ordinal(build):
    check = build[2]['components']['K.contacts']['checks'][1]
    before = audit.binding('K.contacts', check)
    assert before != audit.binding('K.contacts', {**check, 'text': 'a different claim'})
    assert before == audit.binding('K.contacts', copy.deepcopy(check))


@pytest.mark.parametrize('belief,execution,complete,status', [
    (None, True, True, 'unmeasurable'), (True, None, True, 'unmeasurable'),
    (True, True, False, 'unmeasurable'), (False, True, True, 'not_exercised'),
    (True, True, True, 'measured')])
def test_conditional_result(belief, execution, complete, status):
    assert baseline.conditional_result(True, belief_correct=belief, execution_correct=execution,
                                       complete=complete)[0] == status


def test_disguised_ally_truth_and_tick_alignment():
    ep = SimpleNamespace(meta={'rules': 48})
    states = {(t, seat): {'x': seat * 100, 'z': 0, 'disguised': seat == 2} for t in (0, 1) for seat in (0, 2)}
    vis = {(0, 0): {2}, (1, 0): set()}
    passed, detail = baseline.contact_truth(ep, 0, 0, states, vis, 3, 100000)
    assert passed and detail['body_is_ally']
    assert baseline.contact_truth(ep, 0, 1, states, vis, 3, 100000)[0] is False
    assert baseline.contact_truth(ep, 0, 0, states, vis, -1, 100000)[1]['reason'] == 'no_target'


def test_identity_uses_hashes_not_basename(tmp_path, build):
    version = build[1]
    meta = tmp_path / 'episode.meta.json'
    values = {'engine_release': version['engine']['tag'], 'a_side': 1,
              'policies': {'A': {'sha256': version['policy_sha256']}, 'B': {'sha256': 'different'}}}
    meta.write_text(json.dumps(values))
    ep = SimpleNamespace(meta={'engine_release': version['engine']['tag'], 'mode': 'teams', 'seats': 16},
                         source=SimpleNamespace(kind='local', local_meta=meta))
    assert audit.candidate_seats(ep, version, []) == list(range(1, 16, 2))
    values['policies']['B']['sha256'] = version['policy_sha256']
    meta.write_text(json.dumps(values))
    assert audit.candidate_seats(ep, version, []) == list(range(16))
    values['policies'] = {}
    meta.write_text(json.dumps(values))
    with pytest.raises(ValueError, match='identity'):
        audit.candidate_seats(ep, version, [])


def test_log_errors_are_evidence(tmp_path, build):
    m = build[2]
    assert audit.read_log(tmp_path, 0, m)[1][0]['reason'] == 'missing_seat_log'
    (tmp_path / 'player-0.log').write_text('PWD v=2 corrupt\nBASIC error: broke\n')
    events, issues, _ = audit.read_log(tmp_path, 0, m)
    assert not events
    assert [i['reason'] for i in issues] == ['malformed_telemetry', 'seat_disabled']


def test_unknown_check_is_usage_error(build):
    with pytest.raises(pw_cli.UsageError):
        audit.select_checks(audit.Evidence(build[2]), 'unknown')
    selected = audit.select_checks(audit.Evidence(build[2]), 'K.contacts', 'True')
    assert selected == ['K.contacts.2']


def test_truncating_division_and_int32():
    assert baseline.div(-15, 8) == -1
    assert baseline.i32(2**31) == -2**31


def test_adaptation_priority_transition_and_version(build):
    m, s, events, states = tape(build)
    s.components['A.raise_default'] = sf.Component('A.raise_default', 'A', 1, {}, code=1,
        effect=sf.Effect('R.default_goal', '+=', 10, None))
    events.append({'kind': 'PWP', 't': 3, 'a': 1, 'r': 5, 'o': 100, 'n': 110, 'p': 1})
    events.append({'kind': 'PWD', 't': 3, 'r': 5, 'c': 3, 'h': 1, 'p': 1, 'i': [0, 0, 0], 'f': [0]})
    result = reconstruct(s, m, events, states, 0, 8)
    assert all(r['status'] == 'pass' for r in result['ticks'])
    events[-1]['p'] = 0
    assert not reconstruct(s, m, events, states, 0, 8)['ticks'][3]['priority_ok']


def test_wrong_snapshot_never_passes(build):
    m, s, events, states = tape(build)
    events[0]['n'] += 1
    assert reconstruct(s, m, events, states, 0, 8)['issues'][0]['reason'] == 'initial_priority_snapshot'


def test_mismatched_end_does_not_create_valid_window(build):
    m, s, events, states = tape(build)
    events.append({'kind': 'PWE', 't': 4, 'c': 1, 'e': 4, 'k': 0})
    result = reconstruct(s, m, events, states, 0, 8)
    assert result['windows'][0]['end_reason'] == 'event_mismatch'
    assert not result['ticks'][4]['events_ok']


def test_seat_wide_unknown_does_not_inflate_coverage(build):
    evidence = audit.Evidence(build[2])
    key = next(iter(evidence.checks))
    for t in range(100):
        evidence.add(key, 'one', 0, t, 'pass')
    evidence.add(key, 'two', 0, None, 'unmeasurable', 'missing_log')
    row = evidence.summaries([key])[0]
    assert row['coverage'] is None
    assert row['opportunities'] == 100 and row['unmeasurable_seats'] == 1
    assert row['status'] == 'unmeasurable'


class Episode(SimpleNamespace):
    def __getitem__(self, key):
        return self.tables[key]


def test_hosted_identity_requires_played_release_and_upload_receipt(build):
    v = build[1]
    ep = Episode(meta={'engine_release': v['engine']['tag'], 'mode': 'teams', 'seats': 16},
                 source=SimpleNamespace(kind='hosted'), tables={
                     'episodes': pd.DataFrame([{'coworld_version': '0.3.113'}]),
                     'seats': pd.DataFrame([{'seat': 0, 'policy_version_id': 'pv-123'}])})
    receipt = {'build_id': v['build_id'], 'policy_sha256': v['policy_sha256'], 'policy_version_id': 'pv-123'}
    with pytest.raises(ValueError, match='hosted episode release'):
        audit.candidate_seats(ep, v, [receipt])
    ep.tables['episodes'].loc[0, 'coworld_version'] = '0.3.89'
    assert audit.candidate_seats(ep, v, [receipt]) == [0]
    with pytest.raises(ValueError, match='identity'):
        audit.candidate_seats(ep, v, [])


def test_missing_belief_sample_and_no_interpolation(build):
    _, _, m, s = build
    evidence = audit.Evidence(m)
    evidence.checks = {k: v for k, v in evidence.checks.items() if k == 'K.contacts.1'}
    ep = Episode(episode_id='fixture', meta={'rules': 48}, tables={'visibility': pd.DataFrame()})
    runtime = {'ticks': [{'t': t, 'status': 'pass'} for t in range(3)]}
    baseline.audit_seat(ep, 0, {}, [], runtime, [], s, m, m, evidence)
    assert len(evidence.rows) == 1 and evidence.rows[0]['t'] == 1
    assert evidence.rows[0]['status'] == 'unmeasurable'


def test_edited_check_has_no_inherited_evaluator(build):
    _, _, m, s = build
    evidence = audit.Evidence(m)
    evidence.checks = {'K.contacts.1': evidence.checks['K.contacts.1']}
    evidence.checks['K.contacts.1']['binding'] = 'different prose'
    ep = Episode(episode_id='fixture', tables={'visibility': pd.DataFrame()})
    baseline.audit_seat(ep, 0, {}, [], {'ticks': []}, [], s, m, m, evidence)
    assert evidence.rows[0]['reason'] == 'no_evaluator_for_check_text_or_spec'


def test_empty_level_selection_is_usage_error(build):
    with pytest.raises(pw_cli.UsageError, match='no checks'):
        audit.select_checks(audit.Evidence(build[2]), 'K.self_motion', 'Result')


def test_tampered_build_rejected(tmp_path, monkeypatch, build):
    import shutil
    target = tmp_path / audit.BASELINE
    shutil.copytree(build[0], target)
    monkeypatch.setattr(audit.builds, 'BUILDS', tmp_path)
    (target / 'map.json').write_text('{}')
    with pytest.raises(pw_cli.UsageError, match='modified'):
        audit.load_build(audit.BASELINE)


def test_source_map_disagreement_rejected(monkeypatch, build):
    original = audit.builds.read
    def wrong(path):
        result = original(path)
        if path.name == 'map.json':
            result['rules'][0]['priority'] = 999
        return result
    monkeypatch.setattr(audit.builds, 'read', wrong)
    with pytest.raises(pw_cli.UsageError, match='disagrees'):
        audit.load_build(audit.BASELINE)


def test_source_hash_mismatch_rejected(monkeypatch, build):
    original = audit.builds.checked_build
    def wrong(path):
        result = original(path)
        result['source_hashes'][result['source_path']] = 'wrong'
        return result
    monkeypatch.setattr(audit.builds, 'checked_build', wrong)
    with pytest.raises(pw_cli.UsageError, match='source hash'):
        audit.load_build(audit.BASELINE)


def test_cli_unknown_check_and_missing_binary(monkeypatch, capsys, build):
    import pw_strategy
    assert pw_strategy.main(['audit', '.', '--build', audit.BASELINE, '--check', 'wrong', '--json']) == 2
    assert json.loads(capsys.readouterr().out)['ok'] is False
    monkeypatch.setattr(audit.pe, 'discover', lambda roots: [object()])
    def missing(*args):
        raise pw_cli.EnvironmentMissing('missing trace', 'paintbot_pw_lab/tools/build_tools.sh')
    monkeypatch.setattr(audit.pe, 'resolve_binary', missing)
    assert pw_strategy.main(['audit', '.', '--build', audit.BASELINE, '--json']) == 3
    assert json.loads(capsys.readouterr().out)['next']


def test_squad_avoid_memory_survives_death(build):
    comp = build[3].components['K.squad_target']
    params = {p.name: p.value for p in comp.params}
    states = {(t, 0): {'hp': 0 if 73 <= t < 100 else 3, 'x': 0, 'z': 0} for t in range(102)}
    hearts = [{'idx': 0, 'pos': [0, 0]}, {'idx': 1, 'pos': [1000, -1500]},
              {'idx': 2, 'pos': [2000, -1500]}]
    rows = [{'t': t, 'heart': h, 'owner': 0 if h == 0 else -1} for t in range(102) for h in range(3)]
    ep = Episode(meta={'hearts': hearts, 'homes': [[0, 0], [6400, 4000]]}, summary={'ticks': 102},
                 tables={'heart_states': pd.DataFrame(rows)})
    targets = baseline.squad_targets(ep, 0, states, params)
    assert targets[0] == 1
    assert targets[72] == 2
    assert 80 not in targets
    assert targets[100] == 2
    del states[50, 0]
    assert 72 not in baseline.squad_targets(ep, 0, states, params)
