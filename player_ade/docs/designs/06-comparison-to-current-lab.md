# Comparison: the current lab versus the designed pipeline

The pipeline in [02-experiment-lifecycle.md](02-experiment-lifecycle.md), or
something close to it, already exists in the lab in pieces. This document
compares what the lab has today with what the design asks for, and says how the
design closes each gap. The lab facts were read from its skills, docs, and
per-lab records and checked on 2026-10-05.

## Summary

The lab has the **middle two stages** (hypothesis generation, experiment
design/run/verdict) as well-developed *procedures* (skills), and has the
*statistics* for analysis. It has **no topic stage**, **no persistent entities**
linking the stages, **no lifecycle states**, **no comment channel on its
records**, and a record-keeping rule that, as written, forbids keeping the history the UI
displays. The lab's loop is also **evidence-first** (evaluate → diagnose →
improve), where the pipeline is **idea-first** (topic → hypothesis → experiment).

## Stage by stage

| Pipeline stage | What the lab has today | Where |
| --- | --- | --- |
| **Topics** (ideation) | Nothing persisted. The human gives "direction" in conversation (`AGENTS.md` step 3: "consult until the human gives a direction"). Nearest approximations: the single Objective / Next-decision in each lab's `WORKING_CONTEXT.md`; bullets in `TENTATIVE_LESSONS.md` (candidate lessons awaiting evidence, not investigation topics); deferred tasks in `TODO.md`. None supports a write-up with children. | `AGENTS.md` (the cycle, step 3), `<lab>/WORKING_CONTEXT.md` |
| **Hypotheses** | Two generators: the `coworld-hypothesis-miner` skill (statistical: mines a batch of scored episodes for behaviors that separate wins from losses; emits a ranked markdown report of candidates with an 8-field template: Observation / Causal guess / Evidence / Missing data / Change / Expected / Next step / Overfit risk) and Crewrift's `crewrift-diagnose` skill (explanatory: 2–4 mechanisms pinned to code locations, each with a JSON record `{title, evidence, mechanism, change, predicted_effect, confidence, experiment}`). Both write to arbitrary output paths (the miner's convention is `/tmp`); hypothesis ids (`H1`…`H5`) are local to one report. | `.claude/skills/coworld-hypothesis-miner/`, `crewrift_lab/.claude/skills/crewrift-diagnose/` |
| **Experiments** | The `coworld-experiment` skill: design → adversarially criticize (construct validity, config masking, two differing predictions, falsifiability, confounds, power and cost) → redesign until it holds → present the design as HTML before running → run → verdict. Governing rule: "never run an experiment whose outcome couldn't change your mind." One hypothesis at a time. The artifact is a JSON design file `{hypothesis, what_changes, instrument{kind,summary,detail}, if_true, if_false, decision_rule, confounds[], verdict{result, evidence}}` plus a rendered HTML page. No canonical storage path, no id, no index. | `.claude/skills/coworld-experiment/SKILL.md`, `scripts/experiment_report.py` |
| **Results and analysis** | The `coworld-ab` skill and its shared stats engine (`ab_stats.py`): matched, same-window A/B; per-metric verdicts `improved / regressed / inconclusive` with multiple-comparison correction; a rendered HTML comparison report. Analysis is otherwise a *field*, not a stage: the experiment's `verdict{result, evidence}` is one string, and the A/B report's qualitative half is a `--finding` file passed at render time. The experiment JSON has **no field for the experience-request or episode ids** it used; provenance survives only in prose. | `.claude/skills/coworld-ab/`, `scripts/compare_report.py` |

## The "invalidate the experiment" versus "falsify the hypothesis" distinction

The design has analysis first ask whether the results invalidate the
experiment (it tested something else), and only then whether they falsify the
hypothesis. **This distinction does not exist in the lab today.**

- Validity is judged **before the run only**, in the criticism step; a failing
  design is redesigned, not run.
- After the run, "the experiment tested something else" and "the hypothesis is
  undecided" collapse into the **same** verdict value, `inconclusive` ("underpowered,
  confounded, or the predictions weren't as distinct as you thought").
- The verdict enum is `confirmed | refuted | inconclusive`.

The design records this on each result as an outcome of `supports`,
`falsifies`, or `invalid`, each with a reason.

## Where records actually land today

This is inconsistent across labs, which matters because the UI needs one place
to read from.

- **Paintbot** is the only lab that persisted experiment records:
  `paintbot_lab/docs/reports/<name>-experiment.json` (eight files), exactly the
  `coworld-experiment` design JSON with the verdict filled in. Six of them form
  a v49 → v50 → v51 → v52 → v53 chain that is a de facto experiment lineage, but
  it is encoded **only in prose**, in the several `verdict.evidence` strings
  that name a neighboring version. There is no parent/child field.
- **Crewrift** has one experiment record, a script
  (`crewrift_lab/tools/experiments/2026-07-29-chatfix-verdict.py`) whose docstring
  names a preregistration markdown file that **no longer exists in the repo**. The
  "no archive" policy deleted the hypothesis→experiment link.
- **Gods of the Arena** has uploaded twenty policy versions and run many matched
  A/Bs, but has no experiment records in the `coworld-experiment` format. Its
  hypotheses, versions, request ids, and verdicts are written as prose in
  `WORKING_CONTEXT.md` and `TENTATIVE_LESSONS.md`, which point at scratch
  evidence in a gitignored `tmp/` directory. It does have the repo's best model of a
  knowledge index:
  `gods_of_the_arena_lab/docs/research.md`, a "what we know and where" table with
  per-document currency blocks naming the game-engine commit each fact was
  verified against, and inline embargo tags ("Lab-internal finding; do not post").
