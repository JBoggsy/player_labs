# Emerg-ant gameplay contract

Self-contained reference for canonical **Emerg-ant 0.9.1 / GameVersion 57**,
verified 2026-08-21 against
`Metta-AI/coworld-emerg-ant@1e0be3f1ecabf2fc70adb8af81818a9947281cc9`.
Re-resolve live state before operations.

## Match shape

- 32 seats split into two colonies by alternating seat parity.
- Each submitted policy controls one colony and is replicated into 16 seats.
- Eight ants per colony start active: one immobile queen and seven workers.
- Eight more copies begin as reserve brood.
- Eight neutral food patches replenish around the map.
- Each food delivery to the colony's queen hatches one reserve ant.
- The first colony to reach all 16 active ants wins.
- Killing a queen collapses its colony and is an alternate victory path.

This is not the retired GameVersion 52 enemy-cache race. There are no repeated enemy
caches, guns, items, lives, or capture-zone deliveries in GV57.

## Food and brood

Workers forage from neutral sprites labeled `food patch`. A carrier is labeled
`food carried` and must return to its own queen. A successful delivery increases
the colony's active population by hatching one reserve policy copy. Food is therefore
both the scoring objective and an economic multiplier: earlier deliveries create more
workers for later foraging, defense, and combat.

The queen is fixed at the colony center. Navigation that merely targets the queen's
center can congest or oscillate on the nest boundary; delivery approach geometry is a
meaningful policy decision.

## Combat

Combat is physical contact using `weapon mandibles`; the action is button A. There
are no guns or inventory items. Workers can contest patches, carriers, approaches, and
the opposing nest. Queen death is decisive, so offense and nest defense have a direct
strategic tradeoff.

## Pheromones

Agents can emit typed pheromones at an explicit rate. The available semantic types
include scout, food, danger, and home signals; rate ranges from off through urgent.
Pheromones are environmental observations rather than a private message channel, so
both colonies can reason about them.

Button C encodes pheromone selection/emission combinations. Preserve the canonical
protocol implementation unless deliberately testing a signaling change; observation
labels and bit masks are exact contracts.

## Observation and action contract

The policy speaks retained/delta Sprite v1. Important labels include:

- `food patch`
- `food carried`
- `weapon mandibles`
- queen and team-qualified player labels
- typed/rated pheromone labels

Directional movement and buttons are level-held masks. The canonical Nim baseline in
`players/baseline/` at the pinned source commit is the compatibility floor for
parsing, state retention, navigation, and actions.

## Evaluation

Outcome alone is too sparse for diagnosis. At minimum attribute:

- colony win and final active population;
- food pickups and completed deliveries;
- carrier travel time and stuck time near the nest;
- queen survival;
- contact-combat activations and kills;
- pheromone type/rate usage.

For local paired comparisons, pin the seed and run both seat orientations. For paid
Experience Requests, never use self-play: use a current real opponent, pin immutable
policy versions, and rotate seating so both colony colors are covered.
