# Collaborative wiki with mutual editing

A wiki-style knowledge base that organizes the player's knowledge and presents it
to both the player and the user in the form each understands best. Both sides can
change it, and each side's changes are visible to the other.

## Player side

- The wiki is a library of **linked, indexed markdown files** the player builds up
  and modifies.
- Tooling must let the player **search the wiki** and must **make the right
  knowledge available at the right time** (when an agent starts a task, the
  relevant pages should be in front of it without a manual hunt).
- Starting point: probably just an **index file** listing the pages.
- The player should use **sub-agents to manage the wiki** (see the Librarian in
  [04-agents.md](04-agents.md)); tools and skills for this need to be built.
- The final design of the player-side system should be based on **state-of-the-art
  agentic memory systems**, which must be researched with web search before the
  detailed design. See the [research plan](07-research-plan.md).

## User side (in the web UI)

The user side is a section of the web UI. The exact details are still fuzzy; the
requirements are:

1. **Rich content.** Pages must support images, tables, figures, diagrams, and
   charts. Three candidate approaches were named, with no choice made yet
   ([Q3](05-open-questions.md)):
   - Plain `.md` files where every figure is an image file.
   - HTML files rendered from the player-side `.md` files, the way the lab's
     existing report-generation skills produce HTML.
   - A templating system that renders the player-side `.md` files in a
     Wikipedia-like format.

2. **User edits wake the player.** The user can edit wiki pages directly. When
   the user edits, the player is alerted. Current picture of the alert: a
   sub-agent is woken up, handed the diff, and asked to incorporate the change
   into the broader wiki (add cross-links, update other pages that the new
   information affects) and into the broader player knowledge (for example,
   updating experiments in progress that the change bears on).

3. **Player edits notify the user.** The user has a change log and receives
   notifications when the player changes pages, so the user can see and respond
   to player edits in the same way the player responds to user edits.

4. **Text-anchored comments.** The user can attach comments to specific text in
   a page. The player responds to them. This lets the user ask questions and
   raise concerns through an easy, intuitive interface instead of opening a full
   agent session or rewriting the page by hand.

5. **History.** Wiki history is tracked. Every edit is recorded and attributed
   to either the user or the player.

6. **Scheduled maintenance.** A cron-job sub-agent regularly maintains the
   knowledge base, keeping it up to date and well organized. (This overlaps with
   requirement 2; the same Librarian agent likely covers both.)

## Contents

The wiki holds, at least:

- Reports and knowledge about coworlds and Softmax in general.
- Mechanics and details of the specific coworlds being played.
- Field reports.
- Opposition research (other entrants' policies and behavior).
- Web research on similar games.
- More, as it accumulates.

### Special category: strategy pages

A policy's **strategy** is a special category of wiki article. The user wants the
system to enforce, or at least enable, this discipline:

- The natural-language description of the strategy in `.md` files is the **core**
  of the strategy.
- The code implementation is **based on** that core.
- Therefore, **changes to the strategy `.md` files must directly result in
  corresponding changes to the policy code.**

How that "directly result in" works mechanically (who triggers the code change,
whether the user reviews it first, and what happens in the reverse direction when
code changes) is not yet specified. See [Q7, Q8](05-open-questions.md).

## Structure: per-coworld and shared

The current lab separates coworld-specific knowledge (each `<game>_lab/`) from
unified coworld-agnostic knowledge (repo root). The wiki keeps that separation and
the UI mirrors it visually. Where the wiki files physically live relative to the
existing lab directories is open ([Q4](05-open-questions.md)).

## Relationship to the experiment lifecycle

The experiment entities (topics, hypotheses, experiments, results) will very likely
reuse the same page format as wiki pages, with a different connective structure,
especially in the user-facing UI. Collaboration requirements (comments, edits,
attribution, notifications) apply to them equally. See
[02-experiment-lifecycle.md](02-experiment-lifecycle.md).
