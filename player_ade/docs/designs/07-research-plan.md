# Research plan

What has to be learned before the detailed design is written. This document
lists what to research and what each piece of research must answer. It is a
plan; it also records the starting facts already established, each with the
date it was checked.

**Order:**

1. **CAOS** (area 4 below) first. It is the first phase-1 task, because the
   history system and the agent harness both rest on it.
2. **Agentic memory** (area 1) next, before the wiki's indexing and retrieval
   are designed.
3. **Other multi-agent harnesses** (area 2) later, when the autonomous agents
   are designed.

Area 3 is not design research; it is a check made when the UI is built.

## 1. Agentic memory and knowledge systems (for the player-side wiki)

Goal: decide how the player indexes, retrieves, and maintains its knowledge so
that the right pages reach an agent at the right time. The page format and
location are already decided ([01-collaborative-wiki.md](01-collaborative-wiki.md));
this research shapes what is layered on top.

Questions the research must answer:
- What do current agent memory systems do beyond "a directory of markdown plus an
  index file"? (Hierarchical indexes, embeddings/search, memory consolidation
  passes, typed memories, recency and decay.)
- Which of those techniques work with the constraint that the files must also be
  human-readable and human-editable wiki pages?
- How do they handle two writers (human and agent) editing the same store?
- What is the simplest thing that works, and what would force an upgrade later?
- What does CAOS already provide here? (`caos-prime` gives its agent a memory
  directory.)

Method: web search for current systems, papers, and popular open-source
implementations; read what Claude Code and Codex themselves do for memory.

## 2. Multi-agent harnesses (for the later-phase agents)

Goal: with CAOS as the substrate, learn what other harnesses do that
`caos-prime` does not, and whether it is worth borrowing for the scheduled and
triggered agents and their roster.

Sources named by the user:
- **paperclip** and **gastown** (open source).
- Metta-AI repos: **cogamer** and **co-gas** ("extensive repos with a proven
  track record"), plus possibly others in the Metta-AI org.
- Research papers on agent harnesses.

Questions the research must answer, for each:
- How are agents defined? (Instruction file + tools + skills, or something richer?)
- How are they scheduled and triggered? What event sources exist?
- How do agents talk to each other and to the human?
- What does the web UI show, and can it host interactive sessions?
- How is cost tracked and limited?
- Persistence model; what runs where (local machine vs server).
- Maturity, maintenance health, license.

Output: a comparison that says what to borrow and what to build, preferring
existing, well-supported solutions over hand-rolled ones and saying explicitly
why the alternatives lose.

### Prior art surveyed

Starting points for this area. The paths are on the user's Mac (checked
2026-09-17); on the Linux workstation only the metta checkout is present, at
`~/Coding/softmax/metta`.

