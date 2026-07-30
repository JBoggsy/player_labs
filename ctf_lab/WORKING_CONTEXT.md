# CTF working context

**What this is.** The live, high-signal state of *what we're working on right now* in the
CTF lab — the minimal cross-session facts to carry into the next session. Read it on
startup to resume; **update it as you learn** (keep it tight).

> Read order for a newcomer: this file → [`README.md`](README.md) →
> [`docs/ctf-gameplay.md`](docs/ctf-gameplay.md). And the lab-wide
> [`../AGENTS.md`](../AGENTS.md) for the operating model.

---

## Status (2026-07-30, session 12): v56 champion; v57 nearby-grenade convenience validated, not submitted

**Competing CTF and Paintbot champion:** `beacon:v56`, immutable version
`3e40a528-71ec-42c7-b6eb-3b1f5188dc00`. v56 prevents formation, separation,
and peek/duck movement overlays from crossing the glass lineup walls; it passed a
fresh matched gate 10–0 versus v48 at 9–1 before explicit submission.

**Latest inert candidate:** `beacon:v57`, immutable version
`4c1c0723-3dc5-42fc-ac39-dd031a11e94d`, image digest
`sha256:096478b7332bcbc69176da26da46ea7ab09b9810f40ef79766207fe0455608a6`.
It preserves v56's medkit and assigned-item decisions, then lets another bot take
an own-side grenade only when its route is at most 64 px, or 96 px during the
fresh-respawn window. Shield and spray acquisition remain gated until their
tactical doctrines are ready. **v57 was uploaded for evaluation and was not
submitted.**

Activation and hosted gate on CTF 0.7.124:

- 11 convenience starts across 6/10 traced games, all fresh-respawn corner
  grenades; no ordinary pickup fired in that matchup.
- Against live leader `deltashot:v3`, v56 and v57 both finished 5–5 with the
  identical 5–0 Red / 0–5 Blue split.
- Replication versus `co-gas-ctf-simple-richard:v38`: v57 finished 10–0
  (`xreq_6ee9ab0f-490a-4d3b-b258-ba3e16fca3a2`). The v56 control had eight wins
  and one loss in nine indexed completed episodes; one episode remained
  abnormally long-running without an error at handoff
  (`xreq_f028dbe8-afd8-4c2b-9131-d4269fb0782f`). Its eventual result cannot
  overturn v57's outcome non-regression verdict.

The current Coworld source is `Metta-AI/coworld-ctf`
`beae1614ea28c3d7761bae614ae974477db35b2d`, deployed as CTF 0.7.124 /
GameVersion 27. Next item capability: tactical grenade selection for groups and
wall-blocked enemies, with rare use on a single shootable target. Use v57 as the
control. Episode search should screen outcome equivalence first; download one
traced candidate batch only, because dense artifacts are roughly 11–12 MB per
bot and redundant downloads now dominate analysis time.

## Status (2026-07-29, session 11): v40 post discipline evaluated; Reporter Lab adapter + reciprocal firefight detector ready

**Evaluation artifact only:** `beacon:v40`, immutable version
`c8ab6032-20bc-4600-80af-f1c52d9a7cea`, image digest
`sha256:11ad6866c6407ce6ce94240d480a5a0159c920a602d171967afb1e351b0f6d01`.
It keeps v39's `firefight_training_line`, but makes both hold and push posts prefer
forward ground, commits reached posts through local traffic/contact, raises post-switch
hysteresis, and scans the post's best baked primary/shoulder sightlines.
**It was not submitted.**

Three matched 10-episode 8v8 evaluations completed with zero failures:

| opponent | XP request | Beacon result | captures | kills |
|---|---|---:|---:|---:|
| `ctf-focusfire:v63` | `xreq_211ef2e1-d263-465e-8eeb-b253549e0061` | 1-9 | 1-6 | 174-222 |
| `ctf-h050:v1` | `xreq_f6c93f22-ee67-43d9-a180-76271f59d5c8` | 8-2 | 1-0 | 230-208 |
| `alphashot:v222` | `xreq_d5e48a00-7be6-4a4a-9620-fddeca28563c` | 0-1-9 draws | 0-1 | 59-58 |

Against the v39 batches, raw Beacon telemetry shows 9,540 -> 6,122 total post
transitions (-36%), 7,185 -> 3,894 active reselections (-46%), 55% -> 68% of
post-active snapshots settled, and 64% -> 68% selecting positive forward stance.
One of 80 Beacon artifacts is absent in the alpha arm; trace totals use 239/240
agent-games, while episode results are complete.

`tools/run_roundwarehouse_local.py` is now the thin local host adapter for Reporter
Lab's unchanged, unpublished CTF roundwarehouse Wasm; replay event semantics remain
owned by Reporter Lab. `tools/find_firefights.py` consumes its rich Parquet events,
deduplicates released weapon actions, forms reciprocal spatiotemporal exchanges, and
weights them by activity, balance, damage, casualties, breadth, and duration. On v39:
30/30 expansions, 44,962 events, 184 fights. On v40: 30/30, 41,503 events, 174
fights; action volume is nearly flat (5,507 -> 5,422) and attributed fight kills rise
860 -> 875, so the training plan still produces dense combat despite fewer post moves.
Method/provenance: `docs/replay-firefight-detection.md`.

The live Coworld is **ctf 0.7.112 at
`f24943a10dd7383e8e92e77be28d2d75e091a577`**. Its only change from 0.7.111 is
config-gated procedural terrain; these XP requests retain `mapPath: arena`, and there
was no GameVersion bump.

