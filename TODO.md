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

- Re-verify the mechanics documents at polyworld `f2ab9598` (deployed 2026-09-17): `attackMove`
  is registered to BASIC (800 work units), two god-guard gate towers flank each god and must
  both fall before the god takes damage, footmen path to the next enemy building after their
  lane waypoints, and barracks ids are assigned by map order. Update `policy-capabilities.md`,
  `wiki/mechanics.md`, `leveling-economy.md` (fort exposure) and the Currency blocks.
- Local `run-episode -n 3` produced identical games for seeds 2026 and 2028; check whether the
  match seed only affects animation choices before trusting seed counts as independent samples.

- Requested engine change 14 (damage/heal/kill events in the recording) is still open at the
  deployed `f2ab9598`; raise it with the polyworld maintainer (James sends it).
- Agree with Andre who owns the `game-guide`, `hero-statistics`, and `player-standings` wiki
  pages: his Polyworld Buff sync job and our `docs/wiki/` copies both write them.
- Tell the polyworld maintainer that `coworld/gota/guide.md`, the manifest readme, and
  `docs/index.html` say barracks have 900 HP while `sim.nim:3527` gives them 950.
- Regenerate the four rendered reports under `docs/reports/gota-*-2026-09-15.html` from
  their Markdown sources, which are now verified at `7365e4e9`.
- Join the replay expander's per-seat table (`tools/replay_stats.py --json`) into
  `tools/compare.py` and `tools/features.py` on `(episode_id, position)` so every seat,
  not only ours, gets exact last hits, kills and deaths; keep `damage` a stub until change
  request 14 lands.
- Decide the miner's ladder score: confirm whether the league applies 100 or 200 XP per
  simulated minute as the time penalty, then add `--score ladder` to `tools/miner_rows.py`.
- Fix `coworld-episode-artifacts/fetch_artifacts.py` to sniff the `POLYWORLDREPLAY` magic
  and save GotA replays as `replay.bin` (shared skill; needs a go-ahead).

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
