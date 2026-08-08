# Paintbot tentative lessons — session buffer

> **Historical session record.** The GV36 aim-unit lesson below was correct for
> its deployed game but is superseded by Paintbot 0.7.204+/GV40, which restored
> continuous headings and interprets `aimTurnRate=5` as 5 brads per tick.

**Session started:** 2026-08-04 10:34. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](.) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`paintbot_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (CTF-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### Read exact gameplay state from its marker, not a lower-resolution render sprite
Evidence: Stencil inferred GV36's 32-slot gun aim from a soldier sprite with only
16 visual rotations and accumulated 85,885 aim resyncs across a fresh 18-episode
arm. Reading `own aim <brads>` cut that to 196 and raised matched replay accuracy
from 53.3% to 74.3% while shots and kills increased and deaths fell.

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

### Read aim units from the deployed game version and variant together (GV36 historical)
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

### Trace the complete fire gate before changing movement or aim tolerance
Evidence: per-tick cooldown/alignment/wall/teammate reasons showed alignment as
the dominant visible-target blocker, but both alignment strafe and the exact
14 px collision corridor failed replicated defender outcomes. A dominant gate
counter identifies where time is spent, not which intervention will help.

### A promising six-episode mechanics screen must be replicated
Evidence: v14 improved from 1 win / 4 draws / 1 loss to 1 win / 5 draws in its
six-map screen, then fell from 3 to 1 wins in the 18-episode-per-arm replication
and reduced defender kills from 6.44 to 5.06 per episode.

### Keep generated navigation knowledge and runtime use separately visible
Evidence: post generation scored a route-waypoint sightline axis while runtime
swept toward the distant pedestal; the axes differed by mean 23.2 degrees and
up to 90 degrees. Using the generated axis still regressed defender kills, so
the viewer now overlays it as trace-only knowledge rather than implying it is
the accepted runtime action.

### Prioritize the threat to the defended asset inside combat scoring
Evidence: defenders saw multiple enemies on 2,164 of 4,402 alive ticks in the
120 ticks before red-heart steals, but generic target scoring had no heart
input. A bounded heart-threat bonus changed only 6.8% of multi-target choices
yet improved two fresh combined fields from 2W/1D/33L to 8W/2D/26L and raised
defender kills from 5.11 to 6.42 per episode.

### Do not use the CTF warehouse winner projection for four-team Paintbot
Evidence: `episodes.winner` only compares red and blue, so green/yellow wins
were mislabeled draws. Paintbot W/D/L must come from the complete `results.json`
team/win vectors until the warehouse projection is generalized.

### A verified carrier match should bypass a generic combat target latch
Evidence: after Stencil's heart was stolen, v20 could retain an unrelated target
for eight ticks despite a high-confidence carrier being visible and shootable.
Across two fresh matched batches, 77 score overrides and 174 immediate switches
raised defender kills from 4.78 to 6.67 per episode (p=0.024), reduced steals
from 51 to 45, and improved both batches from 4 to 5 wins.
