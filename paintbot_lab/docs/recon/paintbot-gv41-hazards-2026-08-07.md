# Recon: Paintbot GV41 barrage, puddles, and 0.7.209-0.7.211

## Mission

Determine what changed in canonical Paintbot after 0.7.208, quantify the new
grenade-barrage endgame (schedule, launch density, contraction, coverage, and
damage), establish whether paint puddles are active in the live league, and map
the changes Stencil needs. This is an investigation and implementation handoff;
no player behavior was changed.

## Executive summary

- Canonical Paintbot is now **0.7.211**, built from `coworld-ctf` commit
  `9dedac0ed6011aeca92bf2c6403b0e70c955f461` (live `coworld show`, checked
  2026-08-07). The three releases after the lab's documented 0.7.208 are:
  **0.7.209 / PR #250** (replay-seek mask fix), **0.7.210 / PR #249**
  (GV41 barrage), and **0.7.211 / PR #251** (puddle implementation).
- The barrage is live in every Paintbot gameplay variant. Normal 5:00 variants
  begin at **4:30 elapsed** (30 seconds remaining), ramp from **4 to 15 shells/s**
  for 30 seconds, and reach full-board eligibility at **5:00**. `4ffa8` retains
  its 7,500-tick / 5:12.5 clock, so it begins at **4:42.5** and saturates at
  **5:12.5**. The manifest values are identical otherwise
  (`coworld-ctf@9dedac0/coworld_manifest_paintbot.json:580-602`,
  `:712-734`, `:940-963`, `:1075-1094`, `:1206-1226`).
- Reaching 0:00 no longer ends a barrage-enabled game. Full-intensity fire
  continues at 15/s until at most one team is alive; a draw requires the last
  surviving teams to die on the same tick
  (`coworld-ctf@9dedac0/src/ctf/sim.nim:2232-2240`). GV41 also removed the old
  action-floor overtime, even in barrage-off games
  (`coworld-ctf@9dedac0/src/ctf/sim_types.nim:21-30`).
- Paint puddles are implemented but **not active in canonical Paintbot today**.
  `mapPuddles` defaults to zero, none of the live variants sets it, and the
  0.7.211 public config schema does not expose `mapPuddles` or
  `puddleDamagePct`. A custom/pinned map can contain puddles, but current normal
  league generation cannot produce them without another manifest/config change.
- Stencil currently ignores the barrage marker, ignores visible airborne
  grenades, and has no puddle map. Its existing grenade-clear objective only
  consumes warnings received through Stencil's own chat protocol
  (`paintbot_lab/paintbot/stencil_nim/perception.nim:132-150`,
  `paintbot_lab/paintbot/stencil_nim/belief_update.nim:198-223`,
  `paintbot_lab/paintbot/stencil_nim/strategy.nim:67-77`). The first player
  change should therefore be **barrage/shell perception and evasion**, not a
  blind strategic center rush.

## Directory map

```text
coworld-ctf@9dedac0/
  coworld_manifest_paintbot.json       deployed variant schedules
  src/ctf/sim_types.nim                GV41 and weapon/hazard constants
  src/ctf/sim_config.nim               defaults, parsing, validation, replay echo
  src/ctf/sim.nim                      barrage/puddle runtime and win clock
  src/ctf/arena.nim                    puddle geometry and placement
  src/ctf/labels.nim                   policy-visible marker contracts
  src/ctf/global.nim                   player/broadcast marker emission
  src/ctf/replays.nim                  PR #250 restore path
  tests/test_barrage.nim               barrage contract tests
  tests/test_puddles.nim               puddle contract tests

paintbot_lab/paintbot/stencil_nim/
  protocols.nim                        retained Sprite-v1 labels/static metadata
  perception.nim                       scene -> memoryless PaintState
  types.nim                            PaintState and shared runtime types
  belief_state.nim / belief_update.nim persistent tactical state
  worldmap.nim / nav.nim               static geometry and route selection
  strategy.nim / action.nim            objective ladder and controller
```

## Findings

### 1. Exact grenade-barrage schedule

The deployed configuration is:

