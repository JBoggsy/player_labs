# Agricogla signal catalog — the observability search space

The master list of every signal extractable from an agricogla replay, grounded in
the engine (`cogame-agricogla/src/shared/engine/`, verified file:line). This is the
raw material for **analysis lenses** — and *which lenses are worth looking at* is
itself an experiment (see LENS_EXPERIMENTS.md). Build lenses from these signals;
measure which lenses actually change our understanding (lead to winning mutations).

## The richest source: the `log` event taxonomy (GameState.log, GameEvent{round,playerIdx,type,text})
23 distinct event types the engine emits — this is where most signal lives:
setup, take, plow, sow, **bake** (grain→food), **cook** (animal/veg→food), renovate,
**family** (growth), breed, build (room/stable), fences, **occupation**, improvement
(minor/major), pass, starting, **field** (harvest yield), **feed**, **begging**,
release (animal overflow), phase, **harvest**, reveal (round-card), scheduled.

## RAW signals (directly in the replay)
- **Final score by category** (`scoring.ts:12-88`): Fields, Pastures, Grain, Veg,
  Sheep, Boar, Cattle, Unused-spaces(−1 ea), Fenced-stables(+1 ea), Rooms
  (clay×1/stone×2), Family(+3 ea), Begging(−3 ea), Card vp+bonusVp. (Tiers in §3.5
  of STRATEGY.md / agricogla-player.)
- **Per-harvest food**: at rounds {4,7,9,11,13,14} — food available vs needed, via
  `feed`/`begging` events; begging count = food shortfall.
- **Family-growth timeline**: `family` events → which round each member was born.
- **Action taken each round**: actionSpaces[].occupiedBy + `take`/placement events.
- **Cards played + WHEN**: `occupation`/`improvement` events with round.
- **Bread baked**: `bake` events (grain→food). **Crops sown**: `sow`/`field` events.
- **Renovation sequence**: `renovate` events (wood→clay→stone).
- **Animal releases**: `release` events (capacity overflow — pasture under-build).

## DERIVED signals (computed per-player per-game)
- **Points per worker-placement** = score / total placements (action efficiency).
- **Food surplus/deficit margin at each harvest** (when did feeding risk emerge).
- **Rounds-to-first-cooker** (when the food engine activated; `cook` event round).
- **Grain sown vs baked** (crop-engine vs bread split — STRATEGY §1.3).
- **Category-coverage breadth over rounds** (generalist vs specialist; §1.4).
- **Tempo** = cumulative placements per round (front- vs back-loaded).
- **Engine-idle turns** (had a worker, took nothing useful / forced waiting).
- **Family-growth-vs-food**: was each grow ever actually fed? (the §1.2 trap).

## COMPARATIVE / opponent signals (relative to the other 3 seats)
- **Score-gap trajectory** per harvest (my score − leader; when the game was decided).
- **"Beaten to a space"**: a space MY policy scored highly but another seat took
  first (needs policy weights + occupancy by turn order) — contention/blocking.
- **Who won the family-growth space** (4p: only ~2 of 4 can grow in stage 2; §1.7).
- **Relative feeding pressure** (my begging − avg begging).
- **Resource-competition timeline** (who took the scarce wood/clay/reed spaces first).
- **Turn-order advantage** (did seat order decide contested spaces).

## STRATEGIC QUESTION → signal map (what to look at, and why)
| Question | Signals |
|---|---|
| Did we starve? when? | begging events by harvest round; food deficit margin |
| Did we grow uncosted? (§1.2) | family events × "was it fed?" verdict |
| Breadth vs depth? (§1.4) | category-coverage; per-category points |
| Sow before bake? (§1.3) | grain sown vs baked; rounds-to-cooker |
| Beaten to key spaces? (§1.7) | beaten-to-a-space; who won family-growth/wood |
| Card timing | occupation/improvement event rounds; cards-played count |
| Tempo / decisiveness | placements per round; engine-idle turns |

## Composite ideas (combine signals — hypotheses to test as lenses)
- **Economic-health index** = (food+grain+veg) − 2×begging, per round.
- **Begging-resilience** = 1 − begging_taken / num_harvests.
- **Action-sequencing quality** = avg goodness (pile size) of spaces taken vs available.

*Note: this engine checkout may lag the authoritative
Metta-AI/metta:packages/cogweb/games/agricogla — re-verify tiers/events there
before encoding a number. The EVENT TYPES and structure are stable.*
