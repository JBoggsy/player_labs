# release.env and pw_release.py — the one release pin

[`tools/release.env`](../../tools/release.env) is the single source of truth for which
paintbot-pw release (the **release tag**, e.g. `coworld-v0.3.89`) the lab uses, and
`tools/pw_release.py` is the one reader of it: it resolves the tag, the build directory, the
cache root and whether each binary is built. Nothing else in the lab should hold a tag
literal. Part of the lab tool set: [tool index](README.md) (`pw.py release`).

```
PW_RELEASE_TAG=coworld-v0.3.89   # the build every tool defaults to (tools/bin/<tag>/)
PW_RELEASE_SHA=118e1619          # its commit
PW_DOCS_SHA=118e1619             # where the mechanics/policy docs' line citations are exact
```

Two pins on purpose. The **tools** follow the league: a newer build replays older rules
versions hash-exactly, so building the league's tag is enough. The **docs** cite `file.nim:NN`
lines, which are exact only at the commit they were verified at, so `PW_DOCS_SHA` moves only
after someone re-verifies them. [deployed_ref.py](deployed_ref.md) prints the diff between the
two so an agent can judge what needs re-checking.

Who reads it:

| Reader | How |
| --- | --- |
| `build_tools.sh`, `build_native.sh` | `source tools/release.env`; the tag argument still overrides |
| `pw_episodes.py`, `pw_mapdata.py`, `pw_local.py` | `DEFAULT_TAG = pw_release.current_tag()`; every other tool gets it through them |
| `pw_cli.py` | the envelope's `release_tag` (overridden by a tool's `--tag`) |
| `pw.py doctor` | checks every file in `BUILT_BY` and the `libpw.build.json` receipt for the tag |
| `deployed_ref.py` | compares with the league; `--write` updates the tag and sha lines in place |
| shell docs | `source paintbot_pw_lab/tools/release.env; B=paintbot_pw_lab/tools/bin/$PW_RELEASE_TAG` |

## Python API (`tools/pw_release.py`)

```python
import pw_release                      # with paintbot_pw_lab/tools on sys.path
pw_release.current_tag()               # 'coworld-v0.3.89'
pw_release.current_sha()               # '118e1619'
pw_release.docs_sha()                  # '118e1619'
pw_release.bin_dir(tag=None)           # Path to tools/bin/<tag>/
pw_release.require_built("pw_trace")   # Path, or raises pw_release.NotBuilt (exit_code 3)
pw_release.require_built_or_exit("pw_map", tag)   # CLI paths: prints the fix, exits 3
pw_release.cache_root()                # $PW_CACHE_DIR, else tools/.cache/ (read at call time)
pw_release.release_tree(tag=None)      # <cache root>/<tag>/: build_tools.sh's source worktree
```

`NotBuilt`'s message is `<path> is missing: run paintbot_pw_lab/tools/build_tools.sh` (with the
tag appended when it is not the current one); `libpw.dylib`/`libpw.build.json` name
`build_native.sh`. Known tools: `paintbot-headless`, `replay_stats`, `pw_trace`, `pw_map`,
`libpw.dylib`, `libpw.build.json`; anything else is a `ValueError` listing them.

## Environment variables

