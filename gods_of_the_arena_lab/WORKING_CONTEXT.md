# gods_of_the_arena_lab working context

Use the current user request to establish the objective, scope and next decision.
Resolve the active game configuration, policy identity and roster through the platform
before evaluating or changing live participation. Source code and current API responses
define behavior; this file must not substitute for a live-state query.

Maintain only the active objective, unresolved constraints and next action here.
Replace completed or superseded context in place.

## Objective

Create the first Gods of the Arena policy under the **James Botts** player
(`ply_53fb05a6-73d1-494d-ab6c-8d566660d7ce`, the account default). No policy has been
written or uploaded yet; the research phase is complete (see
[docs/research.md](docs/research.md)).

## Identity and environment

- The coworld credential store holds a James Botts player session (set with
  `softmax.auth.set_active_player_session`; the `coworld-player-swap` skill's
  `save_player_session` call no longer exists). Player tokens last about 24 hours; re-mint
  before an upload and confirm with `uv run softmax status` (`subject_type: player`).
- The account's other player, Games Bond, owns the `games-bond-gota` policy; its private
  logs are not readable under the James Botts session.
- Deployed polyworld commit `5422fb0c` (coworld version 2026.9.15.1). Check with
  `tools/deployed_ref.py` at the start of a session.

## Unresolved constraints

- Damage and heal attribution is not recoverable from replays; `damage` is a stub in the
  expander design until [requested change 15](docs/requested-game-changes.md) lands.
- Mono-team versus mixed-team rosters are a platform setting; confirm which the target
  league or experience request uses before reasoning about allies.
- The public wiki still carries the old tower-HP numbers (600/800/1,000); the corrected
  local pages await a public-write go-ahead.

## Next decision

Agree the strategic shape of the first policy with James, then write it, upload it under
James Botts, and run the first experience request. The scaling report's three-phase model
(burst, transition, attrition) and the economy report's last-hit rule are the starting
hypotheses; see [TENTATIVE_LESSONS.md](TENTATIVE_LESSONS.md).
