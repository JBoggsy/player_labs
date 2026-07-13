---
name: coworld-ab
description: "Use to decide whether a change to a Coworld player ACTUALLY helped — A/B the candidate against the baseline head-to-head, fresh, right now, against the same field. Triggers: 'did my change help', 'compare vN vs vM', 'A/B test the player', 'is the candidate better', 'did fixing X regress Y'. Runs two MATCHED fresh experience requests, diffs group-split metrics with significance (a per-lab compare.py adapter over the shared ab_stats engine), renders a comparison report, and guides a qualitative side-by-side. Game-agnostic; each lab supplies its own metric adapter."
---

# Coworld A/B

Decide whether a change **actually helped** — by running the candidate against the baseline
**head-to-head, fresh, right now**. Two halves: a **quantitative** engine (`ab_stats.py` — group-split
metric deltas with significance) driven by a **per-lab adapter** (`compare.py` — your game's metrics),
and a **qualitative** side-by-side **you** run (read both batches' replays/logs for the *why*). The
question is targeted: *did the thing I tried to improve move, and did anything regress?*

This is the **game-agnostic** skill. The *method* and the *statistics* live here; each lab supplies a
small **adapter** for its own metrics (see **What your lab supplies**). Crewrift's `crewrift-ab` is the
reference adapter.

## The one principle that makes it valid: fresh + matched

The league field **drifts** — others change their agents constantly. So you **cannot** compare the
candidate's fresh games against the baseline's stale history; the difference is confounded by
everyone else's changes.

> **Run both versions in the same window, against the same roster/roles/count.** Two matched
> experience requests fired together → field drift hits both equally → the delta is attributable to
> *your* change. The question is "is the candidate better **now**," not "vs last week's field."

## Workflow

1. **Frame** the **baseline** + **candidate** versions and the **target axis** — the one metric the
   change was meant to move. Fix your qualitative lens too (an opponent you lose to, a fault you're chasing).

2. **Fire two MATCHED, fresh experience requests** (`coworld-experience-requests`), byte-identical
   except the subject version:
   - **Pin every seat with an explicit `policy_ref: name:vN`** — **never `top_n`/`random` in an A/B**:
     the champion pool drifts between requests and can seat your own entry, so the arms would face
     different fields.
   - Same target, same pinned roster, same roles (**natural roles unless you're testing a specific
     role** — a pinned-role config can *mask* a gap), same count, same window (fire back-to-back).
   - **Testing an env-flag change?** the baseline must carry **all** of the candidate's runtime env
     *minus the one flag* — isolate exactly the change, not the whole env.

3. **Pull both batches** (`coworld-episode-artifacts`), one dir per side — **streaming by default**:
   fire one `fetch_artifacts.py --xreq … --watch` per arm in the background right after step 2's
   creates, so both downloads overlap the still-running episodes.

4. **Quantitative diff + report** — run *your lab's* `compare.py` adapter (it calls the shared engine),
   then the shared renderer:
   ```bash
   AB=.claude/skills/coworld-ab/scripts
   uv run python <your-lab>/.claude/skills/<lab>-ab/scripts/compare.py /tmp/ab/base /tmp/ab/cand \
     --baseline player:vM --candidate player:vN --target <metric> --json /tmp/ab/diff.json
   uv run python "$AB/compare_report.py" /tmp/ab/diff.json --out /tmp/ab/ab.html \
     --eyebrow "<Game> · A/B comparison" --finding finding.md --verdict "<one-line synthesis>"
   ```
   The adapter leads with the target delta, then a **group-split** table of all metrics, each marked
   **improved / regressed / noise** with a p-value, plus a **regression scan**. It's deliberately
   conservative — a borderline move reads as `noise`. The report renders this as a comparison page;
   it's a **starting point — adapt/extend the visuals** to what the comparison shows.

5. **Qualitative compare — the part numbers can't give.** Read both batches **side by side** through
   your lens; read the player's own logs at the moments that matter. Write a focused finding and pass
   it to the report as `--finding`.

6. **Synthesize the verdict:** did the target move, did anything regress, and does the qualitative
   story explain (or contradict) the numbers? A common, important outcome: numbers say *noise* but
   behaviour visibly changed → more episodes, a sharper metric, or the change didn't do what you thought.

## What your lab supplies — the adapter

The shared engine (`scripts/ab_stats.py`) knows **no** game metrics. Each lab writes one small
`compare.py` (crewrift's is the worked example) that owns exactly:

- a **`Rec`** dataclass + **`load_batch`/`_record`** — extraction from *its* `results.json`/`episode.json`;
- a **`METRICS`** list of `(key, higher_is_better, kind∈{rate,mean}, applies_to_group|None)`;
- a **`metric_value(recs, key)`** aggregation and a **`value_fn(recs, key)`** for the mean test;
- a **`by_group(recs)`** grouping (crewrift: `{crew, imposter}`; a role-less game: `{"all": …}`);
- then imports `ab_stats` and calls `build_deltas(...)`, `render_markdown(...)`, `emit_json(...)`.

That's it — significance, verdicts, JSON contract, and Markdown all come from the engine, and the
report renderer consumes the neutral `{metric, group, base, cand, n_base, n_cand, p, effect, verdict}`
JSON. To add a new game: copy crewrift's `compare.py`, swap the four game-specific pieces.

## Discipline (the hard-won ones)

- **Matched + fresh, every time** — re-run the baseline alongside the candidate; never diff a stale batch.
- **Same tree** — build the baseline by git-stashing the candidate change, so only the subject differs.
- **Recompute on CLEAN episodes** — connect/disconnect-timeouts hit the arms **asymmetrically**; drop
  them (an `ops_fail`-style metric) before comparing or the delta is contaminated.
- **Decompose by group** — different roles are different policies; a change can help one and break the
  other (that's what the regression scan is for; a team-level "win" is a confounded metric).
- **Respect noise** — small batches and borderline deltas are not wins; the engine errs conservative
  on purpose — believe it. Rates need a few hundred appearances/side.
- **One change at a time** upstream, or the delta isn't attributable.

## See also

- **`coworld-experiment`** — hands a hypothesis here when the test needs a designed run (this is that run).
- **`coworld-experience-requests`** / **`coworld-episode-artifacts`** — fire the matched runs / pull them.
- **`crewrift-ab`** — the reference adapter (crewrift's metrics over this engine).
