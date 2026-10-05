# Idea and experiment lifecycle

Improving a policy means coming up with ideas, running experiments to test them,
and recording the results. This document describes that pipeline, the entities
it is made of, and how the user sees and shapes it.

The lab already has most of this pipeline in some form. The **novelty** is
exposing every stage to the user with deep observability into past and current
experiments, and making every stage collaborative. What the lab has today versus
what is described here is compared in
[06-comparison-to-current-lab.md](06-comparison-to-current-lab.md).

## The four stages

1. **Ideation.** Come up with ideas that would improve the policy in some way.
   Ideas can be vague. They usually come from theory-crafting (thinking about the
   game mechanics and how to use them well) or from observing the policy play.

2. **Hypothesis generation.** Given an idea, produce a specific, testable
   intervention that tries the idea out. A hypothesis is one more-or-less concrete
   instantiation of an idea. It must be a plausible way to realize the idea, but a
   failed hypothesis does not necessarily disqualify the idea. A hypothesis must
   also state how it can be falsified and why it genuinely tests the idea.

3. **Experimentation.** Take a hypothesis, plan and implement its intervention,
   then test the resulting policy. One idea can lead to several hypotheses; one
   hypothesis can have several experiments. Each experiment lays out a specific
   implementation design and plan and justifies why that implementation genuinely
   tests the hypothesis.

4. **Analysis.** Once an experiment runs, analyze its results and draw a
   conclusion. Gather every artifact the run produced (logs, result files,
   replays, and so on) and analyze them to determine the outcome. Then compare the
   outcome to the hypothesis in two distinct ways:
   - **Validity check:** do the results *invalidate the experiment* by showing it
     actually tested something other than the hypothesis?
   - **Falsification check:** if the experiment is valid, do the results *falsify
     the hypothesis*?

   These two checks are recorded as each result's outcome (`invalid`, or
   `supports` / `falsifies`) with a reason; see lifecycle states below.

## Entities

The entities are organized as a hierarchy: hypotheses sit under topics,
experiments under hypotheses, and results under experiments. The user's prompt
speaks of both "ideas" and "topics"; these documents treat a topic as the
recorded form of an idea, which the user has not confirmed
([Q32](05-open-questions.md)). The shape:

- **Topics to hypotheses: many-to-many.** A hypothesis can address several
  topics and appears under each of them; it has its own identity rather than
  living inside one topic.
- **Hypothesis to experiments: one-to-many.** Each experiment belongs to exactly
  one hypothesis.
- **Experiment to results: one-to-many.** Running the same experiment again
  (unchanged design, unchanged context; typically a larger sample or a fresh
  window) adds another result under the same experiment.
- **Experiment to experiment: a lineage.** A new experiment that slightly modifies
  an earlier one, or repeats it in a new context (a game version bump, a new
  field or meta), is a **child** of that single earlier experiment. One
  experiment can be the ancestor of many children. The rule of thumb: if the
  design and the context are unchanged it is a new result; if either changed it
  is a child experiment. This is guidance for the player and the user, not a
  rule the tools enforce. A child always belongs to the **same hypothesis** as
  its parent: testing a different hypothesis is a different experiment and
  should be seen as such. The parent link is bare; why the child exists (a
  variant, a replication under a new game version or field, an extension) is
  said in the child's own description.

### Topic

Some thing we want to address. Examples of what a topic might be about:

- A behavioral issue in the policy, or something the policy is bad at.
- A stated goal or outcome, such as improving shot accuracy or increasing last hits.
- A specific intervention, such as increasing fire rate or using movement to cancel
  attack backswings.
- A new strategy component, such as a flanking maneuver or rotating to empty lanes
  for farm.
- Something else entirely.

The essential content of a topic is a **write-up describing what is being
investigated and why.** Topics can be created by the player or by the user.

### Hypothesis

A specific, testable intervention that addresses one or more topics. Unlike a
topic, a hypothesis should be fairly specific. It lists a particular set of
interventions (strategic, tactical, or mechanical) and the expected outcome of
those changes. It must be concrete enough that the player can generate and
propose experiments against it, and that those proposals can be judged on whether
they really test the hypothesis. Hypotheses are themselves judged against the
topics they address: does this really make sense as an attempt to address the
topic?

### Experiment

Associated with one hypothesis. Describes:

- One or more concrete, implementation-level changes to the policy.
- How the change will be evaluated.
- A justification for why the change and its evaluation genuinely test the
  hypothesis, in light of the hypothesis's own claims and the broader topic(s).

Experiments move through their own stages (proposal, implementation, execution,
analysis), each recorded; see lifecycle states. Experiments are the **player's
purview**. The user may suggest
experimental setups inside a topic or hypothesis, but the player generates,
proposes, and executes experiments.

### Results and analysis

Produced by a run experiment. Includes all evidence and artifacts (result files,
scores, replays, logs) plus the player's analysis write-up and conclusions,
including the validity check and the falsification check above.

**Evidence storage** (a design sketch, not yet detailed): evidence is
**referenced in place, by content hash**, not copied under the result. The artifacts skill keeps downloading episode data into each lab's
gitignored `episode_data/`. A git-tracked file, presumably the result record,
references the evidence by a **digest of its content**, and the platform
identifiers (experience request id, episode id) let it be downloaded when no
local copy exists. A local **evidence database**, which the app owns and which is not
git-tracked because it maps hashes to files on one machine, associates each
digest with the local copy when one has been downloaded, or with the platform
identifiers alone when it has not. Content addressability is wanted from the
start. The user has not thought this design through in detail, and how it meets
CAOS, which content-addresses everything, is part of the CAOS work
([07-research-plan.md](07-research-plan.md), area 4).

