# pw_map + pw_mapdata.py: map geometry for plots (T8)

`pw_map` (Nim, built by `build_tools.sh`) samples the engine's own terrain predicates on a
grid from `newWorld`. `pw_mapdata.py` runs it once per (release, map, rules, step) and
caches the result as `.npz` + `.json` under `paintbot_pw_lab/tools/.cache/maps/<tag>/`
(gitignored with the rest of `tools/.cache/`).

## Commands

```bash
source paintbot_pw_lab/tools/release.env; B=paintbot_pw_lab/tools/bin/$PW_RELEASE_TAG
$B/pw_map OUT_PREFIX [--map NAME] [--rules N] [--step UNITS] [--ppm]   # raw export
uv run python paintbot_pw_lab/tools/pw_mapdata.py [--map NAME] [--rules 47] [--step 25] [--png OUT.png]
```

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
| Outputs | cache `tools/.cache/maps/<tag>/<map>-r<rules>-s<step>.{npz,json}`; `--png FILE` |
| `--json` result | `{map, cache_json, cache_npz, nx, nz, step, bounds, hearts, pickups, trenches, cover, water_share}` (counts, not the feature lists: read `cache_json` for those) |
| Exit codes | 0 ok; 2 `pw_map` failed for that map/rules (an unknown map); 3 `pw_map` not built (`next[0]` = `paintbot_pw_lab/tools/build_tools.sh`) |
| Idempotence / cache | one run of `pw_map` per (release, map, rules, step); later calls read the cache |
| Typical next step | `viz` (it loads the same cache) |

The raw exporter is `pw.py map-raw [--tag TAG] OUT_PREFIX ...`: a Nim binary without the envelope (the dispatcher still exits 3 with an envelope under `--json` when it is not built).

## Output

- `OUT_PREFIX.json`: `bounds` [minX, minZ, maxX, maxZ], `step`, `nx`, `nz`, `height_range`,
  `flag_bits`, `cog_radius` (55), `capture_radius` (140), `hearts` (`idx`, `pos`, initial
  `owner`), `pickups` (`idx`, `kind`, `pos`), `trenches` and `cover` as engine `Cover{x,z,w,h}`
  (`h == 0`: a circle of diameter `w` at (x + w/2, z + w/2)), `homes`, `engine_release`, `rules`, `map`.
- `OUT_PREFIX.bin`: heights as int16 little-endian (nz × nx, row j is z = minZ + (j + ½)·step),
  then flags as uint8 (nz × nx): 1 water (`inWater`), 2 blocked at radius 0 (bounds, off
  island, cover), 4 trench, 8 off-island, 16 blocked for a cog centre (radius 55).
- `OUT_PREFIX.ppm` with `--ppm`: a quick-look image.

## Verified (2026-09-29, coworld-v0.3.78)

Heartwick at 25 units: 640 × 384 in 0.2 s, 10 hearts, 16 pickups, 6 trenches, 224 cover,
2.8% water. The rendered image shows the central lake, trenches and tree cover. `twin-mesas`
exports too (640 × 384, 144 cover). Not checked: the other generated maps and the
`blocked_for_cog` layer against real cog paths.
