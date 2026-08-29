# CTF tentative lessons — session buffer

**Session started:** 2026-08-29 13:19. This is THIS SESSION's lesson buffer. Write candidate
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
### The lazily-evaluated `else` branch is load-bearing state semantics in action.nim
Evidence: `belief.sweepTarget` at action.nim:549 mutates the sweep oscillator
(sweepOffset/sweepDir) as a side effect of being *read*, and Nim's lazy `else`
means it only advances on genuinely idle ticks (no combat target, no override
aim). Any re-homing of idle aim that computes the swept value eagerly (e.g.
per-tick in strategy) silently changes oscillator cadence. Found during the
threat-axis-removal recon; drove the axis-mind/sweep-body split in the design.

### Dead ticks bypass strategy entirely — parity claims must account for policy.nim's not_alive intent
Evidence: policy.nim:99-102 hand-builds `makeIntent(Hold, none, "not_alive")`
when dead, and resolveAction still runs (early-out is only selfXy/worldmap).
A field stamped only in decideObjective is absent on dead ticks; bit-parity
against v68 on compare_stencil requires stamping the dead-tick intent too.
### compare_stencil replays must reproduce capture-time STENCIL_* env or they false-FAIL
Evidence: pre-change baseline on a fresh 48-file corpus failed on exactly the
16 forced-active seats (captured with STENCIL_EARLY_DEFENSE=0) until the same
env was set for the replay run; the 32 normal seats passed as-is. Config env
is read at process start and is part of the recorded behavior. Also:
compare_stencil's pinned-cache default errors if only self_play's canonical
cache exists — pass --game-repo paintbot_lab/.cache/coworld-ctf/<canonical-sha>.
### Same-seed self-play is timing-nondeterministic — single-episode micro% is a noisy gate
Evidence: identical seed-404 forced-active gate episodes on v69 and pre-change
v68 code produced different episode lengths (21,504 vs 26,784 snapshots) and
duck% 13.26 vs 18.02 — the v68 CONTROL itself landed outside the 7-13 band.
The policy is deterministic on a fixed wire (278k-decision parity), but live
self-play wire depends on real-time scheduling. Read the duck% band as a
coarse smoke check across draws, not a per-episode pass/fail; the recorded-
wire comparator is the deterministic instrument.
### Hosted policy-artifact upload is flaky — don't preregister artifact-only metrics without a coverage plan
Evidence: in the v69-vs-v68 parity batch, only 28/56 episodes' stencil seats
uploaded trace zips (11 v69 / 17 v68), non-matched across arms (v68's all
from one seating), leaving duck%/peek% underpowered and composition-
confounded; and the trace has shot counters but NO hit counter, so the
preregistered hits/shots was unmeasurable without replay attribution.
Powered fallbacks that saved the verdict: results.json kills (every seat,
every episode) and W-L from scores. Next time: preregister metric sources
against what hosted artifacts actually contain, and treat artifact-derived
rates as best-effort secondary evidence.
