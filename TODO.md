# Open work

These are unresolved tasks, not authorization to resume gameplay work. Reproduce
an issue against the current code and selected game before implementing a change.
Remove a task when it is complete.

## Shared tools

- Add exact league, policy-version and membership selectors to the lifecycle monitor.
- Include failed episode attempts consistently in policy artifact coverage.
- Handle `Retry-After` consistently across shared clients.
- Supply authoritative game identity and replay coverage before connecting behavioral
  miners to Crewrift and Heartleaf data; do not invent missing provenance.
- Verify artifact and roster integration end to end during the next authorized evaluation.
- Support large trace-field projection in warehouse ingestion to bound memory use.
- Check CTF comparison statistics use one team outcome per episode.

## Paintbot

- Check the selected league's runtime and game contract against the Stencil build
  configuration before resuming policy work.
- Review the campaign controller's repository paths and restart it only within
  an authorized campaign.
- Validate danger-field meaning and the effect of fire-windup movement separately.
- Expand learned-policy replay and expert diversity; evaluate temporal-state choices
  with matched data and current runtime measurements.
- Make squad formation match the actual roster and support reconnection when
  communication is limited by distance.
- Generalize event-warehouse team outcomes beyond two colors.
- Resolve whether the policy's observations expose the roster information needed
  for coordination; do not infer it from map size.

## Crewrift

- Reconcile the lab's player SDK dependency with the policy's actual imports.
- Verify ghost tasking, meeting-call fallback and teammate detection against current
  complete-episode traces before choosing a behavioral change.
- Check whether `vote_bar` telemetry describes the actual event it is named for.
- Evaluate social-deception hypotheses with the human, including activation tracing.
- Assess whether shared SDK transport can replace the policy's own bridge.
- Check the game contract for turn-completion signalling and its effect on iteration speed.
- Review tracing verbosity using measured runtime cost and evidence coverage.

## Vanilla WoW

- Resolve the selected game's current movement contract and run an authorized
  complete-episode comparison before drawing conclusions about navigation.

## Inactive CTF

- Determine current Beacon participation before considering retirement. Retirement
  requires explicit authorization and does not follow from documentation maintenance.
