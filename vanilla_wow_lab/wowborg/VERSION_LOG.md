# wowborg version log

## v166 - Ferocious Bite ramp finisher (2026-08-09)

- Version UUID: `327685d0-0d64-4bd5-a606-322610bff48f` (`wowborg:v166`, uploaded
  inert; not submitted). Built from source `937f6ec` against canonical vanilla-wow 0.1.209.
- Adds the maintained Ferocious Bite family only when the qualifying ramp Scorpid is at or below
  40% health and wowborg has five combo points. Rake, Rip, Claw, fight admission, route geometry,
  and every other-contact behavior are unchanged from the safe v162 baseline.
- Feral spell traces now record pre-cast combo points and active power, distinguishing an unknown
  spell or unmet resource gate from a host rejection. The hosted request is pending.

## v165 - forward-progressing local bypasses (2026-08-09)

- Version UUID: `3b4b7594-a711-456c-8d36-8cf282d241cc` (`wowborg:v165`, uploaded
  inert; not submitted). Built from source `1086b45` against canonical vanilla-wow 0.1.209.
- Restores v162's proven one-second clear stride and changes only local hazard candidates from 20
  to 40 yards forward. Adaptive lateral widths and the mandatory 20-yard clearance are unchanged.
- The tangent remains inside the 60-yard lookahead and 80-yard tracking horizons. This isolates
  avoidance path efficiency without weakening the hazard gate.
- Six-run request `xreq_e02535ab-4616-4c12-a8c0-b242294471dd` survived without a
  death, but reached only milestones 15, 18, 18, 18, 20, and 20. Ramp approach/base arrival
  ranged from 166.7 to 210.1 seconds while each run still activated 40-51 avoidances and 31-49
  retreats. The farther tangent did not consistently reduce state churn or improve the frontier,
  so source restores the proven 20-yard forward component before the next experiment.

## v164 - maximum valid clear-road stride (2026-08-09)

- Version UUID: `a14b004c-0efa-481b-8cf9-d88263ce521d` (`wowborg:v164`, uploaded
  inert; not submitted). Built from source `8ada40f` against canonical vanilla-wow 0.1.209.
- Extends only hazard-free, non-combat road translations from one second to the contract maximum
  of 1.5 seconds. All safety behavior and route geometry are unchanged from v162.
- Six-run request `xreq_414ce1c9-2d56-40f0-b372-6d44a5458d60` showed only a marginal
  representative ramp-arrival gain (about 202 to 190 seconds), while longer blind translations
  produced up to three earlier pulls in one episode and one ramp death. The next candidate restores
  the proven one-second clear stride before changing hazard-path efficiency.

## v163 - four-second clear-road strides (2026-08-09)

- Version UUID: `c111df42-03f8-42c4-bc67-40e7603270c3` (`wowborg:v163`, uploaded
  inert; not submitted). Built from source `99d2555` against canonical vanilla-wow 0.1.209.
- Extends only hazard-free, non-combat road translations from one second to four seconds, reducing
  fixed action-round-trip overhead while remaining inside the existing 80-yard hazard horizon.
- Turns, visible-hazard steering, retreat, evasion, ramp movement, combat, route geometry, and all
  hazard thresholds are unchanged from v162. This isolates safe-route throughput.
- Request `xreq_9523234d-13d1-40e6-b099-47a4df0b76e7` failed identically in all six
  episodes at the first clear stride: the canonical action model constrains `move_vector.duration`
  to at most 1.5 seconds, so constructing the four-second action raised validation before host
  submission. The next candidate uses the contract maximum of 1.5 seconds.

## v162 - close fully into feral range (2026-08-09)

- Version UUID: `b1dfbc40-2631-4b5d-8581-83ec6e6a935f` (`wowborg:v162`, uploaded
  inert; not submitted). Built from source `8057d2e` against canonical vanilla-wow 0.1.209.
- Closes to two reported yards before the first attack against the qualifying ramp Scorpid, rather
  than stopping at five yards where the ramp's vertical separation left Rake out of range.
- Exact targeting, form transition, rotation, route geometry, and all other-contact behavior are
  unchanged from v161. This isolates realized feral ability use and time-to-kill.
- Six-run request `xreq_c726b42a-4b82-4961-814c-2b16afd16ee1` produced three ramp
  fights and three safe kills. One fight landed Rake and two Claws; the other two oscillated at
  3.8-8.8 yards and used auto-attacks. All lasted 33-36 seconds, and the best run reached ramp-base
  milestone 20 before the 270-second horizon. Its 1,452 action round trips consumed 266 seconds,
  including 395 one-second hazard-free strides. The next candidate changes only those clear-road
  strides to four seconds; hazard, ramp, retreat, combat, and turn actions remain short.

## v161 - exact-target feral ramp rotation (2026-08-09)

- Version UUID: `922c2942-06d8-4b55-8ac1-bedf7bb41522` (`wowborg:v161`, uploaded
  inert; not submitted). Built from source `f83906a` against canonical vanilla-wow 0.1.209.
- Supplies the qualifying Scorpid's exact GUID to Rake, Claw, and Rip, using the environment's
  existing targeted-spell invocation contract.
- Form transition, target gate, proactive closing, route geometry, and all other-contact behavior
  are unchanged from v160. This isolates realized feral rotation and time-to-kill.
- Six-run request `xreq_dd819d01-f854-4b36-b482-128fb24fc8a6` produced one ramp
  fight. The exact GUID reached the spell command, but host telemetry rejected the first Rake as
  `Out of range`; auto-attacks again killed the mob in 34.3 seconds (1,946 dealt / 367 taken).
  Wowborg survived and reached ramp-base milestone 20, the first clean post-kill advance. The next
  candidate closes to two reported yards before its first attack to absorb the ramp's vertical
  separation and bring melee abilities into range.

## v160 - typed Travel Form aura cancellation (2026-08-09)

- Version UUID: `84f82e8c-f928-4e29-851e-5a2a8b2e0736` (`wowborg:v160`, uploaded
  inert; not submitted). Built from source `b5f3e95` against canonical vanilla-wow 0.1.209.
- Leaves Travel Form through the environment's typed `cancel_aura` action on the observed active
  form spell, then enters Cat on the next frame.
- Target selection, proactive closing, feral rotation, route geometry, and all other-contact
  behavior are unchanged from v159.
- Six-run request `xreq_a732a990-eb51-4157-bb7c-c025c48eac9b` produced one ramp
  fight: typed form exit and Cat entry succeeded, the level-41 Scorpid died in 34.0 seconds after
  1,956 damage dealt and only 110 taken, and wowborg survived at full health. Host telemetry showed
  Rake/Claw were invoked without their required target (`select target` / `cancelled`), leaving
  repeated auto-attacks to do the work. The next candidate supplies the exact Scorpid GUID to every
  offensive feral spell.

## v159 - observed-form transition before ramp combat (2026-08-09)

- Version UUID: `083b6d20-c164-485d-b828-672a6a05e9ae` (`wowborg:v159`, uploaded
  inert; not submitted). Built from source `d737576` against canonical vanilla-wow 0.1.209.
- When ramp combat activates from another form, invokes the observed current-form spell binding to
  leave that form before entering Cat on the next frame, matching maintained real-playerbot.
- Target selection, proactive closing, feral rotation, route geometry, and every other-contact
  behavior are unchanged from v158.
- Six-run request `xreq_b7d21eda-82b8-46ec-9206-4e5906fff375` produced two exact
  proactive activations, but invoking the current-form spell still did not toggle Travel Form off.
  The current environment exposes the intended `cancel_aura` action for active beneficial auras;
  the next candidate uses that typed action for spell 783 before entering Cat.

## v158 - proactive constrained-ramp Scorpid pull (2026-08-09)

- Version UUID: `6d531041-bc99-4755-a0c8-9a4d10457391` (`wowborg:v158`, uploaded
  inert; not submitted). Built from source `4d0a8af` against canonical vanilla-wow 0.1.209.
- When the exact v157 fight gate sees one qualifying Scorpid inside eight yards before combat,
  wowborg now closes to melee and attacks proactively. The feral rotation and multi-attacker abort
  are unchanged.
- Route geometry, terrain holds, ordinary-road avoidance, and all other-contact behavior are
  unchanged. This isolates fight activation and realized time-to-kill from the v157 null probes.
- Six-run request `xreq_903ae02b-bfc0-4f52-9150-8164d764711e` produced two exact
  proactive activations (level 40 at 5.0 yards and level 41 at 7.7 yards), but neither attacked.
  Both repeatedly invoked Cat Form while Travel Form was active; host telemetry returned "You are
  in shapeshift form" until the episode deadline. The next candidate follows the maintained
  real-playerbot transition: invoke the observed current-form binding to leave Travel Form, then
  enter Cat on the next frame.

## v157 - focused constrained-ramp feral fight (2026-08-09)

- Version UUID: `e8629df4-2707-4729-9514-a9dcb14d512d` (`wowborg:v157`, uploaded
  inert; not submitted). Built from source `c456c34` against canonical vanilla-wow 0.1.209.
- Adds combat only when exactly one non-elite entry-5422 Scorpid Hunter at level 40–41 attacks on
  a terrain-constrained ramp anchor. It enters Cat Form, uses Rake while healthy, Claw builders,
  and Rip at three combo points; all other contacts retain the existing escape behavior.
- Route geometry, terrain holds, ordinary-road avoidance, and arrival radii are unchanged from
  v156. This isolates whether the unavoidable ramp pinch is fast and survivable to fight through.
- Request `xreq_d2a1e397-b199-4cd0-be8e-43b5cffa1eb7` and three-run request
  `xreq_3ac8997c-c6bf-451e-8292-46ee09323961` produced no fight activations: three
  episodes exhausted earlier on the variable road prefix, while one reached ramp approach healthy
  and spent 82 seconds holding without the Scorpid wandering into aggro. The next candidate
  proactively closes on and attacks the same uniquely qualifying sub-eight-yard resident instead
  of waiting for a reactive pull.

## v156 - constrained-ramp centerline holds (2026-08-09)

- Version UUID: `35d3023e-a376-4d35-9207-c9424582c2d2` (`wowborg:v156`, uploaded
  inert; not submitted). Built from source `be61bff` against canonical vanilla-wow 0.1.209.
- On terrain-constrained anchors, holds for any immediate or resident hostile inside eight yards
  and suppresses open-road lateral evasion. Outside that gate it follows the canonical centerline.
- Combat, ordinary-road avoidance, route geometry, and arrival radii are unchanged from v155.
  This isolates whether wowborg can establish a supported pre-Scorpid frontier.
- Request `xreq_6ba1066e-b154-4a7b-bc5e-83bdc2054c06` reached milestones 17–18 and
  established a 25-second centerline hold with zero constrained-ramp avoidance/evasion events;
  pre-combat z stayed within 34.6–39.2. The resident then wandered into aggro at 6.7 yards, escape
  pulled a Basilisk, and wowborg died. The next candidate commits only against this single,
  non-elite level-40/41 Scorpid and ports the maintained real-playerbot Cat/Rake/Claw/Rip pattern.

## v155 - calibrated ramp hold floor (2026-08-09)

- Version UUID: `1345f357-a3eb-414d-9942-7fe54be5e726` (`wowborg:v155`, uploaded
  inert; not submitted). Built from source `e7fc2c4` against canonical vanilla-wow 0.1.209.
- Reduces only the terrain-constrained resident hold floor from 20 to 8 yards. This retains a
  one-yard margin over the measured 5–7-yard visible level-gap aggro radius while allowing the
  route to approach the recurring Scorpid 6.4 yards from the ramp-turn anchor.
- Ordinary-road hazard avoidance, crossing holds, route geometry, and arrival precision are
  unchanged from v154.
- Request `xreq_801ccdf9-44a7-4f37-8b2e-e5a294999fd1` reached ramp-turn milestone
  19, but pulled the Scorpid at 4.9 yards and died after falling from the ramp during the preceding
  stationary-hostile evasion. Pinned-navmesh recon found no connected bypass: complete paths pass
  within about 4.5 yards of the Scorpid, while 9–10-yard-clearance offsets end on disconnected
  ledges. The next candidate makes every sub-eight-yard ramp hazard a hold and suppresses all
  open-road lateral evasion on terrain-constrained anchors.

## v154 - broad ramp approach arrival (2026-08-09)

- Version UUID: `4b12b163-c947-4fee-969f-cd6b7110e01f` (`wowborg:v154`, uploaded
  inert; not submitted). Built from source `e030d61` against canonical vanilla-wow 0.1.209.
- Separates the terrain-constrained hazard set from the three-yard tight-arrival set. The broad
  ramp approach keeps resident hold/crossing semantics but restores its sufficient eight-yard
  arrival radius; the observed lip and later narrow bends remain three-yard exact anchors.
- v153 route geometry, hazard timing, and ordinary-road behavior are unchanged. The hosted probe
  should distinguish arrival-tolerance failure from a subsequent ramp-turn failure.
- Request `xreq_2a2d6324-4fb2-470a-8aad-14dc08e7091f` reached both the exact lip and
  broad approach at full health with zero combat. It then spent the remaining 86 seconds cycling
  terrain holds at the ramp-turn frontier. The next candidate reduces only that constrained-ramp
  floor from 20 to 8 yards, still above the measured 5–7-yard visible aggro radius.

## v153 - observed Shimmering Flats ramp lip (2026-08-09)

- Version UUID: `11b765a4-2eaf-419f-8a1d-8d848baa067a` (`wowborg:v153`, uploaded
  inert; not submitted). Built from source `c838e20` against canonical vanilla-wow 0.1.209.
- Inserts the repeatedly observed stable lip at `(-6911.46,-3859.38,39.24)` as a three-yard exact,
  terrain-constrained anchor before the existing ramp approach. This makes the final short slope
  leg begin from the correct heading instead of cutting diagonally off terrain.
- v152 hazard timing, ordinary-road behavior, and all later ramp anchors are unchanged.
- First request `xreq_7b7b2089-a15e-4294-9486-882ff7306868` stopped before the changed
  anchor. Fair repeat `xreq_fb01b524-ea4d-497b-8fa0-f8a1d4f94966` reached the lip at full
  health, then remained six yards from the approach while a Basilisk held at 16.8 yards. The next
  candidate restores only that broad approach's sufficient eight-yard arrival radius.

## v152 - timed crossing on the narrow ramp (2026-08-09)

- Version UUID: `1876851a-0885-433e-be17-055734567913` (`wowborg:v152`, uploaded
  inert; not submitted). Built from source `376d854` against canonical vanilla-wow 0.1.209.
- For a resident projected onto a terrain-constrained ramp, crosses straight while current
  distance exceeds the existing 20-yard safety floor and holds at or inside 20 yards. The far
  resident cannot fall through to ordinary lateral detouring on the only traversable edge.
- The 20-yard gate retains roughly 13 yards over the measured 5–7-yard ordinary aggro radius.
  Rank-1 Prowl and uncalibrated basic melee remain disabled.
- First request `xreq_0bb6ba02-9257-423e-bed2-54e37ce62f20` died before the changed ramp.
  Fair repeat `xreq_5a742ce8-92be-4064-a812-f65bc032db88` stayed at full health and
  exercised 29 terrain holds with 28 releases, but repeatedly cut off the slope after reaching the
  stable lip at `(-6911.46,-3859.38,39.24)`. The next candidate makes that lip an exact anchor.

## v151 - imminent-only narrow-ramp holds (2026-08-09)

- Version UUID: `6aa3b0e1-c341-446b-8be2-db4b93d7c6bb` (`wowborg:v151`, uploaded
  inert; not submitted). Built from source `b37617e` against canonical vanilla-wow 0.1.209.
- Limits the terrain-constrained resident hold to hazards currently inside the existing 30-yard
  hazard-entry gate. Far projected residents no longer freeze the ramp; if one closes during the
  approach, the same traced hold still activates before the 20-yard safety floor.
- Rank-1 Prowl and basic melee remain disabled: current evidence makes both worse than timed
  Travel Form traversal at this pinch.
- Request `xreq_9e8b2946-9085-49c6-8ad1-14b8d2a7ee5e` reached node 9 at full health,
  activated three terrain holds, released twice near 29 yards, then remained blocked at 23.1 yards.
  The next candidate uses the existing 20-yard safety floor and suppresses lateral detours for the
  far resident on this only traversable ramp edge.

## v150 - hold resident hazards on narrow ramps (2026-08-09)

- Version UUID: `a2d455f5-da0b-4e61-8dd2-d0e637c3e998` (`wowborg:v150`, uploaded
  inert; not submitted). Built from source `c71e07d` against canonical vanilla-wow 0.1.209.
- At the six terrain-constrained ramp anchors only, a resident hazard projected into the target
  corridor now triggers waiting rather than the ordinary road's lateral detour. Ordinary roads,
  projected-crossing holds, combat escape, and open-road throughput are unchanged.
