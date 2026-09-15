# Crewborg architecture

Crewborg is a Sprite-v1 policy for Crewrift. The runtime turns a retained scene
into a percept, updates episode-local belief, selects an objective, and converts
that objective into movement, interaction and chat input.

## Components

- Transport maintains scene objects, camera state, walkability and visibility.
- Perception reads labels and decoded map/shadow channels into game facts.
- Belief retains player tracks, phase, task state, cooldown estimates and social evidence.
- Strategy selects role-appropriate modes. Modes emit intents; the action layer
  turns them into button masks and chat.
- Meeting and commander model calls run through the configured backend. Decision
  deadlines and deterministic fallbacks keep gameplay progressing when calls fail.
- Structured traces expose decisions, input evidence, outcomes and model-call costs.

## Current references

- [Package guide](README.md): entry point, runtime configuration and build.
- [Perception and belief](docs/perception-and-belief.md): scene interpretation and state.
- [Player tracking](docs/agent-tracking.md): sightings and movement estimates.
- [Crewmate play](docs/crewmate-play.md): tasks, reports, meetings and survival.
- [Imposter play](docs/imposter-play.md): search, recon, hunt, evade and meeting tactics.
- [Suspicion](docs/suspicion.md): evidence and probability updates.
- [Meetings](docs/meetings.md): chat, voting, deadlines and model calls.
- [Commander](docs/commander.md): optional gameplay direction and priorities.
- [Trace logs](docs/trace-logs.md): diagnostics and evidence fields.
- [Vision model](docs/designs/vision-model.md): observation visibility and prospective geometry.

## Invariants

Keep mutable state scoped to an episode. Use authoritative scene labels and
configuration to interpret identity, roles, teams and geometry. A missing observation
is not proof of absence; distinguish visible facts, retained estimates and inferred intent.

For an imposter, seeking and kill execution are separate responsibilities. Search
keeps crew reachable, recon times approach against cooldown, hunt chooses and
intercepts a victim, and evade determines post-kill positioning. Evaluate these
components using opportunity-conditioned metrics as well as final wins.

For a crewmate, report and vote actions must respect phase and submission semantics.
Voting intent, cast vote and resolved ejection are distinct events. Attribute each
result to the exact seat and episode before measuring a policy effect.

Verify tactical changes with current matched opponents. Changes in game configuration,
role composition or the opponent field can invalidate a previously useful threshold.
Unit checks establish local behavior; hosted evidence establishes field performance.
