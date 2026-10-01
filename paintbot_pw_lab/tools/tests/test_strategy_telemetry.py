"""The v2 parser rejects corrupted identities and missing measurement evidence."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pw_intent import IntentError, parse_v2_line, validate_v2_logs


@pytest.fixture
def mapping():
    return {'flag_words': 1, 'codes': {'rule': {'R.wait': 1}, 'capability': {'C.wait': 1},
            'situation': {'S.ready': 1}, 'knowledge': {'K.position': 1}, 'adaptation': {'A.push': 1},
            'condition': {'C.wait': {'done': 1}}, 'event': {'start': 1, 'done': 2, 'abort': 3},
            'message': {'COM.ping': 1}},
            'rules': [{'id': 'R.wait', 'code': 1, 'capability': 'C.wait'}],
            'components': {'K.position': {'log_fields': [{'name': 'x', 'cells': 1}],
                'checks': [{'reads': ['K.position.x']} ]},
                'COM.ping': {'log_fields': [{'name': 'payload', 'cells': 2}]}}}


@pytest.mark.parametrize('line', [
    'PWD v=2 t=0 r=1 c=1 i=0,-1,2 h=0 p=0 f=1',
    'PWP v=2 t=0 a=0 r=1 o=100 n=100 p=0',
    'PWE v=2 t=0 c=1 e=1 k=0',
    'PWB v=2 t=0 k=1 d=-2147483648',
    'PWC v=2 t=0 m=1 s=1 w=15 d=2,3',
])
def test_all_line_kinds_decode(line, mapping):
    assert parse_v2_line(line, mapping)['t'] == 0


@pytest.mark.parametrize('line', [
    'PWD v=1 t=0 r=1 c=1 i=0,0,0 h=0 p=0 f=0',
    'PWD v=2 t=0 r=1 c=0 i=0,0,0 h=0 p=0 f=0',
    'PWD v=2 t=0 r=1 c=1 i=0,0 h=0 p=0 f=0',
    'PWD v=2 t=0 r=1 c=1 i=0,0,0 h=2 p=0 f=0',
    'PWD v=2 t=0 r=1 c=1 i=0,0,0 h=0 p=0 f=2',
    'PWE v=2 t=0 c=1 e=1 k=-1',
    'PWB v=2 t=0 k=1 d=2147483648',
    'PWB v=2 t=0 k=1 d=1,2',
    'PWB v=2 t=0 k=1 k=1 d=2',
    'PWP v=2 t=0 a=99 r=1 o=100 n=50 p=1',
    'PWC v=2 t=0 m=1 s=1 w=16 d=2',
    'PWC v=2 t=0 m=1 s=1 w=0 d=2',
])
def test_corrupt_or_unmapped_values_fail(line, mapping):
    with pytest.raises(IntentError):
        parse_v2_line(line, mapping)


def test_empty_logs_are_unmeasurable(tmp_path, mapping):
    assert not validate_v2_logs(tmp_path, mapping)['passed']
    (tmp_path / 'episode.meta.json').write_text(json.dumps({'a_side': 0}))
    for seat in range(0, 16, 2):
        (tmp_path / f'player-{seat}.log').write_text('Completed\n')
    result = validate_v2_logs(tmp_path, mapping)
    assert not result['passed']
    assert len(result['failures']) == 8


def test_coverage_is_per_seat_not_union(tmp_path, mapping):
    (tmp_path / 'episode.meta.json').write_text(json.dumps({'a_side': 0}))
    for seat in range(0, 16, 2):
        (tmp_path / f'player-{seat}.log').write_text(
            'PWD v=2 t=0 r=1 c=1 i=0,0,0 h=0 p=0 f=0\nPWB v=2 t=0 k=1 d=25\n'
            'PWC v=2 t=0 m=1 s=1 w=0 d=2,3\n')
    assert validate_v2_logs(tmp_path, mapping)['passed']
    (tmp_path / 'player-14.log').write_text('PWD v=2 t=0 r=1 c=1 i=0,0,0 h=0 p=0 f=0\n')
    result = validate_v2_logs(tmp_path, mapping)
    assert not result['passed']
    assert result['failures'][0]['fields'] == ['COM.ping.payload', 'K.position.x']
