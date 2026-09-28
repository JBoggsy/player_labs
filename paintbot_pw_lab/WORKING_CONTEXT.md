# paintbot_pw_lab working context

Use the current user request to establish the objective, scope and next decision.
Resolve the active game configuration, policy identity and roster through the platform
before evaluating or changing live participation. Source code and current API responses
define behavior; this file must not substitute for a live-state query.

Maintain only the active objective, unresolved constraints and next action here.
Replace completed or superseded context in place.

## Objective

None chosen yet. The lab is stood up (2026-09-28): source-verified references at
`7b2b19f5` / coworld 0.3.65, the deployed-commit check, and a pinned engine build with
hash-checked replay validation and local runs. No policy has been written or uploaded.

## Identity and presence

- Account players: "James Botts" (default) and "Games Bond". Neither has a policy,
  membership or submission in either paintbot-pw league. Confirm `uv run softmax status`
  shows the intended player before the first upload (`coworld-player-swap` skill).
- Credits: 20,000 balance at the cap, refilling ~1,429/day (2026-09-28). A league-like
  episode costs ~0.3 credits.

## Decisions for James

1. **Target league.** Recommended: the main teams ladder
   (`league_b9458ff8-…`), which has a real field (Aaron L, David B, Richard H) and stable
   scheduling. Heartland opened today with one filler policy in 14 of 16 seats and rules
   still moving.
2. **Player identity** for this game (James Botts, Games Bond, or a new one).
3. **Starting policy lane:** plain BASIC from `base.bas`, or the Jev LLM advisor
   (`jev.bas`; needs to confirm the league grants seats an LLM budget), or the neural
   ZIP lane (David's `daveey-pw-neural` is #2).

## Next step (proposed)

Build the per-seat instrument set from [evidence-pipeline.md §8](docs/evidence-pipeline.md)
(`seat_stats.nim`, `pw_episodes.py`, `compare.py`, `features.py`), then upload `base.bas`
unchanged as the baseline and measure it against each current champion with pinned
8-seat opponent rosters at seed 2026.

## Open constraints

- Releases ship several times a day and the league lags the newest tag (round 2237 still
  ran 0.3.64 when 0.3.65 was tagged). Record `coworld_version` per episode and never pool
  rules versions in one comparison.
- League `game_config.seed` is a constant 2026; engine seeds may still differ per job
  (inferred). Check episodes are not near-duplicates before treating them as independent.
- Seat logs for our own hosted policies are expected but not yet exercised.
- Local runs use `behind_lives` 1; the league pays 5.