- The activation trace uses `traverse_hazard_hold` with reason
  `terrain_constrained_resident`; the hold releases once no tracked resident still projects into
  that target corridor.
- Request `xreq_6b180e18-2154-4427-a3ee-1e26f5cce2ba` reached node 9 at full health, then
  activated one hold for a Basilisk still 60.7 yards away and never released before the deadline.
  The policy is safe but too conservative; the next candidate limits this hold to residents inside
  the existing 30-yard hazard-entry gate.

## v149 - conservative open-road throughput (2026-08-09)

- Version UUID: `b8f24e46-e596-4f20-b154-fb8ed19166a3` (`wowborg:v149`, uploaded
  inert; not submitted). Built from source `4c5e9fc` against canonical vanilla-wow 0.1.209.
- Uses a 1.0-second translation only when no road hazard or combat is visible and the target is
  more than 20 yards away. Turns and all hazard, retreat, evasion, and precise-arrival pulses keep
  their previous cadence, avoiding v141's unsafe global 1.5-second stride.
- Each longer translation emits `traverse_road_open_stride`, so hosted traces can measure both
  activation count and realized route throughput.
- Request `xreq_e218fe41-65f7-414d-a012-066a04b1e7d4` fired 258 longer pulses, stayed at full
  health with zero combat, and reached node 9 in about 128 seconds. Generic resident-hazard detours
  then repeatedly stepped off the narrow ramp corridor after reaching its safe lip, so the next
  candidate makes that terrain seam wait rather than detour.

## v148 - tight Shimmering Flats ramp arrivals (2026-08-09)

- Version UUID: `52ad576d-0fc3-4ab4-9570-db29744840f0` (`wowborg:v148`, uploaded
  inert; not submitted). Built from source `205e9e7` against canonical vanilla-wow 0.1.209.
- Tightens only the six narrow Shimmering Flats ramp anchors from 8-yard to 3-yard arrivals.
  Detour anchors, ordinary passes, hazard behavior, and the lower-dock goal are unchanged.
- First request `xreq_36342e76-936c-4950-9f14-c6552ae08b6b` was combat-censored before the
  ramp. Full-health zero-combat repeats `xreq_dc28e85e-d277-4add-8f0c-290e4c6596cf` and
  `xreq_c82b3f22-a720-4816-944c-9c9bd5e786de` both cleared the four exact Detour anchors,
  then lost the returned frame on the second ordinary node-9 translation amid hundreds of game-host
  WebSocket detach/reattach cycles. The three-yard ramp behavior therefore remains unexercised.

## v147 - vertically aligned road milestones (2026-08-09)

- Version UUID: `9ddebbfa-f068-41be-9ea5-32648a60d8c6` (`wowborg:v147`, uploaded
  inert; not submitted). Built from source `57ed0da` against canonical vanilla-wow 0.1.209.
- Retains 60 yards of horizontal hazard-displacement slack for ordinary milestone passes but now
  requires vertical error at most 10 yards. This prevents starting elevated legs below terrain.
- Request `xreq_25bda105-0daf-4943-aa2e-e3f0c87ec9a4` enforced vertical alignment
  on all 11 ordinary pass events (maximum 8.2 yards), reached node 9 within 0.9 vertical yards, and
  emitted the first exact ramp-approach arrival. Its shared 8-yard exact radius was still too loose
  for the following narrow-slope turn.

## v146 - pinned Detour-east turn (2026-08-09)

- Version UUID: `8fe6eaee-e885-4117-bc6e-b5b10035d602` (`wowborg:v146`, uploaded
  inert; not submitted). Built from source `41ed1b2` against canonical vanilla-wow 0.1.209.
- Adds the pinned corridor's shallow `(-7129,-3767)` turn as an exact anchor before the final
  Detour-east diagonal. Cadence, hazard behavior, and refined ramp geometry are unchanged.
- First request `xreq_b3f7b4b0-d3ab-447b-a4d2-94505149ad67` was censored before
  the changed bend by unrelated early hazard displacement. Fair repeat
  `xreq_df6ba150-777d-4417-a4cd-02256116bc59` proved the new turn and final
  Detour-east anchor at full health with zero combat, but ordinary node 9 incorrectly passed 51.6
  vertical yards below its target and began the ramp below terrain.

## v145 - leg-sensitive Traverse settlement cadence (2026-08-09)

- Version UUID: `dbbc1e08-2f0a-42b8-b79f-9f1e010d72af` (`wowborg:v145`, uploaded
  inert; not submitted). Built from source `9e0c895` against canonical vanilla-wow 0.1.209.
- Yields after every pulse on exact terrain anchors and every eight pulses on ordinary roads. This
  combines v139's proven tight-bend cadence with v143's faster open-road cadence.
- Request `xreq_07f6e8d6-9bdc-44a6-8102-a18ad3a0c3b5` stayed full-health with zero
  combat and removed the action timeout, but exhausted unstick at about `(-7144,-3767)` on
  Detour-east, where direct steering turned southeast earlier than the pinned navmesh corridor.

## v144 - curved Shimmering Flats ramp approach (2026-08-09)

- Version UUID: `bb21cd9f-2573-4f1c-bfd2-ff5be57842ac` (`wowborg:v144`, uploaded
  inert; not submitted). Built from source `3e2d09c` against canonical vanilla-wow 0.1.209.
- Adds exact pinned-navmesh approach and turn anchors before the existing ramp base so discrete
  steering follows the cliff's southward curve. Cadence and hazard behavior are unchanged.
- Request `xreq_98016dca-efdf-4bbb-b394-b52d6ebb6433` stayed full-health with zero
  combat, but was infrastructure-censored before the new ramp anchors by another 30-second action
  timeout at about `(-7155,-3769)` on the exact Detour-east leg.

## v143 - periodic Traverse settlement yield (2026-08-09)

- Version UUID: `0f9033bc-0247-4843-9b77-2af1292a43f8` (`wowborg:v143`, uploaded
  inert; not submitted). Built from source `c40a81b` against canonical vanilla-wow 0.1.209.
- Keeps the safe 0.75-second stride and yields for 0.25 seconds every eight settled pulses. This
  retains roughly 97% movement duty while restoring a periodic host settlement seam.
- Request `xreq_79ff2e95-2930-444c-8026-3c30c5066a75` executed 165 scheduled
  yields without v142's repeated host timeout, stayed full-health/zero-combat through Tanaris, and
  reached road node 9 in 164 seconds. Its first coarse ramp anchor still allowed a cliff fall.

## v142 - continuous settled Traverse cadence (2026-08-09)

- Version UUID: `663ecd3e-10eb-4ba4-9a73-0cf33d43a33c` (`wowborg:v142`, uploaded
  inert; not submitted). Built from source `c126d76` against canonical vanilla-wow 0.1.209.
- Restores the proven 0.75-second stride and removes the redundant 0.25-second wait after each
  synchronous action has already returned its settled next frame. Geometry and hazard gates are
  unchanged.
- Requests `xreq_5a105daa-13a3-4304-be2b-515587f6da89` and
  `xreq_c60c6458-3659-4a37-a8ef-63b35a372b60` both stayed full-health with zero
  combat and reached the exact Detour bend quickly, but each hit an isolated 30-second host action
  timeout after roughly 950 uninterrupted actions. A periodic settlement yield is still required.

## v141 - doubled open Traverse stride (2026-08-09)

- Version UUID: `53afe44e-b6aa-4880-9111-eeffe620e64f` (`wowborg:v141`, uploaded
  inert; not submitted). Built from source `1c051b2` against canonical vanilla-wow 0.1.209.
- Doubles open translation to 1.5 seconds while retaining 0.25-second turns, retreat/evasion, and
  final-20-yard precision. The route and 30-yard immediate hazard gate are unchanged.
- Request `xreq_8ab6b8b3-5215-4506-8817-864538ef59a8` reached road node 7 six
  seconds faster than v139, but closed on a Glasshide Basilisk to 2.7 yards and died before node 8.
  The longer stride is unsafe and its speed gain is small.

## v140 - exact Shimmering Flats ramp corridor (2026-08-09)

- Version UUID: `191f1a51-9c67-46a1-8e5e-dc4d28efb9a3` (`wowborg:v140`, uploaded
  inert; not submitted). Built from source `3ef7543` against canonical vanilla-wow 0.1.209.
- Adds the pinned navmesh's three real south-ramp bends as exact route anchors, preventing direct
  steering from falling off the escarpment. Tanaris hazard behavior is unchanged from v139.
- Request `xreq_7ce2cbdf-f84f-4bc4-ae06-5d6be2189fdd` remained alive and reached
  road node 9, but a dense hazard draw consumed 238 seconds and left only 29 seconds for the first
  ramp anchor. It had one brief contact and lost 56 health; the ramp geometry was not falsified.

## v139 - crossing-only patrol hold (2026-08-09)

- Version UUID: `e97ab7d9-2c61-4f95-a334-3c3bf8eb78da` (`wowborg:v139`, uploaded
  inert; not submitted). Built from source `bb9871f` against canonical vanilla-wow 0.1.209.
- Holds only when an isolated moving patrol's projected trajectory crosses wowborg. Immediate and
  guidepoint-resident blockers still use local avoidance, and the hold releases as soon as the
  crossing trajectory clears.
- Request `xreq_2d456355-d5b9-4d8c-936c-d239a369b07d` stayed full-health with zero
  combat, reached all three exact Detour anchors and road node 9 in about 2.5 minutes, then failed
  direct steering toward the Shimmering Flats south-ramp endpoint.

## v138 - persistent safe crossing hold (2026-08-09)

- Version UUID: `cec936af-e9e3-4141-afaa-d693d0a4ccc4` (`wowborg:v138`, uploaded
  inert; not submitted). Built from source `2d61417` against canonical vanilla-wow 0.1.209.
- Retains safely crossing patrol GUIDs while they remain within 70 yards or intersect the active
  lookahead. Holding never moves; a path projected within 20 yards of the holding point or a
  guidepoint-resident destination still escalates to local avoidance.
- Request `xreq_d1cd8097-6b68-4ba5-9e28-7c6c945374fe` stayed full-health with zero
  combat, but spent 6,339 pulses holding and reached only road node 3. The no-hazard branch was
  holding for every moving hostile in lookahead, not only patrols projected to cross wowborg.

## v137 - hazard-tolerant road milestone pass (2026-08-09)

- Version UUID: `de9133dc-8ede-416d-98db-e2713ae88a6d` (`wowborg:v137`, uploaded
  inert; not submitted). Built from source `b7bdcd1` against canonical vanilla-wow 0.1.209.
- Permits ordinary road guidepoints to complete up to 20 yards before their target x when still
  inside the existing 60-yard lateral/z corridor. Exact Detour bend anchors and the Great Lift
  dock retain their 8-yard completion requirement.
- Request `xreq_3c31de07-6a4e-40a6-87f0-c46126c03bbe` emitted eight ordinary
  pass events through node 6, proving the completion change, but died to two Tail Lasher contacts
  before node 7. Detour recon found no connected broad north or south bypass around this pass; the
  crossing-patrol decision still flickered off before the threat had cleared.

## v136 - guidepoint-resident patrol routing (2026-08-09)

- Version UUID: `e604b7aa-fc13-4871-a7b5-bc1a084afb48` (`wowborg:v136`, uploaded
  inert; not submitted). Built from source `ab358ec` against canonical vanilla-wow 0.1.209.
- Holds on the road for true moving cross-traffic, but classifies a patrol whose movement
  destination lies within 30 yards of the active guidepoint as a resident blocker and applies the
  local 20-yard avoidance planner immediately. This replaces v135's unsafe time escalation.
- Request `xreq_80a314cf-f183-43c1-bb7f-e818e708651e` was infrastructure-censored
  by a 30-second action-settlement timeout at node 3 while full-health. Fair repeat
  `xreq_50cabc51-a8db-4a56-88b3-dba3884b0bd2` survived and recovered from one Tail
  Lasher contact, but timed out at node 7 only about 14 yards from its center and just 5 yards short
  of its exact northing threshold. It had effectively reached the milestone but could not advance.

## v135 - bounded per-patrol hold (2026-08-09)

- Version UUID: `cef2e31f-773e-4045-b341-13cb6d3a7b59` (`wowborg:v135`, uploaded
  inert; not submitted). Built from source `b03cabd` against canonical vanilla-wow 0.1.209.
- Caps predictive holding at two wall seconds per patrol GUID. A patrol still projecting across
  the route then becomes a local 20-yard avoidance blocker until it leaves the 80-yard tracked
  set; brief lookahead jitter cannot restart its waiting allowance.
- Request `xreq_cbb87d77-a2ed-48bb-a30e-205105a13733` escalated the first safe
  Scorpid crossing, cascaded into a Glasshide Petrifier contact, and died at node 1 after only 96
  net northing yards. The timer conflated transient crossings with resident blockers.

## v134 - hold for safely crossing patrols (2026-08-09)

- Version UUID: `2354e2a4-a82c-4e25-a719-375e16dfc6c1` (`wowborg:v134`, uploaded
  inert; not submitted). Built from source `11421a5` against canonical vanilla-wow 0.1.209.
- Restores v128's road-preserving 20-yard local sidestep and 30/40-yard avoidance hysteresis.
  A separate 60-yard predictor waits on the road for a moving patrol whose projected path stays
  at least 20 yards from the holding point; immediate blockers and unsafe crossings still detour.
- Request `xreq_f89a11e1-5c2f-4a1e-8518-1dfcc980adb3` stayed full-health with zero
  combat and reached nine guidepoints, but spent 3,129 pulses holding and timed out at road node 7
  after 1,605 net northing yards. A Roc repeatedly projected across the next guidepoint, showing
  that an unbounded wait cannot clear a resident patrol.

## v133 - frozen hazard-bypass waypoint (2026-08-09)

- Version UUID: `f9fb6c08-632e-46e5-b20f-76278b79371a` (`wowborg:v133`, uploaded
  inert; not submitted). Built from source `f371bd1` against canonical vanilla-wow 0.1.209.
- Converts reactive 20-yard avoidance into a frozen 140-yard-ahead lateral waypoint. The waypoint
  is released on arrival and replanned only when a genuinely new patrol intersects the active
  path, preventing the v132 target orbit while preserving early predictive clearance sampling.
- Request `xreq_9a451cfa-f39f-41e5-ada4-d2573837a55b` replanned 23 times as new
  patrol GUIDs entered the displaced path, left the owner road for the surrounding spawn field,
  and died to a Glasshide Petrifier after only 142 net northing yards. The fixed endpoint was
  therefore too large a spatial reaction for Tanaris's mob density.

## v132 - persistent crossing-patrol ownership (2026-08-09)

- Version UUID: `1ccd4562-dba9-458e-ac61-53e0afadb02f` (`wowborg:v132`, uploaded
  inert; not submitted). Built from source `751998a` against canonical vanilla-wow 0.1.209.
- Retains every hostile that triggered the current bypass by GUID until it is physically beyond
  the 70-yard exit radius. Newly intersecting patrols join the active set; hostiles that disappear
  beyond the 80-yard visible envelope clear naturally. This prevents the bypass line itself from
  making wowborg forget a still-nearby patrol and cut back toward it.
- Request `xreq_27e8af9f-97b7-44dd-a7eb-285a398ce527` stayed full-health and
  contact-free, and reduced avoidance lifecycle churn to three starts and two ends. But its
  continuously recomputed target orbited the retained patrols: 79 side switches, 142 retreats,
  only 150 net northing, and a timeout at road node 1.

## v131 - 60-yard crossing-patrol lookahead (2026-08-09)

- Version UUID: `e663e114-f50f-4246-b054-74e2e642474a` (`wowborg:v131`, uploaded
  inert; not submitted). Built from source `811a92e` against canonical vanilla-wow 0.1.209.
- Expands predictive corridor entry/exit from 30/40 to 60/70 yards within the unchanged 80-yard
  tracked-unit set. This targets v130's measured crossing patrol while preserving ten yards of
  observation margin and side hysteresis; route geometry and clearance floor are unchanged.
- Request `xreq_cc157cd3-3f7a-469b-b954-55962bc1c8c9` survived but activated 55
  avoidances and ended 54, walked 5,942 trajectory yards for 1,842 northing, contacted three mobs,
  and timed out at node 8. A bypass changed the line back to the guidepoint, causing its triggering
  patrol to drop from the corridor test while still nearby; wowborg then cut back toward it.

## v130 - Detour-derived Tanaris terrain bend (2026-08-09)

- Version UUID: `c40c37d1-0396-4307-b850-bac8714e1d67` (`wowborg:v130`, uploaded
  inert; not submitted). Built from source `187b820` against canonical vanilla-wow 0.1.209.
