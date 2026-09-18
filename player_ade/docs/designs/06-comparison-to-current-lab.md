# Comparison: the current lab versus the proposed pipeline

The user asked: "This pipeline, or something pretty similar to it, exists already
in the lab setup. Compare what is established in the lab right now to the above
and let me know what the differences are." This document is that comparison,
based on a read of the lab's skills, docs, and per-lab records on 2026-09-17.

## Summary

The lab has the **middle two stages** (hypothesis generation, experiment
design/run/verdict) as well-developed *procedures* (skills), and has the
*statistics* for analysis. It has **no topic stage**, **no persistent entities**
linking the stages, **no lifecycle states**, **no comment channel**, and a
record-keeping policy that actively forbids keeping the history the proposed UI
would display. The lab's loop is also **evidence-first** (evaluate → diagnose →
improve), where the proposal is **idea-first** (topic → hypothesis → experiment).

## Stage by stage

| Proposed stage | What the lab has today | Where |
| --- | --- | --- |
| **Topics** (ideation) | Nothing persisted. The human gives "direction" in conversation (`AGENTS.md` step 3: "consult until the human gives a direction"). Nearest approximations: the single Objective / Next-decision in each lab's `WORKING_CONTEXT.md`; bullets in `TENTATIVE_LESSONS.md` (candidate lessons awaiting evidence, not investigation topics); deferred tasks in `TODO.md`. None supports a write-up with children. | `AGENTS.md:59-61`, `<lab>/WORKING_CONTEXT.md` |
| **Hypotheses** | Two generators: the `coworld-hypothesis-miner` skill (statistical: mines a batch of scored episodes for behaviors that separate wins from losses; emits a ranked markdown report of candidates with an 8-field template: Observation / Causal guess / Evidence / Missing data / Change / Expected / Next step / Overfit risk) and Crewrift's `crewrift-diagnose` skill (explanatory: 2–4 mechanisms pinned to code locations, each with a JSON record `{title, evidence, mechanism, change, predicted_effect, confidence, experiment}`). Both write to arbitrary output paths (the miner's convention is `/tmp`); hypothesis ids (`H1`…`H5`) are local to one report. | `.claude/skills/coworld-hypothesis-miner/`, `crewrift_lab/.claude/skills/crewrift-diagnose/` |
| **Experiments** | The `coworld-experiment` skill: design → adversarially criticize (construct validity, config masking, two differing predictions, falsifiability, confounds, power and cost) → redesign until it holds → present the design as HTML before running → run → verdict. Governing rule: "never run an experiment whose outcome couldn't change your mind." One hypothesis at a time. The artifact is a JSON design file `{hypothesis, what_changes, instrument{kind,summary,detail}, if_true, if_false, decision_rule, confounds[], verdict{result, evidence}}` plus a rendered HTML page. No canonical storage path, no id, no index. | `.claude/skills/coworld-experiment/SKILL.md:32-102`, `scripts/experiment_report.py:6-21` |
| **Results and analysis** | The `coworld-ab` skill and its shared stats engine (`ab_stats.py`): matched, same-window A/B; per-metric verdicts `improved / regressed / noise` with multiple-comparison correction; a rendered HTML comparison report. Analysis is otherwise a *field*, not a stage: the experiment's `verdict{result, evidence}` is one string, and the A/B report's qualitative half is a `--finding` file passed at render time. The experiment JSON has **no field for the experience-request or episode ids** it used; provenance survives only in prose. | `.claude/skills/coworld-ab/`, `scripts/compare_report.py:15` |

## The "invalidate the experiment" versus "falsify the hypothesis" distinction

The proposal wants analysis to first ask whether the results invalidate the
experiment (it tested something else), and only then whether they falsify the
hypothesis. **This distinction does not exist in the lab today.**

- Validity is judged **before the run only**, in the criticism step; a failing
  design is redesigned, not run.
- After the run, "the experiment tested something else" and "the hypothesis is
  undecided" collapse into the **same** verdict value, `inconclusive` ("underpowered,
  confounded, or the predictions weren't as distinct as you thought").
- The verdict enum is `confirmed | refuted | inconclusive`.

So the proposal adds a post-run validity outcome that the current schema cannot
express.

## Where records actually land today

This is inconsistent across labs, which matters because the UI needs one place
to read from.

- **Paintbot** is the only lab that persisted experiment records:
  `paintbot_lab/docs/reports/<policy>-v<N>-<slug>-experiment.json` (nine files),
  exactly the `coworld-experiment` design JSON with the verdict filled in. The
  v49 → v50 → v51 → v52 → v53 chain is a de facto hypothesis lineage, but it is
  encoded **only in prose** inside each `verdict.evidence` that names the next
  version. There is no parent/child field.
