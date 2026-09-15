"""Regression checks for shared evidence contracts; no hosted jobs or player runs."""
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import httpx
import pytest
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]


def module(name, path):
    path = ROOT / path
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


fa = module('fetch_artifacts', '.claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py')
ab = module('ab_stats', '.claude/skills/coworld-ab/scripts/ab_stats.py')
xp = module('xp_dashboard', '.claude/skills/coworld-experience-requests/scripts/xp_dashboard.py')
er = module('experience_request', '.claude/skills/coworld-experience-requests/scripts/experience_request.py')
paint = module('event_warehouse', 'paintbot_lab/tools/event_warehouse.py')
pc = module('paint_compare', 'paintbot_lab/tools/compare.py')
miner = module('variance_miner', '.claude/skills/coworld-hypothesis-miner/scripts/variance_miner.py')
crew = module('crew_compare', 'crewrift_lab/.claude/skills/crewrift-ab/scripts/compare.py')


class ArtifactClient:
    def __init__(self, missing=None):
        self.paths = []
        self.missing = missing

    def get_json(self, path, **params):
        self.paths.append(path)
        return {'id': 'ereq_test'}

    def get_text_or_none(self, path):
        self.paths.append(path)
        return json.dumps([{'position': 3, 'policy_version_id': 'pv', 'has_log': True, 'has_artifact': True}])

    def get_bytes_or_none(self, path):
        self.paths.append(path)
        return None if self.missing and self.missing in path else b'{}'


def test_current_artifact_routes_and_sparse_positions(tmp_path):
    client = ArtifactClient()
    ref = fa.EpisodeRef('legacy', '', 'job', 'https://watch.invalid', '', {'id': 'legacy'})
    result = fa.fetch_episode(client, ref, tmp_path, want_replay=True, want_results=True, want_logs=True)
    assert result['complete']
    assert '/v2/episode-requests/by-job/job' in client.paths
    assert '/v2/episode-requests/ereq_test/pv/policy-logs/3' in client.paths
    assert all(not path.startswith('/jobs/') for path in client.paths)
    assert (tmp_path / 'logs/policy_agent_3.log').exists()


def test_partial_zip_never_marks_complete(tmp_path):
    ref = fa.EpisodeRef('ereq_test', '', None, None, '', {'id': 'ereq_test'})
    fa.fetch_episode(ArtifactClient('/policy-artifact/3'), ref, tmp_path,
                     want_replay=False, want_results=False, want_logs=False)
    assert not (tmp_path / 'policy_artifacts_checked.json').exists()
    assert not fa.episode_is_complete(tmp_path, False, False, True, False)


def test_empty_log_directory_is_not_complete(tmp_path):
    (tmp_path / 'episode.json').write_text('{}')
    (tmp_path / 'logs').mkdir()
    assert not fa.episode_is_complete(tmp_path, False, True, False, False)


def test_access_elevation_rejected():
    with pytest.raises(ValueError, match='Elevated'):
        fa.Client('https://example.invalid', 'test', elevated=True)


@pytest.mark.parametrize("check", [fa._xreq_drained, er._terminal])
@pytest.mark.parametrize("parent", ["failed", "cancelled"])
def test_parent_terminal_does_not_finish_live_children(check, parent):
    detail = {"status": parent, "episode_count": 2, "episodes": [
        {"status": "failed"}, {"status": "running"},
    ]}
    assert not check(detail)
    detail["episodes"][1]["status"] = "cancelled"
    assert check(detail)
    assert not check({"status": parent, "episode_count": 2})


@pytest.mark.parametrize("check", [fa._xreq_drained, er._terminal])
def test_completion_counts_include_submitted_work(check):
    assert not check({"status": "failed", "episode_count": 2, "failed_count": 1, "submitted_count": 1})
    assert check({"episode_count": 2, "failed_count": 1, "completed_count": 1})


def test_exact_fisher_and_welch():
    effect, p = ab.rate_sig(.2, 100, .8, 100)
    assert effect == pytest.approx(.6)
    assert p == pytest.approx(stats.fisher_exact([[20, 80], [80, 20]]).pvalue)
    a, b = list(range(40)), list(range(20, 60))
    assert ab.mean_sig(a, b)[1] == pytest.approx(stats.ttest_ind(b, a, equal_var=False).pvalue)
    with pytest.raises(ValueError):
        ab.rate_sig(.13, 3, .5, 2)


