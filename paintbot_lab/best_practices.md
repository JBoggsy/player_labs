# Paintbot best practices

Apply the [shared practices](../best_practices.md) together with these game-specific rules.

- Match the selected control mode, roster and configuration. Stencil's direct-input
  interface and the public battle-royale playbook interface are distinct contracts.
- For campaign analysis, resolve the cell's mode, map identity and actual participant
  positions. Map size and variant name do not determine team membership or policy layout.
- Derive generated geometry from observations. Keep map caches and derived navigation
  state scoped to the episode. Reject missing geometry instead of displaying a plausible
  fixed arena over an unrelated replay.
- Resolve team colors and wins from configuration/results; never infer them from slot parity.
- Break results down by variant, team, roster and map scale before drawing a general conclusion.
- Separate a completed game from complete evidence. Report missing logs, failed seats
  and unsupported trace formats explicitly.
- Check the source and resolved configuration before assigning meaning to aim, visibility,
  pickup, scoring or timing fields.
- A locked consensus vote must have the same value in local state, quorum counting and
  rebroadcast. Test consistency across all three representations.
- Measure coordination among agents that can participate. Dead teammates cannot demonstrate
  a liveness failure. Range-limited communication also needs an explicit rendezvous mechanism;
  retries alone cannot reconnect physically separated squads.

Use [evaluation setup](docs/tournament-like-experience-requests.md) and
[analysis tools](docs/analysis-tools.md) for concrete workflows.
