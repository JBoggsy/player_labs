---
name: crewrift-diagnose
description: "Use to turn a Crewrift report's signals into evidence-grounded, MECHANISTIC improvement hypotheses — by investigating the replays/logs/code for *why* a behavior happens (or fails to), then presenting candidate directions to the human. Triggers: 'why is crewborg weak at X', 'what should we try / where should we go next', 'form hypotheses', 'diagnose this weakness', 'what's the mechanism behind Y', 'turn this report into directions', 'we got lucky in some games — can we engineer that'. Optional AUGMENTATION of the Report step — it adds candidate hypotheses alongside the report's replay-pointers; it does not replace the human's direction call. Pairs with crewrift-report (signals in) and crewrift-ab (to test a hypothesis)."
---

# Crewrift Diagnose

Turn the **interesting signals** in a report into a small set of **mechanistic
hypotheses for improvement** — each one a claim about *what* the policy is doing (or
not doing) and *why*, grounded in evidence from the replays, logs, and code, with a
concrete change and a predicted, measurable effect.

This is the **direction** step's augmentation. The standard human-in-the-loop flow is:
`crewrift-report` surfaces weaknesses + points the human at interesting replays, and
the human picks where to go. This skill **adds** to that — it offers the human
*"here's what I've been thinking"*: candidate hypotheses to consider **alongside** the
replays. It is **optional**, and it **does not assert** what the human should do —
present hypotheses as options, the human still chooses (or chooses none).

**Output:** you **present the hypotheses in the session chat** (like the report itself
— there's no file). This is a multi-turn, agentic investigation, not a script run.

## Premise

You have a `crewrift-report` (run it first if not — it's the signal source: the
role-split distribution + the flagged "interesting episodes"). Diagnose explains those
signals; it doesn't re-derive them.

## What a good hypothesis is (read this first)

The lessons from prior player-improvement work are blunt about what separates
hypotheses that produced real gains from wasted effort:

- **A mechanism, not a tweak.** State the causal chain: *"X is happening because Y in
  the code, which causes Z."* "Lower the threshold" is not a hypothesis; *"it flees too
  early because the flee gate trips on any believed-imposter within 60px regardless of
  kill-readiness, so it abandons tasks"* is.
- **Grounded in evidence, not plausibility.** "This should obviously help" is a reason
  to *test*, not to assert — historically about half of "obviously good" ideas
  regressed. Every hypothesis must cite what you actually saw (episodes, log lines,
  code location).
- **Pinned to a code location.** If you can't point at the mode/strategy/threshold that
  drives the behavior, it's a vibe, not a hypothesis — keep investigating.
- **With a predicted, observable effect.** Name what should move and by roughly how
  much, per role — this is what `crewrift-ab` will later test (it becomes the target
  axis). A hypothesis you can't measure can't be confirmed.

## The process (multi-turn)

### 1. Pick the signals worth explaining
From the report: the flagged categories and interesting episodes. **Include the
positive outliers, not just the failures** — "we did unusually well / got lucky in
these games" is a hypothesis source as much as "we lost badly here." The three shapes
a hypothesis takes:
- **(a) Stop a bad behavior** — something fires that shouldn't (e.g. votes a real
  crewmate, kills in front of witnesses). *Why does it fire? → gate/remove it.*
- **(b) Enable an absent good one** — something that should happen doesn't (e.g. never
  reports a body it walked past). *Why is it absent/mis-gated? → enable it.*
- **(c) Amplify a working one** — something good happens; make it happen more. Includes
  **engineering the luck**: take the positive-variance episodes, find the *mechanism*
  that made them go well, and make it fire reliably rather than by chance.

### 2. Find the mechanism — investigate, don't guess
This is the core, and it's where the value is. For each signal, work from the
**outcome** down to the **code**:

