# Research plan

The user asked that two areas be researched against the current state of the art
and proven solutions before their detailed design is written. This document lists
what to research and what each piece of research must answer. It is a plan, not
the research itself. Whether to do this research now or in a later session is
[Q23](05-open-questions.md).

## 1. Agentic memory and knowledge systems (for the player-side wiki)

Goal: decide how the player stores, indexes, retrieves, and maintains its
knowledge so that the right pages reach an agent at the right time.

Questions the research must answer:
- What do current agent memory systems do beyond "a directory of markdown plus an
  index file"? (Hierarchical indexes, embeddings/search, memory consolidation
  passes, typed memories, recency and decay.)
- Which of those techniques work with the constraint that the files must also be
  human-readable and human-editable wiki pages?
- How do they handle two writers (human and agent) editing the same store?
- What is the simplest thing that works, and what would force an upgrade later?

Method: web search for current systems, papers, and popular open-source
implementations; read what Claude Code and Codex themselves do for memory.

## 2. Multi-agent harnesses (for the player system)

Goal: choose or adapt a harness for scheduled, triggered, and invoked agents with
inter-agent messaging, spend tracking, and a web UI, supporting Claude Code and Codex.

Sources named by the user:
- **paperclip** and **gastown** (open source).
- Metta-AI repos: **cogamer** and **co-gas** ("extensive repos with a proven
  track record"), plus possibly others in the Metta-AI org.
- Research papers on agent harnesses.

Questions the research must answer, for each candidate:
- How are agents defined? (Instruction file + tools + skills, or something richer?)
- How are they scheduled and triggered? What event sources exist?
- How do agents talk to each other and to the human?
- What does the web UI show, and can it host interactive sessions?
- How is cost tracked and limited?
- Does it support Claude Code and Codex, or one, or neither?
- Persistence model; what runs where (local machine vs server).
- Maturity, maintenance health, license.

Output: a comparison with a recommendation for what to adopt versus build, per the
user's standing rule to prefer existing, well-supported solutions over hand-rolled
ones and to say explicitly why the alternatives lose.

## 3. Collaborative editing and commenting on markdown (for the user-side wiki)

Not named by the user but implied by requirements 1–5 in
[01-collaborative-wiki.md](01-collaborative-wiki.md): existing tools for rendering
a markdown tree as a wiki, with text-anchored comments, per-edit attribution, and
change notifications. To be confirmed as in scope ([Q23](05-open-questions.md)).

## Prior art already on this machine (surveyed 2026-09-17, read-only)

A quick read-only survey of `~/coding` found the following. These are starting
points for research area 2, not conclusions.

| Project | Where | What it is, in brief |
| --- | --- | --- |
| **cogamer** (daveey's playbook repo) | `~/coding/optim-compare/repos/cogamer` | The closest precedent. A fleet of Anthropic managed cloud agents coordinated through an **Asana board as the work queue**. Agents are game-agnostic markdown role prompts (`fleet/prompts/*.md`: worker, ideation, analyst, scout, redteam, librarian, fleet-steward, orchestrator, round-steward, sub-builder, sub-critic, ...) bound to a campaign by a preamble pointing at one game-truth doc (`CAMPAIGN.md`). Shared protocols in `fleet/PROTOCOLS.md`. Scheduling is cron: each run claims at most one task, works it in a fresh context, exits. A single-file FastAPI web UI ("Mission Control") shows board, heartbeats, experiment queue, ledger, and chat with the orchestrator. Git is the scientific record; Asana is workflow state. Read first: `README.md`, `AGENTS.md`, `fleet/README.md`, `docs/asana-fleet/README.md`. |
| **co-gas** (Relh's repo) | `~/coding/optim-compare/repos/co-gas` | A **single-agent standing-mandate harness**, not a fleet. `AGENTS.md` carries the mandate and rules; a Python CLI (`co-gas mandate ...`, `campaign ...`, `schema ...`) renders bounded command batches for an agent to run. No web UI, no scheduler. Git-native evidence records (`experiments/candidates/*.yaml`), a `FAILED_EXPERIMENTS_DO_NOT_REPEAT.md`, and a hash-pinned "executable world model" with source custody. Read first: `README.md`, `AGENTS.md`, `docs/coworld-tournament-playbook.md`. |
| **cogamer** (the Metta package, a different thing) | `~/coding/metta-reporter-runtime/packages/cogamer` and `cogamer-api` (June 2026 checkout; removed from current metta `main`) | A hosted control plane for autonomous Claude Code agents: FastAPI on Lambda, DynamoDB state, agents run as ECS tasks, one GitHub repo per agent. Docs under `packages/cogamer/docs/`. Relevant as a "run agents somewhere other than this Mac" reference. |
| **paperclip**, **gastown** | not checked out | Need to be fetched or read online. |
| Metta `agent-plugins` | `~/coding/metta/agent-plugins` | Skill/prompt distribution for Claude Code, Codex, Cursor. Not a scheduler or UI, but the natural place for shared skills. |
| Metta `packages/antfarm` | `~/coding/metta/packages/antfarm` | An actor orchestration layer (Cloudflare Durable Objects) currently scoped to running episodes and policies, not coding agents. |

Nothing in current metta `main` is a multi-agent scheduler with a web UI; the
cogamer Mission Control plus Asana fleet is the real local precedent.
