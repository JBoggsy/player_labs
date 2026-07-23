<!-- Independent third-party audit of wowborg nav v2 (post v21-v38 campaign),
     performed by OpenAI Codex CLI in a read-only worktree at commit 01e680d.
     Thread: 019f902a-d885-7021-b720-3bccf0f6e08b (codex exec resume-able).
     Commissioned as an overfitting check per James's request, 2026-07-23. -->

# Navigation subsystem audit

## CRITICAL

### 1. The “generalizes” proof is selectively censored and is not two successful fresh-course tests

[world_race.py:160](vanilla_wow_lab/wowborg/policies/world_race.py:160), [world_race.py:219](vanilla_wow_lab/wowborg/policies/world_race.py:219), [world_race.py:239](vanilla_wow_lab/wowborg/policies/world_race.py:239), [wowborg-nav-v2.md:178](vanilla_wow_lab/docs/designs/wowborg-nav-v2.md:178)

What it does: visits same-map stations first, reorders them nearest-first, skips any reachable station whose heuristic travel estimate exceeds its current time share, and removes those skips from the reachability denominator.

Why it is a problem:

- Orgrimmar and RFC—the only catalog entries that exercise urban verticality or L2—were known to exceed the short session share and are therefore systematically skipped. The benchmark can report perfect reachability while never invoking the advertised hard paths.
- Fresh custom stations all receive the single region `"custom"` at lines 101–104, so the claimed ≥3-region rule is not enforced for the actual fresh-course seam.
- The passed courses cited in the outcome are all Durotar. Nothing passed in Orgrimmar, RFC, map 0, water, or transport.
- Git history contradicts “two consecutive fresh courses”: commit `cb44886` says v36 first exposed the canyon-mouth failure, then v37 changed the staging ladder specifically for that same course. Only v38 was a genuinely untouched fresh course.
- The estimate is not proof of physical impossibility: same-map cost is horizontal straight-line distance, and cross-map cost uses unverified hand-authored hints.

Classification: **OVERFITTING / invalid validation methodology.**

Fix direction: evaluate a fixed, held-out drawn order with sufficient per-course time; score every selected reachable station, and never exclude the exact long-range cases the generality claim is about.

### 2. A fully planned off-mesh target can enter an unbounded replan loop

[route.py:190](vanilla_wow_lab/wowborg/nav/route.py:190), [route.py:282](vanilla_wow_lab/wowborg/nav/route.py:282), [route.py:297](vanilla_wow_lab/wowborg/nav/route.py:297), [route.py:368](vanilla_wow_lab/wowborg/nav/route.py:368)

What it does: when `projected_target_distance > 12`, a partial plan fails as unreachable, but a non-partial plan changes `arrival_check` to the projected endpoint. Because that endpoint is not the true target, it is treated as an intermediate hop with the 35-yard stage radius. On arrival, L1 simply replans.

Why it is a problem: once the character is within 35 yards of the projection, L0 can return `ARRIVED` without moving. This path does not add a `replan_spot`; the same-region limiter only applies to `walk_failed` and empty partials. L1 can therefore plan → instant intermediate arrival → plan indefinitely until the caller deadline. A ledge, water edge, mid-air point, or other target whose closest mesh point is 13–35 yards away can produce this.

Classification: **General defect**, especially exposed outside the tested terrain.

Fix direction: make excessive target projection a terminal typed verdict, or explicitly accept the projection once under a separately defined semantic rule; never cycle it as an unbounded intermediate hop.

## HIGH

### 3. “Navigate literally anywhere” is impossible with the shipped world model

[world_model.py:54](vanilla_wow_lab/wowborg/nav/world_model.py:54), [world_model.py:62](vanilla_wow_lab/wowborg/nav/world_model.py:62), [journey.py:73](vanilla_wow_lab/wowborg/nav/journey.py:73)

What it does: the graph contains map 1 Durotar/Orgrimmar nodes, two map 389 RFC nodes, and one one-way portal. Unknown target maps return `unknown_region`; absent graph connectivity returns `no_world_path`.

