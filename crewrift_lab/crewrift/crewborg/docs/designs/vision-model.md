# Crewrift's real vision model, and where crewborg approximates it

## The real mechanic

Crewrift vision is **not a circular radius**. Per-player camera + visibility is computed
in `.cache/crewrift-src/<ref>/src/crewrift/sim.nim`:

- `playerView(sim, playerIndex)` centers a **128×128 world-px camera window** on the
  player (`ScreenWidth = ScreenHeight = 128`, defined in the vendored `bitworld`
  package's `spriteprotocol.nim`) — i.e. roughly **±64px along each axis**, up to
  **~90.5px at a diagonal screen corner** (`64·√2`).
- A point only counts as visible if it's inside that camera frame (`screenPointInFrame`)
  **and** has an unoccluded line of sight through walls (`spritePlayerObservationPointShadowed`).
- This is confirmed to be the literal percept-gating logic
  (`writeSpritePlayerObservationPlayingPlayers`) — not just a rendering detail. It's what
  decides which other players appear in a given player's `visible_players`, which is what
  `crewborg`'s `PlayerRecord.record()` (`types.py`) is fed from.

**Vision is symmetric.** Both sides run the same camera-frame + occlusion check from
their own center, over the same wall geometry — if A is within B's frame and unoccluded,
B is (in practice) within A's frame and unoccluded too. Practically: **if we currently
see a live crewmate at all, they can see us back.**

## Where crewborg approximates vision

The kill-witness gate in `strategy/opportunity.py` uses the live visible roster.
It checks that count against the urgency-dependent witness tolerance. The gate
must use actual observation visibility rather than an unrelated distance radius.

WATCH vantage scoring in `modes/search.py` evaluates task-station positions that
the agent has not yet occupied. It uses a 91px distance cap and wall occlusion.
That circle bounds the diagonal reach of the 128×128 viewport; it is an
approximation for prospective positions, not the exact observation predicate.

Changing either rule can alter kill timing and exposure. Check geometry locally
and evaluate competitive effects with a fresh matched comparison.
