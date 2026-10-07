"""Unit tests for the --watch selection logic (pure function, no network)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fetch_artifacts import EpisodeRef, episode_dirname, episode_is_complete, select_watch_fetches


def _ref(ref_id: str, status: str) -> EpisodeRef:
    return EpisodeRef(
        ref_id=ref_id,
        created_at="2026-07-01T12:00:00",
        job_id="job-1",
        replay_url=None,
        label=status,
        record={"id": ref_id, "status": status},
    )


def _complete_dir(root: Path, ref: EpisodeRef) -> Path:
    d = root / episode_dirname(ref)
    (d / "logs").mkdir(parents=True)
    (d / "policy_artifacts_checked.json").write_text("[]")
    (d / "policy_logs_checked.json").write_text("[]")
    (d / "episode.json").write_text("{}")
    (d / "replay.json").write_bytes(b"")
    (d / "results.json").write_text("{}")
    return d


def test_selection_partitions_done_waiting_exhausted_and_fetchable(tmp_path: Path) -> None:
    done_ref = _ref("ereq_done00000000000", "completed")
    _complete_dir(tmp_path, done_ref)
    running = _ref("ereq_running0000000", "running")
    fresh = _ref("ereq_fresh000000000", "completed")
    failed_terminal = _ref("ereq_failed00000000", "failed")
    tired = _ref("ereq_tired000000000", "failed")

    to_fetch, waiting, exhausted, done = select_watch_fetches(
        [done_ref, running, fresh, failed_terminal, tired],
        tmp_path,
        {"ereq_tired000000000": 3},
        want_replay=True,
        want_logs=True,
        max_attempts=3,
        xreq_drained=False,
    )
    assert [r.ref_id for r in to_fetch] == ["ereq_fresh000000000", "ereq_failed00000000"]
    assert [r.ref_id for r in waiting] == ["ereq_running0000000"]
    assert [r.ref_id for r in exhausted] == ["ereq_tired000000000"]
    assert [r.ref_id for r in done] == ["ereq_done00000000000"]


def test_drained_xreq_sweeps_episodes_with_nonterminal_row_status(tmp_path: Path) -> None:
    # When the xreq itself reports drained, stale per-row statuses must not
    # strand an episode: everything unfetched becomes fetchable.
    running = _ref("ereq_running0000000", "running")
    to_fetch, waiting, exhausted, done = select_watch_fetches(
        [running], tmp_path, {},
        want_replay=True, want_logs=True, max_attempts=3, xreq_drained=True,
    )
    assert [r.ref_id for r in to_fetch] == ["ereq_running0000000"]
    assert waiting == [] and exhausted == [] and done == []


def test_partial_dir_is_retried_not_done(tmp_path: Path) -> None:
    # An episode dir missing its replay fails episode_is_complete -> refetch.
    ref = _ref("ereq_partial0000000", "completed")
    d = tmp_path / episode_dirname(ref)
    d.mkdir(parents=True)
    (d / "episode.json").write_text("{}")   # no replay.json, no logs/
    to_fetch, _, _, done = select_watch_fetches(
        [ref], tmp_path, {},
        want_replay=True, want_logs=True, max_attempts=3, xreq_drained=False,
    )
    assert [r.ref_id for r in to_fetch] == ["ereq_partial0000000"]
    assert done == []


def test_missing_results_json_means_incomplete(tmp_path: Path) -> None:
    # Regression: a dir with episode.json + replay + logs but NO results.json used
    # to count as complete, so watch/idempotent reruns skipped it forever.
    ref = _ref("ereq_noresults00000", "completed")
    d = _complete_dir(tmp_path, ref)
    (d / "results.json").unlink()

    assert not episode_is_complete(d, want_replay=True, want_logs=True)
    # --no-results: results.json must NOT be required.
    assert episode_is_complete(d, want_replay=True, want_logs=True, want_results=False)

    to_fetch, _, _, done = select_watch_fetches(
        [ref], tmp_path, {},
        want_replay=True, want_logs=True, want_results=True,
        max_attempts=3, xreq_drained=False,
    )
    assert [r.ref_id for r in to_fetch] == ["ereq_noresults00000"]
    assert done == []

    _, _, _, done = select_watch_fetches(
        [ref], tmp_path, {},
        want_replay=True, want_logs=True, want_results=False,
        max_attempts=3, xreq_drained=False,
    )
    assert [r.ref_id for r in done] == ["ereq_noresults00000"]


def test_round_flag_is_repeatable() -> None:
    # Regression: --round was a single-value flag; ten --round flags silently kept
    # only the last one.
    from fetch_artifacts import parse_args

    args = parse_args(["--round", "round_aaa", "--round", "round_bbb"])
    assert args.round_ids == ["round_aaa", "round_bbb"]


def test_watch_loop_survives_transient_network_errors(tmp_path: Path) -> None:
    # Regression: an httpx error mid-poll (e.g. RemoteProtocolError) killed the
    # watcher silently. One bad poll pass must log and retry, not die.
    import argparse

    import httpx

    from fetch_artifacts import watch_loop

    ref = _ref("ereq_flaky000000000", "completed")
    _complete_dir(tmp_path, ref)

    class FlakyClient:
        def __init__(self) -> None:
            self.calls = 0

        def get_json(self, path: str, **params: object) -> object:
            self.calls += 1
            if self.calls == 1:
                raise httpx.RemoteProtocolError("server disconnected")
            if "experience-requests" in path and path.endswith("/episodes"):
                return [dict(ref.record, created_at=ref.created_at, job_id="job-1",
                             replay_url=None, participants=[])]
            return {"episode_count": 1, "completed_count": 1, "failed_count": 0}

    args = argparse.Namespace(
        xreq="xreq_test", out=tmp_path, num=10, interval=0.0, max_attempts=3,
    )
    client = FlakyClient()
    rc = watch_loop(
        client, args, "https://example.test",
        want_replay=True, want_results=True, want_logs=True, want_artifacts=True,
    )
    assert rc == 0
    assert client.calls > 1  # first pass errored, loop retried and finished


def test_throttled_artifacts_reach_watch_backoff(tmp_path: Path) -> None:
    import httpx
    import pytest
    from fetch_artifacts import Client, fetch_episode

    with Client('https://example.invalid', 'test') as client:
        client._http.close()
        client._http = httpx.Client(
            base_url='https://example.invalid',
            transport=httpx.MockTransport(lambda request: httpx.Response(429)),
        )
        for fetch in (client.get_bytes_or_none, client.get_text_or_none):
            with pytest.raises(httpx.HTTPStatusError) as caught:
                fetch('/artifact')
            assert caught.value.response.status_code == 429
        with pytest.raises(httpx.HTTPStatusError):
            fetch_episode(client, _ref('ereq_throttled', 'completed'), tmp_path / 'episode',
                          want_replay=True, want_results=True, want_logs=True)


def test_absent_artifacts_remain_optional() -> None:
    import httpx
    from fetch_artifacts import Client

    with Client('https://example.invalid', 'test') as client:
        client._http.close()
        client._http = httpx.Client(
            base_url='https://example.invalid',
            transport=httpx.MockTransport(lambda request: httpx.Response(404)),
        )
        assert client.get_bytes_or_none('/artifact') is None
        assert client.get_text_or_none('/artifact') is None


def test_watch_resumes_partial_episode_without_redownloading_files(tmp_path: Path) -> None:
    import httpx
    import json
    from fetch_artifacts import Client, fetch_episode

    episode = tmp_path / 'episode'
    (episode / 'logs').mkdir(parents=True)
    (episode / 'results.json').write_text('{}')
    (episode / 'replay.json').write_bytes(b'recorded replay')
    (episode / 'logs/policy_agent_0.log').write_text('kept log')
    requested = []

    def respond(request):
        requested.append(request.url.path)
        if request.url.path.endswith('/policy-artifacts'):
            return httpx.Response(200, json=[{'position':i,'policy_version_id':'pv','has_log':True,'has_artifact':False} for i in (0,2)])
        if request.url.path.endswith('/policy-logs/2'):
            return httpx.Response(200, text='remaining log')
        return httpx.Response(404)

    with Client('https://example.invalid','test') as client:
        client._http.close()
        client._http = httpx.Client(base_url='https://example.invalid', transport=httpx.MockTransport(respond))
        result = fetch_episode(client,_ref('ereq_resumed','completed'),episode,
                               want_replay=True,want_results=True,want_logs=True,resume=True)
    assert result['complete']
    assert not any(path.endswith(('/artifacts/results','/artifacts/replay','/policy-logs/0')) for path in requested)
    assert (episode/'logs/policy_agent_0.log').read_text() == 'kept log'
    assert json.loads((episode/'policy_logs_checked.json').read_text())[1]['position'] == 2