Why it is a problem: there is no map 0, boat, zeppelin, hearthstone, elevator, or return-from-instance edge. Night elf zones, Eastern Kingdoms, and cross-continent travel cannot even be represented. Same-map travel bypasses the graph entirely, so its city anchors do not help route through known gates or vertical interiors.

Classification: **OVERFITTING / scope overclaim.**

Fix direction: narrow the contract to “same-map Detour plus seeded RFC entry” until validated transit edge types and other-map topology actually exist.

### 4. Reachability classification treats several reachable modes as unreachable

[route.py:153](vanilla_wow_lab/wowborg/nav/route.py:153), [route.py:164](vanilla_wow_lab/wowborg/nav/route.py:164), [route.py:190](vanilla_wow_lab/wowborg/nav/route.py:190)

What it does:

- Converts `no_path` with waypoints into a partial route.
- Declares a target unreachable when a partial plan reports projection over 12 yards.
- Treats a successful here→here self-probe as proof that a bare no-path result belongs to the target.

Why it is a problem:

- Progressive tile loading can project a distant reachable target against currently loaded geometry; a >12-yard projection is not necessarily target truth.
- Swimming destinations may be executor-reachable but absent from the ground navmesh.
- A character standing slightly off-mesh can fail the self-probe, causing global “planner broken” degradation rather than a source-projection recovery.
- A here→here success proves only that one local query worked, not that target tiles loaded or that the target is unreachable.
- `jump_required` is recorded but completely ignored, so a route requiring a jump has no execution path.

Classification: **OVERFITTING and general classifier defect.**

Fix direction: distinguish source projection, target projection, partial-tile exhaustion, movement mode, and jump segments explicitly; confirm unreachable only with a definitive full-tile query or mode-specific planner.

### 5. The staging ladder is waypoint-count and Durotar-radius dependent

[local.py:22](vanilla_wow_lab/wowborg/nav/local.py:22), [route.py:235](vanilla_wow_lab/wowborg/nav/route.py:235)

What it does: staging only activates for at least four waypoints, chooses `len(waypoints) // 2**attempt`, and treats any intermediate point within 35 yards as already reached.

Why it is a problem:

- A three-waypoint indoor corridor receives no staging recovery.
- Repeated deeper rungs eventually select index 1 repeatedly.
- Waypoint index is not corridor distance; unevenly spaced waypoints make “half” meaningless.
- There is no check that the chosen point is ahead along the corridor or improves geodesic progress.
- A 35-yard arrival radius can encompass an entire small room, the wrong side of a wall, or multiple tunnel turns. Staging can “succeed” without crossing the obstruction.
- The 8-yard final radius can likewise accept the wrong side of thin geometry or a nearby stacked floor.

This ladder was directly tuned to one Durotar canyon failure, despite being labelled structural.

Classification: **Strong OVERFITTING.**

Fix direction: select stages by forward corridor arc length and topology, require measurable post-stage progress, and derive tolerances from corridor clearance/interaction semantics rather than fixed Durotar distances.

### 6. The RFC portal test cannot detect a wrong pad or trigger assumption

[world_model.py:67](vanilla_wow_lab/wowborg/nav/world_model.py:67), [journey.py:131](vanilla_wow_lab/wowborg/nav/journey.py:131), [fake_nav_bridge.py:107](vanilla_wow_lab/wowborg/tests/fake_nav_bridge.py:107), [fake_nav_bridge.py:225](vanilla_wow_lab/wowborg/tests/fake_nav_bridge.py:225)

What it does: hardcodes several Orgrimmar positions marked “verify,” including the RFC pad, then fires trigger 2230 up to three times. The fake exposes every portal binding everywhere because `_near_any_portal()` always returns `True`.

Why it is a problem: the test passes even if the pad coordinate is completely wrong. In production, arriving at the guessed point may offer no trigger binding. The implementation also checks only the destination map, not the expected destination vicinity; an unexpected teleport is retried and later reduced to generic journey failure. The design itself admits this edge has never been hosted-tested.

