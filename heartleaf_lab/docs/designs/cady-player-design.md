# Cady architecture

Cady is a deterministic Heartleaf policy using the SDK SpriteV1 bridge. The
bridge owns transport and scene decoding. Cady owns perception, belief, navigation,
clock-driven strategy, invitations and action selection.

## Decision flow

1. Read labeled sprites and clock state into a Heartleaf observation.
2. Update episode-local belief: identity, home, food, gardens, gnomes and invitation state.
3. Select gathering, invitation or hosting behavior from the game clock and current state.
4. Route movement over the baked walk grid, with stuck detection and replanning.
5. Convert intent into input masks or templated chat; verify interactions before repeating them.

The configured schedule gathers before 3 PM, tours other houses for invitations,
then hosts through dinner resolution. Scoring is hosted food times guests, so the
invitation path is part of the policy's core loop.

See [Cady's guide](../../cady/README.md) for files, tracing, build and execution;
[gameplay](../heartleaf-gameplay.md) for timing and scoring;
[map reference](../heartleaf-map.md) for geometry; and
[villager attendance](../villager-dinner-attendance.md) for invitation behavior.

Model-dependent social control is a [proposal](cady-social-llm-controller.md), not
part of the deterministic runtime. Gameplay changes require a selected objective
and attributable evaluation.
