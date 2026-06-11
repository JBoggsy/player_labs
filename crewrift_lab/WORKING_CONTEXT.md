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
- **Large 2-imp confirmation A/B RUNNING** (2×100 eps/arm, pooled): v22 `xreq_8442b2e3`
  + `xreq_bad4a426`; v24 `xreq_97e04fdd` + `xreq_753bdfa1`. Powered (>90%) for the
  observed +0.23 kills/g gap. Analyze crewborg's own kills (`results.json` by
  `policy_version_id`), connect-failure filtered; this decides whether v24's kill gain is real.

## Current objective — RAISE THE IMPOSTER KILL RATE

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
