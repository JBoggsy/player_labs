# beacon version log

Version → change mapping for the CTF `beacon` policy. Newest first.

## v32/v33/v34 — covered posts: cover + sightlines + a spreading instinct (2026-07-28)

**One image, three env-flipped uploads** (`--secret-env`; the arms of a single A/B):
- **v32** — `BEACON_POSTS=0` (control; plays as v31 did).
- **v33** — `BEACON_POSTS=1 BEACON_POST_FACING=1 BEACON_POST_STANCE_WEIGHT=0.12`. **SUBMITTED
  -> qualified -> 👑 CHAMPION** (`sub_df9f3ac2…`, `lpm_b2f96151…`, auto-champion lineage).
- **v34** — same but `BEACON_POST_STANCE_WEIGHT=0.18` (past the 0.1727 stance crossover).

**Why (human direction):** beacon followed battle plans literally — it *stood at waypoints*
rather than understanding area control, supporting fire, and sight lines. Measured from the v31
replay: pushers arrived 13-47px apart (inside the FF corridor and one 52px grenade blast) with
only 0-3 of 16 sampled rays open past 200px, and `cover_grid` *passed* those positions because
it is non-directional — the wall was between them and the threat, not beside them.

**Changes:**
- **Baked `sightlines` field** (`bake_map.py` → `nav.npz`): `(32, 83, 155)` `uint8`, 4px units,
  400px cap, direction 0 = east advancing counter-clockwise on screen. 3.9s bake; nav.npz
  19,626 → 106,614 bytes. Directional cover is *derived* (short rays at ±4 indices = ±45°),
  not baked separately. Convention: free distance to the first blocked 4px sample.
- **New `posts.py`**: a *post* = nav cell + the direction it watches. Bounded, vectorised
  ranking over ~600 cells (no runtime raycasting): `reach` (sightline along the threat axis),
  `cover` (short flank rays), `stance` (signed; forward when pushing, back when holding),
  `danger` (penalty), with qualification gates so open ground yields no post.
- **Threat axis**: fresh enemy track > danger gradient > plan `facing` > enemy-pedestal prior.
  This makes the plan schema's `facing` load-bearing for the first time.
- **`K<seat><cell>` claim shout** (6 chars), arbitration `C > T > O > G > U > K > E > P`,
  48t refresh / 120t expiry. Selection skips posts claimed by a lower seat or occupied by a
  visible teammate — chat makes "occupied" knowable, which is what v19's fog-blind rally gate
  lacked.
- **Post facing** (`BEACON_POST_FACING`): a settled post centres the sweep on its own
  direction with a narrowed arc; the squad sector offset is suppressed while it owns the sweep
  (`SQUAD_SECTOR_BRADS`=50 exceeds `SWEEP_HALF_ARC`=32 and would aim bots off their own lane).
- **Integration**: plan rung 3.9, `order_hold`/`order_push`, and the static defender hold each
  treat their waypoint as a *search centre* once inside the arrival radius. Rung altitude is
  unchanged, so carry/rejoin/intercept/escort/grenade/medkit/convert all still preempt, and
  A*/danger/peek-duck/combat still govern the approach. `plan.advance` gained
  `milestone_ready` so arriving at the raw waypoint no longer advances the phase and discards
  the post (a latent ordering bug: `advance()` ran before `current_objective()` sharing the
  same `PLAN_ARRIVE_PX`). `spread_point`/`separation_bias` remain the floor.

**Measured (matched arms, 10 eps/arm, ctf 0.7.95, 60/60 episodes, 0 failures):**
- vs **ctf-focusfire:v56** — win 20% → **40%** (p=0.01), score -0.60 → -0.20.
- vs **ctf-h050:v1** — win 0% → **20%** (p=0.00), score -1.00 → -0.60 (first wins off the h0xx line).
- v34 (0.18) beats the control by less (30%/10%); 0.12-vs-0.18 is **not significant** at n=10
  (p=0.18/p=0.08), so 0.12 stays the default.
- **Activation** (control: 0): 1,942 active post-ticks, 181 distinct posts, max 525 ticks on
  one post; threat sources enemy_track 1125 / plan_facing 448 / pedestal 288 / danger 81;
  claim sources uncontested 811 / visible_teammate 641 / heard_K 490 across six seats.
- **Stance verified mechanically despite the null**: 0.12→0.18 moved PUSH posts from +21.5px to
  +32.9px mean forward offset (65% → 72% chosen forward of the waypoint) — "more forward isn't
  better vs these two", not "the term is inert".

