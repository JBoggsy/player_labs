"""Focused instrument checks: uv run python -m unittest discover -s gods_of_the_arena_lab/tools/lasthit_eval."""

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lasthit_eval
from lasthit_eval import Telemetry, mean_field, parse_episode, report


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'logs').mkdir()
        (self.root / 'results.json').write_text(json.dumps({
            'total_xp': [300] * 10, 'outcome': 'RedTeam', 'ticks': 28800, 'seed': 2026,
        }))
        (self.root / 'player_status.json').write_text(json.dumps({
            'players': [{'slot': seat, 'reason': 'Completed'} for seat in range(10)],
        }))
        for seat in range(10):
            (self.root / f'logs/policy_agent_{seat}.log').write_text('')

    def parse(self):
        return parse_episode(self.root, True, Path('candidate.bas'), Path('base.bas'))

    def test_xp_only_identity_and_outcome_counts(self):
        rows = self.parse()
        self.assertEqual([row.hero_class for row in rows], [5, 6, 7, 8, 9, 0, 1, 2, 3, 4])
        self.assertTrue(all(row.telemetry is None and row.xp_matches is None for row in rows))
        self.assertEqual(rows[0].policy, 'candidate')
        self.assertEqual(rows[5].policy, 'reference')
        swapped = parse_episode(self.root, False, Path('candidate.bas'), Path('base.bas'))
        self.assertEqual(swapped[0].policy, 'reference')
        self.assertEqual(swapped[5].policy, 'candidate')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            report(rows)
        self.assertIn('win=1, loss=0', output.getvalue())
        self.assertIn('win=0, loss=1', output.getvalue())
        self.assertNotIn('win=5', output.getvalue())

    def test_rates_use_final_ticks_and_average_seat_rates(self):
        rows = self.parse()[:2]
        rows[0].ticks, rows[1].ticks = 1000, 3000
        rows[0].total_xp, rows[1].total_xp = 100, 900
        for row in rows:
            row.telemetry = Telemetry(240, 6, 0, 0, 1, 0, 0, 0, 0, 0, 0)
        self.assertEqual(mean_field(rows, 'total_xp', rate=True), '200.00')
        self.assertEqual(mean_field(rows, 'lastHits', rate=True), '4.00')
        rows[0].ticks = 0
        self.assertEqual(mean_field(rows, 'lastHits', rate=True), '2.00')
        rows[1].ticks = None
        self.assertEqual(mean_field(rows, 'lastHits', rate=True), '-')

    def test_mirror_and_labels_preserve_role_identity(self):
        rows = parse_episode(self.root, True, Path('candidate.bas'), Path('unused.bas'), True)
        self.assertTrue(all(row.policy == 'candidate' for row in rows))
        self.assertTrue(all(row.policy_path == 'candidate.bas' for row in rows))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            report(rows, 'James Botts', 'Base')
        self.assertIn('James Botts: mean last hits/1,000 ticks=', output.getvalue())
        self.assertIn('win=1, loss=1', output.getvalue())
        self.assertNotIn('Base:', output.getvalue())

    def test_candidate_snapshot_survives_rebuild_between_sides(self):
        source = self.root / 'candidate.bas'
        source.write_text('END\n')
        out = (self.root / 'evaluation').resolve()
        commands = []

        def run(command, **kwargs):
            commands.append(command)
            self.assertEqual((out / 'inputs/candidate.bas').read_text(), 'END\n')
            source.write_text('CHANGED DURING RUN\n')
            return lasthit_eval.subprocess.CompletedProcess(command, 0)

        argv = ['lasthit_eval', '--candidate', str(source), '--reference', str(source),
                '--episodes', '1', '--out', str(out)]
        with patch.object(sys, 'argv', argv), patch.object(lasthit_eval.subprocess, 'run', run), \
                patch.object(lasthit_eval, 'parse_episode', return_value=[]), \
                patch.object(lasthit_eval, 'report'), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(lasthit_eval.main(), 0)
        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0][5:10], [str(out / 'inputs/candidate.bas')] * 5)
        self.assertEqual(commands[1][10:15], [str(out / 'inputs/candidate.bas')] * 5)

    def test_mixed_seats_and_candidate_only_table(self):
        for red, expected in [(True, (1, 3)), (False, (6, 8))]:
            self.assertEqual(lasthit_eval.candidate_seats(red, mixed=True), expected)
            rows = parse_episode(self.root, red, Path('candidate.bas'), Path('base.bas'), mixed=True)
            self.assertEqual(tuple(r.seat for r in rows if r.policy == 'candidate'), expected)
            self.assertEqual(sum(r.policy == 'reference' for r in rows), 8)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                report(rows, mixed=True)
            lines = output.getvalue().splitlines()
            self.assertEqual(len([line for line in lines if line.startswith('candidate ')]), 2)
            self.assertFalse(any(line.startswith('reference ') for line in lines))
            self.assertTrue(any(line.startswith('reference:') for line in lines))

    def test_mixed_runner_argv(self):
        source = self.root / 'candidate.bas'
        source.write_text('END\n')
        out = (self.root / 'mixed').resolve()
        commands = []

        def run(command, **kwargs):
            commands.append(command)
            return lasthit_eval.subprocess.CompletedProcess(command, 0)

        argv = ['lasthit_eval', '--candidate', str(source), '--reference', str(source),
                '--mixed', '--episodes', '2', '--out', str(out)]
        with patch.object(sys, 'argv', argv), patch.object(lasthit_eval.subprocess, 'run', run), \
                patch.object(lasthit_eval, 'parse_episode', return_value=[]), \
                patch.object(lasthit_eval, 'report'), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(lasthit_eval.main(), 0)
        self.assertEqual(len(commands), 2)
        for command, expected in zip(commands, [(1, 3), (6, 8)]):
            self.assertEqual(tuple(i for i, path in enumerate(command[5:15])
                                   if Path(path).name == 'candidate.bas'), expected)
            self.assertEqual(sum(Path(path).name == 'reference.bas' for path in command[5:15]), 8)

    def test_optional_telemetry_and_future_fields(self):
        (self.root / 'logs/policy_agent_0.log').write_text(
            'LH 480 2 1 1 3 9 4 1 2 0 45 7 12 future-field\n')
        row = self.parse()[0]
        self.assertEqual(row.telemetry.lastHits, 2)
        self.assertEqual(row.telemetry.early, 7)
        self.assertEqual(row.telemetry.missed, 12)
        self.assertTrue(row.xp_matches)
        self.assertFalse(row.issues)

    def test_last_snapshot_and_xp_mismatch(self):
        (self.root / 'logs/policy_agent_0.log').write_text(
            'LH 240 0 0 0 1 0 0 0 0 0 150\n'
            'LH 480 2 1 1 3 9 4 1 2 0 45\n')
        row = self.parse()[0]
        self.assertEqual(row.telemetry.tick, 480)
        self.assertEqual(row.xp_expected, 300)
        self.assertTrue(row.xp_matches)
        (self.root / 'logs/policy_agent_0.log').write_text('LH 480 1 0 0 1 2 3 4 5 6 7\n')
        row = self.parse()[0]
        self.assertFalse(row.xp_matches)
        self.assertEqual(row.xp_expected, 25)

    def test_malformed_last_snapshot_does_not_reuse_previous(self):
        (self.root / 'logs/policy_agent_0.log').write_text(
            'LH 240 2 1 1 3 9 4 1 2 0 45\nLH bad\nBASIC error: work budget\n')
        row = self.parse()[0]
        self.assertIsNone(row.telemetry)
        self.assertIn('malformed LH', row.issues[0])
        self.assertEqual(row.basic_errors, ['BASIC error: work budget'])

    def test_missing_failed_episode_is_retained(self):
        (self.root / 'results.json').unlink()
        (self.root / 'player_status.json').write_text(json.dumps({
            'players': [{'slot': 0, 'reason': 'BASIC VM disabled'}],
        }))
        rows = self.parse()
        self.assertEqual(len(rows), 10)
        self.assertTrue(all(row.total_xp is None and row.issues for row in rows))
        self.assertEqual(rows[0].status_reason, 'BASIC VM disabled')


if __name__ == '__main__':
    unittest.main()