def test_small_samples_and_correction():
    small = ab.Delta('win', 'all', True, 0, 1, 4, 4, 'rate')
    small.compute([], [])
    assert small.verdict == 'inconclusive'
    metrics = [('a', True, 'mean', None), ('b', True, 'mean', None)]
    values = lambda rows, key: [row[key] for row in rows]
    value = lambda rows, key: (sum(values(rows, key))/len(rows), len(rows))
    base = {'all': [{'a': i, 'b': i} for i in range(40)]}
    cand = {'all': [{'a': i+30, 'b': i+1} for i in range(40)]}
    ds = ab.build_deltas(base, cand, metrics, value, values, ['all'])
    assert [d.p for d in ds] == pytest.approx(stats.false_discovery_control([d.raw_p for d in ds], method='by'))


def episode(tmp_path, teams=('red', 'red', 'green', 'green'), wins=(False, False, True, True), status='completed'):
    path = tmp_path / 'ep'; path.mkdir()
    row = {'id': 'episode-1', 'status': status, 'coworld_version': 'gv', 'variant_name': 'test',
           'participants': [{'position': i, 'policy_version_id': 'target' if i>=2 else 'opponent', 'policy_name': 'p', 'version': 1} for i in range(4)],
           'game_config': {'slots': [{'team': team} for team in teams]}}
    results = {'team': list(teams), 'win': list(wins), 'scores': [10, 10, 1, 1]}
    (path/'episode.json').write_text(json.dumps(row)); (path/'results.json').write_text(json.dumps(results))
    return path


def test_team_winner_not_score_sum_and_one_episode_sample(tmp_path):
    path = episode(tmp_path)
    meta = paint._load_episode_meta(path)
    assert meta['episode']['winner'] == 'green'
    assert [row['seat'] for row in meta['slots']] == [0, 1, 0, 1]
    groups, excluded = pc.load_batch(tmp_path, 'target')
    assert sum(len(rows) for rows in groups.values()) == 1
    assert next(iter(groups.values()))[0]['win_rate'] == 1
    assert next(iter(groups.values()))[0]['kills_per_seat'] is None


def test_missing_outcome_is_not_draw(tmp_path):
    path = episode(tmp_path, status='failed')
    assert paint._load_episode_meta(path)['episode']['winner'] is None
    (path/'results.json').unlink()
    assert paint._load_episode_meta(path)['episode']['winner'] is None


def test_draw_and_cross_team_rejection(tmp_path):
    path = episode(tmp_path, wins=(False,)*4)
    assert paint._load_episode_meta(path)['episode']['winner'] == 'draw'
    row = json.loads((path/'episode.json').read_text())
    row['participants'][0]['policy_version_id'] = 'target'
    (path/'episode.json').write_text(json.dumps(row))
    with pytest.raises(ValueError, match='exactly one'):
        pc.load_batch(tmp_path, 'target')


def test_sparse_dashboard_identity_and_all_seat_failures():
    poller = xp.Poller(None, [])
    poller._episodes = {'e': {'seats': {3: 'target'}, 'results': {'win': [False, False, False, True], 'scores': [0, 0, 0, 8]}, 'ts': 0}}
    assert poller.snapshot()['leaderboard'][0]['score_mean'] == 8
    poller._episodes['e']['results']['connect_timeout'] = [1, 0, 0, 0]
    assert not poller.snapshot()['leaderboard']


def test_roster_resolution_boolean_and_exact_version(monkeypatch, capsys):
    def handler(request):
        if '/leaderboard' in request.url.path:
            assert request.url.params['include_recent_rounds'] == 'false'
            return httpx.Response(200, json=[{'rank': 1, 'policy_label': 'p:v101'}])
        assert request.url.params['version'] == '101'
        return httpx.Response(200, json={'entries': [{'id': 'pv101', 'version': 101}]})
    monkeypatch.setattr(er, 'observatory_client', lambda _: httpx.Client(base_url='https://example.invalid', transport=httpx.MockTransport(handler)))
    import argparse
    args = argparse.Namespace(policy=None, division='div', server=None, exclude_policy_name=[], top=1)
    er.cmd_resolve(args)
    assert json.loads(capsys.readouterr().out)['opponents'][0]['policy_version_id'] == 'pv101'


