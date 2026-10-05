# Tags and the policy version tree

Two cross-cutting features. Both are decided here at the level of requirements.
What is not fixed here (how the tag list and the version records are stored,
and the tools around them) is detailed after the CAOS work
([07-research-plan.md](07-research-plan.md), area 4).

## Tagging any object

Any object in the system can carry tags: wiki pages, strategy documents,
pipeline entities (topics, hypotheses, experiments, results), policy versions,
and anything else the system manages. Tags are a way to group and find things
across the hierarchies that the pipeline and the wiki tree impose.

- **Vocabulary: a controlled, curated list of tags.** Only tags on the list can
  be applied. Both the user and the player can add to and edit the list as
  needed. Avoiding near-duplicate tags is the player's responsibility whenever
  it edits the list.
- **Who tags: both.** The user and the player can each apply and remove tags,
  with attribution in the history like any other edit.
- **Restricted-removal tags.** Some tags can be removed only by the user. The
  tagging tool enforces this by refusing the player's attempt. A configuration
  lists which tags are restricted; `do-not-publish` is the first.
- **Where tags live: in the front matter** of each markdown file (wiki pages,
  strategy documents, pipeline entities), so tags travel with the file and are
  covered by the same history. Where the tags of a policy version are kept is
  detailed design, since a version is not a markdown file.
- **What the UI does:** a page per tag listing everything that carries it, and
  tag filters on the wiki and pipeline lists.

### The `do-not-publish` tag and publishing

`do-not-publish` is a reserved tag the system understands. Every public write
path (the community skill, the standing forum agent) refuses to publish tagged
content until the user releases it by removing the tag.

Pages without the tag are publishable. An **untagged page may be published by
the player on its own initiative**, without a per-write go-ahead from the user.
The tag marks the specifically protected pages; pages are not protected by
default.

This differs from the lab today, where every public write needs the user's
go-ahead and protected findings are marked by hand in prose (the Gods of the
Arena research index carries inline "lab-internal, do not post" notes). A
scribe's note, not a decision: until the tag and its enforcement exist, the
lab's current go-ahead rule is the only protection and should stay in force.

Because the tag is the only thing between a page and publication, the player's
instructions must include clear guidance on which pages to tag. That guidance
has yet to be written. Two categories are already internal by default and so
belong in it: gameplay-mechanics discoveries and opposition research, which is
what the Strategist writes ([04-agents.md](04-agents.md)).

## The policy version tree

A record of **policy versions** (versions of the game-playing policy, not of
the Player-ADE code or anything else), kept so that:

- the player and the user can look back at prior versions and get at that old
  code when needed;
- both can see how the policy evolved, version to version;
- results can be attached to the exact version they measured.

Its rules:

- **Every upload is a version.** The tree is complete by construction; nothing
  depends on someone choosing to record a version.
- **A version may have more than one parent.** The tree is really a graph with
  merges: a version that combines two earlier ones has both as parents.
  Parentage is **stated by the player** at upload, possibly helped by hints the
  system derives from the source.
- **What a version pins.** Three things, aligned with each other:
  - the **strategy-document state** it was compiled from;
  - the **source snapshot**;
  - the **built artifact** that was uploaded (for Gods of the Arena the
    assembled `.bas` file; for container games the image).

  The record is also expected to carry the version name and id the Observatory
  assigned, since that is how the platform and the lab's tools refer to an
  upload. With CAOS the three pinned states are expected to be content hashes
  captured at upload, so that no commit is needed. Both expectations are the
  scribe's, to be confirmed by the CAOS work.
- **Alignment is recorded, not enforced.** An upload is never blocked by the
  strategy dirty flag ([01-collaborative-wiki.md](01-collaborative-wiki.md)).
  If the flag is set at upload (the strategy changed and the code was not
  recompiled), the upload goes ahead and the version **records the flag**, so
  the tree shows which versions were compiled from their strategy and which
  drifted. Refining code without a strategy change does not set the flag and is
  not drift.
- **No backlinks on the version.** Results point at the version they measured;
  the version record does not list what points at it.

**Phase-1 scope: a minimal tree.** Phase 1 keeps one record per upload with its
parents, the pinned hashes, and the dirty flag, because results need a version
id from the first experiment and the working-context migration needs a home for
its version narrative ([02-experiment-lifecycle.md](02-experiment-lifecycle.md)).
The browsable evolution view and diffing between versions come later.

### What the lab has today

The Observatory assigns each upload a version name and id (for example
`james-botts-gota:v13` and its uuid), and the labs record those in prose in their
working-context files. Uploads are not one-to-one with git commits, because the
lab's speed rule uploads straight after a rebuild without committing. So the
link from an uploaded version back to the exact source it was built from is not
reliably recorded, and the only account of what each version changed is prose.
