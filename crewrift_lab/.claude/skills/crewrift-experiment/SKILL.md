---
name: crewrift-experiment
description: "Use to test ONE hypothesis about crewborg's behaviour rigorously — design an experiment, adversarially criticize it for falsifiability, redesign until it's valid + cheap, run it, and reach a verdict. Triggers: 'test this hypothesis', 'how do we find out if X', 'I think it might be Y — let's check', 'design an experiment for this', 'does this actually test what we think'. This binds the game-agnostic coworld-experiment method to crewrift's instruments: crewrift-event-warehouse (re-analyse existing data), crewrift-ab (a designed run), trace-logs (instrumentation). Standalone on a hunch, or called by crewrift-diagnose."
---

# Crewrift Experiment

Take **one** hypothesis about crewborg and **find out if it's true** — the discipline is: **never run
an experiment whose outcome couldn't change your mind.** This is the **crewrift binding** of the
game-agnostic **`coworld-experiment`** skill: the design/criticize/verdict method lives there; this
file supplies crewrift's concrete instruments and examples. **Read `coworld-experiment` for the full
method.**

It works for a hypothesis from anywhere — a `crewrift-diagnose` hypothesis, or a bare hunch ("I bet we
under-convert kills because we're not close enough when the cooldown lifts"). One at a time.

**Announce:** "Testing one hypothesis. I'll design an experiment, criticize it for falsifiability,
then run the cheapest valid one."

## The falsifiable hypothesis (crewrift example)

State a **claim with an observable consequence**. "Lower the flee threshold" is not a hypothesis.
*"We abandon kills because the flee gate trips on any believed-imposter within 60px regardless of
kill-readiness — so as imposter we should show many proximity intervals to crew that end without a
kill, far more than a baseline that converts"* is.

## Crewrift's instruments (Step 1 of the method — cheapest that can decide it)

1. **Re-analyse existing data** *(default — free)*: a **`crewrift-event-warehouse`** query or replay
   read. Most mechanistic claims about positioning, timing, following, votes, tasks are already in the
   events table — *e.g.* the kill-conversion claim → `player_state` where `kill_cooldown==0`, distance
   to nearest live crew, vs a baseline policy.
2. **A designed experience request** *(when existing data can't isolate the variable)*: a matched batch
   via **`crewrift-ab`** / `coworld-experience-requests`.
3. **Instrumentation** *(last)*: add tracing (`CREWBORG_TRACE_*`, see
   [`trace-logs.md`](../../../crewrift/crewborg/docs/trace-logs.md)) or a probe behaviour, re-run,
   re-analyse.

## Rendering the design (Step 4)

Use the shared renderer with the crewrift eyebrow:

```bash
uv run python .claude/skills/coworld-experiment/scripts/experiment_report.py design.json \
  --out experiment.html --eyebrow "Crewrift · Experiment design"
```

Follow [`report-style.md`](../../../docs/report-style.md); **look at the rendered page** before showing
it, and get explicit go-ahead before running (especially a hosted experience request).

## Crewrift-specific criticism checks

The full falsifiability gate is in `coworld-experiment`. Crewrift specifics that have burned us:

- **Config masking** — a pinned-slot imposter A/B once buried a **30pp imposter gap** that only
  appeared in **natural roles**. Match the config to the question.
- **Proxy vs goal** — kills/g once rose while win% stayed flat; the lever was kill→**win** conversion,
  not kills. Test the thing that maps to winning.
- **Decompose by role** — crew and imposter are different policies; a "crew-win" is a confounded team
  metric, not crewborg's.

## See also

- **`coworld-experiment`** — the full game-agnostic method (design → criticize → verdict). Read first.
- **`crewrift-diagnose`** — generates the hypotheses this tests (and may call this skill).
- **`crewrift-event-warehouse`** — the default experiment instrument (re-analyse existing events).
- **`crewrift-ab`** — the experiment-as-a-matched-fresh-run; also measures whether a confirmed fix helped.
- [`trace-logs.md`](../../../crewrift/crewborg/docs/trace-logs.md) — instrumentation for the "not observable yet" case.
