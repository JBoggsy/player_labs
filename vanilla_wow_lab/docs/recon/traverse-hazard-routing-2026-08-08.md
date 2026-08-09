# Traverse hazard-aware routing recon — 2026-08-08

## Decision

Use a **road-aligned, dynamically replanned route** as the primary Tanaris solution. The
canonical game route begins at the exact league spawn and follows the Tanaris north road;
Wowborg's current hand-authored opening detour instead crosses the four cells containing 87.6%
of historical deaths. Treat combat and stealth as local edge-traversal policies, not as three
competing global routes:

1. Take the cheapest road/navmesh corridor whose live hazard cost is acceptable.
2. If a blocking pull is demonstrably cheap and survivable, kill it with a real feral rotation.
3. Otherwise avoid it dynamically in Travel Form. Do **not** select Prowl rank 1 as the default
   fallback: for this fixture it increases the practical detection radius and slows travel.

This is a recon conclusion, not an implementation. The next attributable step should replace
only the opening Tanaris prefix with the canonical road corridor and evaluate it before adding
combat selection or a generalized hazard-cost planner.

## Evidence that changes the decision

### The current opening route is the wrong baseline

The league fixture spawns a level-60 Tauren druid at `(-9187, -2530.2498, 14.0935)` with 5,000
health and mana, but equips the level-39 `dps-39-twink` gear and `feral-fc-39-twink` spell
templates (`coworld-vanilla-wow@b92f4961:game/leagues/traversal.py:7-55`). The owner game's
canonical world catalog starts its Tanaris road at that exact point, then heads southwest through
`(-8974, -2742)`, `(-8761, -2953)`, and `(-8548, -3164)` before turning toward the Shimmering
Flats ramp (`coworld-vanilla-wow@b92f4961:bots/real_playerbot/policy/world_catalog.nim:336-390`).