## Status (2026-07-29, session 10): firefight-training v39 uploaded and observed; opponent-plan inference tool added

**Evaluation artifact only:** `beacon:v39`, immutable version
`8c7e2943-d9f9-4faa-96ec-f022509a93df`, image digest
`sha256:71284f83971404328045c168faa1c8bcac55f0b8c69f4bad80d7a58628113417`.
It runs `firefight_training_line` with firefight scoring on, focus claims off, posts on,
and dense artifact tracing. **It was not submitted.**

The live Coworld is now **ctf 0.7.111 at `f9e0889466dcd05489d13b51846b5aa5f1527ef2`**
(still GameVersion 26, now 10,000 max ticks). The replay readers and `versions.env`
were advanced to that exact source ref.

Three 10-episode 8v8 hosted evaluations completed against the then-current top three:

| opponent | XP request | Beacon result | captures | kills |
|---|---|---:|---:|---:|
| `ctf-focusfire:v63` | `xreq_0c252cfd-31a2-41dd-96ab-9ebd5a538971` | 5-5 | 2-3 | 216-221 |
| `ctf-h050:v1` | `xreq_f6c91d31-2f10-4a94-ad78-a45ea2f0b3d6` | 8-2 | 2-0 | 216-200 |
| `alphashot:v222` | `xreq_47955bc5-086c-4954-874d-3d5c59fe03e8` | 0-0-10 draws | 0-0 | 62-53 |

The h050 traces alone record 74,031 firefight ticks, 485 engagements, and all four
plan phases. This is evidence that the training instrument activated, not evidence that
v39 is competitively better; the samples are small and deliberately lack a matched
control.

`tools/infer_battle_plan.py` now converts repeated, hash-validated replay trajectories
into JSON/Markdown timelines of persistent groups and inferred move/hold/maneuver
orders. Seed reports for all three opponents are under
`scratch/eval_v39_training/*_inferred_plan.{json,md}` (gitignored); the method and
interpretation limits are documented in `docs/opponent-plan-analysis.md`.

## Status (2026-07-29, session 9 END): **GAME JUMPED 0.7.102/GV23 → 0.7.108/GV26. Firefight measured over 360 eps: NOT significant, DO NOT SUBMIT. Real bottleneck = CAPTURES, not combat.**

**Competing entry: v33 (posts), now league RANK 2 @ 1929 over 247 rounds** (up from
rank 5 @ 1559 at submit — the posts A/B translated). Champion is daveey @ 2293.
v35–v38 uploaded as A/B arms only; **nothing new submitted.**

### The game changed — what it means for beacon (all verified this session)

Deployed **ctf 0.7.108 = commit `a2ec0cc` = GameVersion 26** (resolve the ref by
grepping a 40-hex sha out of `coworld show <cow_id> --json`; the parsed
`game.runnable.source_url` field reads None but the sha is in the raw payload).
60 commits landed since our GV23 pin. What actually touches us:

| change | effect on beacon |
|---|---|
| **GV24: enemy sprite gun rotation FUZZED ±14 brads (~±20°)**, re-rolled every 12 ticks | **No functional impact.** The `<side>` label is derived from the *fuzzed* rotation (`soldierFacingRight`), so enemy `facing` is now noisy near the vertical boundary — but beacon only stores `facing` on tracks and traces it. Nothing decides on it (`strategy.py:250` is a *battle-plan* order facing, unrelated). beacon reads no enemy aim. |
| **GV26(a): SELF marker renders TRUE aim again** | **Good — and note the window.** beacon reads its OWN aim from the self sprite's rotation id (`perception._find_self`, `5100 + rot`). GV24 fuzzed self too, so during GV24–GV25 that readback was corrupted; GV26 exempts self. Used only to correct dead-reckoning drift, so impact was bounded. Our 360-ep ladder ran on GV23 (pre-fuzz) and is unaffected. |
| **GV25: respawn at a RANDOM spot in the home endzone** | Neutral structurally — beacon has no fixed-respawn assumption (all its `*_RESPAWN_TICKS` are ITEM respawns). Kills spawn-camping as a tactic. |
| **GV26(b): HEART carriers fire at 1/3 rate** (`CarrierFireSlowdown=3`) | **NEW and unmodelled.** beacon mirrors `carrierSpeedPct` (70%) but knows nothing about carrier fire rate. Directly relevant to the capture problem: a carrier that stops to fight is now much weaker, so carrying should be evasion + escort-does-the-shooting, and *enemy* carriers are soft targets. |
| **GV26(c): column-1's fifth vertical bar → glass window** | **NO NAV REBAKE.** Commit `3412b24` flipped an EXISTING rect `(268,395,18×60)` to `window: true`. beacon's `bake_map.py` `_RECTS` holds that exact rect and its comment already documents that glass stays in the WALL set (glass blocks movement, bullets, plasma; transparent only to fog-of-war, which the bake does not model). Walls, flow fields and shot sightlines all unchanged. |
| **Server randomizes the game seed** (`c3e3d9a`) | Visible live: `game_config.seed` is now `None` (was `679961`). Better A/B independence; specific episodes are no longer reproducible. |
| `ctf-doubles` variant now uploaded alongside every ctf build | Unexplored. |

Unchanged and re-verified against a live 0.7.108 episode: `maxTicks 5000`,
`visionConeDeg 45`, `lives 3`.

### BREAKING: the replay reader is era-locked — rebuilt at GV26

