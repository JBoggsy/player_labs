# Crewrift tentative lessons — session buffer

**Session started:** 2026-06-25 13:06. This is THIS SESSION's lesson buffer. Write candidate
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

### GROUNDED: post-kill RE-APPROACH is the gap — Aaron closes onto crew (144→64px), crewborg holds ~156px (2026-06-25)
Followed the data (multiple hypotheses, each tested) instead of asserting. (a) v44-vs-v45 (self-report removed) is NOISE: kills 1.69 vs 1.63 Welch p=0.54/MWU 0.74; win 83% vs 73% chi2 p=0.12 (CIs 74-89 vs 64-81 overlap). So self-report was neutral — thread closed. (b) WHERE we kill: SAME as Aaron — ~400px from home, in task rooms (Science Bay/Storage/Med Bay), only 5-10% near home; NOT farming the re-gather point. Crew density AT the kill: crewborg DENSER (1.64 vs Aaron 1.39 other crew within 220px) — kill setup fine, refutes over-isolation. Post-kill distance to nearest living crew: both ~150px at kill+10t, but **Aaron CLOSES to 64px by kill+200t; crewborg HOLDS at 156px**. So crewborg doesn't flee (no jump) AND doesn't re-approach — it sits ~150px out (just out of clean view → the earlier 4% crew-in-view post-kill vs Aaron 18%), can't line up a 2nd kill until a MEETING re-gathers everyone. ROOT CAUSE: **post-kill RE-APPROACH** — after a kill our Search picks a RANDOM nearby room to watch instead of going to the crew right there; Aaron moves onto the nearest crew. FIX: after a kill, beeline to the nearest known crew (close the ~150px gap), i.e. extend Recon's "go to nearest crewmate" across the whole post-kill cooldown, not just the last 100t. NOT voting, NOT kill location, NOT victim isolation, NOT fleeing — re-approach.