**Replay viewing** in phase 1 is a link out to the Observatory's replay viewer
for each episode. An in-app viewer (coworld-specific) comes later.

Mandatory fields on every result: the **game version** it was measured against
(for Gods of the Arena, the commit of the game engine that was deployed, which
the lab already records) and the **date and time** of the run. With these,
results measured on an earlier game version can be recognized, which is when a
replication child experiment is warranted. A result also points at the **policy version** it measured
([09-tags-and-policy-versions.md](09-tags-and-policy-versions.md)).

## Lifecycle states

Every entity carries a state so the user can see what is proposed, in progress,
and finished, and so lists can be filtered.

| Entity | States |
| --- | --- |
| Topic | `open`; `closed` with a reason (for example resolved, abandoned, merged into another topic). |
| Hypothesis | `proposed` (written, no experiment yet); `under test` (at least one experiment in progress); `supported`, `falsified`, `abandoned`, each with a reason. Supported and falsified are judgements made from the results, not computed from them; a falsified hypothesis does not close its topics. |
| Experiment | `proposed`, `implementing`, `running`, `analyzed`. Validity is not an experiment state; it is recorded on each result. |
| Result | `running`, `complete`, `failed` (for example a broken upload or a cancelled request). Each complete result also carries an **outcome** (name provisional): `supports`, `falsifies`, or `invalid` (the run tested something other than the hypothesis), each with a reason. |

**Transitions and spending.** `proposed` to `implementing` and `implementing`
to `running` are separate transitions: implementation costs agent time but no
credits; running spends Softmax experience-request credits. Neither needs an
explicit approval step from the user. Instead, spending is governed by the
**budgeting system** in [03-player-system-harness.md](03-player-system-harness.md):
the player is shown the current credit budget when it is about to make a request
and is responsible for staying within it.

**Who sets states.** The user can set any stored state. The player may set the state
of any entity it created; for other entities it suggests a state change for the
user to approve. Every state change is attributed (user or player) in the
history. A state change does not by itself invoke an agent.

**Derived versus stored.** In-progress states are derived from children where
possible (for example, a hypothesis is `under test` while any of its experiments
is under way, and an experiment is `running` while any of its results is
`running`), so they cannot go stale. Judgement states (`supported`,
`falsified`, `abandoned`, `closed`, a result's outcome) are stored, with their
reasons. The exact derivation rules are detailed design.

## Evidence that is not yet a topic

The lab's loop starts with evidence (evaluate, diagnose, then direction); the
pipeline starts with a topic. The two meet through links. Evidence that no topic
addresses yet (survey reports, mined hypothesis lists, field studies, opposition
notes, diagnostic runs) lives in the **wiki** as ordinary pages. Pipeline
entities and wiki pages are linkable in both directions, so a topic can link to
the pages that motivated it and a page can link to the topics that grew out of
it. See
[01-collaborative-wiki.md](01-collaborative-wiki.md).

## History is kept; write-ups stay current

The pipeline is an archive by design: every topic, hypothesis, experiment, and
result is kept with its state, game version, and date. The lab's rule against
archives applies to the **prose** inside these entities, not to the records:
a topic or hypothesis write-up describes the current understanding only, and an
experiment's description says what it does, not how it changed. See
[01-collaborative-wiki.md](01-collaborative-wiki.md).

## Absorbing the existing lab records

Each lab's `TENTATIVE_LESSONS.md` and `WORKING_CONTEXT.md` are absorbed into the
pipeline and then removed.

- A **tentative lesson** is a hypothesis: a claim, the intervention it implies,
  and the evidence needed. Each entry becomes a hypothesis; where evidence
  already exists (an A/B with a verdict), it also becomes an experiment with a
  result carrying the game version and date it was measured on.
- The working context's **objective and next decision** become open topics.
- The working context's **version narrative** (which version changed what) goes
  to the policy version tree
  ([09-tags-and-policy-versions.md](09-tags-and-policy-versions.md)).

The working context also holds material these mappings do not cover. The
scribe's suggestions for it, not yet ruled on by the user: the measurements in
the version narrative become results attached to those versions, and the
identity and environment facts (deployed game commit, account and platform
player identities, instruments) become wiki pages. When the migration happens
is part of [Q30](05-open-questions.md).

## Collaboration requirements

- The user can **suggest** new topics, ideas, and hypotheses.
- The user can **comment on and edit** experiments and conclusions (and every
  other entity), just as the player can.
- The player must be able to **present** its experimental setup, its evidence, and
  its conclusions to the user.
- The user's feedback must be **incorporated into the improvement loop** the player
  is running, not just recorded.

## Storage and presentation

All entities are stored in a way that is easy for both player and user to work
with. Pipeline entities are expected to reuse the wiki page format
([01-collaborative-wiki.md](01-collaborative-wiki.md)): markdown files with
front matter for tags, an optional comments file, and the same editing tools.
The user has not confirmed this ([Q33](05-open-questions.md)). They differ in
their connective structure (the hierarchy above), especially in the
user-facing UI. Where an entity's structured fields (state,
reasons, links to parents, game version) are kept within that format is
detailed design.
