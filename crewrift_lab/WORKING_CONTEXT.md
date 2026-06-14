# Crewrift working context

**What this is.** The live, high-signal state of *what we're working on right now* in
the Crewrift lab — the minimal set of cross-session facts worth carrying into the next
session. Read it on startup to resume; **update it as you learn** (keep it tight —
prune anything no longer load-bearing). **Clear and reseed it when we pivot to a whole
new direction** (a new objective/hypothesis class), keeping only the new objective.

This is *not* a log or a report archive: reports/replays live with their episodes,
finished work lives in git history / the [version log](crewrift/crewborg/version_log.md),
and durable preferences live in [`user_preferences.md`](user_preferences.md). This file
is the one-screen answer to "where are we and why."

> The active policy/version here is also the onboarding signal: a recorded objective
> below means onboarding is done — resume the loop (see [`AGENTS.md`](AGENTS.md)).

---

## Active league state (2026-06-11)

- **v24** (`b725a6e1`) = self-vote fix (v22) + kill-sooner. **Submitted** `sub_e6969016`
  (provisional, pending the large A/B). **v22** `sub_9a4b4fa9` and **v21** `sub_2c8afd84`
  (still the buggy champion) are now both superseded — retire once v24 places.
- **Large 2-imp A/B (DONE but CONFOUNDED):** `top_n` seated a **different slot-7 partner
  per arm** (v22 got Kyle/Aaron, v24 got a James Boggs crewborg), so the +23% win was a
  partner artifact. Kills (v24 1.93 vs v22 1.73, p=0.005) were more robust — v24 led in
  both the 30-ep and 200-ep batches even as partner-strength flipped — but not clean. (See
  the `top_n`-uncontrolled-roster tentative lesson.)
- **CONTROLLED 2-imp A/B DONE (trustworthy):** fixed roster, partner=slava2 both arms,
  only slot 0 differs (v22 `xreq_1c7f6bdf` / v24 `xreq_57de3453`, 100 eps/arm).
  **Kills +0.21/g (1.37→1.58, +15%), p=0.027 SIGNIFICANT** (robust — same ~+0.2 across all
  3 batches, different partners). **Win +6%, p=0.40 NOT significant** — kill gain doesn't
  reach wins; no ejection cost. **v24 kept** (self-vote fix + real kill bump, strictly
  better than v22). **Kill lever now genuinely improved but kill→win link is weak** →
  next direction should be imposter survival/meetings or crewmate, NOT more kill tuning.
- **v24 league debut (first 7 Competition rounds, 2026-06-11 22:45–23:52, ~480 eps):**
  leaderboard **rank 11/20** (44.15, tight mid-pack cluster 41.8–44.5). Seat-level
  (results.json, all crewborg seats): **crew 25.1% win** (n=406, tasks med 8/8, **0 vote
  timeouts**), **imposter 69.4% win** (n=121) @ **1.79 kills/g** — kill rate now
  field-top tier (top imposters 1.8–2.1) and only 1/121 zero-kill games, **but imposter
  WIN trails the top imposters (83–91%) by ~15–20pp**, and most imposter losses come
  *with* 2 kills (21/34) → the imposter gap is now **conversion** (survival/meetings/
  endgame), not kill volume. Crew gap to the best regulars (slava2 38%, RowDaBoat 35%)
  ≈ 10–13pp, and 77% of seats are crew → **crew is the volume lever**. Round trend:
  48% → ~38% win over the 7 rounds (n=80/round, borderline noise — watch it). Both
  findings confirm the standing call: next direction = imposter conversion or crewmate
  play, NOT more kill tuning. (~10% of league episodes double-seat crewborg — see the
  new tentative lesson before aggregating.)