- Inserts three exact node-8-to-9 corridor anchors derived from the deployed Detour navmesh. Exact
  completion permits the brief x-backtracking needed to regain the walkable bend after hazard
  displacement; the bounded v129 unstick remains as a generic last resort.
- Request `xreq_786d0482-defb-41da-970c-da0a8858156d` died near road node 2 before
  reaching the new anchors. The fatal Scorpid was tracked at 63.2 yards but lay beyond the old
  30-yard corridor horizon; when avoidance finally activated at 27.8 yards, candidate clearance
  had already collapsed, reaching 0–2.7 yards before contact.

## v129 - bounded ordinary-road unstick (2026-08-09)

- Version UUID: `e27cf658-ddef-4d2d-93fe-89b31c4b04dd` (`wowborg:v129`, uploaded
  inert; not submitted). Built from source `29f415a` against canonical vanilla-wow 0.1.209.
- When the existing eight-second route watchdog fires, tries one forward-diagonal pulse on each
  side and traces measured displacement. Target progress resets only after physical movement; two
  blocked attempts retain the existing no-progress termination.
- Corrected Traverse request `xreq_37c9ae98-da0f-424c-8176-6025218f4528` showed the
  first right pulse moved 0.781 yards, but the character rewedged; the next two pulses moved only
  0.323 and 0.463 yards before bounded exhaustion. It survived, but finished at 2,011.7 northing
  yards after one Scorpid and one Basilisk contact. Deployed Detour recon showed the coarse node
  8-to-9 chord omits a required three-anchor terrain bend.

## v128 - calibrated 20-yard clearance floor (2026-08-09)

- Version UUID: `40be968c-6891-4dc2-8d9d-6c18cdbc3811` (`wowborg:v128`, uploaded
  inert; not submitted). Built from source `cd61076` against canonical vanilla-wow 0.1.209.
- Lowers the adaptive router's clearance floor from 25 to 20 yards. This remains above v124's
  fatal 18.6-yard candidate while reducing v127's conservative evasion and retreat cost.
- Request `xreq_b8263b3b-87fe-4fa6-a0c4-9539f2ac875a` stayed full-health with no
  combat or timeout, while reducing avoidance churn roughly in half and reaching 2,027.5 reported
  northing yards. It then wedged on ordinary forward translation at Tanaris road node 9, 222 yards
  from the guidepoint; the general progress watchdog terminated after accepted inputs produced no
  displacement.

## v127 - bounded intermediate-guidepoint pass (2026-08-09)

- Version UUID: `010103bc-3838-4a7e-89a0-975beeb09c9b` (`wowborg:v127`, uploaded
  inert; not submitted). Built from source `87adcda` against canonical vanilla-wow 0.1.209.
- An intermediate road guidepoint is complete after wowborg crosses its northing within 60 lateral
  yards. The Great Lift lower dock retains exact eight-yard arrival, and pass activations trace.
- Request `xreq_dc68b02d-a892-4d7b-b73a-728569f395be` stayed full-health and improved
  to 11 guidepoints / 1,869.8 reported northing, but still used 92 evasions and 66 blocked retreats.

## v126 - blocked retreat-anchor escape (2026-08-09)

- Version UUID: `149ff0eb-750d-4efa-b524-7b7d7302c697` (`wowborg:v126`, uploaded
  inert; not submitted). Built from source `a5d18e3` against canonical vanilla-wow 0.1.209.
- After three retreat pulses move less than 0.5 yards, traces the blocked safe anchor and hands
  control to the existing mobile hazard-evasion path. Adaptive widths and clearance remain v125's.
- Request `xreq_2794b3ad-a849-4a1f-a733-e4659298a305` stayed full-health, cleared nine
  guidepoints, and reached 1,318.5 yards. It then orbited node 7 despite already passing its
  northing by 23 yards within 32 lateral yards.

## v125 - adaptive hazard bypass width (2026-08-09)

- Version UUID: `87739aaf-702e-47fb-971e-acd5c43a4fb7` (`wowborg:v125`, uploaded
  inert; not submitted). Built from source `c491039` against canonical vanilla-wow 0.1.209.
- Requires 25 yards of projected route clearance and selects the shortest safe 30/45/60-yard
  lateral bypass, or the highest-clearance candidate if none are safe. Activation and side-switch
  traces expose both the chosen clearance and lateral width for each side.
- Request `xreq_63741569-df7c-4a98-aae3-e374cf35f365` stayed full-health and selected
  all widths, but a blocked safe anchor caused 721 accepted retreat translations with no movement.

## v124 - discrete eight-direction road steering (2026-08-09)

- Version UUID: `5da21603-0777-48b7-b131-de9420d24ef6` (`wowborg:v124`, uploaded
  inert; not submitted). Built from source `da3459d` against canonical vanilla-wow 0.1.209.
- Accepts the proven 45-degree turn quantum for ordinary steering and adds signed strafe beyond
  22.5 degrees, translating along the nearest discrete 45-degree heading. Hazard geometry and
  state are unchanged.
- Request `xreq_1686e46f-4062-43d6-b495-7db0ebd3e82e` proved the actuator by clearing
  two road nodes without a turn loop or timeout. A 30-yard bypass then accepted 18.6 yards of
  clearance under the old 15-yard floor; a moving Glasshide Gazer closed to 16.5 yards and killed
  wowborg.

## v123 - quantized road heading correction (2026-08-09)

- Version UUID: `ec6fe6c8-f7c4-4847-a242-a7aec0d6d8fc` (`wowborg:v123`, uploaded
  inert; not submitted). Built from source `3af9760` against canonical vanilla-wow 0.1.209.
- Uses an exact 0.25-second turn-in-place action for ordinary heading correction, retaining the
  existing 0.75-second pulse for straight road translation. This targets v122's alternating
  left/right road-node stall without changing hazard geometry or state.
- Request `xreq_46147008-1cf6-43d2-8f2f-37906b15240d` stayed full-health with no
  combat or action timeout, but quarter turns alternated in place under the old 0.20-radian
  ordinary deadband and failed at road node 1.

## v122 - mobile unsafe-anchor holding (2026-08-09)

- Version UUID: `da731748-bd0b-47c6-8b41-8893ba8cb59f` (`wowborg:v122`, uploaded
  inert; not submitted). Built from source `475f58b` against canonical vanilla-wow 0.1.209.
- At an unsafe safe-anchor, uses quantized eight-direction movement away from the active corridor
  hazards until a safe candidate reopens instead of waiting in place.
- Request `xreq_5beaa43e-290d-47b3-a3bf-7e5ef8a0a282` completed three mobile evasions
  with no action timeout, survived at full health, and reached 605.5 living northing yards. It
  then alternated 0.75-second ordinary left/right turns at road node 3 until no-progress.

## v121 - quantized persistent retreat (2026-08-09)

- Version UUID: `377a2f3e-215e-4425-8f98-06d540db6c47` (`wowborg:v121`, uploaded
  inert; not submitted). Built from source `8b0a2e2` against canonical vanilla-wow 0.1.209.
- Keeps v120's persistent safe-anchor state and uses exact 0.25-second actions for every precise
  turn and translation. Hazard geometry and combat behavior are unchanged.
- Request `xreq_7063f045-2013-4368-a884-1893ca923ad7` had zero action timeouts and
  completed 13 retreats, but reached only three guidepoints. At the final anchor it waited while a
  moving Glasshide Gazer closed from 17.5 to 15.3 yards and acquired wowborg; escape then tripped
  the route-progress watchdog. The next candidate replaces stationary unsafe-anchor waiting with
  quantized movement away from the active corridor hazards until a safe bypass reopens.

## v120 - persistent safe-anchor retreat (2026-08-09)

- Version UUID: `851c62e2-2a32-4e8d-8501-18067e495a30` (`wowborg:v120`, uploaded
  inert; not submitted). Built from source `0e2a8fb` against canonical vanilla-wow 0.1.209.
- Once retreat starts, it now persists to the frozen safe anchor even if moving patrols briefly
  restore candidate clearance. Geometry, actuator control, and combat behavior are unchanged.
- Request `xreq_4bef2465-c2bc-4933-868d-dd048e53a561` reduced churn to seven retreats
  and four switches, but persistent retreat exercised a distance-derived 0.5629-second diagonal
  translation that timed out at frame 559. It reached three guidepoints and had one escaped pull.
  The next candidate uses the proven exact 0.25-second quantum for every precise translation;
  turn behavior, state semantics, and geometry are unchanged.

## v119 - diagonal retreat wrapper support (2026-08-09)

- Version UUID: `635748f7-56bd-4295-abed-59ddf4e82f98` (`wowborg:v119`, uploaded
  inert; not submitted). Built from source `90b0f91`; adds the missing strafe pass-through to
  v118's unchanged diagonal precise-retreat strategy.
- Request `xreq_bee76128-17b5-4bcc-adb5-899a08111294` stayed full-health and out of
  combat, reached nine guidepoints / 1,320.1 living northing yards, and mechanically completed
  every retreat. It was inefficient: 140 retreats and 139 side switches consumed the episode at
  road node 7. Retreats ended whenever projected clearance briefly recovered, even while wowborg
  remained 20–45 yards from its frozen safe anchor, then restarted on the next unsafe frame. The
  next candidate keeps retreating until it actually reaches that anchor.

## v118 - diagonal precise retreat (2026-08-09)

- Version UUID: `2e5125da-9fa8-43b7-a8e4-73808d86f8ef` (`wowborg:v118`, uploaded
  inert; not submitted). Built from source `2982c92` against canonical vanilla-wow 0.1.209.
- Adds signed strafe only to precise safe-anchor translation when residual heading exceeds
  22.5 degrees, selecting the closer 45-degree movement direction. Turn duration, ordinary route
  steering, hazard geometry, and escape-only combat are unchanged.
- Request `xreq_e4e7e0ca-8a69-4b96-b84e-c115ef09896b` stayed alive and out of combat,
  but failed after one guidepoint because wowborg's local `select_move_vector` convenience method
  did not expose the upstream action contract's existing `strafe` field. The active source adds
  that missing pass-through; the diagonal strategy itself is unchanged.

## v117 - quantized precise turns (2026-08-09)

- Version UUID: `6e2b8986-7233-4eca-9412-fcb2f03353ae` (`wowborg:v117`, uploaded
  inert; not submitted). Built from source `13604c1` against canonical vanilla-wow 0.1.209.
- Keeps precise turn-only actions at the empirically reliable 0.25-second quantum and accepts a
  heading within that quantum's 45-degree arc before moving toward the safe anchor. Ordinary route
  steering, hazard geometry, and escape-only combat are unchanged.
- Request `xreq_199cfdb3-6a1c-4918-a5ca-adb51b145caf` proved all turn actions settle and
  six retreats end, but the 45-degree acceptance cone was too coarse. On the fatal retreat it
  accepted a 39-degree residual heading, moved forward on the wrong diagonal, passed a Glasshide
  Gazer at 3.68 yards, and died after three guidepoints. The next candidate uses the contract's
  left/right strafe axis when residual error exceeds 22.5 degrees, reducing precise translation
  error to at most 22.5 degrees without changing turn duration.

## v116 - angular-error precise turns (2026-08-09)

- Version UUID: `b5ccf41d-92bd-499d-90cc-a6289c987f1a` (`wowborg:v116`, uploaded
  inert; not submitted). Built from source `217902a` against canonical vanilla-wow 0.1.209.
- Changes only precise safe-anchor turning: duration is remaining angular error divided by the
  documented pi-radian/second turn rate, capped at 0.25 seconds. This removes v115's 45-degree
  sign-flip loop without changing ordinary route steering, hazard geometry, or combat behavior.
- Request `xreq_21621766-8175-471c-91f9-2b748bfd7c5f` did not alternate turn signs, but
  failed at frame 102 when its first non-quarter-second turn (`0.2188` seconds) timed out without
  advancing an observation. It cleared one guidepoint and remained alive with no combat. Owner
  source confirms held axis magnitude is sign-only, so the next candidate retains the reliable
  0.25-second turn quantum and widens only precise arrival's acceptance cone to the matching
  45 degrees.

## v115 - precise safe-anchor arrival (2026-08-09)

- Version UUID: `1035e292-5f91-4e18-9398-89161c4bc14a` (`wowborg:v115`, uploaded
  inert; not submitted). Built from source `35d9050` against canonical vanilla-wow 0.1.209.
- Returns combat to v112's escape-only baseline. When retreating to a recorded safe anchor,
  wowborg now turns in place and then bounds forward-input duration by remaining distance and
  observed movement speed. Ordinary road, avoidance, escape, and lift steering are unchanged.
- Request `xreq_c8dbfd00-8211-4e47-88a7-9e6025b588ca` avoided every pull and death,
  but cleared only nine guidepoints before the episode timeout. At the final retreat, fixed
  0.25-second turn-only pulses alternated direction without moving for 106 seconds: each pulse
  turns about 45 degrees at the documented pi-radian/second rate, overshooting the 0.20-radian
  arrival deadband. The next candidate scales only precise-turn duration to the remaining angular
  error; ordinary steering and all hazard geometry remain unchanged.

## v114 - corrected package entrypoint (2026-08-09)

- Version UUID: `830a0fa0-7d92-416f-8c8a-0eabc9f1015e` (`wowborg:v114`, uploaded
  inert; not submitted). Reuses v113's exact `1e8ca0b` image and vanilla-wow 0.1.209 contract.
- Changes only the uploaded argv from inert `python -m wowborg.main` to the package entrypoint
  `python -m wowborg`, whose `__main__.py` invokes `main()`. Combat and routing code are identical
  to v113.
- Request `xreq_a4c0fd12-fcf6-49b4-8dc6-fb46bb57b302` proved the fight gate activates
  and exact melee starts, but falsified the current-strength premise. Against one level-48 Rabid
  Blisterpaw, basic melee dealt 413 while wowborg lost 570 health in 1.7 seconds. Falling below
  the 80% entry threshold switched to escape and the character died after six guidepoints. The
  pull began after the safe-anchor retreat orbited a point only 6.4 yards away because it reused
  fixed 0.75-second forward-turn pulses. The next candidate returns combat to v112's escape-only
  baseline and changes only retreat arrival: turn in place, then use a distance-bounded pulse.

## v113 - calibrated single-pull combat (2026-08-08)

- Version UUID: `ad98cbe0-d091-4f2b-8f73-3de152516a3a` (`wowborg:v113`, uploaded
  inert; not submitted). Built from source `1e8ca0b` against canonical vanilla-wow 0.1.209.
- Fights exactly one visible, known non-elite attacker when wowborg is at least ten levels higher
  and has at least 80% health. It closes to melee and reuses the v73-proven exact-target engagement
  owner. Multiple, elite, unknown-strength, near-level, and low-health pulls retain direct escape.
  Fight/escape transitions trace the decision inputs, duration, health, and realized damage.
- Requests `xreq_bf8f91db-64b1-470e-9b7a-6330125d4678` and
  `xreq_60b18656-b3c5-4f4a-a829-c59e89524f77` both failed before connection with empty
  policy logs. The upload used `python -m wowborg.main`; that module defines `main()` but does not
  invoke it, so the container exited without connecting. These runs contain no gameplay evidence.
  V114 reuses the exact image with the correct `python -m wowborg` package entrypoint.

## v112 - stable per-encounter safe anchor (2026-08-08)

- Version UUID: `9b8831af-2095-4505-98a5-ddf1e814fe54` (`wowborg:v112`, uploaded
  inert; not submitted). Built from source `a20766f` against canonical vanilla-wow 0.1.209.
- Keeps the safe holding point fixed while any projected corridor hazard remains active, updating
  it only after avoidance ends. All projection, clearance, and steering knobs are unchanged.
- Request `xreq_f8931af8-bc85-4073-85da-021d50524465` completed cleanly with score
  1,996.05, cleared 11 guidepoints, and reached 1,869.4 living northing yards. A single Glasshide
  Basilisk then aggroed at road node 8. Escape moved 146 yards away from the route target while
  health fell from 2,693 to 595; the route watchdog aborted after eight seconds of no targetward
  progress. The next candidate fights one known non-elite attacker only with a ten-level advantage
  and at least 80% health, reusing the v73-proven exact-attacker melee owner. Multiple, elite,
  unknown-strength, near-level, and low-health cases keep the existing escape behavior.

## v111 - two-yard safe-holding arrival (2026-08-08)

- Version UUID: `3202f1c4-8a65-4f9b-b05a-f41523e11f3c` (`wowborg:v111`, uploaded
  inert; not submitted). Built from source `3fd1b9c` against canonical vanilla-wow 0.1.209.
- Changes only safe-holding arrival from the eight-yard road-guidepoint radius to a dedicated
  two-yard radius, allowing the retreat added in v110 to activate.
- Request `xreq_24ae35ee-7dac-4035-9f65-8792bd5d4f89` produced repeated retreat
  activations, but every temporarily safe pulse overwrote the anchor inside the same encounter.
  Retreats therefore collapsed into 6–7-yard oscillations until a Scorpid pulled. The next
  candidate updates the safe point only after the projected hazard corridor fully clears.

