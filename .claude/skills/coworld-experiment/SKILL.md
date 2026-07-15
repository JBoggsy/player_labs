---
name: coworld-experiment
description: "Use to test ONE hypothesis about a Coworld player's behaviour rigorously — design an experiment, adversarially criticize it for falsifiability, redesign until it's valid + cheap, run it, and reach a verdict. Triggers: 'test this hypothesis', 'how do we find out if X', 'I think it might be Y — let's check', 'design an experiment for this', 'does this actually test what we think'. Game-agnostic method; the cheap instruments (re-analyse existing data, a designed run, instrumentation) are supplied by each lab. Leans on coworld-ab for a designed run."
---

# Coworld Experiment

Take **one** hypothesis about a player and **find out if it's true** — by designing an experiment that
could actually *falsify* it, attacking that design until it holds, running it, and reading the result.
The discipline this skill exists to enforce: **never run an experiment whose outcome couldn't change
your mind.**

This is the **game-agnostic** method. The *instruments* it reaches for are lab-specific (each lab has
its own way to re-analyse existing data, and its own designed-run + instrumentation paths); this skill
governs how you *design and judge* the test regardless of game. One hypothesis at a time; if you have
several, run this once each.

**Announce:** "Testing one hypothesis. I'll design an experiment, criticize it for falsifiability,
then run the cheapest valid one."

## Input — a falsifiable hypothesis

State it as a **claim with an observable consequence**, not a wish:

> **Mechanism:** *what* is happening and *why* (pinned to a code location if you can).
> **Prediction:** *if this is true, then **X** should be observable; if false, **X** should not.*

"Lower the threshold" is not a hypothesis. *"We abandon a winning line because gate G trips on
condition C regardless of readiness — so we should observe many intervals that reach C but end without
the payoff, far more than a baseline that converts"* is.

## Step 1 — Design the experiment (cheapest kind that can decide it)

Pick the **cheapest** instrument that can actually test the prediction:

1. **Re-analyse existing data** *(default — free, instant)*. A query or replay read over data you
   already have (your lab's event warehouse / results). Most mechanistic claims about positioning,
   timing, following, votes, tasks, chat are already in data you hold.
2. **A designed experience request** *(when existing data can't isolate the variable)*. A new matched
   batch built to vary exactly one thing — via **`coworld-ab`** / `coworld-experience-requests`.
3. **Instrumentation or a code change** *(last — when the signal isn't observable yet)*. Add tracing
   or a probe behaviour, re-run, then re-analyse. Adding tracing is itself a finding about observability.

Write down, concretely: **what you will measure**, **on what data**, and **the decision rule** — the
threshold/comparison that will read as "true" vs "false" — *before* you run it.

## Step 2 — Criticize the experiment (the gate — do this every time)

Attack your own design before spending anything on it. An experiment that fails any of these gets
**redesigned**, not run:

- **Construct validity** — does this measure the *mechanism*, or just a correlate? A proxy can move
  while the goal doesn't. Test the thing that maps to winning.
- **Does the eval config let the effect show?** A masking config hides the very thing you're testing —
  a pinned-role A/B can bury a gap that only appears in **natural roles**. Match the config to the
  question (and decompose by role/group — a team-level metric is confounded).
- **Two differing predictions** — write **what you'd see if TRUE** and **what you'd see if FALSE**.
  *They must be different.* If both worlds produce the same observation, the experiment is worthless.
- **Falsifiability** — is there a concrete result that would make you *abandon* the hypothesis? If no
  outcome could, it's not an experiment.
- **Confounds** — what *else* could produce the "true" signal even if the hypothesis is false? (field
  drift, role mix, opponent identity, small n, an unrelated change). Control or measure each.
- **Power & cost** — enough episodes/events to separate signal from noise? Is there a *cheaper*
  experiment (usually: an existing-data query instead of a new run) that decides the same question?

State the **if-true** and **if-false** predictions explicitly — they are the contract the result is
read against.

## Step 3 — Redesign until it holds

Loop Step 1 ↔ Step 2 until the experiment is **valid** (differing, falsifiable predictions; confounds
controlled) and **cheap** (the least instrument that decides it). Only then run.

## Step 4 — Present the design for go-ahead (always)

Render the design as a clean HTML report with `scripts/experiment_report.py` (pass
`--eyebrow "<Game> · Experiment design"`) — the hypothesis, what's being changed, the **instrument**,
the **if-true vs if-false predictions side by side**, and the decision rule. **Adapt the HTML where
the content needs it** — it's a starting point, not a form. **Look at the rendered page** before
showing it.

Show it to the human and **get explicit go-ahead before running** — especially for an experience
request, which spends a hosted run. Even for a free existing-data query, present the design first: the
point is the human sees *what's being tested and why*, and that the predictions actually differ.

## Step 5 — Run it

Execute the chosen instrument: the existing-data query, the matched experience request
(`coworld-ab`), or the instrumented re-run. For a hosted run, you may iterate autonomously on
tracing/fetching to get the signal; flag the human only if it needs a *code* change to the player.

## Step 6 — Verdict

Read the result against the **pre-committed** predictions (no post-hoc goalpost-moving), and
**re-render the report with the `verdict` filled** (confirmed / refuted / inconclusive + evidence):

- **Confirmed** — the *if-true* prediction held and the *if-false* one didn't. State the evidence and
  the directed change it supports (hand to `coworld-ab` to measure a fix's effect).
- **Refuted** — the *if-false* prediction held. Say so plainly; a killed hypothesis is a real result.
- **Inconclusive** — neither cleanly held (underpowered, confounded, or the predictions weren't as
  distinct as you thought). Say what a *better* experiment would be, and whether it's worth it.

## Discipline

- **Falsifiability is non-negotiable** — no if-true/if-false split, no run.
- **Commit the decision rule before running** — post-hoc thresholds are how you fool yourself.
- **One variable, same tree** — vary exactly one thing; for a designed run, build the baseline by
  git-stashing the candidate change so both arms share everything else (→ `coworld-ab`).
- **The mechanism can be backwards** — design so a result can refute the *direction*, not just
  presence. A refuted (or inverted) hypothesis is a real, valuable result.
- **Prefer existing data** — a query refutes most hunches for free; spend a new run only when you must.
- **Decompose by role/group** — different roles are different policies; a result in one needn't hold
  in the other.

## See also

- **`coworld-hypothesis-miner`** — generates ranked candidate hypotheses from a scored batch when
  nothing specific is suspected yet; its top candidate is a natural input here.
- **`coworld-ab`** — the experiment-as-a-matched-fresh-run; also measures whether a confirmed fix helped.
- **`coworld-experience-requests`** / **`coworld-episode-artifacts`** — fire designed runs / pull them.
- **`crewrift-experiment`** — the crewrift-specific instrument bindings (event warehouse, trace-logs).
