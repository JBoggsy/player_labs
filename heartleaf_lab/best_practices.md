# Heartleaf best practices

Apply the [shared practices](../best_practices.md) with these game-specific rules.

- Only hosts score: hosted food is multiplied by guests. Gathering alone cannot
  produce a positive score without attendance; measure recruitment as well as food.
- Establish the deterministic invitation behavior before adding model-dependent
  persuasion. A model call must provide measurable benefit over that working baseline.
- Read exact timing from the game. The weekday prefix is part of clock labels;
  dinner display time and dinner resolution time are distinct. See
  [gameplay](docs/heartleaf-gameplay.md) for the schedule.
- Log every sensed value used by a decision gate, including missing values. A silent
  missing clock or target can disable behavior while the policy still appears healthy.
- A player's presence at home on the day boundary does not prove they hosted;
  use the resolved event and score.
- Hearing depends on rendered chat visibility, including map, camera clipping,
  walls and bubble lifetime. Do not replace it with an arbitrary distance radius.
- Treat WebSocket keepalive and game/model stalls as transport questions. Follow
  Cady's bridge settings and inspect disconnect evidence before changing strategy.
- The selected manifest defines the artifact, while source and replay compatibility
  must be established separately. A similarly named tag is not proof of parity.
- Verify replay expansion using the hash/complete indicators. Build tools in an
  isolated directory so sibling dependencies cannot shadow the pinned game dependencies.
  Include the game's required runtime assets.

Read [replay tools](docs/replay-tools.md), [Cady](cady/README.md), and the
[game reference](docs/heartleaf-gameplay.md) for implementation details.
