# release.env and pw_release.py — the one release pin

[`tools/release.env`](../../tools/release.env) is the single source of truth for which
paintbot-pw release the lab uses. Nothing else in the lab should hold a tag literal.

```
PW_RELEASE_TAG=coworld-v0.3.79   # the build every tool defaults to (tools/bin/<tag>/)
PW_RELEASE_SHA=d0728ab1          # its commit
PW_DOCS_SHA=570174a2             # where the mechanics/policy docs' line citations are exact
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
| `deployed_ref.py` | compares with the league; `--write` updates the tag and sha lines in place |
| shell docs | `source paintbot_pw_lab/tools/release.env; B=paintbot_pw_lab/tools/bin/$PW_RELEASE_TAG` |

## Python API (`tools/pw_release.py`)

```python
import pw_release                      # with paintbot_pw_lab/tools on sys.path
pw_release.current_tag()               # 'coworld-v0.3.79'
pw_release.current_sha()               # 'd0728ab1'
pw_release.docs_sha()                  # '570174a2'
pw_release.bin_dir(tag=None)           # Path to tools/bin/<tag>/
pw_release.require_built("pw_trace")   # Path, or raises pw_release.NotBuilt (exit_code 3)
pw_release.require_built_or_exit("pw_map", tag)   # CLI paths: prints the fix, exits 3
pw_release.cache_root()                # $PW_CACHE_DIR, else tools/.cache/ (read at call time)
pw_release.release_tree(tag=None)      # <cache root>/<tag>/: build_tools.sh's source worktree
```

`PW_CACHE_DIR` moves the tools' rebuildable caches out of the repo: the release worktrees
(`build_tools.sh`/`build_native.sh` use `${PW_CACHE_DIR:-tools/.cache}/<tag>`) and the map
rasters (`maps/<tag>/`, [pw_map.md](pw_map.md#cache-location)). Binaries stay in `tools/bin/`.

`NotBuilt`'s message is `<path> is missing: run paintbot_pw_lab/tools/build_tools.sh` (with the
tag appended when it is not the current one); `libpw.dylib`/`libpw.build.json` name
`build_native.sh`. Known tools: `paintbot-headless`, `replay_stats`, `pw_trace`, `pw_map`,
`libpw.dylib`, `libpw.build.json`; anything else is a `ValueError` listing them.

## CLI

```bash
uv run python paintbot_pw_lab/tools/pw_release.py                        # pins + built/missing
uv run python paintbot_pw_lab/tools/pw_release.py --json --require all   # exit 3 if anything is missing
uv run python paintbot_pw_lab/tools/pw_release.py --tag coworld-v0.3.78 --require pw_trace
```

`--json` prints one object (`ok`, `tool`, `release_tag`, `inputs`, `outputs` (always empty),
`counts`, `failures` (`code: not_built`), `result` (`tag`, `release_tag`, `release_sha`,
`docs_sha`, `bin_dir`, `built` map, `release_env`), `next` (the build commands)). Exit 0 ok;
2 unknown `--require` name (the message lists the valid ones); 3 a required binary is missing.

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

## Moving to a new release

```bash
uv run python paintbot_pw_lab/tools/deployed_ref.py --write    # exit 1 = moved
paintbot_pw_lab/tools/build_tools.sh && paintbot_pw_lab/tools/build_native.sh
uv run python -m pytest -q paintbot_pw_lab/tools/tests tools/tests
```

Then read the DOCS diffstat `deployed_ref.py` prints; re-verify the docs and move `PW_DOCS_SHA`
by hand only when that is done. Trace caches are keyed by the `pw_trace` binary's hash and map
caches by tag, so both rebuild on the next load.

## Verified (2026-09-29)

- Moved 0.3.78 → 0.3.79 with `deployed_ref.py --write`. `build_native.sh coworld-v0.3.79`
  (which runs `build_tools.sh`) built all six files; worktree HEAD `d0728ab`.
- `pw_trace` 0.3.79 verified the 3 rules-44 samples in `episode_data/20260928T214433_*`
  (ticks 1649 / 4108 / 2219) and 2 fresh local recordings (`pw_local.py match --record`:
  base vs jev seed 11, base vs base seed 12; library/headless parity ok, traces verified at
  hashes 4161423694 and 3937440839).
- Test suite: 135 passed (128 before plus 7 in `test_pw_release.py`).
