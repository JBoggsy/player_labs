# Open questions

Numbered questions for the user. Each gives the context needed to answer it. When
a question is answered, fold the answer into the relevant design document and
delete the question here. Numbers are stable identifiers and are never reused;
the next new question is Q34.

Where a question lists options, the options are there to make the decision
concrete, not to steer it. Nothing is chosen until the user chooses.

---

## Open

**Q28. Which hard gates remain?** The user has said the user is no longer a hard
gate and the player should be more autonomous. Experiments run without a
per-experiment approval, untagged wiki pages are published without a per-write
go-ahead, and only the user can release a `do-not-publish` page. The current
lab guide has other gates that no decision has addressed:

- **League submission.** Today this is "the human's gate": the agent submits a
  policy version to a league only on explicit authorization. Submission is what
  makes a version compete and affects standings; it cannot be undone, though a
  later version can replace it.
- **Git pushes and pull requests.** Today the root guide makes these follow the
  session's explicit permissions. Commits have no lab-wide permission rule,
  though individual campaigns have gated them. With CAOS recording history,
  commits stop being the record of work, which may change what these gates are
  for.
- **Destructive or irreversible actions**: retiring a policy from a league,
  deleting data.

For each: does it stay a hard gate that only the user can pass, become something
the player does and reports, or become something the player proposes and the
user approves in the UI?

**Q29. How much of the budgeting system is in phase 1?** The budgeting system
([03-player-system-harness.md](03-player-system-harness.md)) has two parts.
The LLM-cost part pauses *scheduled* agents at a threshold, and phase 1 has no
scheduled agents, so its pause has nothing to act on yet, though spend could
still be measured and shown to the user. The experience-request part gives the
agent the current credit balance when it is about to make a request, and the
phase-1 agent does make requests. To decide: is showing the credit balance and
its guidance to the phase-1 agent in phase 1, and is measuring LLM spend for
the user in phase 1 or later?

**Q30. The shared root wiki and the other labs during phase 1.** Two decisions
pull against each other. Phase 1 works on the Gods of the Arena lab only and
leaves the other labs alone. But the files being absorbed include root files
that every lab uses: `best_practices.md` and `user_preferences.md` become
shared wiki pages, the root agent guide is replaced by a fresh instruction
file, and ten session-start hooks point agents in every lab at each lab's
`WORKING_CONTEXT.md` and `TENTATIVE_LESSONS.md`. `docs/learning.md`, which
states the old archive rule and says which knowledge goes in which record file,
has no stated fate. To decide:

- Is the shared root wiki (the root `docs/`) part of phase 1, or only the pilot
  lab's wiki?
- When are the root files converted, and do the labs outside the pilot keep
  using the current files and hooks until they are brought in? If so, the root
  files exist in two forms for a while, which the user wanted to avoid.
- What becomes of `docs/learning.md`?
- When is the pilot lab's own migration done: before the UI is usable, or once
  the pipeline has proven itself on new work?

**Q31. The LLM spend threshold: over what period, and whose spend?** Scheduled
agents are paused when LLM spend passes a threshold, starting at $250. Not yet
stated: whether that is $250 per day, per week, per month, or in total until
the user resets it; whether the spend counted is that of all agents or only of
the scheduled ones; and whether the pause is lifted automatically when a new
period starts or only by the user.

**Q32. Is a topic the same thing as an idea?** The user's prompt names the first
pipeline stage "ideation" and speaks of ideas, and names the first entity a
"topic". The documents treat a topic as the recorded form of an idea, so
"creating an idea" and "creating a topic" mean the same act. Confirm, or say
how they differ (for example, an idea being a looser note that may later become
a topic).

**Q33. Do pipeline entities use the wiki page format?** The user's prompt said
the pipeline entities would likely reuse the wiki page format with a different
connective structure. The documents assume they do: each topic, hypothesis,
experiment, and result is a markdown file with tags in front matter and an
optional comments file, edited with the same tools. The tag decision (tags in
front matter) was made on that assumption. Confirm, or say what differs.

---

## Flagged for later work, not questions

- The wording of the experience-request budget guidance given to agents needs
  workshopping, so an agent is budget-aware without being afraid to spend
  ([03-player-system-harness.md](03-player-system-harness.md)).
- The name of the result field currently called "outcome" is provisional
  ([02-experiment-lifecycle.md](02-experiment-lifecycle.md)).
- The guidance telling the player which pages to tag `do-not-publish` has to be
  written ([09-tags-and-policy-versions.md](09-tags-and-policy-versions.md)).

## Left to detailed design

These are not decided and do not need the user yet. Most depend on what the
CAOS work finds ([07-research-plan.md](07-research-plan.md), area 4). Where a
document offers a scribe's suggestion for one of them, it is labeled as such.

- Where pipeline entities, strategy documents, the curated tag list, and the
  restricted-tag configuration live in a lab's file tree, how entities are
  identified, and whether the tag list is per lab or shared.
- Where an entity's structured fields (state, reasons, parent links, game
  version) are kept.
- The exact rules for deriving in-progress states from child entities.
- What the editing tools do to guarantee nothing is lost, and whether the player
  must always use them.
- The format of the comments file and how anchors survive edits; the format of
  the user-edit changelog and its read-state; whether the user's log of player
  edits is the same record; the evidence database. And where each sits relative
  to CAOS.
- How an edit made by the user in the web UI is attributed in CAOS.
- How the policy version record is stored, what else it carries beyond the three
  pinned states, and how parent hints are derived.
- Whether pages and entities display what links to them.
