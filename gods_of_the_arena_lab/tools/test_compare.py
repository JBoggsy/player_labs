"""Objective-metric checks: uv run python -m unittest discover -s gods_of_the_arena_lab/tools -p test_compare.py."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from compare import seat_value, value_fn, metrics_for
from gota_episodes import EpisodeRecord, Seat, SEAT_CLASSES, team_of_seat, load_batch


def episode(xp, winning_team='red'):
    record = EpisodeRecord('episode', Path('.'), 'completed', False, True,
                           'RedTeam' if winning_team == 'red' else 'BlueTeam', 1000, 1, 'test')
    record.seats = [Seat('episode', position, SEAT_CLASSES[position], team_of_seat(position),
                         'subject' if position == 0 else 'opponent', 13, str(position), None,
                         team_of_seat(position) == winning_team, value, None, False, None, None)
                    for position, value in enumerate(xp)]
    return record


class TeamObjectiveTests(unittest.TestCase):
    def test_single_seat_binary_outcomes_use_rate_tests(self):
        single = {key: kind for key, _, kind, _ in metrics_for('all', True)}
        multiple = {key: kind for key, _, kind, _ in metrics_for('all')}
        self.assertEqual(single['win_team_xp_lead_rate'], 'rate')
        self.assertEqual(multiple['win_team_xp_lead_rate'], 'mean')

    def test_win_and_strict_team_lead_ignore_enemy_xp(self):
        record = episode([600, 500, 400, 300, 200, 900, 800, 700, 600, 500])
        seat = record.seats[0]
        self.assertEqual(seat_value(seat, record, 'win_team_xp_lead_rate'), 1)
        self.assertEqual(seat_value(seat, record, 'team_xp_margin'), 100)
        self.assertEqual(seat_value(seat, record, 'team_xp_rank'), 1)
        seat.won = False
        self.assertEqual(seat_value(seat, record, 'win_team_xp_lead_rate'), 0)
        self.assertEqual(seat_value(seat, record, 'team_xp_lead_rate'), 1)
        self.assertEqual(seat_value(seat, record, 'winning_xp_mean'), 0)

    def test_tie_is_not_a_strict_lead(self):
        record = episode([500, 500, 400, 300, 200] + [0] * 5)
        self.assertEqual(seat_value(record.seats[0], record, 'win_team_xp_lead_rate'), 0)
        self.assertEqual(seat_value(record.seats[0], record, 'team_xp_rank'), 1)

    def test_missing_and_duplicate_teammates_are_not_zeroes(self):
        record = episode([600, None, 400, 300, 200] + [0] * 5)
        self.assertIsNone(seat_value(record.seats[0], record, 'team_xp_margin'))
        record.seats[1] = record.seats[2]
        self.assertIsNone(seat_value(record.seats[0], record, 'team_xp_lead_rate'))

    def test_one_observation_per_episode(self):
        record = episode([600, 500, 400, 300, 200] + [0] * 5)
        values = value_fn([(record.seats[:2], record)], 'win_team_xp_lead_rate')
        self.assertEqual(values, [0.5])

    def test_exact_join_uses_position_not_row_order_and_rejects_stale_xp(self):
        record = episode([600, 500, 400, 300, 200] + [0] * 5)
        rows = [dict(slot=s.position, xp=s.total_xp, win=int(s.won), policy_name=s.policy_name,
                     last_hits=10+s.position, hero_kills=s.position, building_kills=0, deaths=2)
                for s in reversed(record.seats)]
        report = dict(episodes=[dict(episode_id='episode', verified=True, ticks=1000,
                                    outcome='RedTeam', seats=rows)], errors=[])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'episode.json').write_text('{}')
            stats = root/'stats.json'
            stats.write_text(json.dumps(report))
            with patch('gota_episodes.load_episode', return_value=record):
                records, excluded = load_batch(root, stats)
                self.assertEqual(records[0].seats[0].combat.last_hits, 10)
                self.assertEqual(records[0].seats[9].combat.hero_kills, 9)
                self.assertEqual(excluded['missing_exact_replay'], 0)
                rows[0]['xp'] += 1
                stats.write_text(json.dumps(report))
                with self.assertRaisesRegex(ValueError, 'mismatch'):
                    load_batch(root, stats)


if __name__ == '__main__':
    unittest.main()
