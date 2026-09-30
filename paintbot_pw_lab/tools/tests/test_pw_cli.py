"""The shared agent CLI contract (pw_cli.py): one JSON envelope on stdout, exit codes 0/1/2/3,
valid values on usage errors, and the fix command on environment errors."""
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import pw_cli  # noqa: E402
import pw_release  # noqa: E402

ENVELOPE_KEYS = {"ok", "tool", "release_tag", "inputs", "outputs", "counts", "failures", "result", "next"}


def parser():
    p = pw_cli.ArgumentParser("demo", "demo tool", examples=["demo.py --n 1 --json"])
    p.add_argument("--n", type=int, default=0, help="how many")
    p.add_argument("--mode", default="ok", help="what the body does")
    return p


def body(args, report):
    print("human text")                       # must land on stderr in --json mode
    os.write(1, b"native text\n")            # so must a raw write to fd 1 (native code, children)
    if args.mode == "usage":
        raise pw_cli.UsageError("--mode is odd", ["ok", "usage"])
    if args.mode == "env":
        raise pw_cli.EnvironmentMissing("libpw is missing", "paintbot_pw_lab/tools/build_native.sh")
    if args.mode == "notbuilt":
        raise pw_release.NotBuilt("pw_trace", Path("/x/pw_trace"), "paintbot_pw_lab/tools/build_tools.sh")
    if args.mode == "partial":
        report.fail("ep1", "trace_failed", "hash mismatch")
    if args.mode == "crash":
        raise KeyError("boom")
    report.output("/tmp/out.csv")
    report.counts["processed"] = args.n
    return {"n": args.n, "nan": math.nan}


def run(capfd, *argv):
    code = pw_cli.run(parser(), body, list(argv))
    out, err = capfd.readouterr()
    return code, out, err


def envelope(out: str) -> dict:
    lines = [line for line in out.splitlines() if line.strip()]
    assert len(lines) == 1, f"stdout must hold exactly one JSON object, got {lines}"
    data = json.loads(lines[0])
    assert set(data) == ENVELOPE_KEYS
    return data


def test_success_prints_one_envelope_and_sends_text_to_stderr(capfd):
    code, out, err = run(capfd, "--n", "3", "--json")
    data = envelope(out)
    assert code == 0 and data["ok"] is True and data["tool"] == "demo"
    assert data["result"] == {"n": 3, "nan": None}          # NaN is null, never "NaN"
    assert data["counts"] == {"processed": 3, "failed": 0, "excluded": 0}
    assert data["outputs"] == ["/tmp/out.csv"] and data["inputs"] == {"n": 3, "mode": "ok"}
    assert "human text" in err and "native text" in err


def test_without_json_text_stays_on_stdout(capfd):
    code, out, _ = run(capfd, "--n", "1")
    assert code == 0 and "human text" in out and "{" not in out


def test_partial_failure_is_exit_1_with_failures_listed(capfd):
    code, out, _ = run(capfd, "--mode", "partial", "--json")
    data = envelope(out)
    assert code == 1 and data["ok"] is False
    assert data["failures"] == [{"id": "ep1", "code": "trace_failed", "message": "hash mismatch"}]
    assert data["counts"]["failed"] == 1 and data["result"]["n"] == 0   # partial result still returned


def test_usage_error_is_exit_2_and_lists_valid_values(capfd):
    code, out, err = run(capfd, "--mode", "usage", "--json")
    data = envelope(out)
    assert code == 2 and data["result"] == {"valid": ["ok", "usage"]}
    assert data["failures"][0]["code"] == "usage_error" and "valid: ok, usage" in data["failures"][0]["message"]
    assert "--mode is odd" in err


def test_argparse_errors_are_usage_errors_with_an_envelope(capfd):
    code, out, _ = run(capfd, "--n", "seven", "--json")
    assert code == 2 and envelope(out)["failures"][0]["code"] == "usage_error"
    code, out, _ = run(capfd, "--bogus", "--json")
    assert code == 2 and envelope(out)["ok"] is False


@pytest.mark.parametrize("mode, fix", [("env", "paintbot_pw_lab/tools/build_native.sh"),
                                       ("notbuilt", "paintbot_pw_lab/tools/build_tools.sh")])
def test_environment_missing_is_exit_3_and_names_the_fix(capfd, mode, fix):
    code, out, err = run(capfd, "--mode", mode, "--json")
    data = envelope(out)
    assert code == 3 and data["next"] == [fix]
    assert fix in data["failures"][0]["message"] and fix in err


def test_a_crash_still_prints_the_envelope(capfd):
    code, out, err = run(capfd, "--mode", "crash", "--json")
    data = envelope(out)
    assert code == 1 and data["failures"][0]["code"] == "crash" and "KeyError" in err


def test_help_documents_examples_and_exit_codes(capfd):
    with pytest.raises(SystemExit) as done:
        pw_cli.run(parser(), body, ["--help"])
    assert done.value.code == 0
    out = capfd.readouterr().out
    assert "demo.py --n 1 --json" in out and "exit codes: 0 ok" in out and "--json" in out


class Seats:
    def __init__(self, keys, names):
        self.frame = pd.DataFrame({"policy_key": keys, "policy_name": names, "seat": range(len(keys))})

    def __getitem__(self, name):
        return self.frame


def test_require_policy_accepts_keys_and_names_and_lists_valid_ones():
    episodes = [Seats(["pv-1", "pv-2"], ["alpha", None])]
    pw_cli.require_policy(episodes, "pv-2")
    pw_cli.require_policy(episodes, "alpha")
    pw_cli.require_policy(episodes, None)
    pw_cli.require_policy([], "anything")          # nothing loaded: the load failures are the finding
    with pytest.raises(pw_cli.UsageError) as error:
        pw_cli.require_policy(episodes, "beta")
    assert error.value.valid == ["alpha", "pv-1", "pv-2"]


class Batch:
    def __init__(self, episodes, failures):
        self.episodes, self.failures = episodes, failures
        self.exclusions = Counter(code for _, code, _ in failures)


def fake_episode(cache: str, cache_hit: bool):
    return SimpleNamespace(cache_hit=cache_hit, source=SimpleNamespace(cache=Path(cache)))


def test_add_batch_counts_failures_and_refuses_an_empty_batch():
    report = pw_cli.Report("demo")
    report.add_batch(Batch([fake_episode("a/pw_cache", True), fake_episode("b/pw_cache", True)],
                           [("dir/x", "no_replay", "missing tape")]))
    assert report.counts["processed"] == 2 and report.failures[0]["code"] == "no_replay"
    assert report.envelope(1)["counts"]["failed"] == 1
    with pytest.raises(pw_cli.UsageError, match="no episode found"):
        pw_cli.Report("demo").add_batch(Batch([], []))


def test_add_batch_lists_only_the_caches_this_run_traced():
    # Contract rule 2: `outputs` includes every cache the run created (e.g. a --vis-every variant
    # that pw_fights traces), and not the caches it merely reused.
    report = pw_cli.Report("demo")
    report.add_batch(Batch([fake_episode("a/pw_cache", True), fake_episode("b@se6-ve12.pw_cache", False)], []))
    assert report.outputs == ["b@se6-ve12.pw_cache"]


def test_default_out_is_under_the_lab_analysis_dir():
    path = pw_cli.default_out("pw_viz", "abc", "movement.png")
    assert path == pw_release.LAB / "analysis" / "pw_viz" / "abc" / "movement.png"