| Variable | Default | Read by | Effect |
| --- | --- | --- | --- |
| `PW_CACHE_DIR` | `paintbot_pw_lab/tools/.cache` | `pw_release.cache_root()` (at call time), `build_tools.sh`, `build_native.sh` | moves the rebuildable caches: the per-release source worktree `<tag>/` (which `pw_local.py` and `pw_intent.py` run from), the map rasters `maps/<tag>/` ([pw_map.md](pw_map.md#cache-location)) and the [terrain cache](#terrain-cache) `terrain/<tag>/`. Binaries stay in `tools/bin/<tag>/`; per-episode trace caches stay beside the episode. Set it for the build too, or `pw_local` exits 3 naming the missing worktree |
| `PW_TERRAIN_CACHE` | on | `pw_terrain.py` (every tool that runs a `-d:pwTraining` build) | `0` (or `off`/`false`/`no`) disables the [terrain cache](#terrain-cache): nothing is read, written or pruned, and the tools run at the uncached speed |
| `PW_TERRAIN_CACHE_MAX_GB` | `2` | `pw_terrain.py` | total size cap of the terrain cache across tags; least-recently-used files are deleted above it |
| `PW_CLONE` | `~/coding/coworlds/paintbot-pw` | `build_tools.sh`, `deployed_ref.py` (`--clone` default), `pw.py doctor` (`source_clone` check) | the paintbot-pw source clone. `build_tools.sh` clones it (blob-less) when absent, then only fetches; its checkout is never changed |

## CLI

```bash
uv run python paintbot_pw_lab/tools/pw_release.py                        # pins + built/missing
uv run python paintbot_pw_lab/tools/pw_release.py --json --require all   # exit 3 if anything is missing
uv run python paintbot_pw_lab/tools/pw_release.py --tag coworld-v0.3.78 --require pw_trace
```

`--json` prints one object (`ok`, `tool`, `release_tag`, `inputs` (`tag`, `require`), `outputs`
(always empty), `counts` (`processed` = files required), `failures` (`code: not_built`),
`result` (`tag`, `release_tag`, `release_sha`, `docs_sha`, `bin_dir`, `built` map,
`release_env`), `next` (the build commands)). Exit 0 ok; 2 unknown `--require` name (the
message lists the valid ones; plain argparse, so no JSON envelope even with `--json`); 3 a
required binary is missing. Without `--require` it always exits 0, even when files are
missing (the text lists them under `missing:`).

## Agent contract

`uv run python paintbot_pw_lab/tools/pw.py release [--require all|TOOL...] --json` (or the tool directly). Shared rules (envelope keys, exit codes, selector checks): [README.md § Agent contract](README.md#agent-contract), implemented once in `tools/pw_cli.py`.

| | |
| --- | --- |
| Inputs | `--tag TAG`, `--require all\|TOOL...` |
| Outputs | none |
| `--json` result | `{tag, release_tag, release_sha, docs_sha, bin_dir, built: {tool: bool}, release_env}` |
| Exit codes | 0 ok; 2 an unknown tool name; 3 a `--require`d file is missing (`next[]` names the build command) |
| Idempotence / cache | read-only |
| Typical next step | on exit 3 run `next[0]`; `pw.py doctor` covers this and more |

## Terrain cache

Since 0.3.89 (upstream #183) a `-d:pwTraining` build computes a whole 64 × 64 terrain block the
first time any point in it is read, so every short-lived process paid about 20 s for most of the
island: `pw_trace` 18.5 s per tape (0.7 s at 0.3.80), `pw_map` 25 s, each `pw_local` worker
~20 s on its first match. The engine can save a computed table and map it back read-only
(`topography.nim` `saveTerrain`/`loadTerrain`, `native_env.nim`
`pw_terrain_cache_save`/`pw_terrain_cache_load`); the lab uses that through
[`tools/pw_terrain.py`](../../tools/pw_terrain.py) (Python side: pruning, the cap, `pw_local`'s
library) and [`tools/pw_terrain_cache.nim`](../../tools/pw_terrain_cache.nim) (compiled into
`pw_trace` and `pw_map`).

- **What the terrain depends on:** the engine's source (a fingerprint of `topography.nim`,
  `maps.nim` and the table layout, checked on load) and eleven terrain flags that
  `configureRules` sets from the rules version (thresholds 11 … 35, `sim.nim` `configureRules`).
  Not the seed, the policies or the glory config. Generated maps (`--map twin-mesas`, …) are
  never tabled, so they never use the cache. Every rules ≥ 35 tape (all league tapes: 44, 48)
  and every local match share one table.
- **One file per (tag, flag set):** `<cache root>/terrain/<tag>/island-f<bits>.pwterrain`
  (`island-f2047` for rules ≥ 35), 621 MB, the whole world prewarmed. It is built once, by the
  first process to take the file's `flock` (`<file>.lock`, released by the OS when a process
  dies), in about 27 s. The engine writes it to a temporary name and renames it into place.
  Every later process (and every waiting one) maps it read-only through the page cache: the
  load itself takes about 1 ms. It is never rewritten, and nothing is written per run or per process.
- **Bounded:** every tool run prunes before it starts and again when it ends. It deletes other
  tags' directories (it keeps the `release.env` pin and the tag in use), deletes temporary files
  of builders that died (never while their lock is held), then deletes least-recently-used files
  until the total is ≤ `PW_TERRAIN_CACHE_MAX_GB` (default 2). A run that loads a file marks it
  recently used. With under 1.5 GB free and no file yet, a run goes uncached with a warning
  instead of filling the disk. A cap below one file (~0.62 GB) makes every run rebuild and then
  delete it: use `PW_TERRAIN_CACHE=0` instead.
- **Correctness:** results are identical with and without it. `loadTerrain` checks sampled cells
  against the direct terrain functions and rejects another build's file. `pw_trace`'s per-tick
  hash check covers every traced tape. A rejected file is never overwritten: the run continues
  uncached with a `WARNING` naming `pw.py terrain-cache clear`.
- **Who uses it:** `pw.py trace` / `map-raw`, `pw_episodes.py` (so every episode tool), `pw_mapdata.py`
  and `pw_local.py` set `PW_TERRAIN_CACHE_DIR` for the Nim binaries, or attach it to each libpw
  worker. A Nim binary run by hand without that variable is uncached, as before. So are an
  explicit `pw_episodes --binary` and builds from before 0.3.89 (they lack the engine calls).
  `pw_trace` and `pw_map` end their stdout line with `terrain=loaded|built|rejected|off`.
- **Compression:** not used. `gzip -1` shrinks the file to 57 MB, but the engine needs a plain
  file to map. macOS transparent compression (`ditto --hfsCompression`, which keeps mapping
  working) skipped the 621 MB file on this machine (it compressed a 500 MB prefix to 57 MB, but
  not 600 MB).

```bash
uv run python paintbot_pw_lab/tools/pw.py terrain-cache status --json   # files, sizes, last use, cap, free disk
uv run python paintbot_pw_lab/tools/pw.py terrain-cache clear --json    # delete every file (rebuilt on next use)
```

`--json` result: `status` gives `{root, enabled, cap_bytes, total_bytes, free_bytes, files: [{tag, file, path,
bytes, last_used}]}`, and `clear` gives the same plus `removed`. Exit 0; 2 usage (an unknown action, or a
`PW_TERRAIN_CACHE_MAX_GB` that is not a number ≥ 0).

Verified 2026-09-30 (coworld-v0.3.89, 14-core M-series Mac): `pw_trace` 0.25-0.38 s per tape warm
(18.4-19.1 s uncached), identical rows and summaries (except `elapsed_ms`) on the 3 rules-44 samples
and the 4 hosted `seed-pilot-2026-09-30` tapes. `pw_map` 0.08 s warm (25 s uncached), with
byte-identical `.bin`/`.json`/`.ppm`. A 16-match base-vs-base `local screen` took 10.6 s total warm, 33.0 s
cold (builds the file) and 50.5 s uncached (match phase 3.9 vs 0.56 matches/s), with the same 16 final
hashes in all three. Disk stayed at one 621 MB file after 10 traces, 10 `map-raw`s, 10 screens and 2
concurrent screens. A cold `pw_episodes --jobs 4` and a screen racing a trace each built exactly one
file (the others waited on the lock). A planted old-tag directory, an orphaned temporary file and an
older file over a 0.65 GB cap were all deleted by the next run.

## Moving to a new release

```bash
uv run python paintbot_pw_lab/tools/deployed_ref.py --write    # exit 1 = moved
paintbot_pw_lab/tools/build_tools.sh && paintbot_pw_lab/tools/build_native.sh
uv run python -m pytest -q paintbot_pw_lab/tools/tests tools/tests
```

Then read the DOCS diffstat `deployed_ref.py` prints; re-verify the docs and move `PW_DOCS_SHA`
by hand only when that is done. Trace caches are keyed by the `pw_trace` binary's hash and map
caches by tag, so both rebuild on the next load. The old tag's [terrain cache](#terrain-cache)
is deleted by the first tool run after the move, and the new tag's is built on first use.

## Verified (2026-09-30, 0.3.80 → 0.3.89)

- Moved with `deployed_ref.py --write` (exit 1, written); `PW_DOCS_SHA` moved by hand to
  `118e1619` (docs already re-verified there). The first build failed on the lab's own
  `inWater` import (0.3.89 removed `neural_contract.inWater`); with it defined locally in
  `pw_trace.nim` and `pw_map.nim`, `build_native.sh` built all six files, worktree HEAD
  `118e1619`, and `pw.py doctor` passes every local check.
- `pw_trace` 0.3.89 verified the 3 rules-44 samples, the 4 hosted `seed-pilot-2026-09-30` tapes
  and 4 fresh local base-vs-base recordings (11 of 11). Test suite: 211 passed.
- **Slower:** 0.3.89's `-d:pwTraining` terrain table computes a whole 64 × 64 block on first
  touch (#183), so every short-lived process pays for most of the island: `pw_trace` 18.5 s
  per tape (0.7 s at 0.3.80, same tape and hash), `pw_map` 25.8 s (0.2 s), a 16-match
  `local screen` 0.51 matches/s (0.98 at 0.3.80, same machine and load). The engine's own
  remedy (`saveTerrain`/`loadTerrain` shared cache files) is now wired in: see
  [Terrain cache](#terrain-cache) (0.25 s per trace warm).

## Verified (2026-09-29)

- Moved 0.3.78 → 0.3.79 with `deployed_ref.py --write`. `build_native.sh coworld-v0.3.79`
  (which runs `build_tools.sh`) built all six files; worktree HEAD `d0728ab`.
- `pw_trace` 0.3.79 verified the 3 rules-44 samples in `episode_data/20260928T214433_*`
  (ticks 1649 / 4108 / 2219) and 2 fresh local recordings (`pw_local.py match --record`:
  base vs jev seed 11, base vs base seed 12; library/headless parity ok, traces verified at
  hashes 4161423694 and 3937440839).
- Test suite: 135 passed (128 before plus 7 in `test_pw_release.py`).
