# CTF tentative lessons — session buffer

**Session started:** 2026-08-11 15:22. This is THIS SESSION's lesson buffer. Write candidate
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

### Property-test geometric predicates against brute force before shipping — the clever version had a boundary hole
Evidence: Layer 1 clearance rework (2026-08-11). The Lipschitz skip-march version of
segmentClear looked provably correct on paper (I "fixed" the margin from -1 to -2 after
re-deriving), yet the random-map parity test still caught a false pass in one trial: at
clearance exactly PlayerHalf+1 the guarantee radius covers zero pixels, so diagonal
corner pixels between unit steps went unchecked. Replaced with the exact supercover DDA
(reusing the proven walkableNavSegment traversal at pixel resolution) — all 24.6k random
segments then matched brute force. At stencil's segment lengths (<=60px) the skip saved
nothing worth the subtlety; prefer the dumb-exact traversal and let a brute-force
property test be the judge of any cleverness.