| Variant | Clock | Barrage latches | Saturates | Start rate | Max rate |
|---|---:|---:|---:|---:|---:|
| `2v2` | 7,200 ticks = 5:00 | 4:30 elapsed | 5:00 | 4/s | 15/s |
| `4ffa` | 7,200 ticks = 5:00 | 4:30 elapsed | 5:00 | 4/s | 15/s |
| `default` | 7,200 ticks = 5:00 | 4:30 elapsed | 5:00 | 4/s | 15/s |
| `1v1` | 7,200 ticks = 5:00 | 4:30 elapsed | 5:00 | 4/s | 15/s |
| `4ffa8` | 7,500 ticks = 5:12.5 | 4:42.5 elapsed | 5:12.5 | 4/s | 15/s |

The latch condition is remaining ticks `<= barrageStartSec * 24`; it records a
permanent latch and returns without launching on that tick
(`coworld-ctf@9dedac0/src/ctf/sim.nim:2429-2448`). Thereafter both depth and
rate use the same linear progress

```text
p(t) = clamp(t / 30s, 0, 1)
rate(t) = 4 + 11 p(t) shells/s
depth(t) = 40 + (D - 40) p(t) pixels
D = floor(min(map width, map height) / 2) + 1
```

(`coworld-ctf@9dedac0/src/ctf/sim.nim:546-581`). Thus at 15 seconds the true
rate is **9.5/s** and at 30 seconds it is **15/s**. The 30-second ramp launches
exactly **285 shells** at the default 24 Hz schedule; after that, each extra
second of play launches 15 more.

Launch pacing is an accumulator, so shells are spread rather than emitted in
one burst (`coworld-ctf@9dedac0/src/ctf/sim.nim:2449-2461`). At the 4/s start,
the first shell launches six ticks (0.25s) after the latch. Its fixed flight is
`2 * fireWindupTicks = 10` ticks, so the first blast occurs about **16 ticks /
0.67s after the latch** (`coworld-ctf@9dedac0/src/ctf/sim.nim:2417-2427`,
`coworld-ctf@9dedac0/src/ctf/sim_types.nim:468-472`; the deployed windup default
is five ticks at `src/ctf/sim_config.nim:20-28`).

One observability wrinkle: the stated marker publishes
`barrageRatePermille div 1000`, so it reports an integer truncated downward.
At the true 9.5/s midpoint, the bot-visible label says `rate 9`
(`coworld-ctf@9dedac0/src/ctf/global.nim:5933-5960`). Use the schedule math for
exact density; use the marker rate as a coarse live readback.

### 2. Coverage, contraction, and spatial density

Each shell independently chooses one of the four edges with equal probability,
then chooses an inset uniformly in `[0, depth)` and a coordinate uniformly
along that edge. The landing is clamped just inside the arena border
(`coworld-ctf@9dedac0/src/ctf/sim.nim:2383-2427`). The possible-center region is
therefore the union of four edge bands. Before the small border clamp, its area
fraction is:

```text
coverage(d) = 1 - max(W - 2d, 0) * max(H - 2d, 0) / (W * H)
```

Depth grows linearly. The central target-ineligible rectangle contracts at
**`2 * (D - 40) / 30` pixels/second on each dimension** until the shorter-axis
bands meet. This is eligibility, not a hard flood wall: blasts are stochastic,
and their radius reaches beyond the band.

Initial and midpoint possible-center coverage by generated map class:

| Map family / size | Dimensions | Start depth / coverage | 15s depth / coverage | 30s |
|---|---:|---:|---:|---:|
| 2-team small | 1050x560 | 40px / 20.8% | 160px / 70.2% | 100% |
| 2-team standard | 1235x659 | 40px / 17.8% | 185px / 69.3% | 100% |
| 2-team large | 1606x857 | 40px / 13.9% | 234px / 67.8% | 100% |
| 2-team huge | 2223x1186 | 40px / 10.1% | 317px / 66.7% | 100% |
| 2-team giant | 3211x1713 | 40px / 7.0% | 448px / 65.6% | 100% |
| 4-team small | 816x816 | 40px / 18.6% | 224px / 79.7% | 100% |
| 4-team standard | 960x960 | 40px / 16.0% | 260px / 79.0% | 100% |
| 4-team large | 1248x1248 | 40px / 12.4% | 332px / 78.1% | 100% |
| 4-team huge | 1728x1728 | 40px / 9.0% | 452px / 77.3% | 100% |
| 4-team giant (`4ffa8`) | 2496x2496 | 40px / 6.3% | 644px / 76.6% | 100% |

