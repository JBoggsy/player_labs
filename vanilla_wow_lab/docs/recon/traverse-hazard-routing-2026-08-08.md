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
