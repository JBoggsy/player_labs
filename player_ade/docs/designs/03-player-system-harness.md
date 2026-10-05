# The player system and its harness

The "player" is a complete system, not one agent. It is an upgraded, expanded
version of the current lab turned into a complete harness in which different
agents handle different tasks.

Most of this document is a record of requirements, not a detailed design. Phase 1
builds only one piece of it, a single interactive agent
([08-phasing.md](08-phasing.md)); the rest is designed in a later phase.

## Substrate: CAOS

The player runs on **CAOS**, the Content-Addressable Operating System Softmax
is developing ([Metta-AI/caos](https://github.com/Metta-AI/caos)). It is used
from the outset, in two roles:

- **History.** Files and the programs, functions, and tool calls that act on
  them are hashed, so every change and every action the player takes is
  accounted for. This is the history system for the wiki, the pipeline, and the
  policy versions.
- **Harness.** Agents run inside CAOS, starting with the phase-1 agent.

CAOS is a work in progress, and how the agent runs in it is not yet known: what
the agent is inside CAOS, how the web UI connects to it, and how the lab's
existing Claude Code skills, hooks, and instructions carry over. That, and what
else has to be learned before building on it, is in the
[research plan](07-research-plan.md), area 4.

## Components

### Scheduled autonomous agents
Woken at regular intervals with specific instruction files, skills, and tools.
They handle regular tasks that need consistent effort and no user intervention:
knowledge maintenance, forum/wiki interactions on Softmax, experiment monitoring.

### Triggered autonomous agents
Woken when some event happens, or when the user asks. Each has a fixed job with
custom instructions, skills, and tools. The intended effect is that creating an
idea (a topic) immediately leads to agents working on it: when a topic is
created or updated, the Scientist is spun up to generate hypotheses for it and
then to run experiments on each ([04-agents.md](04-agents.md)).

### Agents that are both scheduled and triggered
Example: a Librarian that is regularly woken to keep the wiki accurate, current,
and complete, and is also spun up whenever the user edits the wiki, to incorporate
those changes.

### Invoked interactive sessions
Sessions the user spawns and interacts with directly, for general tasks and
especially for tasks that benefit from human oversight. The user wants to
interact with **multiple instances** of the player in two ways:
- **Short-term interactive sessions.**
- **Long-term loops** that either perform a repeating task or pursue a
  long-horizon goal.

### Inter-agent communication
Robust communication between agents via:
- An internal forum or message board.
- Inter-agent direct messages.
- Possibly a social-media-like board where agents post what they are working on.

(This is separate from the Softmax community forum and wiki, which are public and
belong to each coworld.)

### Spend, budgets, and observability
Tools that give the user insight into which agents are spending how much and why,
what agents are doing, and so on.

Spending is controlled by a **budgeting system**, exposed to the agents
intelligently. Two kinds of spend are budgeted separately:

- **LLM cost** of running agents. Monitored by the harness; scheduled agents are
  **paused** once spend passes a threshold (starting value: $250, to be tuned).
  This budget is **invisible to the agents**: they neither see it nor reason
  about it. The period the threshold covers, and whose spend counts toward it,
  are [Q31](05-open-questions.md).
- **Softmax experience-request credits.** The current balance is retrieved from
  the platform (the account credit endpoint documented in
  [`docs/xp-credits.md`](../../../docs/xp-credits.md): balance, refill, cap, next
  refill) and **given to an agent at the moment it is in a position to make a
  request**, with guidance that it is responsible for staying on budget and
  should therefore weigh whether the proposed request is worth its cost. The
  wording of that guidance needs workshopping: the aim is a budget-aware agent,
  not one afraid to spend, since hosted evaluation is the lab's primary
  instrument.

No per-experiment approval from the user is required for spending
([02-experiment-lifecycle.md](02-experiment-lifecycle.md)). Which parts of the
budgeting system are built in phase 1 is [Q29](05-open-questions.md).

### Skills and tools
Like what the lab has now, but expanded and upgraded: tools and skills for
interacting with the Observatory in many ways, and for each task and each agent
the system uses. New tools the design already calls for: the document editing
tools and the changelog ([01-collaborative-wiki.md](01-collaborative-wiki.md)),
and the tagging tool ([09-tags-and-policy-versions.md](09-tags-and-policy-versions.md)).

### The Manager (the meta-agent)
One agent monitors, measures, analyzes, and improves the other agents, the
overall player system and its harness, and itself. It also creates new agents.
See [04-agents.md](04-agents.md).

### Interop with both Claude Code and Codex
The system must work with both. How each plugs into the CAOS harness is settled
by the CAOS work.

## Per-coworld labs, mirrored in the UI
Coworld-specific knowledge stays separated per lab; coworld-agnostic knowledge is
unified. The UI shows that same structure. The current lab layout is provisional
guidance for this, not a final decision
([01-collaborative-wiki.md](01-collaborative-wiki.md)).

## Softmax integration
Tight integration via tooling and UI: easy querying and downloading of episodes,
replays, logs, and other artifacts; easy replay integration, likely with
coworld-specific aspects. In phase 1, replay viewing is a link out to the
Observatory's viewer, and the sketch for evidence is to reference it by content
hash and platform identifiers
([02-experiment-lifecycle.md](02-experiment-lifecycle.md)). Publishing to
a coworld's public forum and wiki is controlled by the `do-not-publish` tag
([09-tags-and-policy-versions.md](09-tags-and-policy-versions.md)).

## What is designed and what is not
Settled: CAOS as the substrate, the budgeting system, the Manager as the single
meta-agent, and one Scientist to start. Everything else under Components is a
requirement with a sentence under it. The CAOS work, and later a look at what other harnesses do
that is worth borrowing ([07-research-plan.md](07-research-plan.md), area 2),
flesh them out.