A GV23 reader on a fresh GV26 replay dies with `Replay game version does not
match`, and the reverse is equally true. This blocks the **event warehouse** and the
**viewer bundler** on new episodes. Fixed: rebuilt at `a2ec0cc` and
`tools/build_expand_replay.sh` now pins it, with the era table in its header.

**The stable symlink tracks the CURRENT league era, so analysing an OLDER batch
requires naming that era's binary explicitly.** For the 2026-07-29 ladder (GV23):

```
uv run python ctf_lab/tools/event_warehouse.py --episodes <dir> --out <wh> \
  --expand-replay ctf_lab/tools/bin/expand_replay_json-cdd567f
```

### Firefight ladder: 360 episodes, 4 arms × 3 opponents × 30 eps

Pooled over the two decisive opponents (alphashot excluded — draw-locked):

| arm | wins | rate | vs baseline |
|---|---|---|---|
| v35 postsonly (= v33 baseline) | 11/60 | 18.3% | — |
| v36 firefight, NO claims | 17/60 | **28.3%** | p=0.140 |
| v37 + focus claims | 13/58 | 22.4% | p=0.374 |
| v38 + wider spacing | 8/60 | 13.3% | p=0.841 |

**Verdict: DO NOT SUBMIT.** v36 is best at +10pp but p=0.14, and **kills are flat
across all four arms** (enemy lives removed/ep vs h050: 19.4 / 20.2 / 19.0 / 19.3) —
a fight change that doesn't move kills almost certainly didn't move win rate. The
ordering v36 > v37 > v38 does hold on *both* opponents, which is weak evidence it's
real. **Coordination and wider spacing both HURT** — if firefight ever ships, ship it
WITHOUT claims.

### The actual bottleneck: we don't STEAL. Delivery is already fine.

This is the most important result in the session and it is narrower than "captures".

- **Out-captured 6–8×**: vs h050 **5 to 31**; vs focusfire **3 to 24** (60 eps each,
  replay ground truth) — while removing ~19–20 of 24 enemy lives per game.
- **But steal→capture CONVERSION is NOT the problem.** vs h050 we convert **26%** to
  their 29%; vs focusfire **20%** to their **17%** — we are *better* than focusfire at
  finishing a steal. Escort/return work would be fixing something that isn't broken.
- **The deficit is entirely in REACHING their flag**: 19 steals vs their 106 (h050),
  15 vs their 143 (focusfire) — 5–9× fewer attempts.
- **We stall at their defensive line.** Our bots die at median depth 614–672px past
  our own wall (midfield is 617), dying past midfield 49–63% of the time — but the
  flag is at x=1049, so we expire ~380px short.
- **THE ROUTE FINDING.** Approach route in the 10s before a steal (extreme y reached):

  | | top swing (y<140) | **bottom swing (y>520)** | straight mid |
  |---|---|---|---|
  | them (n=249) | 25% | **54%** | 20% |
  | us (n=34) | 9% | 6% | **85%** |

  They swing wide, favouring the bottom. We grind up the middle. `staged_push_top`'s
  own summary calls the bottom *"deliberately naked"* — it is simultaneously the route
  they raid us through and the route we never use.
- **Suggestive but CONFOUNDED:** bots *ordered* to `blue_pedestal` (flank_n) arrived
  within 60px only **1–7 times in 118 episodes**, while the held-back rear arrived
  **14–25** times. The rear also lives longer, so this is not proof the plan causes
  the low steal rate. **A `BEACON_PLAN=""` control arm would settle it** and is cheap.
- **Falsified my own hypothesis** that brawling causes losses: wins average *more*
  contested firefight time than losses (54.7s vs 50.4s vs h050) and high-firefight
  episodes have *more* captures. Fighting isn't hurting; it isn't the constraint.
- **vs alphashot we are draw-locked**: 0% wins, 25–30/30 draws, only 7.9 of 24 enemy
  lives removed (vs ~19.4 elsewhere). A capture problem, not a fighting one — exclude
  it from pooled *fight* statistics.

### Firefight's own design bug, if it's ever revisited

**63–69% of target selections are unshootable at selection**, and 24–30% are beyond
the 350px fire gate (seen directly: `range_px 424.12`, `shootability -1.0`). Selected
range averages ~270px while shots land at ~207px. `shootability` only ranks *among*
visible candidates, so when all are unreachable it still picks one and latches (min
dwell 8t, margin 0.10). Needs a "no acceptable target" state that declines to latch,
and an ideal band re-centred on where shots actually connect.

### Warehouse traps (see `scratch/HANDOVER-warehouse-findings.md`)

- **Every outcome column is dead.** `participants.score/win/kills/deaths/captures` are
  null in 1920/1920 rows and `episodes.winner` is `"draw"` for all 120 episodes,
  because `event_warehouse.py:92-97` reads them from a `results.json` the platform no
  longer serves (`! results artifact unavailable` even with default flags). The tables
  build without error, which is what makes it dangerous. Derive win/draw/loss from
  `episode.json` `scores` joined on **`policy_name`** (the participant field is
  **`position`**, not `slot`); see `tools/fight_ab_report.py::outcome_of`. Kills and
  captures come from `replay_events`.
- **`shot`/`hit` events exist but aren't in the module docstring** — 24,979 and 15,774
  rows with shooter `{x,y,aim}`. They enable accuracy, fire-range and engagement
  analysis; `tools/find_firefights.py` segments two-sided firefights from them.
- **`event='snapshot'` is a sparse periodic dump** (~35/bot/episode). The detail is in
  transition events: 174 `firefight_target` (full score decomposition) and 215
  `focus_claim` per bot. Read those, not snapshots. `firefight_target.cell` is in
  PIXEL space despite the name.

