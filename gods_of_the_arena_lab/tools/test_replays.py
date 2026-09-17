"""Run: uv run python -m unittest discover -s gods_of_the_arena_lab/tools -p test_replays.py.

Set GOTA_TEST_REPLAY and GOTA_TEST_EXPANDED for hosted tape/Layer A parity.
"""
import gzip
import json
import os
from pathlib import Path
import struct
import unittest

from replay_actions import ReplayError, decode, read_replay


def fixture():
    pack = lambda fmt, *args: struct.pack('<' + fmt, *args)
    name = b'gods_of_the_arena'
    data = b'POLYWORLDREPLAY' + pack('HHH', 1, 41, len(name)) + name
    data += pack('HHqiQHHII', 5, 41, 0, 2026, 1, 24, 116, 480, 1)
    data += pack('qiBBBB', 1, 100, 0, 0, 0, 5)
    data += pack('qq', 1, 3) + b'Bot'
    data += pack('iiiii', 2026, 1, 480, 0, 0)
    data += pack('qqqq9fB', 116, 54, 4, 32, *([1.] * 9), 1)
    data += pack('qIiB3xii', 1, 1, 100, 1, -4, 5)
    data += pack('qQ', 1, 123)
    data += pack('iiqiqiqi', 24, 24, 1, 1, 1, 42, 1, 42)
    return data


class DecoderTests(unittest.TestCase):
    def test_layout_padding_identity_and_cpu(self):
        tape = decode(fixture())
        self.assertEqual(tape.actions, [dict(type='action', tick=1, slot=0,
            hero_id=100, kind=1, args=[-4, 5], accepted=None, action_index=0)])
        self.assertEqual(tape.hashes, [123])
        self.assertEqual(tape.cpu[0]['values'], [42])
        self.assertEqual(tape.meta['players'], ['Bot'])
        self.assertFalse(tape.meta['hash_verified'])

    def test_gzip(self):
        self.assertEqual(decode(gzip.compress(fixture())), decode(fixture()))

    def test_truncation_and_trailing_data(self):
        for data in (fixture()[:-1], fixture() + b'x', b'no replay'):
            with self.subTest(size=len(data)), self.assertRaises(ReplayError):
                decode(data)

    def test_unknown_version_rejected(self):
        data = bytearray(fixture())
        struct.pack_into('<H', data, 17, 999)
        with self.assertRaises(ReplayError):
            decode(data)

    @unittest.skipUnless(os.environ.get('GOTA_TEST_REPLAY') and os.environ.get('GOTA_TEST_EXPANDED'),
                         'set hosted replay and Layer A JSONL paths for parity')
    def test_hosted_layer_a_action_parity(self):
        tape = read_replay(Path(os.environ['GOTA_TEST_REPLAY']))
        with Path(os.environ['GOTA_TEST_EXPANDED']).open() as source:
            rows = [r for line in source if (r := json.loads(line))['type'] == 'action']
        self.assertEqual(len(tape.actions), len(rows))
        for decoded, expanded in zip(tape.actions, rows):
            self.assertIsNone(decoded['accepted'])
            self.assertIsInstance(expanded['accepted'], bool)
            self.assertEqual({k: v for k, v in decoded.items() if k != 'accepted'},
                             {k: v for k, v in expanded.items() if k != 'accepted'})


class StatsTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def summary(self):
        heroes = []
        for slot, lh in enumerate([10, 10, 0, 0]):
            team = 'RedTeam' if slot < 2 else 'BlueTeam'
            heroes.append(dict(slot=slot, team=team, **{'class': slot}, policy_name='bot',
                last_hits=lh, hero_kills=0, building_kills=0, tower_kills=0, barracks_kills=0,
                tower_kills_min=0, tower_kills_max=0, barracks_kills_min=0, barracks_kills_max=0,
                deaths=0, assists=0, level=1, xp=25*lh, gold_earned=15*lh, banked_gold=150+15*lh))
        return dict(type='summary', verified=True, results_verified=True, ticks=2000,
                    attribution_complete=True, actions_enabled=False, outcome='time_limit', heroes=heroes)

    def test_rates_ties_and_empty_team_share(self):
        from replay_stats import ExpandedEpisode, episode_stats
        expanded = ExpandedEpisode(self.root/'expanded.jsonl', {}, self.summary(), False)
        report = episode_stats(self.root, expanded)
        red, _, blue, _ = report['seats']
        self.assertEqual(red['xp_per_1000_ticks'], 125)
        self.assertEqual(red['team_last_hit_share'], .5)
        self.assertEqual([r['rank_within_team'] for r in report['seats']], [1, 1, 1, 1])
        self.assertIsNone(blue['team_last_hit_share'])
        self.assertEqual(sum(t['last_hits'] for t in report['teams']), 20)

    def test_unknown_splits_do_not_erase_building_total(self):
        from replay_stats import ExpandedEpisode, episode_stats
        summary = self.summary()
        h = summary['heroes'][0]
        h.update(building_kills=1, tower_kills=None, barracks_kills=None,
                 tower_kills_max=1, barracks_kills_max=1, xp=h['xp']+100)
        summary['attribution_complete'] = False
        report = episode_stats(self.root, ExpandedEpisode(self.root/'x', {}, summary, False))
        red = next(t for t in report['teams'] if t['team']=='RedTeam')
        self.assertEqual(red['building_kills'], 1)
        self.assertIsNone(red['tower_kills'])
        self.assertFalse(report['attribution_complete'])

    def test_cache_reuse_invalidation_and_no_actions(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from replay_stats import expand_episode
        for name in ('replay.json', 'results.json', 'binary'):
            (self.root/name).write_text('input')
        def run(command, **kwargs):
            self.assertIn('--no-actions', command)
            Path(command[2]).write_text(json.dumps(dict(type='meta', tick=0))+'\n'+
                                       json.dumps(self.summary())+'\n')
            return SimpleNamespace(returncode=0, stderr='', stdout='')
        with patch('replay_stats.subprocess.run', side_effect=run) as mocked:
            first = expand_episode(self.root, self.root/'binary')
            second = expand_episode(self.root, self.root/'binary')
            self.assertFalse(first.cache_hit)
            self.assertTrue(second.cache_hit)
            self.assertEqual(mocked.call_count, 1)
            (self.root/'results.json').write_text('changed results')
            self.assertFalse(expand_episode(self.root, self.root/'binary').cache_hit)
            self.assertEqual(mocked.call_count, 2)
            (self.root/'expanded-replay.jsonl').write_text('truncated')
            self.assertFalse(expand_episode(self.root, self.root/'binary').cache_hit)
            self.assertEqual(mocked.call_count, 3)

    def test_failed_expansion_never_publishes_cache(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from replay_stats import expand_episode
        for name in ('replay.json', 'results.json', 'binary'):
            (self.root/name).write_text('input')
        with patch('replay_stats.subprocess.run', return_value=SimpleNamespace(
                returncode=1, stderr='hash mismatch', stdout='')):
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                expand_episode(self.root, self.root/'binary')
        self.assertFalse((self.root/'expanded-replay.jsonl').exists())
        self.assertFalse(list(self.root.glob('.expand-*')))
