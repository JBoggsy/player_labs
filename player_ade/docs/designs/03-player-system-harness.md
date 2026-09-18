# The player system and its harness

The "player" is a complete system, not one agent. It is an upgraded, expanded
version of the current lab turned into a complete harness, with elements of
projects like paperclip and gastown where sub-agents handle different tasks.

The user has flagged this area as the most under-specified, and asked that the
first step be research: synthesize the state of the art and proven solutions
(paperclip, gastown, Metta-AI's `cogamer` and `co-gas`, research papers), then
customize together. See the [research plan](07-research-plan.md). The list below
records the components the user is currently thinking about.

## Components

### Scheduled autonomous agents
Woken at regular intervals with specific instruction files, skills, and tools.
They handle regular tasks that need consistent effort and no user intervention:
knowledge maintenance, forum/wiki interactions on Softmax, experiment monitoring.

### Triggered autonomous agents
Woken when some event happens, or when the user asks. Each has a fixed job with
custom instructions, skills, and tools. Example chain given by the user: when an
idea (topic) is created or updated, a hypothesizer agent is spun up to generate
hypotheses for it; then an experimenter agent is spun up for each hypothesis. So
creating an idea immediately leads to agents working on it.

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

### Spend and observability
Tools that give the user insight into which agents are spending how much and why,
what agents are doing, and so on.

### Skills and tools
Like what the lab has now, but expanded and upgraded: tools and skills for
interacting with the Observatory in many ways, and for each task and each agent
the system uses.

### Meta-agent
An agent for creating new agents and modifying the harness itself. (Its
relationship to the Manager agent in [04-agents.md](04-agents.md) is open:
[Q17](05-open-questions.md).)

### Interop with both Claude Code and Codex
The system must work with both.

## Per-coworld labs, mirrored in the UI
Coworld-specific knowledge stays separated per lab; coworld-agnostic knowledge is
unified. The UI shows that same structure.

## Softmax integration
Tight integration via tooling and UI: easy querying and downloading of episodes,
replays, logs, and other artifacts; easy replay integration, likely with
coworld-specific aspects.

## Recorded, not yet decided
Almost every component above is a heading with a sentence under it. The user has
said these are underspecified in their head right now and expects research into
the state of the art to flesh them out. Questions that must be answered before the
harness can be designed in detail are in [05-open-questions.md](05-open-questions.md)
(Q14–Q22).