### Coordination note — READ THIS IF SEVERAL SESSIONS ARE RUNNING

Another agent is expanding the **warehouse reporter**. As of session 9 end I had NOT
modified `event_warehouse.py`, `viewer.html`, or `viewer_bundle.py` — check `git log`
before assuming that is still true.

Hazards for parallel sessions in this one repo:
- **Never run a background writer against the MAIN working tree.** I pointed a Codex
  job at the main checkout to edit `viewer.html`; it happened to finish without
  writing, but that is exactly how two agents clobber each other. Use a git worktree.
- **Shared files to touch with care:** `WORKING_CONTEXT.md`, `TENTATIVE_LESSONS.md`
  (append-only; a SessionStart hook rotates it into `lessons_archive/`),
  `ctf/beacon/config.py` (every path wants knobs here), `tools/versions.env`.
- **A running `plan_server.py` writes `battle_plans/*.json`** on the editor's Save —
  do not hand-edit the same plan file while a human has it open in the editor (its 2s
  ETag poll will warn, but only if it has unsaved edits).
- `scratch/` is gitignored; treat it as per-session workspace, not a handoff channel.
  Cross-session handoffs go in this file or in a committed doc.

### Battle-plan work started (session 9 END)

`BEACON_PLAN` defaults to **`staged_push_top`**, so the plan interpreter is **already
live in the champion** — editing a plan changes shipped behaviour. Confirmed executing:
bots advance ~2.17 phases, ~half end in phase 3, the hold `fallback` never fired
(0/60), buddy-wait ~82 ticks per agent-game.

**New: `battle_plans/staged_push_bot.json`** — same cover-to-cover staged shape aimed
down the bottom, 6 phases / 20 draft orders, all on named POIs so they drag. The spear
walks `red_rally_bot(421,597) → red_bot_triangle(479,546) → bottom_diamond(617,467) →
blue_bot_triangle(755,546) → blue_pedestal(1049,329)`, splitting only at the steal
(`grabbers [4,5]` / `holders [6,7]`) so it stays together through the exposed crossing.
`screen [2,3]` feints at `red_rally_top`; `home [0,1]` finally covers `red_bot_hold`.
Status **proposal — not wired to any upload.** All 33 locations verified via
`poi.resolve`; interpreter reads back 6 phases / 20 orders / the split.

