# Agents in the system

## What an agent is

An agent is really just a particular **instruction file** (an `AGENTS.md` or
`CLAUDE.md`) plus a set of **tools, skills, and knowledge**. Whether it runs autonomously or interactively, and how
it was started, dictate *some* of its instructions but not most. For example, an
agent started autonomously might have the same instructions as the same agent
started interactively, plus additional instructions for operating with minimal
human interaction.

## Terms

- **Autonomous vs interactive.** An autonomous agent largely acts on its own with
  minimal or no human intervention. An interactive agent is driven by interaction
  with the user. *Driving* is the key word: autonomous agents can ask for help and
  ping the user occasionally, but they drive themselves and seek advice only when
  blocked, or in a non-blocking way. Interactive agents are more like typical
  Claude Code or Codex sessions, with instructions and skills tuned to their job.

- **Scheduled.** Woken at regular intervals to do its job. Must at least be capable
  of running autonomously, since it must finish its job without the user being at
  the computer each time it wakes. Good for tasks needing consistent, predictable
  maintenance.

- **Triggered.** Woken by some trigger and responds to it per its instructions,
  skills, and tools. Triggers may be automatic (new opponent policies submitted,
  changes to a coworld, new ideas created) so triggered agents must also be able to
  run autonomously.

- **Invoked.** Specifically started by the user; more likely interactive than the
  others. Apart from the degenerate case of a user manually firing an otherwise
  triggered agent, invoked agents are generally started for an interactive task or
  session.

Most agents will be all of these to some extent.

## Phase 1: one general-purpose agent

Phase 1 has a single invoked, interactive, general-purpose agent and none of the
roster below. Its instructions and briefing are described in
[08-phasing.md](08-phasing.md).

## Initial roster for later phases (examples, not a complete list)

| Agent | Mode | Responsibility |
| --- | --- | --- |
| **Librarian** | Mostly autonomous, scheduled; also triggered by user wiki edits | Ensure all knowledge about the coworld is accurate and up to date. Manage the wiki: keep it clean and well organized, respond to user changes. |
| **Scientist** | Autonomous, triggered by new or updated topics and hypotheses | Generate hypotheses, run experiments, and analyze results for ideas in the experiment pipeline. One Scientist handles all three. |
| **Strategist** | Not yet specified | Generate strategy ideas for policies; interpret other entrants' strategies from their policies' actions. Everything it writes (mechanics findings, opposition research) is **lab-internal by default** and carries the `do-not-publish` tag ([09-tags-and-policy-versions.md](09-tags-and-policy-versions.md)), under the standing rules that gameplay-mechanics discoveries are proprietary until the user releases them and that competitor intelligence comes only from ordinary, non-elevated access. |
| **Manager** | Not yet specified | The meta-agent. Monitors, measures, analyzes, and improves the other agents, the overall player system and its harness, and itself. Manages and even "hires" agents: sets responsibilities, goals, and expectations; evaluates performance; works with the user to improve them; creates new agents and modifies the harness. |

The user expects this list is incomplete and that some of these roles may prove
too big and be split into smaller ones. The Scientist is the first candidate: if
it proves too big it is split, for example into a hypothesizer per topic and an
experimenter per hypothesis.