Classification: **OVERFITTING / false test confidence.**

Fix direction: validate the pad and trigger against a captured real frame, make the fake spatially enforce trigger volumes, and verify both destination map and destination region.

### 7. Frame starvation is immediately misclassified on the first sample

[local.py:107](vanilla_wow_lab/wowborg/nav/local.py:107)

What it does: after `wait_for_frame()` times out, movement is tolerated only if `history` is non-empty and `observe()` differs from `history[-1]`.

Why it is a problem: `history` starts empty. If L0 begins while a prior executor action is still walking—the exact long-settlement condition the fallback is meant to tolerate—the first timeout returns `NO_FRAME` even when `observe()` shows substantial movement. That consumes replans and can eventually produce `no_progress`.

Classification: **General reliability defect.**

Fix direction: capture a baseline observation before the first wait and compare starvation observations against that baseline.

### 8. Movement supervision cannot distinguish intended locomotion from forced motion or transport

[local.py:125](vanilla_wow_lab/wowborg/nav/local.py:125), [local.py:153](vanilla_wow_lab/wowborg/nav/local.py:153), [bridge.py:564](vanilla_wow_lab/wowborg/bridge.py:564)

What it does: any displacement over 3 yards clears stalls, regardless of direction or cause. Observations expose only position, health, combat, dead, and ghost state.

Why it is a problem:

- Fear, knockback, current drift, falling, or an elevator can count as healthy progress.
- Rooted combat increments stalls until the fixed health/stall heuristic yields, but feared movement can keep resetting stalls indefinitely.
- Swimming, falling, mounted state, transport attachment, breath, and movement-control auras are invisible.
- A healthy 50%-plus character runs through all combat regardless of class, hostile level, DoT, root, or destination risk.
- Horizontal reversals in a long tunnel can be legitimate even when Euclidean goal distance worsens; displacement resets stall but revisit logic can still condemn repeated geometry.

Classification: **General defect exposed by non-Durotar movement modes.**

Fix direction: supervise signed progress along the planned corridor and add explicit movement/control modes for swimming, falling, transport, fear/root, and mount state.

### 9. Lenient frames disable the only recovery action used by combat and death loops

[bridge.py:88](vanilla_wow_lab/wowborg/bridge.py:88), [route.py:395](vanilla_wow_lab/wowborg/nav/route.py:395), [route.py:411](vanilla_wow_lab/wowborg/nav/route.py:411)

What it does: lenient frames set `recommended_action = None`. Combat and death recovery do nothing except select the recommended action.

Why it is a problem: during the documented validation storms, movement may continue because raw move actions are attempted, but combat resolution, release-spirit, corpse running, and reclaim can become inert until the overall deadline. L0’s Stuck cast only helps if spell 7355 happens to be bound; it does not replace recovery recommendations.

Classification: **General reliability defect.**

Fix direction: preserve and independently validate the recommended action’s admissible factors, or implement explicit masked recovery actions for combat/death during lenient operation.

### 10. Budget logic reintroduces straight-line assumptions and carries stale pace across terrain modes

[route.py:74](vanilla_wow_lab/wowborg/nav/route.py:74), [route.py:186](vanilla_wow_lab/wowborg/nav/route.py:186), [route.py:226](vanilla_wow_lab/wowborg/nav/route.py:226), [world_race.py:189](vanilla_wow_lab/wowborg/policies/world_race.py:189)

What it does: the pace estimator persists for the entire race. Planner degradation and empty-partial nudges budget from Euclidean distance; each replan creates a fresh budget.

Why it is a problem:

- A road or mounted pace can carry into an indoor dungeon and make its budget too short.
- Root/fear-interrupted hops can record misleading effective pace.
- Euclidean fallback severely underestimates winding cities, tunnels, switchbacks, and water routes.
- Replan budget resets mean there is no coherent route-wide budget; progressive replanning can consume the caller’s full deadline while each individual plan remains “within budget.”

