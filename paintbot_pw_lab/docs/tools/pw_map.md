# pw_map + pw_mapdata.py: map geometry for plots

Map geometry for plots and spatial metrics: where the water, trenches, cover, hearts and
pickups are, as a terrain raster plus feature lists. `pw_map` (Nim, built by
`build_tools.sh`) samples the engine's own terrain predicates on a grid from `newWorld`.
`pw_mapdata.py` runs it once per (release, map, rules, step) and caches the result as `.npz` +
`.json` under `paintbot_pw_lab/tools/.cache/maps/<tag>/` (gitignored with the rest of
`tools/.cache/`); the cache file stem is `<map>-r<rules>-s<step>`, with `heartwick` for the
default map `""`. Part of the lab tool set: [tool index](README.md) (`pw.py map`,
`pw.py map-raw`).

### Cache location

Set `PW_CACHE_DIR` to keep the tools' caches outside the repo: the map rasters then go to
`$PW_CACHE_DIR/maps/<tag>/`. The same variable moves the per-release source worktree that
`build_tools.sh` / `build_native.sh` create (`$PW_CACHE_DIR/<tag>/`), which `pw_local.py` and
`pw_intent.py` read, so set it for the build too, or rebuild after changing it (`pw_local`
exits 3 naming the missing worktree). Binaries stay in `tools/bin/<tag>/`; per-episode trace
caches stay beside the episode ([pw_episodes.md](pw_episodes.md#cache-variants)). Resolved by
`pw_release.cache_root()` at call time.

```bash
PW_CACHE_DIR=/tmp/pw-cache uv run python paintbot_pw_lab/tools/pw.py map --tag coworld-v0.3.78 --json
```

## Commands

```bash
source paintbot_pw_lab/tools/release.env; B=paintbot_pw_lab/tools/bin/$PW_RELEASE_TAG
$B/pw_map OUT_PREFIX [--map NAME] [--rules N] [--step UNITS] [--ppm]   # raw export
uv run python paintbot_pw_lab/tools/pw_mapdata.py [--map NAME] [--rules 47] [--step 25] [--tag TAG] [--png OUT.png] [--json]
```

Defaults differ: raw `pw_map` uses the engine's `LiveRules` when `--rules` is omitted;
`pw_mapdata.py` (and `load_map`) default to rules 47 and step 25.

```python
from pw_mapdata import load_map, map_for_episode
m = load_map("", rules=47)                 # "" = Heartwick (the league's map)
m = map_for_episode(ep.meta)               # the map a traced episode played on
ax.imshow(m.heights, extent=m.extent)      # world z grows downward, like the viewer
m.water, m.blocked, m.trench, m.off_island # boolean masks (nz, nx); m.mask("blocked_for_cog")
m.meta["hearts"], m.meta["pickups"], m.meta["trenches"], m.meta["cover"], m.meta["homes"]
row, col = m.cell(x, z)
```

## Agent contract

`uv run python paintbot_pw_lab/tools/pw.py map --json` (or the tool directly). Shared rules (envelope keys, exit codes, selector checks): [README.md § Agent contract](README.md#agent-contract), implemented once in `tools/pw_cli.py`.

| | |
| --- | --- |
| Inputs | `--map NAME` ('' = Heartwick), `--rules N`, `--step U`, `--tag`, `--png FILE` |
| Outputs | cache `tools/.cache/maps/<tag>/<map>-r<rules>-s<step>.{npz,json}` (`$PW_CACHE_DIR/maps/<tag>/...` when set); `--png FILE`. The envelope's `outputs[]` lists only the `--png` file, never the cache (even when this run created it): read the cache paths from `result.cache_json` / `result.cache_npz` |
| `--json` result | `{map, cache_json, cache_npz, nx, nz, step, bounds, hearts, pickups, trenches, cover, water_share}` (counts, not the feature lists: read `cache_json` for those) |
| Exit codes | 0 ok; 2 `pw_map` failed for that map/rules (an unknown map; the engine's message, e.g. `Unknown Paintbot map: NAME`, is in `failures[0].message`); 3 `pw_map` not built for `--tag` (`next[0]` = `paintbot_pw_lab/tools/build_tools.sh [TAG]`) |
| Idempotence / cache | one run of `pw_map` per (release, map, rules, step); later calls read the cache |
| Typical next step | `viz` (it loads the same cache) |

The raw exporter is `pw.py map-raw [--tag TAG] OUT_PREFIX ...`: a Nim binary without the envelope (the dispatcher still exits 3 with an envelope under `--json` when it is not built). Its exit codes: 0 ok; 2 bad arguments (usage on stderr); 1 an unknown map (an unhandled engine exception).

## Output

- `OUT_PREFIX.json`: `schema_version`, `tool`, `bounds` [minX, minZ, maxX, maxZ], `step`, `nx`,
  `nz`, `height_range`, `layers`, `flag_bits`, `cog_radius` (55), `capture_radius` (140), `hearts` (`idx`, `pos`, initial
  `owner`), `pickups` (`idx`, `kind`, `pos`), `trenches` and `cover` as engine `Cover{x,z,w,h}`
  (`h == 0`: a circle of diameter `w` at (x + w/2, z + w/2); `cover_note` says the same), `homes`, `engine_release`, `rules`, `map`.
- `OUT_PREFIX.bin`: heights as int16 little-endian (nz × nx, row j is z = minZ + (j + ½)·step),
  then flags as uint8 (nz × nx): 1 water (`inWater`), 2 blocked at radius 0 (bounds, off
  island, cover), 4 trench, 8 off-island, 16 blocked for a cog centre (radius 55).
- `OUT_PREFIX.ppm` with `--ppm`: a quick-look image.

## Verified (2026-09-29, coworld-v0.3.78 and coworld-v0.3.79)

Heartwick at 25 units: 640 × 384 in 0.2 s, 10 hearts, 16 pickups, 6 trenches, 224 cover,
2.8% water (same on both builds; the 0.3.78 run used `PW_CACHE_DIR` and wrote
`$PW_CACHE_DIR/maps/coworld-v0.3.78/heartwick-r47-s25.{json,npz}`). The rendered image shows
the central lake, trenches and tree cover. `twin-mesas` exports too (640 × 384, 14 pickups,
144 cover, 46.6% water). `--map nosuchmap` exits 2; `--tag` of an unbuilt release exits 3. Not checked: the other generated maps and the
`blocked_for_cog` layer against real cog paths.
