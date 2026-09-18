# Open questions

Numbered questions for the user. Each gives the context needed to answer it. When
a question is answered, fold the answer into the relevant design document and
delete the question here. Questions are grouped by what they block; phase-1
questions ([08-phasing.md](08-phasing.md)) come first.

Where a question lists options, the options are there to make the decision
concrete, not to steer it. Nothing is chosen until the user chooses.

---

## Blocks phase 1: naming and scope

**Q1. The word "player".** In the rest of this repo, "player" means the policy
artifact that gets uploaded to Softmax (the "player image", `player-build.md`,
"Coworld player"). The design prompt uses "player" for the agent *system*. Both
meanings will appear on the same UI screens ("the player uploaded player v12").
Keep "player" for the agent system and rename the artifact to "policy" everywhere
in `player_ade`, or pick a different word for the agent system?

*Answer:* Use the word player to mean the complete system and use "policy" for the artifact uploaded to the observatory. We should unify this terminology across this repo.

**Q2. Where the UI runs, and for whom.** Is phase 1 a local app on this Mac, used
by one person, with no login? Or does it need to be reachable from other machines
or by other people? This decides whether authentication, hosting, and multi-user
concerns exist at all in phase 1.

*Answer:* Phase 1 is a local app, though eventually we'll probably want to grow it. But don't worry about anything like that now, just don't close the door on it either.

**Q3. Pilot game.** Which coworld lab is the first one the wiki and pipeline UI are
built against? The Gods of the Arena lab is the most active recently and already
has a `docs/wiki/` directory; Crewrift has the most tooling. Picking one keeps
phase 1 small.

*Answer:* Gods of the Arena will be the pilot game.

---

## Blocks phase 1: wiki storage and format

**Q4. Page format.** Three options were named in the prompt. The practical
difference is who can edit the source directly:

| Option | Source of truth | Agent edits how | User edits how | Figures |
| --- | --- | --- | --- | --- |
| (a) Plain `.md` + image files | `.md` files | Normal file edits | Text editor in the UI, saved back to `.md` | Only as image files |
| (b) HTML rendered from `.md` (like the current report skills) | `.md` files, HTML is a build output | Normal file edits, then re-render | Must edit the `.md`, not the HTML | Anything HTML can show; charts can be live |
| (c) Templated wiki renderer over `.md` | `.md` files, rendered on the fly by the UI | Normal file edits | Editor in the UI, saved back to `.md` | Whatever the renderer supports (images, tables, diagrams from text like Mermaid, charts from data files) |

All three keep markdown as the thing the agent edits. Which one, or a mix (for
example (c) for wiki pages and (b) for generated reports embedded in them)?

*Answer:* (c) sounds like the right answer to me. We can start with a basic rendered that includes images and Mermaid diagrams, then maybe extend it as we go. I'd like more support for figures than just plain images, and (c) offers a path for extending support as new needs come up. The templating system should start off simple, though.

**Q5. Where the wiki files live.** Options: (i) each lab's existing docs become
that lab's wiki (Gods of the Arena already has `gods_of_the_arena_lab/docs/wiki/`),
with the repo-root docs as the shared wiki; (ii) a new wiki tree under
`player_ade/` with per-lab sub-trees, leaving the existing lab docs alone; (iii)
something else. Related: should the nine existing labs' documents be migrated
into the wiki, or does phase 1 start with only the pilot game and migrate later?

*Answer:* I think we structure the wikis under the `docs/` of each game's lab, withthe root docs as the shared wiki. The navigation between wikis can still be done because links can span folders. I think this touches on a broader question about organization of the labs in PlayerADE, if only because I want that structure to be genuinely thought out and not just adopted-by-default from the current lab structure. I do think the current lab structure mostly makes sense, but we may end up wanting to more rigorously define what a coworld lab looks like, have mechanisms for instaniating new labs in a uniform way, etc. I bring this up not to say that we must design those features now, but to make sure it's clear that the current structure is provisional guidance, not a final say. Indeed, I think the pilot GOTA lab will teach us a lot about the kind of structure we want. For now, just use the GOTA lab, don't worry about the other labs. 

**Q6. How the phase-1 agent learns about user edits and comments.** With no
background Librarian yet, the user's edits and comments sit until the interactive
agent is next started. How should it find them? For example: a start-of-session
briefing that lists unseen edits and open comments; an "inbox" page the agent is
instructed to read; or the user explicitly asks the agent to look. Also: should
the agent mark a comment as seen/handled, and can the agent leave comments on the
user's text as well?

