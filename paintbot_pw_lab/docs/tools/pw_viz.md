# pw_viz.py: movement diagrams, heatmaps, timelines (T9)

Draws traced episodes (the [episode tables](tables.md)) over the release's terrain raster
([pw_map](pw_map.md)). matplotlib only. Every command writes a PNG (or GIF) and a JSON of exactly
the data it plotted, with the same stem. Colours follow the Softmax Ink & Print house style:
warm paper background, Ember = terracotta `#b4532a`, Azure = ink blue `#1f4c9a` (the pair passes the
dataviz palette validator for colour-blind separation and contrast), neutral grey for unowned hearts,
one navy ramp for densities.

## Commands

Run from the repo root. Roots are anything `pw_episodes.py` accepts (episode dirs, batch dirs,
`NAME.replay`). Episodes that fail to load are printed as `FAILED [code] … (not plotted)` and make
the exit code 1; the rest are still drawn.

```bash
T=paintbot_pw_lab/tools/pw_viz.py     # or: uv run python paintbot_pw_lab/tools/pw.py viz ...
uv run python $T movement  ROOT... --from 0:40 --to 1:05 [--seats 3,5 | --team 0 | --policy KEY] [--bbox x0,z0,x1,z1] [--no-shots] [--fine] [--out m.png]
uv run python $T heatmap   ROOT... [--policy KEY] [--team 0|1] [--kind density|deaths] [--normalize-side] [--out h.png]
uv run python $T occupancy ROOT... --policy A --policy B [--team 0|1] [--raw-sides] [--out o.png]
uv run python $T timeline  ROOT... [--out t.png]          # several episodes: t-<episode>.png each
uv run python $T gif       EPISODE --from 0 --to 12s [--team 1] [--bbox …] [--out a.gif]
```

Without `--out` the files go to `paintbot_pw_lab/analysis/pw_viz/<episode id | batch-<hash>>/`
under a name built from the command and selectors (see Agent contract below), so a rerun with
the same arguments overwrites its own image.

- **Times**: `1500` = tick, `62.5s` = seconds, `1:10` = m:ss (24 ticks/s). Ticks use the table
  convention (`t` = world tick after the step). `--from`/`--to` apply to `movement` and `gif`
  only. A `--from` at or after the end of every match is a usage error (exit 2) that lists each
  episode's length; the sample league episode lasts 1:08.7, so `--from 1:10` is refused there.
  A `--to` past a match's end is clamped to its last tick and reported.
- **`--policy`** matches `policy_key` (the exact `policy_version_id`, or `local:<name>`) or
  `policy_name`. `--seats`, `--team` and `--policy` combine (all must hold). An unknown policy or
  seat, or a combination that matches no seat in any episode, is exit 2 with the valid values.
