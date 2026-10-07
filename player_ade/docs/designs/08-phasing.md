# Phasing: start simple

The user's direction for sequencing: **"Let's start simple."**

## Phase 1

Build three things, as a local app for one user, against one lab:

1. The **web UI for the wiki** ([01-collaborative-wiki.md](01-collaborative-wiki.md)).
2. The **web UI for the experiment pipeline**
   ([02-experiment-lifecycle.md](02-experiment-lifecycle.md)).
3. A **single, general-purpose, invokable, interactive agent** that the user
   starts and drives from the UI.

Not in phase 1: the scheduled and triggered autonomous agents, the specialized
roster (Librarian, Scientist, Strategist, Manager), and inter-agent messaging.
Those come after the UI and the single agent exist; their requirements are
recorded in [03](03-player-system-harness.md) and [04](04-agents.md) so later
phases have a starting point. How much of the budgeting system is in phase 1 is
[Q29](05-open-questions.md).

## Order of work

1. **Understand and stand up CAOS** ([07-research-plan.md](07-research-plan.md),
   area 4). Everything else rests on it.
2. **Research agentic memory** (area 1) before the wiki's indexing and
   retrieval are designed.
3. Detailed design, then the build.

## Phase-1 decisions

| Topic | Decision | Detail in |
| --- | --- | --- |
| Where it runs | A local app used by one person. It will probably grow beyond that; nothing about hosting, authentication, or multiple users is designed now, but design choices should not close that door. | |
| Pilot game | Gods of the Arena. The wiki and pipeline UI are built against `gods_of_the_arena_lab/` only; other labs are untouched until later. What that means for the root files every lab shares is [Q30](05-open-questions.md). | [01](01-collaborative-wiki.md) |
| Substrate | CAOS from the outset, as the history system and as the agent harness. | [03](03-player-system-harness.md) |
| Wiki location | Each lab's `docs/` is that lab's wiki; the root `docs/` is the shared wiki. The current lab structure is provisional. | [01](01-collaborative-wiki.md) |
| Page format | Markdown files rendered on the fly by a simple templated renderer (markdown, images, Mermaid to start); tags in front matter; comments in an optional JSON file per page. | [01](01-collaborative-wiki.md) |
| Editing | The player has dedicated editing tools that ensure nothing gets lost or overwritten. The user edits in the UI. | [01](01-collaborative-wiki.md) |
| User edits and comments | User edits accumulate as diffs in a changelog until the agent marks them read; related pages carry an unread-changes marker; comments are threaded, go both ways, and can be resolved. | [01](01-collaborative-wiki.md) |
| Notifications | In-app only. | [01](01-collaborative-wiki.md) |
| Strategy drives code | Strategy documents first, then the agent compiles them into policy code; an automated dirty flag and diff highlight when they diverge. | [01](01-collaborative-wiki.md) |
| Pipeline | Topics, hypotheses, experiments, and results with their links, lineage, and lifecycle states; wiki pages hold evidence that is not yet a topic. | [02](02-experiment-lifecycle.md) |
| Spending | No per-experiment approval; spending is governed by the budgeting system. | [02](02-experiment-lifecycle.md), [03](03-player-system-harness.md) |
| Evidence | A design sketch, not yet detailed: referenced in place by content hash plus platform identifiers, with a local, untracked evidence database. Replay viewing links out to the Observatory viewer. | [02](02-experiment-lifecycle.md) |
| Tags | A curated tag list; tags in front matter; restricted-removal tags enforced by the tagging tool; `do-not-publish` honored by every public write path; tag pages and tag filters in the UI. | [09](09-tags-and-policy-versions.md) |
| Policy versions | A minimal version tree: one record per upload with its parents, the pinned hashes, and the dirty flag. | [09](09-tags-and-policy-versions.md) |
| Lab record files | Best practices and preferences become wiki pages; each lab's working context and tentative lessons are absorbed into the pipeline. The old files are deprecated; the timing is [Q30](05-open-questions.md). | [01](01-collaborative-wiki.md), [02](02-experiment-lifecycle.md) |

## The phase-1 agent

**Where it runs.** In CAOS. What the agent is inside CAOS, how the web UI
connects to it, how the lab's existing Claude Code skills, hooks, and
instructions carry over, and where Codex fits are all settled by the CAOS work
([07-research-plan.md](07-research-plan.md), area 4).

**Its instructions.** A **fresh top-level instruction file structured for
Player-ADE**, into which the current root agent guide's rules are migrated
section by section. The nine shared lab skills are kept as they are until the
CAOS work says how they port. While moving sections, **the assumptions being
abandoned must not be carried over**: the user is no longer a hard gate, and
the agent is meant to be more autonomous than the terminal-session guide
assumes. Which specific gates remain is [Q28](05-open-questions.md). The lab's
speed-over-caution rule carries over in pipeline terms: propose, implement, and
run without ceremony.

The file adds duties the current guide does not have:

- read the changelog of user edits and mark entries read, when the user asks;
- respond to comments, and resolve only its own unless asked;
- use the dedicated editing tools so that nothing is lost when it edits
  documents;
- write a policy change into the strategy documents first, then compile;
- weigh experience-request spend against the budget it is shown;
- tag pages `do-not-publish` where the guidance says to, and publish only
  untagged pages.

**Per-lab instructions.** Each lab's guidance survives as a **per-lab wiki
page** that the agent is pointed at. It replaces the lab's `AGENTS.md`
read-order list, which refers to files that are being removed.

**Its briefing at session start.** The general instructions plus the **wiki and
pipeline state of the lab it was started in**. This replaces the per-lab
`WORKING_CONTEXT.md` and `TENTATIVE_LESSONS.md` files and the session-start
hook that points every agent at them. The changelog of user edits is not pushed
into the briefing: the instructions carry a pointer to it, and the user drives
when the agent looks.

**What it needs.** The skills and knowledge of the whole improvement loop (the
existing lab skills), plus the tools to read and write wiki pages and pipeline
entities.

## What one interactive agent means for the two surfaces

Because phase 1 has one interactive agent and no autonomous ones:

- Nothing reacts to a user edit on its own. Edits and comments are recorded, and
  the agent deals with them when the user invokes it and asks. The alert to a
  background agent and the scheduled wiki maintenance (wiki requirements 2
  and 6) arrive with the autonomous agents.
- Creating a topic does not spawn agents. The user creates or comments on topics
  and hypotheses in the UI, and the agent works the pipeline when the user
  invokes it.

## Later phases (order not yet decided)

- The autonomous scheduled and triggered agents and their roster: Librarian,
  Scientist, Strategist, Manager.
- Inter-agent messaging, and observability of what agents are doing. Spend
  tracking is [Q29](05-open-questions.md).
- The other labs, and a deliberate definition of what a lab is.
- Notifications outside the app.
- An in-app replay viewer; the browsable policy-version evolution view and
  version diffing.
- Reachability beyond one local user.
