# CTF tentative lessons — session buffer

**Session started:** 2026-08-08 12:20. This is THIS SESSION's lesson buffer. Write candidate
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

### Grep the callers before believing a TODO's debt inventory — it was right, but incomplete
Evidence: Nav deep-dive (2026-08-08). TODO.md's walkability item was exactly right
(5 walkableSegment callers, 2 walkableNavSegment callers, belief.danger trace-only —
all reproduced by grep in minutes), but a 10-minute caller sweep of worldmap.nim found
additional dead/trace-only nav code the TODO didn't know about: `pastRally` (0 callers),
`rallyPoint` (trace-only), `Objective.flowGoal` (trace-only; the real planner switch is
the parallel `FlowReasons` string list in action.nim:6), `distanceAt` duplicating
`routeDistance`. Cheap caller-census first; it both validates the debt list and grows it.

### Stencil has three "beeline, no walkability check" movement paths — implicit stuck-jitter is their only wall handling
Evidence: spray pursuit (action.nim:501-506) overwrites the movement mask with a direct
octant at the enemy; grenade evacuation (strategy.nim:235-245) and carrier-heard escort
(strategy.nim:288-292) emit unvalidated radial/extrapolated points (A* then snaps via
nearestWalkable, but the point itself can be off-map/unwalkable). Any nav unification
should decide whether beeline-with-jitter is a sanctioned third planner or a bug class.

### Spot-verify a subagent's load-bearing claims against primary source before folding them in
Evidence: nav deep-dive (2026-08-08). A breadth agent correctly found the engine keeps two
collision masks (walkMask for movement, wallMask for bullets) and implied stencil's
single-mask conflation was a behavioral bug. Reading the engine bake (map_art.nim:899-901)
and the diamond restamp (sim.nim:2677-2678) showed the masks are written as exact complements
and kept in sync — the "bug" downgraded to an undocumented invariant plus a real-but-different
staleness gap (init-only sprite vs live diamond restamps). One targeted read flipped the
report's framing from "fix the fire gate" to "add an invariant comment".

### The intent-reason string is the de-facto nav API — planner choice, micro exemptions, and clamps all key off it
Evidence: action.nim keys planner selection (FlowReasons list), peek/duck exemption
(action.nim:229-231), fire-freeze exemptions, and the endzone clamp all off
`intent.reason` string membership. Adding an objective without updating every list
silently gets A* + full micro. A refactor should make these properties of the intent
type, not string-set membership.