*Answer:* Let's answer the second part first: the agent an comment on the user's text and can reply to comments (and the user can reply to agent comments), and we should allow the agent to mark comments as resolved, but part of it's instructions should be to only mark its own comments resolved unless the user specifically asks. In terms of finding the edits, I think edit diffs should be stored in a changelog that builds up until the agent specifically marks them as read. The agent's instructions should include a clear pointer to the change logs and instructions for how to read/mark them as read, but nothing else. The user should be the driver of that interaction for now. Another thing that will be helpful to the agent is that files which link to or are linked from a changed page should maybe have some marker so the agent knows a related page has unread changes. That way the agent at least gets a warning that the information it's reading might be out of date, since a related page was changed.

**Q7. Strategy pages driving code, forward direction.** The rule is "changes to
the strategy `.md` must directly result in corresponding changes to the policy
code." In phase 1 with one interactive agent, what does "directly" mean? For
example: the UI shows a "strategy changed, code not yet updated" flag until the
agent is invoked and reconciles them; or the user invokes the agent with a
one-click "sync code to strategy" action. And given the lab's speed preference
(upload without pre-checks), does the user want to review the code change before
it is uploaded when it came from a strategy edit, or should it go straight to
rebuild and upload?

*Answer:* I think right now this should mostly be in the agent's instructions and a changelog-type thing similar to the wiki pages. The agent should have instructions that the strategy `.md` (or `.md`*s*, there may be a collection of them) are the true policy description and the code is a "compiled" version of that polict description, where the compilation process is the coding agent writing/editing the compiled policy code (e.g., the `.bas` in GOTA) based on the strategy markdown(s). Thus, changes to the strategy should first be written into the strategy document(s), then the strategy should be compiled into the uploadable artifact. In addition to these instructions, there should also be an automated system that detects changes to the strategy `.md` file(s) and flags the policy artifact as dirty, and highlights the diffs in the strategy docs so the agent knows exactly what needs to be updated.

**Q8. Strategy pages driving code, reverse direction.** When the agent changes
policy code as part of an experiment, must it update the strategy page first
(strategy page is always the leading document), or after (strategy page is kept
in sync but code can lead during experiments), or only when an experiment's
change is adopted permanently?

*Answer:* Following on the previous answer, the agent should alter the strategy documents first, then "compile" them into policy code. It's likely we'll update and improve this process as we go; I already think that part of the compilation process will need to involve refining the policy code multiple times until it works well, and such refinements might not warrant a change to the strategy docs. We'll need to find the right balance and tooling to make this work well. The ultimate objective is to have the policy's strategy, tactics, and mechanics described in natural language as a sort of contract between player and user, and to allow easy, natural refinement of the overall policy through natural language, and to separate those from the implementation details and the tuning, parameterization, and refining of code. 

**Q9. Edit history mechanism.** The repo is already in git, and git can attribute
each commit to "user" or "agent" and produce a diff-based change log. Is git the
history store for the wiki and pipeline entities, with the UI committing the
user's edits automatically? Or does the user want a separate history store (a
database) so wiki history is independent of code commits?

**Q10. Comments.** Are comments threaded (replies under a comment) and resolvable
(marked done)? Who may resolve: user only, or the agent when it believes it has
addressed the comment? Where are comments stored: alongside the page (a sidecar
file), in the page as annotations, or in a database?

**Q11. Notifications in phase 1.** Is an in-UI change log and unread indicator
enough for phase 1, or does the user also want out-of-app notification (for
example the Discord DM channel the token broker already uses) when the agent
changes something?

---

## Blocks phase 1: experiment pipeline

**Q12. Hierarchy shape.** The prompt says a hypothesis addresses "one or more
topics", which makes topic→hypothesis many-to-many rather than a strict tree.
Experiments are described as belonging to exactly one hypothesis. Confirm: topics
↔ hypotheses many-to-many; hypothesis → experiments one-to-many; experiment →
results one-to-one (or one-to-many if an experiment is re-run)?

**Q13. Lifecycle states.** The UI needs a state for each entity so the user can
see what is proposed, in progress, and finished. The prompt names
proposal → implementation → execution for experiments, and the two analysis
outcomes (invalid experiment; hypothesis falsified or not). Please confirm or
correct a state list for each entity. A candidate to react to:
- Topic: open, closed (with a reason: resolved, abandoned, merged into another).
- Hypothesis: proposed, under test, supported, falsified, abandoned.
- Experiment: proposed, implementing, running, analyzed, invalid.
Should the user be able to set states (for example, closing a topic), or only the
agent, or both with attribution?

**Q14. Approval before spending.** The lab's standing preference is that the
agent creates hosted experience requests without asking. In the pipeline, an
experiment consumes credits when it runs. Should an experiment carry an explicit
"approved to run" step the user must take in the UI, or does the standing
preference hold (the agent runs experiments it proposes, and the user intervenes
by commenting or changing state)?

