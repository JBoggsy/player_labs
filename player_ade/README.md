# player_ade — Player Agentic Development Environment

`player_ade` is the home for designing and building a web-UI-based, multi-agent
development environment on top of this lab. Everything for that project lives
here: design documents, plans, working knowledge, and (later) implemented code.

**Status (as of 2026-10-05):** the high-level design is recorded. Nothing is
implemented yet. The questions still open are in
[open questions](docs/designs/05-open-questions.md). The first task is understanding and standing up CAOS, the substrate the system
is built on ([research plan](docs/designs/07-research-plan.md), area 4).

**Phase 1:** a local, single-user web app piloted on the Gods of the Arena lab:
a wiki UI, an experiment-pipeline UI, and one general-purpose interactive agent
running in the CAOS harness. See [phasing](docs/designs/08-phasing.md).

## Terms used throughout

- **User** — the human (James) who sets direction, judges gameplay quality, and
  collaborates with the agent system.
- **Player** — the whole coding-agent-powered system that develops policies. It is
  a *system* (many agents, skills, tools, and a knowledge base), not one agent.
- **Policy** — the game-playing program that gets built, uploaded, and evaluated on
  Softmax. "Policy" is the word for this artifact and "player" is reserved for
  the agent system. The rest of the repo still calls the artifact a "player";
  unifying that terminology across the repo is a recorded task in the root
  [`TODO.md`](../TODO.md). Two other things are also called players elsewhere
  and are named differently here: the Softmax platform's own "player" (the
  competitor identity an account uploads under) is a **platform player**, and
  the other competitors in a league are **entrants**.
- **Experience request** — a batch of hosted evaluation games that the player
  asks Softmax to run for a policy version. It spends credits from a
  replenishing allowance and is the lab's main way of measuring a policy.
- **Coworld** — one game on the Softmax Observatory platform. Each has its own lab
  directory in this repo (`crewrift_lab/`, `gods_of_the_arena_lab/`, ...).
- **Wiki** — the shared knowledge base of markdown pages that both the user and
  the player read and edit.
- **Pipeline** — the idea and experiment lifecycle: topics, hypotheses,
  experiments, and results.
- **CAOS** — the Content-Addressable Operating System Softmax is developing
  ([Metta-AI/caos](https://github.com/Metta-AI/caos)). Files and the actions
  taken on them are hashed, so every change and every action is accounted for.
  It is the history system and the agent harness for this project.

## Documents

| Document | What it covers |
| --- | --- |
| [Vision and goals](docs/designs/00-vision-and-goals.md) | Why this project exists, the three aims, the major components, the foundation |
| [Collaborative wiki](docs/designs/01-collaborative-wiki.md) | Shared knowledge base: page format, mutual editing, comments, history, notifications, strategy documents |
| [Idea and experiment lifecycle](docs/designs/02-experiment-lifecycle.md) | Topics, hypotheses, experiments, and results: their shape, states, evidence, and how the user works with them |
| [Player system and harness](docs/designs/03-player-system-harness.md) | CAOS as the substrate; scheduled, triggered, and invoked agents; messaging; budgets; the Manager |
| [Agents](docs/designs/04-agents.md) | What an agent is, the agent taxonomy, and the initial roster |
| [Open questions](docs/designs/05-open-questions.md) | Numbered questions for the user, each with the context needed to answer it |
| [Comparison to the current lab](docs/designs/06-comparison-to-current-lab.md) | What the lab has today versus what the design asks for, and how the design closes each gap |
| [Research plan](docs/designs/07-research-plan.md) | What must be learned before detailed design: CAOS, agentic memory, other harnesses |
| [Phasing](docs/designs/08-phasing.md) | Phase 1 scope, its decisions, the phase-1 agent, and what is deferred |
| [Tags and policy versions](docs/designs/09-tags-and-policy-versions.md) | Tagging any object, publishing control, and the tree of policy versions |

A first-time reader should take them in this order: vision (00), phasing (08),
wiki (01), pipeline (02), tags and versions (09), harness (03), agents (04),
research plan (07), comparison (06), open questions (05).

The originating prompt is [`prompts/high-level-design.prompt.md`](prompts/high-level-design.prompt.md).

## How these documents are written

- The user is the designer. The agent's role is scribe: record, organize, and ask.
  Nothing in these documents is the agent's own design decision unless labeled as a
  recorded suggestion awaiting the user's call.
- Plain language over jargon. Precision and clarity over concision.
- Open questions are numbered `Q1`, `Q2`, ... and collected in one place. When a
  question is answered, the answer is folded into the relevant document and the
  question is removed from the list. Numbers are stable identifiers: a removed
  question's number is never reused, so gaps in the sequence are expected.
- These are living documents that describe the design as it stands. Replace
  superseded content in place. Do not keep decision dates, rejected alternatives,
  or a change history inside them (git has it).
