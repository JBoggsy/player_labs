# Phasing: start simple

Recorded from the user, 2026-09-17: **"Let's start simple."**

## Phase 1 (first step)

Build:

1. The **web UI for the wiki** ([01-collaborative-wiki.md](01-collaborative-wiki.md)).
2. The **web UI for the experimentation pipeline**
   ([02-experiment-lifecycle.md](02-experiment-lifecycle.md)).
3. A **single, general-purpose, invokable, interactive agent** that the user
   starts and drives from the UI.

Explicitly *not* in phase 1: the scheduled and triggered autonomous agents, the
specialized roster (Librarian, Scientist, Strategist, Manager), inter-agent
messaging, spend tracking, the meta-agent. Those come after the UI and the
single agent exist. The design documents for them stay as recorded so later
phases have a starting point.

## Consequences for the phase-1 design

Because there is one interactive agent and no autonomous ones in phase 1:

- Wiki requirement 2 ("user edits wake the player") and 6 (scheduled
  maintenance) cannot be met by a background agent yet. In phase 1 the user
  edits and comments are **recorded** (history, change log, comments) and the
  interactive agent **sees them when next invoked**. How the agent is pointed at
  pending edits and comments at session start is a phase-1 design question
  ([Q6](05-open-questions.md)).
- The experiment pipeline's "creating a topic immediately spawns agents" chain is
  deferred. In phase 1 the user creates or comments on topics and hypotheses in
  the UI, and the interactive agent works the pipeline when the user invokes it.
- The single agent needs the **skills and knowledge of the whole loop** (the
  existing lab skills) plus the ability to read and write wiki pages and pipeline
  entities in whatever format the UI uses.

## Later phases (order not yet decided)

- Autonomous scheduled/triggered agents, starting with the Librarian (wiki) and
  the Scientist (pipeline), since they attach to the two phase-1 surfaces.
- Inter-agent messaging, spend and activity observability.
- Manager / meta-agent.
- Codex interop, if not already covered by phase 1's agent runner.
