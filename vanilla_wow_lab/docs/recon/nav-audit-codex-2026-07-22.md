# Codex audit: wowborg navigation — generality, robustness, reliability

**Date:** 2026-07-22. **Auditor:** OpenAI Codex (thread 019f8aa8-1d70-7563-b976-777a5b4a58fe),
audit-only over a detached worktree at campaign commit 5e191a0 (v5-v20 endpoint).
**Commissioned by James** to check whether the nav layer is overfitted to the Durotar
race waypoints before reuse for RFC dungeon navigation. Verdict: the RACE POLICY is
benchmark machinery, not a general nav layer — do not reuse directly for RFC; the bridge
seam is sound. Line refs are into the worktree copy = identical to 5e191a0.

Audited snapshot: detached campaign commit `5e191a0` (v5–v20 endpoint). Refreshed remotes do not contain this commit on either current `origin/main` or `upstream/main`, so findings apply specifically to the requested campaign code. No tests were run; this was a read-only source/history/test-coverage audit.

## Findings, ranked by severity

### Critical

1. **All navigation topology and arrival logic is 2D; RFC’s stacked floors will produce false arrivals and false progress decisions.** `distance_2d` discards `z`, then drives stage selection/rearming, arrival, budgets, split distance, and stall displacement ([waypoint_race.py:203](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:203), [waypoint_race.py:279](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:279), [waypoint_race.py:361](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:361), [waypoint_race.py:437](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:437)). `ARRIVAL_TOLERANCE_YARDS=8` therefore means “within eight yards horizontally at any elevation.”  
   **Failure scenario:** Standing directly below an RFC waypoint causes the leg to be marked complete even though the character is on the wrong floor with no route to the target.

2. **Waypoints have no map/instance identity; after an RFC death or instance exit, dungeon coordinates are silently sent on the character’s current exterior map.** Catalog and override points are only `[x,y,z]` ([waypoint_race.py:41](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:41), [waypoint_race.py:176](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:176)); movement fills `WorldPoint.map_id` from `loc.map_id`, not from the waypoint ([waypoint_race.py:462](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:462), [bridge.py:180](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/bridge.py:180)).  
   **Failure scenario:** A wipe releases the player outside RFC, after which the policy requests the next RFC coordinate on Kalimdor and either wedges, moves somewhere unrelated, or burns the leg budget.

3. **The policy has no combat-aware navigation state despite RFC combat being constant.** It special-cases only death, never `in_combat`, and otherwise keeps selecting movement ([waypoint_race.py:336](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:336), [waypoint_race.py:451](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:451)). The contract classifies `combat_interrupted` as a successful movement settlement ([types.py:12](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/types.py:12)), but the bridge drops granular settlement kind and position ([bridge.py:213](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/bridge.py:213)).  
   **Failure scenario:** A trash pull repeatedly interrupts movement; six stationary observations are classified as navigation failure, so the policy skips the waypoint and starts steering deeper into the dungeon while combat remains unresolved.

### High

4. **Death recovery preserves stale leg state while wall-clock budgets continue running.** Dead/ghost frames defer to the recommendation without pausing or rebasing `leg_started_at`, `leg_origin`, budget, progress baseline, or stages ([waypoint_race.py:337](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:337)); elapsed wall time later triggers failure ([waypoint_race.py:398](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:398)).  
   **Failure scenario:** Corpse recovery takes two minutes; on resurrection the current leg immediately budgets out or resumes a via-chain whose “passed” nodes describe the pre-death location.

5. **Any movement over five yards counts as progress, even movement away from the goal or a permanent oscillation.** `DISPLACEMENT_EPSILON_YARDS=5` resets the stall streak without checking direction, bounded area, route advancement, or repeated positions ([waypoint_race.py:433](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:433)). Such a leg survives until the hard `2 * leg_budget` cap ([waypoint_race.py:398](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:398)).  
   **Failure scenario:** The coastal-rock wedge alternates between two points six yards apart, resetting `no_progress_streak` forever and consuming hundreds of seconds before the hard budget intervenes.

6. **The via-chain algorithm assumes open-world, linear, Euclidean topology.** It finds the horizontally nearest via node, drops its prefix, clears nodes from 35 yards away, and rearms them only after 100 horizontal yards ([waypoint_race.py:108](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:108), [waypoint_race.py:264](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:264), [waypoint_race.py:271](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:271)). Those thresholds came directly from one Durotar gate oscillation and corridor.  
   **Failure scenario:** A via node on the floor above is horizontally closest, so the policy drops the actual stair/door approach and steers into a wall; the 100-yard rearm rule cannot recover inside a compact dungeon.

7. **Leg budgets are Durotar pace estimates, not robust navigation deadlines.** `60 + 1 second per 2D yard`, with a `2×` hard cap, was calibrated from uninterrupted outdoor travel at roughly 1.3–2 yd/s ([waypoint_race.py:96](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:96), [waypoint_race.py:121](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:121), [waypoint_race.py:402](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:402)). It ignores navmesh path length, vertical routing, combat, doors, party waits, and death.  
   **Failure scenario:** Two RFC points are 15 yards apart horizontally but separated by a long ramp and several pulls, yielding a 75-second nominal budget and a false DNF at 150 seconds.