Classification: **OVERFITTING plus general budget defect.**

Fix direction: keep mode/terrain-conditioned pace, exclude externally interrupted samples, and maintain one route-wide budget based on accumulated planned corridor distance.

### 11. The benchmark does not collect the robustness data it claims to score

[journey.py:191](vanilla_wow_lab/wowborg/nav/journey.py:191), [world_race.py:276](vanilla_wow_lab/wowborg/policies/world_race.py:276)

What it does: journey legs retain only kind, destination, status, and reason. World Race then hardcodes `deaths`, `combat_pauses`, and `replans` to zero.

Why it is a problem: the design promises recovery, efficiency, planned distance, walked time, combat, death, and replan metrics, but the evidence surface discards them. A course can be declared robust even when every route experienced recoveries or pathological churn.

Classification: **Benchmark/instrumentation defect.**

Fix direction: propagate the complete `RouteResult` metrics through each journey leg and derive station totals from them.

### 12. The fake structurally guarantees away the most important real failures

[fake_nav_bridge.py:56](vanilla_wow_lab/wowborg/tests/fake_nav_bridge.py:56), [fake_nav_bridge.py:169](vanilla_wow_lab/wowborg/tests/fake_nav_bridge.py:169), [test_nav.py:28](vanilla_wow_lab/wowborg/tests/test_nav.py:28)

What it does: movement is a constant 14-yard straight-line 3D interpolation; plans are straight-line waypoint chains; settlements are immediate successes; here→here always succeeds; portals bind everywhere.

Why it is a problem: it cannot express curved corridors, uneven waypoint spacing, stacked walkable floors, partial paths with useful waypoints, source/target projection, off-mesh swimming, jump segments, changing chunk sizes, moving transports, mask refusal, settlement timeout/supersession, frame drought, fear/root, or spatial portal volumes. The “wrong floor” test does not model floors—the fake normally climbs directly in Z and the test stops it using a point wall.

Classification: **OVERFITTING in the test infrastructure.**

Fix direction: replace the geometric toy with captured planner/frame/settlement fixtures plus a corridor-script fake that can express projections, short curved routes, vertical layers, delayed failures, and movement modes.

## MEDIUM

### 13. Settlement correlation knowingly accepts the wrong action’s result

[bridge.py:427](vanilla_wow_lab/wowborg/bridge.py:427)

What it does: any settlement with `settled.frame_id >= awaited_frame_id` satisfies the wait; a newer settlement is returned as if it were the awaited outcome.

Why it is a problem: a reconnect, autonomous action, stale poll, or concurrent control path can cause action N+1’s settlement to stand in for action N. This violates the bridge’s stated exact-settlement contract. Most callers also ignore the returned success flag.

Classification: **General protocol defect.**

Fix direction: require exact frame/request correlation and return an explicit lost/superseded failure otherwise.

### 14. The world graph’s “nearest” and cost semantics are wrong for vertical cities

[world_model.py:110](vanilla_wow_lab/wowborg/nav/world_model.py:110), [world_model.py:119](vanilla_wow_lab/wowborg/nav/world_model.py:119)

What it does: chooses the nearest place using horizontal distance only, and Dijkstra uses static `cost_hint` despite the docstring saying walk edges are re-costed live.

Why it is a problem: in Orgrimmar, two anchors can be horizontally close but vertically or topologically far apart. A character above the Cleft can be assigned to its underground node. When alternate routes are added, guessed costs can choose an unusable path or drive erroneous benchmark skips.

Classification: **OVERFITTING to mostly flat outdoor coordinates.**

Fix direction: select anchors by a live route/projection cost and make graph costs reflect validated traversal time or distance.

### 15. World Race reachability can exceed 100%

[world_race.py:159](vanilla_wow_lab/wowborg/policies/world_race.py:159)

What it does: the reachability numerator counts every arrival, including an “unreachable” station incorrectly reached; the denominator counts only attempted expected-reachable stations.

