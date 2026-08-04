# stencil v1 — design

*2026-08-03. Living document; updated as the implementation reveals new
information.*

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
- **Non-goal (v1)**: posts (covered-sightline fighting positions), battle
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
| `game teams <n> map <w>x<h>` marker | team count, colors prefix, seat dealing, roster inference (teams + size class → 4 vs 8 seats/team) |
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
action (movement/aim/fire/peek-duck/grenade, minus post paths), fight
(sightline-field scoring → exact rays; ≤8 candidates/tick is cheap), chat
(grid dims from the map; protocol unchanged), squads (roster-aware tables,
derived geometry; command layer still OFF), items (spawn table now
**discovered from sightings** — generator placements are per-map), strategy
(the ladder minus plan/POI/post rungs), policy orchestration, tracing, and the
`STENCIL_*` configuration layer.

Notable default flips vs beacon: `FIREFIGHT`/`FOCUS_CLAIMS` default **ON**
(they were beacon's champion configuration, set per-upload there).

## Performance envelope

The one-time WorldMap build is the only heavy step: native summed-area erosion,
cover extraction, and lazy Dijkstra over the largest grid (giant 2-team,
~402x215 = ~86k cells). The measured giant-map p95 was 419 ms under 16-process
contention; per-tick work is label scans, constant-time lookups, and occasional
A*. The native websocket loop has no keepalive timeout that can interrupt a
slow first frame.

## Risks / open questions

- **Seats-per-team inference** (teams + width≥2000 → 8) is a heuristic. The
  `1v1` duel now exists and intentionally degrades through this approximation;
  the wire still states no muster.
- **Item discovery** starts blind — early-game fetches only happen after
  sightings. If evals show med-kit latency mattering, seed guesses from the
  RULES layout rules per shape.
- **4-team threat model** is beacon's 2-team model with more colors; no
  third-party reasoning yet (e.g. don't break up a rival-vs-rival fight).
- **Live seating splits teams across policies** (7+7+2 etc.): chat protocol
  only reaches our own seats; squads treat non-protocol allies as anonymous
  teammates — measure whether coordination assumptions hurt in `2v2`.
