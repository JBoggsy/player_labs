# Documentation audit — 2026-08-29 (stencil-centered)

Scope: every doc describing the stencil policy, ahead of the strategy-rework
epoch (body/mind separation). Method: docs treated as claims and verified
against the v68 source (`paintbot/stencil_nim/`), `VERSION_LOG.md`, and live
platform state (`coworld leagues`/`memberships --mine`/`deploy-audit`,
controller state on this Mac).

## Headline findings

1. **Orientation docs were five champions behind.** `README.md` and
   `AGENTS.md` status blocks were frozen at "v54 champion, verified
   2026-08-07" while WORKING_CONTEXT/VERSION_LOG recorded the completed
   navigation rework and v68's championship (2026-08-14). Both architecture
   paragraphs still described the pre-rework stack (erosion nav grid,
   flow-field movement, per-opponent posts) and misordered the strategy
   ladder. Fixed against code.
2. **Live drift found during verification (new facts, now recorded):**
   - A second league, **Elite Paintbot** (`league_15cf0b94`, created
     2026-08-19), lists stencil:v68 competing (`lpm_243bbc99`) — previously
     unrecorded anywhere.
   - Canonical paintbot is **0.7.242** (`cow_ed016cb2`); the build pin
     remains 0.7.215 (game-pin review already parked in TODO, gap widened).
   - **The campaign controller is broken**: its LaunchAgent still points at
     the pre-rename repo path (`personal_labs_paintbot/`); FileNotFoundError
     every poll since ~2026-08-26, no orders placed.
   - coworld CLI is 0.1.39 and `coworld list` now shows only your own
     uploads, silently breaking AGENTS.md's staleness-check one-liner;
     `coworld deploy-audit` is the working replacement.
3. **Design docs lagged the rework they governed.** The nav-rework sketch had
   no v67/Layer-5 close-out (added, including kill-list honesty notes: the
   threat-axis kill only half-landed — `threatAxis`/`sweepTarget` still drive
   idle aim sweep); `stencil-v1-design.md` still presented erosion/choke-
   rally/flow-field internals as current (freshness banner + rework addendum
   added); the port doc's module map omitted `planner.nim`/`danger_field.nim`
   and still claimed erosion (rewritten); six shipped nav design docs and the
   rl-exhaustive-baseline report were missing from `docs/README.md` (indexed).
4. **Seating claims were stale in five places.** The 2026-08-11 commissioner
   change (even captain/ally split, true `1v1` mode, mode↔variant
   decoupling, 10x10 rollback) was recorded in the tournament doc but not
   propagated to README/AGENTS/WORKING_CONTEXT/v1-design/communication doc.
   All fixed; noted that under the even split the parity squads land within
   one owner's block (derived, not hosted-validated). James's
   `user_preferences.md` still cites 7+7+1+1 — his text, left untouched.
5. **`tools/compare_stencil.py` was mislabeled** in README's layout as the
   A/B metric adapter; it is the wire-decision parity comparator. The
   pot-scoring-aware `compare.py` adapter is still missing.
6. **WORKING_CONTEXT reseeded for the pivot** per its own contract: the
   v59-v67 history stack compressed to a digest (full record stays in
   VERSION_LOG + layer docs), stale v54-era next steps replaced, and the
   verified body/mind boundary map written in as the new current objective.

## Verified body/mind boundary (for the strategy rework)

`policy.decide` → `perceive` → `updateBeliefCore` → role assignment (in
policy.nim) → `strategy.decideObjective` (priority ladder → one typed
`Intent`: kind, validated point, arriveRadius, movingGoal, clampToEndzone,
suppressFireFreeze, profile, micro set; reason = telemetry only) →
`action.resolveAction` (corridor-bounded follower over the weighted-A*
planner + combat overlay). Known leaks, recorded in WORKING_CONTEXT:
threat-axis reads in action.nim, defender post assignment in policy.nim,
chat as a policy.decide side channel, strategy mutating Belief telemetry.

## Files changed

`README.md`, `AGENTS.md`, `WORKING_CONTEXT.md`, `docs/README.md`,
`docs/stencil-communication.md`, `docs/designs/stencil-v1-design.md`,
`docs/designs/stencil-nim-port.md`,
`docs/designs/nav-rework-sketch-2026-08-11.md`, `../TODO.md` (game-pin
update; Elite Paintbot + controller-repair entries; nav rework closed with
survivors), `TENTATIVE_LESSONS.md` (five candidate lessons). Dated reports
and recon were left untouched per the supersession rule.
