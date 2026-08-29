# stencil v1 — design

*2026-08-03. Living document; updated as the implementation reveals new
information.*

> **Freshness note (2026-08-29):** the WorldMap/navigation internals described
> below (footprint erosion, choke/rally anchor fractions, flow-field movement,
> the v5/v12 per-front posts) are the v1-v59 design and are **superseded by
> the completed navigation rework (v60-v68)** — see the addendum
> [below](#post-v1-addendum-the-navigation-rework-v60v68) and the per-layer
> docs it links. The problem statement, scrap/port ledger, multi-team
> generalization, and squad-consensus addenda remain current.

## Problem

Beacon (the CTF champion lineage) is auto-mirrored into the live Paintbot
league and scores 0: its world model is an **offline bake of the fixed CTF
arena** (`nav.npz` flow fields, hand-authored POIs, battle plans drawn on known
coordinates), while paintbot generates a fresh map per episode in five size
classes with 2-or-4 teams. Everything predicated on a single known map is dead
weight; everything else (combat micro, belief, chat, item skills, the strategy
ladder's shape) is proven and portable.

## Goals / non-goals

- **Goal**: a competitive Paintbot policy that plays every live variant
  (`default`, `2v2`, `4ffa`, `4ffa8`) from one image, with all map knowledge
  acquired online per episode.
- **Goal**: preserve beacon's evolved combat core (aim/lead/fire-gate/FF-guard,
  peek-fire-duck, firefight target scoring + focus claims, hearing, chat,
  convert trigger) with minimal semantic drift, so its lessons carry.
- **Historical non-goal (v1)**: posts (covered-sightline fighting positions), battle
  plans, opponent plan inference — the parts beacon built ON TOP of the fixed
  arena. Re-derivable later from online geometry if evals demand it.
- **Non-goal**: paint-coverage play — paint is cosmetic in this game.

## The load-bearing decision: `WorldMap` replaces the bake

Beacon's one clean seam was `mapdata.py` — eight functions every consumer went
through. stencil rebuilds that seam as an **episode-scoped object**
(`worldmap.nim: WorldMap`) constructed the first frame the init snapshot is
complete:

| input (wire) | product |
|---|---|
| `walkability map` sprite (snappy RGBA, alpha=walkable) | pixel wall mask; footprint-eroded 8px nav grid (summed-area-table erosion); cover cells |
| `game teams <n> map <w>x<h>` marker | team count, colors prefix, and initial seat dealing; roster size grows separately from observed identities |
| `endzone <color> <shape> <box>` markers | per-color home/capture anchors, derived choke & rally lines (fractions of the home→center axis), spawn aim, inside-base tests |
| `<color> flag planted` sightings | heart pedestal positions (never fog; resolve at t=0) |

Flow fields and route-distance fields are computed **lazily per goal cell**
(Dijkstra, cached on the instance) — the beacon flow-field API without the
offline bake. There are deliberately **no module-level caches** (beacon's
`lru_cache` loaders were a latent cross-episode bug under procgen); the Belief
owns the WorldMap and the runtime rebuilds it if the map signature changes.

Derived anchors replace authored ones: `CHOKE_X` → `choke_point(color)`
(45% along home→center, snapped to cover), `SQUAD_RALLY_X` → `rally_point` /
`past_rally` (65% projection), `BASE_FRONT_X` → `inside_base(color, margin)`,
`PEDESTAL` → learned pedestals, POIs/plans → gone.

### Post-v1 addendum: generated post knowledge

`stencil:v5` reintroduced posts without restoring fixed-map data. Each agent
generates only its own team's front against each live opponent. Cover cells
near the opponent→home shortest-route corridor are bucketed by route progress;
a bounded, spatially distributed subset is scored with nine forward firing
rays. The final score combines firing-line depth, corridor relevance, and the
contrast to a nearby reachable duck cell. Six spatially separated posts per
front are retained when enough valid pairs exist. `stencil:v12` makes defenders
consume this knowledge: unique post positions are ranked from the team's home
center outward, assigned by defender seat, and used as hold targets with the sweep axis
aimed toward the post's opponent front. A forced-forward ranking was tested and
rejected because it reduced shots, hits, and kills without improving heart
recovery. Heart-theft interception retains higher priority, and generic choke
cover remains the no-post fallback.

`stencil:v21` keeps that behavior and makes the boundary between generated
knowledge and runtime action inspectable. Each defender snapshot identifies its
assigned post, duck point, opponent front, score, heart distance, forwardness,
and trace-only scored sightline center; the HTML navigation viewer overlays the
assignment on the full per-front map. Follow-up attempts to change alignment
movement, the fire corridor, duck use, post ranking, and sweep axis were all
rejected by hosted replication and are recorded in `VERSION_LOG.md`.
Defender gun-target scoring additionally includes a bounded threat term for
route progress toward the home heart (or proximity to the observed thief after
a steal). Once the heart is stolen, a visible high-confidence carrier match
overrides generic target score and the normal target latch so the defender can
engage immediately. These changes affect target choice without changing
movement or objectives.

### Post-v1 addendum: leaderless squad orders

`stencil:v48` restores the useful behavioral vocabulary of battle plans without
restoring their fixed-map coordinates. There is no squad leader. Every member
proposes a hold, watch, or move directive; members vote on a deterministic
majority choice and commit only after a quorum agrees. Kind ties resolve toward
hold, then watch, then move, while point ties use the spatial medoid and stable
map/opponent coordinates—never sender identity.

The order layer supplies tactical goals, not movement micro. Move orders advance
through generated fronts at staged route progress; hold and watch orders occupy
distinct generated firing/duck posts near the agreed cell. Existing A*, danger,
cover, formation, sightline sweep, fire gating, and peek/fire/duck behavior
execute those goals. Carry, theft interception, escort, grenade safety, item,
and wipe-conversion emergencies remain above squad orders in the strategy
ladder.

The ten-character shout protocol uses `Q` proposals and `V` votes with sender,
epoch, kind, quantized map cell, and opponent. The original squad table pairs
same-parity identities. That matched the disabled ladder's equal entrant
blocks and is **not roster-aware**: under the 7+7+1+1 seating current when
this was written, one pair could include the foreign allied seat and other
captain-owned seats could be omitted. *(Update 2026-08-29: the campaign now
splits captain/ally evenly, under which parity squads happen to fall within
one owner's block — see `../stencil-communication.md`; roster-awareness
remains the robust fix.)* Structured traces expose consensus transitions, proposal/vote sets,
commits and timeouts, chosen orders/posts, arrivals, and following time. A
roster-aware redesign is now an explicit follow-up rather than a claimed
invariant of the protocol.

`stencil:v49` adds a short commit-acknowledgement phase so a member that has
observed quorum can converge a peer that missed one of the votes. A peer accepts
the acknowledgement only when it matches its own vote or independently derived
choice; no member gains command authority.

`stencil:v50` makes that protocol safe under late proposals by locking each
member's first vote for an epoch: intersecting quorums can no longer reuse a
member whose vote changed. Fresh forward-epoch squad traffic also advances a
lagging member's local clock, while the 36-value ring comparison rejects older
delayed messages. Snapshot telemetry counts these repairs as
`squad_consensus_resyncs`.

`stencil:v51` fixes the incomplete v50 implementation: quorum counting and the
local vote table use the already locked vote rather than recomputing a choice
after late proposals. This is the property that makes intersecting majorities
a safety guarantee.

`stencil:v52` treats a live consensus timeout as a cohesion failure and enters
the same bounded last-known-squad rejoin path used after respawn. This prevents
an orderless isolated member from falling through to independent role behavior
indefinitely.

`stencil:v53` tested refreshing that rejoin target while regrouping, but the
full-seat stress gate rejected it: timeouts and prolonged live epoch drift both
increased. The source is restored to v52's bounded static-target behavior.

### Post-v1 addendum: the navigation rework (v60–v68)

The five-layer navigation rework (2026-08-11 → 08-14, all layers hosted-
validated; v68 is the live champion) replaced most of this document's WorldMap
and movement internals. What changed, against the sections above:

- **The erosion nav grid is gone.** The walkability product is now an exact
  **L∞ clearance field** with the `canStand`/`segmentClear`/`nudgeClear`
  predicate family; the 8 px grid is *derived* from clearance and survives
  only for comms/telemetry coordinates, the Dijkstra oracle, and local micro
  geometry (v61; the fuller consumer census is in the Layer 4 doc).
- **Choke/rally axis fractions are gone.** Topology is derived from the map:
  4-connected component labels, priority-flood watershed rooms + chokepoints,
  16-ray directional cover (map edge is not cover), and `defenseGate`
  replacing `choke_point`/`rally_point`/`past_rally` (v62).
- **Flow fields no longer move agents.** Movement routes through one
  weighted-A* pixel-lattice planner (`planner.nim`) with belief-derived LOS
  danger and carrier/hunter cost profiles; the lazily minted stable-goal
  Dijkstra fields survive only as the planner's heuristic oracle (v65/v66).
- **Strategy→action is a typed contract.** Strategy emits an `Intent` with a
  pre-validated goal (`nearestReachable`) and typed permissions; reason-string
  dispatch and all beelines are dead; unroutable goals are loud bugs
  (v66 — [`nav-layer4-intent-contract-2026-08-13.md`](nav-layer4-intent-contract-2026-08-13.md)).
- **The v5/v12 per-front posts became the post atlas.** Posts exist wherever
  there is cover (~14k on a giant map), with 16-sector reach profiles and lazy
  duck pairing; selection is two-phase and scored situationally against
  believed enemy tracks. Defenders, early defense (home-room entrance gates),
  barrage centering (danger-penalized room peaks), and squad orders all select
  from the atlas (v63/v64/v67).
- **Micro is corridor-bounded.** Peek/duck, separation, and formation bias may
  perturb motion only within a corridor of the planned path; the 90° stuck
  jitter is deleted in favor of a penalty-replan watchdog with loud telemetry
  (v68 — [`nav-layer5-follower-2026-08-14.md`](nav-layer5-follower-2026-08-14.md)).

Governing sketch (with per-layer status addenda):
[`nav-rework-sketch-2026-08-11.md`](nav-rework-sketch-2026-08-11.md). Full
evidence per layer: `VERSION_LOG.md` v60-v68.

Seating note: the "current campaign 2v2-mode seating is 7+7+1+1" risk recorded
below is dated — since the 2026-08-11 commissioner change the split is an
**even** captain/ally half-split, under which the two-team parity squads fall
entirely within one owner's block (see
[`../stencil-communication.md`](../stencil-communication.md)).

