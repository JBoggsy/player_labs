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
It is uploaded inert as **wowborg:v133**
(`f9fb6c08-632e-46e5-b20f-76278b79371a`, source `f371bd1`). Request
`xreq_9a451cfa-f39f-41e5-ada4-d2573837a55b` replanned 23 times as new patrol
GUIDs entered its displaced path, left the owner road for the surrounding spawn field, and died to
a Glasshide Petrifier after only 142 net northing yards. The next candidate restores the proven
20-yard local sidestep and 30/40-yard immediate horizon. A separate 60-yard predictor holds on the
road for a moving patrol whose path stays at least 20 yards from the player; only an immediate
blocker or a patrol projected inside the holding radius triggers lateral avoidance.
It is uploaded inert as **wowborg:v134**
(`2354e2a4-a82c-4e25-a719-375e16dfc6c1`, source `11421a5`). Request
`xreq_f89a11e1-5c2f-4a1e-8518-1dfcc980adb3` stayed full-health with zero combat
and reached nine guidepoints, but spent 3,129 pulses holding and timed out at road node 7 after
1,605 net northing yards. A Roc repeatedly projected across the next guidepoint, showing that an
unbounded wait cannot clear a resident patrol. The next candidate caps holding at two wall seconds
per GUID, then treats a still-present patrol as a local blocker until it leaves the 80-yard tracked
set; brief trajectory jitter does not reset the timer.
It is uploaded inert as **wowborg:v135**
(`cef2e31f-773e-4045-b341-13cb6d3a7b59`, source `b03cabd`). Request
`xreq_cbb87d77-a2ed-48bb-a30e-205105a13733` escalated the first safe Scorpid
crossing, cascaded into a Glasshide Petrifier contact, and died at node 1 after only 96 net northing
yards. The timer conflated transient crossings with resident blockers. The next candidate instead
holds for genuine cross-traffic but locally avoids a moving patrol whose destination lies within
30 yards of the active guidepoint. The observed safe early Scorpid destination was about 188 yards
from node 1; v134's blocking Roc repeatedly targeted within about 12 yards of node 7.
It is uploaded inert as **wowborg:v136**
(`e604b7aa-fc13-4871-a7b5-bc1a084afb48`, source `ab358ec`). Request
`xreq_80a314cf-f183-43c1-bb7f-e818e708651e` was infrastructure-censored by a
30-second action-settlement timeout at node 3 while full-health. Fair repeat
`xreq_50cabc51-a8db-4a56-88b3-dba3884b0bd2` survived and recovered from one Tail
Lasher contact, but timed out at node 7 only about 14 yards from its center and just 5 yards short
of its exact northing threshold. The next candidate permits ordinary guidepoints to pass up to 20
yards before their target x while retaining the existing 60-yard lateral/z corridor. The three
Detour bend anchors and Great Lift remain exact.
It is uploaded inert as **wowborg:v137**
(`de9133dc-8ede-416d-98db-e2713ae88a6d`, source `b7bdcd1`). Request
`xreq_3c31de07-6a4e-40a6-87f0-c46126c03bbe` emitted eight ordinary pass events
through node 6, proving the completion change, but died to two Tail Lasher contacts before node 7.
Pinned 0.1.209 Detour recon found no connected broad north or south bypass around this pass. The
next candidate instead retains a crossing GUID while it remains within 70 yards or intersects
lookahead, holding without displacement. A projected path inside 20 yards of the holding point
still escalates to local avoidance, and guidepoint-resident classification remains active.
It is uploaded inert as **wowborg:v138**
(`cec936af-e9e3-4141-afaa-d693d0a4ccc4`, source `2d61417`). Request
`xreq_d1cd8097-6b68-4ba5-9e28-7c6c945374fe` stayed full-health with zero combat,
but spent 6,339 pulses holding and reached only road node 3. The retention rule exposed a more
basic classification defect: the no-hazard branch held for every moving hostile in lookahead,
whether or not its projected patrol crossed wowborg. The next candidate holds only an isolated
projected crossing; immediate and guidepoint-resident blockers still use local avoidance, and a
held crossing releases as soon as its projected trajectory clears.
It is uploaded inert as **wowborg:v139**
(`e97ab7d9-2c61-4f95-a334-3c3bf8eb78da`, source `bb9871f`). Request
`xreq_2d456355-d5b9-4d8c-936c-d239a369b07d` stayed full-health with zero combat,
reached all three exact Detour anchors and road node 9 in about 2.5 minutes, then failed the
Shimmering Flats south-ramp leg. Pinned 0.1.209 navmesh shows that reachable 265-yard corridor
bends through `(-6884,-3900,54)`, `(-6876,-3912,100)`, and `(-6848,-3925,125)`; direct steering
at the far endpoint repeatedly fell from the escarpment. The next candidate adds those three real
corridor bends as exact anchors without changing the proven Tanaris hazard policy.
It is uploaded inert as **wowborg:v140**
(`191f1a51-9c67-46a1-8e5e-dc4d28efb9a3`, source `3ef7543`). Request
`xreq_7ce2cbdf-f84f-4bc4-ae06-5d6be2189fdd` remained alive, reached the same 15
Tanaris milestones, and had one brief contact costing 56 health, but an unusually dense hazard
draw took 238 seconds to road node 9 and left only 29 seconds for the first ramp anchor. The ramp
geometry is not falsified; the fixed episode horizon makes actuator throughput the binding
constraint. The next candidate doubles open translation from 0.75 to 1.5 seconds while keeping
0.25-second precision for turns, retreat/evasion, and the final 20 yards of every target. Its
roughly 10.5-yard open stride remains inside the existing 30-yard immediate hazard gate.
It is uploaded inert as **wowborg:v141**
(`53afe44e-b6aa-4880-9111-eeffe620e64f`, source `1c051b2`). Request
`xreq_8ab6b8b3-5215-4506-8817-864538ef59a8` reached road node 7 six seconds
faster than v139, but the longer stride closed on a Glasshide Basilisk to 2.7 yards and died before
node 8. The stride is unsafe and its speed gain is small. Trace/code reconciliation found the real
throughput defect: each synchronous vector action already returns its settled next frame, but
Traverse then submitted a redundant 0.25-second wait before every next pulse. The next candidate
restores the proven 0.75-second stride and removes that wait, increasing movement duty cycle from
75% to 100% without increasing one-pulse hazard reaction distance.
It is uploaded inert as **wowborg:v142**
(`663ecd3e-10eb-4ba4-9a73-0cf33d43a33c`, source `c126d76`). First request
`xreq_5a105daa-13a3-4304-be2b-515587f6da89` stayed full-health with zero combat
and reached the Detour bend in 132 seconds, but one action timed out after 30 seconds while the
prior 948 actions all settled (p99 377 ms). Fair repeat
`xreq_c60c6458-3659-4a37-a8ef-63b35a372b60` again stayed full-health, reached all
three exact bend anchors, then hit the same timeout after roughly 985 uninterrupted actions. The
next candidate yields for 0.25 seconds every eight settled pulses: roughly 97% movement duty cycle
versus the original 75%, with a periodic host settlement seam.
It is uploaded inert as **wowborg:v143**
(`0f9033bc-0247-4843-9b77-2af1292a43f8`, source `c40a81b`). Request
`xreq_79ff2e95-2930-444c-8026-3c30c5066a75` executed 165 scheduled yields
without v142's repeated host timeout, stayed full-health/zero-combat through Tanaris, and reached
road node 9 in 164 seconds. The first ramp anchor was still too coarse for discrete steering:
wowborg ran east along the cliff edge and fell before reaching its required southward bend. The
next candidate splits the pinned navmesh approach at `(-6905,-3869,39)` and
`(-6890,-3885,48)` before the existing exact base anchor.
It is uploaded inert as **wowborg:v144**
(`bb21cd9f-2573-4f1c-bfd2-ff5be57842ac`, source `3e2d09c`). Request
`xreq_98016dca-efdf-4bbb-b394-b52d6ebb6433` stayed full-health with zero combat,
but was infrastructure-censored before reaching the new ramp anchors: another 0.75-second action
timed out at about `(-7155,-3769)` on the exact Detour-east leg. Sparse yields improve ordinary
road cadence, but this tight bend needs v139's every-pulse settlement seam. The next candidate
yields after every pulse on exact anchors and every eight pulses on ordinary roads.
It is uploaded inert as **wowborg:v145**
(`dbbc1e08-2f0a-42b8-b79f-9f1e010d72af`, source `9e0c895`). Request
`xreq_07f6e8d6-9bdc-44a6-8102-a18ad3a0c3b5` stayed full-health with zero combat
and removed the action timeout, but exhausted unstick at about `(-7144,-3767)` on Detour-east.
Pinned 0.1.209 navmesh shows the corridor stays shallow to `(-7129,-3767)` before turning
southeast; direct steering forced the diagonal too early. The next candidate adds that real turn
as an exact anchor so crossing no longer depends on v139's lucky left unstick.
It is uploaded inert as **wowborg:v146**
(`8fe6eaee-e885-4117-bc6e-b5b10035d602`, source `41ed1b2`). First request
`xreq_b3f7b4b0-d3ab-447b-a4d2-94505149ad67` was censored by unrelated early
hazard displacement before the changed bend. Fair repeat
`xreq_df6ba150-777d-4417-a4cd-02256116bc59` proved the new exact turn and final
Detour-east anchor at full health with zero combat, but exposed an upstream completion defect:
ordinary node 9 passed at z `-22.7` versus target z `28.9` because its 60-yard pass tolerance
combined y and z. The ramp therefore began below terrain and repeatedly fell/reset. The next
candidate retains 60 yards of horizontal hazard-displacement slack but requires vertical error at
most 10 yards before an ordinary milestone can pass.
It is uploaded inert as **wowborg:v147**
(`9ddebbfa-f068-41be-9ea5-32648a60d8c6`, source `57ed0da`). Request
`xreq_25bda105-0daf-4943-aa2e-e3f0c87ec9a4` enforced vertical alignment on all
11 ordinary pass events (maximum 8.2 yards), reached node 9 within 0.9 vertical yards, and emitted
the first exact ramp-approach arrival. It then fell approaching the ramp turn. The shared 8-yard
exact radius is too loose for the narrow slope; the next candidate tightens only the ramp anchors
to 3 yards while retaining existing tolerances for Detour anchors and the lower-dock goal.
It is uploaded inert as **wowborg:v148**
(`52ad576d-0fc3-4ab4-9570-db29744840f0`, source `205e9e7`). Its first request
`xreq_36342e76-936c-4950-9f14-c6552ae08b6b` was combat-censored before the ramp. Two
full-health zero-combat repeats (`xreq_dc28e85e-d277-4add-8f0c-290e4c6596cf` and
`xreq_c82b3f22-a720-4816-944c-9c9bd5e786de`) both cleared the four exact Detour anchors,
then lost the returned frame on the second ordinary node-9 translation. The latter trace records
the 0.75-second action at `(-7096.53,-3793.63,8.43)` timing out after 30 seconds while the game
host recorded hundreds of WebSocket detach/reattach cycles. The ramp-radius change therefore
remains unexercised. The next candidate reduces exposure to that host churn with a conservative
1.0-second translation only when no road hazard or combat is visible and the target is more than
20 yards away; turns and all hazard/arrival pulses retain their prior cadence. Every longer pulse
emits `traverse_road_open_stride`. It is uploaded inert as **wowborg:v149**
(`b8f24e46-e596-4f20-b154-fb8ed19166a3`, source `4c5e9fc`). Request
`xreq_e218fe41-65f7-414d-a012-066a04b1e7d4` fired 258 longer pulses, stayed at
full health with zero combat, and reached node 9 in about 128 seconds. It then repeatedly reached
the safe ramp lip near `(-6912,-3859,39)`, but generic resident-hazard detours stepped laterally off
the narrow elevated corridor, fell/reset, and consumed the rest of the episode. The next candidate
holds instead of laterally detouring when a resident hazard projects into one of the six tight ramp
anchors; ordinary roads keep their existing dynamic detours. The hold emits reason
`terrain_constrained_resident` and releases when no tracked resident still projects into the
target corridor. It is uploaded inert as **wowborg:v150**
(`a2d455f5-da0b-4e61-8dd2-d0e637c3e998`, source `c71e07d`). Request
`xreq_6b180e18-2154-4427-a3ee-1e26f5cce2ba` reached node 9 at full health, then
activated one terrain-constrained hold for a Basilisk still 60.7 yards away and never released
before the episode deadline. The next candidate holds only an imminent resident inside the
existing 30-yard hazard-entry gate; far projected residents may be crossed before they arrive.
Rank-1 Prowl remains invalid here because its exact detection range is worse than visible level-gap
aggro, and current basic melee remains too weak to promote over the timing solution. It is uploaded
inert as **wowborg:v151** (`6aa3b0e1-c341-446b-8be2-db4b93d7c6bb`, source `b37617e`).
Request `xreq_9e8b2946-9085-49c6-8ad1-14b8d2a7ee5e` reached node 9 at full health,
activated three terrain holds, released twice near 29 yards, then remained blocked at 23.1 yards.
The next candidate suppresses ordinary lateral detours for a resident on the only narrow ramp
edge, crosses straight while its current distance exceeds the existing 20-yard safety floor, and
holds at or inside 20 yards. This retains roughly 13 yards over the measured 5–7-yard visible aggro
radius without reviving uncalibrated melee or inferior rank-1 Prowl. It is uploaded inert as
**wowborg:v152** (`1876851a-0885-433e-be17-055734567913`, source `376d854`).
First request `xreq_0bb6ba02-9257-423e-bed2-54e37ce62f20` died before the changed ramp.
Fair repeat `xreq_5a742ce8-92be-4064-a812-f65bc032db88` stayed at full health, reached
node 9, and exercised 29 terrain holds with 28 releases, but never arrived at the approach. Its
positions repeatedly identify a stable ramp lip at `(-6911.46,-3859.38,39.24)` before direct
steering cuts off the slope. The next candidate inserts that observed lip as a three-yard exact
anchor before the existing approach; v152 hazard timing is unchanged. It is uploaded inert as
**wowborg:v153** (`11b765a4-2eaf-419f-8a1d-8d848baa067a`, source `c838e20`).
First request `xreq_7b7b2089-a15e-4294-9486-882ff7306868` stopped before the changed
anchor. Fair repeat `xreq_fb01b524-ea4d-497b-8fa0-f8a1d4f94966` reached the new lip at
full health as milestone 17, then remained six yards from the broad approach while a Basilisk held
at 16.8 yards. The next candidate separates terrain-constrained hazard handling from three-yard
arrival precision: the approach retains ramp hold semantics but restores its sufficient eight-yard
arrival, while the lip and later narrow bends remain three-yard anchors.
It is uploaded inert as **wowborg:v154**
(`4b12b163-c947-4fee-969f-cd6b7110e01f`, source `e030d61`). This is a single
mechanism change: route geometry and hazard timing are identical to v153, so reaching the approach
will isolate the former three-yard arrival tolerance as the blocker.
Request `xreq_2a2d6324-4fb2-470a-8aad-14dc08e7091f` reached both the lip and approach
at full health with zero combat, validating that mechanism. It then cycled 18 constrained-ramp
holds and 17 releases for 86 seconds at the ramp-turn frontier. The recurring Scorpid is about
6.4 yards from the turn anchor; the conservative 20-yard floor therefore cannot complete this
route even though ordinary level-gap aggro was measured at 5–7 yards. The next source candidate
changes only that floor to 8 yards. Ordinary-road avoidance and route geometry remain unchanged.
It is uploaded inert as **wowborg:v155**
(`1345f357-a3eb-414d-9942-7fe54be5e726`, source `e7fc2c4`).
Request `xreq_801ccdf9-44a7-4f37-8b2e-e5a294999fd1` reached ramp-turn milestone 19,
then pulled the Scorpid at 4.9 yards and died. The important precursor was geometric: generic
lateral evasion for the stationary Scorpid had already moved wowborg off the supported ramp, with
observed z falling through 25, 18, 10, and -35 before the host returned it to the requested
anchor. A pinned 0.1.209 navmesh offset sweep found that complete approach-to-base paths converge
within about 4.5 yards of the Scorpid; candidates with 9–10 yards of clearance terminate on a
disconnected ledge. There is no legitimate geometric bypass. The next source candidate treats
every immediate or resident hazard inside eight yards as a hold on terrain-constrained anchors
and suppresses open-road lateral evasion there. This should establish a supported pre-fight
frontier without yet changing combat.
It is uploaded inert as **wowborg:v156**
(`35d3023e-a376-4d35-9207-c9424582c2d2`, source `be61bff`).
Request `xreq_6ba1066e-b154-4a7b-bc5e-83bdc2054c06` reached milestones 17–18 and
validated the supported frontier: over 429 pre-combat observations, z stayed within 34.6–39.2 and
no constrained-ramp avoidance or evasion activated. After 25 seconds, the resident wandered into
aggro at 6.7 yards; escape pulled a second Basilisk and died. Waiting therefore reduces but cannot
remove the pinch hazard. External Classic data places entry 5422 at level 40–41 with roughly
1.8–2.0k health, while v114 measured 243 basic-melee DPS and the two escape runs imply roughly
200–213 incoming DPS. That predicts an approximately eight-second basic kill inside a roughly
13-second full-health survival window. The next source candidate commits only against this exact,
single, non-elite Scorpid and ports the game repo's maintained real-playerbot feral ordering: Cat
Form, Rake while healthy, Claw builders, and Rip at three combo points. Every other contact still
escapes.
That candidate is uploaded inert as **wowborg:v157**
(`e8629df4-2707-4729-9514-a9dcb14d512d`, source `c456c34`). Route geometry,
terrain holds, and all other-contact behavior are unchanged, so the hosted result isolates the
fight decision and realized feral time-to-kill.
Request `xreq_d2a1e397-b199-4cd0-be8e-43b5cffa1eb7` and three-run request
`xreq_3ac8997c-c6bf-451e-8292-46ee09323961` produced zero fight activations.
Three episodes exhausted on the variable road prefix; the remaining episode reached the ramp
approach healthy and held for 82 seconds, but the resident never wandered into aggro. A reactive
fight therefore does not convert the hold into a bounded edge cost. The next source candidate
proactively moves to and attacks the same uniquely qualifying sub-eight-yard Scorpid; all other
contacts retain avoidance/escape.
That candidate is uploaded inert as **wowborg:v158**
(`6d531041-bc99-4755-a0c8-9a4d10457391`, source `4d0a8af`).
Six-run request `xreq_903ae02b-bfc0-4f52-9150-8164d764711e` produced two exact
proactive activations: a level-40 Scorpid at 5.0 yards and a level-41 Scorpid at 7.7 yards. Neither
reached attack. Both repeatedly invoked Cat Form while Travel Form was active, and host telemetry
reported "You are in shapeshift form" until deadline. This is a form-transition defect, not a
combat-strength result. The next source candidate follows the maintained real-playerbot pattern:
invoke the observed active-form binding to leave Travel Form, then enter Cat on the next frame.
That candidate is uploaded inert as **wowborg:v159**
(`083b6d20-c164-485d-b828-672a6a05e9ae`, source `d737576`).
Six-run request `xreq_b7d21eda-82b8-46ec-9206-4e5906fff375` produced two exact
proactive activations, but invoking the current-form spell still did not toggle Travel Form off.
The current environment action catalog exposes `cancel_aura` for every active beneficial aura;
the next source candidate invokes that typed action for spell 783, then enters Cat on the next
frame. This keeps the transition inside the current public action contract rather than emulating a
keypress or adding a compatibility path.
That candidate is uploaded inert as **wowborg:v160**
(`84f82e8c-f928-4e29-851e-5a2a8b2e0736`, source `b5f3e95`).
Six-run request `xreq_a732a990-eb51-4157-bb7c-c025c48eac9b` produced the first
successful ramp kill. Typed form exit and Cat entry succeeded; the level-41 Scorpid died in 34.0
seconds after 1,956 damage dealt and only 110 taken, and wowborg survived at full health. This
confirms that fighting the unavoidable pinch is safe. It is not yet efficient: host telemetry shows
Rake and Claw were invoked without their required target (`select target` / `cancelled`), leaving
repeated auto-attacks to do the work. The next source candidate supplies the exact Scorpid GUID to
Rake, Claw, and Rip.
That candidate is uploaded inert as **wowborg:v161**
(`922c2942-06d8-4b55-8ac1-bedf7bb41522`, source `f83906a`).
Six-run request `xreq_dd819d01-f854-4b36-b482-128fb24fc8a6` produced one ramp
fight. The exact GUID reached the environment command, but host telemetry rejected the first Rake
as `Out of range`; the route stopped closing at five reported combat yards while the ramp still had
material vertical separation. Auto-attacks again killed the Scorpid in 34.3 seconds (1,946 dealt /
367 taken). Wowborg survived and reached ramp-base milestone 20, the first clean post-kill advance.
The next source candidate closes to two reported yards before attacking so the ramp's 3D geometry
cannot leave melee abilities outside range.
That candidate is uploaded inert as **wowborg:v162**
(`b1dfbc40-2631-4b5d-8581-83ec6e6a935f`, source `8057d2e`).
Six-run request `xreq_c726b42a-4b82-4961-814c-2b16afd16ee1` produced three safe
ramp kills. One fight landed Rake and two Claws, while the other two remained auto-attack kills;
all lasted 33-36 seconds. The best run reached ramp-base milestone 20 but exhausted the 270-second
horizon there. Its trace spent 266 seconds in 1,452 action round trips, including 395 one-second
hazard-free strides. The next source candidate changes only clear-road strides to four seconds.
At observed Travel Form speed each remains inside the existing 80-yard tracked-hazard horizon;
hazard, ramp, retreat, combat, and turn actions retain their shorter durations.
That candidate is uploaded inert as **wowborg:v163**
(`c111df42-03f8-42c4-bc67-40e7603270c3`, source `99d2555`).
Request `xreq_9523234d-13d1-40e6-b099-47a4df0b76e7` failed identically in all six
episodes at the first clear stride. Canonical 0.1.209 constrains `move_vector.duration` to at most
1.5 seconds, so the four-second action raised local validation before reaching the host. The next
source candidate uses the contract maximum of 1.5 seconds.
That candidate is uploaded inert as **wowborg:v164**
(`a14b004c-0efa-481b-8cf9-d88263ce521d`, source `8ada40f`).

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