- **Crewrift** has one experiment record, a script
  (`crewrift_lab/tools/experiments/2026-07-29-chatfix-verdict.py`) whose docstring
  names a preregistration markdown file that **no longer exists in the repo**. The
  "no archive" policy deleted the hypothesis→experiment link.
- **Gods of the Arena** has no experiment records at all yet (no policy uploaded).
  It does have the repo's best model of a knowledge index:
  `gods_of_the_arena_lab/docs/research.md`, a "what we know and where" table with
  per-document currency blocks naming the game-engine commit each fact was
  verified against, and inline embargo tags ("Lab-internal finding; do not post").
- Raw evidence lives in
  `<lab>/episode_data/xreq_<id>/<timestamp>_ereq_<id>-<seat>/` (results, episode
  metadata, logs, replays), downloaded by the shared artifacts skill.

## Gaps against the proposal, in one list

1. **No topic entity.** Nothing sits between "the human said something in chat"
   and a hypothesis.
2. **No hierarchy, ids, or links between stages.** Stages chain by skill prose and
   human hand-off ("where every mined candidate goes next"), not by data. The only
   stable ids are the platform's (`xreq_…`, `ereq_…`).
3. **No lifecycle states.** The only state-like values are terminal verdicts. The
   word `pending` in the experiment renderer is a display fallback for a missing
   key, not a state. Nothing represents proposed / criticized / implementing /
   running / analyzed.
4. **No comment channel on any entity.** All human feedback is chat. Reports are
   static HTML. The only inbox-like thing is the forum agent's `attention` list in
   its `state.json`, an agent→human flag with no reply path.
5. **No user-created entities and no notifications** when the user edits files.
6. **A hypothesis is one-shot.** "One hypothesis at a time"; a refuted hypothesis
   is terminal, with nothing above it (a topic) to survive the refutation.
7. **Record-keeping policy forbids the history the UI needs.** Four separate
   authoritative statements say not to keep it:
   - `docs/learning.md:17-20`: "Remove obsolete reports, version logs and change
     narratives. Do not recreate an archive."
   - `docs/learning.md:26-28`: raw artifacts and results "remain the evidence for
     analysis; do not turn them into a permanent documentation history."
   - `best_practices.md:105-107`: "Do not accumulate change narratives, audit
     records or historical reports."
   - `user_preferences.md`: "Remove historical reports, version logs, obsolete
     measurements, change narratives."
   A browsable archive of past topics, hypotheses, experiments, and results is
   exactly what these rules currently forbid. See [Q23](05-open-questions.md).
8. **Analysis is a field, not a stage**, and the experiment record does not
   reference its evidence by id.
9. **Storage is per-lab and inconsistent** (see above). No shared path
   convention, index, or schema validation.

## What the lab has that the proposal should keep

- The **criticism gate** in `coworld-experiment` (design must be falsifiable,
  cheap, and unconfounded before it runs) and the rule that only experiments
  whose outcome could change your mind get run.
- The **shared statistics engine** and per-lab metric adapters in `coworld-ab`;
  the miner's shared engine and per-lab feature adapters. The adapter pattern is
  how game-agnostic method meets game-specific data.
- The **JSON-plus-rendered-HTML** convention for experiment and comparison
  reports, and the "Ink & Print" report style shared across renderers.
- The **routing table** in `docs/learning.md` (which kind of knowledge goes in
  which file) and the promotion rule (tentative until independent evidence).
- `gods_of_the_arena_lab/docs/research.md` as a template for a wiki index with
  currency and embargo markers.

## Existing automation the design can build on

- **One scheduled agent**: the standing forum agent (`tools/forum_agent/run.sh`),
  headless Claude Code run every 30 minutes by launchd
  (`com.jamesboggs.forum-agent.gota`), configured per lab by a `brief.md` and a
  `state.json`. Its rules ("a run's default outcome is no write", one comment per
  run, never commits) are a useful precedent for autonomous agents.
- **One hook**: `SessionStart`, nine copies (one per lab), each read-only,
  injecting "read this lab's WORKING_CONTEXT and TENTATIVE_LESSONS".
- Manual background jobs: streaming artifact download, the XP dashboard that the
  user requires for any request over 16 episodes.
- No file-watch or post-edit hooks, no message bus, no spend tracking, no search
  tooling over the lab's own docs.
