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

## Gods of the Arena

- Send `gods_of_the_arena_lab/docs/requested-game-changes.md` to the polyworld maintainer
  (James sends it); then mark items done as they land and drop any the host now exposes.
- Publish the tower-HP correction (1,200/2,400/4,800) from `docs/wiki/mechanics.md` and
  `docs/wiki/game-guide.md` to the public wiki once James authorizes the write.
- Build the replay expander per `docs/replay-format.md` §4 (Nim core at the deployed commit,
  Python tape decoder, `compare.py`/`features.py` adapters); keep `damage` a stub until
  change request 15 lands.
- Fix `coworld-episode-artifacts/fetch_artifacts.py` to sniff the `POLYWORLDREPLAY` magic
  and save GotA replays as `replay.bin` (shared skill; needs a go-ahead).
- When `tools/deployed_ref.py` reports a new deployed commit, re-run the checks in
  `docs/research.md`; `main` already carries a tower rebalance (900/1,200/1,800 HP).

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
