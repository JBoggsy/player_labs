# Collaborative wiki with mutual editing

A wiki-style knowledge base that organizes the player's knowledge and presents it
to both the player and the user in the form each understands best. Both sides can
change it, and each side's changes are visible to the other.

## Page format

A wiki page is a **markdown file**. The markdown files are the single source of
truth for both sides:

- The **player** reads and edits pages as markdown, with dedicated editing
  tools (below) that ensure nothing gets lost or overwritten.
- The **user** reads pages in the web UI, which renders the markdown on the fly
  with a **templated wiki renderer**, and edits them in the UI, which saves the
  edit back to the same markdown file.

The renderer starts simple: markdown, images, and Mermaid diagrams. Pages must
eventually support tables, figures, diagrams, and charts, and the renderer is
the path for adding richer figures (charts from data files, other diagram
types) as needs come up.

Each page may have two companions:

- **Front matter** at the top of the file, holding its tags
  ([09-tags-and-policy-versions.md](09-tags-and-policy-versions.md)).
- An optional **JSON comments file** next to the page, holding its comment
  threads (below).

## Player side

- The wiki is a library of **linked, indexed markdown files** the player builds up
  and modifies.
- Tooling must let the player **search the wiki** and must **make the right
  knowledge available at the right time** (when an agent starts a task, the
  relevant pages should be in front of it without a manual hunt).
- The starting point for indexing is probably just an **index file** listing
  the pages.
- The final design of indexing and retrieval is based on **state-of-the-art
  agentic memory systems**, which are researched before that design is written
  ([07-research-plan.md](07-research-plan.md), area 1).
- The player uses **sub-agents to manage the wiki** (the Librarian in
  [04-agents.md](04-agents.md)); tools and skills for this need to be built.
  This arrives with the autonomous agents, after phase 1.

## Editing tools for the player

Pages and other documents are plain files, and the player can edit them through
**dedicated tools** that ensure nothing gets lost or overwritten. The tools
cover wiki pages and the other documents in the same format, not only the wiki.

What the tools do to deliver that guarantee is detailed design. The scribe's
suggestions, not yet ruled on by the user: a read-page and an edit-page tool;
keeping the comments file and its anchors intact through an edit; refusing to
overwrite a page that changed since the player last read it. Whether the player
must always use these tools, or may also edit files directly, is not decided.

## User side (in the web UI)

The wiki is a section of the web UI. Its requirements:

1. **Rich content.** Rendered as described under page format.

2. **User edits reach the player.** The user can edit wiki pages directly. Every
   user edit is recorded as a diff in a **changelog** that accumulates until the
   player explicitly marks entries as read. The player's instructions contain a
   clear pointer to the changelog and how to read and mark it, and nothing more:
   the user drives when the player looks at pending edits. Pages that link to, or
   are linked from, a page with unread changes carry a **marker**, so a player
   reading a related page is warned that what it is reading may be out of date.
   This document calls this the **user-edit changelog**.

   Once autonomous agents exist, the same changelog feeds an alert: a sub-agent
   is woken up, handed the diff, and asked to incorporate the change into the
   broader wiki (cross-links, other affected pages) and into the broader player
   knowledge (for example, experiments in progress that the change bears on).

3. **Player edits notify the user.** The user has a change log of the player's
   edits and receives notifications when the player changes pages, so the user
   can see and respond to player edits in the same way the player responds to
   user edits. In phase 1 notifications are **in-app only** (for example a
   change log page and an unread indicator). Pushes outside the app, through
   email or a push service such as ntfy, may be added later. Whether this log
   and the user-edit changelog are one record seen from two sides or two
   records is detailed design.

4. **Text-anchored comments.** The user can attach comments to specific text in
   a page, and the player responds to them. This lets the user ask questions and
   raise concerns through an easy, intuitive interface instead of opening a full
   agent session or rewriting the page by hand. Comments go both ways: the player
   can comment on the user's text and reply to the user's comments, and the user
   can reply to the player's. Comments can be marked **resolved**. The player may
   resolve comments, but its instructions say to resolve only its own unless the
   user specifically asks it to resolve others.

   Each page's comments live in the optional **JSON comments file next to the
   page**. How a comment's anchor is recorded and re-attached after the page is
   edited is detailed design. The scribe's suggestion, not yet ruled on: record
   the quoted text plus position hints, and keep a comment whose text can no
   longer be found, marked as orphaned, rather than dropping it.

5. **History.** Every edit is recorded and attributed to either the user or the
   player. The history system for this, and for everything the player does, is
   **CAOS**: every file version and every action is a hashed object, so every
   change and every action is accounted for. How wiki edits by the user and the
   player become CAOS history, and where the changelog's read-state and the
   comment records live relative to it, is settled by the CAOS work
   ([07-research-plan.md](07-research-plan.md), area 4).

6. **Scheduled maintenance.** A scheduled sub-agent regularly maintains the
   knowledge base, keeping it up to date and well organized. The same Librarian
   agent likely covers this and the alert in requirement 2. This arrives with
   the autonomous agents, after phase 1.

## Contents

The wiki holds, at least:

