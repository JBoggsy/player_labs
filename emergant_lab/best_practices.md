# Emerg-ant best practices

These practices layer on top of [`../best_practices.md`](../best_practices.md).

## Pin the complete deployed identity

Always record Coworld ID, semantic version, manifest hash, source commit, and
GameVersion together. The old 0.6.1 / GV52 cache race and current 0.9.1 / GV57 colony
foraging game are materially different contracts despite sharing the repository name.

## Measure colonies without multiplying the sample size by 16

The results schema repeats team outcome across all 16 policy copies. Treat each
episode/team as one win observation. Aggregate individual `captures`, kills, and
deaths within a colony for mechanism-level reporting.

## Separate queen-collapse wins from forage wins

The first colony to 16 active ants wins through food delivery, but a queen kill
collapses the colony immediately. Report those endpoints separately: a 1–3 queen-loss
is not evidence that the losing policy's forage rate was intrinsically worse.

## Match local comparisons by seed and orientation

For every local candidate, run the same seeds with candidate on each seat parity.
Report per-seed sweeps, total colony wins, and deliveries. Side effects can dominate a
single episode, so never call an unpaired one-off a same-seed comparison.

Always pass `--variant emerg-ant` to `coworld run-episode`. Supplying the live
manifest alone does not select live gameplay; the CLI otherwise uses its certification
fixture (`maxTicks=300`, `hitPoints=1`, `forageGoal=1`), which is not valid strategy
evidence.

## Never buy self-play with XP

Experience requests cost money and real opponents cost the same as self-play. Use
local episodes for self-play and paid requests only against a current real opponent,
with immutable policy versions and color rotation.

## Treat roles as behavior, not labels

The inherited Stencil role enum does nothing by itself in the compact GV57 controller.
A worker logged as `HomeDefender` still forages unless the decision function explicitly
implements guard positioning and interception. Validate roles from objectives and
positions in telemetry, not startup labels.

## Reuse protocol code; re-derive strategy

The exact canonical GV57 baseline is the compatibility floor for Sprite v1 parsing,
navigation, action masks, and pheromone control. Paintbot/CTF architecture is historical
evidence only; GV57 food, brood, contact combat, queen, and pheromone semantics must be
derived from the pinned game source.