The dimensions follow the five size scales and the 1235x659 two-team or
960x960 four-team shells (`coworld-ctf@9dedac0/src/ctf/arena.nim:1350-1379`,
`:1651-1668`). Campaign cells may use rectangular quad-mirror four-team maps;
for those, use their stated wire dimensions with the same formula.

**“Full coverage” does not mean uniform density.** Corners are selectable from
two adjacent edges and are hotter during the ramp. At full depth a square map
is approximately uniform because every point receives one horizontal-edge and
one vertical-edge contribution. A rectangular two-team map remains edge-biased:
the north/south half of the launches reaches the full board, while the
east/west half remains concentrated in side bands of depth `H/2`. On a standard
1235x659 board at saturation, a point in a side band has about **2.9x** the
landing-center density of a point in the central longitudinal band. Center play
is therefore lower risk, not safe.

Also distinguish landing-center coverage from damage reach. Barrage shells are
ordinary grenades: open-ground damage is **2 hp**, same-trench damage **6 hp**,
and damage to a victim in another trench **1 hp**. The nominal radius is 52px,
but collision against the player's 6px half-body produces a 58px on-axis reach
(`coworld-ctf@9dedac0/src/ctf/sim_types.nim:473-484`,
`src/ctf/sim.nim:1358-1438`). Shields absorb first. Environmental shells grant
no kill credit, and lethal hits report “shelled by the grenade barrage”
(`coworld-ctf@9dedac0/src/ctf/sim.nim:1469-1485`). Permanent floor stains from
grenades remain cosmetic; they do **not** become paint puddles
(`coworld-ctf@9dedac0/src/ctf/sim.nim:1386-1403`).

### 3. What policies can observe

When barrage mode is configured, every player stream receives an invisible
marker on every rendered state:

```text
grenade barrage depth <n> rate <n> start <n> sat <n>
```

Depth and rate are zero before the latch. The marker is explicitly emitted to
player views, not just the broadcast
(`coworld-ctf@9dedac0/src/ctf/labels.nim:359-368`,
`src/ctf/global.nim:6207-6209`). Airborne shells are ordinary fog-gated
`grenade air` objects; their displayed motion is linear from their edge source
to their landing target over ten ticks
(`coworld-ctf@9dedac0/src/ctf/global.nim:5286-5347`,
`src/ctf/sim.nim:1265-1269`). Visible blasts use `blast stage <n>` and unseen
landings produce the existing jittered `grenade sound` ring
(`coworld-ctf@9dedac0/src/ctf/global.nim:5399-5449`).

Stencil retains all sprite labels generically, so the new objects do not break
the protocol decoder (`paintbot_lab/paintbot/stencil_nim/protocols.nim:193-278`).
But perception only recognizes the stationary `grenade` pickup and the
post-impact `grenade sound`; it does not recognize `grenade air`, `blast stage`,
or the barrage marker (`paintbot_lab/paintbot/stencil_nim/perception.nim:132-150`).
The current `clear_grenade` objective reads only `belief.grenadeWarnings`, which
are populated by decoded teammate `G` chat messages; those messages describe
Stencil's own planned throws, not environmental shells
(`paintbot_lab/paintbot/stencil_nim/chat.nim:190-205`,
`belief_update.nim:198-223`, `strategy.nim:67-77`).

### 4. Paint puddle behavior and current activation state

Puddles are unions of one 26-30px core disc and 2-4 smaller lobes, with a hard
45px maximum reach from the anchor (`coworld-ctf@9dedac0/src/ctf/arena.nim:
1290-1313`). Actual membership is the disc union, not the bounding box
(`coworld-ctf@9dedac0/src/ctf/arena.nim:921-946`). This corrects a stale section
of the design doc that still describes a 64px square; the merged implementation
and RULES are authoritative.

For every full **24 ticks / one second of continuous center-point occupancy**,
the game rolls a default **10% chance of 1 damage**. Leaving for even one tick,
dying, or respawning resets the clock. Damage goes through shield first;
puddles do not slow motion or firing and do not block shots or vision
(`coworld-ctf@9dedac0/src/ctf/sim.nim:2335-2381`,
`src/ctf/sim_types.nim:570-581`). At 3 base hp, an unshielded player who never
leaves has an expected 30 seconds to death, but the distribution is broad and
each one-second roll is avoidable by briefly exiting.

