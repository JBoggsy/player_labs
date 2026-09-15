# Emerg-ant lab — agent guide

Read the root [`../AGENTS.md`](../AGENTS.md),
[`../best_practices.md`](../best_practices.md), and
[`../user_preferences.md`](../user_preferences.md) first. They define the speed-first
evaluate → report → decide → implement → upload loop and the human-only league
submission gate. This file adds Emerg-ant-specific rules.

## Startup read order

Read [the lab README](README.md), [gameplay](docs/emerg-ant-gameplay.md),
[working context](WORKING_CONTEXT.md), [best practices](best_practices.md),
and [preferences](user_preferences.md).


## Policy

The Nim policy under `emergant/stencil_ant_gv57_nim/` adds telemetry, carrier routing
and queen-defense behavior. Select the policy artifact and evaluation objective with
the human, and resolve current participation through the platform.

## Source of truth

- Deployed pins: [`tools/versions.env`](tools/versions.env)
- Game contract: [`docs/emerg-ant-gameplay.md`](docs/emerg-ant-gameplay.md)
- Ultimate authority: the pinned `Metta-AI/coworld-emerg-ant` source and current
  Observatory manifest
- Paintbot code: reusable architecture evidence, never authority for Emerg-ant
  mechanics or constants

The name is **Emerg-ant** in game-facing prose and identifiers. The directory stays
`emergant_lab` to match this repository/workspace's established spelling.

## Evaluation and reporting

Use matched local play for cheap self-play and iterative testing. Experience requests
consume [granted credits](../docs/xp-credits.md): never use one for self-play; target a current real opponent and start
artifact streaming immediately after creation. For every comparative claim:

- keep roster, roles, and time window matched;
- collapse `win` to one observation per episode/team rather than counting eight
  identical seat rows;
- aggregate per-seat `captures` to colony delivery progress;
- separate delivery, combat, survival, navigation, and pheromone hypotheses;
- inspect policy traces/replays before turning a correlation into a behavioral claim.

`coworld run-episode` defaults to the certification fixture even when given the live
manifest path. Every strategic local run must pass `--variant emerg-ant`; otherwise
the resulting 300-tick, one-hit-point, forage-goal-1 episode is invalid evidence.

The live competition uses 32 seats split across two teams. Resolve the active league
and roster afresh before designing an experience request.

## Implementation boundaries

- Change one attributable component per iteration.
- Keep strategy knobs separate from logic.
- Re-derive movement, combat, timing, visibility, and input constants from the
  pinned Emerg-ant source before adapting any Paintbot module.
- Pheromones are public environmental state. Never treat them as private radio.
- The user has explicitly authorized local self-play for iterative improvement. Keep
  it matched by seed and seat orientation; do not substitute hosted XP self-play.
- Uploading is inert and routine. **Never submit to the league without James's explicit
  permission in the current task.**

## Working context and guidance

Keep the active objective, scope, unresolved constraints and next decision in
[WORKING_CONTEXT.md](WORKING_CONTEXT.md). Keep testable unresolved ideas in
[TENTATIVE_LESSONS.md](TENTATIVE_LESSONS.md); promote supported rules to
best_practices.md and remove resolved claims. Follow the
[shared learning workflow](../docs/learning.md). Update these documents in place;
do not create session archives, version logs or change narratives.
