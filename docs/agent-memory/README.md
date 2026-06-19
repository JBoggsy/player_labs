# Agent memory (exported snapshot)

This directory is an **exported copy** of the coding agent's persistent
cross-session memory for this repo. The live source lives outside the repo at
`~/.claude/projects/<project>/memory/` and persists across sessions on the
operator's machine; this is a point-in-time snapshot committed so the knowledge
travels with the repo (clones, fork, other machines).

## What's here

Each `*.md` file is **one memory** — a single durable fact, written
point-in-time, with frontmatter (`name`, `description`, `type`). Types:

- `user` — who the operator is / preferences
- `feedback` — guidance on how the agent should work (with the why)
- `project` — ongoing work, goals, constraints not derivable from code/git
- `reference` — pointers to external resources

[`MEMORY.md`](MEMORY.md) is the index loaded each session — one line per memory.

## Caveats

- **Point-in-time, not live.** These reflect what was true when written; file or
  flag citations may have drifted. Verify against current code before relying on
  one. The committed snapshot can also lag the live memory dir.
- **Not auto-synced.** Re-export by copying the live `memory/` dir here when you
  want to refresh the snapshot.
- **Durable lessons graduate elsewhere.** Per-session lessons live in each lab's
  `TENTATIVE_LESSONS.md` → `lessons_archive/` → (via `/lessons-review`)
  `best_practices.md`. This dir is agent memory, a separate track.