Why it is a problem: three reachable arrivals plus one supposedly unreachable arrival yields `4/3 = 1.333`. That corrupts the headline used to justify generality.

Classification: **General metrics defect.**

Fix direction: calculate reachable success only over expected-reachable rows and report unexpected adversarial arrivals separately.

### 16. Portal retries are time-based and validate only map identity

[journey.py:143](vanilla_wow_lab/wowborg/nav/journey.py:143)

What it does: makes three fire attempts, sleeps one second only after a failed selection, and accepts any position on the destination map.

Why it is a problem: delayed loading can outlast the settlement polling, repeated trigger packets can be sent during transfer, and a teleport to an unexpected location on map 389 is accepted. Death or GM/instance relocation to the same map is indistinguishable from correct portal traversal.

Classification: **General reliability defect.**

Fix direction: treat transfer as its own state with a bounded load wait and validate the destination against a region/radius, not just `map_id`.

### 17. Journey replan state is an undeclared cross-call attribute

[journey.py:108](vanilla_wow_lab/wowborg/nav/journey.py:108)

What it does: creates `_last_replan_at` dynamically and retains it across `journey_to()` calls, while `replan_count` resets locally.

Why it is a problem: today the stale value usually has little effect because the count starts at zero, but comparisons can cross maps and `Point.distance` does not reject differing map IDs. It is ambiguous state with no lifecycle and will produce surprising behavior if the thrash policy evolves.

Classification: **General state-management defect, currently low blast radius.**

Fix direction: keep replan history local to one journey and compare only points on the same map.

## LOW

### 18. Documentation still labels the shipped design a proposal and overstates implemented behavior

[wowborg-nav-v2.md:3](vanilla_wow_lab/docs/designs/wowborg-nav-v2.md:3), [wowborg-nav-v2.md:46](vanilla_wow_lab/docs/designs/wowborg-nav-v2.md:46)

The document remains “proposal for review” and describes waypoint hopping, settlement fidelity, cross-continent challenge content, robustness metrics, and a diverse course shape that the outcome section or implementation later contradicts.

Classification: **Documentation reliability defect.**

Fix direction: mark the actual shipped scope and separate implemented, hosted-validated, unvalidated, and future capabilities.

## State-leak assessment

- `LocalMover` is genuinely per-call stateless.
- Persistent `PaceEstimator` state is intentional session learning, but unsafe across mounted/outdoor/indoor/swim modes.
- `_last_replan_at` is accidental cross-call state and should be local.
- Replan/staging state correctly starts fresh per `navigate_to`, but the off-mesh intermediate-arrival path bypasses its limiter.

## Verdict

The claim that this navigation “generalizes” or “one-shots new challenges” is **not justified**. The evidence supports a narrower statement: it has become reasonably effective at direct semantic movement across several Durotar outdoor routes, including one held-out Durotar course. The benchmark actively avoids or excludes the long-range, city, dungeon, transport, water, and cross-map cases needed to establish the broader claim. RFC entry remains explicitly unproven, and cross-continent travel is not implemented.

Before trusting it in a genuinely new environment, I would require:

1. A held-out, adequately timed suite covering Orgrimmar interiors, RFC, map 0, water, and cross-continent transit—fixed order, no skip censoring, and no code change after seeing the course.
2. Real or captured contract tests for partial/projection behavior, short curved corridors, stacked floors, frame storms, exact settlements, fear/root/fall/swim, and spatial portal triggers.
3. A mode-aware reachability/state machine plus a validated world model: source-vs-target projection, jump/swim/transport execution, proven RFC entry, and actual boat/zeppelin/hearth edges.

This was a read-only source audit; I did not run the unit suite because it would not add evidence for the unrepresentable real-world cases above. The requested independent Claude pass also could not run because its authentication endpoint failed with `getaddrinfo ENOTFOUND portal.sso.us-east-1.amazonaws.com`; no second-model findings are represented here.