1. **Locate the moments.** Use the report's flagged episodes; from `crewrift-ab`-style
   per-episode/role decomposition, find *which* episodes show the pattern (the variance
   carries the mechanism — what do the bad ones, or the lucky ones, have in common?).
2. **Read the objective timeline** (`expand_replay` — see
   [`crewrift-replays.md`](../../../docs/crewrift-replays.md)) at those ticks: what
   actually happened (kills/bodies/votes, true roles)?
3. **Read the policy's own logs** at the same ticks — what did it *perceive, believe,
   and decide*? (crewborg: its per-tick traces,
   [`crewborg/docs/trace-logs.md`](../../../crewrift/crewborg/docs/trace-logs.md);
   Nim players: plain-text stderr.) The gap between "what was true" (timeline) and
   "what it believed/chose" (logs) is usually where the mechanism lives.
4. **Trace it into the code.** Find the mode / strategy / threshold that produced that
   decision (crewborg: [`crewborg/design.md`](../../../crewrift/crewborg/design.md) and
   its `AGENTS.md` "where things are" table). Name the exact place — that's your
   mechanism.

**Tracing-escalation branch (act autonomously — no human gate):** if the logs are too
thin to find the mechanism, get more tracing and re-run. If it's a config knob
(crewborg: `CREWBORG_TRACE_GROUPS` / `CREWBORG_TRACE_INCLUDE` — see trace-logs.md), just
**turn it up → re-run the experience request → re-pull (coworld-episode-artifacts) →
re-report → resume the investigation.** This is mechanical; don't stop to ask. (Only
flag the human if getting the needed signal requires a *code* change to the player's
tracing — that's itself a finding.)

### 3. Form the hypotheses
Produce **one or two at minimum, no fixed cap** — and they need **not** be competing;
a spread of independent improvement mechanisms is good. Each hypothesis states:
- **the observation** (the signal, with evidence: episodes / log lines),
- **the mechanism** (what + why, pinned to a code location),
- **the directed change** (what to alter — one component, so it stays attributable),
- **the predicted effect** (what should move, per role — the future `crewrift-ab` target),
- **confidence + what would falsify it.**

### 4. Present to the human — as options, not directives
In the chat, alongside the report's replay-pointers, offer the hypotheses: *"From the
report, here are N mechanistic hypotheses — candidates for your consideration, not a
recommendation,"* each with its evidence → mechanism → change → predicted effect. Then
hand the decision back: where does the human want to go? (They may pick one, combine,
or set a different direction entirely.)

## Discipline (the do / don'ts, from prior improvement work)
- **Mechanism, not tweak; code location, not vibe; predicted effect, not hand-waving.**
- **Plausibility ≠ evidence** — "obviously helps" gets tested, never asserted.
- **Variance/outliers carry the mechanism** — decompose; the lucky wins and the worst
  losses are both hypothesis sources.
- **Don't optimize the obvious intermediate metric** — check it actually maps to
  score/win; counterintuitive correlations (e.g. dying *more* while scoring *more*) are
  signal, not noise.
- **Don't thrash** — investigate one signal to a grounded mechanism before spawning the
  next hypothesis; generating hypotheses faster than you ground them is the classic
  failure.
- **Prefer an unexplored mechanism over a marginal tweak** to something already
  well-tuned.
- **Present, don't assert; don't auto-implement.** The only thing you do autonomously
  is the tracing-escalation re-run (§2).

## See also
- [`crewrift-report`](../crewrift-report/SKILL.md) — the signals this consumes.
- [`crewrift-ab`](../crewrift-ab/SKILL.md) — test a hypothesis's predicted effect (its
  predicted effect → the A/B target axis).
- [`crewrift-replays.md`](../../../docs/crewrift-replays.md) + the policy's log docs —
  the investigation surfaces.
- [`crewrift-gameplay.md`](../../../docs/crewrift-gameplay.md) — to read events as gameplay.
- `best_practices.md` (lab root) — the cross-cutting checklist these disciplines distill.
</content>
