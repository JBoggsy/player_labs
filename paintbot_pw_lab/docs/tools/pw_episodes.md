# pw_episodes.py: episode reader, trace cache, tables (T2)

Turns downloaded or locally recorded episodes into hash-verified Parquet tables. The table
schema and Python API are the contract in [tables.md](tables.md); this page is the how-to.
Source: `tools/pw_episodes.py`.

## Commands (from the repo root)

```bash
# 1. Build the release tools once per tag (pw_trace, pw_map, paintbot-headless)
paintbot_pw_lab/tools/build_tools.sh

# 2. Fetch episodes (hosted) with the shared fetcher, or record locally
uv run python .claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py \
    --ereq ereq_... --out paintbot_pw_lab/episode_data

# 3. Trace + tables for everything under one or more roots (cached; exit 1 if any failed)
uv run python paintbot_pw_lab/tools/pw_episodes.py paintbot_pw_lab/episode_data/<batch>

# Options
    --tag coworld-vX.Y.Z | --binary PATH   which pw_trace build (default: PW_RELEASE_TAG in tools/release.env)
    --state-every 6 --vis-every 0 --window A:B   trace sampling
    --refresh                              ignore caches
    --jobs J                               parallel traces (default: half the cores)
    --sql "select ..."                     DuckDB query over the tables after loading
```

Output: one line per episode (`rules`, `ticks`, `winner`, `glory`, `results_check`,
`cached`/`traced`, notes), then `loaded N episodes, M failed`, one `FAILED [code] path:
message` line per failure, and the exclusion counts.

## Agent contract

`uv run python paintbot_pw_lab/tools/pw.py episodes ROOT... --json` (or the tool directly). Shared rules (envelope keys, exit codes, selector checks): [README.md § Agent contract](README.md#agent-contract), implemented once in `tools/pw_cli.py`.

| | |
| --- | --- |
| Inputs | episode dirs, batch dirs (searched recursively) or `NAME.replay`; `--tag`/`--binary`, `--state-every`, `--vis-every`, `--window A:B`, `--refresh`, `--jobs`, `--sql` |
| Outputs | per-episode cache `<episode dir>/pw_cache/` (or `NAME.pw_cache/`): `trace.jsonl`, `tables/*.parquet`, `receipt.json`; `outputs[]` lists the caches this run (re)built |
| `--json` result | `{episodes: [{episode_id, rules, ticks, winner, glory: [g0, g1], results_check, cached, notes, cache}], sql?: [rows]}` (`sql` only with `--sql`) |
| Exit codes | 0 ok; 1 some episodes failed to load or verify (the rest are used; one `failures[]` entry each, `counts.failed_by_code`); 2 usage error: bad arguments, roots with no episode, or an unknown selector (`--window`, `--binary`; `result.valid` lists the valid values); 3 `pw_trace` not built (`next[0]` = `paintbot_pw_lab/tools/build_tools.sh`) |
| Idempotence / cache | a cache is reused while its receipt (tape, metadata, binary and option digests) matches; `--refresh` re-traces. Reruns are cheap |
| Typical next step | `uv run python paintbot_pw_lab/tools/pw.py metrics ROOT --json` (the envelope's `next[]`), or `--sql` for one question |

## Inputs it accepts

- Hosted episode directory: `episode.json` and/or `results.json`, plus the tape under any
  of `replay.json`, `replay.json.z`, `replay`, `replay.bin`, `replay.gz`, `*.replay`. The tape
  may be raw, gzip or zlib (it sniffs the bytes, not the name: the fetcher's `replay.json`
  is the raw tape).
- A public round-listing row saved as `episode.json` next to the gunzipped (or gzip)
  `replay_url` works too: no `game_config` means team from parity (noted), and the scores
  are checked against `participant_scores`.
- Local: `NAME.replay` plus optional `NAME.meta.json` (schema in [tables.md](tables.md)).

## Failure codes (never silently dropped)

| code | meaning | next step |
| --- | --- | --- |
| `no_replay` | directory has metadata but no tape | refetch (`--force`); a missing artifact is "retry", not "absent" |
| `bad_tape` | not a `POLYWORLDREPLAY` tape, or another game | check the download |
| `trace_failed` | `pw_trace` failed: hash mismatch, unsupported (newer) rules, tape ends early | build the recording's tag (`build_tools.sh <tag>`) and retry with `--tag`; a mismatch at the current tag is a finding |
| `identity` | participants do not cover every seat, or slot team ≠ seat parity | inspect `episode.json` |
| `results_mismatch` | results/participant scores disagree with the trace | do not use the episode; investigate |

## Verified (2026-09-29)

All 8 test episodes load: the 3 rules-44 samples (`results_check results.json`), 3 local
recordings (with and without `.meta.json`), 2 hosted 0.3.78 episodes (`participant_scores`).
A cached rerun of all 8 took 1.4 s. A tape with one flipped byte fails as `trace_failed`
(hash mismatch at tick 1641); a directory without a tape fails as `no_replay`; editing
`results.json` invalidates the cache and fails as `results_mismatch`. Tests:
`paintbot_pw_lab/tools/tests/test_pw_episodes.py`.

## Limits

- Seat logs are parsed only for `PWI ` intent lines and `BASIC error:`; the intent format is
  owned by T13 and not yet emitted by any policy.
- Episodes that failed on the platform (`status` failed, no tape) are listed as `no_replay`;
  a forfeit's outcome is not synthesized here.
- `open_duckdb` globs every cached table under the roots; a stale cache from an older
  `TABLES_VERSION` stays on disk until that episode is loaded again.
