# Agents in the system

## What an agent is

An agent is really just a particular **instruction file** (`AGENTS.md` /
`CLAUDE.md`) plus a set of **tools, skills, and knowledge**. Whether it runs
autonomously or interactively, and how it was started, dictate *some* of its
instructions but not most. For example, an agent started autonomously might have
the same instructions as the same agent started interactively, plus additional
instructions for operating with minimal human interaction.

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

## Initial roster (examples, not a complete list)

| Agent | Mode | Responsibility |
| --- | --- | --- |
| **Librarian** | Mostly autonomous, scheduled; also triggered by user wiki edits | Ensure all knowledge about the coworld is accurate and up to date. Manage the wiki: keep it clean and well organized, respond to user changes. |
| **Scientist** | Autonomous, triggered by new/updated topics and hypotheses | Generate hypotheses, run experiments, and analyze results for ideas in the experiment pipeline. |
| **Strategist** | (not yet specified) | Generate strategy ideas for policies; interpret other players' strategies from their policies' actions. |
| **Manager** | (not yet specified) | Manage, improve, and even "hire" other agents. Set responsibilities, goals, and expectations for other agents; evaluate their performance; work with the user to improve them. |

The user expects this list is incomplete and that some of these roles may prove
too big and be split into smaller ones. In the user's triggered-agent example, the
Scientist's job is described as two agents: a **hypothesizer** (one per topic) and
an **experimenter** (one per hypothesis). Whether that split is intended or just
illustrative is [Q16](05-open-questions.md).