- **`--fine`** re-traces with every-tick states for the window (`TraceOptions(window=…)`). The
  result is cached as its own variant (`pw_cache@se6-ve0-w<A>_<B>/` beside the default
  `pw_cache/`, see [pw_episodes.md](pw_episodes.md#cache-variants)), so it never replaces the
  default trace other tools read.
- **`--tag`** picks the release build for both the trace (its own cache variant when it is not
  the pinned tag) and the terrain raster (`maps/<tag>/`), so a plot of an old-rules episode uses
  that release's map. That tag needs `pw_trace` and `pw_map` built (`build_tools.sh <tag>`).
- **`PW_CACHE_DIR`** (env var): where the map rasters are cached, `$PW_CACHE_DIR/maps/<tag>/`
  instead of `paintbot_pw_lab/tools/.cache/maps/<tag>/`. Point it at a scratch directory to keep
  a run from writing into the repo (see [pw_map.md](pw_map.md#cache-location)).

## Agent contract

`uv run python paintbot_pw_lab/tools/pw.py viz COMMAND ROOT... --json` (or the tool directly). Shared rules (envelope keys, exit codes, selector checks): [README.md § Agent contract](README.md#agent-contract), implemented once in `tools/pw_cli.py`.

| | |
| --- | --- |
| Inputs | `movement\|heatmap\|occupancy\|timeline\|gif`, roots; `--from/--to` (movement, gif only), `--seats`, `--team`, `--policy` (twice for occupancy), `--kind`, `--bbox`, `--out`, `--fine`, `--tag` |
| Outputs | an image plus a JSON of the plotted data. Default: `paintbot_pw_lab/analysis/pw_viz/<episode id \| batch-<hash>>/<command>[-<kind>][-t<from>-<to>][-team<n>][-seats<list>][-<policy>].png` (`.gif` for gif); `--out FILE` overrides; timeline over several episodes adds `-<episode>` |
| `--json` result | `{images: [...], data: [...], window: {from_tick, to_tick, match_end_ticks, clamped_to_end, starts_after_end} or null, episodes: [...]}` |
| Exit codes | 0 ok; 1 some episodes failed to load or verify (the rest are used; one `failures[]` entry each, `counts.failed_by_code`); 2 usage error: bad arguments, roots with no episode, or an unknown selector (`--policy`, `--seats`, a filter matching no seat, a `--from` at or after the end of every match, `--to` before `--from`, `--from/--to` on a command without a window; `result.valid` lists the valid values); 3 `pw_trace` not built (`next[0]` = `paintbot_pw_lab/tools/build_tools.sh`) |
| Idempotence / cache | same inputs, same path: a rerun overwrites its own image. `--fine` and a non-pinned `--tag` trace into their own cache variant; map rasters go to `$PW_CACHE_DIR/maps/<tag>/` (default `tools/.cache/maps/<tag>/`) |
| Typical next step | Read the PNG before describing it, and check one drawn event with `episodes --sql` |

A `--to` past a match's end is clamped to its last tick and reported (`result.window.clamped_to_end`, a note on stderr). In small multiples, an episode that ended before `--from` gets an empty panel titled so (`starts_after_end`); only a window past the end of **every** episode is refused.

## What each figure shows

- **movement**: one panel per episode (small multiples, 2 columns when several). Per seat, a
  polyline of its state samples in the team colour, **broken at every dead sample and every respawn**
  (never joining a death spot to a spawn point), a dot at each stretch's start, arrowheads every
  48 ticks and at the end, and the seat number at the last visible point. Markers: kill × at the
  killer's position at the fatal blow (from `damage.attacker_x/z`), death ○ at the victim, capture ◆
  at the heart, pickup ▲, grenade blast ring (radius 360 at rules ≥ 40, else 270), shot rays (hits:
  full line to the victim; misses: the first 600 units, dotted). Hearts are coloured by their exact
  owner at the window's end (t = 0 owners + `capture_complete`), with a faint 140-unit capture circle.
  Deaths, kills, pickups, blasts and shots are limited to the selected seats; captures are shown
  for both teams. With `--policy`, each panel title says which side the policy played and who it
  played against; a panel with no matching seats says so instead of silently showing an empty map.
- **heatmap**: hexbin of alive state samples (`density`) or of death positions (`deaths`) for the
  selected seats across all episodes. Hearts drawn with their t = 0 owners. `--normalize-side`
  rotates Azure seats 180° onto Ember's side (see below).
- **occupancy**: two policies side by side, share of alive samples per 250-unit cell, and the
  **Bhattacharyya overlap** `Σ √(p·q)` of the two normalized grids (1 = same distribution, 0 = never
  the same cell; null when a policy has no samples). **Side normalization is on by default**: the
  maps are point-symmetric about the midpoint of the two homes, so without it two policies that
  played opposite sides look different just because of the side (measured on the samples:
  daveey-pw-neural vs aaron-paintbot-pw overlap 0.059 raw vs 0.284 normalized). `--raw-sides` turns
  it off. Normalization refuses (ValueError) on a map whose hearts are not point-symmetric.
- **timeline**: four stacked panels sharing a m:ss axis: meter (points) with the win line, glory
  (unsettled running value; the label gives the final settled value), kill and capture ticks per
  team, and the exact heart-ownership strip per heart. No dual axes.
- **gif**: one frame per state sample (at most 240), 3-second trails, positions labelled by
  seat, events of the last second, hearts at the frame's owners. ~1 MB and ~15 s for 12 s of
  one team.

## JSON beside each image

`movement`: `{"kind", "panels": [{episode_id, from_tick, to_tick, seats, bbox, state_every,
hearts_at_end: [{heart, x, z, owner}], trails: [{seat, team, segment, points: [[t, x, z]]}],
events: {kills, deaths, captures, pickups, blasts, shots}}]}` — event rows carry `t`, `seat`, `team`
and the plotted `x/z` (shots: `x0,z0,x1,z1` as drawn, `hit`, `victim`). `heatmap`: `points`,
`count`, `normalize_side`. `occupancy`: `grids` (counts per cell, rows = z), `extent`, `cell`,
`samples`, `bhattacharyya`, `normalize_side`. `timeline`: `t`, `meter_ticks`, `glory`, `kills`,
`captures`, `heart_ownership` (`[start, end, owner]` per heart). `gif`: `frames` (ticks), `fps`.

## Python

```python
import pw_viz as pv
pv.plot_movement([ep], Path("m.png"), 1680, 2400, team=0)          # returns the JSON dict
pv.movement_panel(ax, ep, mapdata, t0, t1, seats, bbox=...)       # draw into your own axes
pv.plot_timeline(ep, Path("t.png"), moments=None)
pv.trail_segments(states_of_one_seat, spawn_ticks); pv.heart_owners_at(ep, t); pv.bhattacharyya(a, b)
pv.to_ember_side(frame, ep.meta); pv.parse_time("1:10")
```

## Verified (2026-09-29, coworld-v0.3.78 build)

- All commands ran on the three rules-44 samples in `episode_data/` (and the report ran on
  13 episodes); every PNG was looked at and fixed for legibility (labels off-panel, crowded
  labels, raw version ids in titles, empty panels).
- **Known-moment check**: episode `ereq_5092af64…`, kill at t = 65 (seat 13 → seat 8, gun, 3,935
  units). The diagram puts × at (5670, 1184), the hit ray ending at (1788, 1778), ○ at (1773, 1730),
  and seat 8's trail restarting at H0 after its t = 137 respawn, all matching `kills`, `shots`
  and `spawns`. With `--fine` seat 8's trail ends at t = 64, the tick before the kill.
- Tests: `tools/tests/test_pw_viz.py` (time parsing, trail breaks, heart owners, overlap, side
  normalization, moment selection).

Not verified: against the web viewer at the same tick (no hosted viewer run here); local
`NAME.replay` episodes (none were on disk; the code paths are the same tables); FFA or generated
maps; a batch heatmap over 100+ episodes (it loads every episode's tables into memory).

## Limits

- Trails are state samples (every `state_every` = 6 ticks by default): a cog can move ~40 units
  between samples, and very short lives can be one point. Use `--fine` for tick-exact paths.
- Shot rays for misses are truncated for legibility; the full ray is in the `shots` table.
- Dense windows (16 seats, 30 s, shots on) are busy by nature; narrow with `--team`, `--seats`,
  `--bbox`, `--no-shots` or a shorter window.
- The GIF is slow-ish (one matplotlib redraw per frame) and meant for short windows.