`mapPuddles` is an exact requested count, 0-64, on generated two-team maps only.
Pairs are map-symmetric; an odd request adds a symmetric center splat. Placement
avoids walls, trenches, existing puddles, and base pockets, and may produce
fewer than requested if bounded placement attempts run out
(`coworld-ctf@9dedac0/src/ctf/arena.nim:2442-2526`). Four-team generation rejects
an explicit positive request. Every puddle emits one init-snapshot marker:

```text
puddle <x0>,<y0> <x1>,<y1>
```

The marker is a **conservative bounding box**, not exact disc membership
(`coworld-ctf@9dedac0/src/ctf/labels.nim:187-199`,
`src/ctf/global.nim:3451-3464`).

The deployed 0.7.211 variant configs contain no `mapPuddles` key, while the
engine default is zero (`coworld-ctf@9dedac0/src/ctf/sim_config.nim:20-53`). The
live public schema exposes all four barrage controls but no puddle controls.
Therefore normal current campaign episodes have no puddles. If puddles are meant
to affect the league now, the missing work is upstream/configuration first:
expose the two keys in `config_schema` and set a nonzero count on the intended
two-team variants. A policy-only change cannot make them appear.

### 5. PR #250 and the “few others” in this release window

There is one other merged PR between the lab's 0.7.208 baseline and 0.7.211:
PR #250 / commit `4664a3a`. It fixes replay seeks restoring dynamic spinning
diamond geometry into otherwise donated static walk/wall/FOV masks. It changes
replay restore only, not live gameplay or the player wire. Stencil needs no
behavior change for it, but replay-based diagnosis should use 0.7.209+ source;
otherwise a seek can show phantom collision/vision geometry even though linear
playback is correct (`coworld-ctf@9dedac0/src/ctf/replays.nim:179-195`, with
the restamp implementation at `src/ctf/sim.nim:2734-2755`).

## Required Stencil changes, prioritized

### P0 — update provenance and evaluation inputs

1. Update the lab's canonical game pin/docs from 0.7.208 / GV40 to **0.7.211 /
   `9dedac0` / GV41**. `self_play.py` already resolves the canonical live source,
   so its architecture is correct; stale prose and any manually pinned replay
   expansion are the risk.
2. Update the project-local CLIs through the repo's dependency tool before
   operational use: this checkout has `coworld 0.1.35` versus current 0.1.37,
   and `softmax-cli 0.26.27` versus current 0.26.29 (checked from the isolated
   project environment and PyPI on 2026-08-07). The current CLI was sufficient
   for this read-only investigation; no lockfile was changed.
3. Make all new A/B requests use 0.7.211. Old 0.7.208 results remain useful for
   pre-barrage mechanics but cannot predict timeout/endgame behavior.

### P1 — parse the barrage and visible shells

Make one attributable capability change:

1. Add a `BarrageState` (`depth`, integer marker rate, `startSec`, `saturateSec`,
   active) and visible airborne-grenade observations to `types.nim`.
2. Parse `grenade barrage ...` and `grenade air` in `perception.nim`. Preserve
   airborne object IDs so positions can be tracked across frames.
3. Fold the marker and short shell tracks into `Belief`. Since flight is linear
   and fixed at ten ticks, two consecutive positions are enough to project the
   landing area conservatively. Treat the projection as uncertain because
   integer interpolation and fog can reveal a shell mid-flight.
4. Reuse the existing `clear_grenade` seam, but feed it projected landing
   warnings with the real **58px body-hit reach plus movement margin**. Carry-home
   and active thief interception should remain above evasion only when they are
   immediately decisive; otherwise a lethal projected shell should win.
5. Trace marker depth/rate, visible shell count, projected landing, time-to-hit,
   and evasion decision. Without these, a hosted result cannot distinguish bad
   prediction from bad path selection.

Do not start with a blanket “run to center at 4:30” rule. The center is lower
density, especially on rectangular maps, but not safe after saturation; shell
tracking offers a direct, falsifiable capability and also fixes Stencil's
pre-existing blindness to ordinary enemy grenades.

### P2 — add a barrage-aware endgame doctrine

After shell evasion works, add a separate config-gated strategic layer:

- At latch, prefer increasing minimum edge distance when not carrying,
  intercepting, or in a favorable immediate fight.
- At full saturation, prefer movement and local shell avoidance over static
  center camping. Preserve team spread: clustered squads multiply one blast's
  damage, and a 52px blast can hit every teammate in a tight formation.
