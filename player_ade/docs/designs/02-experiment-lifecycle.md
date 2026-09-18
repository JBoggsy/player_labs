# Idea and experiment lifecycle

Improving a policy means coming up with ideas, running experiments to test them,
and recording the results. This document records the pipeline the user described,
the entities it is made of, and how the user is meant to see and shape it.

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

## Entities

The entities form a hierarchy: topics contain hypotheses, which contain
experiments and their results. (Whether this is a strict tree or whether one
hypothesis can sit under several topics is open: [Q10](05-open-questions.md).)

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

Experiments have their own lifecycle: **proposal → implementation → execution**,
each recorded. Experiments are the **player's purview**. The user may suggest
experimental setups inside a topic or hypothesis, but the player generates,
proposes, and executes experiments.

### Results and analysis

Produced by a run experiment. Includes all evidence and artifacts (result files,
scores, replays, logs) plus the player's analysis write-up and conclusions,
including the validity check and the falsification check above.

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
with. The wiki page format will likely be reused, with a different connective
structure (the hierarchy above) especially in the user-facing UI. The design
questions here are about *how this information is exposed to the user*; they are
collected in [05-open-questions.md](05-open-questions.md) (Q9–Q13).