## v110 - retreat to a safe holding point (2026-08-08)

- Version UUID: `e33c39e7-3653-4e45-957f-bad88258b67b` (`wowborg:v110`, uploaded
  inert; not submitted). Built from source `e95156e` against canonical vanilla-wow 0.1.209.
- Records the latest position with a safe local hazard edge. When both bypasses fall below the
  15-yard floor, wowborg retreats to that point before waiting; retreat start/end are traced.
  Request `xreq_da39a3f7-4160-4291-b288-753be45a9b48` showed no retreat activations:
  the last-safe point was commonly one seven-yard pulse behind, but v110 reused the eight-yard
  route-arrival radius and misclassified it as already reached. The next candidate uses a
  dedicated two-yard holding-point radius.

## v109 - wait for a safe patrol edge (2026-08-08)

- Version UUID: `6ada5206-cb39-4c3f-8b8b-db9b93fd86d6` (`wowborg:v109`, uploaded
  inert; not submitted). Built from source `dc8fe3d` against canonical vanilla-wow 0.1.209.
- When the retained avoidance side remains below the existing 15-yard clearance floor, wowborg
  waits for the moving patrol instead of entering a known-unsafe edge. Wait start/end are traced,
  and intentional waiting refreshes the road-stall budget.
- Request `xreq_b05d3806-0a9b-4ef7-b9e2-02dbf97ae61c` activated and released one
  wait, then waited again at 14.5 yards from a Glasshide Petrifier. The patrol crossed the
  stationary character, pulled at close range, and backed out to its 29.5-yard casting distance.
  The next candidate retreats to the last safe observation before waiting there.

## v108 - cross-guidepoint hazard continuity (2026-08-08)

- Version UUID: `c2896a36-05a4-4a0c-ba88-83d8ae57c48c` (`wowborg:v108`, uploaded
  inert; not submitted). Built from source `8376f77` against canonical vanilla-wow 0.1.209.
- Preserves v107's live avoidance side across road-guidepoint arrivals instead of restarting the
  edge evaluator at each leg. Geometry, tracking horizon, clearance threshold, and steering are
  unchanged.
- Request `xreq_b64d45bd-4169-470d-bd03-634192fe700f` proved continuity across road
  node 7 and reached 1,784.9 living northing yards. It later chose a route with only 11.9 yards
  of best predicted clearance through two Glasshide Basilisks and pulled at 5.6 yards. The next
  candidate waits when neither side meets the existing 15-yard floor, then resumes when the
  moving patrol opens a safe edge.

## v107 - moving-hostile path projection (2026-08-08)

- Version UUID: `d7f5fe7d-3d99-4924-88a1-e78865dcc3fd` (`wowborg:v107`, uploaded
  inert; not submitted). Built from source `d33799e` against canonical vanilla-wow 0.1.209.
- Tracks visible hostiles out to 80 yards, tests their advertised movement segments against the
  forward corridor and both candidate player segments, and retains a chosen side unless its
  predicted clearance falls below 15 yards. Activation traces now record both side clearances
  and every tracked hostile destination.
- Request `xreq_3a8dc2f1-fdae-4bb5-81a8-1936f01ae2d2` cleared the earlier Scorpid
  cluster and reached 10 guidepoints / 1,684.8 living northing yards. It then discarded an active
  right-side avoidance at road node 7 and restarted it on node 8 only when the same Starving
  Blisterpaw was 10.3 yards away; both candidate clearances were already unsafe. The next source
  candidate preserves the avoidance side across guidepoint boundaries.

## v106 - live 0.1.209 observation contract (2026-08-08)

- Version UUID: `ec727f01-fbe8-45e9-b1c7-b129c3d2c54a` (`wowborg:v106`, uploaded
  inert; not submitted). Rebuilds v105's unchanged corridor-filtered router against canonical
  `vanilla-wow:0.1.209` image
  `sha256:2c06427e2a96ab96f3ba19fedb6049c2eab30e463c167e27fb6781c415f25dfa`.
- This compatibility-only version accepts the live `Unit.sub_name` and quest-reward observation
  fields.
- Request `xreq_7d385999-abc3-4231-8b78-c5bb21a2bc2f` proved the contract and route
  work through road node 4, but falsified endpoint-only clearance. Avoiding a Rabid Blisterpaw
  drove south while an unselected Scorpid Dunestalker entered at 3.2 yards; repeated side switches
  also showed unstable scoring around moving packs. The next candidate scores the player's path
  against hostile movement segments over an 80-yard tracking horizon and switches only when the
  retained side falls below 15 yards of clearance.

## v105 - corridor-filtered cluster clearance (2026-08-08)

- Version UUID: `af1d041f-61d2-45a5-bb44-6051762f2934` (`wowborg:v105`, uploaded
  inert; not submitted). Built from source `d763b81` with the published 0.1.188 contract.
- Refines v104 without changing the road: avoidance activates only for an 18-yard forward
  corridor intersection, side clearance includes every hostile within the 30/40-yard envelope,
  and switching requires five yards of benefit. Actual combat uses a direct attacker-radial flee
  target. Side switches emit `traverse_hazard_avoidance_switched`.
- Request `xreq_9e058bae-fea0-4824-9045-13333b28a992` ran after the canonical game
  advanced to 0.1.209 and failed before movement: v105's 0.1.208 policy contract rejected the
  newly added `Unit.sub_name` and four quest-reward fields. V106 is the same router rebuilt
  against the new immutable game image, so its next request restores attribution.

## v104 - pre-aggro live-hostile steering (2026-08-08)

- Version UUID: `6472b8dc-0499-4a05-b28d-070c029b950d` (`wowborg:v104`, uploaded
  inert; not submitted). Built from source `1d44515` with the published 0.1.188 contract.
- Keeps the measured road and combat escape, then adds the first live hazard overlay. A hostile
  within 30 yards ahead creates two local side candidates; wowborg bends bounded steering toward
  the one with greater clearance and holds that side until 40 yards clear. Activation and exit
  emit `traverse_hazard_avoidance` and `traverse_hazard_avoidance_ended`.
- Request `xreq_f77ed886-9df8-4b54-98ff-7a88222840ff` activated avoidance nine times,
  proving that live units arrive early enough to plan around. It still died because any nearby
  unit triggered a turn while only that unit influenced side choice; avoiding a Rabid Blisterpaw
  exposed a Glasshide Gazer, and the stale side persisted. The next candidate triggers only on an
  18-yard forward-corridor intersection, scores both sides against every nearby hostile, switches
  sides only for a five-yard clearance gain, and flees directly away after an actual pull.

## v103 - run-through escape on incidental combat (2026-08-08)

- Version UUID: `a7b0bc17-80b6-4e7c-b909-dbefe9486428` (`wowborg:v103`, uploaded
  inert; not submitted). Built from source `928cb29` with the published 0.1.188 contract.
- Keeps v102's measured route unchanged. A road leg now continues its bounded steering while in
  combat rather than declaring route failure and disconnecting. It emits
  `traverse_combat_escape` with health and visible attacker evidence on activation, then
  `traverse_combat_escape_ended` after leashing the pull.
- Request `xreq_46900459-a4be-465a-8a34-d54006fa5746` proved the escape activates and
  continues moving, but a seed-dependent Glasshide Gazer pulled earlier at 7.9 yards and dealt
  lethal damage while following wowborg for roughly 100 route yards. Post-pull escape is too
  late. The next candidate uses visible hostile locations before aggro to bend steering pulses
  toward the higher-clearance side of the road, with 30/40-yard hysteresis and activation traces.

## v102 - measured channel between Brute and Gazer (2026-08-08)

- Version UUID: `775f286c-aa9d-4834-86e1-75730cfb3762` (`wowborg:v102`, uploaded
  inert; not submitted). Built from source `48db44c` with the published 0.1.188 contract.
- Replaces v101's premature northern turn with two measured gates: v100's already-traversed
  center-road point `(-8401.8,-3220.7)` south of the Brute, then `(-8300,-3220,17.4)` north of
  the Gazer. This keeps 42 and 57 yards of observed positional clearance, respectively, before
  reconnecting to road node 4.
- Request `xreq_f0744efc-7573-4b44-b978-0934c83cc599` cleared both hazards at full
  health and reached road node 5, then took one 62-damage hit at `(-7989.2,-3488.8)`. The route
  policy stopped and disconnected solely because `in_combat` was true, despite retaining 97.7%
  health. The next candidate keeps steering along the route during incidental combat and traces
  both escape activation and combat exit instead of freezing to death.

## v101 - first live Gazer bypass (2026-08-08)

- Version UUID: `22efcbf3-9091-4299-8023-c848981f0362` (`wowborg:v101`, uploaded
  inert; not submitted). Built from source `5c56fff` with the published 0.1.188 contract.
- Adds only `tanaris-gazer-bypass-north` at `(-8350,-3180,14.1)` between canonical road nodes
  3 and 4. The pinned navmesh connects both legs, and the waypoint shifts the local corridor more
  than 40 yards north of v100's observed Glasshide Gazer patrol.
- Request `xreq_18d73da8-12b7-4a42-a8f2-83224fb9367e` falsified that fixed
  bypass: it crossed the 4.1-yard aggro radius of a Dunemaul Brute at
  `(-8396.0,-3178.9)`, which dealt 2,825 damage over 83.8 seconds and killed wowborg at
  `(-8395.8,-3175.2)`. The next candidate stays on v100's proven center-road trajectory until
  south of the Brute, then crosses east between it and the Gazer.

## v100 - continuous road steering exposes the first live hazard (2026-08-08)

- Version UUID: `a3249a32-7436-4165-ab67-3359a716d279` (`wowborg:v100`, uploaded
  inert; not submitted). Built from source `9266477` with the published 0.1.188 contract.
- Request `xreq_0d41a1ff-baf6-4f0c-9aa7-fce4681903f7` proved the movement
  mechanism: fixed 0.75-second steering pulses advanced through frame 400 with no host stalls,
  environmental damage, or movement failures. Wowborg reached four guidepoints and gained
  872.08 living northing yards before entering combat at `(-8314.9,-3269.0)`.
- Replay inspection identifies one Glasshide Gazer (entry 5420) at roughly
  `(-8331.1,-3277.4)`. It dealt 2,808 damage over 108.7 seconds while the stopped policy dealt
  none, killing wowborg at 630.5 seconds. The next candidate adds one real-navmesh-verified
  northern waypoint at `(-8350,-3180,14.1)`, more than 40 yards clear of the observed patrol,
  then rejoins the unchanged road at node 4.

## v99 - wait-separated vector pulses (2026-08-08)

- Version UUID: `24514f4d-25c9-4da3-bed4-e8dbb844e692` (`wowborg:v99`, uploaded
  inert; not submitted). Built from source `b227100` with the published 0.1.188 contract.
- Request `xreq_4d5365af-50cb-4f11-9aa5-02b569f992bc` completed the 0.75-second
  forward-turn and advanced a wait from frame 11 to frame 12. The following 0.431-second vector
  still timed out, disproving the vector-continuation reset hypothesis.
- Every observed 0.75-second vector has settled; every shorter vector has timed out. The next
  candidate therefore uses one fixed 0.75-second duration for all steering pulses.

## v98 - physically productive turn arcs (2026-08-08)

- Version UUID: `cda8fa1c-0c7a-41d1-b240-afdadce677f3` (`wowborg:v98`, uploaded
  inert; not submitted). Built from source `4aee96b` with the published 0.1.188 contract.
- Request `xreq_b1b28122-0177-414e-b977-72a94a70b2b7` completed the bootstrap and
  made the first forward-turn arc productive: it displaced 6.4 yards and returned frame 11.
  A second consecutive vector action then timed out on frame 11.
- The next candidate inserts one proven contract-native wait frame between steering pulses,
  breaking the vector continuation chain while keeping every actual movement pulse productive.

## v97 - post-bootstrap vector steering (2026-08-08)

- Version UUID: `864ec7ce-66ef-407a-b1ef-fe8a83588f2d` (`wowborg:v97`, uploaded
  inert; not submitted). Built from source `2b7a586` with the published 0.1.188 contract.
- Request `xreq_160ce10a-d3d4-4634-80c6-9b503d44c153` again completed the semantic
  bootstrap. Its first 0.75-second turn-only road action returned frame 11 successfully; the
  following 0.239-second turn-only action made no positional progress and timed out on frame 11.
- The next candidate turns with forward input held, making every bounded steering action
  physically productive rather than asking the host to settle consecutive in-place turns.

## v96 - southwest movement bootstrap (2026-08-08)

- Version UUID: `087e081b-a163-4377-977f-8439c3f9cbd7` (`wowborg:v96`, uploaded
  inert; not submitted). Built from source `b537e88` with the published 0.1.188 contract.
- Request `xreq_1299172a-e1d0-4c68-b5d8-111811a8fa9d` proved the short southwest
  bootstrap: nine movement prefixes advanced frames 2 through 10 and settled within eight yards
  of `(-9200,-2545)` without combat or damage. The following eastbound semantic action again
  advanced inside the host but never returned frame 11 to the policy.
- The next candidate retains the proven semantic bootstrap, then drives canonical road legs with
  bounded ordinary keyboard steering. This isolates whether vector actions only failed previously
  because they were submitted as the first movement at the exact spawn.

## v95 - canonical long-movement contract probe (2026-08-08)

- Version UUID: `a6f5493e-d1b0-47bc-91ae-f5afefa03081` (`wowborg:v95`, uploaded
  inert; not submitted). Built from source `f14e439` with the published
  `vanilla-wow:0.1.188` game contract image
  `sha256:4e560ebcd9eec85f09305e15ae51cdc216715ee0135aa5968c26793fde334ac3`.
- Request `xreq_2f5ba9c4-db30-40d2-83dd-47a353c8a1f0` reproduced v90 exactly:
  the host acquired the canonical eastbound route and advanced 4.94 yards, but the policy never
  received frame 3 and timed out on frame 2. The local planner independently reported
  `helper_error`; there was no combat, damage, or death.
- Fresh v88's southwest opening returned successive frames on the same host. The next candidate
  therefore adds a short southwest movement bootstrap, safely before v88's lethal old endpoint,
  then turns onto the canonical road on the following frame.

## v94 - published 0.1.188 contract with rejected micro-targets (2026-08-08)

- Version UUID: `f7a4329f-d383-40e6-a88b-0168d3b8bedb` (`wowborg:v94`, uploaded
  inert; not submitted). Built from source `ce25c1d` with the exact
  `vanilla-wow:0.1.188` policy-side package image
  `sha256:4e560ebcd9eec85f09305e15ae51cdc216715ee0135aa5968c26793fde334ac3`.
  Policy image manifest:
  `sha256:358691b96f66d32754ac2f46584e44010f950cbe107878827bf8e08f5ce653f7`.
- Request `xreq_5b2351c5-bcc7-4cf6-ae05-f5c47305a133` proved that the experimental
  seven-yard micro-target still times out without motion under the older package. It does not
  test the original long semantic movement shape that worked in v88.
- Fresh control `xreq_d53a387d-906d-4dfd-9372-abfc3018f1ed` reran unchanged v88 against the
  current 0.1.208 game and confirmed real movement. It later died at the old southwest detour
  `(-9313.6,-2689.8)` and spent 84.2% of the episode as a ghost, so it validates transport only.

## v93 - post-form wait activation probe (2026-08-08)

- Version UUID: `b300526c-5f90-47f4-bb79-cbfef0e80e98` (`wowborg:v93`, uploaded
  inert; not submitted). Built from source `ce25c1d` against `vanilla-wow:0.1.208`.
  Policy image manifest:
  `sha256:b277bbf68e7443901c446bebdc1fce28e57e51c2f6e09dc49025b39a2297b7de`.
- Request `xreq_12df99ec-6d9f-419f-8a33-71e1d7f8ea39` accepted an explicit wait from frame 2
  to frame 3, then timed out on the first movement action without advancing frame 3. This rules
  out a simple Travel Form settlement race.

## v92 - semantic micro-target activation probe (2026-08-08)

- Version UUID: `e05dc2ad-be49-4e9f-b9c2-a971ca6a7c31` (`wowborg:v92`, uploaded
  inert; not submitted). Built from source `c5881ed` against the exact
  `vanilla-wow:0.1.208` environment image. Policy image manifest
  `sha256:a76c87619a92d1aca52ec6f95f1bb050d784297b460b9d5bd8ea942f94755929`.
- Replaces v91's bounded vector input with seven-yard semantic micro-targets intended to settle
  inside the five-second host action horizon. Request
  `xreq_3f2afccb-a366-446e-a201-a431bd5ff07f` still timed out on the first movement action
  without advancing frame 2. Target length therefore is not the discriminator.
