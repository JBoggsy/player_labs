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
  `tools/deployed_ref.py` at the start of a session. Polyworld `main` (`e127989`,
  2026-09-15) already carries our observation requests 1–13, a tower rebalance, and two
  heal buffs; none is live. A policy that references the new names
  ([docs/policy-capabilities.md §3.6](docs/policy-capabilities.md)) fails to compile on
  the deployed build, so gate any use of them on the deployed commit.

## Public discussion

- The hero-role proposal is public: `post_f177c436-fd32-4923-bac9-56595a5142f9` in the
  Gods of the Arena forum, posted as the James Botts player. A launchd job
  (`com.jamesboggs.forum-agent.gota`, every 30 minutes) runs the standing forum agent
  (`tools/forum_agent/`, brief in `forum_agent/brief.md`); it records what the thread
  produces in [docs/roles.md](docs/roles.md) and flags items for James in
  `forum_agent/state.json` under `attention`.

## Unresolved constraints

- Damage and heal attribution is not recoverable from replays; `damage` is a stub in the
  expander design until [requested change 14](docs/requested-game-changes.md) lands (still
  open on `main`).
- The observation expansion is merged but not deployed. Until it is, the burst-killer and
  siege rules must work from the deployed surface (no `selfTarget`, no `objectTarget`, no
  spell warnings); decide whether the first upload targets the deployed surface or waits.
- Mono-team versus mixed-team rosters are a platform setting; confirm which the target
  league or experience request uses before reasoning about allies.
- The public wiki still carries the old tower-HP numbers (600/800/1,000); the corrected
  local pages await a public-write go-ahead.

## Next decision

James adopted the role model in [docs/roles.md](docs/roles.md) as the provisional basis for
the first policy (2026-09-15): per-class branches for burst killer, duelist, siege front, and
healer, with the farm priority in that document. Next: agree which role behavior to write
first, write it, upload under James Botts, and run the first experience request. Candidate
first behavior: the burst-killer rule (hold the ultimate for an enemy hero), which applies
to seven of ten heroes. The scaling report's three-phase model and the economy report's
last-hit rule remain the supporting hypotheses; see
[TENTATIVE_LESSONS.md](TENTATIVE_LESSONS.md).
