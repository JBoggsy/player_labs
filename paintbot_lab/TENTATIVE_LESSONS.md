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

### An eval variant must actually reach the strategy rung being tested
Evidence: stencil:v6 assigned defensive posts in `1v1`, but every trace stayed
in the higher-priority convert hunt because one enemy has only three lives. The
7-4-1 duel result therefore said nothing about post defense; `2v2` traces were
required to observe `to_post` and `hold_post` activation.

### Lock generated Paintbot terrain with mapSeed, mapSize, and mapLayout
Evidence: generic experience-request `seed` values produced different map
dimensions across intended A/B arms. The explicit map fields reproduced the
same geometry and made the six-map 4FFA post-selection matrix valid.

### Read aim units from the deployed game version and variant together
Evidence: GameVersion 36 changed aim to a 32-slot ring, while Paintbot 0.7.184
retained `aimTurnRate=5` in each variant. Treating that value as one slot was
wrong; it means five slots / 40 brads per command. The corrected modular
controller raised replay hit rate from 20.9% to 51.5% against the top field.

### More forward defensive posts can reduce both coverage and combat output
Evidence: v11 correctly assigned all 12 sampled defenders to forward posts,
but versus homeward-ranked v9 on six locked 4FFA maps it fell from 285 shots / 156
hits / 56 kills to 205 / 90 / 23, while both arms returned every stolen heart.

### Own-heart defense cannot control every terminal event in multi-team FFA
Evidence: in the locked 4FFA matrix Stencil returned every observed theft of
its own heart yet still lost games when one opponent captured another
opponent's heart. An all-map draw-or-win target therefore crosses from local
defensive mechanics into third-party FFA strategy.