def test_miner_rejects_duplicates_and_nonfinite():
    rows = [miner.Episode(str(i), float(i), {'x': float(i)}) for i in range(8)]
    rows[-1].episode_id = rows[0].episode_id
    with pytest.raises(ValueError, match='duplicate'):
        miner.associate(rows, {})
    rows[-1].episode_id = '7'; rows[-1].score = float('nan')
    with pytest.raises(ValueError, match='finite'):
        miner.associate(rows, {})


def test_rotation_preserves_nonstandard_entries_and_does_not_commit(tmp_path):
    (tmp_path/'tools').mkdir(); (tmp_path/'test_lab').mkdir()
    shutil.copy(ROOT/'tools/rotate_lessons.sh', tmp_path/'tools/rotate_lessons.sh')
    buffer = tmp_path/'test_lab/TENTATIVE_LESSONS.md'
    buffer.write_text('A lesson without the required heading.\n')
    subprocess.run(['bash', str(tmp_path/'tools/rotate_lessons.sh'), 'test_lab'], input='{"source":"startup"}', text=True, check=True, capture_output=True)
    archives = list((tmp_path/'test_lab/lessons_archive').glob('*.md'))
    assert len(archives)==1 and archives[0].read_text()=='A lesson without the required heading.\n'
    before = buffer.read_text()
    subprocess.run(['bash', str(tmp_path/'tools/rotate_lessons.sh'), 'test_lab'], input='{"source":"resume"}', text=True, check=True, capture_output=True)
    assert buffer.read_text()==before
    assert 'git -C' not in (tmp_path/'tools/rotate_lessons.sh').read_text()


def test_malformed_artifact_is_bounded_and_other_episode_progresses(tmp_path):
    import argparse
    class BrokenClient(ArtifactClient):
        def get_json(self, path, **params):
            if path.endswith('/episodes'):
                return [{'id': 'ereq_bad', 'status': 'completed'}]
            return {'episode_count': 1, 'completed_count': 1}
        def get_bytes_or_none(self, path):
            return b'<html>not JSON</html>'
    args = argparse.Namespace(xreq='xreq_test', out=tmp_path, num=10, interval=0, max_attempts=2)
    assert fa.watch_loop(BrokenClient(), args, 'https://example.invalid',
                         want_replay=False, want_results=True, want_logs=False, want_artifacts=False) == 1
    assert json.loads((tmp_path/'watch_state.json').read_text())['ereq_bad'] == 2


def test_archive_failure_preserves_buffer(tmp_path):
    (tmp_path/'tools').mkdir(); (tmp_path/'test_lab').mkdir(); (tmp_path/'bin').mkdir()
    shutil.copy(ROOT/'tools/rotate_lessons.sh', tmp_path/'tools/rotate_lessons.sh')
    buffer = tmp_path/'test_lab/TENTATIVE_LESSONS.md'; buffer.write_text('Important original.\n')
    failing_mv = tmp_path/'bin/mv'; failing_mv.write_text('#!/bin/sh\nexit 1\n'); failing_mv.chmod(0o755)
    import os
    env = dict(os.environ, PATH=str(tmp_path/'bin')+os.pathsep+os.environ['PATH'])
    result = subprocess.run(['bash', str(tmp_path/'tools/rotate_lessons.sh'), 'test_lab'], input='{"source":"startup"}',
                            text=True, capture_output=True, env=env)
    assert result.returncode == 1
    assert buffer.read_text() == 'Important original.\n'


def test_crew_whole_episode_failure_excluded_from_gameplay(tmp_path):
    path = episode(tmp_path)
    row = json.loads((path/'episode.json').read_text())
    row['participants'] = [{'position': 3, 'policy_name': 'subject', 'version': 2}]
    results = {'scores': [0,0,0,100], 'win': [0,0,0,1], 'tasks': [0]*4, 'kills': [0]*4,
               'crew': [1]*4, 'imposter': [0]*4, 'disconnect_timeout': [1,0,0,0]}
    (path/'episode.json').write_text(json.dumps(row)); (path/'results.json').write_text(json.dumps(results))
    records, outcomes, excluded = crew.load_batch(tmp_path, 'subject', 2)
    assert not records
    assert excluded == {'failed_episode_gameplay': 1}
    assert crew.metric_value(outcomes, 'ops_fail_rate') == (1,1)


