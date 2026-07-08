# Crewrift's real vision model, and where crewborg approximates it

**Status:** reference doc, written 2026-07-06 after tracing the actual mechanic in the
vendored game source. Read this before adding or tuning any "can X see Y" constant.

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

## Where crewborg approximates this, and how

Two places in the codebase model "can X see Y" — for different purposes, so they don't
have to (and, before 2026-07-06, didn't) use the same number:

1. **The kill-witness gate** (`strategy/opportunity.py`'s `unwitnessed()`). Reworked
   2026-07-06: since vision is symmetric and `belief.roster` is fed purely from our own
   vision, counting how many live non-teammate crewmates are currently visible to us
   (`last_seen_tick == belief.last_tick`) **is** the witness count, exactly — no radius
   or staleness window needed as a proxy. That count is checked against an
   urgency-ramped tolerance (`witness_tolerance()`: 1 at zero urgency, up to 6 — an
   "always strike" ceiling in this game's 6-crew format — by full urgency), not gated
   as a bare yes/no on any witness at all. (Previously used a bespoke
   `BASE_ISOLATION_RADIUS = 48` / `WITNESS_WINDOW_TICKS = 72` decaying-with-urgency
   heuristic that was never derived from the 128px screen constant and was actually
   *smaller* than the true ~64–90px reach — a real gap where the gate could clear a kill
   as "unwitnessed" that would in fact have been seen in-game.)
2. **WATCH vantage scoring** (`modes/search.py`'s `VANTAGE_RANGE`, in `_best_vantage()`).
   This asks a genuinely different, *prospective* question — "how far can a *candidate
   standing point* see into a room" — for spots the agent hasn't stood at yet, so it
   can't be answered by "are they in `belief.roster` right now." It still needs a
   distance cap, corrected 2026-07-06 from an arbitrary `360` to **`91`** (`ceil(64·√2)`,
   the circumscribed-circle radius of the true 128×128 square — chosen to over-cover
   rather than under-cover, since in-room wall occlusion (`_segment_clear`) is what
   actually narrows it down; see that module's own comment). Later the same day,
   `_best_vantage()` was rewritten to score only **room task-station points**
   (`_room_task_indices`), not arbitrary open-floor points — WATCH always latches onto a
   task while observing rather than hovering mid-room (see `imposter-play.md`'s
   "Vantage selection" section). The standalone `visionbake.py` module and its
   precomputed-pickle asset (`map/croatoan_visionbake.pkl.gz`), which used to score
   *arbitrary* floor points for the now-removed camouflage one-shot, were deleted
   entirely as part of that rework — they no longer exist in this codebase.

Both are still **circular approximations of a square viewport** — exact for the
witness gate now (roster membership already reflects the true square+occlusion check),
approximate for vantage scoring (a real geometry query against a point that isn't
necessarily where we're currently standing). A precise axis-aligned box check is
possible there if the circular approximation ever proves too loose in practice; not
done here since walls already do most of the real narrowing.

## Caution before re-tuning

This lab's own history (`crewrift_lab/lessons_archive/`) records **three separate
refuted attempts** to further *relax* the witness gate (dropping it after kill #1
instead of #2, lowering `URGENCY_FULL_TICKS` from 240→80) — each moved kills/ejections
the wrong direction. This doc's changes are a **correctness fix + a mechanism
simplification**, not a re-loosening — but they touch the same lever, so validate with
a fresh A/B (`crewrift-ab` skill) before shipping to a league, not just unit tests.
