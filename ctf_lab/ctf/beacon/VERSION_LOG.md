# beacon version log

Version → change mapping for the CTF `beacon` policy. Newest first.

## v18 — team chat: the E/U/G/C/T shout protocol (2026-07-22)

**Why (human direction):** teamwork substrate. Except T (and maybe E) these are
building blocks for later squad coordination, not expected win movers yet.

**Protocol** (`chat.py`): 10-char budget, `<type><cell>[h]` — cell = 2x base-36
nav-grid coords (≤6 chars total). `E`=enemy seen (edge-triggered per sighting
burst, re-arms after 48 clear ticks, 72t cooldown), `U`=under fire at my cell
(fresh impact ≤90px — new `belief.under_fire`), `G`=grenade en route to cell,
`C`=carrier heartbeat + heading octant, `T`=enemy thief fix. Send arbitration:
priority C>T>G>U>E, ≥30t between shouts (server: 1/s, one live bubble).

**Receive** (`perception._heard_shouts` + `belief._update_chat`): bubbles parsed
from `<team> shout <addr>: <text>` labels; dedup per (sender,text) over the ~3s
bubble life; own-bubble echo skipped. SAME-TEAM payloads decode: E/T → phantom
enemy-track sightings (+ thief_fix), C → carrier_fix (pos+heading+tick),
G → grenade_warnings, U → danger blob. ENEMY bubbles: payload untrusted, but the
bubble position itself is a live ±20px enemy fix → track fold (knob
CHAT_ENEMY_BUBBLE_FIX).

**Consumers:** intercept rung fires on heard thief fix (`intercept_thief_heard`);
escort rung follows the carrier heartbeat with heading projection
(`escort_carrier_heard`); teammates within 80px of a shouted grenade landing flee
(`clear_grenade`). Send path: runtime → Command.chat → decide returns (mask, chat)
→ bridge packs 0x81. Tracing: `chat_sent`/`chat_heard` per kind, `under_fire`,
fixes in snapshots. Knob: `BEACON_CHAT` (default ON). 72 tests.

## v16 — hearing: sound-ring perception + duck-on-heard-fire (2026-07-22)

**Why:** beacon was deaf — `shot impact` (every bullet landing, audible MAP-WIDE
through walls/fog, jittered ±20px, team-anonymous) and `grenade sound` rings arrived
in every frame and were ignored. All enemy knowledge was sight-only, so fights
400px away behind a wall were invisible and unseen shooters never triggered cover.

