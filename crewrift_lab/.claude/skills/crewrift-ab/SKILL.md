---
name: crewrift-ab
description: "Use to A/B test two Crewrift policy versions head-to-head and decide whether a change actually helped — RIGHT NOW, against the current field. Triggers: 'did my change help', 'compare v2 vs v1', 'A/B test crewborg', 'is the candidate better than the baseline', 'test this hypothesis', 'did fixing the imposter regress the crewmate'. Runs two matched fresh experience requests, compares hard metrics (compare.py) AND guides a context-driven qualitative investigation of the logs/replays. Distinct from crewrift-report, which surveys ONE batch descriptively."
---

# Crewrift A/B

Decide whether a change to a player policy **actually helped** — by testing the
candidate against the baseline **head-to-head, fresh, right now**. This is the
loop's *re-measure* step (`crewrift_lab/AGENTS.md`): you changed one thing and
uploaded it; this tells you if it beat the version it came from.

It has two halves: a **quantitative** engine (`scripts/compare.py` — role-split
metric deltas with significance) and a **qualitative** investigation **you** run
(read the two sides' logs/replays for the *why*, steered by your context). The
question is always targeted: *did the thing I tried to improve move, and did
anything regress?* — not the broad "what's interesting here" of `crewrift-report`.

## The one principle that makes it valid: fresh + matched

The league field **drifts** — other people change their agents constantly. So you
**cannot** compare the candidate's fresh games against the baseline's stale
historical games; the difference would be confounded by everyone else's changes.

> **Run both versions in the same window, against the same roster/roles/count.** Two
> matched experience requests fired together → field drift hits both equally → the
> delta is attributable to *your* change. The question is "is the candidate better
> **now**," not "would it have beaten last week's field."

Don't reuse an old downloaded baseline batch. Re-run the baseline fresh alongside the
candidate, every time.

## Workflow

### 1. Frame the test
Name the **baseline** and **candidate** versions, and the **target axis** — the one
metric the change was meant to move (e.g. `kills_mean` for imposters, or shrinking
`imposter_no_kills_rate`). Optionally fix your qualitative lens now too: a specific
**opponent** you're losing to, or a specific **fault** you're chasing.

### 2. Fire two MATCHED, fresh experience requests
Use the **`coworld-experience-requests`** skill, identical params for both except the
subject version:

```sh
S=.claude/skills/coworld-experience-requests/scripts/experience_request.py
# rank the current field to pick the shared opponents (name + version per seat)
uv run python $S resolve --division <div_…> --top 7
# build TWO request bodies that are byte-identical except the subject's policy_ref
# (same target, same pinned roster, same roles, same count), then create BOTH back-to-back:
uv run python $S create baseline_req.json
uv run python $S create candidate_req.json
uv run python $S monitor <xreq_baseline>     # and the candidate xreq
```

Matched = same target, **same explicitly-pinned opponent roster**, same role
distribution, same episode count, same window. (Fire them back-to-back so they see
the same field.) In the `roster`, name **every** seat with an explicit
`policy_ref: "name:vN"` — **never `top_n`/`random` in an A/B**: the champion pool
drifts between requests and can even seat your own league entry, so the two arms
would face different fields (this exact confound burned the v22-vs-v24 A/B; see
`crewrift_lab/TENTATIVE_LESSONS.md`). Pin the subject at its slot; the only byte
that differs between the two bodies is the subject's `policy_ref` version. See the
experience-requests skill's `references/api.md` for the body fields.

### 3. Pull both batches
With the **`coworld-episode-artifacts`** skill, one directory per side:
```sh
A=.claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py
uv run python $A --xreq <xreq_baseline>  --out /tmp/ab/base
uv run python $A --xreq <xreq_candidate> --out /tmp/ab/cand
```

### 4. Quantitative compare
```sh
scripts/compare.py /tmp/ab/base /tmp/ab/cand \
  --baseline crewborg:v<BASELINE_N> --candidate crewborg:v<CANDIDATE_N> --target kills_mean
```
It leads with the **target axis** delta, then a **role-split** table of all metrics
(win rate, score, tasks, kills, penalties, no-vote, and the report categories as
rates), each marked **improved / regressed / noise** with a p-value, plus a
**regression scan** (did fixing one role break the other?). It is deliberately
conservative — a borderline move reads as `noise`, not a win. Mind the small-n
warning; rates need a few hundred appearances per side to separate from noise.

### 5. Qualitative compare — *the part numbers can't give you*
`compare.py` says **whether** something moved; it can't say **why**, and it misses
patterns no column captures. Investigate the two batches **side by side**, steered by
your context. (This is your own reasoning over the artifacts — not the `crewrift-report`
survey; you're comparing two sides on a chosen axis, not cataloguing one.)

**Set your lens** from the framing — pick the ones that apply:
- **A target dimension** — the behavior the change was about (e.g. "imposter kill
  timing", "meeting votes").
- **A specific opponent** — are we losing to one player? (e.g. "are we still getting
  killed by `pale blue`?")
- **A specific fault** — a failure you're hunting (e.g. "voting out a real crewmate",
  "not fleeing after a kill").

**Then read both sides for that lens:**
1. Build the version-matched reader once (`crewrift_lab/tools/build_expand_replay.sh`)
   and expand episodes from **both** batches — the objective event timeline
   (kills/bodies/votes/tasks, with true roles). See
   [`crewrift-replays.md`](../../../docs/crewrift-replays.md).
2. Read the policy's **own logs** on each side for its reasoning at the moments that
   matter (crewborg: [`crewborg/docs/trace-logs.md`](../../../crewrift/crewborg/docs/trace-logs.md);
   others: plain-text stderr).
3. **Compare the two sides on the lens** and write a focused finding, with evidence
   from each side. Examples of what this surfaces that the table won't:
   - *"Baseline got killed by `pale blue` in 6/20 imposter games right after a vent;
     candidate avoids that — down to 1/20."*
   - *"Both still vote a real crewmate ~1/3 of meetings; the candidate's suspicion
     model changed the number it picks but not the error rate — the fix didn't land."*
   - *"Candidate kills earlier (tick ~1500 vs ~2800) but gets caught more — explains
      why kills_mean rose yet win_rate didn't."*

### 6. Synthesize the verdict
Combine the quantitative delta and the qualitative finding into one call for the
human: **did the targeted thing improve, did anything regress, and does the
qualitative story explain (or contradict) the numbers?** A common, important outcome:
the numbers say *noise* but the behavior visibly changed — then you need more episodes,
a sharper target metric, or the change didn't do what you thought.

## Discipline (don't skip)
- **Matched + fresh, every time** — re-run the baseline alongside the candidate; never
  diff against a stale batch.
- **Decompose by role** — crewmate and imposter are different policies; a change can
  help one and break the other (the regression scan exists for exactly this).
- **Respect noise** — small batches and borderline deltas are not wins. `compare.py`
  errs conservative on purpose; believe it.
- **One change at a time** upstream, or the delta isn't attributable.

## Files
- `scripts/compare.py` — the quantitative role-split diff (+ `--json`).
- The qualitative half is agent-run (§5), leaning on `build_expand_replay.sh`,
  `crewrift-replays.md`, and the policy's log docs.