- Raw evidence lives under each lab's gitignored `episode_data/`, by convention
  one directory per experience request, holding one directory per episode named
  by a timestamp and a shortened episode id (results, episode metadata, logs,
  replays). The shared artifacts skill downloads it.

## Gaps, and how the design closes each

1. **No topic entity.** Nothing sits between "the human said something in chat"
   and a hypothesis.
   *Design:* topics are a first-class entity that either side can create.
2. **No hierarchy, ids, or links between stages.** Stages chain by skill prose and
   human hand-off ("where every mined candidate goes next"), not by data. The only
   stable ids are the platform's (`xreq_…`, `ereq_…`).
   *Design:* topics link to hypotheses many-to-many, hypotheses to experiments
   and experiments to results one-to-many, and experiments carry a parent link
   to the experiment they derive from.
3. **No lifecycle states.** The only state-like values are terminal verdicts. The
   word `pending` in the experiment renderer is a display fallback for a missing
   key, not a state.
   *Design:* every entity has states, with reasons on the closing ones.
4. **No comment channel on records or markdown sources.** Feedback on
   hypotheses, experiments, and results is chat, and the experiment and A/B
   reports are static HTML. There is one working precedent: the lab's rendered
   research reports and design documents (under `docs/reports/`,
   `gods_of_the_arena_lab/docs/reports/`, and `paintbot_pw_lab/docs/designs/`)
   embed a comment sidebar in which the reader selects text to comment and the
   agent's replies are stored with each comment. The only other inbox-like thing
   is the forum agent's `attention` list in its `state.json`, an agent→human
   flag with no reply path.
   *Design:* text-anchored, threaded, resolvable comments from both sides on
   every page and entity.
5. **No user-created entities and no notifications** when the user edits files.
   *Design:* the user creates and edits entities in the UI; a changelog carries
   the user's edits to the player and the player's edits to the user.
6. **A hypothesis is one-shot.** "One hypothesis at a time"; a refuted hypothesis
   is terminal, with nothing above it (a topic) to survive the refutation.
   *Design:* a falsified hypothesis does not close its topics.
7. **The record-keeping rule forbids the history the UI needs.** Four statements
   say not to keep it:
   - `docs/learning.md`: "Remove obsolete reports, version logs and change
     narratives. Do not recreate an archive."
   - `docs/learning.md`: raw artifacts and results "remain the evidence for
     analysis; do not turn them into a permanent documentation history."
   - `best_practices.md`: "Do not accumulate change narratives, audit
     records or historical reports."
   - `user_preferences.md`: "Remove historical reports, version logs, obsolete
     measurements, change narratives."

   *Design:* the rule is amended to apply to current-state prose only;
   structured, dated history is kept
   ([01-collaborative-wiki.md](01-collaborative-wiki.md)).
8. **Analysis is a field, not a stage**, and the experiment record does not
   reference its evidence by id.
   *Design:* each result is its own record with an analysis write-up, an
   outcome, the game version and time it was measured, the policy version, and
   its evidence referenced by content hash and platform ids.
9. **Storage is per-lab and inconsistent** (see above). No shared path
   convention, index, or schema validation.
   *Design:* one page format for wiki pages and pipeline entities; their layout
   in a lab is detailed design.
10. **Evidence-first versus idea-first.** The lab starts from evaluation; the
    pipeline starts from a topic.
    *Design:* evidence that is not yet a topic lives in wiki pages, linked both
    ways with the pipeline entities that grow out of it.
11. **Uploaded versions are not tied to their source.** Uploads happen without
    commits, so only prose says what each version changed.
    *Design:* every upload is a recorded version pinned to its strategy, source,
    and artifact ([09-tags-and-policy-versions.md](09-tags-and-policy-versions.md)).

## What the lab has that is worth keeping

A recorded suggestion from the scribe; the user has not ruled on this list.

- The **criticism gate** in `coworld-experiment` (design must be falsifiable,
  cheap, and unconfounded before it runs) and the rule that only experiments
  whose outcome could change your mind get run.
- The **shared statistics engine** and per-lab metric adapters in `coworld-ab`;
  the miner's shared engine and per-lab feature adapters. The adapter pattern is
  how game-agnostic method meets game-specific data.
- The rendered **experiment and comparison reports** and the "Ink & Print"
  report style shared across their renderers, as page content the wiki can show.
- The **promotion rule** in `docs/learning.md`: guidance stays tentative until
  independent evidence supports it. (That file's routing table, which says
  which kind of knowledge goes in which record file, is replaced by the wiki
  and pipeline.)
- `gods_of_the_arena_lab/docs/research.md` as a template for a wiki index with
  currency and embargo markers.

## Existing automation the design can build on

- **One scheduled agent**: the standing forum agent (`tools/forum_agent/run.sh`),
  headless Claude Code run on a timer, configured per lab by a `brief.md` and a
  `state.json`. The Gods of the Arena one is scheduled every 30 minutes by a
  launchd job on the user's Mac. It already writes to the public forum, so it
  is one of the public write paths the `do-not-publish` tag has to govern. Its rules ("a run's default outcome is no write", one comment per
  run, never commits) are a useful precedent for autonomous agents.
- **One hook**: `SessionStart`, with ten commands (one per active lab), each read-only,
  injecting "read this lab's WORKING_CONTEXT and TENTATIVE_LESSONS". The design
  replaces it with a briefing drawn from the lab's wiki and pipeline state.
- Manual background jobs: streaming artifact download, the XP dashboard that the
  user requires for any request over 16 episodes.
- No file-watch or post-edit hooks, no message bus, no spend tracking, no search
  tooling over the lab's own docs.
