# CTF working context

**What this is.** The live, high-signal state of *what we're working on right now* in the
CTF lab — the minimal cross-session facts to carry into the next session. Read it on
startup to resume; **update it as you learn** (keep it tight).

> Read order for a newcomer: this file → [`README.md`](README.md) →
> [`docs/ctf-gameplay.md`](docs/ctf-gameplay.md). And the lab-wide
> [`../AGENTS.md`](../AGENTS.md) for the operating model.

---

## Status (2026-07-23, session 7 END): **v24 SUBMITTED (qualifying); rank 3 @ 0.55. NEXT: the convert trigger**

**League state at close:** v24 submitted (`sub_c047199b…`, membership in the NEW
Qualifiers(staging) division — the league re-added staging; promotion is async).
v23 (=v22 image) is the currently-competing champion. Standings: rank 3 @ 0.5495
(daveey 0.697, Alex Smith 0.552 — we're 0.003 behind #2). New entrant NanosaurusX
(rank 4, 11 rounds) — unprofiled, recon when they have history.

**THE NEXT LEVER (designed, not built): the CONVERT TRIGGER.** v24's hold doctrine
is saturated: 14 draws in 20 eval games, several with banked lives leads (11-5,
8-5), zero conversion attempts. Build the leader escalation rule:
- presence recovered to full strength → re-order P/F (exit backoff);
- enemy-weakness read → all-in (needs a kill-confirm chat message or
  time-since-enemy-contact heuristic; recall the 6-lives-vs-1 draw and the
  13-vs-9-lives LOSS in scratch/eval_v22).
Design sketch in session-7 conversation; goals vocabulary + order machinery
(v22-v24) all ready for it. Also parked: cross-squad coordination (leaders never
conspire), S-scout distinct behavior, squad-scoped chat (seat digit spare bytes).

**v24 details:** A(0-2) holds TOP lane / B(5-7) BOTTOM (choke y 165/494), C(3-4)
pushes mid; order decay → backoff-hold (no home-creep behind rally). Measured:
**0W/9D/1L vs focusfire** (near-stalemate-proof), 1W/5D/4L vs h006. 91 tests.

**Standing watch items:** (1) arena-large map flip (mapPath in the deployed
config — needs full rebake if it flips); (2) game redeploys mid-session (check
each xreq's coworld version; reader pins per era in build_expand_replay.sh);
(3) player-binding trap on upload (verify /stats/policy-versions?player_id=
before any submit); (4) results.json deaths/kills fields NULL at 0.7.69+ —
compute from replay kill events.

## (prior) Status (2026-07-23, session 7b): **v23 SUBMITTED+CHAMPION; v24 side-holds — near-stalemate-proof vs focusfire**

**v23 = v22 image, re-uploaded + submitted under the DEFAULT player** (v22 had
silently bound to the secondary player `seedtest-base-newcomer` — the bare coworld
tool did this with NO active session; check bindings via
`/stats/policy-versions?player_id=…` before submitting). Qualified → champion.

**v24 (uploaded, NOT submitted):** (1) squads renamed **A(0-2)/B(5-7) side squads,
C(3-4) middle pair**; (2) new defaults: A holds TOP lane, B holds BOTTOM (choke
line y 165/494), C pushes middle; (3) **order decay → backoff-hold** (stale order =
self-issued H stepped 70px home if forward of rally, in place otherwise; live
leader O overrides). 91 tests.

**v24 measurement: vs focusfire 0W/9D/1L** (v22: 0/6/4; v21: 0/0/10) — the
side-hold structure nearly stalemate-proofs the phase machine. **vs h006 1W/5D/4L**
(v22: 0/3/7). Draw lives-margins: we out-bank them in some (11-5, 8-5) but most
draws show 1-2 lives ours vs 4-8 theirs — h006 wins the attrition inside the draws.
**The CONVERT-TRIGGER gap is now the single dominant lever**: 14 draws in 20 games,
several with big banked leads, zero conversion attempts. League entry: v23.

## (prior) Status (2026-07-23, session 7): **v22 SQUAD COMMAND — leader orders + respawn discipline; wins→draws shift**

**Principle recorded** (user_preferences.md): lives > captures. Verified sharper at
0.7.69: timeout = SCORELESS DRAW (no lives tiebreak) — so lives are the resource to
convert before tick 5000, not a win condition themselves.

**v22 (uploaded, NOT submitted):** `O<seat><goal><cell>` leader orders (goals
H/S/P/F/T; leader = lowest seat; members obey own leader only; TTL 240t → graceful
fallback to static roles) + `P<seat><cell>` presence pings (60t). Leader engine:
thief→T, carrier→F, past-rally + mate-presence-stale → **H stepped 70px home**
(back off, hold gained ground); defaults D-hold/A1-flag/A2-push. Respawn
discipline: death snapshots rejoin point (freshest identity-tagged squadmate
track); respawn REJOIN rung (below carry) navigates there cautiously, exits on
badge contact ≤160px or 360t. 88 tests; live-wire verified.

**v22 measurement (10-ep 1v1s): outcome DISTRIBUTION shifted exactly as the
principle predicts — vs focusfire 0W/6D/4L (v21: 0/0/10); vs h006 0W/3D/7L.**
Command layer fully live: 2,258 orders sent / 2,304 heard, 4,883 pings sent /
14,830 heard, 227 backoff events, 214 rejoin-ticks/agent. Deaths 428 vs 340 —
still net-negative on kills but no longer collapsing.
**IDENTIFIED GAP: no CONVERT trigger.** "Hold when weak" works; nothing re-orders
a PUSH when strength recovers (presence refreshes / respawners rejoin) — squads
that back off stay backed off, so preserved lives never cash in. That's the next
lever: leader rule "presence recovered + past mid-game → P/F again" (+ possibly
enemy-weakness signals: kill-confirms via chat).

League entry: v18 (champion). Uploads v19-v22 inert. WATCH: arena-large map flip.

## (prior) Status (2026-07-22, session 6f): **v21 — nameplates + wave-gate OFF; 0.7.69 caught up**

**Game catch-up (0.7.66→0.7.69):** (1) **Nameplates landed** — `identity <color>
<name>` badges, alpha..theta assigned by slot order within team (== our seat
notion!), fog-gated with their player, `slotIdentityIndex` in sim.nim. (2) gunRange
moved into per-map CtfMap (still 1300 on `arena`). (3) A SECOND MAP exists:
**"arena-large" (1606×858, gunRange 1690)** — deployed config still `mapPath:
"arena"` (standard arena verified shape-identical; nav valid) — **WATCH for a map
flip; it needs a full geometry port + rebake.**

**v21 (uploaded, NOT submitted):** wave-gate OFF by default (human call; machinery
kept behind BEACON_SQUAD_WAVE_GATE for a future game-state-reactive gate);
`Enemy.identity`/track identity from badges (sticky, association-gated: identified
sighting never claims a different player's track); cohesion pulls toward the nearest
identified SQUADMATE. 82 tests.

**v21 measurement (10-ep 1v1s @ 0.7.69): 1-9 h006, 0-10 focusfire, acc 0.610;
wait-ticks 0 (gate off confirmed), cohesion 558 t/agent.** IMPORTANT unknown: the
v18 champion's 6-4-vs-focusfire was measured at 0.7.51 (maxTicks 10000, spawn
protection); the game is different now — no current baseline says whether squad
flocking helps or hurts. **Next: A/B BEACON_SQUADS=0 vs =1 at 0.7.69** (subagent,
strong power, same method as the hearing A/B) before believing cohesion's 558
t/agent is net-positive. League entry: v18 (champion, rank ~3-4).

## (prior) Status (2026-07-22, session 6e): **v18 SUBMITTED+CHAMPION (rank 3-4!); v19/v20 squad play built; platform churning**

**v18 submitted (human go-ahead) → qualified → champion.** Standings recovered
dramatically as blind-v6 rounds washed out: rank 3 @ 0.62 at submission, rank 4
@ 0.48 later (Alex Smith 1st, daveey 2nd, softmaxwell 3rd — close race).

**v19 squad play** (design: docs/designs/ctf-squad-play-design.md): seat-deterministic
squads (D=0-2, A1=3-4, A2=5-7) + anonymous flocking (separation<40px, cohesion@120px)
+ rally wave-gating + rank-offset aim sectors (0/±50 brads). **v19's buddy-sensing
rally gate DEADLOCKED** (fog hides squadmates — everyone aims enemy-ward; 153
wait-ticks/agent, wins collapsed). **v20 fix: tick-synchronized wave windows**
(commit only in first 36t of each 120t period — pure tick function, zero sensing).
NOTE: nameplates (alpha-theta IDs) are being added upstream (human) — when they land,
cohesion can upgrade to true squadmate identity in squads.py locally.

**v20 measurement PARTIAL, and the numbers are murky for platform reasons:**
- League redeployed 0.7.66 mid-iteration: **maxTicks 10000→5000, spawnProtectTicks
  REMOVED** (arena/labels/constants otherwise unchanged; reader re-pinned 2641542).
  All cross-version baselines invalid; games now often end at the 5000t limit.
- vs h006: **0-10** (v20), acc 0.661 held, wave-gate still expensive (162 wait
  ticks/agent — the window idles attackers h006's blitz punishes).
- vs focusfire: TWO consecutive xreqs deleted server-side (404 minutes after
  create); division memberships list currently EMPTY — platform restructure in
  progress. Measurement blocked until it settles.
**Open decision:** squad wave-gating looks net-negative vs blitz opponents under
maxTicks 5000 (tempo cost doubled). Candidates: shrink period/window, gate waves to
non-blitz opponents, or drop wave-gating and keep sectors+flocking (knobs allow
BEACON_SQUAD_* A/B). v15 remains prior champion entry; v18 current champion; v19/v20
uploads inert.

## (prior) Status (2026-07-22, session 6d): **v18 CHAT built + verified live; hearing A/B = NULL**

**Hearing A/B (subagent, n=40/arm vs focusfire:v36, pre-registered):** REFUTED/NULL —
ON 7/40 vs OFF 8/40 wins, Fisher p=1.0, diff −2.5pp CI [−19.7,+14.8]. Manipulation
check decisive (OFF arm: 0 heard_events across 48 agents; v17 = the OFF upload, do
not submit). So v16's apparent focusfire gain was noise/something else; hearing is
retained as SUBSTRATE (danger-field feed) with no win claim. Report:
`scratch/ab_hearing/AB_REPORT.md`.

**v18 chat (uploaded, NOT submitted):** the E/U/G/C/T 10-char shout protocol
(`chat.py`), send arbitration (C>T>G>U>E, 30t interval, E edge-triggered w/ re-arm),
bubble perception + same-team decode into belief (phantom tracks, thief_fix,
carrier_fix+heading, grenade_warnings, danger stamps; enemy bubbles = position fix
only), consumers: intercept_thief_heard / escort_carrier_heard / clear_grenade.
Smoke (10 eps ea): **6-4 vs focusfire (first series win!), 2-8 h006**, acc 0.631.
Activation ALL LIVE: sent E1090/U735/G123/C50/T15; heard 4488 same-team decodes +
1050 enemy-bubble fixes; consumers fired (T-intercept 11, clear_grenade 13, C-escort
2). Human framing: these are building blocks for squad coordination — only T/E
expected to move outcomes yet; don't over-read the focusfire 6-4 (n=10; the A/B
lesson applies).

**Version map:** v15 = league champion (competing). v16 hearing. v17 = v16+HEARING=0
(A/B artifact, never submit). v18 = chat (current head). Next levers (human to
direct): squad movement/responsiveness on E/U (support/flank), danger-gated routing,
send-priority tuning (E/U dominate the budget).

## (prior) Status (2026-07-22, session 6c): **v16 HEARING built + measured** — uploaded, NOT submitted

Direction (human): teamwork, starting with using AUDIO to understand the map (chat
deferred). Game facts (b571dd3): `shot impact` rings = every bullet landing, audible
MAP-WIDE through walls/fog, ±20px jitter, team-anonymous, ~0.5s; `grenade sound`
same idea; shouts = ≤10 chars, ~247px radius, BOTH teams hear, jittered, carries
team+shouter identity. beacon was fully deaf before v16.

**v16 (uploaded):** sound-ring perception → deduped `HeardImpact` events (40px match,
60t TTL) → danger stamps (0.5 heat/32px, first-hearing only) → duck-on-heard-fire
(≤180px, fresh, own-fire suppression via aim-ray corridor). Tracing:
heard_events/heard_duck_ticks. Measured (1v1 x10 vs top-3; baseline = v15 recon2):
- Wins: h006 1-9 (same), **focusfire 4-6 (was 0-10)**, Picasso 9-1 (same). acc 0.658 (held).
- Activation: perception HEALTHY (95 heard events/agent); duck consumer NEARLY DEAD
  (0.5 ticks/agent — the 4-way gate rarely co-occurs). So the focusfire jump is
  probably the danger-stamp pathway (or variance) — NOT the duck rung. Verdict on
  hearing's win contribution: promising but unattributed; needs an A/B
  (BEACON_HEARING=0 arm) or a bigger sample before submit/credit.
Next levers: gate behaviors on the danger field (which hearing now feeds) rather than
raw heard events; then the chat layer (share enemy fixes/tactics — deferred by human).

## (prior) Status (2026-07-22, session 6b): RECON 2 of the current top-3 done — report `scratch/recon2_1v1/RECON_REPORT.md`

1v1s (beacon:v15, 10 eps each): **1-9 ctf-h006:v1** (Alex Smith, rank 1) · **0-10
ctf-focusfire:v36** · **9-1 Picasso:v16**. Profiles:
- **h006 = tick-0 blitz**: advance 356px at bucket 0, 103/214 kills in the first 1000
  ticks at 530px depth; Picasso-tier gun (0.551); arc-forward kit (10% alive-time,
  14% non-gun kills); mid-game escorted steals (median 4293, 67% conversion). Beats us
  by killing our attackers mid-push (178/222 beacon deaths before tick 2500 @ 571px).
- **focusfire v36 = same phase machine as v35** (steal gate now ≥ tick ~3900), item mix
  shifted toward arcs. Beats us in the long-grind lives race.
- **Picasso = solved** (9-1; its skirmish loses to our better gun + shield).
Strategic fork (human call): blitz-proof opening (defensive first ~1500 ticks / arc
denial) vs faster conversion vs opponent-adaptive opening — h006 and focusfire demand
opposite postures. Note: beacon has 0.609 acc this batch, best in field; "1v1" eval
shape now documented in `ctf_lab/user_preferences.md` + agent memory.

## (prior) Status (2026-07-22, session 6): **v15 SUBMITTED, QUALIFIED, CHAMPION** (human go-ahead)

Overnight check: game still deployed at 0.7.51/b571dd3, but that ref includes
**GameVersion 17: grenade blast radius 40→52** (only substantive delta vs c76e0c75;
arena hash + config.json + labels identical — v14's nav bake and wire port stay
valid). **v15 = v14 + the blast-radius constant** (widens the lob's teammate-splash
veto to 72px). Submitted `sub_443c6a23…` → membership `lpm_4f91376e…` **QUALIFIED →
competing → 👑 CHAMPION** (v6's old membership benched next commissioner pass).
Standings at submission: rank 7 (score ~0.0008 — 274 rounds of blind-v6 history;
expect the score to climb as v15 rounds accumulate). New field note: **Alex Smith
entered at rank 1 (0.838, 20 rounds)**, above daveey — worth reconnaissance once
they have round history.

## (prior) Status (2026-07-21, session 5b FINAL): **GOAL MET — v14 accuracy 0.657, items live.** v14 uploaded, NOT submitted (v6 still the competing entry)

**Endstate of the accuracy/items ladder (10-ep 8v8 vs each top-3 per version):**
| ver | acc | vs Picasso | vs autoresearch | vs focusfire | note |
|---|---|---|---|---|---|
| v10 | 0.234 | 5-5 | 7-3 | 0-10 | lead aim + items + wire port |
| v11 | 0.333 | 7-3 | 8-2 | 0-10 | max-range fire gate |
| v12 | 0.273 | 6-4 | 5-5 | 1-9 | windup freeze (regression exposed stale nav) |
| v13 | 0.312 | 7-3 | 9-1 | 0-10 | **GV16 arena rebake** + slack 8 |
| **v14** | **0.657** | 6-4 | **10-0** | 2-8 | boundary-crossing aim calib + glass-aware fire gate |

v14 beats every opponent on per-shot accuracy (them: 0.47-0.56). Items: shield
17.6% alive-time / grenade 10.8% / 55 non-gun kills / throws confirmed via traces.
**SUBMITTING v14 to the league is the human's gated call** (would evict v6).
Watch-outs: focusfire still wins the series (its phase machine, not our gun);
the arena is now GameVersion 16 — any future redeploy = re-check `ArenaLeftObstacles`
+ rebake (bake_map.py mirrors b571dd3).

## (prior 5b) Status: v10-v12 SKILL EXPANSION — lead aim + items; goal acc ≥0.5 + consistent item use

**Goal (human-set):** shot accuracy ≥0.5 and consistent+effective item use, measured in
8v8 single-policy-side xreqs vs each top-3 (10 eps each). Iterations (all uploaded,
none submitted):
- **v10** — velocity-lead aim (tracks EMA × LEAD_TICKS=6, ≥3-frame gate); item system
  (`items.py`: sim-mirrored spawn table, optimistic belief w/ seen-empty back-off,
  fog-gated pickup perception, hp/carried from overhead sprites, single-claimant fetch
  seat 2→shield 3/4→grenades, hurt→medkit; strategy rung 3.5); grenade C-button
  charge/release (SDK 7-bit mask clamp widened to 0xFF in main.py); **0.7.49+ wire
  port** (player stream back to 1x px — 0.7.8 renderer restore; flag labels
  `<color> flag [planted]`; aim readback = self sprite id 5100+rot, 16-step).
  Measured: acc 0.234 (spray: 7.8k shots), shield 20% alive-time, throws work,
  5-5 Picasso / 7-3 autoresearch / 0-10 focusfire.
- **v11** — FIRE_MAX_RANGE_PX=350 hold-fire gate + resync slack 12→8. Measured: acc
  **0.333** (range histogram monotonic 45.8%@<70px → 26%@280-350px), 7-3 Picasso /
  8-2 autoresearch / 0-10 focusfire. First-ever wins vs Picasso + autoresearch.
- **v12** — movement freeze through the 5-tick fire windup (sim fires from the
  shooter's CURRENT position along the LOCKED angle → our strafe displaced our own
  ray ~14px = full corridor). Carrier exempt. Measuring now (`scratch/eval_v12/`).

**Platform note: the league redeploys FAST** — 0.7.49 → 0.7.51 within this session
(each xreq's `coworld` field says which; get the ref via `coworld show <cow_id> --json`
manifest source_url). expand_replay pins so far: b571dd3=0.7.51, c76e0c75=0.7.49,
d60dc27=0.7.4, 761c098=0.5.4. Replay reader must match each batch's version.

## (prior) Status (2026-07-21, session 5): TOP-3 RECON DONE — full report in `scratch/recon_top3/RECON_REPORT.md`

**League moved again: ctf 0.7.49** (coworld `cow_07dfad4a…`, source ref `c76e0c75b…` —
read from `coworld show <cow_id> --json` manifest `game.runnable.source_url`). New since
0.7.4: **shields** (6hp, 3x slower fire) + **plasma arcs** (cone weapon). Replay-reader
pin bumped to c76e0c75 in `tools/build_expand_replay.sh` (old eras: d60dc27=0.7.4,
761c098=0.5.4). NOTE: beacon:v6 has NOT been re-ported/validated against 0.7.49 —
standings sank to **rank 6 of 6 (0.057, 256 rounds)**; checking v6 vs the new game
version is an open thread.

**Field (score):** 1. daveey/ctf-focusfire:v35 (0.941) · 2. softmaxwell/Picasso:v16
(0.767) · 3. Aaron/ctf-autoresearch:v28 (0.561) · relh (0.14) · richard (0.07) · us (0.057).

**Recon findings (hypothesis-tested over 95 league episodes, warehouse at
`scratch/recon_top3/wh`):**
- **focusfire = phase machine**: turtle+kill in own half to ~tick 2500 (0 steals before
  tick 3000 in 101 runs), push mid-game, cash in a late capture vs a thinned defense
  (steals at median 2 enemies alive). Focus fire confirmed (28% multi-shooter kills vs
  Picasso's 18%, matchup-controlled). Heavy item use: 12.7% shield / 7.2% grenade /
  4.9% arc alive-time; ~9.5% of kills are non-gun.
- **Picasso = best marksman** (accuracy tops every matchup incl. 0.514 vs focusfire) but
  its 88 steals convert 5.7% — median carry 23 ticks, 0px progress, stolen into 6 alive
  defenders. Steal↔win correlation is reverse-caused (already winning before stealing).
- **autoresearch = early escorted grab-and-run**: 42% steal conversion, escort at 96px
  (vs 300-380px others), steals at median tick 1902 into 3 defenders; wins avg 3380
  ticks. Only policy with seat-role structure (2 anchors + strike group). But 2-22 vs
  focusfire when the early grab fails.
- **Implications for beacon**: (1) don't feed focusfire's early kill-box — steal EARLY
  (≤~2000) with a ≤100px escort (autoresearch proves the pattern); (2) shields/items are
  uncontested strategy currency; (3) focus-fire targeting (wounded-target priority) is
  measurable and copyable.

**Warehouse upgrades this session (committed to tools/):** `expand_replay_json.nim`
rewritten to emit positions on kill/shot/steal/capture + periodic `pos`/`flag_pos`
snapshots (every 30 ticks) — spatial queries now possible. `event_warehouse.py` now
also ingests league episodes (identity from `policy_results` when xreq-style
`participants` is absent). Helper: `scratch/recon_top3/q.py` (dedup views over the
double-fetched league episodes — same episode can arrive under 2 policies' batches).

## (prior) Status (2026-07-14, session 3): LEAGUE REDEPLOYED ctf 0.7.4 — beacon ported to the new wire format

**The league redeployed** (new coworld `cow_e7586b05-3b53-465a-bb87-b9847a1b7bf9`, ctf
**0.7.4**, source ref `d60dc27` = coworld-ctf HEAD 2026-07-14; GameVersion 1→2; NOTE the
live xreqs report "ctf v0.7.4" — 0.7.3/`5450c64` + a disconnect-win fix + bot grenades). The old
`cow_325613c1…`/0.5.4 IDs below are stale. **Division scores RESET** — everyone 0.500 with
0 rounds; our old rank-#2 history is void. Breaking changes since our 761c098 pin:

- **3x observation render scale (0.6.0+):** map-layer object coords + sprite sizes arrive
  at 3x map resolution; recover map px via `(obj.x + sprite.w/2) / 3`. FIXED: perception
  `_center` divides once at the seam (`config.RENDER_SCALE = 3`); everything downstream
  (nav.npz, thresholds, belief, traces) stays in map pixels.
- **Flags → hearts (0.7.0):** capture-object labels now `red heart`/`blue heart`. FIXED in
  perception label lookups (internal names still say "flag").
- **Death no longer lifts fog:** a dead viewer sees only terrain, pedestal hearts, and its
  own `corpse <color> <side>` sprite. Perception already reads dead (no `self …` label);
  belief docs updated — dead frames carry no sightings, tracks just age, danger decays.
- **Grenades (0.7.0):** corner pickups, C-button (mask bit 128) charged throw over walls,
  ~40px blast, 2 dmg, hurts thrower/teammates too. Labels: `grenade`, `grenade air`,
  `grenade carried`, `throw target`, `blast stage N`, `grenade sound`. Beacon IGNORES them
  for now (correctness first) — a later iteration can pick up/throw.
- **Scoring:** WinReward 100 → +1 winners / -1 losers per capture-or-wipe.
- **Arena geometry: UNCHANGED** (sim.nim block byte-identical except exports) — `nav.npz`
  needs no rebake. Slot→team, aim/vision/speed constants, CarriedFlagLift all unchanged.
- `CTF_REF` re-pinned to `d60dc27` in `tools/build_expand_replay.sh` (old replays need the
  old pin). All 36 beacon tests green, incl. new wire-scale/heart/corpse regressions.

**DONE this session:** v6 (the port) built + uploaded; **6 x 10-episode 8v8 field evals
run** vs each current division entrant (ids in `scratch/eval_v6_field/xreq_ids.txt`,
results downloaded there, dashboard on :8765). **v6 post-redeploy baseline:**

| Opponent | Result | Notes |
|---|---|---|
| ctf-focusfire:v5 (daveey, #1) | **0-9** | beacon 0 captures, dies 23.9/game vs 13.3 — same gap as the old baseline bot |
| Picasso:v1 (softmaxwell, #3) | **10-0** | all by capture, 0 deaths |
| daf-actinf-ctf-v4:v1 (docxology, #4) | **10-0** | scores ±1 with 0 kills/0 captures/0 deaths — opponent likely never connected/abandoned; weak signal |
| ctf-flankfire:v1 (Aaron, #5) | **10-0** | all by capture, 0 deaths |
| co-gas relhalpha:v7 (#6) | **10-0** | all by capture, 0 deaths |
| co-gas richard:v7 (#7) | **10-0** | all by capture, 0 deaths |

The port restored full function: v6 cleanly beats everyone except daveey's new
**ctf-focusfire:v5**, which replaced ctf-baseline-16 as the wall (0-9, out-fought ~2:1
on kills).

**v6 SUBMITTED (human go-ahead) and QUALIFIED — now the competing champion entry**
(`sub_f319957b…`, membership `lpm_08989373…`, qualified in ~12 min, v5 benched).
Standings at submission: rank #2 of 7 (0.497, 64 mostly-v5 rounds) behind daveey
(0.679). Expect the score to climb as correct-wire v6 rounds accumulate.

**v7 (2026-07-15, uploaded, NOT submitted): peek-fire-duck micro — NO EFFECT vs
focusfire.** Design `docs/designs/ctf-peek-fire-duck-design.md`: fire→duck→peek cycle
(baseline lineage), wall-mask LoS rays in nav.npz, first consumer of the tracks
groundwork, `BEACON_PEEK_DUCK=1` default. A/B (10 eps each, 8v8):
- vs focusfire: v6 0-9 (kills 128/207, deaths 23.9) → **v7 0-9 (127/209, 24.0)** —
  statistically identical. The mechanism either never fires in the real fight shape
  or isn't the binding constraint.
- Regressions clean: flankfire 10-0, Picasso 10-0 (all by capture).
**ANSWERED (v8/v9 diagnostic, 2026-07-15): the micro FIRES — it just doesn't help.**
v8 = v7 + activation tracing (`belief.micro`, `micro` transition events, cumulative
`micro_ticks` in snapshots — now standing lab discipline, see `user_preferences.md`:
every behavior change ships with activation tracing). v9 = same image with
`BEACON_TRACE_OUTPUTS=jsonl@stderr` (the artifact-zip path comes back EMPTY from the
fetcher — policy_artifacts always []; stderr logs are the reliable channel). 3-ep
diagnostic vs focusfire: **duck = 14.0% of alive time, peek = 3.7%** (6,891/1,838
ticks across 24 beacon-agents; 421 duck + 219 peek engagements) — yet kills/deaths
unchanged (42/71, 23.0 deaths/game; 0-1 with 2 draws). Hypotheses (a) no-cover and
(b) never-triggers are REFUTED; **(c) stands: focusfire's edge is not cover micro —
likely target selection/velocity lead/focus-fire, or beacon's cover time is spent in
the WRONG places (ducking mid-push instead of fighting from prepared lines).**
Next lever candidates: velocity-lead aim + wounded-target priority (baseline's
prio = dist + traverse - hp bonus - focus bonus), or warehouse the diagnostic to see
WHERE deaths happen relative to micro state. v6 remains the competing champion;
v7/v8/v9 uploads inert.

**Crash scare (2026-07-15 evening — resolved, NOT a beacon bug):** a "v6 crashing
constantly" report was investigated; fresh league logs show v6 ending normally
("game over: server closed the connection" — v6 is stderr-QUIET by design since traces
go to jsonl@artifact; don't misread quiet logs as dead agents). The only real crash
traceback in fresh rounds was a co-gas policy (`bitworld_player.py`
ConnectionClosedError). MEANWHILE the field moved, twice: (1) the league coworld
redeployed again — now `cow_ffafb5af…` (still 0.7.4 @ d60dc27; our pin is current);
(2) daveey shipped **ctf-focusfire:v7** built specifically to beat beacon:v6
(coworld-ctf #9 "working grenade loop" + #10 "late all-in breaks peek-duck stalemates",
commit msg cites "8W-0L-16D vs beacon:v6"). Fresh v6-vs-focusfire:v7 league games score
0.0/0.0 (draws). Countering the grenade + tick-6800 all-in kit is the next strategic
question. Also: fetch_artifacts league-episode logs are keyed by AGENT ORDER not slot —
map slots via episode.json policy_results before reading.

## (prior) Status (2026-07-14, session 2): belief groundwork — player tracks + danger field (uncommitted)

Toward open thread 3 (close the baseline gap), beacon's belief state grew two folded,
**not-yet-gated** structures (`ctf/beacon/belief.py`, config knobs `BEACON_TRACK_*` /
`BEACON_DANGER_*`):
- **Player tracks** (`Belief.enemy_tracks` / `teammate_tracks`, `PlayerTrack` in types.py):
  last-seen pos/tick/facing per player, greedy nearest-neighbour association under a
  reachability gate (Chebyshev, since velX/velY clamp per-axis: MAX_SPEED_PX_TICK = 704/256
  = 2.75 px/tick/axis from sim.nim), EMA velocity across close sightings, TTL 120 ticks
  (~5 s, matches the baseline's). Updated while dead too (ghosts see the whole map).
- **Danger field** (`Belief.danger`, float32 [GRID_H, GRID_W] 0..1): init hot on the enemy
  half / cold on ours; visible enemies stamp 1.0; spreads one walkable-masked 3x3-max ring
  per NAV_CELL/(0.75 x max speed) ticks (~every 3.9 ticks — deliberately slower than a
  fleeing player so the zone lingers); exponential decay half-life 48 ticks.
- **Tracing:** every `snapshot` trace event now carries `enemy_tracks`/`teammate_tracks`
  (pos, age, facing, vel, frames_seen) and `danger` (block-max 4x-downsampled 38x20 grid,
  quantized 0..255, `cell_px: 32`) — renderable as a heatmap; warehouse ingests it as-is.
  Cost: ~3.6 KB/snapshot, update_belief ~15 us/tick.
- Nothing reads these yet — next iteration gates ONE behavior on them (pursuit,
  exposure-aware routing, or aim-at-danger) as its own attributable A/B.
- Known limits (documented in belief.py): no kill percept, so dead enemies' tracks linger
  to TTL; own vision doesn't clear danger (a swept-empty corridor stays hot until decay).

**Replay-overlay upstream change (2026-07-14): PRs OPEN.** Sprite-v1's 0x86 debug-sprite
channel is now implemented end-to-end for CTF; design doc at
`docs/designs/ctf-debug-sprite-overlay-design.md`. Two PRs (designed here, implemented by
Codex under review, both test-green):
- **Metta-AI/bitworld#235** — debug-sprite codec (master's 87724ba) cherry-picked onto
  `daveey/hd-client-pin` (the branch CTF pins; master lacks the HD client). Includes a fix
  for the branch-tip test failure (stale 0x7f mask assertion after ButtonC).
- **Metta-AI/coworld-ctf#6** — server validates (structure + snappy pixels,
  32 KiB/player/tick cap) → records (replay record 0x06) → folds into per-player
  DebugOverlay; keyframes SNAPSHOT overlays (leaves shift indices, so prefix re-fold is
  inexact); global viewer renders the selected player's overlay (map layer, z=29000, id
  pools 40000+idx*1024, payload ids 0..1023). 8 new tests; full suite 67 green.
  DEPENDS on #235: after it merges, bump nimby.lock's bitworld SHA on the PR branch
  (worktrees live at /tmp/codex-ctf-overlay/{bitworld,coworld-ctf}).
Still needed after merge: SDK `pack_debug_sprites_packet()` (coworld-tools), beacon
emitting overlays (danger heatmap + tracks + path), league redeploy for hosted replays.

## (prior) Status (2026-07-14): beacon:v5 SUBMITTED, qualified, competing — rank #2 of 6

**v5 was submitted** (`sub_fb788e45…`, membership `lpm_d5d2e3dc…`) after the session below,
qualified, and is now **competing as our champion entry** in Competition
(`div_37361341…`): **rank #2 of 6, score 0.298** (46 rounds) behind daveey's champion
(0.434). The field grew to 6 entrants — a new #3, Aaron's `ctf-flankfire:v1` (0.274,
173 rounds), sits close behind us. Recent-round form (last 20 rounds, 2026-07-14):
beacon avg round-score ≈0.34 vs daveey ≈0.38 — closer than the cumulative scores suggest.

## (prior) Status (2026-07-10, session 1): beacon:v5 takes games off the baseline (4-11)

**v5 (latest, uploaded — NOT yet submitted):** carrier escort + attack bias. v4 diag vs the
baseline showed attackers grabbed the flag but died solo before delivery, while 5 defenders
sat idle (baseline barely attacks; captures ~0 both sides). v5 adds an **escort rung**
(attackers converge on a teammate carrier and move home WITH it) and shifts **DEFENDER_COUNT
5→3** (5 attackers push+escort). Results:
- **vs baseline: 4-11 (26% win), 4 captures** — up from v4's 0-20/0 captures. First version to
  take games off the champion. Still dies 20.9/game — it wins by CAPTURING before being wiped,
  not by out-fighting.
- **vs co-gas: 16-0, 16 captures, 0 deaths** — no regression (cleaner than ever).

**v4 is the currently-submitted/competing version** (`sub_b7fe5799…`). **v5 is a strict
improvement — re-submitting it is the human's gated call.**

## (prior) Status: beacon:v4 fixes CAPTURE; v3 is the competing champion

**v4 (latest, uploaded, NOT yet submitted):** fixed the "stuck on the flag" bug — a carried
flag renders ~10px above its carrier (`CarriedFlagLift`), but perception's carry threshold was
6px, so `i_carry` was NEVER true (0/38,204 snapshots); the carrier sat on the pedestal in
"steal" mode. Fix: `_CARRY_DIST` 6→24px + pedestal-before-carry ordering + 3 regression tests.
- **vs co-gas: 20-0 by CAPTURE** (1 capture every game; kills 496→5, deaths 3.4→0.0/game —
  games now end instantly by grab-and-run instead of attrition). Bug fully resolved, confirmed live.
- **vs baseline: still 0-~7** (0 captures either side, beacon wiped 24/game). Against the elite
  Nim champion beacon dies before completing a grab-and-run; capturing didn't crack it.

**v3 is the SUBMITTED, qualified, competing entry** (`sub_6f0eb779…`, membership `lpm_d3691543…`).
v4 is a clear improvement (real captures) — **re-submitting v4 is the human's gated call.**

## (prior) Status: beacon:v3 built, uploaded, SUBMITTED — qualifying

The first CTF player, **`beacon`**, is live. A deterministic Player-SDK SpriteV1 cyborg
(design: [`docs/designs/ctf-player-v1-design.html`](docs/designs/ctf-player-v1-design.html)),
vendored at `ctf_lab/ctf/beacon/`. Three iterations shipped this session:

- **v1** minimal loop — lost 0-12 to the baseline (rushed solo, got wiped).
- **v2** seat-based roles (5 defenders hold our turf / 3 attackers push) — 0-10 vs baseline,
  7-8 vs co-gas.
- **v3** friendly-fire gate + cover-seeking defenders + teammate perception — **19-0 vs
  co-gas** (FF was the big cost: beacon deaths 6.1→3.4/game), still 0-20 vs the baseline.

**Submitted `beacon:v3`** to the CTF league (`league_3243d905…`), submission
`sub_6f0eb779…`, membership `lpm_d3691543…`, `--auto-champion always`. **Status: placed,
qualifying async** in Qualifiers(staging) — the commissioner runs qualifier rounds on a
~30-min schedule, so qualification is not instant. Check with:
`uv run python .claude/skills/coworld-policy-lifecycle/scripts/policy_lifecycle.py monitor --name beacon`

**Where beacon stands:** clear **#2 of 3** in the division — dominates both co-gas variants,
loses only to the elite purpose-built Nim `ctf-baseline-16` (rank 1). "Doing well"
field-relative; not the champion.

## Key facts (hard-won this session — full detail in TENTATIVE_LESSONS.md)

- **Games are decided by WIPE, not capture** — captures are ~0 on both sides every game;
  the team that keeps its lives wins (wipe, or time-limit tiebreak on lives remaining). So
  survival ≥ attacking. Metric = win rate + deaths/game, not K/D.
- **Friendly fire is ON and was beacon's biggest cost** — v2 lost 6/game to its own bullets.
  The teammate-in-corridor fire gate (v3) fixed it → co-gas 7-8 → 19-0. Gate snap-fire
  before anything else.
- **The baseline is a very strong Nim bot** (tracks, exposure-cost nav, peek-fire-duck).
  Beating it head-to-head is the division's hardest bar; beacon hasn't yet.
- **beacon never actually CAPTURES** — attackers reach the enemy pedestal (x≥1049) but
  `i_carry` never fires. Either the touch/carry-detection is too tight (perception uses
  ≤6px; baseline uses ≤4px and works) or attackers die/get blocked before the grab. This is
  the top open thread — capturing would win the wipe-stalemate games outright.
- Eval infra: matched 8v8 head-to-heads (team_blocks seating = the real league shape).
  `ctf_lab/tools/agg_eval.py <dir>` aggregates a results dir. Streaming `--watch` fetch got
  stuck "pending" once; a one-shot `--no-replay --no-logs --no-artifacts` results fetch is
  the reliable fallback.

## Open threads (next steps, human-directed)

1. **Confirm beacon qualified** (monitor above) — should enter Competition as #2.
2. **Make beacon CAPTURE** (highest-leverage next lever): fix carry detection / push more
   attackers / escort the carrier. Winning the wipe-stalemate games vs co-gas is already
   done; capturing is how you start taking games off the baseline.
3. **Close the baseline gap**: enemy-track memory (remember foes after they leave the cone),
   exposure-aware routing (avoid cells a remembered enemy covers), peek-fire-duck micro —
   the baseline's remaining edges. Each is one attributable iteration.
4. Ereq ids + results for this session live under `ctf_lab/scratch/` (gitignored).

## Eval how-to
- Division `div_37361341-2970-4dac-9528-55398bab0d1a` (Competition),
  `div_64d9b2dc…` (Qualifiers), league `league_3243d905-d32d-4ec6-978b-fa94751d4a37`,
  coworld `cow_e7586b05-3b53-465a-bb87-b9847a1b7bf9` (ctf **0.7.4**, redeployed 2026-07-14;
  scores reset). Field (7 entrants): daveey, Aaron (`ctf-flankfire`), us, softmaxwell,
  docxology, Richard Higgins, RelhAlpha.
- Build: `ctf_lab/tools/build_player.sh beacon --tag players-beacon:dev`; upload:
  `uv run coworld upload-policy players-beacon:dev --name beacon`.
- beacon behavior knobs are env vars (`BEACON_DEFENDERS`, `BEACON_FF_CORRIDOR_PX`, …) in
  `ctf/beacon/config.py` — set at upload time for A/B.

## Discipline (from [`../AGENTS.md`](../AGENTS.md))

Human sets strategic direction; you build observability, measure, hold the correctness gate.
**Propose-and-pause.** Change one component per iteration. Uploading is routine/ungated;
**league submission is the human's gate** (done this session with explicit go-ahead).
