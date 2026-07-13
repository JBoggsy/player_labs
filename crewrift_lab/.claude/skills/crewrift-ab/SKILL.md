---
name: crewrift-ab
description: "Use to decide whether a crewborg change ACTUALLY helped — A/B the candidate against the baseline head-to-head, fresh, right now, against the same field. Triggers: 'did my change help', 'compare v71 vs v70', 'A/B test crewborg', 'is the candidate better', 'did fixing the imposter regress the crew'. This is the crewrift ADAPTER for the game-agnostic coworld-ab skill: crewrift's metrics (crew/imposter, kills/tasks/penalty…) over the shared stats engine. It's also the 'designed run' that crewrift-experiment hands off to."
---

# Crewrift A/B

Decide whether a change **actually helped** — by running the candidate against the baseline
**head-to-head, fresh, right now**. This is the **crewrift adapter** for the game-agnostic
**`coworld-ab`** skill: it supplies crewrift's metrics and grouping; the method (fresh+matched, pin
every seat, respect noise) and the statistics live in `coworld-ab`. **Read `coworld-ab` for the full
method** — this file documents only what's crewrift-specific.

## The crewrift adapter — `scripts/compare.py`

`compare.py` owns the game-specific half and imports the shared engine
(`.claude/skills/coworld-ab/scripts/ab_stats.py`) for all statistics/verdicts. It provides:

- **`Rec` + `load_batch`/`_record`** — read crewrift `results.json`/`episode.json` (both the league
  `policy_results[]` and experience-request `participants[]` slot shapes).
- **`METRICS`** — `win_rate`, `score_mean`, `tasks_mean` (crew), `kills_mean` (imposter),
  `penalty_mean`, `no_vote_rate`, `ops_fail_rate`, `imposter_no_kills_rate`, `crew_low_tasks_rate`,
  `crew_lost_nearly_won_rate`.
- **`by_group`** — crewrift's grouping is **role**: `{crew, imposter}`.

## Workflow

Follow **`coworld-ab`**'s workflow. The crewrift-specific commands:

```bash
S=crewrift_lab/.claude/skills/crewrift-ab/scripts
AB=.claude/skills/coworld-ab/scripts
uv run python "$S/compare.py" /tmp/ab/base /tmp/ab/cand \
  --baseline crewborg:v70 --candidate crewborg:v71 --target kills_mean --json /tmp/ab/diff.json
uv run python "$AB/compare_report.py" /tmp/ab/diff.json --out /tmp/ab/ab.html \
  --eyebrow "Crewrift · A/B comparison" --finding finding.md --verdict "<your one-line synthesis>"
```

`compare.py` leads with the target delta, then a **role-split** table with per-metric
**improved/regressed/noise** verdicts and a **regression scan** (did fixing one role break the
other?). The report renders it as a comparison page — **adapt/extend the visuals** to what the
comparison shows, following [`report-style.md`](../../../docs/report-style.md), and **look at it**
before presenting.

**Qualitative half** (the part numbers can't give): read both batches side by side — expand both with
the version-matched `expand_replay` / the warehouse, and read crewborg's own logs
([`trace-logs.md`](../../../crewrift/crewborg/docs/trace-logs.md)) at the moments that matter. Write a
focused finding (e.g. *"v71 lands the 2nd kill far more — `following_interval` now ends in a kill 7/20
vs 2/20"*) and pass it as `--finding`.

## Crewrift-specific discipline

The universal A/B discipline is in `coworld-ab`. Crewrift specifics:

- **Recompute on CLEAN episodes** — connect/disconnect-timeouts (`ops_fail`) hit the arms
  **asymmetrically**; the `ops_fail_rate` metric surfaces them, drop before comparing.
- **Decompose by role** — crew and imposter are different policies; "crew win" is a confounded team
  metric. The regression scan catches fixing one role by breaking the other.
- **Pin every seat** — the champion pool can seat our own entry under the same display name; an
  unpinned A/B faces different fields (burned the v22-vs-v24 A/B).

## See also

- **`coworld-ab`** — the full game-agnostic method + the shared `ab_stats` engine (read this first).
- **`crewrift-experiment`** — hands a hypothesis here when the test needs a designed run (this is that run).
- **`crewrift-event-warehouse`** — the deep side-by-side for the qualitative half.
- [`report-style.md`](../../../docs/report-style.md) — adapting the comparison HTML.