## Multi-team generalization

- `Team` is a color token; active colors = wire-stated prefix of
  red/blue/green/yellow. Enemy = every other active color.
- Slot deal `slot mod teams` guesses the color; the first `self <color>`
  sighting **locks** the real one (hosted seating is authoritative, not our
  guess). Seat = `slot div teams`.
- Per-color heart states; **steal target** = nearest live enemy heart by
  walkable route from home, re-chosen when a heart retires. Retirement =
  neither heart sprite present AND that team's scoreboard deaths exhaust its
  lives.
- The **convert trigger** generalizes to the *weakest live enemy team* (pot
  scoring makes a draw = a loss, so hunting the wipe stays nearly free).
- Roles scale: defender count = `round(3/8 x seats_per_team)`; hold points
  spread perpendicular to the home→center axis at the choke anchor.

## What was scrapped vs ported (from the ctf_lab inventory)

**Scrapped**: `mapdata/nav.npz` + `bake_map.py`, `poi.py` +
`points_of_interest.json`, `plan.py` + `plans/` + `battle_plans/` + plan/POI
editors + `infer_battle_plan.py`'s POI vocabulary, `posts.py` (baked-sightline
dependent), anti-turtle's arena-specific lineup classifier, fixed item spawn
tables + seat-keyed item assignments, arena-anchored tests.