| Project | Where | What it is, in brief |
| --- | --- | --- |
| **cogamer** (daveey's playbook repo) | `~/coding/optim-compare/repos/cogamer` | The closest precedent for a fleet. Anthropic managed cloud agents coordinated through an **Asana board as the work queue**. Agents are game-agnostic markdown role prompts (`fleet/prompts/*.md`: worker, ideation, analyst, scout, redteam, librarian, fleet-steward, orchestrator, round-steward, sub-builder, sub-critic, ...) bound to a campaign by a preamble pointing at one game-truth doc (`CAMPAIGN.md`). Shared protocols in `fleet/PROTOCOLS.md`. Scheduling is cron: each run claims at most one task, works it in a fresh context, exits. A single-file FastAPI web UI ("Mission Control") shows board, heartbeats, experiment queue, ledger, and chat with the orchestrator. Git is the scientific record; Asana is workflow state. Read first: `README.md`, `AGENTS.md`, `fleet/README.md`, `docs/asana-fleet/README.md`. |
| **co-gas** (Relh's repo) | `~/coding/optim-compare/repos/co-gas` | A **single-agent standing-mandate harness**, not a fleet. `AGENTS.md` carries the mandate and rules; a Python CLI (`co-gas mandate ...`, `campaign ...`, `schema ...`) renders bounded command batches for an agent to run. No web UI, no scheduler. Git-native evidence records (`experiments/candidates/*.yaml`), a `FAILED_EXPERIMENTS_DO_NOT_REPEAT.md`, and a hash-pinned "executable world model" with source custody. Read first: `README.md`, `AGENTS.md`, `docs/coworld-tournament-playbook.md`. |
| **cogamer** (the Metta package, a different thing) | `~/coding/metta-reporter-runtime/packages/cogamer` and `cogamer-api` (a June 2026 checkout; the package is not in current metta `main`) | A hosted control plane for autonomous Claude Code agents: FastAPI on Lambda, DynamoDB state, agents run as ECS tasks, one GitHub repo per agent. Docs under `packages/cogamer/docs/`. A reference for running agents somewhere other than the user's own machine. |
| **paperclip**, **gastown** | not checked out | Need to be fetched or read online. |
| Metta `agent-plugins` | `agent-plugins/` in the metta checkout | Skill and prompt distribution for Claude Code, Codex, Cursor. Not a scheduler or UI, but the natural place for shared skills. |
| Metta `packages/antfarm` | `packages/antfarm/` in the metta checkout | An actor orchestration layer (Cloudflare Durable Objects) scoped to running episodes and policies, not coding agents. |

## 3. Existing components for the wiki UI (a build-time check)

When the UI is built: is there an existing markdown wiki renderer, editor
component, or text-anchoring library worth using instead of writing one? The
renderer, the comments file, and in-app notifications are already decided
([01-collaborative-wiki.md](01-collaborative-wiki.md)), so this is a choice of
parts, not of design.

## 4. CAOS as the history system and the agent harness

**CAOS** (Content-Addressable Operating System), which Softmax is developing, is
the substrate from the outset: the history system for the wiki and for
everything the player does, and the harness the phase-1 agent runs in. The
premise: files and the programs, functions, and tool calls that act on them are
all hashable, so every change and every action is accounted for. The system is
a work in progress and the user does not fully understand it yet; the user and
the scribe work through it together.

What exists (checked 2026-09-23, read-only):

- [Metta-AI/caos](https://github.com/Metta-AI/caos) (public, active). In its own
  words: "functional programming with git as the values and docker as the
  functions, cached by redis." A server holds a content-addressed store and runs
  compute; workers are containers that receive inputs as git objects and stage
  results back into git without committing to the main repo; each input-to-output
  mapping is cached and reused. It ships an agent harness (bounded bash,
  stateless LLM calls, durable LLM turns, recursive grep, a chat protocol in
  `design/chat.md`) and Claude Code integration (`integrations/claude-code/`).
  Prerequisites: Nix with flakes, Docker.
- [Metta-AI/caos-session](https://github.com/Metta-AI/caos-session) (public): the
  starting tree for an agent session that works through caos; the target repo is
  imported into the conversation rather than cloned.
- [Metta-AI/caos-prime](https://github.com/Metta-AI/caos-prime) (private): "a
  self-improving agent harness on a content-addressed substrate" with persistent
  sub-agents, a mode that runs it unattended on a timer, a refine loop that reviews and
  rewrites the harness, and a terminal agent dashboard. Design and build plan in
  its `design/prime-agent.md`.
- The `~/Coding/softmax/metta` checkout on the Linux workstation carries a
  `.caos-expr` pin, so the metta repo is itself worked through caos.
- On the Linux workstation (checked 2026-10-05): Docker is installed; Nix is
  not; no caos binaries are installed.

The scribe's expectations, to be confirmed or corrected by this research; none
of these is a decision:

- The phase-1 agent runs in the agent harness the `caos` repository ships (its
  workers that run one model turn at a time, and its chat protocol), and the web
  UI connects to an agent as a client of that protocol.
- Every agent turn and tool call is then a hashed, recorded job, and the
  agent's instruction set is itself a versioned object.
- `caos-prime` is the natural basis for the later-phase agents and for the
  Manager.
- The strategy, source, and artifact that a policy version pins can be captured
  as content hashes at upload, with no commit needed.

Questions this research must answer:
- What is the unit of history in CAOS (a commit, an object, a job), and how does
  a wiki edit by the user or the player become one? How is attribution recorded?
- Can the app read history, diffs, and "who changed what" from CAOS cheaply
  enough to drive the changelog, the related-page markers, and the strategy
  dirty flag?
- Where do the app's own records (changelog read-state, comments, pipeline
  entities, the evidence database, policy version records) live: in CAOS
  objects, or beside them?
- How does CAOS's content addressing meet the evidence design (results
  referencing evidence by digest) and the policy version tree (strategy, source,
  and artifact pinned by hash at upload)?
- What is the phase-1 agent inside CAOS: Claude Code running through CAOS's
  Claude Code integration, or an agent built from CAOS's own workers? Do the
  lab's Claude Code skills, hooks, and instructions carry over, or are they
  ported? What does a web UI need in order to connect to a running agent? Where
  does Codex fit?
- How mature is it today and what is the setup cost (Nix with flakes, Docker,
  and CAOS's own server stack running locally)? Which parts are ready to build
  on now and which need to be built or wait on Softmax?

Method: read the caos `README.md`, `design/` directory, and the Claude Code
integration; read caos-prime's `design/prime-agent.md`; bring the CAOS stack up
locally (its `caosd up` command); then discuss with the user.
