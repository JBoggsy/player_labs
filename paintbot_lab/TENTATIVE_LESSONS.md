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

### Re-verify the campaign contract from live data before every eval — it drifted massively in 3 days
Evidence: v60 validation (2026-08-11). Since the docs' round-381 snapshot: board migrated
10×10→16×16 hex (round 955), a true 1v1 head-to-head mode appeared (49 cells), _duo_roster
switched from 7+7+1+1 to an even captain/ally split, every cell now sets map_size, deployed
canonical moved 0.7.216→0.7.227, and campaign episodes carry perk loadouts. Two of my first
requests violated the allies-fixed rule and were cancelled/re-posted — caught only because I
read current metta episodes.py AND diffed real round-967 episode rows instead of trusting the
doc. The doc's own "re-resolve dated values" warning was the only part still fully true.

### Real campaign episode rows are the cheapest seating oracle
Evidence: v60 validation (2026-08-11). Rather than re-deriving slot layouts from variant
manifests, listing the champion's completed campaign ereq rows and grouping participant
positions by label gave every layout in one query: 2-team = alternating parity, ffa =
interleaved mod 4, plus live coworld_version (0.7.227) and current champion labels for free.

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
