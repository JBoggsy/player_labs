# beacon v7 — peek-fire-duck micro (design)

**Goal.** Close the firefight gap vs `ctf-focusfire:v5` (v6 baseline: 0-9, out-killed
207-128, 23.9 deaths/game). Beacon's combat is stand-and-deliver: during the gun's
cooldown+windup it stands exposed (or walks its nav path in the open), and it pays its
aim traverse while visible. The baseline/focusfire lineage spends cooldown behind a wall
and pays aim traverse in cover, re-emerging with the shot pre-laid.

**Reference.** `players/baseline/baseline.nim` in coworld-ctf (ships with the game,
documented): the three-state fire → duck → peek cycle, `findDuckCell` / `findPeekCell`
(nearest reachable nav cell that breaks / opens a sight line, 3-cell search radius),
`DuckRange=340`, threat freshness ≤30 ticks, carrier + pedestal-rush exemptions.

## Behavior (one movement override in `resolve_action`)

Priority, checked when alive and `BEACON_PEEK_DUCK=1` (default on), and NOT carrying
and NOT in the final pedestal approach (within `PEEK_DUCK_RUSH_EXEMPT_PX` of the steal
target — grab speed beats safety there, mirroring the baseline's `pocketRush` exemption):

1. **Duck (gun down + threat near):** if `not fire_ready` and a fresh enemy track
   (age ≤ `DUCK_THREAT_FRESH_TICKS`, dist ≤ `DUCK_RANGE_PX`) exists: move to the
   nearest reachable cell the threat cannot see (`find_duck_cell`); hold there; keep
   the AIM on the threat (vision cone stays on the lane; combat overlay unchanged).
2. **Peek (gun up + target wall-blocked):** if `fire_ready` and the nearest fresh
   track is NOT line-of-sight visible: PRE-LAY aim on the (velocity-predicted) track
   position and sidestep to the nearest cell that opens the firing line
   (`find_peek_cell`). The existing fire logic takes the shot the tick the ray clears.
3. Otherwise: normal navigation (unchanged).

The combat overlay (snap-aim + fire gate + FF gate) is untouched; peek/duck only
override *movement* and, when ducking/peeking, the *desired aim*.

## New infrastructure

- **Pixel wall mask in `nav.npz`:** `bake_map.py` already computes `build_wall_mask()`
  (per-pixel, exactly sim.nim `isArenaWall`) but only ships the footprint-eroded grid —
  wrong for LoS (sight/bullets have no 6px body). Bake adds `wall` (bool [659,1235]).
  One-time rebake; geometry unchanged (verified byte-identical @ d60dc27).
- **`mapdata.ray_clear(a, b)`:** sampled segment test over the wall mask (~2px step,
  numpy-vectorized), mirroring the baseline's coarse ray. Used for both "threat sees
  cell" (duck) and "cell opens firing line" (peek), plus a walkable-grid reachability
  check from our cell (as the baseline does with `gridRayClear`).
- **First consumer of `belief.enemy_tracks`** (v6 groundwork): duck/peek key on
  remembered, velocity-predicted tracks, not just currently-visible enemies.

## Knobs (config.py, env-overridable)

`BEACON_PEEK_DUCK` (1), `BEACON_DUCK_RANGE_PX` (340), `DUCK_THREAT_FRESH_TICKS` (30),
`PEEK_TARGET_FRESH_TICKS` (24, baseline's `FreshShotTicks`), `PEEK_DUCK_SEARCH_CELLS`
(3), `PEEK_DUCK_RUSH_EXEMPT_PX` (90). No peek range cap needed: the gun is map-wide
(baseline `FireRange = 1250`), so any opened line is a valid shot.

## Validation

Unit tests: ray_clear across a known wall / open ring; duck cell breaks LoS; peek cell
opens LoS; carrier exemption. Then build+upload v7 and A/B **v7 (on) vs v6** against
`ctf-focusfire:v5` (2x10 eps, 8v8) — the single-bit change is the env default, so the
arms are v7-vs-focusfire and v6-vs-focusfire. Also re-run 1-2 field opponents to check
no regression (captures stay 10-0). Success: win ≥2 of 10 vs focusfire or a clear
deaths/kills improvement (deaths <20/game, kill ratio >0.75).

## Risks

- Duck oscillation (leave cover → get shot → re-duck): mitigated by peek pre-lay (we
  exit cover with the shot ready) and hold-still-when-arrived.
- Attackers stalling mid-push (duck loops instead of advancing): the rush exemption +
  duck requires a *fresh* (≤30 tick) threat; stale tracks don't pin us.
- Python ray cost: ~50 rays x ~200 samples worst case per tick — vectorized numpy,
  well under the ~15us belief budget's order of magnitude; measure in tests.