def test_policy_discovery_current_cursor_routes():
    class Pages:
        def get_json(self, path, **params):
            if path == '/stats/policy-versions':
                assert params['version'] == 101
                return {'entries':[{'id':'pv','version':101}], 'next_cursor':None}
            if path == '/v2/policy-versions/pv/episodes':
                if 'cursor' not in params:
                    return {'entries':[{'id':'first','created_at':'2026-09-14'}], 'next_cursor':'next'}
                return {'entries':[{'id':'second','created_at':'2026-09-13'}], 'next_cursor':None}
            assert path.startswith('/episodes/')
            return {'id':path.rsplit('/',1)[1], 'tags':{'job_id':'job'}}
    refs=fa.discover_by_policy(Pages(),'player',101,2)
    assert [r.ref_id for r in refs] == ['first','second']


def test_corrupt_marker_is_incomplete(tmp_path):
    (tmp_path/'episode.json').write_text('{}')
    (tmp_path/'policy_logs_checked.json').write_text('[')
    assert not fa.episode_is_complete(tmp_path, False, True, False, False)


def test_missing_comparison_arm_does_not_invent_zero():
    renderer = module('compare_report', '.claude/skills/coworld-ab/scripts/compare_report.py')
    d = ab.emit_json('base','candidate','win_rate',[
        ab.Delta('win_rate','all',True,None,.5,0,10,'rate')])
    page=renderer.render(d,None,None,'test')
    assert 'Δ ·' in page


def test_membership_pagination_keeps_older_matches():
    lifecycle = module('policy_lifecycle', '.claude/skills/coworld-policy-lifecycle/scripts/policy_lifecycle.py')
    def respond(request):
        if request.url.params.get('cursor') == 'page2':
            return httpx.Response(200, json=[{'id': 'older'}])
        return httpx.Response(200, json=[{'id': 'newer'}], headers={'X-Next-Cursor': 'page2'})
    with httpx.Client(base_url='https://example.invalid', transport=httpx.MockTransport(respond)) as client:
        assert lifecycle.get_all_rows(client, '/v2/league-policy-memberships', mine=True) == [
            {'id': 'newer'}, {'id': 'older'},
        ]


def test_create_preserves_admission_cost_preview(monkeypatch, tmp_path, capsys):
    from argparse import Namespace
    preview = {'estimated_cost_credits': 7.5, 'player_pod_llm_spend_limit_usd': None}
    def respond(request):
        if request.url.path == '/openapi.json':
            return httpx.Response(200, json={'components': {'schemas': {'V2CreateExperienceRequestRequest': {
                'properties': {'roster': {}}, 'additionalProperties': False,
            }}}})
        if request.method == 'POST':
            return httpx.Response(200, json={'id': 'xreq_test', 'cost_preview': preview})
        return httpx.Response(200, json={'id': 'xreq_test', 'episode_count': 1, 'cost_preview': None})
    monkeypatch.setattr(er, 'observatory_client', lambda server: httpx.Client(
        base_url='https://example.invalid', transport=httpx.MockTransport(respond)))
    body = tmp_path / 'request.json'
    body.write_text('{"roster": []}')
    er.cmd_create(Namespace(server=None, body=str(body), check_schema=False))
    assert json.loads(capsys.readouterr().out)['cost_preview'] == preview


def test_rotation_does_not_archive_fresh_templates(tmp_path):
    (tmp_path / 'tools').mkdir()
    (tmp_path / 'test_lab').mkdir()
    script = tmp_path / 'tools/rotate_lessons.sh'
    shutil.copy(ROOT / 'tools/rotate_lessons.sh', script)
    def rotate():
        subprocess.run(['bash', str(script), 'test_lab'], input='{"source":"startup"}',
                       text=True, check=True, capture_output=True)
    rotate()
    buffer = tmp_path / 'test_lab/TENTATIVE_LESSONS.md'
    buffer.write_text(__import__('re').sub(r'(?<=Session started:\*\* )[0-9-]+ [0-9:]+', '2000-01-01 00:00', buffer.read_text()))
    rotate()
    archives = tmp_path / 'test_lab/lessons_archive'
    assert not list(archives.glob('*.md'))
    buffer.write_text(buffer.read_text().replace('**Lifecycle.**', 'Important pre-divider lesson.\n\n**Lifecycle.**'))
    rotate()
    saved = list(archives.glob('*.md'))
    assert len(saved) == 1
    assert 'Important pre-divider lesson.' in saved[0].read_text()