117 tests pass. Knobs: `BEACON_POSTS`, `BEACON_POST_FACING`, `BEACON_POST_STANCE_WEIGHT`,
`BEACON_POST_SEARCH_RADIUS_PX`, `BEACON_POST_MIN_SEPARATION_PX`, and the rest of the
`BEACON_POST_*` family in `config.py`. Design:
`docs/designs/beacon-posts-cover-sightlines-2026-07-28.html`.

## v31 — buddy-wait: no solo pushes into danger (2026-07-28)

**Why (human direction):** "moving up to flank is … waiting for your other
flank" — a group member shouldn't charge a dangerous objective alone just
because the plan says go.

**Changes:** on a plan MOVE whose target is on the ENEMY half, a bot with no
group-mate confirmed within `BEACON_PLAN_BUDDY_RADIUS_PX` (visible badge or
fresh identity track, conservative like squadmates_alive) HOLDS in place
instead — budgeted at `BEACON_PLAN_BUDDY_WAIT_TICKS` (~6s) total per phase,
then pushes regardless (the v19 no-deadlock rule). Solo groups and holds never
wait. Cleared on phase advance. Traced: plan_buddy_wait_ticks/_waiting.
106 tests.

## v30 — POI vocabulary + battle-plan interpreter (2026-07-27)

**Why (human direction):** execute the co-general battle plans directly —
"feed it these plans and see how they play out" — with the hard constraint
that the plan supplies GOALPOSTS, not motion: every existing skill (A* +
danger field, peek/duck, cover routing, combat overlay) still governs HOW a
bot moves, and every emergency rung still preempts the plan. No death marches.

**Changes:** (1) **`poi.py`** — the canonical named points/areas map
(`mapdata/points_of_interest.json`, human-curated rev 5) as the single source
of truth; red-frame authoring with automatic blue mirroring (prefix-swap when
the twin exists, geometric mirror otherwise). Strategy code and plans share
the same names. (2) **`plan.py`** — the interpreter: loads
`plans/<BEACON_PLAN>.json` (baked snapshot of battle_plans/, see plans/README),
maps my seat → group through per-phase splits, emits the group's primary
order as a `plan_move`/`plan_hold`/`plan_to_hold` intent at rung 3.9 (below
carry/intercept/escort/medkit/convert; above the static split, which remains
the no-plan/no-order fallback). Phase advancement is PER-BOT, no comms:
milestone (arrived at my phase target, `BEACON_PLAN_ARRIVE_PX`) or timeout
(`BEACON_PLAN_PHASE_TIMEOUT_TICKS`, the v19 lesson) — gated by the next
phase's entry TAG when machine-evaluable (tick/enemy_lives/own_deaths ≤/≥ N).
(3) **Contingencies v1**: a hold order's `fallback` location engages when
pressed (under_fire + 2 visible enemies) — the rear's delay-then-fall-back
doctrine; death clears the latch, phase advance clears it. (4) Traced:
`plan_phase`, `plan_phase_age`, `plan_advances`, `plan_milestone_hit`,
`plan_fell_back` in every snapshot (+ objective transitions show plan_*
reasons). `BEACON_PLAN=` empty disables the whole layer. 105 tests.

**Known gaps (deliberate, for the next iterations):** `watch` orders traced
but not yet steering aim; no branch conditions (the break-vs-flank choice
runs both as written); waypoints (`via`) not yet threaded into nav (A* polyline
is close); presence() tags un-evaluable without the squad presence table.

## v29 — squad layer OFF: back to the static role split (+ convert kept) (2026-07-27)

**Why (human direction):** watching the h035 games, our squads read as "a
chaotic mess, several hanging back" vs Alex's disciplined midline. Rather than
keep tuning a coordination layer we can't yet see into, roll back to the
pre-squad strategy and let the new tracing/viewer explain the failure first.

**Changes:** (1) `SQUADS` and `SQUAD_COMMAND` default **0** — no leader orders,
no pings, no rejoin rung, no order decay/backoff, no formation forces, no
wave-gating, no spread points, no aim sectors. Strategy falls through to the
**static role split** (v2-v18 shape): defenders hold their cover-snapped choke
points, attackers push the flag; carry/intercept/escort/item rungs unchanged.
All machinery kept + tests pinned via a `squads_on` fixture — re-enable with
env flags for A/Bs. (2) **The convert trigger survives the rollback** as a
standalone rung (`convert_hunt`, above the role split): it's a global-signal
read, not coordination, and it's the single biggest measured win (v26 A/B).
(3) Chat: protocol sends (O/P) gate off with SQUAD_COMMAND; the intel messages
(carrier heartbeat C, thief fix T, enemy E, under-fire U, grenade G) still
send and still fold into belief — they inform individports, not orders.

