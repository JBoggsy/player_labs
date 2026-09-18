# player_ade — Player Agentic Development Environment

`player_ade` is the home for designing and building a web-UI-based, multi-agent
development environment on top of this lab. Everything for that project lives
here: design documents, plans, working knowledge, and (later) implemented code.

**Status:** high-level design in progress. Nothing here is implemented yet.
**Phase 1** (decided 2026-09-17): web UI for the wiki and the experiment pipeline,
plus one general-purpose invokable interactive agent. See [phasing](docs/designs/08-phasing.md).

## Terms used throughout

- **User** — the human (James) who sets direction, judges gameplay quality, and
  collaborates with the agent system.
- **Player** — the whole coding-agent-powered system that develops policies. It is
  a *system* (many agents, skills, tools, and a knowledge base), not one agent.
  See [open question Q1](docs/designs/05-open-questions.md) on this name, which
  currently clashes with the lab's use of "player" for the uploaded policy artifact.
- **Policy** — the game-playing program that gets built, uploaded, and evaluated on
  Softmax. (The rest of the lab often calls this a "player"; inside `player_ade`
  we say "policy" to avoid the clash.)
- **Coworld** — one game on the Softmax Observatory platform. Each has its own lab
  directory in this repo (`crewrift_lab/`, `gods_of_the_arena_lab/`, ...).

## Documents

| Document | What it covers |
| --- | --- |
| [Vision and goals](docs/designs/00-vision-and-goals.md) | Why this project exists, the three aims, the major components |
| [Collaborative wiki](docs/designs/01-collaborative-wiki.md) | Shared knowledge base with mutual editing, comments, history, notifications |
| [Idea and experiment lifecycle](docs/designs/02-experiment-lifecycle.md) | Topics → hypotheses → experiments → results/analysis, exposed to the user |
| [Player system and harness](docs/designs/03-player-system-harness.md) | Scheduled/triggered/invoked agents, messaging, spend, meta-agent, Claude Code + Codex |
| [Agents](docs/designs/04-agents.md) | Agent taxonomy and the initial roster (Librarian, Scientist, Strategist, Manager) |
| [Open questions](docs/designs/05-open-questions.md) | Numbered questions for the user, each with the context needed to answer it |
| [Comparison to the current lab](docs/designs/06-comparison-to-current-lab.md) | What the lab already has versus what the design asks for |
| [Research plan](docs/designs/07-research-plan.md) | What needs outside research before detailed design (memory systems, harnesses), plus prior art found locally |
| [Phasing](docs/designs/08-phasing.md) | Phase 1 scope and what it defers |

The originating prompt is [`prompts/high-level-design.prompt.md`](prompts/high-level-design.prompt.md).

## How these documents are written

- The user is the designer. The agent's role is scribe: record, organize, and ask.
  Nothing in these documents is the agent's own design decision unless labeled as a
  recorded suggestion awaiting the user's call.
- Plain language over jargon. Precision and clarity over concision.
- Open questions are numbered `Q1`, `Q2`, ... and collected in one place. When a
  question is answered, the answer is folded into the relevant document and the
  question is removed from the list.
- These are living documents. Replace superseded content in place; do not keep a
  change history inside them (git has it).