@pytest.mark.parametrize('results', [None, '<html>bad data</html>'])
def test_crew_failure_survives_missing_results(tmp_path, results):
    path = episode(tmp_path, status='failed')
    row = json.loads((path / 'episode.json').read_text())
    row['participants'] = [{'position': 0, 'policy_name': 'subject', 'version': 2}]
    (path / 'episode.json').write_text(json.dumps(row))
    if results is None:
        (path / 'results.json').unlink()
    else:
        (path / 'results.json').write_text(results)
    records, outcomes, excluded = crew.load_batch(tmp_path, 'subject', 2)
    assert not records
    assert crew.metric_value(outcomes, 'ops_fail_rate') == (1, 1)
    groups = crew.by_group(records)
    groups['episodes'] = outcomes
    deltas = ab.build_deltas(groups, groups, crew.METRICS, crew.metric_value, crew.value_fn, crew.GROUPS)
    failure = next(d for d in deltas if d.metric == 'ops_fail_rate')
    assert failure.group == 'episodes' and failure.n_base == 1


@pytest.mark.parametrize('payload', ['<html>not JSON</html>', '"oops"', '[1]', '{}', '{"connect_timeout":1}'])
def test_dashboard_bad_json_does_not_stop_poll(payload):
    class BadResultClient:
        def get_json(self, path):
            return [{'id': 'bad', 'status': 'completed', 'participants': None}]
        def get_text_or_none(self, path):
            return payload
    poller = xp.Poller(BadResultClient(), ['xreq_test'])
    poller._poll_once()
    snapshot = poller.snapshot()
    assert snapshot['poll_count'] == 1
    assert snapshot['result_errors'] == 1
    assert snapshot['scored_episodes'] == 0


@pytest.mark.parametrize('results', [None, '<html>bad data</html>'])
def test_crew_completed_without_results_is_unknown(tmp_path, results):
    path = episode(tmp_path)
    row = json.loads((path / 'episode.json').read_text())
    row['participants'] = [{'position': 0, 'policy_name': 'subject', 'version': 2}]
    (path / 'episode.json').write_text(json.dumps(row))
    if results is None:
        (path / 'results.json').unlink()
    else:
        (path / 'results.json').write_text(results)
    records, outcomes, excluded = crew.load_batch(tmp_path, 'subject', 2)
    assert not records and not outcomes
    assert excluded == {'unknown_episode_outcome': 1}


@pytest.mark.parametrize('results', [b'{"scores":[5]}', b'\xff',
                                     b'{"connect_timeout":[],"disconnect_timeout":[]}'])
def test_crew_partial_ops_evidence_is_unknown(tmp_path, results):
    path = episode(tmp_path)
    row = json.loads((path / 'episode.json').read_text())
    row['participants'] = [{'position': 0, 'policy_name': 'subject', 'version': 2}]
    (path / 'episode.json').write_text(json.dumps(row))
    (path / 'results.json').write_bytes(results)
    records, outcomes, excluded = crew.load_batch(tmp_path, 'subject', 2)
    assert not records and not outcomes
    assert excluded == {'unknown_episode_outcome': 1}


def test_crew_known_success_with_unknown_role_reports_exclusion(tmp_path):
    path = episode(tmp_path)
    row = json.loads((path / 'episode.json').read_text())
    row['participants'] = [{'position': 0, 'policy_name': 'subject', 'version': 2}]
    (path / 'episode.json').write_text(json.dumps(row))
    (path / 'results.json').write_text(json.dumps({'scores': [5], 'win': [0], 'tasks': [0],
        'kills': [0], 'connect_timeout': [0], 'disconnect_timeout': [0]}))
    records, outcomes, excluded = crew.load_batch(tmp_path, 'subject', 2)
    assert not records
    assert crew.metric_value(outcomes, 'ops_fail_rate') == (0, 1)
    assert excluded == {'incomplete_target_seat_results': 1}