- The older moving v88 image carried the 0.1.188 policy-side environment package; the current
  package removed its remote navmesh setup but did not change `VanillaWowEnv.step`. The next
  candidate explicitly advances one contract-native wait frame after Travel Form activation
  before submitting movement, testing the remaining cast-to-movement synchronization boundary.

## v91 - bounded road steering activation probe (2026-08-08)

- Version UUID: `b2cc42e5-822d-4459-89eb-6c16195a7e3c` (`wowborg:v91`, uploaded
  inert; not submitted). Built from source `0b21234` against the exact
  `vanilla-wow:0.1.208` environment image. Policy image manifest
  `sha256:faf0824538516d715a22efd27f4b38756a142878ef30c1f4245a42e25a443987`.
- Keeps v90's canonical road but replaces long semantic moves with bounded ordinary steering.
  Activation request `xreq_ba3e0d47-539f-4e3d-8f89-44c776e050fb` narrowed the failure further:
  its first 0.249-second turn-only `move_vector` timed out for 30 wall-seconds without advancing
  frame 2. No route motion, combat, damage, death, or ghost state occurred.
- The next candidate uses short semantic micro-targets instead. v90 proved that `move_to`
  advanced 4.94 yards before the five-second environment action deadline, so a target within
  that settlement horizon can complete rather than retaining a long movement continuation.

## v90 - canonical road to the Great Lift lower dock (2026-08-08)

- Version UUID: `6593c92d-2c1a-46f8-abe5-658300d5a7eb` (`wowborg:v90`, uploaded
  inert; not submitted). Built from source `fb09adc` against the exact
  `vanilla-wow:0.1.208` environment image. Policy image manifest
  `sha256:60f8460cb9a7e9c0fff156f46989be78d33dc83900b2c2a99240003dad798b3d`.
- Replaces the static opening detour and partial route with the deployed owner's canonical
  level-51 road spine: 23 connected ordinary-navmesh legs and 6,560.2 route yards through
  Tanaris, the Shimmering Flats, and Thousand Needles. On lower-dock settlement it emits
  `traverse_great_lift_arrived` and ends; it does not wait for or board the lift.
- First five-episode hosted request `xreq_0e577780-d491-4ac5-9a4f-256258d15c7a`
  deterministically failed before combat: all five runs remained alive at spawn, and the first
  302-yard semantic move timed out after advancing only 4.94 yards. Environment telemetry
  records an `advanced_corridor` settlement followed by `action_deadline_expired`; every policy
  trace ended with zero guidepoints and `reason=no_progress`. This falsifies the coarse hosted
  movement activation, not the navmesh route, whose exact pinned plan is connected.

## v89 - navigation tooling and Stuck cooldown cleanup (2026-08-08)

- Version UUID: `18b5df77-d270-4f43-a168-2b4a8d389255` (`wowborg:v89`, uploaded
  inert; not submitted). Built from source `a5c9c01` against the exact
  `vanilla-wow:0.1.208` environment image. Policy image manifest
  `sha256:ae8a99cc2ecf5e96319f80f2b0a949def74db37cc93a372a8de64ea9c141e78a`.
- Wowborg now checks the authoritative `cooldown_spell_ids` projection before invoking the
  Stuck spell 7355. A cooldown suppresses the redundant cast, emits
  `stuck_skipped(reason=cooldown)`, and lets the existing local-mover wait fallback advance
  the frame. Navigation, route selection, combat, stealth, and recovery behavior are otherwise
  unchanged.
- Local cleanup reclaimed 658.6 MB of disposable BuildKit cache without removing shared images
  or volumes. `tools/route_lab.sh` now runs its pinned amd64 image explicitly, and
  `route_lab.py` imports `WorldPoint` from the current `environment.contract.policy` module.
  One focused cooldown regression passed, an ad-hoc real-navmesh route arrived, and the exact
  amd64 build/import verification completed. Hosted activation evidence remains pending.

## v88 - 0.1.188 bring-up and unchanged 0.1.208 seamless-movement control (2026-08-07–08)

- Version UUID: `3f955f79-6404-4d51-8efe-c04675d22926` (`wowborg:v88`, uploaded
  inert; not submitted). Built from runtime source `cbbbee0`. Registry evidence identifies
  policy image digest `sha256:c2174abab0852777bcedbc182bfac67695a9a6b07e57f40c19a631a43189afdf`
  and client hash `sha256:ae8a99cc2ecf5e96319f80f2b0a949def74db37cc93a372a8de64ea9c141e78a`.
  The older claim that `88b214…` was its base image digest was wrong: that value is the
  0.1.188 game container's registry `client_hash`, whose actual image digest is `4e560eb…`.
- Updates stale-frame recovery to match the canonical `Observation` rejection
  messages. Hosted canary `xreq_9d61f4e7-b776-45af-8956-5f3fafadff02`, episode
  `ereq_3c0ea5fd-26ac-4ff4-9fb9-b5f0fdb81102`, completed without an operational
  or policy failure and advanced through frame 111. The retained policy trace
  contains five successful stale-frame refreshes.
- The host instrumentation is available in the retained game log and parses as
  306 typed events: 96 admissions, 46 executed actions, 50 executor-free actions,
  46 continuation preparations, 45 prefix settlements, two movement-control
  transitions, 15 action stalls, five rejected requests, and one close. This run
  deliberately exposed the next environment bug instead of producing a movement
  comparison: the character displaced zero yards. The first move emitted only a
  `route_turn`, then settled `forward_not_held`; all 44 later movement prefixes
  settled `no_movement_emitted`, so continuation remained inactive.
- Wowborg was not rebuilt for the environment fix. On canonical `vanilla-wow:0.1.208`,
  owner acceptance request `xreq_c0649f44-ecca-4f82-bc2a-e1cdf95684b1` completed 5/5
  with mean score 1,615.62 and 17,308.749 trajectory yards. There were zero nonterminal
  stops, host stalls, rejected requests, detached frames, or direct left/right reversals.
  Eleven turn runs lasted at most 100 ms, down 98.5% from 144 on the 0.1.207 canary, and
  none had the old same-waypoint route-bearing disappearance signature. Three raw
  stop/restart pairs were final forced-root/scoring-logout artifacts with no later
  observation. This isolates the improvement to the game environment; v88 remains inert
  and unsubmitted.
- Independent lab request `xreq_cb6f96ae-00d0-40ab-b5a5-d10cb46248e0` then reproduced
  the result 5/5: mean score 1,607.572, 17,352.720 trajectory yards, zero active
  nonterminal stops, host stalls/rejections/detached frames, stale-frame rejections,
  direct reversals, or old bearing-disappearance signatures. It recorded ten turns at
  most 100 ms (93.1% below the 0.1.207 canary), plus two death/ghost control transitions
  and two final scoring/logout artifacts kept separate from traversal continuity.

## v86-v87 - superseded 0.1.188 contract bring-up (2026-08-07)

- v86 (`92e3963c-16fb-43e6-8975-bbe6f2a9ad7e`) migrated Wowborg from the removed
  `AgentFrame`/`AgentAction` and `/env` surfaces to `Observation`/`Action` over the
  injected `/player` session. Its canary connected but rejected frame 1 because
  the host emitted the open spell intent `threat_reduction` while its packaged
  `SpellObservation` still declared a closed literal set. The superseded request
  `xreq_887c869f-60e0-4ef6-bfdd-73b059b440f3` was cancelled after the deterministic
  failure began retrying.
- v87 (`c3852b29-1580-4443-a059-62a4744c2d9d`) restored the narrow spell-intent
  compatibility widening. Canary `xreq_42484cc9-e966-4686-a0dc-b4c1d1b372c6`
  completed, but the old stale-frame error markers left it pinned on frame 2 with
  399 rejected submissions. v88 supersedes it. Neither version was submitted.

## v85 - Vanilla WoW 0.1.178 semantic session migration (2026-08-06)

- Version UUID: `d346b685-7e5e-42ac-afbd-acfe0b8420c9` (`wowborg:v85`, uploaded inert;
  not submitted). Built from source `5253d60` against canonical `vanilla-wow-episodic
  0.1.178` and its exact linux/amd64 image
  `sha256:ec18781aed1c53d60d188a2287eba7e594affe1447df408ac17bf37f44131f6c`.
- Removes Wowborg's auxiliary direct `/player` progress connection. In 0.1.178 each slot has
  one immutable interaction mode; opening `/player` first claimed the slot as direct and made
  the semantic `/env` handshake return HTTP 403. `/env` remains the sole gameplay connection,
  and the policy's navigation/action behavior is otherwise unchanged.
- Matched request `xreq_4f0dd79f-f7e8-4e61-834c-adaf7d4689ce` completed 5/5. Scores were
  1,190.46, 1,315.65, 1,368.19, 1,305.86, and 1,523.10. Across 17,755.902 trajectory yards,
  the replays contain 500 raw forward stops, 492 boundary-only stops, and zero falling packets.
  That is **27.71 boundary-only stops per 1,000 yards**, down 25.2% from v80 on 0.1.174
  (37.04), but it misses the preregistered 50% stopping-fix threshold (below 18.52). The new
  host improves continuity but does not fix the visible stop/start churn.

## v81-v84 - superseded 0.1.178 contract bring-up (2026-08-06)

- v81 (`c6962e30-0e58-4808-9478-eb0aa6007700`) ported Wowborg to the flat 0.1.178
  `AgentAction`/available-action contract. v82 (`412ef217-ee8f-4710-a716-0f90baa0b0a3`)
  delegated slot/token query construction to the pinned SDK. v83
  (`86f55014-d545-4936-b1e9-f90c257a6a19`) added credential-safe endpoint-shape tracing. v84
  (`f950a5bf-38ba-409d-9ac4-fab5798297ed`) supplied the required semantic interaction query.
- These uploads were inert and never submitted. Their hosted diagnostics failed before frame 1
  with HTTP 403; v84's retained traces proved the final blocker was not missing auth/query keys
  but the incompatible direct `/player` slot claim removed in v85.

## v80 - current-contract action response timing ledger (2026-08-06)

- Version UUID: `db6faec7-451a-483f-b65d-db2b3f80fded` (`wowborg:v80`, uploaded inert;
  not submitted). Built from source `917e83a` with private tags `strategy=traverse`,
  `source=917e83a`, and `experiment=action-response-timing-current-contract`; amd64 image
  manifest `sha256:31c2b6afe33b4c12c6d6fc47a5ed8d627322dc749e322dec1e28982fb6dfe426`.
- Replaces v79's stale `player.sdk.navmesh.models` import with the canonical traverse-wow
  0.1.174 `environment.navigation` contract; timing instrumentation and gameplay behavior are
  otherwise unchanged. Exact 0.1.174 linux/amd64 build verification passed.
- Hosted request `xreq_75c86237-6b7a-4a3a-abe3-cb4b9fd65687` completed 5/5 without policy
  failures. Wowborg submitted an action for 100% of 2,561 unique offered frames. Median and p95
  frame age were 0.548 ms and 0.810 ms, but each run had exactly three synchronous navigation
  pauses over the host's five-second deadline (15 total, 7.63-17.23 seconds): initial planning,
  frontier replanning after opening no-progress, and ghost recovery planning. Those pauses were
  followed by all 15 stale-frame rejections. The replays still contain 717 forward stops and 707
  boundary-only stops, while only 38 raw stops fall in the coarse wall-clock windows of the 15
  slow responses. This falsifies missed frame responses as the primary source of the pervasive
  choppiness, but confirms Wowborg creates three long over-deadline silence windows per run.
  Exact host `action_stall` counts remain unavailable at the policy evidence boundary.

## v79 - action response timing ledger (2026-08-06)

- Version UUID: `8ba9953a-3c7d-48ca-a9c6-d872a044b8e7` (`wowborg:v79`, uploaded inert;
  not submitted). Built from source `c69ce0e` with private tags `strategy=traverse`,
  `source=c69ce0e`, and `experiment=action-response-timing`; amd64 image manifest
  `sha256:b8233c2c00aea09419a26e5f0b9f1af93186be2ac0bd338dbc5b05c6ea1e0c06`.
- Behavior-neutral instrumentation records policy-visible timing for every offered frame:
  frame receipt-to-submission latency, synchronous `/env` step round-trip, submitted and
  returned frame IDs, raw action status, stale refresh, and locally skipped stale/terminal
  actions. It does not guess `/env`-internal continuation-release reasons or host
  `action_stall` counts.
- The build contract was refreshed from stale traverse-wow 0.1.160 to the exact active
  traverse-wow 0.1.174 game image
  (`sha256:cec97b29f7c2e79ce3f6ef816d50116b28ba4a323069a0fbcbd26538408408d8`). The real
  linux/amd64 image build and its `/env` plus `/player` import verification passed. Per lab
  policy, no local gameplay smoke or routine test suite preceded upload; the hosted episode
  is the behavioral test.
- Hosted request `xreq_e71c7cfd-117d-4992-a194-48de1ab1910a` failed before play because the
  source still imported `player.sdk.navmesh.models`, which does not exist in 0.1.174. v80 fixes
  that current-contract startup bug and supersedes v79.

## v78 - complete regional spawn-safe opening (2026-08-05)

- Version UUID: `36f3f0bf-2261-42ec-9d8a-4a084e145b81` (`wowborg:v78`). Built from source
  `3e95dcb` with private tags `strategy=traverse`,
  `source=3e95dcb`, and `experiment=complete-spawn-safe-opening`; amd64 image manifest
  `sha256:5150e1ddf8985a836fcd9f8a31c30efaa658059b185c0f38829e3a10466b5059`.
- Replaces only v77's unsafe three-point opening with eight exact ordinary-navmesh
  guidepoints, then rejoins the existing first Centipaar bypass. The 2,122.1609-yard
  nine-leg exact Detour route has zero conservative detection-plus-wander envelope
  intersections across all 136 pinned regional hostile rows and 704 smooth-route points.
  The tightest clearance is +0.226 yards, so an exact first-nine-entry regression pins the
  coordinates. Combat, recovery, the later route, and normal Great Lift boarding are
  unchanged. Focused checks: 8/8 passed.
- Corrected-clock hosted canary `xreq_e984c401-f498-449d-8aa6-77cad0e1912b` on canonical
  `traverse-wow 0.1.174` completed 1/1 with no failure and scored **1,304.14 northing**.
  The ordinary-access replay contains 1,114 client movement packets, 3,746.6 trajectory
  yards, zero falling packets, and a Travel Form cast; no owned policy-log artifact was
  listed at ordinary permissions. Submission `sub_6c5e6403-d23f-4296-8ee9-3f4dee8b2477`
  placed membership `lpm_67027432-7d93-40ba-9f3c-8ed632f83735` with
  `auto_champion=never`. It subsequently qualified and became the active champion; v63 is
  benched. Its round-325 replay (`ereq_b222a884-8660-440c-860d-3050ec7278b6`) shows one
  unrecovered death, 1,531.0 ghost seconds, 2,818 incoming and zero outgoing damage, and 13
  Stuck invocations. The stateful batch profiler is documented in
  `docs/vanilla-wow-replay-analysis.md`.

## v77 - spawn-safe Tanaris opening (2026-08-05)

- Version UUID: `e9cfde9d-5ac5-41a2-ac56-0977de5401b5` (`wowborg:v77`, uploaded inert;
  not submitted). Built from source `4217916` with private tags `strategy=traverse`,
  `source=4217916`, and `experiment=spawn-safe-opening`; amd64 image manifest
  `sha256:bfdac1b1f1297b357d68add23e50211ba0ccaa15f3a0dc7b55a45e5004fdc62c`.
- Prepends three ordinary-navmesh graph-center guidepoints before the existing first bypass.
  Their exact chained Detour route is 1,249.0415 yards (+9.03% versus v75) and has zero
  conservative-envelope intersections across all 48 pinned hostile spawns in the 1,500-yard
  opening region. The tightest positive margin is 2.324 yards; the fatal v75 Scorpid has
  12.085 yards of margin. Travel Form, recovery, the remaining route, and normal Great Lift
  boarding are unchanged. Focused checks: 39/39 passed.
- Current-format request `xreq_227bf53a-a8f3-42a0-bc00-1a367d5b9457`
  (`ereq_2284a7b1-9cde-4dfe-a5ea-bb5239934536`) completed with a ghost-derived
  **1,752.34 score** and `reached_goal=false`. Maximum living x was only `-9056.248`.
  A Rabid Blisterpaw (entry 5427, low GUID 22586) wandered onto GP1 and killed wowborg
  before the guidepoint completed. The claimed 48-spawn audit was incomplete: it reused a
  route-local subset while the correct regional query contains 136 hostile rows. Re-auditing
  v77 against all 136 finds seven envelope intersections. The next candidate must regenerate
  only the opening against that complete set; a one-off nudge leaves six known crossings.

