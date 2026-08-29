# Paintbot tentative lessons — session buffer

**Session started:** 2026-08-06 10:50. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`paintbot_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Paintbot-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### Re-derive controller units whenever the deployed GameVersion changes
Evidence: Stencil correctly modeled GV36's 32-slot ring, but retained that
model after GV40 restored continuous 0..255 headings. Against the live
5-brad-per-tick turn, the old modular five-slot solver could alternate between
nearby headings instead of converging. Exact `own aim` perception could reveal
the error but could not repair a wrong control model.

### Derive campaign seating from variant structure and commissioner code, never the map-ref name
Evidence: Paintbot 0.7.205 changed map ref `1v1` to a 16-seat, two-team game.
Current Metta consequently classifies it as campaign mode `2v2` and normal
invasions seat two captains plus two allies 7+7+1+1 with paired captain swaps.
Reading `1v1` as either two agents or two policies produced incorrect eval docs
and hid that Stencil's static parity squads can include a foreign allied seat.

### Cut paired two-team field tests by captain side before trusting the aggregate
Evidence: In the round-383 v54 top-champions batch, each `2v2` opponent, ally
pair, map, and seed was held fixed while captains swapped colors. V54 went 3-0
as blue captain but 1-1-1 as red captain, a weakness hidden by the combined
4-1-1 result. Three pairs are diagnostic rather than a stable effect estimate.

### Preserve FFA field composition when a loss clusters around specific rivals
Evidence: V54 went 3-2-1 across six distinct round-383 `4ffa` cells. The only
two fields containing both Daveey and relh produced the draw and loss; the
remaining fields yielded three wins and one draw. A follow-up should hold that
field composition rather than treating all FFA opponents as exchangeable.

### Treat a small paired-side split as a hypothesis, not a policy diagnosis
Evidence: The round-383 sample suggested a `2v2` red weakness from three paired
cells, but the larger round-385 set went 14-2 as red and 15-1 as blue across 16
episodes per side. Pairing exposed the original split correctly; replication
showed it was not a general side effect.

### Separate objective failures from combat failures
Evidence: On round-385 `1v1` cell `(3,2)`, v54 lost by capture to Max Yankov in
both captain colors despite 21-11 and 22-3 kill/death exchanges. Aggregate aim,
hit, and kill strength would hide a reproducible heart-defense or interception
failure.

### Replicate FFA weakness with the exact three-opponent field
Evidence: Across two distinct round-385 cells/colors, v54 went 0-2 against the
Max/Ron/daveey field and 0-1-1 against relh/Alex/Jordan. The earlier
Daveey-plus-relh pattern did not emerge as the stable grouping in the broader
sample; complete field identity is the attributable unit.

### Treat campaign prompt writes as eventually consistent
Evidence: The direct prompt endpoint accepted round-398 writes and restores,
but the immediate composed-full-prompt or restore readback remained stale long
enough to produce false verification failures. Bounded readback retries
resolved the lag; durable state must also roll back to its prior checkpoint so
a transient verification failure remains retryable.

### Split historical replay preparation from accelerator training
Evidence: Exact Sprite-v1 recovery needs the era's Coworld source and locked Nim
dependencies, while SFT needs only compact semantic samples and deduplicated
maps. A prepared bundle reproduced cached and exact-source corpora identically
and trained on MPS, so GPU hosts need neither raw replays nor simulator builds.
