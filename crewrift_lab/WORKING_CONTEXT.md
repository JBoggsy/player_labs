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

## NEW DIRECTION (2026-06-12, James): tune the suspicion system — learned from replays

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
  **NEXT (in order): (1)** corpus scrape reached ~1,350 eps and continues — rerun
  `expand_corpus → build_dataset → fit --features runtime` at full scale and re-vendor
  the weights JSON (one `cp`, structure unchanged); **(2)** Gate-1 smoke (build_player
  + local run); **(3)** 2-imp `crewrift-ab` v24-vs-v25, target axes = crew win +
  votes-at-crew rate (expect ~0 player-votes as crew except witnessed); **(4)** then
  James's Gate-2 call. Follow-up detectors (next fit): `tasks_completed_watched`
  (−9.0, the big one — task-sprite-transition perception), chat-stance accumulation
  (accusations_made/times_accused), `reported_bodies`/`button_calls`.

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