- Reports and knowledge about coworlds and Softmax in general.
- Mechanics and details of the specific coworlds being played.
- Field reports.
- Opposition research (other entrants' policies and behavior).
- Web research on similar games.
- Evidence that has not yet become a pipeline topic: survey reports, mined
  hypothesis lists, field studies, diagnostic runs (see the relationship to the
  pipeline, below).
- Each lab's **instruction page**: the lab-specific guidance an agent is pointed
  at when it starts work in that lab ([08-phasing.md](08-phasing.md)).
- Supported method and the user's durable preferences (below).
- More, as it accumulates.

### The existing lab record files

The lab's current record files are **absorbed** into the wiki and the pipeline
and then removed.

- The root `best_practices.md` (supported method) and `user_preferences.md` (the
  user's durable preferences) become **wiki pages** in the shared wiki, rendered
  and commentable like any other.
- Each lab's `WORKING_CONTEXT.md` and `TENTATIVE_LESSONS.md` are absorbed into
  the pipeline ([02-experiment-lifecycle.md](02-experiment-lifecycle.md)).

These files are being deprecated. When the migration happens, and what the
labs outside the pilot rely on in the meantime, is [Q30](05-open-questions.md).

### Special category: strategy pages

A policy's **strategy** is a special category of wiki article, governed by this
discipline:

- The natural-language strategy documents (one markdown file or a collection of
  them) are the **true description of the policy**.
- The policy code (for example the `.bas` files in Gods of the Arena) is a
  **"compiled" version** of that description. The compiler is the coding agent:
  compilation means the agent writing or editing the code from the strategy
  documents.
- Therefore a change to the policy is made by **first writing it into the strategy
  documents, then compiling the strategy into the uploadable artifact**. This
  holds whoever originates the change: when the player changes the policy for an
  experiment, it alters the strategy documents first, then compiles.

Two mechanisms support this:

- The player's **instructions** state the discipline above.
- An **automated check** detects changes to the strategy documents, flags the
  policy artifact as **dirty** (strategy changed, code not yet recompiled), and
  highlights the diffs in the strategy documents so the player knows exactly what
  needs to be updated. This works like the wiki changelog. The flag never blocks
  an upload; a version uploaded while it is set records that fact
  ([09-tags-and-policy-versions.md](09-tags-and-policy-versions.md)).

Compiling will often mean refining the code several times until it works well,
and such refinements may not warrant a strategy change. The right balance and
tooling for that will be found as the system is used. The objective is that the
policy's strategy, tactics, and mechanics are described in natural language as a
contract between player and user, that the whole policy can be refined easily
and naturally in that language, and that those descriptions stay separate from
implementation details and from the tuning, parameterization, and refining of
code.

## Current-state prose versus kept history

This amends the lab's rule against archives, whose real target is **prose**.
Any document that is descriptive or normative about the current state of
affairs or about desired changes (a wiki article, a strategy document, a topic
or hypothesis write-up, an experiment description) describes the present only.
An agent reading such a page must never encounter old, out-of-date ideas,
version references, change narratives, or history, except where an older idea
is clearly relevant to the current state and the document says so.

Having an archive is fine. Older versions, edit histories, changelogs, past
experiments and results, the policy version tree, and CAOS's record of every
action are all kept; they are structured, dated, and versioned, so they cannot
be mistaken for current claims. Prose carries no "superseded" tag or state: a
stale page is corrected in place, and its history lives in the edit history.
If it proves useful, the rule may be lightened to allow a changelog or history
at the bottom of an article or in a companion article.

The lab states the old rule in `docs/learning.md`, `best_practices.md`, and
`user_preferences.md`. The last two become wiki pages and take the amended
wording then; what becomes of `docs/learning.md` is part of
[Q30](05-open-questions.md).

## Publishing

Wiki pages may be published to a coworld's public community forum and wiki. A
page tagged `do-not-publish` is never published until the user releases it; a
page without that tag may be published by the player on its own initiative. See
[09-tags-and-policy-versions.md](09-tags-and-policy-versions.md).

## Structure: per-coworld and shared

Each game's wiki lives under that lab's `docs/` directory, and the repo root
`docs/` is the shared, coworld-agnostic wiki. Navigation between wikis works
because links can span folders. The UI mirrors this separation visually.

Phase 1 builds against the Gods of the Arena lab only; the other labs are left
alone and brought in later. That lab's knowledge already sits in its `docs/`
directory, indexed by `docs/research.md`. Its `docs/wiki/` subdirectory is
something else: the lab's maintained copies of the pages it publishes to the
game's public community wiki.

The current lab structure is **provisional guidance, not a final decision**. It
mostly makes sense, but the user wants the organization of labs inside Player-ADE
to be genuinely thought out rather than adopted by default: later work may define
more rigorously what a coworld lab looks like and add uniform mechanisms for
instantiating new labs. The pilot on Gods of the Arena is expected to show what
that structure should be.

## Relationship to the experiment lifecycle

**Wiki pages and pipeline entities can link to each other in either
direction.** A topic, hypothesis, experiment, or result can link to wiki pages,
and a wiki page can link to pipeline entities. This is how evidence that has not yet become a topic is held: survey reports, mined
hypothesis lists, field studies, opposition notes, and diagnostic runs are
**wiki pages**, not a pipeline entity of their own, and a topic that grows out
of one links to it as its motivation.

The pipeline entities (topics, hypotheses, experiments, results) are expected
to reuse the wiki page format, with a different connective structure,
especially in the user-facing UI. The user has not confirmed this
([Q33](05-open-questions.md)); tags in front matter and the editing tools
assume it. The collaboration requirements above (comments, edits, attribution,
notifications) apply to pipeline entities equally. See
[02-experiment-lifecycle.md](02-experiment-lifecycle.md).
