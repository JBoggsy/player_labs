# Crewrift working context

**What this is.** The live, high-signal state of *what we're working on right now* in
the Crewrift lab — the minimal set of cross-session facts worth carrying into the next
session. Read it on startup to resume; **update it as you learn** (keep it tight —
prune anything no longer load-bearing). **Clear and reseed it when we pivot to a whole
new direction** (a new objective/hypothesis class), keeping only the new objective.

This is *not* a log or a report archive: reports/replays live with their episodes, and
durable preferences live in [`user_preferences.md`](user_preferences.md). This file is
the one-screen answer to "where are we and why."

> The active policy/version here is also the onboarding signal: a recorded objective
> below means onboarding is done — resume the loop (see [`AGENTS.md`](AGENTS.md)),
> don't restart [`../docs/getting-started.md`](../docs/getting-started.md).

---

## Current objective

Improve **crewborg** (the Python policy under optimization). Newest uploaded version is
**v17** (`policy_version_id bd97b769-57fc-4279-a0b0-fc628e056a2d`); nothing newer has
been shown better, so v17 is the current baseline. Not in a submit-decision yet.

Immediate focus: **find and fix crewborg's biggest score leaks**, starting from a
cheap score-anomaly scan of recent daily-league play (below).

## Working lens — the score-anomaly filter

Flag any episode whose crewborg score is **not** a "clean success" value (see scoring
in [`docs/crewrift-gameplay.md` §6](docs/crewrift-gameplay.md)):

- **Crewmate** clean: **8** (all 8 tasks, lost) or **108** (all tasks, won).
- **Imposter** clean: **20 / 30** (lost, 2–3 kills) or **120 / 130 / 140** (won, 2–4 kills).

Join the score to crewborg by **`policy_version_id`**, never by slot position — the
same league field can contain a *different* player's same-named fork (e.g. a
`crewborg-v23` in another slot).

## Live findings (this direction)

From a scan of the **latest 3 completed daily-league rounds** (262/261/260;
`league_605ff338-0a2e-4e62-aeda-559df9a9198f`) — **312** completed v17 episodes,
**~25% anomalous**, **0 ops/disconnect failures** (crewborg is robust):

1. **Crewmate task-incompletion — 67 eps (dominant).** Score = tasks done (1–7), lost.
   Mixed: "killed/idle/too-slow" (real fault) vs "team lost fast, no chance." Needs a
   killed-vs-idle split from replays/traces before it's actionable.
2. **Vote-timeout abstentions (−10) — highest-confidence bug.** crewborg sometimes
   neither votes nor skips in a meeting; skip is free, so this is never correct. Only
   surfaced where it pushed the score below threshold (e.g. all-8-tasks → **−2**, or a
   win → **98**), so the **true rate is likely higher** than those few.
3. **Imposter 1-kill games — 10 eps.** Under-killing; otherwise a strong imposter
   (≥2 kills in ~87% of imposter games, never 0).

## Open threads / awaiting direction

Proposed next steps (human picks): **(A)** replay-dive the vote-timeout abstentions
(cheapest, highest-confidence — also measure the true rate); **(B)** `crewrift-report`
on round 262 to split the 67 task-incompletion games killed-vs-idle; **(C)** widen the
scan (all of today's completed rounds; include 286/263 once they finish).
Possible tooling follow-up: codify the score-anomaly filter into `crewrift-report`.
