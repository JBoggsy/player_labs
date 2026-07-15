# beacon version log

Version → change mapping for the CTF `beacon` policy. Newest first.

## v7 — peek-fire-duck micro (2026-07-15)

**Why:** v6 field eval vs `ctf-focusfire:v5` (the new #1): 0-9, out-killed 207-128,
23.9 deaths/game. Beacon's combat was stand-and-deliver — it stood exposed through the
gun's cooldown+windup and paid aim traverse while visible. The baseline/focusfire lineage
spends cooldown behind a wall and re-emerges pre-aimed (design doc:
`docs/designs/ctf-peek-fire-duck-design.md`; reference: `players/baseline/baseline.nim`).

**Changes:** (1) nav.npz now ships the raw per-pixel `wall` mask; `mapdata.ray_clear`
(sampled segment LoS, ~14us/map-length ray). (2) fire→duck→peek movement override in
`action.py`: gun down + fresh near threat (≤30 ticks, ≤340px) → sidestep to the nearest
cell that BREAKS the threat's line, hold, keep aim on its arc; gun up + fresh track
(≤24 ticks) wall-blocked → PRE-LAY aim and sidestep to the cell that OPENS the line
(combat overlay fires the tick it clears). Exempt while carrying and within 90px of the
steal pedestal. First consumer of the v6 tracks groundwork (velocity-predicted).
(3) knobs: `BEACON_PEEK_DUCK` (default ON — the A/B bit), `BEACON_DUCK_RANGE_PX`, etc.
~10us/tick worst case. 42 tests pass. Upload: `beacon:v7`.

## v6 — port to ctf 0.7.3 wire format (2026-07-14)

**Why:** the league redeployed ctf **0.7.3** (`cow_e7586b05…`, source `5450c64`,
GameVersion 2) — v5 is blind on the live game: since 0.6.0 map-layer observations arrive
at **3x map resolution** (all its position reads were 3x off), and since 0.7.0 the capture
objects are labeled `red/blue heart` (its `… flag` lookups matched nothing). Division
scores also reset (+1/-1 scoring now); old eval baselines are void.

**Changes (correctness port only — no behavior/strategy change):** (1) perception
`_center` recovers map px by `(wire + sprite/2) / RENDER_SCALE` (new `config.RENDER_SCALE
= 3`); all internals (nav.npz, thresholds, belief, traces) stay in map pixels. (2) heart
labels in the flag-state lookups. (3) belief docs/dead-state: death no longer lifts fog
(dead frames carry no sightings; own body is `corpse …`, never misread as a player).
Grenades (also new in 0.7.x) are deliberately IGNORED this version. Arena geometry is
unchanged upstream — nav.npz not rebaked. 36 tests pass (new wire-scale, heart-carry,
corpse regressions). Upload: `beacon:v6`.

## v5 — carrier escort + attack bias (2026-07-10)

**Why:** vs the baseline, v4 diag showed attackers DO reach the flag and DO carry it
(seats 5/7 maxX 1017/1055, i_carry True) but die before delivering — 3 solo attackers
can't escort the flag home through the baseline's coordinated defense + overwatch, and 5
defenders were wasted bodies (the baseline barely attacks our flag; captures ~0 both sides).

**Changes:** (1) new escort rung — when a teammate is carrying (enemy flag off-pedestal,
visible, not mine), attackers navigate to the carrier's position and move home *with* it,
so it isn't a lone target. (2) DEFENDER_COUNT 5→3 (3 hold our turf, 5 push+escort).
26 tests pass. Upload: `beacon:v5`.

## v4 — fix carry detection (the "stuck on the flag" bug) (2026-07-10)

**Why:** watched replays — attackers reached the enemy pedestal but never brought the
flag home; they got stuck ON the flag. Root cause (confirmed in `src/ctf/sim.nim` +
`global.nim` and against 38,204 logged snapshots where `i_carry` was `false` EVERY
time): a carried flag rides **~10px above** its carrier (`CarriedFlagLift=10`), so the
flag's observed centre sits ~10px from our self-sprite centre — but perception's carry
threshold was **6px**, so carry was NEVER detected. The carrier stayed in `steal` mode,
and the steal flow-field treats the pedestal it's standing on as "arrived" → it just sat
there.

**Fix:** `_CARRY_DIST` 6 → **24px** (clears the 10px lift with margin, well under the
distance to a teammate carrier). Reordered detection so the pedestal test (≤4px = resting
= stealable) precedes the carry test (off-pedestal + within 24px = we carry it), so
standing on the pedestal with the flag still resting isn't misread as carrying. 3 carry
regression tests reproduce the real sim geometry (grab / rest / midfield). 24 tests pass.
Upload: `beacon:v4`. **Expected:** attackers now run the flag home → actual CAPTURES,
which win the wipe-stalemate games outright and start taking games off the baseline.

## v3 — cover-seeking + friendly-fire gate (2026-07-10)

**Why:** v2 vs co-gas (15 eps) = 7-8 despite kills 227-0 and beacon losing FEWER lives —
its 6 deaths/game were ALL **friendly fire** (co-gas got 0 kills; friendly fire is ON and
beacon shot teammates in its own fire line). And v2 still lost 0-10 to the baseline because
defenders held in the OPEN vs the baseline's peek-fire-from-cover.

**Changes (this iteration):**
1. **Friendly-fire gate** — perceive same-colour "player" sprites as teammates; hold fire
   if a visible teammate is within ~22px of the shot ray and closer than the target.
2. **Cover-seeking defenders** — bake a cover grid (walkable cells adjacent to a wall,
   1850 of them) and snap defender hold points to the nearest cover cell, so they
   peek-fire from behind obstacles instead of standing in the open.
21 tests pass; FF-gate + role smoke verified. Upload: `beacon:v3`.

**Results (matched 8v8, 20 eps each):**
- vs co-gas-ctf-simple-richard:v4 → **19-0** (was 7-8 at v2). beacon deaths 3.4/game
  (was 6.1 — FF eliminated), co-gas wiped 22.7/game, kills 496-0.
- vs ctf-baseline-16:v4 (rank-1 champion) → still 0-20, but trades improved (beacon
  deaths 24→22.8/game, kills 162→345 vs v2). The elite Nim baseline remains unbeaten.

**SUBMITTED** to the CTF league (`sub_6f0eb779…`, `--auto-champion always`), membership
`lpm_d3691543…`, 2026-07-10. Placed; qualifying async in Qualifiers(staging).
beacon is the clear #2 in the 3-policy division (dominates both co-gas variants).

## v2 — seat-based roles, defensive bias (2026-07-10)

**Why:** v1 lost 0-12 vs ctf-baseline-16:v4. Diag showed every game decided by WIPE
(0 captures both sides); beacon fully wiped (288 deaths) rushing 8-abreast into the
enemy's defended pedestal (far respawn walk-back). Games are won by *surviving*, not
capturing (see TENTATIVE_LESSONS).

**Change (one lever):** seat-based roles. Seats 0-4 = **defenders** holding cover on our
own turf (choke x≈390 mirror, spread across a y-band); seats 5-7 = **attackers** still
pushing the flag. New rungs: carry-home (all) > intercept a *visible* thief (all) >
defender hold / attacker steal. Knobs: `BEACON_DEFENDERS` (5), `BEACON_HOLD_ARRIVE_PX`.
18 tests pass; v2 role smoke verified. Upload: `beacon:v2`.

## v1 — minimal complete loop (2026-07-10)

First version. Deterministic Player-SDK SpriteV1 cyborg (design:
`ctf_lab/docs/designs/ctf-player-v1-design.html`).

- **Nav:** offline-baked 8px walkable grid + two Dijkstra flow fields per team
  (steal → enemy pedestal, home → own capture zone); online A* fallback for
  arbitrary goals. `tools/bake_map.py` → `mapdata/nav.npz`.
- **Strategy:** priority ladder — carry enemy flag home > steal enemy flag.
- **Aim (lighthouse):** sweep ±32 brads across the threat axis (unit vector to
  enemy pedestal); snap onto the nearest visible enemy and fire through a
  geometric fire-gate; edge-triggered A, no rotation on the firing tick.
- **Perception:** sprite-label lookups (self/player/aim-dot/flag/fire-icon).
- Team from slot parity (even=red, odd=blue). Keepalive disabled (ping_interval=None).
- 12 unit tests pass; container import + synthetic-frame smoke verified.

Upload: `beacon:v1` (tags purpose=v1-minimal-loop, lab=ctf).