**Q15. Evidence storage and replay viewing.** Episode artifacts (replays, logs,
result files) are large and already downloaded into per-episode directories by
the existing artifacts skill. Should an experiment's results page copy artifacts
under the experiment, or reference them where they already are (local path plus
the Observatory URL)? And is replay viewing inside the UI a phase-1 requirement,
or is a link to the Observatory's replay viewer enough for now?

**Q16. Existing lab records.** The lab currently keeps `WORKING_CONTEXT.md`
(active objective and next decision) and `TENTATIVE_LESSONS.md` (candidate
guidance awaiting evidence) per lab, plus `best_practices.md` and
`user_preferences.md` at the root. Do these become wiki pages (and if so, does
`TENTATIVE_LESSONS.md` become something in the pipeline, since its entries are
effectively hypotheses)? Or do they stay as they are, outside the wiki?

---

## Blocks phase 1: the interactive agent

**Q17. How the agent runs inside the UI.** Two broad approaches:
- **Embedded terminal** running the real Claude Code CLI (and Codex CLI) in a
  browser terminal. Cheapest to build; every existing skill, hook, and
  permission prompt works unchanged; the UI mostly adds "start a session in this
  lab with this context". Looks like a terminal, not a chat.
- **Custom chat UI** built on the Claude Agent SDK (and Codex's equivalent). The
  UI can render tool calls, show wiki pages the agent is editing, and link
  messages to entities. Much more to build, and permission prompts, skills, and
  hooks must be re-plumbed.
Which does the user want for phase 1? And must Codex be supported in phase 1, or
is Claude Code alone acceptable to start?

**Q18. What "general-purpose" includes.** Is the phase-1 agent the current lab
agent (this repo's `AGENTS.md`, skills, and preferences) plus new instructions
for reading and writing wiki pages and pipeline entities? Or a fresh instruction
file written for the UI? The first is faster and keeps the existing loop intact.

---

## Not blocking phase 1: research and later phases

**Q19. When to do the research.** The prompt asks for research into agentic
memory systems (for the wiki) and agent harnesses (for the player system). The
harness research is a later-phase concern now. The memory-system research could
still affect how phase 1 lays out and indexes the wiki. Do that research before
finalizing the phase-1 wiki design, or start with "markdown plus an index file"
as the prompt suggests and research later? Also: is research area 3 in
[07-research-plan.md](07-research-plan.md) (existing tools for commenting and
editing markdown collaboratively) wanted?

**Q20. Manager versus meta-agent.** The harness document lists "a meta-agent for
creating new agents and modifying the harness itself"; the agents document lists a
Manager that "hires" and improves other agents. Same agent or two?

**Q21. Scientist split.** The triggered-agent example describes a hypothesizer
(one per topic) and an experimenter (one per hypothesis), while the roster names a
single Scientist. Is the split intended, or illustrative?

**Q22. The Strategist and opposition research.** The Strategist "interprets the
strategies of other players from their policies' actions." The user preference
file says gameplay-mechanics discoveries are proprietary until released, and
competitor intelligence must come only from ordinary access. Does that same rule
apply to what the Strategist writes into the wiki, and should the UI mark pages
as "do not publish"?

---

## Surfaced by the comparison to the current lab

**Q23. The "no archives" rule versus a browsable pipeline history.** Four
authoritative lab documents (`docs/learning.md`, `best_practices.md`,
`user_preferences.md`) say to remove historical reports, version logs, and change
narratives and never to recreate an archive. The proposed UI exists to show past
and current topics, hypotheses, experiments, and results, which is an archive.
The two cannot both hold. Options: (i) exempt the pipeline store and wiki history
from the rule (the rule keeps applying to prose docs such as `WORKING_CONTEXT.md`
and `best_practices.md`, which must stay current-state only); (ii) amend the rule
itself; (iii) keep the rule and have the UI show only *current* entities, with
closed ones deleted. Which?

**Q24. Idea-first versus evidence-first.** The lab's loop starts with evaluation
(run episodes, diagnose, then the human sets direction). The proposed pipeline
starts with a topic. Both can coexist (an evaluation produces topics), but the UI
needs a home for "evidence that has not yet become a topic": survey reports, mined
hypothesis lists, field studies. Is that a wiki page type, a pipeline entity of
its own (for example "observation" or "finding"), or attached to a topic as its
motivation?

**Q25. Post-run validity as a separate outcome.** Today's experiment verdict is
`confirmed | refuted | inconclusive`, and a run that turned out to test the wrong
thing is filed as `inconclusive`. The proposal wants "the experiment was invalid"
recorded separately from "the hypothesis is undecided". Confirm that the experiment
record should gain an explicit validity outcome (for example
`valid | invalid`, with a reason) alongside the hypothesis verdict, and that an
invalid experiment leaves the hypothesis's own state unchanged.
