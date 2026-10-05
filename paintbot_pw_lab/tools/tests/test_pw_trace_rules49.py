"""Exercise rules49 replay changes through the actual engine and trace binary."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import pw_episodes as pe
import pw_terrain

TAG = 'coworld-v0.3.115'
BIN = TOOLS / 'bin' / TAG
pytestmark = pytest.mark.skipif(not (BIN / 'pw_trace').exists(), reason='rules49 tools not built')


@pytest.mark.parametrize("explode_tick", [0, 1000])
def test_self_destruct_is_not_a_grenade_and_commands_survive(tmp_path, explode_tick):
    policy = tmp_path / 'self.bas'
    policy.write_text(f'walkTo(3200, 2000)\nIF worldTick = {explode_tick} THEN\nselfDestruct()\nEND IF\nEND\n')
    replay = tmp_path / 'self.replay'
    subprocess.run([str(BIN / 'paintbot-headless'), '--bot', f'{policy}:16',
                    '--seed', '7', '--ticks', str(explode_tick + 2), '--record', str(replay)],
                   check=True, capture_output=True)
    assert pe.tape_header(replay.read_bytes())['rules'] == 49
    trace = tmp_path / 'trace.jsonl'
    with pw_terrain.session(TAG) as directory:
        subprocess.run([str(BIN / 'pw_trace'), str(replay), str(trace), '--state-every', '1'],
                       env=pw_terrain.env(directory), check=True, capture_output=True)
    rows = [json.loads(line) for line in trace.read_text().splitlines()]
    assert rows[-1]['verified']
    meta = rows[0]
    assert meta['schema_version'] == 2
    assert {'cmd_self_destruct', 'sniper', 'radar_until', 'mister_until'} <= set(meta['state_columns'])
    events = [r for r in rows if r['type'] == 'event']
    kills = [r for r in events if r['kind'] == 'kill']
    assert len(kills) == 16
    assert all(r['weapon'] == 'self_destruct' for r in kills)
    assert not any(r['kind'] == 'grenade_blast' for r in events)
    blasts = [r for r in events if r['kind'] == 'self_destruct']
    assert blasts
    if explode_tick:
        # Earlier bombers kill later would-be bombers, which must not explode.
        assert len(blasts) < 16
        assert any(not r['self'] and not r['friendly'] for r in kills)
        assert len({r['seat'] for r in blasts}) == len(blasts)
    states = [r for r in rows if r['type'] == 'state']
    col = meta['state_columns'].index('cmd_self_destruct')
    assert all(s[col] is None for s in states[0]['seats'])
    assert all(s[col] == 1 for s in states[-1]['seats'])
