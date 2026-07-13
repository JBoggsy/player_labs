---
name: crewrift-living-docs-discipline
description: "In the player_labs/crewrift lab, keep WORKING_CONTEXT.md and TENTATIVE_LESSONS.md updated as you work — don't batch it to the end"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f70c9801-7ee7-499b-97f9-4fd0848a6b8e
---

In the `player_labs` Crewrift lab, two living docs must be maintained *as you go*, not
just at session end: `crewrift_lab/WORKING_CONTEXT.md` (the one-screen "where are we and
why" — reseed it on each direction pivot) and `crewrift_lab/TENTATIVE_LESSONS.md` (an
eager buffer of candidate lessons, each with a hit count). The version log and git
commits are not a substitute — these two files are the cross-session resume state and the
lesson ledger.

**Why:** During the v22/v23 imposter-kill session James explicitly checked whether I'd
been keeping them current, and I had not — WORKING_CONTEXT was two pivots stale (still on
the old "MAKE CREWBORG VOTE" objective) and several strong lessons (the self-vote bug, the
connect-failure-vs-saturation finding) lived only in commits. I had to reconstruct and
reseed in one batch, which is exactly what the "update as you learn" instruction is meant
to prevent.

**How to apply:** After each meaningful finding or direction change, update the relevant
doc in the same turn — append a candidate lesson the moment something looks reusable, and
reseed WORKING_CONTEXT when the objective changes. Treat it as part of the loop, like the
version log.

**Update (2026-06-12):** James automated the lessons *lifecycle* because instruction-
following alone wasn't reliable: a SessionStart hook (`crewrift_lab/tools/rotate_lessons.sh`)
archives each session's TENTATIVE_LESSONS.md to `crewrift_lab/lessons_archive/` and creates
a fresh per-session buffer; `/lessons-review` (≈weekly, human-driven)
graduates lessons that RECUR across archived session buffers. Writing lessons AS YOU GO is
still the agent's job — the hook only rotates. WORKING_CONTEXT.md discipline is
unchanged (still manual).

**Update (2026-07-13):** The four per-lab Stop-hook nudges were replaced by ONE
repo-wide nudge (`tools/lessons_stop_nudge.sh` at the repo root) — the per-lab hooks all
fired on every stop regardless of which labs the session touched. The new hook fires at
most once per session and names only the labs the session actually worked in (detected
via lab-path hits in the transcript's tool_use lines) whose buffers are still untouched,
with an explicit instruction not to add entries to labs not worked in.
