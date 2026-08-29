# Emerg-ant lab — agent guide

Read the root [`../AGENTS.md`](../AGENTS.md),
[`../best_practices.md`](../best_practices.md), and
[`../user_preferences.md`](../user_preferences.md) first. They define the speed-first
evaluate → report → decide → implement → upload loop and the human-only league
submission gate. This file adds Emerg-ant-specific rules.

## Startup read order

1. [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md)
2. [`README.md`](README.md)
3. [`docs/emerg-ant-gameplay.md`](docs/emerg-ant-gameplay.md)
4. [`best_practices.md`](best_practices.md) and
   [`user_preferences.md`](user_preferences.md)
5. [`TENTATIVE_LESSONS.md`](TENTATIVE_LESSONS.md)

Use the dated [founding recon](docs/recon/emerg-ant-2026-08-20.md) only for the
retired 0.6.1 / GameVersion 52 history. Re-resolve live releases, leagues, rosters,
and CLI versions before relying on dated state.

## Current state

As of 2026-08-21, `stencil-ant:v6` remains the promoted player
(`3da684b3-c68a-46c7-9d3a-c25d36a60afe`). It has never been submitted. The newer
uploaded v7 experiment was rejected after its nominal crowd-redirection mechanism
produced zero sampled activations. Immutable history is in
[`emergant/stencil_ant_gv57_nim/VERSION_LOG.md`](emergant/stencil_ant_gv57_nim/VERSION_LOG.md).

The active player starts from the exact canonical GameVersion 57 Nim baseline, adds
telemetry, routes carriers through two offset queen-delivery lanes, and implements a
bounded danger-pheromone queen alarm. V6 keeps v5's precise launch conditions and
moves the active defense post from 58 to 68 px outward. It beat an all-in local queen
rush 5–1, then beat the current champion 3–1 in a four-episode hosted color swap. A
same-window v5 control split 2–2; the favorable delta is promising but still small-n.

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
have a real cost: never use one for self-play; target a current real opponent and start
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
- Do not add compatibility for the retired GV52 cache-race behavior to a GV57 player.
- The user has explicitly authorized local self-play for iterative improvement. Keep
  it matched by seed and seat orientation; do not substitute paid hosted self-play.
- Uploading is inert and routine. **Never submit to the league without James's explicit
  permission in the current task.**

## Lab hygiene

Keep all Emerg-ant-specific source, analysis, fixtures, and docs under this directory.
Update [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md) as facts change and append uploads
to the future player's `VERSION_LOG.md`. Capture candidate lessons eagerly in
[`TENTATIVE_LESSONS.md`](TENTATIVE_LESSONS.md); the root hooks rotate and nudge it.

When a work thread finishes, reconcile the context, propose the next decision, and
pause. Do not auto-chain into gameplay strategy changes.