## v76 - reacquire Travel Form after recovery (2026-08-05)

- Version UUID: `5a13f3cf-89d0-4f52-a8b8-ea6a7668021f` (`wowborg:v76`, uploaded inert;
  not submitted). Built from source `d3216d7` with private tags `strategy=traverse`,
  `source=d3216d7`, and `experiment=travel-form-safe-resume`; amd64 image manifest
  `sha256:caec163ab8ff035d5df3b7ab99324ef3a53c06ece50fecb43405d71b2209f93d`.
- The route's existing verified living, out-of-combat safe-resume seam now reacquires Travel
  Form after combat or corpse recovery. The route, normal lift boarding, and healthy
  run-through behavior are unchanged. Focused checks: 39/39 passed. Hosted request
  `xreq_5d974b37-303d-4175-b218-9c59d9b0d329` was cancelled while still pending after the
  independent replay reducer proved v75 never revived, so the safe-resume callback would not
  execute on the observed blocker. v76 produced no episode evidence and remains inert.

## v75 - board and ride the observed Great Lift (2026-08-05)

- Version UUID: `c75e24cc-166f-43df-9d52-d77724cc4b16` (`wowborg:v75`, uploaded inert;
  not submitted). Built from source `aed90c9` with private tags `strategy=traverse`,
  `source=aed90c9`, and `experiment=great-lift-normal-boarding`; amd64 image manifest
  `sha256:42f891392315a497a46e5f76226500113cb46e898108871308377237cda73d7d`.
- After reaching the lower dock, Traverse waits for visible platform entry 11898/11899 at
  dock height, turns and walks onto it with bounded ordinary `move_vector` input, stops
  piloting once authoritative `on_transport` is observed, then walks toward the upper dock
  above z=80 and resumes navmesh travel at the upper road. It does not inject coordinates,
  teleport, bridge the disconnected navmesh, or use death routing. Focused checks: 39/39
  passed. Current-format request `xreq_f658f8de-ab1c-44a9-ae11-f12fb3e48478`
  (`ereq_6781dd4f-4ba8-492a-84a9-39344f8c5cb8`) completed with **1,764.21 northing**
  and `reached_goal=false`. It traveled 2,807.5 yards and ended on the normal Tanaris road
  chain at `(-7422.79,-3726.72,10.16)`, so the lift mechanism was not reached and remains
  inconclusive. The stateful owned-replay reducer recorded one death, while the replay contains
  only the startup Travel Form cast. The next isolated change reacquires Travel Form through
  the existing safe post-combat/post-revival route callback.

## v74 - speed-first Travel Form (2026-08-05)

- Version UUID: `621ee466-2caf-4325-881d-0ba483dc1bfd` (`wowborg:v74`, uploaded inert;
  not submitted). Built from source `d421042` with private tags `strategy=traverse`,
  `source=d421042`, and `experiment=speed-first-travel-form`; amd64 image manifest
  `sha256:2a0465e3157a66524715d24dbd47c81b831b3995e68b947ae7c32d44d1b2fe98`.
- Traverse now activates Travel Form immediately and uses the existing healthy run-through
  navigation behavior instead of deliberately engaging early attackers. No movement or
  recovery bypass was added. Focused checks: 32/32 passed.
- Current-format request `xreq_3bad8628-4872-4422-a805-41f74ac3c256` completed on
  `traverse-wow 0.1.166` with **1,797.73 northing** and `reached_goal=false`, below the
  preregistered 2,000-yard failure floor. The ordinary-permission fetch returned its replay
  but no owned policy trace, results artifact, or policy log. The replay confirms one Travel
  Form cast and 2,790.9 yards of trajectory. This result did not reach or test the Great Lift.

## v73 - hand hostile contact to combat immediately (2026-08-05)

- Version UUID: `45f04501-7e76-4511-a9b7-892b421cc607` (`wowborg:v73`, uploaded inert;
  not submitted). Built from source `351126e` with private tags `strategy=traverse`,
  `source=351126e`, and `experiment=early-combat-handoff`; amd64 image manifest
  `sha256:ae5fe98ab7971f64d13e6d9cee26ebc0adf5bafd3af821e49b0e520317054fc6`.
- Only Traverse's existing `engage_attackers` flag now makes the local mover surface the first
  combat frame before generic run-through, stall bookkeeping, or Stuck. Other strategies retain
  healthy run-through behavior. Exact-target face then attack remains the primary sequence; if
  server movement authority is already blocked, attack starts and face is retried when authority
  returns. Focused checks: 32/32 passed.
- Canonical 10x hosted request `xreq_0be069a7-204b-47a9-a39d-be483e820180` completed valid on
  `traverse-wow 0.1.164` with **408.57 northing** and `reached_goal=false`. That northing is not a
  comparative result because the 10x episode clock outruns ordinary locomotion, but the targeted
  mechanism passed: first hostile contact surfaced before any Stuck action; three exact attackers
  were faced and attacked successfully; outgoing damage reached 7,695; all three fights ended;
  and wowborg had zero deaths. A full-duration 0.1.160 request
  (`xreq_c317e459-ee91-4bab-a0fb-b789f2709bed`) was cancelled after live league inspection showed
  that its 45-wall-minute format is obsolete; the active league now uses the same 270-wall-second
  10x format as the mechanism request.

## v72 - engage exact Traverse attackers (2026-08-05)

- Version UUID: `c6e67ab5-cbe3-4e1e-8970-8be5e27d2638` (`wowborg:v72`, uploaded inert;
  not submitted). Built from source `c0cc241` with private tags `strategy=traverse`,
  `source=c0cc241`, and `experiment=exact-attacker-melee`; amd64 image manifest
  `sha256:5a07cc5e0057d129f0b4b2d515082b49d4506fb239f00b8803cc597af17c3b29`.
- Changes only Traverse's existing combat pause. It resolves a typed active attacker from the
  current auto-attack GUID, visible recent damage source, or a live visible unit targeting
  wowborg; within five yards it faces, starts semantic melee, and holds the swing. When no exact
  adjacent attacker is available, the prior flee/wait behavior remains unchanged. Activation
  traces include target GUID, face/attack settlement, and cumulative outgoing damage. Route,
  Prowl, recovery, and every other strategy are unchanged. Focused checks: 30/30 passed.
- Canonical 10x hosted request: `xreq_90ef6893-552c-4f08-8360-1c1c299203ca` on
  `traverse-wow 0.1.164` completed valid in about 4.5 wall-clock minutes with **1,860.96
  northing** and `reached_goal=false`. The score was ghost-derived: maximum living x was only
  `-8905.77`, wowborg died at 154.8 simulation seconds before any guidepoint, and it spent the
  remaining 80.3 wall-clock seconds as a ghost. The mechanism resolved the exact attacker and
  started auto-attack, but the face action failed while the authoritative frame reported movement
  unavailable. It dealt zero outgoing damage across 335 hold observations. Both pre-registered
  criteria failed; the next experiment defers facing until movement authority returns.

## v71 - reacquire Prowl after recovery (2026-08-05)

- Version UUID: `d5960580-8056-4026-b2a8-f79f3799f896` (`wowborg:v71`, uploaded inert;
  not submitted). Built from source `fe11437` with private tags `strategy=traverse`,
  `source=fe11437`, and `experiment=prowl-reacquire`.
- Changes only the recovery seam for the existing early Prowl behavior: the game-agnostic route
  navigator can notify a strategy after combat ends or corpse recovery restores a living,
  out-of-combat frame. Traverse uses that hook during its first four guidepoints to run the
  already traced, idempotent Cat/Prowl activation before movement resumes. The route, initial
  stealth, combat fleeing, corpse recovery, and post-bypass Travel Form are unchanged. Focused
  checks: 2 recovery-hook tests and 6/6 Traverse strategy tests passed.
- Matched hosted request: `xreq_2604d7d8-8d51-489f-b310-d9017b83bd42` completed valid with
  **1,139.61 northing (7.18%)** and `reached_goal=false`. The pre-registered mechanism passed:
  Prowl activated successfully after both corpse recoveries (three successful activations total),
  deaths fell from three to two, dead/ghost time fell from 2,219.6 to 2,003.6 seconds, and maximum
  living x improved from `-8423.30` to `-8047.39`. It reached the first bypass guidepoint for the
  first time, but only after 2,570.5 seconds because two deaths still incurred roughly 1,000-second
  corpse runs. The first fight began with Prowl already active, so the next experiment adds only
  exact-attacker melee engagement to the existing combat pause.

## v70 - Prowl through the early hostile band (2026-08-05)

- Version UUID: `c330d793-586b-4cc6-a7ec-0c15a1109ab2` (`wowborg:v70`, uploaded inert;
  not submitted). Built from source `d072d11` with private tags `strategy=traverse`,
  `source=d072d11`, and `experiment=early-prowl`; amd64 image manifest
  `sha256:566565115de4734969e7f67a6020a4a3fbc334621f4e04d1282c299d361b946f`.
- Changes only survival through the early predicted hostile band: enter Cat Form (768), cast
  the highest known Prowl rank, remain stealthy through the four bypass guidepoints, then
  switch back to Travel Form (783) for the long dock leg. The v69 route, navigation, combat,
  recovery, and lift behavior are unchanged. Cat, Prowl, and Travel activation/settlement are
  traced separately. Focused strategy checks: 6/6 passed.
- Matched hosted request: `xreq_36167fe8-b19a-4989-b634-c332c5d908bf`. It completed valid
  with a reported **1,751.51 score (11.03%)** and `reached_goal=false`, but the headline
  includes a graveyard teleport and ghost movement. Maximum living x was `-8423.30`, only
  763.70 yards (4.81%) north of spawn. Cat Form and Prowl rank 1 both settled successfully at
  startup, then Prowl was lost at the first hostile detection and never reacquired because the
  blocking first-guidepoint navigation call occupied the rest of the episode. It reached zero
  guidepoints; three deaths consumed 2,220 seconds (83.3%). The next experiment changes only
  Prowl reacquisition at the navigator's safe post-combat and post-revival resume seams.

## v69 - avoid the full active Centipaar spawn set (2026-08-05)

- Version UUID: `69885bb8-34f4-4e7c-9d90-56e6d91edd71` (`wowborg:v69`, uploaded inert;
  not submitted). Built from source `61a8e84` with private tags `strategy=traverse`,
  `source=61a8e84`, and `experiment=centipaar-bypass`; amd64 image manifest
  `sha256:ea144443231965ec4deff0ac287428e78b23727eb8538493d753f56811eff53a`.
- Changes only the route table to four exact bypass guidepoints followed by the existing
  Great Lift lower dock. The 5,995.5-yard, 17-chunk exact 0.1.160 Detour proof reaches the
  dock, clears v67's Silithid coordinates by at least 41 yards, and crosses zero static or
  conservative-wander encounters across all 112 active Centipaar Wasp/Worker spawns. Eight
  other static hostile exposures remain. Travel Form, combat, recovery, lift behavior, and
  navigation control are unchanged. Focused strategy checks: 6/6 passed.
- Matched hosted request: `xreq_e1288518-2403-460e-8a5a-12a43c02bfee`. Evaluation is
  completed with **662.68 northing (4.17%)**, final/max living `world_x=-8524.32`, and
  `reached_goal=false`, regressing sharply. It attempted only the first bypass guidepoint,
  arrived at none, then failed `no_progress`. Two deaths consumed 2,193 seconds (82.3% of
  the episode): Rabid Blisterpaw plus Glasshide Petrifier caused the first, and another
  Rabid Blisterpaw caused the second. The Great Lift was never attempted. Eliminating
  Centipaar exposure was insufficient because remaining early-route hostiles kill wowborg
  before it reaches the protected corridor.

## v68 - direct Detour route to the Great Lift (2026-08-05)

- Version UUID: `bb7f59cc-a684-4ab4-b485-7071170502d1` (`wowborg:v68`, uploaded inert;
  not submitted). Built from source `fa083a6` with private tags `strategy=traverse`,
  `source=fa083a6`, and `experiment=direct-great-lift`; amd64 image manifest
  `sha256:d4251fcac43969e84393c1052cd42c2d62aedae227d3c99d76f0ac7d2056b0bc`.
- Changes only the route table to one semantic target: the existing Great Lift lower dock.
  Exact 0.1.160 Detour continuation reaches it in 13 chunks and 5,673.4 yards. Compared with
  v67, this is 1,031.1 yards shorter and crosses 15 rather than 49 static hostile detection
  ranges. Travel Form, combat, recovery, lift behavior, and navigation control are unchanged.
  Focused strategy checks: 6/6 passed.
- Matched hosted request: `xreq_3864dc6e-0e6f-45bd-8bae-fc9f3529da5a`. Evaluation is
  **cancelled before gameplay** (`running_at` absent; zero completed episodes). The expanded
  hazard audit found the direct Detour polyline passes 2.3 yards from an active Centipaar
  Wasp and 11.6 yards from v67's fatal Wasp onset, so running it would knowingly reproduce
  the lethal corridor. This cancellation provides no gameplay or performance evidence.

## v67 - bypass the observed southern mob corridors (2026-08-05)

- Version UUID: `a59a5117-1678-4c80-894d-c44a180c4052` (`wowborg:v67`, uploaded inert;
  not submitted). Built from source `cee622a` with private tags `strategy=traverse`,
  `source=cee622a`, and `experiment=east-bypass`; amd64 image manifest
  `sha256:8735805ca7cfc72a51b4aaaa0ccfda52ffef96c6410c4f6176de266f19f59dad`.
- Changes only the route table: the 23-point populated Tanaris/Thousand Needles road is
  replaced by the exact-0.1.160-Detour-proven east bypass at
  `(-8033.689,-2283.733,23.1)` and `(-6960.3,-3739.2,46.1)`, then the existing Great Lift
  lower dock. Travel Form, combat, recovery, lift behavior, and navigation control are
  unchanged. Focused strategy checks: 6/6 passed.
- Matched hosted request: `xreq_3293f9ba-ad00-4fdd-aefa-f71617e590a7`. Its purpose is to
  determine whether the geometrically valid bypass avoids v66's three observed hostile
  corridors and reaches the Great Lift lower dock. It completed with **1,300.82 northing
  (8.19%)**, final `world_x=-7886.18`, and `reached_goal=false`, 505.56 below v66. It reached
  only `tanaris-east-bypass`; `tanaris-east-entry` failed with `no_progress`, and the Great
  Lift was never attempted. Two deaths consumed 1,741 seconds (65.3% of the episode). The
  next iteration replaces the bypass with the shorter, lower-exposure direct Detour corridor.

## v66 - semantic Traverse route with the image default command (2026-08-05)

- Version UUID: `415de479-47fe-4bd0-877a-1238a29ebd96` (`wowborg:v66`, uploaded inert;
  not submitted). It is byte-for-byte the v65 image from source `b2e58e4`, uploaded without
  a command override so the image's working `python3 -m wowborg` command is retained.
- Matched hosted request: `xreq_288ca227-6bcc-44a9-8a5d-92ca4cb60ca6`. This is the
  authoritative semantic-route experiment; v65 produced no gameplay evidence. It completed
  with **1,806.38 northing (11.38%)**, final `world_x=-7380.62`, and
  `reached_goal=false`. The trace attempted eight guidepoints, arrived at seven, and recorded
  no typed route failure. Two deaths after aggro by Scorpid Dunestalker near
  `(-9025,-2690)` and Glasshide Gazer near `(-8170,-3326)` consumed 1,568 seconds; a third
  hostile corridor began near guidepoint 8. The next iteration changes only the southern
  route to avoid all three.

## v65 - follow the semantic Traverse route to the Great Lift (2026-08-05)

- Version UUID: `f1c58c43-9a1c-402b-98d8-b1ced0074ddc` (`wowborg:v65`, uploaded inert;
  not submitted). Built from source commit `b2e58e4` with private tags
  `strategy=traverse`, `source=b2e58e4`, and `experiment=semantic-route-prefix`.
- Adds only the current owner policy's 23-guidepoint smooth Tanaris/Thousand Needles route
  prefix through the Great Lift lower dock. Travel Form, combat, recovery, and the adaptive
  northbound fallback remain unchanged from v64. Each guidepoint activation and arrival is
  traced; route failure abandons the prefix and restores the existing fallback.
- Local image manifest:
  `sha256:8459bf415324f5e4d0c39dedbe1ce5739318adaa0190d07babfa3710a1682f31`.
  Full focused suite: 72/72 tests passed.
- Packaging failure: its upload metadata overrode the image command with
  `python -m wowborg.main`. That module defines `main()` but does not invoke it, so the
  container exited before `player_session_connected`. The first hosted job
  (`fe82ac3c-0e3f-4810-b17e-16a922026ede`) exhausted the episode deadline with
  `player did not connect`; its automatic retry showed the same missing policy log. Request
  `xreq_32a6f4d3-3ba0-48d1-a64d-b460fd6ed3e2` was cancelled. v66 repackages the identical
  image with its correct default command.