8. **A policy exception “resumes” only the object-level counters; the actual state machine restarts at waypoint zero.** Every `run()` recreates `index`, timers, progress baselines, and stage hysteresis ([waypoint_race.py:239](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:239)); the shim catches any exception and calls the same policy object’s `run()` again ([shim.py:178](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/shim.py:178)). Completed counters and splits remain, producing a hybrid old/new state.  
   **Failure scenario:** A transient exception near the last RFC waypoint reconnects successfully but sends the character back toward course waypoint zero while retaining the previous completion metrics.

9. **An offered frame can become a permanent busy-loop when neither the requested nor recommended action is selectable.** Both policies simply `continue` without consuming or invalidating the frame ([waypoint_race.py:465](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:465), [random_walk.py:82](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/random_walk.py:82)); `wait_for_frame` does not suppress an already-seen frame ([bridge.py:131](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/bridge.py:131)). The death branch has the same hole if no recovery recommendation exists.  
   **Failure scenario:** RFC offers a dead/ghost frame with no currently legal reclaim action; the policy rereads the same immutable frame until the session deadline.

### Medium

10. **The first leg receives a different, smaller budget than every subsequent staged leg.** Initial setup calculates budget from direct `to_target` only ([waypoint_race.py:425](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:425)); `advance()` budgets the full via-chain path ([waypoint_race.py:321](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:321)). This is one consequence of the large `advance()` nonlocal state cluster.  
    **Failure scenario:** The same RFC staged route budgets out when randomly selected first but succeeds when selected later.

11. **Settlement correlation uses `settled.frame_id >= requested_frame_id`, so a later action can be reported as the requested one.** The returned request ID, action kind, success, and detail all come from whichever newer settlement was observed ([bridge.py:198](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/bridge.py:198)). This is mostly latent under strictly synchronous operation but becomes relevant around timeouts, reconnects, and unawaited chat actions.  
    **Failure scenario:** A timed-out move is overwritten by a later combat settlement; the bridge reports the combat result as the move’s outcome and hides the missing settlement.

12. **The tier system and random course order are Durotar benchmark machinery, not general navigation abstractions.** Tiers are radial bands around one Durotar spawn and course composition is sized for a 970-second outdoor race ([waypoint_race.py:3](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:3), [waypoint_race.py:96](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:96)). Random ordering assumes every pair is traversable in either direction, unlike dungeon progression, doors, drops, and encounter gates.  
    **Failure scenario:** Randomization orders an RFC waypoint behind a locked encounter door before the waypoint that unlocks it.

13. **`random_walk` reports any successful settlement as “reached,” including corridor advancement or combat interruption.** `legs_reached` increments solely from `outcome.success` ([random_walk.py:95](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/random_walk.py:95)), while successful movement kinds explicitly include non-arrival outcomes ([types.py:12](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/types.py:12)). It also chooses arbitrary 2D offsets at the current `z`, which is weak exploration in stacked interiors ([random_walk.py:40](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/random_walk.py:40), [random_walk.py:75](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/random_walk.py:75)).  
    **Failure scenario:** Every attempted RFC move is combat-interrupted, yet the summary claims a high successful-leg count.

14. **Lap and move metrics overstate successful navigation.** Crossing the end of the course increments `laps_completed` even when the final leg was skipped ([waypoint_race.py:301](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:301)); `moves` increments before mask refusal and therefore counts recommended fallbacks as waypoint moves ([waypoint_race.py:461](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/policies/waypoint_race.py:461)).  
    **Failure scenario:** A course with one unreachable final waypoint reports a completed lap and misleading movement efficiency.

## Constant/generalization verdict

- **Fundamentally Durotar-specific:** tier boundaries/composition, `STAGE_CLEAR_YARDS=35`, `STAGE_REARM_YARDS=100`, via-chain catalog contents, `LEG_BUDGET_BASE_SECONDS=60`, and `LEG_BUDGET_SECONDS_PER_YARD=1`.
- **Potentially general concepts, but not current values/implementation:** arrival tolerance, progress epsilon, displacement-based detour recognition, no-progress limit, via-chain routing, and a hard leg deadline.
- **Unsafe for RFC as written:** every use of 2D distance, nearest-suffix via selection, random waypoint ordering, current-map destination binding, and wall-clock budgets that include combat/death recovery.

Current tests mainly use a bridge that teleports exactly to destinations, plus a stationary failure double ([test_waypoint_race.py:45](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/tests/test_waypoint_race.py:45), [test_waypoint_race.py:195](/private/tmp/codex-worktree-1784737662/vanilla_wow_lab/wowborg/tests/test_waypoint_race.py:195)). There is no coverage for z-stacked points, map changes, death relocation, combat interruption, directional oscillation, restart continuity, rearm hysteresis, or late/newer settlements.

## Recommendation

Do not reuse `WaypointRacePolicy` directly for RFC. Preserve the bridge seam, but first separate the Durotar race benchmark from a map-aware navigation state machine. RFC navigation needs:

- waypoint identity including map/instance and vertical/topological arrival;
- ordered route segments or a route graph, not radial tiers and randomized all-pairs legs;
- explicit combat, death, corpse-run, teleport, and instance-reentry transitions;
- progress based on route/corridor advancement with oscillation detection;
- budgets derived from active navigation time and planned path cost, pausing for combat/recovery;
- resumable state owned by the policy object;
- exact settlement correlation and preservation of settlement kind/end position.

The via-chain idea remains useful, but only as explicit topological route metadata with direction, map/floor identity, and local clearing conditions—not nearest-node inference from 2D distance.