Wowborg instead begins with a west/south/east hand detour advertised as crossing zero static
hostile envelopes ([traverse.py](../../wowborg/strategies/traverse.py#L35-L76)). Hosted evidence
invalidates that premise: 106 of 121 historical deaths occurred in four adjacent cells along
`y ~= -2500`, and 88.6% of incoming damage landed there
([history profile](../wowborg-history-profile-2026-08-06.md#L5-L16)). Six of six v78 repeats died,
all with Glasshide Petrifier as the last damage source, despite the static envelope prediction
([history profile](../wowborg-history-profile-2026-08-06.md#L75-L92)).

The owner road is also 695 yards shorter than Wowborg's current prefix to comparable eastward
progress near `x=-7577` (1,997 versus 2,692 yards by 3-D guidepoint sum). That is about 71
simulation seconds at 9.8 yards/second Travel Form speed before considering the current route's
combat and recovery losses. The precise full-route saving needs a navmesh path comparison because
the two prefixes end at different `y` coordinates.

### What we are actually fighting

The exact pinned world database in environment digest
`sha256:f950683bd15014e0fd9be0c4226d70474fe05a0b09fe09b2a55fb0c351dfd3e4` gives the recurring
opening enemies these properties:

| Enemy | Entry | Level | Base health | Base melee | Detection | Swing |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Glasshide Gazer | 5420 | 45–46 | 1,848–1,919 | 88.0–89.8 | 18 yd | 2.0 s |
| Scorpid Dunestalker | 5424 | 46–47 | 1,919–1,990 | 89.8–92.0 | 18 yd | 2.0 s |
| Rabid Blisterpaw | 5427 | 47–48 | 1,990–2,062 | 92.0–93.9 | 18 yd | 2.0 s |
| Glasshide Petrifier | 5421 | 48–49 | 2,062–2,138 | 93.9–96.1 | 18 yd | 2.0 s |

These are class-level base values; armor, player mitigation, miss/dodge, creature spells, and
damage variance affect realized damage. The policy should therefore use them as priors and learn
from observed health and damage, not pretend they are exact time-to-kill figures.

VMaNGOS computes ordinary proximity aggro from template detection range minus the target-minus-
creature level difference, with a minimum of five yards. Against our level-60 character, these
level-45–49 mobs therefore have only a **5–7 yard ordinary aggro radius**, assuming the default
aggro-rate multiplier. This is why a live moving-unit overlay can be much less conservative than
an 18-yard static circle while still accounting for patrol motion. See the primary VMaNGOS
implementation of [`Creature::GetAttackDistance`](https://github.com/vmangos/core/blob/a10102850006195c1dda88f311195d67f520af76/src/game/Objects/Creature.cpp#L2193-L2241).

Historical realized combat is more sobering than the level gap suggests. Across 113 current-family
runs, Glasshide Petrifiers caused 69.2% of incoming damage. Only v73 genuinely fought: it killed
three exact attackers, dealt 7,825 damage, took 3,811, survived, but advanced only 417 yards
([history profile](../wowborg-history-profile-2026-08-06.md#L8-L16),
[version log](../../wowborg/VERSION_LOG.md#L233-L250)). This establishes that basic melee can
survive one observed sequence, but is far too slow to justify a general “fight through” rule.

### Avatar combat strength is not current policy combat strength

The fixture has a substantial feral kit: Cat Form, Prowl, Tiger's Fury, Rake, Claw, Rip,
Ferocious Bite, Feral Charge, Frenzied Regeneration, and healing spells are present in its spell
template. The owner bot already demonstrates the decision structure we should reuse conceptually:
form selection, Prowl openers, target-lifetime-aware bleeds, combo-point finishers, and emergency
healing (`coworld-vanilla-wow@b92f4961:bots/real_playerbot/policy/class_combat/druid.nim:172-390`).

Traverse does not use that capability. All navigation calls set `engage_attackers=False`, and the
latent engagement helper only faces, starts auto-attack, and waits
([traverse.py](../../wowborg/strategies/traverse.py#L294-L306),
[route.py](../../wowborg/nav/route.py#L455-L528)). Thus the router must not estimate a fight using
the theoretical avatar loadout and then hand it to today's auto-attack-only policy.

The canonical Observation already supplies most of the online estimator inputs:

- each visible unit's level, current/max health, location, movement, combat distance, target,
  casting state, and auras (`coworld-vanilla-wow@b92f4961:environment/contract/policy.py:126-209`);
- attacker count, highest level delta, elite presence, and incoming damage rate
  (`policy.py:705-716`);
- combat duration and cumulative damage done/taken, plus sequenced damage/heal/spell events
  (`policy.py:1376-1434`);
- spell usability, resource cost, range, cooldown, and intent (`policy.py:639-702`).

It does **not** expose a simple player attack-power, weapon-DPS, or armor scalar. That is not a
blocker: estimate realized DPS and incoming DPS from combat events, and seed cold-start estimates
from a targeted combat calibration batch. Static item arithmetic would be less reliable than the
server's actual hit, armor, dodge, crit, spell, and form outcomes.

## Fight-through decision model

Maintain conservative, exponentially updated estimates by enemy entry and attacker count:

- `player_dps(entry, rotation_state)` from damage done divided by active engagement time;
- `incoming_dps(entry, attacker_count)` from damage taken over the same window;
- `ttk = remaining_enemy_health / lower_confidence_player_dps`;
- `ttl = effective_player_health / upper_confidence_incoming_dps`;
- `fight_cost = acquisition + form/rotation setup + ttk + post-fight recovery`;
- `bypass_cost = extra_path_yards / current_movement_speed + risk_penalty`.

Fight only when all of these hold:

1. every attacker is identified and non-elite;
2. `ttl` exceeds `ttk` by a meaningful safety margin (start at 2x, then calibrate);
3. estimated ending health stays above the emergency band and no likely add enters during `ttk`;
4. `fight_cost` is lower than the dynamically replanned bypass cost;
5. the combat owner can run the calibrated feral rotation, rather than basic auto-attack.

If combat starts unexpectedly, recompute from observed attacker count and incoming rate. Continue
the kill only while the safety inequality remains true; otherwise choose a navmesh escape edge
that increases distance from all live attackers and respects their leash behavior.

The missing empirical input is full-rotation DPS/TTK. The cheapest valid next instrument after the
road experiment is a matched hosted batch against the four opening entries, recording per-fight
health curves, attacker count, spell sequence, DPS, TTK, and recovery time. v73 is useful proof of
mechanism but only one auto-attack sample and cannot set a robust threshold.

## Stealth decision model

### Rank-1 Prowl is a trap in this fixture

The exact pinned `Spell.dbc` row for Prowl 5215 applies stealth value **100** and a **-40% movement
speed** effect. The spell template contains 5215 but not ranks 2 or 3 (6783/9913), and none of its
talent spells supplies `SPELL_AURA_MOD_STEALTH_LEVEL`. Wowborg correctly chooses the highest known
rank, so it can only choose rank 1 ([traverse.py](../../wowborg/strategies/traverse.py#L124-L178)).

VMaNGOS creature stealth detection uses creature level x5 versus the target's stealth aura value,
at 5/6 yard per five skill points, capped at 30 yards; detection from behind is nine yards shorter,
and a five-yard alert band precedes actual detection. See the primary
[`Unit::IsVisibleForOrDetect` implementation](https://github.com/vmangos/core/blob/a10102850006195c1dda88f311195d67f520af76/src/game/Objects/Unit.cpp#L6770-L6838).
For stealth value 100, the resulting level-45–49 Tanaris detection ranges are approximately:

| Mob level | Facing detector | Behind detector | Alert begins |
| ---: | ---: | ---: | ---: |
| 45 | 21.7 yd | 12.7 yd | +5 yd |
| 46 | 22.5 yd | 13.5 yd | +5 yd |
| 47 | 23.3 yd | 14.3 yd | +5 yd |
| 48 | 24.2 yd | 15.2 yd | +5 yd |
| 49 | 25.0 yd | 16.0 yd | +5 yd |

That is materially worse than the same mobs' 5–7 yard ordinary aggro against a visible level-60
character. Prowl also gives up Travel Form's 40% speed bonus and applies its own 40% penalty;
even with Cat Form movement talents, it imposes a large time cost. Current Traverse has Prowl
disabled (`PROWL_ROUTE_GUIDEPOINTS = 0`) and immediately selects Travel Form
([traverse.py](../../wowborg/strategies/traverse.py#L21-L24)); that is correct for the present
loadout, although it was reached without this explicit model.

If the fixture later supplies Prowl rank 3 (stealth value 300, -20% speed), stealth becomes a real
local option. The router should then expand each moving hostile into a directional detection disk
using level, facing, motion destination, and uncertainty; plan behind detectors where possible;
replan on every material movement sample; and exit Prowl once the hazard cluster is behind us.
Stealth cannot be entered in combat, so it is preventive routing—not an escape action.

## Router shape

Keep geometry and hazard semantics separate:

1. **Geometry graph:** existing navmesh nodes/edges and route length.
2. **Static prior:** creature spawns, entry/level range, wander radius, and known road corridor.
3. **Live overlay:** visible hostile position, velocity/destination, facing, health, target, and
   casting state; retain unseen tracks briefly with growing positional uncertainty.
4. **Edge evaluator:** travel time plus expected contact cost. Contact cost is the minimum valid
   policy among visible bypass, calibrated fight, and (only with adequate stealth rank) Prowl.
5. **Replanner:** refresh when a hostile moves across the corridor, attacker count changes, combat
   starts/ends, or an edge's expected cost crosses a hysteresis threshold.

The first implementation does not need a new general planner. Reuse the owner road guidepoints,
route between them with the existing navmesh API, and add a small live-hostile clearance check
before each local hop. Generalize only after hosted evidence shows which observations actually
predict contact. This preserves attribution and avoids repeating the failed static-envelope
assumption.

## Recommended experiment order

1. **Road baseline:** replace only the opening Tanaris detour with the canonical road points;
   retain Travel Form and current run-through behavior. Compare fresh matched episodes on deaths,
   first-contact location/time, living northing, and Great Lift arrival.
2. **Dynamic avoidance:** overlay live hostile tracks and locally replan around predicted 5–7 yard
   ordinary aggro disks plus movement uncertainty. Compare against the road baseline.
3. **Combat calibration:** add/borrow a focused feral rotation, then collect entry-specific DPS,
   incoming DPS, TTK, ending health, and recovery time. Do not enable fight selection before this.
4. **Fight selector:** enable only the conservative inequality above, with each decision traced.
5. **Stealth:** park for this fixture. Re-open only if a higher Prowl rank becomes available or an
   empirical hosted test contradicts the exact DBC/core calculation.

### First live road contact

v100 supplied the first usable baseline. Fixed-duration ordinary steering followed the road for
872.08 living northing yards with no movement failure or damage, then contacted one Glasshide
Gazer near `(-8331,-3277)`. The replay measured 2,808 incoming damage over 108.7 seconds and zero
outgoing damage because the route policy stopped on combat; this is an avoidance case, not
evidence that fighting is cheap. The pinned navmesh accepts a northern waypoint at
`(-8350,-3180,14.1)` and a clean reconnection to road node 4. That two-leg corridor stays more
than 40 yards from the observed patrol position, compared with the baseline's 18.2-yard contact
sample, and is the next attributable dynamic-avoidance probe.

v101 falsified the direct northern bypass. It encountered a different hazard, one Dunemaul Brute
at `(-8396.0,-3178.9)`, at 4.1 yards and died after taking 2,825 damage over 83.8 seconds. The
paired traces expose a usable channel: v100 passed safely through `(-8401.8,-3220.7)`, 42 yards
south of the Brute, and a due-east leg at `y=-3220` stays 57 yards north of the observed Gazer.
The next probe therefore delays its deviation until the original road has passed the Brute, then
crosses between the two measured patrol positions. This remains route-first hazard handling; both
fights had zero policy damage and prohibit a fight-through inference.

v102 validated that channel at full health and reached road node 5. Its next contact at
`(-7989.2,-3488.8)` exposed a policy-level failure independent of route geometry: the first hit
dealt only 62 damage, leaving 2,692/2,754 health, but `_steer_road_leg` treated `in_combat` as a
terminal route failure and disconnected. The character then has no actor and is inevitably
killed during retention. The next probe keeps moving toward the road target during incidental
combat and traces the live attacker set plus combat exit. This is an escape edge, not a fight:
it preserves route-first handling and measures whether ordinary leash distance is cheaper than
another static detour.

v103 falsified run-through escape as a sufficient fallback. Its trace confirms continued physical
progress for roughly 100 yards, but one seed-dependent Glasshide Gazer had already pulled at 7.9
yards and remained engaged until death. This also proves fixed patrol coordinates are not a
complete model. The next probe consumes the canonical complete visible-unit set before contact:
hostiles within 30 yards ahead bend the next bounded pulse toward whichever side yields greater
clearance, the chosen side is retained until 40 yards clear, and activation/end are traced. The
30/40-yard hysteresis is deliberately wider than the measured 4.1-7.9-yard pull distances while
remaining local enough to avoid abandoning the road corridor.

v104 proved visibility is early enough—nine avoidance activations occurred before death—but
falsified “nearest unit plus sticky side.” It turned for off-corridor mobs and scored clearance
against only the trigger, so one avoidance could enter another hostile's envelope. The refined
edge test activates only when a hostile lies within an 18-yard forward corridor, evaluates both
side candidates against *all* nearby hostiles, changes the retained side only when the alternative
adds at least five yards of clearance, and uses an attacker-radial escape vector after contact.
This directly implements the geometry/live-overlay separation in the router shape above.

V105 did not test that refinement. Its request
`xreq_9e058bae-fea0-4824-9045-13333b28a992` landed immediately after canonical
vanilla-wow advanced from 0.1.208 to 0.1.209, and the older policy-side model rejected the new
`Unit.sub_name` and quest-reward observation fields before movement began. V106 is a
compatibility-only rebuild of the identical router against the exact 0.1.209 game image; its
hosted result is the first valid test of the cluster-clearance hypothesis.

V106 supplied that test and reached road node 4 before dying. At
`(-8188.5,-3307.9)`, a Rabid Blisterpaw 29.8 yards ahead triggered a right-side diversion;
three accelerated seconds later, a previously unselected Scorpid Dunestalker pulled from 3.2
yards. The router also alternated sides repeatedly around earlier moving Gazers. Two assumptions
were wrong: endpoint clearance does not model intersecting trajectories, and a 40-yard tracked
set is too short when one real control second advances ten game seconds. The next edge evaluator
tracks 80 yards, compares the entire candidate segment with each hostile's advertised movement
segment, clears stale avoidance when the projected forward corridor is empty, and permits a side
switch only below a 15-yard safety floor. Its activation trace records both candidate clearances
and every tracked destination so the next failure is attributable.
That evaluator is uploaded inert as wowborg:v107
(`d7f5fe7d-3d99-4924-88a1-e78865dcc3fd`, source `d33799e`).

V107 cleared the former Scorpid failure and reached road node 7 with 1,684.8 living northing
yards. It had already selected a right-side path around a Starving Blisterpaw at 46.9 yards, but
`_steer_road_leg` returned on guidepoint arrival and discarded that live routing state. The next
leg reactivated only when the same mob was 10.3 yards away, with predicted clearances of 10.0
yards right and 1.0 left; combat began one pulse later at 5.4 yards. The next change carries the
selected side across road-leg boundaries without changing the hazard geometry or thresholds.
That state-lifetime fix is uploaded inert as wowborg:v108
(`c2896a36-05a4-4a0c-ba88-83d8ae57c48c`, source `8376f77`).

V108 preserved the side through road node 7 and gained another 100 living northing yards. Its
next Glasshide Basilisk cluster produced only 11.9 yards of predicted right clearance and 2.2
left; the router still selected right, then pulled one Basilisk at 5.6 yards. This is a temporal
route edge: when neither bypass meets the existing 15-yard floor, remain outside ordinary aggro
and let the accelerated patrol move. The next candidate emits wait start/end, suspends the
no-progress timer while intentionally stationary, and resumes as soon as one side becomes safe.
That temporal edge is uploaded inert as wowborg:v109
(`6ada5206-cb39-4c3f-8b8b-db9b93fd86d6`, source `dc8fe3d`).

V109 activated `traverse_hazard_wait`, released once, then waited again with 14.5 yards of best
clearance from a Glasshide Petrifier. Stationary waiting was not safe: the accelerated patrol
crossed the character, pulled at close range, and moved back to its 29.5-yard casting distance.
The next temporal edge retains the last observation whose bypass met the 15-yard floor, retreats
to that point when the corridor becomes unsafe, and only waits once it reaches that known-safe
holding position.
That safe-holding edge is uploaded inert as wowborg:v110
(`e33c39e7-3653-4e45-957f-bad88258b67b`, source `e95156e`).

V110 emitted no `traverse_hazard_retreat`. The stored safe point was often the previous
seven-yard movement pulse, but the implementation reused the eight-yard road-guidepoint arrival
radius and therefore considered that holding point already reached. The next candidate changes
only safe-holding arrival to two yards, allowing the intended retreat to activate without
altering threat projection or the 15-yard clearance floor.
That radius-only correction is uploaded inert as wowborg:v111
(`3202f1c4-8a65-4f9b-b05a-f41523e11f3c`, source `3fd1b9c`).

V111 emitted repeated retreat start/end events, proving the radius correction activated the new
edge. It still pulled a Scorpid because every pulse that briefly restored 15 yards of clearance
overwrote the safe point while the encounter remained live; subsequent retreats collapsed into
6–7-yard oscillations around the hazard. The next candidate freezes the last clear-corridor
anchor for the entire encounter and updates it only after avoidance ends.
That anchor-lifetime correction is uploaded inert as wowborg:v112
(`9b8831af-2095-4505-98a5-ddf1e814fe54`, source `a20766f`).

V112 request `xreq_f8931af8-bc85-4073-85da-021d50524465` cleared 11 guidepoints and
reached 1,869.4 living northing yards, improving on every earlier 0.1.209 candidate. It then
pulled one Glasshide Basilisk at road node 8. The direct-away escape remained in combat for
7.9 seconds, moved 146 yards away from the road target, and lost 2,098 health before the generic
target-progress watchdog aborted at 595 health. This is the calibrated fight case described
above: one known non-elite level-45–49 attacker versus a level-60 player near full health, with
v73 already proving that exact-attacker melee can kill three such attackers without death. The
next candidate fights only when attacker count is one, the attacker is known non-elite and at
least ten levels lower, and player health is at least 80%; it preserves escape for every other
case and traces the decision inputs and outcome.
That calibrated single-pull combat edge is uploaded inert as wowborg:v113
(`ad98cbe0-d091-4f2b-8f73-3de152516a3a`, source `1e8ca0b`).
V113's uploaded argv incorrectly used `python -m wowborg.main`; that module defines but does not
invoke `main()`, so two requests failed before connection with empty logs and provided no gameplay
evidence. The identical image is re-uploaded inert as wowborg:v114
(`830a0fa0-7d92-416f-8c8a-0eabc9f1015e`) with the correct `python -m wowborg` entrypoint.

V114 request `xreq_a4c0fd12-fcf6-49b4-8dc6-fb46bb57b302` supplied the missing
current-contract combat calibration. The gate selected one level-48 Rabid Blisterpaw at 97%
player health, closed from 18 yards, and successfully faced and started auto-attack. Over the
next 1.7 seconds, basic melee dealt 413 damage while wowborg took 570. At the 80% health floor it
switched to escape and died. Current auto-attack is therefore not a safe or fast fight policy;
fight-through remains unavailable until a real feral rotation is calibrated.

The causal pre-pull defect was actuator precision. Both bypasses were unsafe, and the recorded
safe anchor was only 6.4 yards behind, but fixed 0.75-second forward-turn pulses repeatedly
orbited it rather than arriving within the two-yard hold radius. The next candidate returns to
v112's escape-only combat baseline and changes only safe-anchor arrival: turn in place first,
then use a distance-bounded forward pulse.
That precise safe-anchor arrival is uploaded inert as wowborg:v115
(`1035e292-5f91-4e18-9398-89161c4bc14a`, source `35d9050`).

V115 request `xreq_c8dbfd00-8211-4e47-88a7-9e6025b588ca` avoided all combat and
deaths, but reached only nine guidepoints before the episode timeout. The final retreat exposed
a second actuator defect: for 106 seconds, the character stayed at one position while alternating
left and right 0.25-second turn-only pulses. With the documented pi-radian/second turn rate, each
pulse rotates about 45 degrees and crosses the 0.20-radian precise-arrival deadband. The next
candidate scales precise-turn duration to remaining angular error divided by that turn rate,
capped at the existing 0.25 seconds. Ordinary steering and all hazard geometry are unchanged.

V116 request `xreq_21621766-8175-471c-91f9-2b748bfd7c5f` eliminated the alternating
sign symptom, but falsified continuous duration control. After three successful 0.25-second
turn-only pulses, its first 0.2188-second pulse timed out at frame 102 without advancing an
observation. The character was alive and out of combat after one guidepoint. Owner source also
shows `heldAxis` reduces every nonzero input magnitude to its sign, ruling out fractional turn
strength. The next candidate therefore retains the reliable 0.25-second, approximately 45-degree
turn quantum and widens only precise arrival's heading acceptance cone to that same angle.

V117 request `xreq_199cfdb3-6a1c-4918-a5ca-adb51b145caf` proved that quantized turns
settle reliably and ended six retreats, but exposed the geometric cost of the 45-degree acceptance
cone. During its fatal retreat, two quarter-second turns left a 39-degree residual heading. The
policy accepted it, moved forward on that diagonal, passed a Glasshide Gazer at 3.68 yards, and
died after three guidepoints. The action contract supplies signed strafe as a second binary
translation axis: forward plus left/right strafe moves at a 45-degree offset. The next candidate
uses that diagonal whenever residual heading exceeds 22.5 degrees, bounding translation error at
22.5 degrees while retaining only the already-proven duration quanta.

V118 request `xreq_e4e7e0ca-8a69-4b96-b84e-c115ef09896b` failed before testing that
geometry. The upstream action model and runtime accept `strafe`, but wowborg's local
`GymSession.select_move_vector` convenience method hard-coded zero and did not accept the keyword.
The policy stayed alive and out of combat, then raised the exact `TypeError` after one guidepoint.
The next source candidate adds only the missing wrapper pass-through; the diagonal strategy is
unchanged.

V119 request `xreq_bee76128-17b5-4bcc-adb5-899a08111294` supplied the first complete
proof of eight-direction retreat. Wowborg stayed at full health, never entered combat, reached
nine guidepoints and 1,320.1 living northing yards, and every retreat mechanically ended. It was
not efficient: 140 retreat activations and 139 side switches consumed the episode at road node 7.
The temporal defect is explicit in the trace: retreat ended as soon as projected clearance rose
above 15 yards, even 20–45 yards from the frozen safe anchor, then restarted when the moving
patrol made the next frame unsafe. The next candidate makes reaching the anchor, rather than a
momentary clearance change, the retreat completion condition.

V120 request `xreq_4bef2465-c2bc-4933-868d-dd048e53a561` confirmed the temporal fix:
retreat activations fell from 140 to seven and side switches from 139 to four. It also exposed the
remaining unsupported actuator shape. Once a persistent retreat approached its anchor, the
distance-derived 0.5629-second diagonal translation timed out at frame 559. The run reached three
guidepoints and escaped one pull. Exact 0.25-second actions already settle reliably and move about
2.45 yards in Travel Form, closely matching the two-yard hold radius. The next candidate therefore
uses that exact quantum for all precise translation instead of deriving duration continuously.

V121 request `xreq_7063f045-2013-4368-a884-1893ca923ad7` proved the fully quantized
actuator path with zero action timeouts and 13 completed retreats, but reached only three
guidepoints. The remaining failure repeated v109's already-established stationary-wait hazard:
at the final safe anchor, a moving Glasshide Gazer closed from 17.5 to 15.3 yards while wowborg
waited, then acquired it. Escape moved away from the route and triggered the progress watchdog.
The next candidate removes stationary unsafe-anchor waiting and uses quantized eight-direction
movement away from the active corridor hazards until a safe candidate reopens.

V122 request `xreq_5beaa43e-290d-47b3-a3bf-7e5ef8a0a282` proved that mobile hold:
three unsafe-anchor evasions ended without an action timeout, wowborg survived at full health,
and living northing improved from v121's 424.1 to 605.5 yards. The run then exposed an independent
ordinary-steering actuator defect at road node 3. From frames 592–650, 0.75-second forward-turn
pulses alternated left and right on every action and left the character 65.6 yards from the
guidepoint until the progress watchdog fired. The next candidate uses the already-proven
0.25-second turn-in-place quantum for ordinary heading correction while retaining 0.75-second
straight translation.

V123 request `xreq_46147008-1cf6-43d2-8f2f-37906b15240d` stayed full-health with
no combat or action timeout, but falsified turn quantization alone. The unchanged 0.20-radian
ordinary heading deadband made quarter turns alternate in place at road node 1. The next
candidate treats ordinary translation as the same discrete eight-direction actuator used for
precise movement: accept heading error through 45 degrees and add signed strafe beyond 22.5
degrees, selecting the nearest 45-degree translation direction without unsupported turn sizes.

V124 request `xreq_1686e46f-4062-43d6-b495-7db0ebd3e82e` proved discrete ordinary
steering by clearing the first two road nodes without a turn loop or action timeout. The next
failure calibrated the fixed bypass geometry: a 30-yard lateral candidate with 18.6 yards of
projected clearance passed the old 15-yard floor, then one 7.3-yard ordinary pulse consumed most
of that margin as a moving Glasshide Gazer closed to 16.5 yards, acquired, and killed wowborg.
The next candidate requires 25 yards of projected clearance and selects the shortest 30/45/60
yard lateral bypass that satisfies it, falling back to the highest-clearance candidate when every
width is unsafe.

V125 request `xreq_63741569-df7c-4a98-aae3-e374cf35f365` stayed full-health and
out of combat, and its activation telemetry proved all three lateral widths were selected. It
then exposed a physical-anchor failure rather than a scoring failure: a safe anchor only 5.9 yards
away was blocked, but wowborg issued 721 accepted quarter-second retreat translations without
moving. Persistent retreat reset the general route-stall timer on every frame. The next candidate
detects three consecutive retreat pulses below 0.5 yards, records the blocked anchor, and hands
control to the existing mobile hazard-evasion vector.

V126 request `xreq_2794b3ad-a849-4a1f-a733-e4659298a305` proved the blocked-anchor
transition 68 times, stayed full-health with no combat or timeout, cleared nine guidepoints, and
reached 1,318.5 living northing yards. Its remaining inefficiency was a route-geometry contract:
at road node 7, wowborg had crossed the node's northing by 23 yards and was only 32 yards lateral,
but the exact eight-yard arrival circle forced it to orbit the patrol cluster for the rest of the
episode. The next candidate accepts intermediate guidepoints after crossing their northing within
60 lateral yards while retaining exact eight-yard arrival at the Great Lift lower dock.

V127 request `xreq_dc68b02d-a892-4d7b-b73a-728569f395be` emitted the bounded pass,
stayed full-health with no combat or timeout, and improved to 11 guidepoints / 1,869.8 reported
northing yards; actual max x was another 156.6 yards ahead. Its remaining cost was 92 evasions and
66 blocked retreats under the 25-yard clearance floor. The measured tuning interval is now useful:
15 yards accepted v124's fatal 18.6-yard bypass, while 25 is safe but expensive across v125–v127.
The next candidate uses a 20-yard floor, rejecting the known fatal candidate while recovering five
yards of routing freedom.

V128 request `xreq_b8263b3b-87fe-4fa6-a0c4-9539f2ac875a` preserved the safety
result: full health, no combat, no death, and no action timeout. Relative to v127, avoidance fell
from 92 to 36 activations, blocked retreats from 66 to 28, and side switches from 50 to 22. It
reached 2,027.5 reported northing yards and actual max x -7159.5 before an ordinary collision at
Tanaris road node 9. From that point accepted 0.75-second forward inputs produced no displacement
until the eight-second route watchdog fired. The next candidate keeps that watchdog bounded but,
before terminating, tries one traced forward-diagonal recovery pulse on each side and requires
measured displacement to reset progress.
It is uploaded inert as **wowborg:v129**
(`e27cf658-ddef-4d2d-93fe-89b31c4b04dd`, source `29f415a`). Corrected Traverse
request `xreq_37c9ae98-da0f-424c-8176-6025218f4528` fired the recovery: the first
right pulse moved 0.781 yards and reset progress, but ordinary steering rewedged; the next left and
right pulses moved only 0.323 and 0.463 yards before bounded exhaustion. It survived at 2,011.7
northing yards after one Scorpid and one Basilisk contact, so diagonal unstick is not the route fix.

A deployed 0.1.209 Detour query from node 8 and both hosted stuck poses found a valid smooth route
to node 9, but not the coarse straight chord. The corridor bends through approximately
`(-7194,-3733)`, `(-7172,-3754)`, and `(-7097,-3795)` before the node-9 climb. The active candidate
adds these as exact anchors. They deliberately disable northing-pass completion: after hazard
displacement, regaining the first bend can require brief x-backtracking.
It is uploaded inert as **wowborg:v130**
(`c40c37d1-0396-4307-b850-bac8714e1d67`, source `187b820`). Request
`xreq_786d0482-defb-41da-970c-da0a8858156d` died near road node 2 before reaching
the new anchors, so it did not test the terrain correction. The fatal Scorpid was visible in the
tracked set at 63.2 yards but lay beyond the old 30-yard projected corridor. Avoidance activated
only at 27.8 yards; at 19.5 yards the best candidate clearance was 2.7 yards and contact followed.
The next candidate expands predictive entry/exit to 60/70 yards inside the existing 80-yard
tracked-unit envelope, preserving ten yards of observation margin while retaining hysteresis.
It is uploaded inert as **wowborg:v131**
(`e663e114-f50f-4246-b054-74e2e642474a`, source `811a92e`). Request
`xreq_cc157cd3-3f7a-469b-b954-55962bc1c8c9` survived but activated 55 avoidances
and ended 54, walked 5,942 trajectory yards for 1,842 northing, contacted three mobs, and timed out
at node 8. The widened horizon exposed a state defect rather than merely conservative tuning: a
bypass changes the line back to the guidepoint, the triggering patrol can drop from that new
corridor while still nearby, and wowborg then cuts back toward it. The next candidate retains
triggering hostiles by GUID until each is beyond the 70-yard exit radius, while allowing new
crossing patrols to join the active set.
It is uploaded inert as **wowborg:v132**
(`1ccd4562-dba9-458e-ac61-53e0afadb02f`, source `751998a`). Request
`xreq_27e8af9f-97b7-44dd-a7eb-285a398ce527` stayed full-health and contact-free,
and reduced avoidance lifecycle churn to three starts and two ends. But the continuously
recomputed target orbited retained patrols: 79 side switches, 142 retreats, only 150 net northing,
and a timeout at road node 1. The next candidate freezes a concrete 140-yard-ahead lateral
waypoint, releasing it on arrival and replanning only for a genuinely new crossing patrol.

## Open uncertainties

- The exact full-route navmesh cost of the owner road versus the current direct Great Lift line.
- Realized feral DPS and recovery time against each recurring Tanaris enemy.
- How far in advance moving units enter the player's complete visible-unit set; this determines
  the required static-prior/uncertainty buffer.
- Actual patrol velocity and wander distribution by spawn. The database's pinned spawn radius is
  not enough; historical trajectories already proved that.
- Whether any creature-specific spell or social-assist behavior makes a nominally safe single
  pull become a multi-attacker pull.

These are all measurable in hosted episodes. None justifies retaining the current opening detour
or enabling rank-1 Prowl.
