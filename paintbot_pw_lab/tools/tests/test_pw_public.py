"""pw_public.py: the one polite public-data fetcher (User-Agent, back-off, gzip replays, idempotent saves).
No network: the opener and sleep are injected."""
import gzip
import io
import json
import sys
import urllib.error
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import pw_public  # noqa: E402

TAPE = pw_public.TAPE_MAGIC + b"\x00" * 32


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def http_error(code, retry_after=None):
    headers = {"Retry-After": retry_after} if retry_after else {}
    return urllib.error.HTTPError("https://x", code, "err", headers, None)


def test_get_sends_a_user_agent_and_backs_off_on_429():
    seen, sleeps = [], []
    answers = [http_error(429, "7"), http_error(503), b"payload"]

    def opener(request, timeout):
        seen.append(request.get_header("User-agent"))
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return Response(answer)

    assert pw_public.get("https://x/v2/rounds", sleep=sleeps.append, opener=opener) == b"payload"
    assert all(agent == pw_public.USER_AGENT for agent in seen) and "urllib" not in pw_public.USER_AGENT.lower()
    pause = pw_public.REQUEST_PAUSE_SECONDS
    assert sleeps == [pause, 7.0, pause, pw_public.BACKOFF_SECONDS * 2, pause]   # Retry-After, then doubling


def test_get_gives_up_after_the_retry_limit_and_does_not_retry_403():
    calls = []

    def always(code):
        def opener(request, timeout):
            calls.append(code)
            raise http_error(code)
        return opener

    with pytest.raises(pw_public.PublicFetchError, match="HTTP 429"):
        pw_public.get("https://x", sleep=lambda s: None, opener=always(429))
    assert len(calls) == pw_public.MAX_RETRIES + 1
    calls.clear()
    with pytest.raises(pw_public.PublicFetchError, match="HTTP 403"):
        pw_public.get("https://x", sleep=lambda s: None, opener=always(403))
    assert len(calls) == 1


def test_replays_are_stored_as_gzip_and_junk_is_refused():
    assert gzip.decompress(pw_public.gzip_tape(TAPE)) == TAPE
    already = gzip.compress(TAPE)
    assert pw_public.gzip_tape(already) == already
    with pytest.raises(pw_public.BadReplay):
        pw_public.gzip_tape(b"<html>not found</html>")


def test_save_episode_writes_both_files_once(tmp_path, monkeypatch):
    fetched = []
    monkeypatch.setattr(pw_public, "get", lambda url: fetched.append(url) or TAPE)
    row = {"id": "ereq_1", "status": "completed", "replay_url": "https://r/1"}
    directory = tmp_path / "ereq_1"
    assert pw_public.save_episode(directory, row, {"id": "round_9", "round_number": 9}) is True
    assert json.loads((directory / "episode.json").read_text())["round_number"] == 9
    assert gzip.decompress((directory / "replay.gz").read_bytes()) == TAPE
    assert pw_public.save_episode(directory, row, {"id": "round_9", "round_number": 9}) is False
    assert fetched == ["https://r/1"]                     # the re-run made no request


def test_skip_reason():
    ok = {"status": "completed", "replay_url": "u", "coworld_version": "0.3.79"}
    assert pw_public.skip_reason(ok) is None
    assert pw_public.skip_reason({**ok, "status": "running"}) == "status=running"
    assert pw_public.skip_reason({**ok, "replay_url": None}) == "no_replay_url"
    assert pw_public.skip_reason(ok, {"0.3.78"}) == "other_version"