- **RowDaBoat's edge decoded (2026-06-12, 480-ep stats + 40-replay aggregate):** the
  leader's dominance is ~all CREW-side: crew 39.2% win vs our 25.1% (imposter 74% @1.83
  kills ≈ ours). Mechanism: crew wins are a parity-vs-task race (ghosts keep tasking!),
  and RowDaBoat (a) almost never votes players (0.00 complicity in crew ejections over
  33 crew games; we're 1.04 votes-at-crew/g, 0.48 complicity), (b) burns the emergency
  button every game to reset imposter kill CDs (canned line "just resetting imposter
  cool downs", shared with truecrew), (c) reliably finishes 8/8. Crew ejections ran 14
  in 20 crew losses vs 4 in 20 wins; imposters ejected 2/40 games → our accuse/vote
  feature is likely negative EV as crew. Exemplars in `/tmp/rdb_focus` (77d55243,
  89c510fb, f3b7b1fa = RDB crew beating crewborg-as-imposter; 633ce75a = crewborg
  imposter winning via 2 kills + 2 engineered mis-ejections). Full details in the new
  tentative lesson. **Candidate directions:** crew = vote restraint (skip unless
  near-certain); imposter = engineer mis-ejections (the conversion lever we're missing).
- **XP-request API rebuilt (2026-06-11, metta #15572):** the body is now a single
  `roster` field (one entry per seat: `policy_ref`/`top_n`/`random` selector + `slot`
  pinning or `-1` round-robin); `requester`/`opponents`/`rotate_seats`/`player_selection`
  are gone. Skill docs (`coworld-experience-requests`, `crewrift-ab`) updated to match.

## ACTIVE EXPERIMENT (2026-06-12, James): button-runner interception (imposter), Tier 1

Counter the field's dominant crew defense — pressing the emergency button to **reset
every imposter's kill cooldown** (and call a meeting). Design + Phase-0 study:
`crewrift/crewborg/docs/designs/button-runner-interception.md`. **Phase-0 (DONE, 1,875
games):** reset-calls in **92.5%** of games, **~2 crew calls/g**, **~900-tick rhythm**
(median gap 945 — past our 500 kill CD, so the runner is killable), runners travel
**solo** and funnel through the **bridge↔Hydroponics corridor** (~150–280px east of the
button). Study script: `suspicion_lab/tools/button_runner_study.py`.

**Tier 1 BUILT (flag `CREWBORG_FRONT_BIAS`):** new `strategy/button_intercept.py`
(`button_approach_points()` from substrate anchor→button polylines, band 140–300px) +
`SearchMode._next_search_point` prepends those corridor points during the pre-kill
Search window. Bias only (visible victim still wins via `_target`). 364 tests, ruff
clean, **Gate-1 PASS** (flag-on search path ran in-image, 0 tracebacks). Code uncommitted
on `main` (commit after the A/B verdict + doc audit).

**A/B DONE — Tier 1 REJECTED (regression):** baseline **v26** (flag off,
`xreq_fa91574b…`) vs candidate **v27** (same image +`--secret-env CREWBORG_FRONT_BIAS=1`,
`xreq_c8abf3cb…`), controlled 2-imp 100 eps/arm (crewborg imposter@0, slava2 partner@7,
fixed top crew@1–6, game v0.1.54). **kills 1.27→0.91/g (−28%, p=0.000, d=−0.58), no-kill
games 7%→23%, 2+kill games 31→13.** Win/score noise. The flag worked; the standing
positional bias is the wrong mechanism — camping the bridge corridor sacrifices
occupancy-driven straggler hunting and parks us in a witness-dense area (kills fail
`unwitnessed`). Artifacts `/tmp/ab_front/{base,cand}`. (NB v26/v27 lacked v25's
trace/metrics env — slot-0 logs empty — so mechanism is from kill distributions, not traces.)

**FOLLOW-UP DONE (James): isolation-off — NO EFFECT, REJECTED.** Traced 2×2, 100 eps/arm
(v28 control `xreq_5eff20a6…`, v29 no-iso `xreq_584b8086…`, v30 no-iso+front
`xreq_291ad7b1…`; artifacts `/tmp/ab_front/{v28,v29,v30}`). **Dropping the witness gate is
a no-op on kills: 1.27→1.24/g (p=0.80)**, score/win noise, ejection 7%→9%. **Trace
mechanism:** Hunt spends ~96% of ticks (every arm, incl. iso-off) **closing distance to a
victim, not waiting out witnesses** — the gate is rarely what blocks a kill; first-kill
tick unchanged (~4500). Front-bias trace-confirmed active (v30 search 302px vs ~400px) yet
still regresses (1.27→1.07). v28 control replicated v26 (1.27 exactly) → clean control,
zero roster drift. **3rd independent confirmation (after BE_DUMB v23, kill-sooner v24) that
imposter kills are at a structural ceiling (~1.27/g, cooldown-bound).**

**STANDING CALL: the imposter-kill lever is EXHAUSTED — stop tuning it.** Remaining levers
= crew play / conversion (vote restraint, task-race, survival), per the prior suspicion
direction. v25 remains champion; none of v26–v30 submitted (all experimental). Code: both
flags (`CREWBORG_FRONT_BIAS`, `CREWBORG_NO_ISOLATION`) gated off by default + the Phase-0
study + design doc — disposition (commit gated-off à la BE_DUMB vs revert) pending James.

**CAVEAT on the above A/Bs (James, 2026-06-13): all used a PINNED top-7-champion roster** —
the division's *strongest* crew, which plausibly caps imposter kills. We had NOT tested vs
a representative field. **RANDOM-FIELD three-way RUNNING (2026-06-13):** v25/v28/v29 each
@slot0 (attribute by slot), **7 `random:true` active champions, NATURAL roles**, 4 reps ×
100 eps/subject = **1,200 eps** (random resolves once-per-request, so multiple reps =
multiple field draws — see api.md). xreq ids in `/tmp/rand_field/xreqs.tsv`; bodies
`/tmp/rand_field/{v25,v28,v29}_req.json`. Measures (a) v25↔v28 parity (gated code inert?),
(b) v28↔v29 iso-off effect vs a real field (not just strong crew), (c) crewborg's natural
crew+imposter performance in the wild (~77% crew seats). Artifacts → `/tmp/rand_field/`.

**RANDOM-FIELD DONE (2026-06-13, 1,200 eps, 0 fail; timeout-filtered).** Two findings:
1. **Cross-subject three-way was CONFOUNDED** — `random:true` resolves once-per-request, so
   v25/v28/v29 drew *different* opponent lineups (v25 SAME brain as v28 yet read 1.07 vs 1.47
   imp kills — impossible for identical policies). 4 reps didn't average it out. Can't read
   the iso-off delta from this. (For A/B deltas, pin the roster; random is for 1-subject field reads.)
2. **THE REAL PAYOFF — kills are OPPONENT-RELATIVE, not structurally ceilinged** (pooled all
   1,200, field-mix-invariant): imposter kills/g vs **strong(≥55) 1.12 / mid 1.61 / weak(<50)
   1.90**, corr(opp_strength,kills) = **−0.35**. The "~1.27 ceiling" from all prior A/Bs was an
   ARTIFACT of always pinning the top-7 (strongest crew). **Kill levers may still pay vs the
   non-top field (most of it)** → the "imposter lever exhausted" call was premature; it's
   exhausted *vs elite crew*, open vs the rest. James's random-field instinct was right.
   Natural-role field read (for reference): crewborg crew win ~35-45%, tasks 6-7/8, ~18-22% of
   seats imposter. v25 still champion; v26-v30 inert/experimental.

**WEAK-CREW A/B DONE (2026-06-13) — iso-off RESCUED, "exhausted" call REVERSED.** Pinned 2-imp,
v28 control vs v29 no-iso, crew = ranks 11-16 (mean ~47), 100 eps/arm, traced (v28 `xreq_dbb61f51`,
v29 `xreq_2568cea0`; artifacts `/tmp/ab_weak/`). **iso-off WINS vs weak crew: kills 1.69→1.92
(p=0.016), imp win 59%→73% (p=0.05), score 75.7→92.4, ejected 14%→3%.** (Opposite of the top-7
A/B where it was a no-op, 1.27→1.24.) Trace mechanism: more kill attempts (1.65→1.89) — the witness
gate WAS blocking strikes vs beatable crew; ejections DROP because faster kills hit parity before a
meeting (3-kill games 6→15, game ~130t shorter). **`CREWBORG_NO_ISOLATION` profile = neutral vs
elite, win vs the weaker majority, never-worse observed → plausible SHIP candidate.** Front-bias
stays rejected (regressed both regimes).

**NATURAL-FIELD A/B DONE (2026-06-13, pre-ship blended-EV check).** Pinned representative
opponent lineup (ranks ~1/3/5/8/12/14/17, SAME both arms), NATURAL roles, v28 vs v29, 100
eps/arm (v28 `xreq_833d6b23`, v29 `xreq_5ec382b4`; artifacts `/tmp/ab_nat/`). Results:
**(a) NO crew-side regression** — crew win 33%→37%, tasks 7.6→7.8, score 41→44 (all noise; flag
is imposter-only, confirmed). **(b) imposter kills 1.20→1.44 directionally consistent (d=+0.38)
but p=0.23 (noise) — UNDERPOWERED:** natural roles gave only 25/18 imposter games per arm
(~22% of seats). **(c) blended score FLAT (54.7→54.0)** — the imposter kill gain is real but
imposters are too rare a seat to move the leaderboard average much. Design lesson: natural roles
can't both confirm a kill effect (too few imposter games) AND measure blended EV; the weak-crew
win came from PINNING imposter (~97 imposter games → significance).

**STATE OF THE no-iso EVIDENCE:** vs weak crew pinned-imposter = clear win (kills +0.23 p=0.016,
win +14pp p=0.05, ejected 14%→3%); vs top-7 = no-op; natural blended = no crew harm + directional
imposter gain but the blended-average lift is small (imposters ~22% of seats). **DECISION PENDING
(James):** options — (1) ship v29 anyway (asymmetric never-worse, helps imposter games), (2) a
larger PINNED-imposter natural-opponent batch (~300 eps) to power the blended imposter estimate,
or (3) bank it and pivot to crew (the 78%-of-seats volume lever). Code uncommitted on `main`.

## PRIOR DIRECTION (2026-06-12, James): tune the suspicion system — learned from replays

James's calls: (1) evidence **instances** sum (not per-type max), (2) add
**exculpatory** evidence, (3) the main thing: build the data-science pipeline —
scrape all games, expand replays, fit evidence weights from ground truth, and adopt
any evidence type that earns weight. Design doc written:
`crewrift/crewborg/docs/designs/suspicion-learning.md` (scrape → expand → per-observer
dataset → logistic-regression fit → weights.json into the agent). Key enabler
verified: the upgraded expander (coworld-crewrift `42fed21`, PR #57) emits JSONL with
ground-truth roles, true kill attribution, player states, AND **exact per-(observer,
target) rendered-view visibility intervals** — so "did the player see it" is computed,
not modelled. ⚠️ Don't land instance-summing alone with current hand weights — it
raises posteriors and worsens mis-votes; land with fitted weights (design §1).
- **PIPELINE BUILT + FIRST MODEL FIT (2026-06-12):** `crewrift_lab/suspicion_lab/`
  (scrape_corpus → expand_corpus → build_dataset → fit → eval; see its README).
  Interim fit, 341 games / 35k rows: **full model CV AUC 0.811** (calibrated);
  **runtime-subset (existing event-log features only) AUC 0.739**; decision sim at
  P≥0.9 → 88% of votes hit imposters (live hand model: 42%), net +8.3/100 over
  always-skip. Fitted facts: `tasks_completed_watched` ≈ perfect exculpation (−9.0;
  needs a NEW runtime perception detector — top integration priority);
  `follow_death` strongest graded cue; `accusations_made` +1.1 (incriminating);
  `tailing` ~10× weaker than the hand LR 6.5. Weights:
  `suspicion_lab/models/v1-runtime/suspicion_weights.json`.
- **RUNTIME INTEGRATION DONE (2026-06-12, uncommitted→committed; NOT yet built/
  uploaded):** `suspicion.py` now loads `data/suspicion_weights.json` (vendored,
  v1-runtime fit) and scores with the FITTED model: instance-summed features with
  per-context dedup, exculpatory negative weights, exposure feature
  (`PlayerRecord.seen_ticks`, incremented in event_log), offline-sample unit contract
  (duration/24), witnessed kill/vent kept as a definitional floor. **Crewmate vote:
  P≥0.9 only, NO clear-leader rule** (held-out sim: ~100% imposter precision);
  **imposter deflection keeps the legacy clear-leader logic** (mis-ejections are its
  goal). Legacy hand model = fallback (`CREWBORG_SUSPICION_WEIGHTS=0`). 343 tests
  pass (39 legacy-pinned + 9 new fitted-path), ruff clean; Dockerfile already COPYs
  the data/ package. suspicion.md updated + provenance row added.
- **v2: SOCIAL DETECTORS + FULL-CORPUS REFIT DONE (2026-06-12, James's "get the
  full feature set into the player"):** new `strategy/social_evidence.py` in the
  fast loop (after event_log, before suspicion) maintains cumulative PlayerRecord
  counters: **watched task completions** (global `crew_tasks_remaining` HUD counter
  decrements by exactly 1 while exactly ONE visible living player ends a ≥56-tick
  task dwell — fake Pretend holds never decrement, so they can't trigger it), **chat
  stances** (offline-mirrored accuse/defend regex over `chat_log`, deduped by
  (tick,speaker,text) so per-meeting clears don't lose counts), and **attributed
  votes** (VoteDot carries voter+target slots! staged during Voting, committed once
  at meeting end: cast/skip/against-me/agreed-with-me). Only
  `button_calls_made`/`reported_bodies` are not yet wired (worth ~0.011 AUC) —
  CORRECTION (James, 2026-06-12): they ARE observable; the game's MeetingCall
  interstitial (4b9297d, deployed) shows the caller's icon + "<caller>
  pressed/reported" in the player view; crewborg's perception predates it and
  doesn't parse it yet. Next detector: parse the interstitial -> caller counters
  -> refit with button/reported -> full 0.812 ceiling. **Full corpus: 2,684 eps scraped,
  1,875 expanded, 196k rows. v2-runtime AUC 0.801 vs full-model ceiling 0.812**
  (v1 was 0.704); decision sim @ P≥0.9: 94% imposter precision, net +17.3/100.
  Weights re-vendored (`data/suspicion_weights.json`, intercept +0.392 — note an
  unseen player's baseline P≈0.6, behaviorally contained: vote needs 0.9, Accuse
  needs an active tail). 353 tests pass (10 new social-evidence), ruff clean.
  **SHIPPED (2026-06-12): v25 = the fitted model + v3 weights + interstitial caller
  parse.** Gate-1 PASS (weights verified in-image, 0 log errors). **Submitted + placed**
  (`sub_07dae14f`, `lpm_c04b55cc`) on James's explicit go-ahead. **A/B vs v24 (pinned
  roster, 40 eps × 2 configs): crew win 22%→35% (p=0.22), votes-at-crew 0.88→0.05/g,
  OWN ejections 52%→2%** (the evolved field — sussybuster-aaln, truecrew v20/21 — was
  voting accuse-heavy v24 out!), team crew-ejections 30→6; imposter scan clean (kills
  up p=0.01, win noise, ejections 11%→7%). v25 kept. **NATURAL EVAL DONE (200 eps, xreq_25c447f9 fixed-top-7 + xreq_911e10e1
  random-pool; random roles, all seats rotating):** **crew win 43.8%** (n=146, pv-id
  attributed) vs v24's 25.1% debut — above even RowDaBoat's 39.2% benchmark; imposter
  68.5% @1.43 k/g (held). Vote mechanism in the wild: votes-at-crew 0.01/g (batch A)
  / 0.23 (batch B) vs v24's 0.88; own ejections 2–3%; **19 imposter ejections in
  batch A's 100 games** (field baseline ≈5/100) — restrained votes actually convert
  to ejections now. Tasks faster (done-8 median ~3850 vs ~5300). v25 IS champion
  already (the random pool seated it as its own teammate — double-seats in batch B).
  Field shift: truecrew v20/v21 (Andre) now top this pool (54–60% win); RowDaBoat
  mid-pack. **NIGHTLY CHAMPION LOOP INSTALLED (2026-06-12, James):** user crontab
  `30 0 * * *` → `suspicion_lab/tools/nightly_refit.sh` (scrape → refit → gates
  [AUC≥0.70, ≥500 games, test suite, Gate-1] → vendor → build → upload → SUBMIT,
  auto, per standing instruction; logs in suspicion_lab/logs/). Caveats: skips if
  the machine sleeps through 00:30; aborts safely if softmax auth expires or
  Docker is down. **Remaining open items:** (a) retire stale memberships
  (v24/v22/v21 — v25 is placed+champion); (b) offline/runtime feature parity test;
  (c) the nightly fit uses the full corpus — consider a recency window if the
  field's drift outpaces accumulation.

## Prior objective — RAISE THE IMPOSTER KILL RATE (done: v24 shipped; kill→win link weak)

crewborg is a respectable mid-pack player (clean 50-game eval, 2026-06-11) but its
weakest dimension is **imposter kills: ~1.7/game vs the top imposters' ~2.0**, and in
this game that gap *is* the win gap (64% vs 80% imp win). With 2 imposters the win
ceiling is ~2 kills each (crew loses at parity), so the goal is concretely **convert
1-kill games into 2-kill games** — i.e. get *more kill attempts*, not better aim.

Active policy: **v22** (`40e29a8c`) — the self-vote bugfix, **submitted** to the
Competition league 2026-06-11 (`sub_9a4b4fa9`), currently **qualifying** in Qualifiers
(`lpm_dd5c96db`). **v21** (`52fc8572`) is still the live **champion** and carries the
self-vote bug — **retire it once v22 qualifies into Competition**
(`coworld retire-membership lpm_3e95ac16`). Don't retire before v22 places (the older
`competing` versions also have the bug).

## The diagnosis that motivates this (5 expanded replays + traces, 2026-06-11)

crewborg's imposter problem is **passivity, not skill**:
- **Kill conversion is ~100%** — `kill_attempted == kills` in every game. When it tries,
  it succeeds. The bottleneck is purely **too few attempts** (1–3/game vs a ~4–5 ceiling).
- **Mode-time is dominated by blending:** **54–74% `pretend`** (fake tasks), only
  **0.1–2.9% `hunt`**, with big idle gaps (764–983 ticks) between kills — far past the
  **500-tick kill cooldown**, so cooldown windows are wasted.
- **It never gets caught:** survived to the end / **never ejected** in all 5 games. It's
  spending the match buying a safety margin it isn't using → lots of unused aggression.
- **Root cause in code:** `SEARCH_LEAD_TICKS = 100` (opportunity.py) makes it position
  only in the *last fifth* of the cooldown, and Hunt requires an **already-visible**
  victim (`has_visible_victim`, no pre-positioning). So when the kill comes ready it's
  usually mid-pretend somewhere random and has to start hunting cold.

## BE_DUMB ceiling experiment — DONE, rejected (2026-06-11)

v23 (`2ba6a477`, v22 image + `CREWBORG_BE_DUMB=1`) vs v22, both imposter-pinned (1-imp)
vs top-7, 30 eps, connect-failure filtered:
- **v22 baseline:** 2.25 kills/g, **14% ejected**. **v23 BE_DUMB:** 2.47 kills/g (+10%),
  **40% ejected** (~3×). Mode shift confirmed (pretend 68%→0%, search 24%→97%, hunt
  1.9%→3.2%) — but **hunt barely moved despite 97% search**: the cap is the 500-tick
  cooldown + victim isolation, NOT blending time. **Pure aggression is a bad trade.**
- **Reframe (James):** crewborg's lower league kills (1.73 in 2-imp) vs solo (2.25) is
  **not** the partner stealing victims — a sloppy partner kills in obvious spots, the body
  is reported fast, and a **report resets every imposter's kill cooldown**, so we lose our
  CD window. Only lever on our side: **get our kill in ASAP**. (Parked otherwise.)
- v22 baseline data lives at `/tmp/ab_v22` (`xreq_9274d50f`); reuse as the A/B baseline.

## Current experiment — v24 "kill sooner", 2-IMPOSTER A/B (RUNNING)

Three changes (committed `2199e4c`): `SEARCH_LEAD_TICKS` 100→**250**; Pretend `DO_TASK`
holds a fake task **only while a crewmate is visible** (`has_visible_victim`); the hold
**stops** the instant the last crewmate leaves view (re-dispatch toward crew/victims).
v24 = `b725a6e1` (v22 env, NO BE_DUMB).

- **1-imp A/B (DONE, inconclusive-by-design):** v22 2.27 kills / v24 2.00, within noise
  (t≈1.3); mode shift confirmed (pretend 69%→48%, search 24%→45%, hunt 1%→3%). **But
  1-imp has no partner**, so it can't test the partner-report-CD-reset mechanism the
  changes target — and James's standing rule is now **always 2-imposter evals, never
  1-imp** (see [user_preferences](user_preferences.md)).
- **2-imp A/B (RUNNING):** crewborg slot 0 = imposter + slot 7 = partner imposter, 6
  crew, vs top-7, 30 eps each. baseline v22 `xreq_dff96e86`, v24 `xreq_a62759e9`. Measure
  crewborg's **own** kills (`results.json` by `policy_version_id`). **Ejection detection:
  the 1-imp "GameOver right after a vote" trick fails here** (game continues while the
  other imposter lives) — detect crewborg ejection from its trace role→dead or the replay.
- **Decision:** if v24 > v22 on crewborg's kills in 2-imp → the kill-sooner changes earn
  their place; if not → kill lever exhausted (2× confirmed search-time isn't it), pivot.
  Don't ship v24 without a 2-imp win.

## Remaining kill levers (if v24 helps but not enough)

- **Stalk a committed victim:** have Search lock onto `select_victim()` and shadow it at
  kill-range during cooldown (sharper than "walk hotspots until a victim is visible").
- **Partner-report CD reset** (parked): nothing we can do from our side beyond killing ASAP.

## Working lens — the score-anomaly filter

Scoring (`docs/crewrift-gameplay.md` §6): win +100 · task +1 (×8) · kill +10 ·
vote-timeout −10. Imposter "clean success": **20/30** (lost, 2–3 kills) /
**120/130/140** (won). Join scores to crewborg by `policy_version_id`, never by slot.
**Always filter connect/disconnect-timeout episodes (−100) before concluding** — they
corrupt win rates platform-wide (see tentative lessons).

## Imposter code map (for this work)

- `strategy/rule_based.py` `_select_imposter` — the gate: evade → report_body →
  (`self_kill_ready` & `has_visible_victim`)→hunt → (`ticks_until_kill_ready ≤
  SEARCH_LEAD_TICKS`)→search → else **pretend**. `CREWBORG_BE_DUMB` shortcut at the top.
- `strategy/opportunity.py` — `SEARCH_LEAD_TICKS`, `DEFAULT_KILL_COOLDOWN_TICKS=500`,
  `select_victim` (most-isolated reachable visible straggler), `has_visible_victim`,
  `unwitnessed`/`kill_urgency_ticks` (witness bar relaxes with urgency), `TEAMMATE_CLAIM_RADIUS`.
- `modes/hunt.py` / `modes/search.py` / `modes/pretend.py` / `modes/evade.py` — the modes.
- **Trace to verify:** per-tick `domain.decision_snapshot` (mode/intent) + `domain.kill_attempted`
  in the artifact `telemetry.jsonl`; expand replays with `tools/bin/expand_replay`
  (the `3ea899eb` build matches game 0.1.51) for objective kill ticks — but **trust
  results.json for kill COUNTS** (replay attribution is unreliable at simultaneous-body ticks).