## v64 - maintain Travel Form before Traverse frontiers (2026-08-05)

- Version UUID: `b7a35d49-d39c-4cd8-aa06-d6562d0f4037` (`wowborg:v64`, uploaded inert;
  not submitted). Built from source commit `1f93d76` with private tags
  `strategy=traverse`, `source=1f93d76`, and `experiment=travel-form`.
- Adds only traced activation/reacquisition of Druid Travel Form (spell 783) before each
  frontier. Navigation, frontier selection, combat behavior, and recovery are unchanged from
  v63. Local image manifest:
  `sha256:87303ffdcadb349a619ea8237d5d9d7bc4e5a785c9c49b4fac016d74657b83d7`.
- Matched hosted request `xreq_422da653-5c3f-45dc-a5e5-804ad77757a0`, episode
  `ereq_6b3a8f57-bcd1-4187-89cb-12b4f3dcd184`, completed on the exact 0.1.160
  Traverse variant with **1,740.77 northing (10.97%)**, below v63's 1,959.23 baseline.
  Replay confirms spell-783 casts at 8.0s and 1,293.7s, but it died at 239.0s, 1,339.9s,
  and 2,508.3s and traveled 11,098 yards for a final `world_x=-7446.23`. Travel Form
  activated, but accelerating the same greedy path reached the lethal corridor sooner; the
  next iteration changes only the route prefix.

## v63 - open hosted spell-intent compatibility (2026-08-05)

- Version UUID: `7b3e2eb7-9b3f-47a7-b096-7217fc2daa06` (`wowborg:v63`). Built from
  source commit `02ab0ce` with private tags `strategy=traverse` and `source=02ab0ce`;
  local image manifest `sha256:11921bb1b4522a70bc6f104858d3148adf5a33a737a1f2d1bd066cf85078f1bf`.
- Behavior is unchanged from v62. Before frame parsing, it widens only
  `SpellObservation.intent_names` from the stale packaged Literal to `list[str]`, matching
  the owner client's open vocabulary and accepting the host's observed `threat` and
  `threat_reduction` labels. Focused suite: 68/68 tests passed; real amd64 build verified
  both `/env` and `/player` imports.
- Hosted canary `xreq_17763e42-3a8f-4cca-9ea1-d1172ebde234`, episode
  `ereq_58e8eed3-79e3-47d4-8440-c031790dfcd1`, completed on the exact 0.1.160 Traverse
  variant with score/northing **1,959.23** (12.34% of the 15,874.33-yard goal). It attempted
  four frontiers and arrived at three, but died twice and spent about 1,574 seconds (59% of
  strategy runtime) on corpse recovery. Replay trajectory was 8,707.5 yards for only 1,959.23
  net northing. This is the baseline for the Travel Form iteration.
- Submitted to Traverse Wow as submission `sub_941c5190-13a5-4ca5-93b1-d0bba19d8b19`.
  It was placed immediately as active competing membership
  `lpm_059413b3-fa38-4c8f-b218-8521406d24a2`. Official round 142
  (`round_d1a45aeb-00d6-4fce-bb53-06f066f2ad56`) completed with a valid **1,776.98**
  northing score (`world_x=-7410.02`, `reached_goal=false`), fifth of seven in the round.
  Round 143 (`round_36c2f641-d101-425b-aa3d-6c2ef7f9db03`) completed with **1,308.52**
  northing (`world_x=-7878.48`, `reached_goal=false`), fifth of eight. The leaderboard
  retains its 1,776.98 best score and places it rank 7 after two rounds. Round-result ID:
  `rres_e12c47a3-a88a-4f26-9d0a-91675299e5ba`; replay job:
  `f91c061b-1ef5-4878-b2a6-50d755d2c131`.
- Round 144 (`round_6061ea14-fdb6-4ab5-bec2-36085a7f8b6a`) completed with **1,357.49**
  northing (`world_x=-7829.51`, `reached_goal=false`), sixth of seven scored entrants.
  The leaderboard retains 1,776.98 and rank 7 after three rounds. Round-result ID:
  `rres_29a8de20-c032-4819-866a-4f96dd5448e9`; replay job:
  `14d24b45-89cb-42e4-8455-490adf2f6280`.
- Round 145 (`round_97932121-2e61-47b0-8aaa-0eeb27d5774b`) completed with a new retained
  best of **1,834.47** (`world_x=-7352.53`, `reached_goal=false`), sixth of nine. Round-result
  ID: `rres_66f89a96-6599-4750-90ed-4b35ccd6c3b1`; replay job:
  `fb41c199-140a-4729-8ccd-501ead206ebc`.
- Round 146 (`round_5c914794-356e-4433-81f1-31958799a10d`) scored **1,624.98**
  (`world_x=-7562.02`, `reached_goal=false`), sixth in the round. The leaderboard retains
  1,834.47 and places wowborg rank 8 after five rounds. Round-result ID:
  `rres_d35a7fb5-b394-4d6a-93db-4f071921b19b`; replay job:
  `a5c374eb-0eae-472f-b5f0-2769dd9656c1`. Round 147 is running.

## v62 - Traverse strategy boundary and northbound frontier objective (2026-08-05)

- Version UUID: `b2f6f022-90a9-48b2-a5ac-cd37464046ec` (`wowborg:v62`, uploaded inert;
  not submitted to a league). Built from source commit `683b0af` with private tags
  `strategy=traverse` and `source=683b0af`.
- Bakes `WOWBORG_STRATEGY=traverse` into this immutable version. The new strategy registry
  isolates competition objectives from shared navigation/recovery so later competitions can
  receive their own one-strategy version without forking the bot.
- Traverse repeatedly queries the canonical connected local-navmesh graph and chooses the
  safest untried frontier with greatest Kalimdor world X. Its trace records strategy startup,
  every frontier activation, authoritative northing gain, route failures, and final goal
  fraction.
- Built against certified traverse-wow 0.1.160
  (`cow_3eca82b6-2ad7-476b-88af-832d1faa666d`, game image
  `sha256:bc2aec56961cd2d106b4d9d52a7ec63f49517b2421fcef6b5fe168bd33183cdb`).
  This release publishes the copied Python contract from `/opt/coworld-python`.
- Local image manifest: `sha256:e51bf00f8c7b3f45ccba5ed4e2a6b01bee6fb0c22256100fbcb20b0f3a09ec00`.
  Full focused suite: 67/67 tests passed; real amd64 build verified both `/env` and `/player`
  imports.
- Targeted hosted request `xreq_9b9bd8b7-45c3-4bf9-af54-d62c0cac6cbb`, episode
  `ereq_0bae0bd3-2fcc-4942-9475-257aa7e30200`, failed before the first parsed frame on the
  exact 0.1.160 `kalimdor-south-to-north` variant. The host emitted spell intents `threat`
  and `threat_reduction`, which its own packaged closed `AgentFrame` enum rejects. The policy
  artifact contains the exact `ControlProtocolError`; there are no results or replay. Do not
  submit v62.

## (unnumbered) - typed startup-settlement supervision (2026-08-04, locally proven, NEVER uploaded)

- Preserves the upstream distinction between a submitted action with an observed typed result
  and an already-pushed frame where no matching `action_state` has arrived. L0 no longer counts
  the latter as a movement stall, preventing the startup Stuck cast and false replan without
  weakening the two-settlement unstick threshold for genuine settled stalls.