**Rotating diamonds (same session, viewer question):** verified in the deployed
sim — the near-midline column-5 diamonds are DRAWN spinning but "COLLISION,
LOS, and the fog masks keep the exact static diamond — the spin is pure
decoration and never enters gameHash" (sim.nim buildAnimatedDiamonds). The
static nav bake is CORRECT; no pathing change needed. Documented in
bake_map.py; the viewer draws the static truth, which is what the game
actually enforces.

## (pending v28) — observability: seat/tick-keyed tracing for cross-bot analysis (2026-07-27)

**Why (human direction):** debugging squad tactics needs to sync all 8 bots'
beliefs in one match; the old traces couldn't (transition events lacked seat,
trace ticks are per-bot frame counters, and the warehouse silently ingested 0
trace events because it only read the stderr fallback, not the artifact zips).

**Changes (trace-only, no behavior):** (1) every trace event now carries
seat+team (self-describing; no join-to-snapshot needed). (2) NEW `order`
transition event — every squad-command change with its **source**
(leader rule / heard O / decay backoff / decay convert; `belief.order_source`)
— the coordination state machine is now directly observable. (3) NEW `sync`
event at first spawn (the shared Playing-start moment). (4) Snapshots add
`order_source`, `order_age`, `presence_age` (per-squadmate staleness — the
backoff rule's raw input), `intent_point`. (5) Warehouse: reads
`telemetry.jsonl` from artifact zips (fixes the 0-trace bug), stamps every
trace row with **`eng_tick`** (engine-tick alignment via first-spawn ↔ replay
phase=Playing), first-class `order_goal`/`order_source`/`enemy_lives_left`
columns. Verified end-to-end on the v26 A/B batch: 16,859 trace events, all 8
seats aligned on one engine-tick axis against replay kills. 105 tests.

**Chat-cost check (same session):** chatting is FREE — the bridge sends the
0x81 chat packet alongside the 0x84 mask packet in the same frame flush
(sprite_bridge `_pack_outbound`), the server folds both into the same tick's
input, and the sim applies shouts without touching movement/fire state.
`choose_shout` never modifies the mask. No action is ever displaced by chat.

## v26 — convert trigger: read the team scoreboard, collapse to finish (2026-07-24)

**Why (v25 A/B + human direction "start trying to close"):** v25's spread
holders sat 1-2 kills from the wipe for whole halves (focusfire draws: beacon
21-23 kills vs ~15; 5D/10D exploded). Under GV21 a draw pays -1 like a loss, so
a near-wipe hold is the worst posture in the game. Session-7's designed convert
trigger, now built on a NEW signal: the fog-independent top-center team
scoreboard ("team score RED k/d" labels — found in the 2026-07-23 rules audit),
which gives the ENEMY team's aggregate deaths every frame.

**Changes:** (1) **perception `_team_scores`** parses both teams' (kills,
deaths); folded into belief (`own/enemy_team_score`). (2)
**`squads.enemy_lives_left`** = 24 - enemy deaths (exact while 16 slots stay
connected; a disconnect makes us under-trigger — safe direction).
(3) **Leader rule 3 (CONVERT)**: enemy lives <= `BEACON_CONVERT_ENEMY_LIVES`
(default 6) -> order T at the freshest enemy evidence (visible > fresh track >
their pedestal); preempts backoff and the side-hold defaults, sits below
thief/carrier fixes. (4) **Order decay override**: a stale-order member with
the wipe in reach self-issues T instead of the v24 backoff-hold (the scoreboard
is global — no leader needed to know it's time). Traced: `enemy_lives_left`
live + `convert_events` cumulative. 99 tests.

## v25 — squad spread: stop stacking on the order point (2026-07-23)

**Why (human direction):** squads stack on top of each other — team kills from
being right on top of each other are costing games. Warehouse (v24 batches):
9,006 teammate-pair snapshots at <25px (vs 2,246 at 25-40), 3 of beacon's 5 team
kills at ≤14px, stacks concentrated at the hold anchors (x≈336-344/368-378).
Root cause: every squad member receives the SAME order point and A*s to the same
cell; the v19 separation force only ever applied to `steal`/`to_hold` movement —
never to order-driven movement (`order_*` reasons), and never to a HOLDING agent
(hold emits no movement at all), so stacked holders stayed stacked forever.

**Changes:** (1) **`squads.spread_point`** — members rank-offset a shared H/S/P
order point along y (0 / +70 / -70 px, `BEACON_SQUAD_SPREAD_PX`, same scheme as
the aim sectors; snapped to nearest cover, clamped on-map) so a 3-man squad
holds a short line across its lane, one grenade can't splash two of us, and
bodies don't block each other's lanes. (2) **Separation for ordered movement** —
the formation bias now also applies to `order_to_hold`/`order_push`/`order_hunt`
navigation. (3) **`squads.separation_bias`** (split out of formation_bias) —
a HOLDING agent's only movement is now the push-apart nudge when a teammate is
inside 40px. 95 tests.

## v24 — squad defaults: side-holds + middle push; order decay -> backoff (2026-07-23)

**Why (human direction):** three command-layer changes. (v23 = the v22 image
re-uploaded under the default player after v22 silently bound to the secondary
player 'seedtest-base-newcomer' — identity fix only, SUBMITTED + champion.)

**Changes:** (1) **Squads renamed A/B/C**: A = seats 0-2 and B = 5-7 (3-person
side squads), C = 3-4 (2-person middle squad). (2) **New defaults**: A holds the
TOP side lane and B the BOTTOM (both at the choke line, y 165/494 — the map's
lane bands); C PUSHES the middle (617, 329). Anchors the field against flank
blitzes; C probes and creates pressure. (3) **Order decay -> backoff-hold**: a
member whose order goes stale (leader dead/out of earshot) now self-issues H at
its position stepped 70px toward home — same posture as losing a teammate —
instead of falling through to the old static role split. Behind the rally line
it holds in place (no home-creep from repeated decays). A live leader's next O
overrides immediately. 91 tests.

## v22 — squad command: leader orders, flexible goals, respawn discipline (2026-07-23)

**Why (human direction):** squads' fixed behaviors -> flexible, leader-set goals;
and stop the respawn trickle (agents feeding 1-by-1 back into contact). Standing
principle recorded in user_preferences.md: lives > flag captures (verified sharper
at 0.7.69: timeout = scoreless draw, NO lives tiebreak — hold when weak, convert
before the clock when strong). *[Correction, 2026-07-23 audit: "scoreless" was
wrong — a timeout draw is -1 for BOTH sides (GameVersion 21 TimeoutReward), the
same score as losing. The no-tiebreak part stands. See user_preferences.md.]*

**Chat additions:** ``O<seat><goal><cell>`` orders (goals H hold / S scout / P push
/ F flag / T thief-hunt; priority below C/T, above G/U/E; rebroadcast 72t) and
``P<seat><cell>`` presence pings (lowest priority, 60t cadence). Members obey only
their OWN leader's order (leader = lowest seat, static); orders live 240t then
fall back to the static role split — squads degrade gracefully to v21 behavior
when the leader is dead/out of earshot.

**Leader engine** (squads.lead_squad, first match wins): thief fix -> T; carrier
fix -> F; PAST RALLY + squadmate presence-stale (~190t without badge/ping/order)
-> **H stepped 70px back toward home** (back off + hold the gained ground);
defaults D hold choke / A1 flag / A2 push mid.

**Respawn discipline:** on death, snapshot rejoin point = freshest identity-tagged
squadmate track (else own position stepped home); on respawn, REJOIN rung (below
carry, above all else) navigates there cautiously (existing micro + danger field),
exits on squad contact (squadmate badge <=160px) or 360t timeout, then resumes
orders. Because the squad now HOLDS on member loss, the dead member's stale
memory stays accurate — the two halves reinforce.

**Tracing:** live order + orders_sent/heard, pings_sent/heard, backoff_events,
rejoin_ticks, squadmates_alive per snapshot. Knob: BEACON_SQUAD_COMMAND (default
ON — the A/B bit). Live-wire verified (leader broadcasts O at tick 1, pings
between, rebroadcasts on cadence). 88 tests.

## v21 — nameplates + wave-gate off (2026-07-22, 0.7.69 catch-up)

**Why (human direction):** drop wave-gating (tempo cost > sync benefit under
maxTicks 5000; keep the machinery for a future game-state-reactive gate);
squads cohere by being CLOSER, now with real identity — the upstream nameplate
feature landed (0.7.69: `identity <color> <name>` badges, alpha..theta by slot
order within team = exactly our seat notion, fog-gated with their player).

**Game catch-up (0.7.66 -> 0.7.69):** identity badges added; gunRange moved from
config.json into per-map CtfMap (still 1300 on `arena`); a second map
"arena-large" (1606x858, gunRange 1690) EXISTS but the deployed config still
selects `mapPath: "arena"` — standard-arena geometry verified shape-identical,
nav.npz stays valid. WATCH: if the league ever flips to arena-large, beacon
needs a full re-bake + geometry port.

**Changes:** (1) `SQUAD_WAVE_GATE` off by default (BEACON_SQUAD_WAVE_GATE=1 to
re-enable). (2) Perception: identity badges parsed and associated to player
sprites (30px radius) -> `Enemy.identity` (0=alpha..7=theta). (3) Tracks carry
sticky identity; association gate: an identified sighting never claims a track
known to be a different player. (4) Cohesion pulls toward the nearest identified
SQUADMATE (identity==squadmate seat) when one is known, else nearest teammate.
82 tests.

## v20 — tick-synchronized wave windows (2026-07-22, v19 fix)

**Why:** v19's buddy-sensing rally gate DEADLOCKED — teammates at the rally are
fog-hidden (everyone aims enemy-ward; 60° cone + 90px bubble miss a mate 60px
behind), so buddies_near read 0 and every attacker burned the full 150t timeout
every push (traces: 153 wait-ticks/agent, wins collapsed to 1-9/0-10 — though the
league ALSO redeployed mid-iteration: 0.7.66, maxTicks 10000→5000, spawn
protection removed; re-baseline needed). ALSO: with games now ending at the time
limit (avg end ~5049), tempo is twice as expensive.

**Change:** `should_wait_for_squad` now gates on the TICK — the one squad signal
fog can't hide. Pushes commit only in the first SQUAD_WAVE_WINDOW_TICKS (36) of
each SQUAD_WAVE_PERIOD_TICKS (120); attackers reaching the rally mid-period hold
(≤84t) and commit together at the window edge. Pure function of tick — every
agent computes it identically, zero comms, no sensing. 78 tests.

## v19 — squad play: formation, wave-gating, aim sectors (2026-07-22)

**Why (human direction):** team tactics — squads of 2-3 that form up, stick
together, and cover angles. Design: docs/designs/ctf-squad-play-design.md. Core
constraint: visible teammates are ANONYMOUS, so membership is seat-deterministic
(zero comms) and flocking is anonymous-proximity; nameplates (alpha-theta,
upstream WIP) will later upgrade cohesion to true squadmate identity.

**Changes:** (1) `squads.py`: D=seats 0-2, A1=3-4, A2=5-7; within-squad rank.
(2) Formation bias in navigation: separation <40px pushes apart (52px grenade
blast, FF), cohesion pulls toward the nearest teammate when <1 buddy within
120px; exempt while carrying/fetching/intercepting. (3) **Wave-gating**: an
attacker at the rally line (x=450 mirrored) HOLDS (`squad_rally` objective)
until squad-size-1 buddies are near, timeout 150t — converts the dribble-in
attack into waves. (4) **Aim sectors**: lighthouse sweep centre offset by rank
(0/+50/-50 brads) — squads cover a cone + shoulders instead of one arc x3.
(5) Tracing: `squad_wait_ticks`/`squad_cohesion_ticks` in snapshots. Knobs:
`BEACON_SQUADS` (default ON — the A/B bit) + `BEACON_SQUAD_*`. 78 tests.

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

## v17 — A/B arm: v16 image with BEACON_HEARING=0 (2026-07-22)

**Not a code change.** Same local image as v16 (`players-beacon:dev`), re-uploaded
with `--secret-env BEACON_HEARING=0` as the hearing-OFF arm of the pre-registered
hearing A/B vs ctf-focusfire:v36 (telemetry keys confirm the image is v16 code —
no chat counters). Result: NULL — ON 7/40 vs OFF 8/40, Fisher p=1.0, diff −2.5pp
CI [−19.7, +14.8]; manipulation check passed (OFF arm: 0 heard_events across 48
sampled agents; ON arm: 4062). Report: `ctf_lab/scratch/ab_hearing/AB_REPORT.md`.
Never submit v17 to a league; it exists only for the experiment.

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
