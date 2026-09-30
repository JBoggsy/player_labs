# pw_episodes.py: episode reader, trace cache, tables

Turns downloaded or locally recorded episodes into hash-verified Parquet tables: it finds
every episode under the roots, traces each tape with `pw_trace` (cached per episode), checks
identity and results, and lists every episode it could not use. It is the first step on any
episode data; every analysis tool loads through it. The table schema and Python API are the
contract in [tables.md](tables.md); this page is the how-to. Source: `tools/pw_episodes.py`.
Part of the lab tool set: [tool index](README.md) (`pw.py episodes`).

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
    --state-every 6 --vis-every 0 --window A:B   trace sampling (--vis-every a multiple of --state-every)
    --refresh                              ignore caches
    --jobs J                               parallel traces (default: half the cores)
    --sql "select ..."                     DuckDB query over the tables after loading
    --json                                 one JSON envelope on stdout (agent contract)

# Examples (the --help examples)
uv run python paintbot_pw_lab/tools/pw_episodes.py paintbot_pw_lab/episode_data/20260928T214433_* --json
uv run python paintbot_pw_lab/tools/pw_episodes.py EPISODE_DIR --window 1200:1500 --vis-every 24
uv run python paintbot_pw_lab/tools/pw_episodes.py ROOT --sql "select t, seat, victim from kills" --json
```

`--sql` runs over the batch just loaded, in the cache variant it was loaded with (so
`--tag`/`--window` queries see that trace); the views are named like the tables in
[tables.md](tables.md). Only `pw_episodes`-level columns exist in each table: `shots`,
`kills` and the rest carry `seat`/`team`, not `policy_key`; join `seats` on
`(episode_id, seat)` for policy identity.

Output: one line per episode (`rules`, `ticks`, `winner`, `glory`, `results_check`,
`cached`/`traced`, notes), then `loaded N episodes, M failed`, one `FAILED [code] path:
message` line per failure, and the exclusion counts.

## Agent contract

`uv run python paintbot_pw_lab/tools/pw.py episodes ROOT... --json` (or the tool directly). Shared rules (envelope keys, exit codes, selector checks): [README.md § Agent contract](README.md#agent-contract), implemented once in `tools/pw_cli.py`.

| | |
| --- | --- |
| Inputs | episode dirs, batch dirs (searched recursively) or `NAME.replay`; `--tag`/`--binary`, `--state-every`, `--vis-every`, `--window A:B`, `--refresh`, `--jobs`, `--sql` |
| Outputs | per-episode cache `<episode dir>/pw_cache/` (or `NAME.pw_cache/`), or a variant `pw_cache@<variant>/` (`NAME@<variant>.pw_cache/`) for a non-default tag or trace options: `trace.jsonl`, `tables/*.parquet`, `receipt.json`; `outputs[]` lists the caches this run (re)built; `result.episodes[].cache` names the one used |
| `--json` result | `{episodes: [{episode_id, rules, ticks, winner, glory: [g0, g1], results_check, cached, notes, cache}], sql?: [rows]}` (`sql` only with `--sql`) |
| Exit codes | 0 ok; 1 some episodes failed to load or verify (the rest are used; one `failures[]` entry each, `counts.failed_by_code`); 2 usage error: bad arguments (a malformed `--window`, `--state-every` < 1 or a `--vis-every` that is not a multiple of it, a missing `--binary`), roots with no episode, or a `--sql` query DuckDB rejects (`result.valid` lists the table names); 3 `pw_trace` not built for the tag (`next[0]` = `paintbot_pw_lab/tools/build_tools.sh [TAG]`) |
| Idempotence / cache | a cache is reused while its receipt (tape, metadata, binary and option digests) matches; `--refresh` re-traces. Reruns are cheap. Each (tag, options) pair has its own cache directory, so tracing with `--tag X` or finer options never replaces another trace (see Cache variants) |
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
| `invalid` | an `EpisodeError` without a more specific code (e.g. `load_episode` given a path holding several episodes) | use `load_batch` |
| `OSError`, `ValueError`, `KeyError` | an unreadable file or malformed JSON/metadata: the Python exception name is the code | inspect the file named in `failures[].id` |

Two batch-level errors are not per-episode codes: two different episode directories with the
same `episode_id` (e.g. a copied episode dir; passing the same path twice is deduplicated)
raise from `load_batch`, which the CLI reports as failure code `crash`, exit 1; an unexpected
exception is also `crash` (a tool bug, traceback on stderr).

## Verified (2026-09-29)

Re-run on build `coworld-v0.3.79`: the 3 samples (cached, exit 0) and 8 local
`pw_local screen --record --record-seeds 1-4` recordings (exit 0, `results_check none`); the
three `--help` examples; `--tag coworld-v0.3.78` and `--window 1200:1500 --vis-every 24` each
wrote their own variant directory beside the default one; `--window 15:10`, a missing root,
`--binary /nope`, `--state-every 0` and a bad `--sql` all exit 2.

Earlier, on `coworld-v0.3.78`, all 8 test episodes loaded: the 3 rules-44 samples (`results_check results.json`), 3 local
recordings (with and without `.meta.json`), 2 hosted 0.3.78 episodes (`participant_scores`).
A cached rerun of all 8 took 1.4 s. A tape with one flipped byte fails as `trace_failed`
(hash mismatch at tick 1641); a directory without a tape fails as `no_replay`; editing
`results.json` invalidates the cache and fails as `results_mismatch`. Tests:
`paintbot_pw_lab/tools/tests/test_pw_episodes.py`.

## Cache variants

The cache directory is keyed by what was traced, not just by the episode:

| Trace | Hosted episode dir | Local `NAME.replay` |
| --- | --- | --- |
| pinned tag (`tools/release.env`), default options | `pw_cache/` | `NAME.pw_cache/` |
| `--tag coworld-v0.3.78` | `pw_cache@coworld-v0.3.78/` | `NAME@coworld-v0.3.78.pw_cache/` |
| `--vis-every 24` | `pw_cache@se6-ve24/` | `NAME@se6-ve24.pw_cache/` |
| `--tag X --window 960:1560` (also `pw_viz --fine`) | `pw_cache@X+se6-ve0-w960_1560/` | `NAME@X+se6-ve0-w960_1560.pw_cache/` |
| `--binary PATH` | `pw_cache@bin-<sha256[:10]>/` | `NAME@bin-<sha256[:10]>.pw_cache/` |

So `pw.py episodes DIR --tag X` after `pw_viz --fine` (or `pw_intent`'s dense trace, or
`--vis-every`) traces once into its own directory and leaves the others in place; the next run
with the same tag and options is a cache hit. Before 2026-09-29 there was one `pw_cache/` per
episode and any other tag or granularity silently re-traced and replaced it.

- The "pinned tag" is read from `tools/release.env` when the tool starts. After
  `deployed_ref.py --write` moves the pin, the new tag's traces take over `pw_cache/` (the old
  default is re-traced once) and an explicit `--tag <old>` gets its own variant.
- `open_duckdb(roots)` reads only the default `pw_cache/` of each episode; pass the loaded
  `Batch` to query a variant.
- Variants are never deleted automatically. `rm -rf <dir>/pw_cache@*` is safe: a missing cache
  is rebuilt on the next load.

## Limits

- Seat logs are parsed only for `PWI ` intent lines and `BASIC error:`; the intent format is
  defined in [pw_intent.md](pw_intent.md) (emitted by policies wired with `reference/intent_telemetry.bas`).
- Episodes that failed on the platform (`status` failed, no tape) are listed as `no_replay`;
  a forfeit's outcome is not synthesized here.
- `open_duckdb` globs every cached table under the roots; a stale cache from an older
  `TABLES_VERSION` stays on disk until that episode is loaded again.
