# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-14 10:36. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`crewrift_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Crewrift-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### Top-N-vs-rest differential reports must stratify every stat by outcome (win/loss) before calling it an advantage
Evidence: the round-level top-3 advantage reporter's strongest findings were outcome echoes ("best imposters alive least" = they win fastest, restated). Pooled top-vs-rest comparisons make any stat downstream of the outcome (time alive, game length, raw totals) separate the groups by construction, with the best p-values in the report. Fix is mechanical: re-test within wins only and within losses only; echoes vanish, skill survives. Full guidance written to crewrift_lab/docs/top3-advantage-reporter-guidance.md (opportunity-conditioning table, early-game panel, out-of-sample ranking, FDR).