**Editor:** `uv run python ctf_lab/tools/plan_server.py --port 8792` then
`http://localhost:8792/tools/plan_editor.html`. Added a **New** button (in-memory only
until Save, so a mistyped name can't clobber a file).

**Three plan-authoring gotchas learned the hard way:**
1. **A late entry tag STALLS the push.** Only `tick`/`enemy_lives`/`own_deaths` are
   machine-evaluated (`plan.py:142` `_TAG_RE`), and a phase's entry tag must ALSO hold
   before a bot advances — so `tick>=900` freezes a bot that already arrived. With
   ~407-tick mean lifespan vs alphashot, that is how bots never reach the steal phase.
   Keep tags permissive and let MILESTONE drive; the 900-tick timeout is the fallback.
   `staged_push_top` has this flaw: its steal phase gates on `enemy_lives<=18`.
2. **`via` waypoints are parsed but never consumed** (`plan.py:64,109`; no `.via`
   reader downstream) — editor-only decoration. The per-phase target IS the routing,
   which is why the bottom push is six hops rather than one arrow with waypoints.
3. **A plan with `orders: []` renders a blank canvas** — the renderer is fine. If you
   want something to drag, author the orders.

### Firefight-training battle plan (2026-07-29)

**Executed evaluation plan: `battle_plans/firefight_training_line.json`.** This is deliberately
an evaluation instrument, not a competitive plan: four bots establish and hold
`red_rally_mid`, with two each at `red_top_vee` and `red_bot_vee`. At tick 600
(25 seconds at 24 ticks/sec), the groups advance to center, `top_diamond`, and
`bottom_diamond`, then hold those positions for the rest of the game. Its objective
is dense, varied engagement traces for improving firefight mechanics; do not judge
it by win rate and do not submit it. It was baked into `beacon:v39`, uploaded without
submission, and evaluated in the three session-10 XP batches summarized above.

### In flight / unanalysed

- **30 GV26 baseline episodes DRAINED but NOT fetched or analysed.** `beacon:v35`
  (posts on, firefight off ⇒ v33 behaviour) × 10 eps vs each of `ctf-focusfire:v63`,
  `ctf-h050:v1`, `alphashot:v222`. IDs: `scratch/eval_gv26_base/xreq_ids.txt`. This is
  the comparison point any new plan must beat, and it also shows whether the GV26 rule
  changes moved anything on their own.
- **Field moved again (2026-07-29 late):** focusfire **v63** rank 1 @1991,
  **h050:v1 now rank 2** @1911, osprey:v12 rank 3, alphashot **v222** rank 4 @1620.
  Re-resolve before composing any roster.

### Next — INDEPENDENT paths (safe to run in parallel sessions)

Each path names the files it owns. **Stay inside your path's files** so parallel
sessions don't collide, and remember another agent owns the warehouse reporter.

1. **Battle plan / steal rate** — owns `battle_plans/*.json`, `ctf/beacon/plan.py`.
   Finish `staged_push_bot`, then A/B it vs `staged_push_top`. Run the
   `BEACON_PLAN=""` control arm at the same time to settle whether the plan helps at
   all. Primary metric: **steals**, not win rate (steals are ~5× more frequent, so far
   cheaper to resolve at n=10-30).
2. **Fire gate / accuracy** — owns `ctf/beacon/action.py`, `ctf/beacon/fight.py`,
   `config.py` FF knobs. The measured constraint: selection moved to long range but
   shots did not (0-199px share only 47%→45%). Fix the "no acceptable target" latch bug
   and re-centre the ideal band on where shots actually connect (~207px).
3. **The alphashot draw-lock** — 0% wins across all four arms, 25–30/30 draws, only
   7.9/24 enemy lives removed. Needs its own diagnosis; fight tuning cannot touch it.
   GV26(b) (carrier fires at 1/3) and GV25 (random respawn) are both unexploited.
4. **Firefight viewer overlay** — owns `tools/viewer.html`, `tools/viewer_bundle.py`.
   **Use an ISOLATED WORKTREE.** 8 bundles ready in `scratch/fight_bundles/`. Render
   the transition events (174 `firefight_target`, 215 `focus_claim` per bot), NOT the
   sparse snapshots.

**Do NOT submit anything** without a fresh A/B that clears significance; v33 is the
competing champion at rank 2 and the firefight ladder did not beat it.

---

## (measurement detail) Status (2026-07-29): firefight implementation reference — flags, protocol, tracing, tunables

Beacon now has intentional gun targeting behind `BEACON_FIREFIGHT=1`: `fight.py`
scores at most eight visible enemies by ordinal wound level, a 220–300px effective
range band, bounded focus-claim bias, baked bullet sightline + friendly-fire
shootability, aim traverse, and shield state. A short target latch prevents
thrash, while an unshootable current target may switch immediately. The overlay
does not alter `strategy.py` or any movement rung. Plasma-arc carriers keep the
legacy short-range weapon behavior, with excluded firefight-eligible ticks counted
as `firefight_arc_exempt_ticks`.

`BEACON_FOCUS_CLAIMS=1` adds identity-first `FI<seat><identity><cell>` and
cell-fallback `FC<seat><cell>` shouts at the exact arbitration position
`C > T > O > G > U > K > F > E > P`. Exclusivity is local to one fight
(400px), not team-global. Claims are a bounded score bias, not orders, but they
are load-bearing convergence machinery: the score is not literally shared because
range, aim cost, visibility, and friendly-fire corridors differ by bot. Claims
expire on their communication clock even if the target remains visible; missing
targets release earlier on a corroborating aggregate enemy death or on a fixed
missing-target fallback.

Both flags default OFF. Trace output includes mode transitions/ticks, decomposed
target scores, one cumulative `firefight_target_switches` counter, claim
send/hear/suppression/release data, friendly-fire suppression, arc exemptions,
and distributions of selected-target and actual-shot ranges. Beacon cannot
observe kills, so true kill ranges remain replay-ground-truth analysis.

Firefight parameters now come from the family-tagged `TUNABLE_REGISTRY` in
`config.py`, including the pre-existing FF corridor. `python -m
ctf.beacon.tuning dump` exposes JSON domains/invariants; `secret-env NAME=VALUE
...` validates a sweep assignment and emits the repeated Coworld upload flags.
The README documents the build → upload → matched hosted-arm workflow.

**Hard mechanism bound:** this iteration can move the 187px measured kill-range
baseline toward the 220–300px target band, but cannot produce a meaningful 400px+
kill tail. `FIRE_MAX_RANGE_PX=350` and the aim/fire geometry are deliberately
unchanged; a 400px+ tail needs a separate fire-gate/accuracy iteration.

## Status (2026-07-28): **v33 (POSTS) SUBMITTED -> QUALIFIED -> 👑 CHAMPION.** Posts help on both opponents; stance sweep null

**v33 SUBMITTED on human go-ahead** (`sub_df9f3ac2-7f1d-448f-a08f-63b95eeface0`,
membership `lpm_b2f96151-7cbd-4f25-9369-cf09a319efd0`, `--auto-champion lineage`,
league `league_3243d905-d32d-4ec6-978b-fa94751d4a37`) -> **qualified -> competing ->
👑 CHAMPION** (replaced our own v28 per lineage). Placement took ~2 min (status=pending
with NO membership for the first poll — that is normal async placement, not a failure).

**MONITOR GOTCHA RE-CONFIRMED (3rd time):** `policy_lifecycle.py monitor --watch` printed
`DONE — terminal verdict: competing` while OUR submission was still `status=pending`. It
verdicts off the NEWEST membership, which right after a submit is the PRIOR version's. Always
grep the submission id (`sub_…`) for `membership=lpm_…`, then read THAT membership's block.

**STANDINGS ARE PER-PLAYER, NOT PER-VERSION:** the division leaderboard shows "James Boggs
rank 5 @ 1559.21, 157 rounds" — that is cumulative account history (v28-era), NOT v33's
performance. v33 has 0 competition rounds at submit time; expect the score to move only as
rounds accrue. Field at submit: 1 Andre von Houck 2255.9, 2 daveey 1887.0, 3 Alex Smith 1756.1,
4 Jordan 1730.3 (36 rounds), **5 us 1559.2**, 6 softmaxwell, 7 Michael Smith, 8 Andrew Brower.
NOTE a NEW league exists — **"Ctf Doubles"** (`league_79796d56…`, created 2026-07-28) — we are
NOT in it; do not submit there by accident when re-resolving league ids.

## (measurement detail) Status (2026-07-28): **POSTS MEASURED — posts ON helps on both opponents; stance sweep null. v32/v33/v34 uploaded, NOT submitted**

**A/B RESULT (matched arms, one image env-flipped via `--secret-env`, 10 eps/arm,
ctf 0.7.95, 60/60 episodes, 0 failures):**
- **v32 = posts OFF** (control), **v33 = posts ON stance 0.12** (shipped default),
  **v34 = posts ON stance 0.18** (past the 0.1727 crossover).
- vs **ctf-focusfire:v56**: win 20% -> **40%** (v33, p=0.01), score -0.60 -> -0.20.
- vs **ctf-h050:v1**: win 0% -> **20%** (v33, p=0.00), score -1.00 -> -0.60 — first wins
  ever off the h0xx line.
- v34 (0.18) also beats off but less (30% / 10%). Direct 0.12-vs-0.18: 0.12 ahead on both,
  **p=0.18 / p=0.08 — not significant at n=10.** 0.12 stays default.
- Reports: `scratch/eval_posts_ab/reports/*.html`; xreq ids in
  `scratch/eval_posts_ab/xreq_ids.txt`.

**ACTIVATION (all live, control shows 0):** 1,942 active post-ticks / 181 distinct post
cells / max 525 ticks on one post. threat_source: enemy_track 1125, plan_facing 448,
enemy_pedestal 288, danger_gradient 81 (live evidence beats the static prior ~4:1, and the
plan's `facing` is now load-bearing). claim_source: uncontested 811, visible_teammate 641,
heard_K 490 across six seats — **the K protocol works in real games.**
**Stance term verified mechanically despite the null outcome:** 0.12 -> 0.18 moved PUSH posts
forward +21.5px -> +32.9px mean (65% -> 72% chosen forward of the waypoint), so the honest
reading is "more forward isn't better vs these two", not "the term is inert".

**FIELD MOVED AGAIN (recon this session):** rank 1 is now **alphashot-ghost-red-ca3e95f:v1**
(Andre von Houck), 2 focusfire:v56, 3 **ctf-h050:v1** (h035 is gone), 4 jordan-ctf-candidate:v9,
6 Picasso:v28, 7 swarm:v1. Game is **0.7.95**. Both losses-heavy baselines mean beacon is
currently mid-field — posts close part of the gap but do not make us favourites.

**ALPHASHOT RECON DONE (n=10/arm, 0.7.96):** v32(off) 10% win -> **v33(posts) 20%** (p=0.08,
non-significant but positive) — **no regression vs the field leader.** kills 136 -> 174.
**The gap is the FIGHT, not the ground:** forward sightline reach is IDENTICAL (beacon 92px
mean/84 median vs alphashot 93/84, both 7-9% open >=200px, measured with our own baked field),
but alphashot kills at **222px mean vs our 187px** (59% of our kills inside 200px vs their 44%;
we take 0% beyond 400px vs their 4%) and logs **101 clustered kills vs our 61**. Posts had little
room: max dwell only **71 ticks** (vs 525 vs focusfire) because beacon lives just **407 ticks**
against alphashot. Report: `scratch/recon_alphashot/reports/`.

**NEXT:** (a) **the FIGHT is now the lever** — we kill at 187px while `FIRE_MAX_RANGE_PX`=350
allows much longer, so a range/hold-fire audit plus wounded-target priority and focus fire are the
evidence-ranked candidates; (b) **audit beacon against GameVersion 23** (replays are GV23 =
`cdd567f`: shield BREAKS on depletion, overtimeTicks 500 — our config/docs assume GV21/22);
(c) the stance sweep needs n>=30 or should be parked; (d) posts still untested vs Picasso/swarm/
jordan.

## (prior) Status (2026-07-28): **covered posts implementation in working tree, not uploaded**

Beacon now has an offline-baked `sightlines` field (`32 x 83 x 155`, `uint8`,
4px units, 400px cap) and a `posts.py` decision layer. Behind
`BEACON_POSTS=1`, battle-plan move/hold targets, live H/S/P squad orders, and
the static defender hold fallback become search centres for separated covered
positions with a committed threat direction. `BEACON_POST_FACING` independently
centres a narrower lighthouse sweep on that direction. The `K<seat><cell>`
claim message decays after 120 ticks and sits in arbitration
`C > T > O > G > U > K > E > P`. Traces expose post cell/direction, score
terms, threat and claim source, live settlement ticks, cumulative ticks on
posts, and claim send/hear counts.

The motivating replay baseline was **measured on a 16-direction fan**: pushers
arrived 13-47px apart with only 0-3 sampled rays open beyond 200px. Do not call
that a 32-direction measurement. Future post A/B reporting should compare
forward-reach distance distributions rather than counts of open directions;
distance is invariant to the fan resolution.

Plan milestones under posts advance on arrival at the latched post, not on the
raw waypoint and not after the 96-tick anti-oscillation dwell. The phase timeout
remains unconditional. With posts disabled, the original
`advance()`-before-`current_objective()` behavior is retained exactly.

## Status (2026-07-27, session 8 cont 2): **OBSERVABILITY BUILD-OUT — v28 uploaded (trace-only), belief-overlay viewer shipped**

**Chat is FREE** (verified: 0x81 chat + 0x84 mask are separate packets in the
same frame flush; server folds both into one tick; shouts never touch the mask).

**v28 uploaded (NOT submitted; trace-only, plays identically to v27):** every
trace event seat/team-stamped; NEW events `order` (every squad-command change
with source: leader/heard/decay/convert), `sync`, `heard_chat`, `heard_sound`;
snapshots add order_source/order_age/presence_age/intent_point/nav_path/
item_spawns/heard_events_live/visible_enemies+teammates. Warehouse now ingests
traces from artifact zips (was silently 0 since v18 — only the stderr fallback
was read!) and stamps **eng_tick** (engine-tick alignment per episode+slot via
first-spawn ↔ phase=Playing; raw trace ticks are per-bot frame counters,
offsets 51-108 observed). Cross-bot queries MUST use eng_tick.

**NEW: belief-overlay replay viewer** — `tools/viewer.html` + bundler
`tools/viewer_bundle.py <episode_dir>` (needs episodes fetched WITH artifacts;
expand_replay_json now takes pos_every arg — bundles use 1). Overlays per
selected bot (dropdown, or global): vision polygon (wall-clipped rays), chat
hearing radius, heard chats/sounds, enemy/ally tracks (age-faded), squadmate
presence staleness, item beliefs, danger heatmap, goal+order (goal/source/age),
nav path, state card. All toggleable; tick-by-tick stepping (←/→, shift=24) +
play/scrub. Verified in-browser on a v26 episode. NOTE: overlay resolution =
snapshot cadence — record viewer batches with **BEACON_DIAG_EVERY_TICKS=1**
(default 96 → overlays up to ~4s stale; the belief-age readout shows it).

**v28 SUBMITTED → qualified → 👑 CHAMPION** (sub_4fabc37f…, lpm_fa09ccb7…, one
qualifier round, no crashes). League games now emit full telemetry. Standing:
**rank 5 @ 0.417** (was rank 8 @ 0.06 at v27 entry — convert rounds accruing).
Monitor gotcha: `policy_lifecycle.py monitor` verdicts off the NEWEST membership
— right after a submit that's still the PRIOR version's; pin to the submission id
(/v2/league-submissions → memberships) for the real verdict.

**v29 (squads OFF) A/B vs v28 (matched, 10 eps/arm, game 0.7.8x, FIELD MOVED
AGAIN — h035 now rank 1 @ 0.651, focusfire v56 rank 2, new alphashot:v2 rank 4):**
- vs focusfire v56: **v28 2W/7D/1L → v29 0W/4D/6L (REGRESSED, p<0.001)** —
  the squad layer was load-bearing against focusfire; the static split feeds it.
- vs h035: v28 2W/0D/8L → v29 1W/0D/9L (noise, p=0.08) — squads weren't the
  h035 gap either way; h035 beats both shapes decisively.
- ALSO: h035 now beats v28 too (2W/8L vs the 2W/2D/6L three days ago at v27) —
  either h035 improved in place or 0.7.8x rules shifted the matchup.
**VERDICT: do NOT submit v29 — the rollback loses more than the squad chaos
did.** v28 stays champion. The rollback build stays useful as the clean baseline
arm for squad-layer A/Bs (BEACON_SQUADS env-flips on one image).
NOTE: these arms were recorded at default trace cadence but with the v28+
tracing — 1M trace events in the v28_focusfire warehouse alone; the
decay/backoff + earshot analysis can run on THIS data (no new batch needed).

**NEXT: mine the v29_ab warehouses** — (a) order-source/decay timeline vs
earshot (hang-back hypothesis, now answerable from data on disk), (b) what
changed in the focusfire matchup that squads were absorbing, (c) h035 mid-lane
fight quality. POI map (points_of_interest.json + tools/poi_editor.html) is
seeded and awaiting human curation — it becomes the strategy vocabulary.

## (prior) Status (2026-07-27, session 8 cont): **v27 (=v26 image) SUBMITTED → champion. FIELD SHIFTED: h035 + swarm new; focusfire at v56; game 0.7.81**

**v26 hit the player-binding trap AGAIN** — a leftover `coworld player use` session
(`seedtest-loop1-newcomer` active) bound the v26 upload to the seedtest player
(verified from A/B episode participants: `seedtest-base-veteran`). Fix: `coworld
player unset`, re-upload same image → **beacon:v27**, 1-ep probe confirmed default
player, submitted (sub_092e439f…) → **qualified → competing → 👑 CHAMPION**
(lineage). The old v25 membership shows disqualified substatus=broken — superseded;
v27 is the live entry. RULE HARDENED: `coworld player list` + check the ● active
marker BEFORE every upload, not just before submit.

**FIELD RECON (2026-07-27, beacon:v27 1v1s, 10 eps each, game 0.7.81):**
- **ctf-focusfire:v56** (daveey, rank 1 @ 0.70; was v1): **4W/6D/0L** — we no
  longer lose to it, but it stopped feeding kills (steals 15 vs our 1; kills
  221-174 us): draws are back vs the leader. Their v1→v56 pace = daily iteration.
- **ctf-h035:v1** (Alex Smith, rank 2 @ 0.56; REPLACED h006): **2W/2D/6L — the
  new problem.** Beats us by ATTRITION: out-kills us at mid (122 vs 92 kill
  events), 23 flag steals/10 games (constant pressure that pulls our holds; 3
  captures slip through, ~20 carriers die), losses end tick ~3900-4600 (wipes +
  captures, before the clock). Our own flag pressure: 3 steals in 10 games.
- **swarm:v1** (Michael Smith, rank 3 @ 0.44, NEW): **6W/0D/4L** — decisive
  games both ways (their 25 steals + 3 caps vs our 4+1); high mutual TK (8 vs
  11) suggests a melee-ball style. Winnable but volatile.
- Rest: Picasso v26, co-gas relh v27 / richard v34, autoresearch v41.
  NanosaurusX gone. **The division iterates DAILY — recon before every submit.**

**NEXT LEVERS (evidence-ranked):** (1) **the h035 gap** — mid-lane fight quality
+ carrier-hunting (their steals) + our own flag pressure (3 steals/10 games is
nothing; C-squad push isn't generating steals); (2) keep the convert trigger —
focusfire draws at 21-23 kills suggest CONVERT_ENEMY_LIVES=6 may be too tight
for their v56 (they stopped over-extending); consider 8-10 A/B; (3) swarm TK
noise — our 8 TKs vs their melee ball, check FF gate under crowding.

## (prior) Status (2026-07-24, session 8): **v25 SUBMITTED+competing; v26 convert trigger built+uploaded, A/B in flight**

**v25 submitted on human go-ahead** (sub_652bd0cb…) → qualified → **competing**
(entry rank 8 @ 0.075 — post-restructure standings, expect climb as rounds
accrue). Binding verified from live episode participants (default player).

**v26 (uploaded, NOT submitted): the CONVERT TRIGGER** — session 7's designed
lever, built on the fog-independent team scoreboard (`team score RED k/d`
labels, discovered in the 2026-07-23 rules audit): `enemy_lives_left` = 24 −
enemy deaths; leaders order T (all-in hunt at freshest enemy evidence) when
enemy lives ≤ 6 (`BEACON_CONVERT_ENEMY_LIVES`); stale-order members self-convert
instead of backing off. Traced: `enemy_lives_left`, `convert_events`. 99 tests.
**A/B v26 vs v25 MEASURED (matched, 0.7.76): vs focusfire 5W/5D/0L → 10W/0D/0L
(p<0.001) — every draw converted, zero losses, stacking still fixed. Vs h006
0W/10D both arms, but the trigger FIRES (4/10 eps crossed enemy-lives ≤ 6; v25's
best was 5 lives) — the all-in trades 1:1 with h006 (21-22 kills each) and the
clock ends it. v26 strictly dominates v25.** Reports:
`scratch/eval_v26_ab/ab_{focusfire,h006}.html`. **Next lever: the h006 FIGHT**
(win the traded engagements — accuracy/cover/grenades — or open a capture path;
doctrine is no longer the constraint). v26 uploaded, NOT submitted — submit is
the human's call (v26 > v25 on evidence). League on **0.7.76** (`d78450e`) —
cone 45 / maxTicks 5000 / arena unchanged; team-score labels intact; replay
reader re-pinned d78450e (0.7.70-0.7.76 era; 72fb1b1 kept for the 0.7.69 era).

**Platform gotcha (2026-07-24): fresh xreqs 404 on GET for seconds-to-minutes
after create (indexing lag), then appear as completed. Don't re-fire on a 404 —
wait and re-check (we burned ~6 duplicate xreqs learning this). The artifact
fetcher's --watch crashes on that 404 (retry patch = TODO).**

## (prior) Status (2026-07-23, session 8): **v25 spread built+measured — mechanism works, outcome REGRESSED; needs the finisher. League on 0.7.70**

**v25 (uploaded, NOT submitted): squad spread** — rank-offset shared order points
(0/±70px y, `spread_point`), separation applied to order_* movement, and a
push-apart nudge as the hold state's only movement. Stacking is FIXED: stacked-ticks
67→5.6/appearance (h006), 28.6→5.9 (focusfire). But the matched A/B (10 eps/arm,
same-window, 0.7.70) says **outcome regressed**: focusfire 7W/0D/3L (v24) → 5W/5D/0L
(v25); h006 2W/5D/3L → 0W/10D/0L. Losses → ZERO (spread strictly helps defense);
draws exploded, and under GV21 draw = -1 = loss. Every focusfire draw: beacon ahead
21-23 kills vs ~15, 1-2 kills short of the 24-kill wipe, holders never collapse to
finish. **v25's spread makes the CONVERT TRIGGER mandatory, not optional**: safer
posture + no finisher = permanent stalemate. Reports:
`scratch/eval_v25_ab/ab_{focusfire,h006}.html`; per-opponent matched arms in
`scratch/eval_v25_ab/`. NEW: `ctf-ab` skill (adapter over coworld-ab engine) built
this session — use it for every future A/B.

**League redeployed 0.7.69→0.7.70 overnight** (episode.json coworld_version). v24's
yesterday numbers (0W/9D/1L vs focusfire) vs today's v24 arm (7W/0D/3L) are
incomparable — the game changed. Diff 0.7.70's source vs 72fb1b1 before trusting any
geometry/rules assumption; audit docs pinned to 0.7.69/72fb1b1 (2026-07-23 audit).

## (prior) Status (2026-07-23, session 7 END): **v24 SUBMITTED (qualifying); rank 3 @ 0.55. NEXT: the convert trigger**

**League state at close:** v24 submitted (`sub_c047199b…`, membership in the NEW
Qualifiers(staging) division — the league re-added staging; promotion is async).
v23 (=v22 image) is the currently-competing champion. Standings: rank 3 @ 0.5495
(daveey 0.697, Alex Smith 0.552 — we're 0.003 behind #2). New entrant NanosaurusX
(rank 4, 11 rounds) — unprofiled, recon when they have history.

**RULES CORRECTION (2026-07-23 audit): a timeout draw is NOT scoreless — it's -1
for BOTH sides** (GameVersion 21 `TimeoutReward`; verified in the deployed `72fb1b1`
sim AND empirically — every drawn v24 episode scores all 16 players -1 in
results.json). The session-7 "timeout = scoreless draw, tie costs 0" premise was
wrong; score-wise a draw IS a loss. This *raises* the convert trigger's value: v24's
14 draws in 20 games each paid -1, not 0. Draws still beat losses only in that they
deny the opponent's +1.

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
