---
name: crewrift-report
description: "Use to turn a SET of Crewrift episodes (an experience request, a policy's recent league games, a round/tournament batch) into a dense, high-signal report on a player policy's strengths and weaknesses. Triggers: 'analyze/report on these XP-request episodes', 'where is crewborg weak', 'find the interesting/bad/good games', 'what did v15 do wrong as imposter', 'summarize this batch of replays/logs', post-mortem of an evaluation. Crewrift-specific (roles, votes, kills, expand_replay). Pair with coworld-episode-artifacts (to pull the episodes) and coworld-experience-requests (to create them)."
---

# Crewrift Report

Turn the large, noisy pile of episode artifacts from an experience request (or a
batch of tournament episodes) into a **dense, high-signal report** that makes a
player policy's strengths and weaknesses easy to spot. This is the analysis engine of
the loop's **Report** step (see `crewrift_lab/AGENTS.md`).

It works by finding the **"interesting" episodes** — the outliers and failure/success
cases that actually carry signal — and nailing down what the policy did in them, so
the human can quickly see where to improve. Read
[`references/signals.md`](references/signals.md) for the full taxonomy of what's
flagged and why; read [`crewrift_lab/docs/crewrift-gameplay.md`](../../../docs/crewrift-gameplay.md)
to interpret events as gameplay.

## Three tiers (cheap → deep)

Most signal is cheap; only drill deep where it pays off.

1. **Tier 1 — structured (`scripts/report.py`).** Reads `results.json` + `episode.json`
   across the batch (no replay parsing). Per-slot **role flags**, scores, tasks,
   kills, vote behavior, and timeouts give role-decomposed distributions and flag most
   "interesting" categories instantly. Scales to hundreds of episodes.
2. **Tier 2 — objective timeline (`scripts/profile_replay.py`).** Runs the
   version-matched `expand_replay` on a flagged episode and extracts what Tier 1
   can't: **killed-by-imposter vs ejected-by-vote vs survived**, the **itemized score
   breakdown**, **vote correctness** (did it vote a real imposter? eject a real
   crewmate?), and an **event-feature vector**.
3. **Tier 3 — the policy's own logs.** The subjective *why* at the tick of interest
   (crewborg: [`crewrift/crewborg/docs/trace-logs.md`](../../../crewrift/crewborg/docs/trace-logs.md);
   others: plain-text stderr). Reach for this on the few juiciest episodes.

## Workflow

1. **Get the episodes** into one directory with the `coworld-episode-artifacts` skill
   (by experience request, `--policy <name> --version N`, round, or division), e.g.
   `… fetch_artifacts.py --policy crewborg --version 15 -n 100 --out /tmp/eps`.

2. **Tier 1 — the report:**
   ```sh
   scripts/report.py /tmp/eps --policy crewborg --version 15 --json /tmp/report.json
   ```
   Read the role-split distribution and the ranked **interesting episodes**. The
   `episode_dir` on each line is the drill-in handle.

3. **Tier 2 — profile the flagged episodes.** Build the replay reader once
   (`crewrift_lab/tools/build_expand_replay.sh`; Observatory replays match
   `CREWRIFT_REF`), then:
   ```sh
   scripts/profile_replay.py /tmp/eps/<episode_dir> --policy crewborg:v15
   ```
   Run it on the episodes Tier 1 flagged (the killed/ejected, vote-correctness, and
   score-breakdown facts are here). Parallelize across the flagged set if there are
   many.

4. **Tier 3 — read the logs** of the most informative episodes at the tick the
   profile points to, for the behavioral *why*.

5. **Synthesize.** Write a dense report for the human: the headline role-split
   outcome, then a ranked list of concrete strengths and weaknesses, each tied to
   specific episodes and the deviating signal — and frame the takeaways as
   **explicit, falsifiable hypotheses** ("as imposter it skips every meeting → never
   ejects crew; predict: forcing aggressive votes raises imposter win-rate"), not
   conclusions.

## Discipline (from `best_practices.md`)

- **Always decompose by role** — crewmate and imposter are effectively two different
  policies; an aggregate hides one role being broken. `report.py` splits every
  distribution; keep that split in your synthesis.
- **Separate operations from behavior** — connect/disconnect timeouts (−100) are a
  *crash*, not a strategy flaw; they get their own category. Don't let them pollute
  behavioral analysis.
- **Chase the "should-have-won" game** — `crew_lost_nearly_won` (tasks ≈ complete but
  lost) is usually the most informative failure.
- **Mind small n** — `report.py` warns under ~20 appearances; don't over-read a thin
  batch. Pull more episodes for firm claims.
- **A/B is the next step** — to judge whether a change helped, run this on two
  versions' batches and compare role-split distributions + which categories shrank.
  (v1 reports one batch at a time; diffing two reports is straightforward.)

## "Unusual event profile"

`profile_replay.py` emits a per-episode **feature vector** (kills, bodies, meetings,
ticks, the policy's votes/ticks-alive/kills). An episode is **unusual** = an outlier
on some feature relative to the batch (robust z / rank), reported with the *specific*
deviating feature ("alive only 180 ticks vs median 3000", "0 chats vs median 4").
Aggregating these features across the batch for automatic outlier flagging is the
documented next extension; for now, scan the feature vectors of flagged episodes.

## Files

- `scripts/report.py` — Tier 1 structured report (+ `--json`).
- `scripts/profile_replay.py` — Tier 2 per-episode fact sheet from `expand_replay` (+ `--json`).
- `references/signals.md` — the category taxonomy, the artifact field reference, the
  score model, and the `expand_replay` event-line formats.