**Ported with the WorldMap seam**: perception (plus pixel decode + marker
parsing — new), belief (tracks/danger/hearing/chat/firefight), nav (flow + A*),
action (movement/aim/fire/peek-duck/grenade), fight
(sightline-field scoring → exact rays; ≤8 candidates/tick is cheap), chat
(grid dims from the map; protocol extended with consensus), squads
(static parity tables, leaderless consensus, generated geometry), items (spawn table now
**discovered from sightings** — generator placements are per-map), strategy
(the ladder minus plan/POI/post rungs), policy orchestration, tracing, and the
`STENCIL_*` configuration layer.

Notable default flips vs beacon: `FIREFIGHT`/`FOCUS_CLAIMS` default **ON**
(they were beacon's champion configuration, set per-upload there).

## Performance envelope

The one-time WorldMap build is the only heavy step: native summed-area erosion,
cover extraction, lazy Dijkstra, and post generation over the largest grid.
The pre-post measured giant-map p95 was 419 ms under 16-process contention.
The final hosted v5 post pass added 20 ms small, 109 ms large, 164 ms standard
four-team, 1.16 s huge, and 2.78 s giant on representative slots. It runs once
inside the normal five-second start countdown; per-tick work remains label
scans, constant-time lookups, and occasional A*.

## Risks / open questions

- **Seats-per-team inference** grows conservatively from observed identity
  badges because the wire still states no muster. Low-index seats cannot know
  4-vs-8 muster until they observe a sufficiently high identity.
- **Item discovery** starts blind — early-game fetches only happen after
  sightings. If evals show med-kit latency mattering, seed guesses from the
  RULES layout rules per shape.
- **4-team threat model** is beacon's 2-team model with more colors; no
  third-party reasoning yet (e.g. don't break up a rival-vs-rival fight).
- **Campaign 2v2-mode seating splits ownership** *(originally 7+7+1+1; since
  2026-08-11 an even captain/ally half-split)*: the static parity squad table
  is not roster-aware, so a seating change can silently regroup squads across
  owners. Replace it with membership learned from Stencil chat/presence
  before treating squad liveness as representative.
