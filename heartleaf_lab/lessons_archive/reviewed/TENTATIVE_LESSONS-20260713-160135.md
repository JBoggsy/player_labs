# Heartleaf tentative lessons — session buffer

**Session started:** 2026-07-13 11:14. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`heartleaf_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Heartleaf-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### heartleaf_lab is the canonical template for scaffolding a brand-new game lab
Evidence: When creating vanilla_wow_lab this session, heartleaf_lab was the best model because
it was itself created in "scaffolding-only, no player yet" state. Faithful new-lab scaffold =
README.md + AGENTS.md (game layer over root) + near-empty best_practices.md + seeded
WORKING_CONTEXT.md + TENTATIVE_LESSONS.md + docs/<game>-gameplay.md (self-contained anchor doc)
+ tools/{rotate_lessons,lessons_stop_nudge}.sh (paths swapped per-lab) + lessons_archive/ +
.claude/skills/lessons-review/SKILL.md. Plus registration: 2 hook entries in root
.claude/settings.json + root README layout/list. Player package added only when first policy built.
Status: this note is about the meta-process, not Heartleaf gameplay — flagging for the meta/root buffer if one existed.