- Revisit Stencil's hold/post and early-defense behavior. Static defensive posts
  near map edges become predictably bad after 4:30, while current objectives can
  hold indefinitely (`paintbot_lab/paintbot/stencil_nim/strategy.nim:79-96`,
  `:165-179`).
- Treat survival as a win condition rather than a draw clock. The old implicit
  assumption that the episode simply ends at `maxTicks` is gone.

Evaluate this as a late-game behavioral change on completed 0.7.211 episodes,
cut by variant/map size and by whether the episode reached the latch. Report
barrage deaths, time alive after latch, captures/wipes, clustering, and win rate.

### P3 — prepare puddle support before upstream enables it

Puddle work is not urgent for current league play, but the clean integration is:

1. Extend `ProtocolClient.cacheStaticLabel` to retain `puddle` boxes alongside
   game/endzone markers (`protocols.nim:39-75`).
2. Pass them into `newWorldMap`; add a static conservative hazard mask separate
   from `wall`/`walkable`. Never merge puddles into walkability: the game permits
   crossing them and the only wire geometry is a loose bbox.
3. Add a **soft route cost** in both cached Dijkstra flow fields and A*, rather
   than a hard obstacle. Today both use only geometric step length
   (`worldmap.nim:220-250`, `nav.nim:21-64`). A hard block can destroy the only
   route; zero cost guarantees needless exposure.
4. Add an immediate “exit current puddle” objective, using the closest low-cost
   neighboring cell, and make carrying/interception explicitly decide whether
   the short exposure is worth it.
5. Trace puddle occupancy estimate, planned exposure cells, and reroute reason.

Because the marker is conservative, the first implementation should bias away
without claiming exact membership. Exact disc geometry would require a richer
wire contract than PR #251 provides.

## Cross-references and surprises

- PR #251 is deployed, but puddles are not enabled. “Code exists” and “league
  uses it” are different facts here.
- The puddle design doc's square geometry is stale after the follow-up organic
  splat commit. Source, labels, and RULES consistently use disc unions.
- The barrage marker truncates fractional rates. It is sufficient for phase
  detection but not exact density calculation.
- Full-board barrage coverage is spatially nonuniform on rectangular maps.
  Center is relatively safer after saturation; it is not a safe zone.
- Barrage stains and puddles share paint art but are mechanically unrelated.
- The checked-out `coworld-ctf` working branch is not `origin/main`; this recon
  fetched/pruned and read the exact canonical `origin/main` tree without
  changing that checkout. The player-labs tree was also preserved because it is
  15 commits ahead of `origin/main` with extensive user changes.

## Unresolved

1. **No hosted 0.7.211 Stencil episodes were analyzed.** Source proves the
   rules and current blindness, but not the empirical barrage death rate or
   whether opponents already exploit the new endgame.
2. **The intended live puddle count is unknown.** Current effective count is
   zero. A future manifest/league change must choose counts by two-team variant;
   the source provides no “recommended density” because the mechanic is exact
   count mode only.
3. **Best strategic tradeoff after latch is empirical.** Center pressure,
   ongoing capture attempts, spread, and aggression should be tested after the
   direct shell-evasion capability exists.

## Next steps

Recommended next iteration: implement only P1 (marker + airborne-shell tracking,
projected warning, evasion trace), rebuild/upload a new inert Stencil version,
then run campaign-shaped 0.7.211 evaluations targeted at episodes likely to
reach 4:30. Pause before adding the broader P2 doctrine so the shell-awareness
effect remains attributable.

## Files read (full or significant section)

- `coworld-ctf@9dedac0`: `coworld_manifest_paintbot.json`, `config.json`,
  `docs/RULES.md`, `docs/ENV_VARIATION.md`, both 2026-08-07 design docs,
  `src/ctf/{arena,global,labels,replays,sim,sim_config,sim_state,sim_types}.nim`,
  `tests/test_barrage.nim`, `tests/test_puddles.nim`, `tests/test_replay.nim`.
- Current player lab: `AGENTS.md`, `README.md`, `best_practices.md`,
  `user_preferences.md`, `WORKING_CONTEXT.md`, `TODO.md`, and Stencil's
  `protocols.nim`, `perception.nim`, `types.nim`, `belief_state.nim`,
  `belief_update.nim`, `worldmap.nim`, `nav.nim`, `strategy.nim`, `action.nim`,
  `chat.nim`, and `config.nim`.
