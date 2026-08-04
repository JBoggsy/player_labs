# Paintbot tentative lessons — session buffer

**Session started:** 2026-08-04 10:34. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`ctf_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (CTF-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### A downloader can label an XP bundle incomplete even when every policy artifact is present
Evidence: all four stencil:v1 map probes completed and downloaded 16/16/16/32
navigation ZIPs, but `fetch_artifacts.py` exhausted the episodes because the
separate results artifact and policy-log listing were unavailable. Inspect the
requested artifact class directly before treating the aggregate fetch verdict
as loss of evidence.

### Bound expensive tactical geometry before exact ray evaluation
Evidence: the first online-post implementation ray-scored every corridor cover
cell and took 29.6 s on a hosted giant map. Bucketing cheaply by route progress,
evaluating a bounded candidate set, simplifying duck contrast to three threat
rays, and computing only the agent's own team fronts reduced the same pinned
giant map to 2.78 s without changing the selected-position model.