**Changes:** (1) perception `_heard_impacts` reads both ring labels →
`CtfState.heard_impacts`. (2) belief `_update_heard`: dedup ring sightings (rings
persist ~12 ticks at a STABLE jittered position; match ≤40px) into `HeardImpact`
events, TTL 60 ticks. (3) danger field: each NEW event stamps heat 0.5 over a 32px
blob (weaker than a seen enemy's 1.0 — anonymous; wider — jitter + shooter-not-here).
(4) behavior consumer: **duck-on-heard-fire** — gun down + fresh impact ≤180px (and
NOT along our own aim ray — own-fire suppression, corridor 24px) = duck threat even
with no seen track; `belief.heard_duck` marks the activation. (5) tracing:
`heard_events`/`heard_duck_ticks`/`heard_live` in snapshots. Knob: `BEACON_HEARING`
(default ON — the A/B bit) + `BEACON_HEARD_*`. 61 tests.

## v15 — GameVersion-17 blast radius; SUBMITTED + CHAMPION (2026-07-22)

**Why:** overnight game check before submitting v14: deployed ref unchanged
(0.7.51/b571dd3) but it carries GameVersion 17 — grenade blast radius 40→52.
Everything else v14 depends on (arena, config.json, labels, spawns) verified
identical, so v15 is v14 + the one constant (widens the lob teammate-splash
veto to 72px).

**Submitted** (human go-ahead): `sub_443c6a23…` → membership `lpm_4f91376e…`
**QUALIFIED → competing → CHAMPION** (auto-champion always; evicts v6's entry).

## v11–v14 — accuracy ladder to 0.657 (2026-07-21, same session as v10)

Iterating on v10's 0.234 accuracy toward the ≥0.5 goal (10-ep 8v8 vs each top-3
per version):
- **v11** — `FIRE_MAX_RANGE_PX=350` hold-fire gate + aim-resync slack 12→8.
  **0.333**; first-ever series wins vs Picasso (7-3) and autoresearch (8-2).
- **v12** — movement freeze through the 5-tick windup (the sim fires from the
  shooter's CURRENT position along the LOCKED angle; strafing displaced our own
  ray ~14px). **0.273** — REGRESSED, which exposed…
- **v13** — …the **stale nav grid**: GameVersion 16 (ctf 0.7.51) changed the
  arena under us (midline chevrons → windowed bracket, column-3 discs thinned).
  bake_map.py re-ported from b571dd3, nav.npz rebaked; FIRE_SLACK_PX 11→8 (the
  old gate allowed 22px perp misses vs the 14px corridor). **0.312** (0.442 vs
  Picasso), 9-1 autoresearch.
- **v14** — aim **boundary-crossing calibration** (the tick the 16-step readback
  changes while rotating pins the true aim to ±2.5 brads) + **glass-aware fire
  gate** (`ray_clear` required: GameVersion-15/16 windows pass vision but block
  bullets — shooting through one was a guaranteed miss). **0.657 overall**
  (0.622 focusfire / 0.647 Picasso / 0.694 autoresearch) on ~2.9k shots —
  beacon out-shoots the whole field per-shot. Wins: 10-0 autoresearch,
  6-4 Picasso, 2-10 focusfire (first regulation wins vs it). Items steady:
  shield 17.6% alive-time, grenade 10.8%, 55 non-gun kills, throws confirmed.

**GOAL MET: ≥0.5 accuracy in every top-3 matchup + consistent effective item use.**

## v10 — lead aim + item skills (2026-07-21)

**Why:** top-3 recon (scratch/recon_top3): beacon's warehouse accuracy was 0.163 vs
the field's 0.43-0.56, and items (shields especially) were an uncontested edge only
focusfire used (12.7% shield alive-time). Goal gate: ≥0.5 accuracy + consistent item
use, measured in 1v1 xreqs vs each top-3 policy.

**Changes:** (1) **Velocity-lead aim** (`_lead_aim_pos`): snap aim extrapolates a
visible enemy along its track's EMA velocity by `BEACON_LEAD_TICKS` (default 6 — the
5-tick windup + 1 tick latency; baseline LeadTicks parity), gated on ≥3-frame tracks.
First gate on the v6 tracks groundwork. (2) **Item system** (`items.py`): fixed spawn
table mirroring sim.nim formulas (4 corner grenades, 2 endzone shields, 2 arcs, 2
center med kits), optimistic present-belief with observed-empty refutation +
respawn-interval back-off; fog-gated pickup perception (`grenade`/`shield`/`plasma
arc`/`med kit` labels), own hp from the overhead `hp N/3` bar, carried state from
`* carried` markers. **Single-claimant fetch**: our-side shield → seat 2, top/bottom
grenade → seats 3/4 (pure function of seat — no radio needed); hurt agents divert to
med kits (any seat: the sim only lets hurt players take one). Strategy rung 3.5,
detour-capped. (3) **Grenade throw**: C-button (bit 128; SDK mask clamp widened to
0xFF in main.py — the pinned bitworld decodes the full byte) charge/release machine
lobbing at fresh wall-blocked tracks ≥90px, teammate-splash veto. (4) **Arc fire**
logic if carrying (nobody fetches arcs — the gun matters more). (5) **Vision cone
60°** (config.json changed upstream; was 45). (6) Activation tracing: `lead_shots`/
`unled_shots`/`lead_brads_sum`/`throws` cumulative in snapshots; `item`/`throw`/`heal`
transition events. Knobs: `BEACON_LEAD_AIM`, `BEACON_ITEMS`, `BEACON_GRENADE_THROW`
(all default ON). 51 tests pass.

## v8/v9 — micro activation tracing (2026-07-15)

**Why:** v7's A/B vs focusfire was dead flat (0-9 both arms) with no way to tell
"never fired" from "fired and didn't help". New standing discipline (James,
`user_preferences.md`): every behavior change ships activation tracing.

**Changes (v8):** `belief.micro` ("duck"/"peek"/None, set per tick by the override),
`micro` transition trace events, cumulative `micro_ticks` in every snapshot. 43 tests.
**v9** = the same image uploaded with `--secret-env BEACON_TRACE_OUTPUTS=jsonl@stderr`
— the artifact-zip trace path returns empty from the fetcher; stderr is reliable.

**Diagnostic verdict (3 eps vs focusfire):** duck 14.0% / peek 3.7% of alive time
(421+219 engagements, 24 agents) — the micro FIRES; kills/deaths unchanged. Cover
micro is not the binding constraint vs focusfire; next lever is target
selection/velocity lead/focus-fire (or warehouse WHERE deaths happen vs micro state).

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