- Built against a disposable owner-HEAD SDK and exercised only with an exact 0.1.152 runtime
  derivative containing owner fix `1608da7a` (owner-repo PR #7809); no game or policy artifact
  was published.
- Known data-only course: 2/2 reachable arrivals, 1/1 impossible target rejected, zero replans,
  zero falls, 165.3 replay yards, and one uninterrupted forward span per reachable journey.
- Held-out course: repository search confirmed `(-500,-4300,46)` was absent before the run;
  it arrived in 97.5 seconds as one 121.8-yard forward span with zero replans/falls, while the
  matching z=226 high-air target failed fast as unreachable.
- Full wowborg regression suite: 64/64 tests passed. Never
  uploaded: it must be rebuilt against the released game SDK and verified hosted after the
  owner fix ships.

## v61 - accelerated-wow 0.1.152 SDK rebuild (2026-08-04)

- Version UUID: `e3493732-4c72-4204-9e57-4976a1ce18c6` (`wowborg:v61`, uploaded inert;
  not submitted to a league). Behavior unchanged from v59/v60.
- **Numbering note:** upload numbering follows the last *uploaded* version (v60). The
  2026-08-03 local 0.1.146 rebuild below was never uploaded, so it never took a version
  number — `wowborg:v61` is this 0.1.152 build, not that one.
- Built against 0.1.152's game image
  (`sha256:e479e11a4ea45c4ca36bf8d03c283e8f0da1fc26f2feb27d81807fc472efcc4f`), pinned in
  `tools/versions.env`. Canonical Coworld `cow_1acc54b8-80f9-4965-adb5-9325c0472619`.
- **SDK break fixed:** `player/sdk/navmesh/__init__.py` stopped re-exporting, so
  `from player.sdk.navmesh import route_navmesh` now fails. Import moved to
  `player.sdk.navmesh.client` (matching the SDK's own `cli/commands.py`) in
  `wowborg/environment.py`, `tools/build_player.sh`, and `tools/route_lab.py`.
  `build_player.sh`'s sanity check caught this before any episode ran.
- 0.1.152 also adds chat observation fields (`chat_messages`, `chat_input_text`,
  `chat_messages_first_sequence`/`_last_sequence`/`_truncated`, `ChatMessageObservation`),
  so the pre-0.1.152 builds' `extra="forbid"` frame model would reject its frames.
- Hosted `xreq_03d44ab9-1e00-4ec5-9cce-522f17d5a601`, `custom-fresh-start-10x`, 2 episodes:
  **1 completed, 1 failed.**
  - `ereq_e950ddfa-e04c-45cd-8d47-8577fee2d785` — failed `player_error`, WebSocket 1011
    `environment session ended before hello`, no replay. Locally the same startup path dies
    on a game assertion, twice out of two: `session.nim(310) httpAssetFetchesActive() == 0`
    in `finishEnvHostSessionStartup`.
  - `ereq_7e785792-9895-4b3b-bb92-f2301ec84abe` — completed, score 1.0, replay retained.
- **The 0.1.146 falling bug is gone; the character still cannot move.** Across all 84
  observations z holds at exactly the spawn 38.718 and never sinks (0.1.146 fell to 28/18.6).
  But the replay contains **zero movement packets** — not even one `MSG_MOVE_START_FORWARD`
  — and 32 of 36 movement failures are a new gate: *"piloted movement controls settled:
  movement collision readiness timed out"*. Trajectory 0.0 yd, 1 distinct x/y.

## (unnumbered) - accelerated-wow 0.1.146 SDK rebuild (2026-08-03, built + locally run, NEVER uploaded)

- Behavior is unchanged from v59/v60. Rebuilt `linux/amd64` against accelerated-wow
  0.1.146's exact game image
  (`sha256:ab5f989cbdde51c5ae3ca80550365798f780c483927cb54a19c1c624632be01c`), now
  pinned in `tools/versions.env`.
- **Build-contract change:** the game image serves its Python packages from `/app`;
  releases through 0.1.127 used `/usr/local/lib/python3.11/dist-packages`. The
  Dockerfile COPY paths were updated — the build fails outright without it.
- Local image manifest: `sha256:f40218f7a055375e04b1a61d86e2c355d820d2a1ca83f858072c272f8ecd8676`.
- Never uploaded, so it holds no `wowborg:vN` number (see the numbering note above).
  Built solely to isolate whether the 0.1.146 movement failure was our stale SDK copy.
  It is not: a full local exact-image `custom-fresh-start-10x` episode reproduced the
  hosted failure exactly — **1 distinct x/y position, 0.0 trajectory yards**, 144 replay
  movement packets, 33 forward starts, character falling from spawn z 38.718 to 18.6.
- Not uploaded: uploading is pointless until a release lands where the character can
  walk. Rebuild against that release rather than shipping this one.

## v60 - accelerated-wow 0.1.127 SDK rebuild (2026-07-31)

- Version UUID: `99a2c257-bbad-4bb2-9eb5-1eefa8920f06`
  (`wowborg:v60`, uploaded inert; not submitted to a league).
- Behavior is unchanged from v59 (`6df4d2d`). The `linux/amd64` image was rebuilt
  against accelerated-wow 0.1.127's exact game-image SDK
  (`sha256:7262b629ce02ac230ffa3a375c7e1ba8307293a5c94258b87412153cb5d9a5ba`)
  so its strict `AgentFrame` model accepts the release's added observation fields.
- Local image manifest:
  `sha256:25a675ecab81416f781679dd89f3cacf69a1f66df608a4c7ccaad1435c9b8a63`.
- Hosted movement-continuity retest:
  `xreq_d2255259-ee1b-4647-bc71-2ea93133ab54` on accelerated-wow 0.1.127 /
  `custom-fresh-start-10x`. It did not dispatch: 0.1.127 certification failed its
  smoke episode after 3,600 seconds, so the request remained pending without a
  job ID, replay, or results.
- **Retested on accelerated-wow 0.1.146 (2026-08-03):** `xreq_45fa56c4-1b49-4f4c-9a08-f819cd9be62a`,
  episodes `ereq_c0454d48-b8a4-4a31-89f5-3c22d4b653cb` and
  `ereq_635799dd-9c48-4b3e-8ac4-2a63ed7c53fd`. Both completed with score 1.0 and a
  retained replay — but the character never moved: 1 distinct x/y position and 0.0 trajectory
  yards in each, against the v59 baseline's 1,315.8 yd. v60's `AgentFrame` schema is
  byte-identical to 0.1.146's, so this is not a contract mismatch; the unnumbered 0.1.146
  rebuild reproduces it locally. The movement-continuity comparison remains unanswered.
- Full exact-image local `custom-fresh-start-10x` episode completed cleanly with
  score 1.0, 312 observations, 311 intents, a replay, and 1,391.080 yards of replay
  trajectory. Versus the hosted v59 baseline, movement packets fell 4,097 -> 1,376
  (-66.4%): forward starts 239 -> 22 (-90.8%), forward stops 243 -> 25 (-89.7%),
  heartbeats 2,907 -> 600 (-79.4%), turn starts 326 -> 347 (+6.4%), and turn stops
  356 -> 357 (+0.3%). The environment-owned forward continuation is therefore
  working locally; hosted confirmation still waits for a certifiable release.

## v59 - behavior-neutral `/player` progress observer (2026-07-30)

- Version UUID: `fc660a1d-2ec2-45d2-bf9a-e7725d8be246`
  (`wowborg:v59`, uploaded inert; not submitted to a league).
- Built `linux/amd64` from source commit `6df4d2d`. `/env` remains the sole
  gameplay owner with its original policy budget. A read-only `/player` socket
  reports canonical level/XP/displacement samples and sends `done` at the
  owner-standard handoff deadline minus 35 seconds.
- Local image manifest:
  `sha256:7bb7e532a112c2cad42da37719ce9e2ef97df6564f6ef681ff85ade97f052349`.
- Hosted request:
  `xreq_50048077-8098-4ece-a725-460866e70ed4` on certified accelerated-wow
  0.1.124 / `custom-fresh-start-10x`.
- Verdict: 2/2 completed with score 1.0, retained replay, no retry or error.
  The observer emitted 248 / 247 progress reports, ended both sessions with
  `player_session_done`, and reported 1,314.4 / 1,309.9 yards. The replays
  contain 4,115 / 4,097 movement packets.
- Episodes: `ereq_292052b7-c092-404b-91de-c55d29b180dc`
  ([replay](https://softmax-public.s3.amazonaws.com/replays/249d8681-6c05-4fdb-ae14-ae6070d42506.replay))
  and `ereq_422085f1-9ec7-4554-b2ba-9942947e5dc2`
  ([replay](https://softmax-public.s3.amazonaws.com/replays/22800b03-b0b6-4e97-ae71-57a596a48680.replay)).
- Solo overworld replay intentionally has no Godview sidecar; the packaged
  viewer reconstructs movement from the selected POV's recorded client packets.

## v58 - exact policy-budget cap (superseded, 2026-07-30)

- Version UUID: `d21a35e7-f4e6-4247-a658-9df91c900c46`
  (`wowborg:v58`, uploaded inert; not submitted to a league).
- Built from source commit `2f9e751`, image manifest
  `sha256:948568fb2b063886a182d118826c98932cdc496c97497d3cf5a50c12036703b0`.
- Correctly measured the teardown margin from the `/player` handoff, but still
  capped the policy's own budget and therefore changed station selection. Its
  request `xreq_b56f2696-860e-4614-9057-140e55edf5f4` was cancelled before
  evaluation; v59 removes the behavioral confound.

## v57 - `/player` teardown margin (superseded, 2026-07-30)

- Version UUID: `1c645f35-0d52-4fdc-89d3-47f0f921b9d4`
  (`wowborg:v57`, uploaded inert; not submitted to a league).
- Built from source commit `3722172`, image manifest
  `sha256:6f5f99f21b3bd58196c83e6e92cee7a06bf970fb5a4daf7fa11da4c50b7f2dd7`.
- Request `xreq_cef1458f-ad8d-4b00-82d9-ed3debf65aa1` completed 2/2 with score
  1.0 and replay. One episode emitted 153 progress reports, reported 738.4
  yards, retained 2,451 movement packets, and sent clean `done`.
- Superseded because its policy-duration cap changed World Race's time-share
  calculation; v59 moves deadline ownership entirely into the observer.

## v56 - first `/player` progress observer (failed, 2026-07-30)

- Version UUID: `84b7a8c2-fe4e-4013-95a8-cc1375b4727b`
  (`wowborg:v56`, uploaded inert; not submitted to a league).
- Built from source commit `ad891af`, image manifest
  `sha256:db32ed339b6795c82ce666f7f3d3886a4bd6f8ee4b2b9b4b005c5170961ae438`.
- The observer connected and emitted real progress, but wowborg sent no `done`
  before the `/player` deadline. Both jobs failed as `session deadline reached`;
  retry request `xreq_573bf3a4-8983-41ba-a4b4-4eb6ea28d7a7` was cancelled.

## v55 - final 0.1.124 default-catalog artifact (2026-07-30)

- Version UUID: `94c46921-5c5d-4486-b780-1d1d31f43591`
  (`wowborg:v55`, uploaded inert; not submitted to a league).
- Built `linux/amd64` from the same source commit `4d6b434` proven by v54, with
  the normal station catalog restored for future evaluation or submission review.
- Local image manifest:
  `sha256:22b7fe797abb62aecd709a3a076604436ab808c28af48b300fa7ff039953dd4e`.
- Evidence is compositional: v52 proved default-catalog known navigation, while
  v54 proved this exact final runtime code on the held-out course.

## v54 - held-out course with queued-error drain (2026-07-30)

- Version UUID: `d7ffc80c-8c73-468f-9a17-62f8f42d2f54`
  (`wowborg:v54`, uploaded inert; not submitted to a league).
- Built `linux/amd64` from source commit `4d6b434`; the runtime drains consecutive
  typed request errors before accepting the host's newer pushed frame.
- Local image manifest:
  `sha256:4a1247ae9ef4948092a6b169df16d02aea157b6b219105b022aab0f597276e1e`.
- Hosted held-out request:
  `xreq_c0d63be1-8ef3-4192-825a-380e84843f0c` on certified accelerated-wow
  0.1.124 / `custom-fresh-start-10x`.
- Verdict: held-out navigation confirmed in two independent episodes. Both
  completed with score 1.0 and replay, reached `novel-east-rise` in 332.9 /
  341.8 seconds, correctly classified `novel-high-air` as unreachable, and had
  five advancing frame refreshes.
- Episodes: `ereq_ae6a184a-741d-4125-ab8f-e681189f97d1`
  ([replay](https://softmax-public.s3.amazonaws.com/replays/01f12e1a-232f-4908-a12a-7bfcd598071b.replay))
  and `ereq_c47138c9-e9e3-42b7-b4fe-c30725ba21ca`
  ([replay](https://softmax-public.s3.amazonaws.com/replays/26c188cd-6d7b-4969-a579-4777e59e3b21.replay)).

## v53 - held-out course with transient retry (2026-07-30)

- Version UUID: `c210ad97-fc1b-486a-ba5a-6f1f7d4d0d3a`
  (`wowborg:v53`, uploaded inert; not submitted to a league).
- Built `linux/amd64` from source commit `a2636f1` with the preregistered
  held-out Durotar course and v52's single transient no-progress retry.
- Local image manifest:
  `sha256:41102802debe3637f90c70137c9ad58da16536a2c209dbc96d47f2a1fbd12ef7`.
- Hosted request:
  `xreq_62bf9b89-e840-4637-a64a-29c55b143d23` on certified accelerated-wow
  0.1.124 / `custom-fresh-start-10x`.
- Verdict: operational failure. Both episodes exited when a second queued stale
  request error arrived while the runtime was waiting for the current frame.

## v52 - transient no-progress retry (2026-07-30)

- Version UUID: `9d876528-9dba-4945-9498-6bdff9a3625f`
  (`wowborg:v52`, uploaded inert; not submitted to a league).
- Built `linux/amd64` from source commit `a2636f1`; World Race retries a station
  once when its first journey ends specifically as `no_progress`.
- Local image manifest:
  `sha256:80f2a8a759bfa5af04b4ad48a472a2edc64298e1ff644f0e1086e77a7664a8a4`.
- Hosted request:
  `xreq_62dd5b9b-3b83-4950-a9ec-a3ca902d179d` on certified accelerated-wow
  0.1.124 / `custom-fresh-start-10x`.
- Verdict: known challenge completion demonstrated. Both episodes completed with
  score 1.0 and replay; one reached `valley-gate` in 207.7 seconds. The other
  activated `nav_station_retry` on Sarkoth but did not finish before teardown.
- Episodes: `ereq_da240441-192c-4e29-9059-0683d8ca680b`
  ([replay](https://softmax-public.s3.amazonaws.com/replays/6f88d2db-2807-4e26-9551-b204642323d1.replay))
  and `ereq_07a29d3a-afe6-48a4-b605-854e4235f160`
  ([replay](https://softmax-public.s3.amazonaws.com/replays/5b0db2c0-6259-4303-a2b4-707d6a537eae.replay)).

## v51 - held-out course with current-socket refresh (2026-07-30)

- Version UUID: `221a8b82-09f7-4424-9316-caeb20282cbd`
  (`wowborg:v51`, uploaded inert; not submitted to a league).
- Built `linux/amd64` from source commit `15e6a13` with the same untouched
  Durotar course prepared in v49 and v50's current-socket frame recovery.
- Local image manifest:
  `sha256:f3f1bc089da5d0175c67ce26ccf18ad0413aef7356a8a97e2a10648016587256`.
- Purpose: hosted held-out navigation evaluation after v50 clears the recovery
  mechanism gate.

## v50 - current-socket AgentFrame recovery (2026-07-30)

- Version UUID: `04a59594-63fa-477e-86d2-e897917e07ef`
  (`wowborg:v50`, uploaded inert; not submitted to a league).
- Built `linux/amd64` from source commit `15e6a13`; after a stale/deadline
  rejection, the hosted runtime consumes the next pushed frame on the existing
  `/env` connection instead of resetting the Gym lifecycle.
- Local image manifest:
  `sha256:6060e515d0354b9621d24ad7cddadae9d9af6067a710fb31bb4d7ffa4c00ad73`.
- Hosted experiment:
  `xreq_92f74d1c-5a12-49a9-8579-36d435e3d6c2` on certified accelerated-wow
  0.1.124 / `custom-fresh-start-10x`.
- Verdict: frame recovery confirmed, station completion not yet confirmed. Both
  episodes completed with score 1.0 and replay; every refresh advanced, stale
  runs capped at one, and positions changed 264/337 times. Both first reachable
  stations exhausted their no-progress replans during the startup movement stall.

## v49 - held-out Durotar navigation course (2026-07-30)

- Version UUID: `821fe38c-ac0c-4852-ad77-493797f6ad40`
  (`wowborg:v49`, uploaded inert; not submitted to a league).
- Built `linux/amd64` from source commit `34ba007` with a data-only course that
  had never appeared in wowborg code or documentation: east rise, north basin,
  canyon approach, and an intentionally unreachable high-air target.
- Local image manifest:
  `sha256:34288844bb4b36403e51e51d2ab9936c538781d18a67b6468e273127827fdecb`.
- Purpose: held-out hosted evaluation after frame-refresh is established
  independently. This build retains v48's unsuccessful reset-based recovery and
  is superseded before evaluation.

## v48 - stale AgentFrame recovery (2026-07-30)

- Version UUID: `5ef2cfc8-054f-4721-9cdd-503a16d78922`
  (`wowborg:v48`, uploaded inert; not submitted to a league).
- Built `linux/amd64` from source commit `34ba007`; this candidate attempted to
  refresh a stale `AgentFrame` with `VanillaWowEnv.reset()`.
- Local image manifest:
  `sha256:4ddb52f05715c6da3d6268caffaef14f7c3c3c6aa25b85af919704fec645f3c7`.
- Hosted experiment:
  `xreq_2b5eabc9-9a92-4c0a-8055-63f1b77b4796` on certified accelerated-wow
  0.1.124 / `custom-fresh-start-10x`.
- Verdict: rejected. Both episodes ended as `player_error`; reset opened a new
  Gym lifecycle instead of reattaching to the retained session.

## v47 - accelerated-wow 0.1.124 compatibility baseline (2026-07-30)

- Version UUID: `57583ca8-476e-430a-ad3b-bc7c33ce40d0`
  (`wowborg:v47`, uploaded inert; not submitted to a league).
- Built `linux/amd64` from source commit `0a4bc2c` against the certified
  accelerated-wow 0.1.124 contract and deployed game image
  `sha256:ed11e79d...d173a`.
- Adopted the upstream `environment.runtime.episode` module and the consolidated
  `NavmeshRoute` shape. The route lab uses the same compatibility interpretation.
- Local image manifest:
  `sha256:fe23e6c526b05ea88ecae024622322f26bae7442281fdc0ffa54555e011af729`.
- Purpose: establish the first hosted `/env` navigation baseline after the
  game-side session startup fix; no navigation behavior change from v46.

## v46 - canonical `/env` migration (2026-07-29)

- Version UUID: `13b4b697-54d0-4cfe-941a-ed6a3e913211`
  (`wowborg:v46`, uploaded inert; not submitted to a league).
- Replaced every wowborg-owned client path and adapter with the owner-provided
  synchronous Gymnasium contract: `AgentFrame` observations and `AgentAction`
  submissions over hosted `WS /env`.
- Policy image: `linux/amd64`, local manifest
  `sha256:8c3ef0560ba95e024580b0cfe6b42696d006e5f053166d2f8b24f3edbe4cb406`;
  copies only `environment/` and `player/sdk/` from accelerated-wow 0.1.122
  (`sha256:608ac6685...e5e4`). The build rejects historical client binaries.
- Validation before upload: 62/62 wowborg tests; 13/13 declared real-navmesh
  stations; two untouched data-only sequential held-out courses passed 3/3 each:
  scorpid basin → Razor Hill vendor → Razor north field, and south-road west →
  lower canyon west → Barrens gate.
- Hosted runtime request:
  `xreq_52b27d01-17e1-4f5b-860f-cbd096e606bc`, canonical accelerated-wow
  0.1.122 / `custom-fresh-start-10x`.

## v5-v20 - waypoint races: iteration to consistency (2026-07-21/22)

- v3 (`b10f3bb0`): first 0.1.31 contract probe — seam works, no world data (all moves
  failed). v4 (`6242a51a`): VANILLA_WOW_ASSET_SERVICE_URL→--assets fix; random_walk
  102/135 legs, 1,510 yd (replay-confirmed).
- v5 (`purpose=v5-waypoint-race`) → v20 (`purpose=v20-south-rim`): the waypoint_race
  ladder. Key versions: v6 progress-based legs; v8 authored staging chains; v10
  socket-timeout resilience (reconnect + resumable loop); v13 staging hysteresis;
  v16 moving-legs-never-budget-out (zero false DNFs since); v17 course sizing
  (2 near+1 mid+1 far); v19 far-legs-DIRECT (staging retired for long hauls);
  v20 south-rim mid target.
- Endpoint (v19+v20, 8 episodes): 6/8 fully clean, ~1.9 yd/s overall, 740-yd far legs
  in 356-391 s, laps completing. Residual: rare coastal-rock wedge (~1/8); hard tier
  (east field / mesa / NW ridge) quarantined as the future-nav benchmark.


## v3 - nim_control migration (built + fake-server smoked, not yet uploaded)

- Migrated to the game's 0.1.31 policy seam: `action.json` no longer exists upstream;
  the bridge now drives `vanilla_wow.nim_control.v1` (binary-framed local TCP,
  port 41114+slot) — arm external selection via GoalRequest, read EnvironmentFrames
  (observation + dense bindings + factorized action masks), submit one mask-admitted
  FactorizedAction per offered frame, settle via typed ActionSettled. Recon:
  `docs/recon/player-contract-0131-2026-07-21.md`.
- Base image bumped to vanilla_wow 0.1.31 (digest in `tools/versions.env`); player
  images no longer bundle world data — the shim forwards the wrapper's `--assets=<url>`
  to king_richard; session budget derives from KING_NIMROD_SESSION_DEADLINE_SECONDS.
- random_walk is frame-driven now; mask-refused moves fall back to the frame's
  recommended action; death defers to recommended recovery instead of stopping.
- Evidence unchanged (trace/artifact/breadcrumbs); artifact bundle now also carries
  environment-frame.json + decision-audit/leveling-performance/decision-loop-profile
  when present. 0.1.31 caveat: /say text must be in the frame's admitted vocabulary.
- Validated: 57 unit tests (bridge tests run the real wow_sdk client from the pinned
  image's SDK snapshot against a scripted control server); image builds amd64;
  end-to-end container smoke (fake king_richard serving the control socket): goal
  armed, 5+ legs selected/settled, positions tracked, clean teardown.

## v2 - shim adoption: random-point navigator

- Version UUID: `eb6aa13e-4fcd-4037-a443-42fc7ae676d0` (uploaded 2026-07-15,
  `players-wowborg:dev` linux/amd64, tag `purpose=v2-shim-random-walk`).

- Architecture change: our policy now drives the game's bundled Nim client
  (`king_richard --scenario=nim-control`, autonomous planner off) through its file
  bridge, layered on the DEPLOYED reference player image (vanilla_wow 0.1.19 player
  image, pinned by digest in `tools/versions.env`). No Python WoW protocol code in the
  hosted path. Design: `docs/designs/wowborg-v2-shim-adoption.md`.
- New: `shim.py` (supervisor), `bridge.py` (typed seam), `types.py`,
  `policies/random_walk.py` (T0: random 10–20 yd legs with typed movement settlements).
- Observability, three redundant channels: `trace.py` (JSONL + `WOWBORG-TRACE` stdout of
  every observation/intent/typed outcome), `artifact.py` (session-end evidence zip PUT to
  `COWORLD_PLAYER_ARTIFACT_UPLOAD_URL`), and rate-limited `/say` breadcrumbs
  (`ShimBridge.say`) that land inside the CWREPLAY itself.
- Honors the duration budget (`WOWBORG_DURATION_SECONDS`, default 120 s) — the v1
  "never self-terminates" defect is gone by construction (the shim stops the Nim client
  and exits; the base wrapper sends `done`).
- Validated locally: 45 unit tests; image builds amd64; end-to-end container smoke with
  a scripted fake king_richard (12 s, 12 legs, all `reached_target`).
- v1 login-stack modules retained for debugging; no longer the image entrypoint.

## v1 - idle login skeleton

- Version UUID: `6d3b00e5-512b-4c62-95c5-2a83367867b7` (uploaded 2026-07-13, `players-wowborg:dev` linux/amd64).
- Pure Python WoW realmd/world login client.
- Enters the seeded `wow_session.character_name`.
- Idles with periodic `CMSG_PING`.
- Does not decode world state or take gameplay actions.
- Does NOT honor the session's `deadline_seconds` — never self-terminates, so hosted
  episodes always run to the full variant deadline (fix in v2).
- First hosted smoke 2026-07-14: `xreq_23feebad-…`, 4 episodes on `orc-fresh-start`
  (5× self-play), all completed, score 0.0, no crash. Policy logs not retained; login
  success not yet confirmed from artifacts.

---

## Re-fetching episode artifacts

`vanilla_wow_lab/episode_data/` is a local cache (gitignored) and was cleared on 2026-08-04.
Every episode referenced above is re-downloadable from the Observatory by id:

```sh
uv run python .claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py \
  --ereq <owned_ereq_id> --out vanilla_wow_lab/episode_data
```

Only retrieve another player's logs or artifacts when ordinary non-elevated access permits it.
Never use elevated permissions for competitor intelligence. Some ordinary-permission fetches
return only a replay; score that evidence with `tools/movement_report.py <episode_dir>`.

The movement-continuity baseline is `ereq_422085f1-9ec7-4554-b2ba-9942947e5dc2` (v59 on
0.1.124): 4,097 movement packets, 239 forward starts, 243 stops, 326 turn starts, 356 turn
stops, 2,907 heartbeats, 3.8% falling, 1,315.812 replay yards, 249 move actions, 13 movement
failures, 4 stale-frame rejections.
