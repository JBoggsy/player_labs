# wowborg version log

## v421 - keep the full mesa bypass under jump control (2026-08-11)

- Version UUID: `bd2e69d3-73b1-45d4-a95b-5cb0e557d0de` (`wowborg:v421`,
  uploaded inert; not submitted).
- Retains V420's route and cadence, but treats all 20 existing mesa-bypass
  anchors as one continuous steep-terrain band. The exact three-yard anchors
  and 0.25-second inputs are unchanged; jump control no longer turns off
  between narrow or intermittently unsupported surface patches.
- V420's canonical request
  `xreq_b817f9b9-d1f8-4b37-810a-8255198424fb` completed 100/100 with no
  platform failures. Extending the two jumps converted mesa 1 to 2 at 34/34
  and mesa 11 to 12 at 16/16, and two runners reached mesa 20. Those controls
  are retained.
- Failures shifted to the first later non-jump anchors rather than disappearing:
  12 runners ended at mesa 2, six at mesa 17, four at mesa 18, and three at
  mesa 12. This demonstrates one continuous terrain band rather than two
  isolated edges. No runner reached the Great Lift.

## v420 - continue jumping through each mesa landing (2026-08-11)

- Version UUID: `613dc641-6879-4535-aeac-7f86a1844e2f` (`wowborg:v420`,
  uploaded inert; not submitted).
- Retains V419 and extends its two mesa-lip jumps through exactly the following
  anchors: mesa 1--2 and mesa 11--12 now use continuous precision jumps. This
  keeps the avatar under jump control until the acquired surface settles; all
  later mesa anchors and route behavior are unchanged.
- V419's canonical request
  `xreq_66e044bb-a563-4c90-aa4c-533a8b17f1ab` completed 100/100 with no
  platform failures. The two lip classifications worked: direct 343 to mesa 1
  converted at 22/22 versus V418's 7/16, and mesa 10 to 11 converted at 6/6
  versus 3/6. Retained in active source.
- The first non-jump target after each lip then exposed the airborne acceptance:
  14 runners ended at mesa 1 while targeting mesa 2, and three ended at mesa
  11 while targeting mesa 12. No runner reached the Great Lift. Extending each
  jump by one authored three-yard anchor addresses that same landing state
  without widening acceptance or changing the rest of the mesa.

## v419 - jump the two false mesa lip acquisitions (2026-08-11)

- Version UUID: `b1cd5427-d5b7-4e21-bd67-e3717cbd557f` (`wowborg:v419`,
  uploaded inert; not submitted).
- Retains V418's direct supported landing jump. Marks only mesa-bypass anchors
  1 and 11 as steep terrain, applying the established continuous 0.25-second
  jump control and climb-edge acceptance at those two lip acquisitions. All
  other mesa anchors and route behavior are unchanged.
- V418's canonical request
  `xreq_2d68d970-68eb-4278-bc09-3b3a91ef221f` completed 100/100 with no
  platform failures. The new ledge jump converted ledge anchor 2 to the
  supported landing at 23/23 and reached direct 339 at 22/23, resolving the
  prior variable-airborne landing failure. Retained in active source.
- The next two death signatures are identical false-edge misses. Nine of 16
  direct-343 runners ended before mesa anchor 1, falling from z84 to z-43.
  The fastest mesa runner reached anchor 10 at 227 seconds; only three of six
  anchor-10 arrivals acquired anchor 11 after overshooting its lip and falling
  to z25 before death. No runner reached the Great Lift.

## v418 - target the supported landing before takeoff (2026-08-11)

- Version UUID: `b8a942a4-7145-4fb5-8a04-350ad5791369` (`wowborg:v418`,
  uploaded inert; not submitted).
- Retains V415's upstream route and V417's measured touchdown center. Changes
  the ledge jump itself: after exact ledge anchor 2, skips direct 338 and
  continuously jumps southeast to the exact landing anchor at
  `(-5759, -1876, z86.1)`. The jump now acquires its safe heading before
  takeoff rather than trying to correct variable airborne momentum afterward.
  No other route behavior changes.
- V417's canonical request
  `xreq_d1afd3ae-64be-45ee-bbb5-db29b3a67cf8` completed 100/100 with no
  platform failures, but the post-direct-338 correction was rejected: only
  10/20 direct-338 runners acquired the landing anchor and eight reached
  direct 339. No runner reached the Great Lift.
- V416 and V417 together show that changing a target after direct 338 cannot
  reliably correct the already-airborne trajectory. The established ledge-2
  origin and measured stable touchdown are 63 yards apart at nearly equal
  elevation; targeting that chord directly removes the unstable intermediate
  acquisition.

## v417 - center the landing anchor on observed touchdowns (2026-08-11)

- Version UUID: `7b1f2f2e-d4c9-479f-8ba5-758648cdbc8c` (`wowborg:v417`,
  uploaded inert; not submitted).
- Retains V415 and V416's explicit landing-guidepoint structure, but moves the
  anchor from `(-5734.6, -1870.6, z86.1)` to
  `(-5759.0, -1876.0, z86.1)`. This is the median first stable-ground position
  of V416's 19 observed direct-338 landings and remains aligned with the
  south-east airborne momentum. No other route behavior changes.
- V416's canonical request
  `xreq_67f70bdd-947b-40c5-bf73-4a4e19742e23` completed 100/100 with no
  platform failures, but the original anchor was rejected: only 17/28
  direct-338 runners acquired it and 14 reached direct 339, no improvement
  over V415's 22/38 direct-339 conversion. No runner reached the Great Lift.
- The failed V416 anchor pulled toward `y=-1870.6` while runners still carried
  southward momentum. Successful touchdowns clustered at x -5772..-5756 and
  y -1881..-1868, with medians `(-5759, -1876)`; failures commonly turned
  north and fell to the false lower layer before landing.

## v416 - land due east before turning toward direct 339 (2026-08-11)

- Version UUID: `d12ec866-5529-4ff0-bec9-8322d1095b32` (`wowborg:v416`,
  uploaded inert; not submitted).
- Retains V415. Inserts one exact terrain-tight landing anchor at
  `(-5734.6, -1870.6, z86.1)` between direct 338 and direct 339. The runner
  now holds its eastbound jump heading until the known landing surface, then
  turns northeast on stable ground. No cadence, acceptance, or other route
  behavior changes.
- V415's canonical request
  `xreq_871b8a00-db90-4d23-b820-3376c47f7677` completed 100/100 with no
  platform failures. The direct-329 lower-surface bypass converted 39/43
  runners to direct 336, versus V414's 14/36 conversion to direct 330, and is
  retained.
- That additional volume isolated the next failure: 38 runners reached direct
  338, but 16 ended there. Successful traces held `y≈-1871`, landed near
  `(-5735, -1871, z86)`, and continued; failed traces began turning north
  toward distant direct 339 while still above z107 and fell through the ledge
  seam. The new anchor is the successful traces' observed landing point.

## v415 - follow the real lower surface after direct 329 (2026-08-11)

- Version UUID: `fb0524be-ef78-4e92-bf19-187489d64719` (`wowborg:v415`,
  uploaded inert; not submitted).
- Retains V414. After direct 329, targets supported direct 336 directly rather
  than the false upper-layer direct 330--335 sequence. The existing clear
  stride safely descends from the z129 plateau to the real z86 surface; direct
  336 is about 35 yards north on that same surface at z87. No cadence,
  acceptance, or other route behavior changes.
- V414's canonical request
  `xreq_a1f8cd63-c5b2-4f64-ae6b-38c39481ba33` completed 100/100 with no
  platform failures. The new entry converted direct 307 to ridge 5 at 52/52
  and reached ridge 21 with 44 runners, versus V413's 45/66 conversion to
  ridge 1 and 43 ridge-21 arrivals. Retained in active source.
- The downstream false-layer failure reproduced at scale: 36 runners reached
  direct 329, only 14 reached direct 330, and 22 episodes ended at direct 329.
  Those traces safely fell to the stable z86 surface near
  `(-5863, -1900)` but could not satisfy direct 330's false z129 target before
  the deadline. Successful old-path runners spent about 19 seconds on that
  leg before the remaining descent sequence.

## v414 - carry direct-307 momentum onto the ridge shelf (2026-08-11)

- Version UUID: `c7c513c6-dccc-4c95-ab24-a615cd429038` (`wowborg:v414`,
  uploaded inert; not submitted).
- Retains V413 except for the direct-307 ridge entry. After direct 307, skips
  direct 308, direct 309, and ridge anchors 1--4, and continuously jumps to
  exact ridge anchor 5. This turns the runner southeast onto the descending
  shelf instead of first carrying it east to direct 309 and then demanding an
  immediate southwest reversal at the cliff lip.
- V413's canonical request
  `xreq_e6eee008-02cd-497b-8697-090dfccb3f2a` completed 100/100 with no
  platform failures. It produced the best absolute throughput so far: 70
  direct-275 arrivals, 67 direct-296 arrivals, 45 ridge-1 arrivals, and 43
  complete ridge crossings. The remaining local losses clustered at direct
  308 (8), direct 309 (11), and the reversal before ridge 1.
- Trace geometry supports this chord: direct 307 is typically accepted around
  `(-6247, -2292, z131)` with eastward momentum, while ridge 5 is about 21
  yards southeast at `(-6229, -2303, z137)`. It is the first established
  lower-shelf anchor aligned with that momentum. No cadence or acceptance
  radius changes.

## v413 - ground the direct-309 ridge reversal (2026-08-11)

- Version UUID: `beb5ff43-cf5f-46e9-bcae-791a11dfd3ce` (`wowborg:v413`,
  uploaded inert; not submitted).
- Retains V412. Restores source-route direct 308 instead of skipping 307 to
  309, and makes direct 308 exact/terrain-tight like direct 309. The approach
  is now two short 0.25-second acquisitions before reversing toward ridge 1,
  rather than one 18-yard chord. No acceptance radius is broadened.
- V412's canonical request
  `xreq_5c241fc7-da0d-4bc8-8452-788a0dbd1bc1` produced 100 completed episodes
  and zero failures (the request status readback briefly lagged despite all
  counters being terminal). Direct 293 to 296 remained 54/54, direct 309 was
  reached by 45/53, and ridge-21 arrivals rose to 32.
- The remaining transition deaths share one state: direct 309 is accepted near
  `(-6225, -2288, z139)` while northeast airborne momentum persists. Ridge 1
  is only 3.6 yards southwest. Turn-only inputs rotate the character but do
  not cancel that momentum, and nine runners continued northeast off the edge.
  Direct 308 is the existing intermediate ground anchor at
  `(-6229.5, -2290.1, z139.2)`.

## v412 - retain only the safe direct-296 edge jump (2026-08-11)

- Version UUID: `96f1ed79-ff30-4f68-9596-8cca4e5d5b2f` (`wowborg:v412`,
  uploaded inert; not submitted).
- Retains V410's landing-to-clear transition and V411's direct-296 steep jump.
  Removes direct 309 from the steep class, restoring its prior exact non-jump
  control. No other behavior changes.
- V411's canonical request
  `xreq_ff23015e-03a4-4434-bd62-a37321aa8d62` completed 100/100 with no
  platform failures. Direct 293 to 296 improved from 33/50 in V410 to 56/56,
  and direct 307 to 309 improved from 25/30 to 56/56. Ridge-21 arrivals rose
  from 15 to 29.
- The direct-309 climb-edge acceptance was unsafe: 25 runners arrived there
  and then died before ridge 1, versus four such deaths in V410. Direct 296
  had no corresponding death cluster. This version preserves the independently
  clean edge fix and rejects only the harmful one.
- Canonical request `xreq_5c241fc7-da0d-4bc8-8452-788a0dbd1bc1` retained the
  direct-296 conversion at 54/54 and produced 32 ridge-21 arrivals. Retained as
  the active baseline for V413.

## v411 - jump the two remaining northern false edges (2026-08-11)

- Version UUID: `b84d9d94-c105-474d-84f1-1236829632c3` (`wowborg:v411`,
  uploaded inert; not submitted).
- Retains V410's safe landing-to-clear transition. Adds direct 296 and direct
  309 to the existing steep-guidepoint class, giving those two false-surface
  edges continuous 0.25-second jumps and the established eight-yard
  climb-edge acceptance. No other route or cadence changes.
- V410's canonical request
  `xreq_4c15d3fe-f5b8-4732-803f-8c391ed2ce90` completed 100/100 with no
  platform failures. All three ledge-2 runners reached direct 338, 339, and
  343. Each direct-339 leg safely switched from 13 short landing pulses to 12
  clear strides and completed in about 8.8 seconds versus V408's 10.8; none
  reached the Lift because they entered the late route at 246--258 seconds.
- Upstream, 17 of 50 direct-293 arrivals ended there while targeting direct
  296: traces repeatedly fell from z121 to the false lower layer. Five more
  runners died after direct 307 while targeting exact direct 309, falling from
  z126 to z14. These are geometric edge failures, not combat or platform
  failures, and use the same short-jump control already proven at nearby steep
  anchors.
- Rejected as a combined change after canonical evaluation: direct 296 is
  retained, but direct 309's broad climb-edge acceptance caused 25 immediate
  pre-ridge deaths and is removed in V412.

## v410 - resume clear strides after the mesa landing (2026-08-11)

- Version UUID: `fbf17aea-d0c5-4369-bb06-03579a3046c2` (`wowborg:v410`,
  uploaded inert; not submitted).
- Restores V408's route and bounded-jump cadence after rejecting V409. On the
  direct-339 leg only, retains 0.25-second pulses while the runner is more than
  three vertical yards from the supported z87 surface, then resumes the
  existing 1.5-second clear-road stride for the remainder of the 189-yard mesa
  chord. The false-layer mesa-bypass anchors remain terrain-tight.
- V408 proved that the short pulse lands this jump safely and that the complete
  chord is supported, but its successful runner spent 10.8 wall seconds and 85
  actions reaching direct 339. V405 proved that starting a clear stride while
  still 27 yards above the target is fatal. The vertical gate preserves the
  landing fix while removing precision cadence after it has done its job.
- Canonical request `xreq_4c15d3fe-f5b8-4732-803f-8c391ed2ce90`
  completed 100/100 with no platform failures. Three runners exercised the
  gate; all three survived through direct 343. The direct-339 leg used 25
  actions and about 8.8 wall seconds in each trace. Retained in active source.

## v409 - accelerate bounded jump bands (2026-08-11)

- Version UUID: `bf8c8a2c-5722-4549-bc92-230713dbac1b` (`wowborg:v409`,
  uploaded inert; not submitted).
- Separates the already-classified bounded straight-jump bands from genuinely
  tight terrain control. Direct 141--215 and 258--275 now use the existing
  0.75-second Traverse pulse instead of an unconditional 0.25-second pulse;
  tight ledges, ridge anchors, mesa bypasses, exact descents, and hazard
  evasion retain their current precision cadence.
- V408's canonical request
  `xreq_282020d3-7511-4f2a-a20d-f0f4caa46708` completed 100/100 with no
  platform failures. Both ledge-2 arrivals reached direct 338. One landed,
  reached direct 339 and 343, traversed all 20 mesa-bypass anchors, and reached
  direct 359: the first complete crossing of the false-surface ledge/mesa
  barrier. The other fell after direct 338.
- The successful runner reached direct 359 at 268.9 seconds and then received
  the fixed 270-second `scoring_logout`; it did not reach the Great Lift. Its
  bounded jump bands consumed about 51 wall seconds, making their conservative
  cadence the largest isolated throughput cost that can be changed without
  altering route geometry.
- Rejected after canonical evaluation. Request
  `xreq_0818d49d-e666-47d6-aae6-a60a125a9c92` completed 100/100 with no
  platform failures, but deaths rose from 33 to 74 and direct-275 arrivals
  fell from 63 to 7. Of 55 runners reaching direct 258, 48 failed before
  direct 275, commonly falling from the physical ridge after a 0.75-second
  pulse. The longer bounded-jump cadence also did not improve the sole late
  runner's milestone times. Active source restores V408's 0.25-second control.

## v408 - land the ledge jump with short road pulses (2026-08-11)

- Version UUID: `c973268c-b0fa-4651-b0e0-db1c40e197dd` (`wowborg:v408`,
  uploaded inert; not submitted).
- Removes the rejected v406/v407 airborne-settle branch and marks direct 339
  as terrain-tight. After the successful jump to direct 338, road movement is
  therefore split into 0.25-second pulses instead of the fatal 1.5-second
  open-road stride; all other route controls remain unchanged.
- V407's canonical request
  `xreq_16c02db5-e7cb-467c-a10e-295a080078e1` completed 100/100 with no
  platform failures. Three runners reached ledge anchor 2, but none entered
  the settle branch: two episodes ended just as they came within the trigger
  radius and one ended mid-jump with a typed action timeout. No runner reached
  direct 338 or the lift.
- V405 already isolated the landing failure: direct 338 was accepted at z114,
  then the first 1.5-second stride fell to z97 while moving 15 yards and the
  second fell to z38 before death. Short pulses reuse the established
  terrain-tight control and avoid that irreversible airborne stride.

## v407 - settle the ledge jump on the locomotion clock (2026-08-11)

- Version UUID: `c22ecc3a-0249-4e6a-91c9-c00a64034ef9` (`wowborg:v407`,
  uploaded inert; not submitted).
- Replaces v406's direct-338 simulation `wait` with a zero-input
  `move_vector`. The latter advances WoW locomotion and gravity while
  commanding neither forward nor lateral motion; all route targeting remains
  unchanged.
- V406's canonical request
  `xreq_9b030fed-b5ad-4072-b377-37c0ac196535` completed 100/100 with no
  platform failures. Its sole ledge-2 arrival emitted 804 airborne-settle
  pulses without reaching direct 338; none reached direct 339 or the lift.
- The settle trace remains bit-identical at
  `(-5776.848, -1872.094, 113.587)` for all 804 accepted wait actions. Hosted
  `wait` freezes this movement state, so it cannot be used to let gravity land
  the runner.

## v406 - settle the ledge jump before resuming the road (2026-08-11)

- Version UUID: `9c4934d9-f33b-4ab1-9ece-d0721557e66a` (`wowborg:v406`,
  uploaded inert; not submitted).
- Retains v405's successful ledge-2 to direct-338 jump. At that one landing,
  when the runner is within eight planar yards but remains more than ten yards
  above the target, submits wait pulses until gravity settles the character;
  the ordinary road leg resumes only after the landing is physically close.
- V405's canonical request
  `xreq_e66c3e73-d7dc-4841-a11e-70e1fb84c092` completed 100/100 with no
  platform failures. All four ledge-2 arrivals crossed to direct 338, but all
  four died before direct 339; none reached direct 343 or the Great Lift.
- The common trace accepts direct 338 at z114 over its z86 target, then the
  first 1.5-second non-jump road pulse carries the falling runner to z97 and
  the second to z38 before death. Settling in place removes that post-jump
  horizontal overshoot without changing other terrain jumps.

## v405 - jump the unsupported northern ledge chord (2026-08-11)

- Version UUID: `2efc5d49-39e3-44a4-9b89-9a50bd8dd3e6` (`wowborg:v405`,
  uploaded inert; not submitted).
- Retains v404's successful lower-to-upper ridge jump. After exact ledge
  anchor 2, skips the unsupported anchor-3/direct-337 chord and applies one
  continuous eastward terrain jump to direct 338, where the stable mesa
  resumes 52 yards away.
- V404's canonical request
  `xreq_7fde8541-8e9b-43cd-b82c-9d392ceba21b` completed 100/100 with no
  platform failures. Of 19 lower anchor-21 arrivals, all reached anchor 43,
  18 reached upper anchor 70, and 17 completed anchor 81 and direct 312. Four
  reached direct 332 and ledge anchors 1--2; none reached ledge anchor 3 or
  direct 337.
- A common full-health trace walks east from ledge anchor 2 while its z falls
  from 85 to 12, then dies before anchor 3. Direct 338 is aligned east of the
  ledge and rejoins the supported z86 mesa, so the jump does not release over
  the false physical surface.

## v404 - correct v403's uploaded module entrypoint (2026-08-11)

- Version UUID: `061df677-96c6-4461-8ee8-e3ff30db1bca` (`wowborg:v404`,
  uploaded inert; not submitted).
- Byte-identical route code to v403, uploaded with the valid
  `python -m wowborg` entrypoint. The prior upload mistakenly used
  `python -m wowborg.main`; that module defines `main()` but does not invoke
  it, so the policy exited without connecting.
- V403's request `xreq_9b2a0c56-5887-4be0-8bdf-b4543f915822` is invalid as
  gameplay evidence: its terminal jobs uniformly reported `player_error`,
  "player did not connect before the configured startup deadline," with no
  replay, results, or policy artifacts.

## v403 - land the shelf jump along the supported upper ridge (2026-08-11)

- Version UUID: `09a1df9b-6f89-4031-98ee-00f8a7660e9f` (`wowborg:v403`,
  uploaded inert; not submitted; invalid entrypoint, never connected).
- Retains v402's reliable anchor-21 to 43 jump, but replaces the premature
  anchor-54 target with a northward jump directly to upper-ridge anchor 70.
  The target turns momentum along the supported upper ridge and resumes exact
  walking at anchor 71.
- V402's canonical request
  `xreq_cae98785-5e75-408b-aa65-110c7ee02de0` completed 100/100 with no
  platform failures. All 22 anchor-21 arrivals reached anchors 43 and 54, but
  none reached anchor 55 or direct 312; 21 of those 22 runners then died.
- The common trace declares anchor 54 arrived eight yards early while still
  airborne around z139 over its z101 target. Releasing the continuous jump
  there carries the runner east to unsupported z57 terrain. Anchor 70 lies
  north on the real upper ridge, so the jump remains active through the false
  arrival and its landing momentum follows supported ground.

## v402 - chain the aligned jump through the second shelf gap (2026-08-11)

- Version UUID: `09caae6b-3321-4ad6-80b6-a19cee3ba585` (`wowborg:v402`,
  uploaded inert; not submitted).
- Retains v401's anchor-21 to 43 jump, then skips false anchors 44--53 and
  applies the same continuous eastward jump toward anchor 54, about 24 yards
  farther. Ordinary exact climbing resumes at anchor 55.
- V401's canonical request
  `xreq_aadb2e3a-81bf-48b0-b1e3-4f6f563b9403` completed 100/100 with no
  platform failures and 34 traces containing a death. All 19 anchor-21
  arrivals reached aligned anchor 43; two reached anchors 44--48, and one
  reached 49--53. None reached direct 312 or the Great Lift.
- The aligned first jump removed v400's southward reversal but still ends
  before stable ground: 16 traces ended with no frame toward anchor 44 and one
  stalled there. Anchor 54 continues east on the same line and is 24 yards
  beyond anchor 43, so the second jump extends the same attributable mechanic
  through the remaining false patch.

## v401 - jump through the false shelf without reversing momentum (2026-08-11)

- Version UUID: `81ab1c87-8fcf-443c-8636-d5352edeb8dc` (`wowborg:v401`,
  uploaded inert; not submitted).
- Retains v400's localized continuous jump after lower anchor 21, but aims it
  directly east-southeast at anchor 43 instead of the airborne anchor 28. The
  39-yard target aligns with the next route leg, so the policy does not
  reverse over the unsupported patch.
- V400's canonical request
  `xreq_de4d0c97-83e7-443e-b599-00fa159ec274` completed 100/100 with no
  platform failures and 34 traces containing a death. All 19 anchor-21
  arrivals activated the skip and reached anchor 28, but 18 stalled toward
  anchor 29; only one reached anchors 29--32. None reached direct 312 or the
  Great Lift.
- The common trace reaches anchor 28 while airborne, then retained southward
  momentum carries it roughly 20 yards to y=-2376 while steering back toward
  anchor 29. It repeatedly falls and server-corrects there. Anchor 43 lies 39
  yards east-southeast of anchor 21 and the subsequent route continues east,
  removing that midair reversal.

## v400 - jump the false lower-shelf navmesh patch (2026-08-11)

- Version UUID: `c539ad07-ab95-4575-ae26-0e52af7ba064` (`wowborg:v400`,
  uploaded inert; not submitted).
- Retains v399's lower-shelf bypass, but after exact anchor 21 skips false
  anchors 22--27 and applies the existing continuous terrain-jump primitive
  only toward anchor 28, a 16-yard span. Ordinary exact walking resumes
  immediately afterward; global steering is unchanged.
- V399's canonical request
  `xreq_a0dfe6ad-830b-4ca6-939e-043b684a854d` completed 100/100 with no
  platform failures and 33 traces containing a death. Of 37 direct-309
  arrivals, 27 crossed lower-route anchors 6--12, 26 crossed 13--18, 21
  reached 20, 20 reached 21, 12 reached 22, and only three reached 23--25.
  None reached direct 312 or the Great Lift.
- Failure traces at anchor 23 remain full-health and non-combat but fall
  repeatedly through fixed x/y around `(-6215.45, -2347.04)` while the server
  corrects z back near 94. This is an unsupported navmesh patch, not a normal
  descent or combat failure; anchor 28 is 16 yards across it on the east shelf.

## v399 - bypass the ridge lip on the lower southern shelf (2026-08-11)

- Version UUID: `89d55041-79d7-4c9d-b696-6220014f9ed5` (`wowborg:v399`,
  uploaded inert; not submitted).
- Replaces v398's still-lethal plateau approach with an 81-anchor, 278-yard
  real-navmesh route that approaches west of the ridge lip, descends onto the
  broad lower shelf, crosses east, and climbs gradually to direct 312. It
  costs roughly ten seconds versus the original chord.
- V398's canonical request
  `xreq_d9c5a3f2-003f-41c1-a2f2-66ecb04ff29a` completed 100/100 with no
  platform failures and 30 traces containing a death. Thirty-five reached
  direct 309; 31 reached ridge anchors 1--6, 26 reached 7, 15 reached 8, four
  reached 9, and one reached 10. None reached direct 312 or the Great Lift,
  proving the shared southern-plateau approach—not only v397's hairpin—is the
  active failure surface.
- Three fresh pinned-navmesh sections connect direct 309 to the lower shelf,
  traverse it, and rejoin direct 312 without using the failed lip. The full
  route is 278 yards and every returned centerline point is retained exactly.

## v398 - round the southern ridge on a continuous plateau loop (2026-08-11)

- Version UUID: `b84c445f-fe9e-4d41-afea-2eac2a092650` (`wowborg:v398`,
  uploaded inert; not submitted).
- Replaces v397's 81-yard out-and-back arc with a 140-yard, 43-anchor
  supported plateau loop whose turns remain continuous. It adds about four
  seconds versus the original ridge chord and changes no combat, hazard,
  stealth, or general steering behavior.
- V397's canonical request
  `xreq_7cce9c31-99c0-442c-a140-f509ce22c7bc` completed 100/100 with no
  platform failures and 33 traces containing a death. Of 26 direct-309
  arrivals, 21 reached arc anchors 1--6, 18 reached 7, eight reached 8, and
  two reached 9--10; none reached direct 312 or the Great Lift.
- The failure trace shows the short arc's two navmesh sections form a
  180-degree turn at anchor 10 on the ridge lip. Even turn-in-place actions
  retain southward movement long enough to fall. Three fresh real-navmesh
  sections instead round the broad plateau through x=-6175 before rejoining
  direct 312, avoiding the reversal entirely.

## v397 - route around the narrow ridge on a short southern arc (2026-08-11)

- Version UUID: `dad122cf-a6c7-4659-a85f-8b27ba34792b` (`wowborg:v397`,
  uploaded inert; not submitted).
- Replaces the failed direct-309--312 ridge centerline with a fully pinned
  26-anchor southern arc and makes the direct-309 join exact. Removes v396's
  rejected ridge-only heading-control machinery.
- V396's canonical request
  `xreq_5ac726a0-9908-4f8a-ab3a-c86dd4f4502d` completed 100/100 with no
  platform failures. Of 36 direct-309 arrivals, 27 reached ridge anchor 1, 15
  reached anchor 2, one reached anchor 3, and none reached anchor 4 or direct
  312. There were 51 deaths and no Great Lift arrival, decisively rejecting
  turn-in-place heading alignment on the three-yard ridge anchors.
- Fresh pinned-navmesh queries found a supported southern arc in two sections:
  27.2 yards from direct 309 to `(-6216.53, -2312.53, 148.13)`, then 54.1
  yards to direct 312. At 81.3 yards total, it adds only about 36 yards versus
  the lethal chord while avoiding the narrow ridge entirely.

## v396 - align heading before moving on the dense ridge (2026-08-11)

- Version UUID: `9f606363-9127-4cf9-8a91-a334af0f2964` (`wowborg:v396`,
  uploaded inert; not submitted).
- Retains v395's dense exact ridge, but replaces its binary full-strength
  lateral correction with a ridge-only five-degree heading contract: turn in
  place outside five degrees, then move straight with exact quarter-second
  pulses. The proven post-staircase ledge keeps its existing two-degree strafe
  behavior; all other steering keeps the 45-degree turn and 22.5-degree strafe
  deadbands.
- V395's canonical cohort published 98 traces with no platform failures. The
  later correction worked: all three runners reaching ridge anchor 6 crossed
  anchors 7--14 and rejoined direct 312. But full-strength strafe overcorrected
  the three-yard early anchors, causing 7 deaths toward anchor 3, 8 toward 4,
  3 toward 5, and 6 toward 6. One runner reached direct 332; the mesa did not
  activate. There were 45 deaths in the 98 recovered traces and no Great Lift
  arrival.

## v395 - hold the shallow ridge centerline laterally (2026-08-11)

- Version UUID: `95871773-3bbd-4be6-8e4d-c64ca1d1a6e9` (`wowborg:v395`,
  uploaded inert; not submitted).
- Retains v394's exact dense ridge and applies the existing two-degree lateral
  strafe deadband only to its 14 anchors. The ordinary 22.5-degree deadband
  remains everywhere else except the already proven post-staircase ledge.
- V394's canonical request
  `xreq_63a203fe-b5bc-4c86-8fb8-56a5417e3852` produced 100 traces with no
  platform failures. Twenty-nine reached direct 309 and ridge anchors 1--2,
  19 reached anchor 3, 12 reached 4, eight reached 5, three reached 6, and one
  reached 7. That runner crossed anchors 1--7 in about 1.5 seconds at full
  health, then the shallow turn toward anchor 8 stayed inside the ordinary
  strafe deadband: y drifted from -2284 to -2241 while z fell from 136 to 13,
  causing death. There were 47 deaths and no Great Lift arrival; the later
  mesa did not activate.

## v394 - follow the direct-309--312 ridge centerline exactly (2026-08-11)

- Version UUID: `4fa1b38f-360b-427c-a814-e52e4f3cca97` (`wowborg:v394`,
  uploaded inert; not submitted).
- Retains v393's complete upper-mesa repair and replaces source direct 310/311
  with the full 14-point pinned-navmesh centerline from direct 309 to 312. All
  ridge anchors use exact quarter-second control before rejoining source direct
  312; no hazard, combat, or later-route behavior changes.
- V393's canonical request
  `xreq_88068622-c7ff-4e4a-8045-d36d4b6725e9` completed 100/100 with no
  platform failures. Forty reached direct 309 and 38 reached restored 310, but
  2 died toward 310, 16 died toward 311, and 6 died toward 312. Only two
  reached direct 332 and none reached 338, so the mesa change did not activate.
  There were 54 deaths and no Great Lift arrival. The pinned ridge query shows
  the omitted centerline points at roughly three-yard spacing throughout the
  lethal section.

## v393 - keep the upper-mesa bend fully dense (2026-08-11)

- Version UUID: `e590cf17-7c69-4d34-95c3-5dc86c703073` (`wowborg:v393`,
  uploaded inert; not submitted).
- Retains v392's validated direct-343 join and first eight upper-mesa anchors,
  then restores the nine omitted three-yard navmesh points across the bend and
  through the direct-355 rejoin. All 20 mesa bypass anchors remain exact and
  terrain-constrained; upstream behavior is unchanged.
- V392's canonical request
  `xreq_a045ea03-0596-442a-bac2-9c422476df0a` completed 100/100 with no
  platform failures. The ridge repair activated strongly: all 41 direct-309
  arrivals reached restored 310, 27 reached 311, and 19 reached 312, eliminating
  the prior 18-run death cluster on the skipped chord. One downstream runner
  crossed exact direct 343 and mesa bypass anchors 1--8 at full health. The
  coarse selection then omitted three navmesh points before anchor 9; the
  runner fell immediately at that bend and died. There were 51 deaths and no
  Great Lift arrival.

## v392 - retain supported terrain at the ridge and upper-mesa joins (2026-08-11)

- Version UUID: `ee4109ed-3537-4aef-8ee3-53d7e5a69159` (`wowborg:v392`,
  uploaded inert; not submitted).
- Makes two independently traced corrections within the route-geometry
  component. It removes the direct-309 to 312 skip so source anchors 310/311
  retain the supported ridge. At the later mesa, it makes direct 343 exact,
  restores the four omitted three-yard navmesh approach anchors, and applies
  exact quarter-second control across all 11 upper-mesa bypass anchors.
- In v391's first 100-episode cohort, 18 full-health, non-combat runners died
  on the 309--312 chord. The pinned navmesh reports a 14-point supported ridge
  corridor descending smoothly from z138.8 to z125.4 through source 310/311.
- V391's repeat request
  `xreq_1dd39175-921a-471e-a09b-a36bac83ac18` completed 100/100 with no
  platform failures. Fifty-six reached direct 275, 53 reached restored 276, 52
  reached 277/293, 41 reached 307/309, 18 survived to 312, eight reached 332,
  four reached 337, and one reached 338--343. That runner accepted direct 343
  off the intended join, then a 1.5-second stride toward the prematurely
  coarsened first bypass anchor crossed the edge and fell. There were 61 deaths
  and no Great Lift arrival.

## v391 - stay on the supported upper mesa after direct 343 (2026-08-11)

- Version UUID: `f3777fde-b677-46b2-b294-e30c24fca4a2` (`wowborg:v391`,
  uploaded inert; not submitted).
- Replaces the inactive source direct-344--354 lower layer with seven anchors
  from a fresh pinned-navmesh query that remain on the supported z84--88 upper
  mesa and rejoin the existing route at direct 355. Removes the rejected
  lower-layer jump, exact-descent, and skip classifications; upstream behavior
  is unchanged.
- The pinned 0.1.209 navmesh reports a 78.2-yard, 27-point upper-surface
  corridor from direct 343 to direct 355. Its height remains z84.41--87.71,
  while the source corridor dives to z52 at direct 348 before climbing back to
  z87 at direct 355. A direct query from 343 to the Great Lift basin has no
  path, consistent with the source route's accidental layer switch.
- V390's two canonical cohorts completed 100/100 each with no platform
  failures. The first never activated direct 338. The repeat reached 338--343
  once; its jump toward 344 moved horizontally but repeatedly fell through and
  server-corrected around the false lower layer, never landing. Across the
  repeat, 58 reached direct 275, 57 reached restored 276, 56 reached 277/293,
  and one reached 338--343. There were 55 deaths and no Great Lift arrival.

## v390 - chain jumps down the direct-344--348 shelf sequence (2026-08-11)

- Version UUID: `a3461781-a72f-42fd-8ee5-1d4ddd5dc13c` (`wowborg:v390`,
  uploaded inert; not submitted).
- Retains v389's dense exact ramp anchors and applies the existing one-shot
  jump primitive to direct 344 through 348. Each leg gets one aligned jump,
  then returns to exact quarter-second steering; no upstream route, hazard,
  combat, or stealth behavior changes.
- V389's canonical request
  `xreq_335d0e05-8428-44fe-b90b-511971d78406` completed 100/100 with no
  platform failures. Sixty-two reached direct 275, 60 reached restored
  276/277/293, 11 reached 332/333, eight reached 336, six reached 337, four
  crossed through 343, and one reached exact 344. The other three fell while
  walking toward 344; the direct-344 arrival fell and died toward 345. The
  pinned navmesh cannot connect direct 343 to the Great Lift basin and reports
  the local 344--348 corridor partial, confirming discrete physical shelves
  rather than one supported walking ramp. There were 66 deaths and no Great
  Lift arrival.

## v389 - control the complete direct-344--348 descent precisely (2026-08-11)

- Version UUID: `3accbe7d-d4fa-47fd-87c7-46dc17854c7e` (`wowborg:v389`,
  uploaded inert; not submitted).
- Retains v388's restored direct 346 and exact direct-346/347 controls, and
  classifies only direct 344 as an exact descent point. This makes the complete
  source ramp from 344 through 348 use quarter-second terrain-constrained
  movement.
- V388's canonical request
  `xreq_a2bca2c0-6bb3-4c4b-be7d-b0f248e9ccd0` completed 100/100 with no
  platform failures. Fifty-nine reached direct 275, 57 reached restored 276,
  56 reached 277/293, ten reached 332--334, seven reached 336, four crossed
  into 337, two reached 338, and one reached 343. That frontier activated
  direct 344 but took a 1.5-second open stride because 344 was retained without
  being classified exact; it fell from z83.30 to z67.35 on the first pulse and
  never reached 344. There were 54 deaths and no Great Lift arrival. The new
  346/347 behavior was not activated.

## v388 - follow the dense post-mesa ramp through direct 347 (2026-08-11)

- Version UUID: `aaecb36b-5434-426a-95d3-d7ddaf196630` (`wowborg:v388`,
  uploaded inert; not submitted).
- Retains v387 and removes only the direct 345 to 347 skip, restoring source
  anchor 346. It also classifies direct 346 and 347 as exact descent points so
  they use quarter-second terrain-constrained movement.
- V387's second canonical cohort reached direct 343, restored 344, 345, and
  347. Direct 347 was then accepted by the ordinary road-pass rule at z61.37,
  9.55 yards below its z70.92 target, while the character was already falling;
  it died at z-41.94 approaching direct 348. The pinned navmesh reports an
  eight-point, 35.7-yard ramp from the direct-345 arrival to direct 348, with
  source anchors 346 and 347 following that supported descent.
- Superseded by v389 after its sole direct-343 arrival exposed that retained
  direct 344 still used an ordinary 1.5-second stride rather than the ramp's
  exact quarter-second control.

## v387 - retain direct 344 on the mesa descent (2026-08-11)

- Version UUID: `40598596-0735-4d5d-9088-454fab3e6b67` (`wowborg:v387`,
  uploaded inert; not submitted).
- Retains v386's time recovery and chained ledge jumps, and removes only the
  direct 343 to 345 skip. V386 reached 343 safely, then the chord that omitted
  source descent anchor 344 walked off the mesa and fell from z86 to z-44.
- Two canonical-spawn requests completed 100/100 each with no platform
  failures: `xreq_847afa22-2170-4994-962d-7e7a3e1d37c7` and
  `xreq_429425d2-8d84-43a2-8441-9ba01da300ab`. The first did not activate the
  changed descent. In the repeat, one runner crossed direct 343, restored 344,
  345, and 347, validating the direct-344 fix; it then fell before direct 348.
  Across the repeat, 60 reached direct 275, 58 reached restored 276/277, 56
  reached 293, eight reached 332, and one reached 338--347. There were 59
  deaths and no Great Lift arrival.

## v386 - retain direct 276 to avoid the 275--277 collision trap (2026-08-11)

- Version UUID: `855d8902-011f-4c82-8426-2f8842514458` (`wowborg:v386`,
  uploaded inert; not submitted).
- Retains v385's proven chained ledge jumps and removes only the supported-road
  skip from direct 275 to 277. The first direct-338 run spent 33.1 seconds on
  that rising chord and invoked 12 collision unstick cycles; source point 276
  is the missing intermediate climb anchor. Restoring it should reclaim most
  of that time and leave usable horizon after the ledge.
- Canonical-spawn request `xreq_51ddb223-8d2f-4493-bcb8-862403a6183e`
  completed 100/100 with no platform failures. In the first 76 traces, 43
  reached direct 275, 40 reached restored 276, 39 reached 277, and 38 reached
  293; the prior 33.1-second 275--277 trap fell to 1.14 seconds. Six reached
  direct 332, four reached 335/336, one crossed both jumps through 338 at
  249.1 seconds (16.4 seconds earlier than v385), then reached 339, 341, and
  343. It fell on the skipped 343--345 descent; no Great Lift arrival.

## v385 - chain the direct-338 jump from the tiny landing (2026-08-11)

- Version UUID: `5d82af10-7735-4ab4-aa01-9d8096947b88` (`wowborg:v385`,
  uploaded inert; not submitted).
- Retains v384's successful jump into direct 337 and applies the same one-shot
  jump immediately toward direct 338. Hosted traces reach direct 337 at the
  expected z85.46 landing height, but the first non-jump pulse then falls;
  direct 337 is a tiny intermediate landing rather than continuous road.
- Three canonical cohorts completed 100/100 each with no platform failures:
  `xreq_9de13e45-5276-42ed-a11a-7a7a6d4df0ad`,
  `xreq_96a45afd-e04c-4c26-a08d-d12a9110417f`, and
  `xreq_39cdf2fa-3f27-4443-b847-3cef3dee2347`. The first two never activated
  direct 337. In the third, five reached direct 332--334, four reached 335/336,
  two jumped into 337, and one chained the second jump into direct 338—the
  first complete hosted crossing of the post-staircase gap sequence. It then
  traveled 117 safe yards toward direct 339 before the 270-second episode
  ended. No Great Lift arrival; superseded by v386's upstream time recovery.

## v384 - jump the final direct-337 ledge discontinuity (2026-08-11)

- Version UUID: `2d0c8a03-57f1-4b27-92a9-a09a8c1f8906` (`wowborg:v384`,
  uploaded inert; not submitted).
- Retains v383's centered approach and reuses the proven one-shot route jump
  only for direct 337. V383 held y near -1870, but z fell from 85 to 82 within
  five horizontal yards and continued to the ground through the target's x;
  the pinned navmesh also marks this apparently connected corridor partial.
- Canonical-spawn request `xreq_7b4ed2fa-b2dd-4e6b-931b-71de631f9efe`
  completed 100/100 with no platform failures. In the first 81 recovered
  traces, six reached direct 336 and three crossed the centering anchors plus
  the new jump into direct 337—the first hosted crossing of that
  discontinuity. All three then fell on the first non-jump pulse toward direct
  338; superseded by v385's chained one-shot jump.

## v383 - hold the centered line into direct 337 (2026-08-11)

- Version UUID: `55754732-da3b-42ae-9145-2a4aaca8315e` (`wowborg:v383`,
  uploaded inert; not submitted).
- Retains v382's three real-navmesh centering anchors, but restores the normal
  strafe deadband for the final eight yards into direct 337. V382 arrived at
  ledge 03 on supported ground at y=-1871.27/z85.21; treating the target's
  harmless 0.34-yard lateral offset as an error then oscillated north and fell.
  The remaining chord should proceed straight along the centered line.
- Canonical-spawn request `xreq_4a381f3f-af6f-4e14-abf9-a80766e77a61`
  completed 100/100 with no platform failures. The first recovered frontier
  reached all three ledge anchors and held the centered line, but lost altitude
  immediately after ledge 03 and fell through direct 337's x coordinate. This
  confirms a short physical discontinuity rather than v382's lateral-control
  overshoot; superseded by v384's one-shot jump.

## v382 - center the direct-336--337 narrow ledge (2026-08-11)

- Version UUID: `c0d71205-14a0-45de-b069-5b4dbbe73efe` (`wowborg:v382`,
  uploaded inert; not submitted).
- Retains v381 and replaces the unsupported one-target chord from direct 336
  to 337 with three anchors sampled from the pinned real navmesh. The corridor
  is supported but only about five degrees off the current heading; ordinary
  steering's 22.5-degree strafe deadband therefore held the starting y until
  the ledge fell away. These four ledge targets use a two-degree lateral
  deadband and exact quarter-second pulses to track the corridor center.
- Canonical-spawn request `xreq_8f08a37c-d003-442e-a3d5-a26999aed450`
  completed 100/100 with no platform failures. Artifact publication is still
  draining, but the first frontier trace reached all three new ledge anchors,
  proving the centerline fix crossed the section where v381 fell. It then
  overcorrected the final 0.34-yard lateral offset into direct 337 and fell;
  superseded by v383's straight final chord.

## v381 - traverse the full direct-336--338 ledge precisely (2026-08-11)

- Version UUID: `5a6cbe96-61b6-4572-98c6-0a2156bb3502` (`wowborg:v381`,
  uploaded inert; not submitted).
- Retains v380 and extends tight/exact quarter-second steering to direct 336
  and 337. In v380 the sole run to reach direct 336 was accepted about eight
  yards above the source anchor, then long strides drifted laterally and fell
  before direct 337. The whole post-staircase ledge now uses one consistent
  precise control contract.
- Canonical-spawn request `xreq_1b7b495d-64aa-43ad-8d7e-0e6160ffbed6`
  completed 96/96 with no platform failures: 47 deaths, 49 survivors, 12,142
  guidepoint arrivals, and 403,234 replay trajectory yards. Forty-nine reached
  direct 293, two crossed 332--335, one reached 336, and none reached 337 or
  338; no Great Lift arrival. The frontier trace held y near -1867 until the
  supported strip moved toward y=-1871, then fell from z84 to z12. The pinned
  navmesh confirms the 49.8-yard corridor is supported but reports the direct
  query as partial; v381's precision alone could not correct its shallow
  lateral offset.

## v380 - traverse the direct-338 ledge precisely (2026-08-11)

- Version UUID: `87ce1932-ef75-4486-a7ca-16d42a6217fb` (`wowborg:v380`,
  uploaded inert; not submitted).
- Retains v379 and classifies only direct 338 as tight/exact. The real navmesh
  reports a supported 32.2-yard ledge from direct 337 to 338, but v379's
  ordinary 1.5-second strides drifted laterally from y=-1870 to y=-1846 and
  fell to z11. Precise quarter-second steering should stay on the ledge; no
  jump is added.
- Canonical-spawn request `xreq_580ccefe-8dff-4e91-a58b-acc9ebfac774`
  completed 64/64 with no platform failures. Twenty-three runs reached direct
  293 and three crossed direct 332--334; one reached direct 336 but died before
  337, so direct 338's changed control never activated. The trace shows the
  broad 336/337 acceptance and long-stride behavior begins the ledge fall
  before 338. The candidate is superseded by precise control across 336--338.

## v379 - retain the direct-336/337 ledge turn (2026-08-11)

- Version UUID: `d8fd5758-9e48-46e6-9ccb-809a3e0060bd` (`wowborg:v379`,
  uploaded inert; not submitted).
- Retains v378 and removes only the `335 -> 338` supported-road skip. V378's
  frontier run crossed the full 332--335 descent, then the 88-yard skipped
  chord fell from z91 to z12 and killed the full-health character. The source
  anchors at direct 336/337 first turn onto the z85 supported ledge before the
  route continues east.
- Forty-six of 48 canonical-spawn jobs in request
  `xreq_f498d099-88cc-4c07-8415-550f6555e88f` completed while two hosted jobs
  remained delayed. The recovered sample has 24 direct-293 arrivals, two
  direct-332 arrivals, and one complete 332--337 crossing. The frontier then
  died approaching direct 338 after ordinary long strides drifted off its
  narrow supported ledge. Final cohort aggregation awaits the two delayed jobs;
  the direct-336/337 restoration is mechanically validated and retained.

## v378 - route north around the Centipaar hive (2026-08-11)

- Version UUID: `62c18bf8-5582-41bb-8ce1-60f4de8ea2b0` (`wowborg:v378`,
  uploaded inert; not submitted).
- Reverts v377's global clearance increase and replaces the 252-yard straight
  bridge chord through the hive with a real-navmesh-validated northern arc via
  `(-8180,-2300)` and `(-7940,-2300)`. The 498-yard arc stays on one connected,
  supported surface and remains about 45 yards north of the closest observed
  Centipaar patrol, adding roughly 246 route yards without v377's unbounded
  local detours.
- Canonical-spawn request `xreq_df9d304c-9948-4075-b339-bb6664475517`
  completed 48/48 with no platform failures. Thirty-four runs crossed the
  northern bypass, 22 reached direct 293, and one crossed all of direct
  332--335 before dying on the skipped chord to 338. Deaths were 24 and total
  guidepoints reached jumped from v377's 879 to 4,729. The replay-derived
  4,531-yard maximum was a post-death graveyard artifact; the authoritative
  policy best was 3,385 yards. The geometric bypass is retained.

## v377 - restore a 20-yard hive clearance floor (2026-08-11)

- Version UUID: `daae9982-1adf-425f-ae9a-82e6d6c219a6` (`wowborg:v377`,
  uploaded inert; not submitted).
- Reverts v375/v376's unsafe-detour hold branch and retains v374's terrain and
  reactive-combat controls. Raises the ordinary level-scaled hazard uncertainty
  margin from three to 15 yards, producing a 20-yard floor against the recurring
  level-46--49 Centipaar mobs. Prior hosted evidence kept all 12 runs alive at
  that floor; the later 12-yard experiment regressed to 9/12, while current
  8-yard cohorts die in more than half of episodes.
- Canonical-spawn request `xreq_cb4d2d63-6ebb-41ee-999f-04ce891fc504`
  completed 48/48 with no platform failures. Deaths fell to 13 from v376's 26
  and the unchanged v374 repeat's 29, but no run cleared the bridge: best
  northing was 1,996 yards and median regressed to 1,144. Total trajectory rose
  to 181,532 yards because the local detour controller churned instead of
  selecting a stable bypass. Rejected in favor of explicit route geometry.

## v376 - hold only for an immediately fightable blocker (2026-08-11)

- Version UUID: `76c5ac5a-af43-45ed-89d5-e26db2aae133` (`wowborg:v376`,
  uploaded inert; not submitted).
- Retains v374's terrain controls and narrows v375's unsafe-detour hold to the
  cases that can actually activate its guarded clearance fight: exactly one
  non-elite level-49-or-lower blocker within 45 yards, at least 80% player
  health, and no predicted add at the blocker over the next six seconds.
  Unsuitable or multi-blocker crossings use the prior avoidance behavior rather
  than waiting indefinitely.
- Canonical-spawn request `xreq_f2a63d71-a23b-4078-a5e2-b9c8b16643b1`
  completed 48/48 with no platform failures. Deaths improved from the unchanged
  v374 repeat's 29 to 26, but hold pulses remained 5,070 versus 563 and total
  trajectory fell from 90,264 to 80,498 yards. Twelve proactive fights fired;
  no run reached direct 332. Rejected and reverted.

## v375 - hold when every hazard detour is unsafe (2026-08-11)

- Version UUID: `a6a9e36f-8e06-4823-9434-f6be7f77d5cf` (`wowborg:v375`,
  uploaded inert; not submitted).
- Retains v374, but stops taking the least-bad sidestep when both candidate
  paths violate the router's estimated aggro clearance. The blocking enemies
  become an explicit hold set: one isolated non-elite level-49-or-lower blocker
  can be cleared after the existing three-second/80%-health/add-prediction
  gates; multiple or stronger blockers are still waited out.
- Canonical-spawn request `xreq_cd20acb5-3257-4f0a-aa1e-f4e42c55c6ac`
  completed 48/48 with no platform failures. Against the unchanged v374 repeat,
  deaths changed only from 29 to 28 while hold pulses exploded from 563 to
  24,030 and trajectory fell from 90,264 to 73,085 yards. Twenty-one guarded
  proactive fights did activate, but the broad hold also trapped unsuitable and
  multi-blocker cases. Rejected in favor of holding only when the existing
  fight gates can actually be satisfied.

## v374 - traverse the direct-332--335 descent staircase (2026-08-11)

- Version UUID: `c78d4618-67c5-4872-bdae-5b9865506309` (`wowborg:v374`,
  uploaded inert; not submitted).
- Retains v373, classifies direct 333 as an exact descent, and applies one-shot
  forward-lip control to the measured direct-332--335 staircase. Direct 332's
  jump crossed 1/1 in v373; the landing then stalled at unclassified direct 333
  before the two larger already-classified drops at 334/335.
- Initial canonical-spawn request
  `xreq_fed0bc47-1fb9-4d2e-ab42-4dc50e5a91ed` completed 48/48 with no platform
  failures, but no run reached the changed staircase (best direct guidepoint
  309). It had 26 deaths; 25 occurred in the northern Tanaris hazard corridor,
  and the router repeatedly selected a sidestep whose measured clearance was
  below its own aggro requirement. Unchanged 48-episode repeat
  `xreq_a017bfbc-42fb-4131-87e0-3eddd67e9684` also completed 48/48 without
  reaching the staircase (best direct guidepoint 312; best northing 2,831).
  It recorded 29 deaths, 563 hold pulses, and 90,264 trajectory yards. The
  staircase control remains mechanically untested.

## v373 - jump the direct-332 descent lip (2026-08-11)

- Version UUID: `ba1333a2-c1c0-4e94-97be-2d6163ea8dfb` (`wowborg:v373`,
  uploaded inert; not submitted).
- Retains v372 and adds only direct 332 to the one-shot jump set. The target is
  roughly ten yards ahead and 6.5 yards lower; v372's exact descent steering
  oscillated at the lip, drifted 37 yards away, and timed out.
- Initial canonical-spawn request `xreq_218756bb-62e3-460e-9367-3fb5a9844ccc`
  completed 24/24 without reaching direct 332. The unchanged 48-episode repeat
  `xreq_078aee76-c92d-49bb-8197-3f39011f0218` produced one direct-332 attempt
  and one successful crossing, with best northing 3,329 yards. That run then
  failed at direct 333, the first of three adjacent descent lips. The direct-332
  jump is retained. The next candidate classifies direct 333 as an exact
  descent and applies the same one-shot lip control to the measured 332--335
  descent sequence.

## v372 - add scoped direct-298 jump (2026-08-11)

- Version UUID: `eefd6177-73f2-441d-8b2d-1cc36f8ab0ea` (`wowborg:v372`,
  uploaded inert; not submitted).
- Retains v371 and adds only direct 298 to the steep-jump set. The measured
  route rises 13.2 yards over 17.4 horizontal yards there; a healthy v371 run
  crossed direct 293 and 296 before exhausting collision recovery at 298.
- Initial canonical-spawn request `xreq_c0fb8481-e5c0-40a8-9a8e-4d17f78feeab`
  completed 24/24 without reaching direct 293, so it could not evaluate the
  change. The unchanged repeat
  `xreq_5c69b146-2d48-4619-81f9-5ee5b26a8e47` completed 24/24: direct 293,
  298, and 302 each crossed on every attempt, and best northing advanced from
  2,889 to 3,322 yards at direct 330. At direct 332, exact descent steering
  oscillated at a 6.5-yard lip, drifted 37 yards away, and timed out. The
  direct-298 jump is retained. The next candidate adds a one-shot forward jump
  only to direct 332's already-classified exact descent.

## v371 - combine clearance fights with direct-293 jump (2026-08-11)

- Version UUID: `2068ee08-20e8-442b-9625-92a1b6b921cb` (`wowborg:v371`,
  uploaded inert; not submitted).
- Retains v370's time-bounded single-blocker clearance fights and adds only
  direct 293 to the steep-jump set. Hosted v364 evidence already showed this
  exact jump crosses the ridge in about 1.5 seconds; v370 newly delivered a
  healthy cohort member to the same ridge before ordinary movement timed out.
- Canonical-spawn request `xreq_39820a57-c7ca-4c70-90b7-7256ab4e1032`
  completed 24/24 with no platform failures and no Great Lift arrivals. Deaths
  improved from 14 to 12, survivors rose from ten to 12, total guidepoints
  reached rose from 733 to 856, and hold pulses fell from 2,886 to 587. All
  three direct-293 attempts crossed successfully; one continued through direct
  296 and then exhausted collision recovery at direct 298. The combined
  clearance-fight and direct-293 controls are retained. The next candidate adds
  scoped jump control to direct 298's measured 13.2-yard climb over 17.4 yards;
  direct 302 is already in the steep set.

## v370 - time-bound clearance-fight add prediction (2026-08-11)

- Version UUID: `8192a021-9960-4a58-9fa6-d3f0f1dde44e` (`wowborg:v370`,
  uploaded inert; not submitted).
- Retains v369's single-blocker and health gates, but predicts adds at the
  blocker location over the next six seconds instead of rejecting on any
  eventual crossing of the character's current location along a patrol's full
  remaining path.
- Canonical-spawn request `xreq_5ac24426-207d-4b7d-8c81-7d9c4c66a8e0`
  completed 24/24 with no platform failures and no Great Lift arrivals. Two
  guarded proactive fights activated against a level-47 Wasp and level-49
  Sandreaver; all fights still began with at most one attacker. Deaths matched
  v367 at 14, hold pulses fell from v369's 5,788 to 2,886, and total
  guidepoints reached set a cohort high of 733. The best run reached direct 293
  alive, where ordinary movement timed out for 32 seconds. The fight-window
  predictor is retained; the next candidate recombines v364's already-proven
  scoped jump at that exact ridge.

## v369 - clear a prolonged single-enemy hold (2026-08-11)

- Version UUID: `8b63fb67-306c-4d72-8a49-a898ee5f5d94` (`wowborg:v369`,
  uploaded inert; not submitted).
- After three seconds at a terrain-constrained hold, permits a proactive fight
  only when exactly one held blocker is a non-elite level-49-or-lower enemy,
  health is at least 80%, and no likely add crosses the approach. Multi-blocker,
  low-health, elite, and stronger holds retain avoidance/wait behavior.
- Canonical-spawn request `xreq_5f63b78f-c499-47e5-87fe-bddd3f8141c3`
  completed 24/24 with no platform failures and no Great Lift arrivals. Deaths
  matched v367 at 14 and best northing reached 2,832 yards, but the intended
  proactive branch never activated; one survivor still accumulated all 5,788
  hold pulses. The full-patrol-path add check was rejecting blockers based on
  eventual crossings outside the measured four-to-five-second fight window.
  The next candidate bounds that prediction to the fight location and a
  six-second horizon.

## v368 - reacquire Travel Form after combat (2026-08-11)

- Version UUID: `7ba105a1-d36b-405d-bc95-20a717af443a` (`wowborg:v368`,
  uploaded inert; not submitted).
- Resets the current road leg's Travel Form attempt and fallback latches when a
  Traverse fight ends. Combat and post-fight Rejuvenation both change form, so
  the old latches could otherwise leave the character walking until the next
  guidepoint.
- Canonical-spawn request `xreq_4932f03b-428b-4f58-9f43-3121f0e79c8f`
  completed 24/24 with no platform failures and no Great Lift arrivals. Travel
  Form casts rose from 49 to 65 and best northing rose from 2,698 to 2,849
  yards, but deaths worsened from 14 to 16 and total guidepoints reached fell
  from 687 to 652; median northing remained 1,996 yards. The latch reset is
  rejected because it did not improve consistency. The next candidate instead
  converts a prolonged single-blocker hold into a guarded clearance fight.

## v367 - react before entering estimated aggro range (2026-08-11)

- Version UUID: `761ea27e-7a59-455d-bd52-34af9e96db2f` (`wowborg:v367`,
  uploaded inert; not submitted).
- Increases the hazard-router activation/deactivation distances from 30/40 to
  45/55 yards while leaving the per-enemy aggro-radius estimate unchanged.
- Canonical-spawn request `xreq_e9894ee0-808a-4501-9253-6117350ca108`
  completed 24/24 with no platform failures and no Great Lift arrivals. Versus
  v366, deaths fell from 15 to 14, survivors rose from nine to ten, total
  guidepoints reached rose from 608 to 687, and best northing improved from
  2,671 to 2,698 yards; median northing remained 1,996 yards. The earlier
  reaction margin is retained as a modest consistency improvement. The next
  candidate resets Travel Form's per-leg attempt latch after combat changes
  form, allowing the fast form to be reacquired after post-fight healing.

## v366 - relax broad bridge pass envelopes (2026-08-11)

- Version UUID: `dad4d7e6-23c6-4c3d-88b8-3d8981d164b5` (`wowborg:v366`,
  uploaded inert; not submitted).
- Restores v363's cast-and-move healing and removes the broad safe-bridge legs
  from the six-yard corridor set. The measured climb and descent anchors remain
  exact; ordinary bridge legs may pass within the standard 60-yard envelope.
- Canonical-spawn request `xreq_126766e9-6550-4cdf-9631-159bf96d286f`
  completed 24/24 with no platform failures and no Great Lift arrivals. Deaths
  fell to 15 and survivors rose to nine. The best reached direct 275 at
  x=-6515.57 with 5,048 trajectory yards, materially less path waste than
  v363's 6,508-yard best. The relaxed pass rule is retained, but deaths still
  cluster on bridge 02/03. The next candidate increases hazard-reaction margin
  without changing the estimated aggro radius.

## v365 - wait for post-fight healing to complete (2026-08-11)

- Version UUID: `795b7255-3833-4d7e-aa0c-1787ada5722a` (`wowborg:v365`,
  uploaded inert; not submitted).
- Removes v364's direct-293 jump and waits out an active Rejuvenation until the
  same 80% health threshold that triggered healing is restored.
- Canonical-spawn request `xreq_ff690f79-8334-4af6-b57d-22ee77a776c7`
  completed 24/24 with no platform failures and no Great Lift arrivals. Deaths
  rose to 19 and the best survivor regressed to direct 250 at x=-6744.87. Some
  runs spent 50--117 wait frames stationary beside the patrol that caused the
  fight, inviting another pull before healing completed. Waiting is rejected;
  v363's cast-and-move behavior is restored. The next candidate instead relaxes
  the broad bridge legs' six-yard pass envelope so hazard avoidance can remain
  lateral to the Centipaar endpoint.

## v364 - jump the direct-293 ridge (2026-08-11)

- Version UUID: `31eb06bd-616f-4e95-bc5b-99fc5523fac3` (`wowborg:v364`,
  uploaded inert; not submitted).
- Adds direct 293 to the steep-jump set, leaving v363's short bridge, combat,
  and post-fight healing unchanged.
- Canonical-spawn request `xreq_48b8fc3a-eb8b-4675-a387-808151bb426d`
  completed 24/24 with no platform failures and no Great Lift arrivals. It had
  17 deaths and seven survivors. The best run activated the jump and reached
  direct 293 in 1.5 seconds, but stopped at direct 296 on `no_frame`; the best
  final x=-6354.91 was behind v363. The jump is mechanically valid but did not
  improve the cohort frontier, so it is removed. The next candidate instead
  waits for Rejuvenation to restore the configured 80% health threshold before
  resuming Travel Form.

## v363 - combine healing with the shorter supported bridge (2026-08-11)

- Version UUID: `035f5252-c807-4864-9378-5464c5c33f4c` (`wowborg:v363`,
  uploaded inert; not submitted).
- Replaces the 844-yard wide bridge with the 331-yard, six-anchor
  Detour-supported bridge from v353/v355 while retaining v362's verified
  post-fight healing.
- Canonical-spawn request `xreq_8a83932a-24e5-4935-954b-d13b95e293c7`
  completed 24/24 with no platform failures and no Great Lift arrivals. Deaths
  fell to 16 and 31 Rejuvenation casts succeeded. The best living run reached
  x=-6294 at direct 296 with 6,508 trajectory yards, recovering the v355
  frontier. Its trace spent about 47 seconds colliding below direct 293 before
  finally climbing, then failed at direct 298 for lack of a next frame. The
  short bridge and healing are retained; v364 adds scoped jump control only to
  the measured direct-293 ridge.

## v362 - queue healing after gate-lost fights (2026-08-11)

- Version UUID: `30d742ad-9f47-470c-b9f4-4e3c6cfe7a32` (`wowborg:v362`,
  uploaded inert; not submitted).
- Queues low-health post-fight healing after either `combat_ended` or
  `gate_lost`, while retaining the requirement that combat actually clear
  before exiting form and casting. Route geometry is unchanged from v360/v361.
- Canonical-spawn request `xreq_50c1d242-226a-4057-bf65-4d2981142f63`
  completed 24/24 with no platform failures and no Great Lift arrivals. It
  produced 28 successful Rejuvenation casts and reduced deaths from v361's 23
  to 18, validating the corrected transition. Throughput remained poor: the
  best run reached route activation 41 (`tanaris-northern-direct-147`), while
  the six non-death runs mostly ended on deadline, `no_frame`, or no progress
  within the 844-yard bridge. Healing is retained; the wide route is rejected
  in favor of the shorter supported bridge.

## v361 - heal after low-health Traverse fights (2026-08-11)

- Version UUID: `e175c5a9-30e6-4819-8d1d-5f00433972f0` (`wowborg:v361`,
  uploaded inert; not submitted).
- Adds an 80% post-fight health threshold and uses the existing Rejuvenation
  transition before resuming Travel Form. The v360 route is unchanged.
- Canonical-spawn request `xreq_3a74fce1-21f7-4888-8a8e-bcd5fac75e99`
  completed 24/24 with no platform failures and no Great Lift arrivals. It had
  23 deaths, 45 fights, and a best route activation of 40. Rejuvenation handling
  emitted 68 events after 13 clean `combat_ended` boundaries, but 27 fights
  ended with `gate_lost` while the character remained in combat; those
  low-health escapes were not queued for healing. The experiment exposes a
  state-machine gap rather than rejecting post-fight sustain: v362 queues the
  heal on either fight-ending reason and still waits for combat to clear before
  casting.

## v360 - route outside the observed southern hive boundary (2026-08-11)

- Version UUID: `325fab49-eab5-4570-a7a4-bbb11a406b7b` (`wowborg:v360`,
  uploaded inert; not submitted).
- Widens the bridge to an 844-yard Detour-supported route near y=-2700 and
  leaves only the measured climbs and descents terrain-constrained.
- Canonical-spawn request `xreq_d670dbe9-d1d7-4b63-9f77-14fcaff375ee`
  completed 24/24 with no platform failures and no Great Lift arrivals. Seven
  runs crossed the bridge, but 21/24 died and only two exceeded 2,500 yards
  northing. The best living run reached direct 275 at x=-6504.68. The wide
  route proves the supported geometry is traversable, but its extra distance
  and broad hostile exposure make geometry-only avoidance too slow and
  inconsistent. It is retained for one isolated combat-sustain experiment.

## v359 - route along the supported southern hive boundary (2026-08-11)

- Version UUID: `2ec95f47-fe97-402f-a3d0-32a0ca5966c3` (`wowborg:v359`,
  uploaded inert; not submitted).
- Moves the bridge to a 412-yard Detour-supported corridor about 34 yards south
  of the first observed patrol line, rejoining east of the hive.
- Canonical-spawn request `xreq_15745978-a7cf-4cb7-83b3-d69c881c1dce`
  completed 24/24 with no platform failures and no Great Lift arrivals. No run
  crossed and 13/24 died. The authored canyon anchors were traversable, but
  traces exposed Stingers, Swarmers, Silithid Swarms, and a Sandreaver as far
  south as y=-2460. This boundary is still inside the hive and is rejected.

## v358 - route north of both observed Centipaar patrol lines (2026-08-11)

- Version UUID: `c406cd88-92ac-4159-a1fd-04bdace419b7` (`wowborg:v358`,
  uploaded inert; not submitted).
- Widens the bridge bypass to a 371-yard Detour-supported corridor north of the
  Stinger and Swarmer positions observed in v356/v357.
- Canonical-spawn request `xreq_09fbfce2-ed97-41b5-8f7a-de10db7d237c`
  completed 24/24 with no platform failures and no Great Lift arrivals. One run
  crossed and reached direct 293 at x=-6375, but 18/24 died and the other 23
  failed to cross. Traces exposed additional Worker, Wasp, and Sandreaver
  patrols as far north as y=-2359. The entire near-north corridor remains inside
  the hive and is rejected.

## v357 - dogleg north of the bridge-02 Stinger pack (2026-08-11)

- Version UUID: `7794f340-40fe-46b0-a0c4-51770059a0de` (`wowborg:v357`,
  uploaded inert; not submitted).
- Replaces the original bridge-02 chord with a Detour-supported dogleg about
  30--40 yards north of the first observed Stinger pack.
- Canonical-spawn request `xreq_4d8bc26f-b73a-4bc9-aa92-3823f71e0c60`
  completed 24/24 with no platform failures and no Great Lift arrivals. Only
  2/24 crossed the new bridge and 12/24 died. The dogleg landed beside a
  different Swarmer patrol near (-7952, -2384), causing the constrained router
  to hold indefinitely or accumulate attackers. This local dogleg is rejected.

## v356 - scope jump control to the direct-293 ridge (2026-08-11)

- Version UUID: `f27587fe-cf94-4f80-9627-57d6ed133e07` (`wowborg:v356`,
  uploaded inert; not submitted).
- Adds direct 293 to the steep-jump set after v355 spent its final 46 seconds
  colliding below that 15-yard ridge.
- Canonical-spawn request `xreq_db4cb31c-3f18-4281-aa0f-46575bfe6aa3`
  completed 24/24 with no platform failures and no Great Lift arrivals. Only
  two runs exceeded 2,500 yards northing and neither reached direct 293, so the
  new control never activated and the cohort cannot judge it. Ten runs died,
  predominantly after the long bridge-02 leg entered the Centipaar pack near
  (-7932, -2428). The direct-293 change is removed while that earlier
  consistency bottleneck is isolated.

## v355 - extend only clear-road movement to 1.5-second strides (2026-08-10)

- Version UUID: `54a30422-61b2-4922-853f-83e17cb96487` (`wowborg:v355`,
  uploaded inert; not submitted).
- Restores v353's quarter-second terrain control and extends only hazard-free,
  unconstrained clear-road translation from 1.0 to the previously hosted-proven
  1.5-second input limit.
- Canonical-spawn request `xreq_9e24d697-11ee-45fb-b691-68dac51a7629`
  completed 24/24 with no platform failures and no Great Lift arrivals. Three
  runs exceeded 2,500 yards northing; the best reached x=-6292.36, improving
  the v353/v354 frontier. It then spent roughly 46 seconds colliding beneath
  direct 293, a 15-yard climb over 21 horizontal yards that was missing from
  the steep-jump set. The clear stride is retained; the next candidate adds
  scoped climb control only at direct 293.

## v354 - try half-second control on active terrain bands (2026-08-10)

- Version UUID: `a25ee243-d806-4736-a449-c44a1439cd94` (`wowborg:v354`,
  uploaded inert; not submitted).
- Uses half-second rather than quarter-second precise movement on direct bands
  140--215 and 258--275, leaving the supported bridge and all other behavior
  identical to v353.
- Canonical-spawn request `xreq_bb0adf87-cb13-4aad-a73f-fd8727529e4c`
  completed 24/24 with no platform failures and no Great Lift arrivals. The
  best run reached direct 293 at x=-6364.8, slightly behind v353's direct-296
  best. It also needed about 92 seconds from direct 260 to failure, versus
  roughly 74 seconds for v353 to reach direct 296. The cadence change is
  rejected; quarter-second terrain control is restored.

## v353 - bridge the supported northern surface into the proven corridor (2026-08-10)

- Version UUID: `8b84befe-d3e3-4cd0-bf1e-4eb88b06fcad` (`wowborg:v353`,
  uploaded inert; not submitted).
- Replaces the disconnected ridge descent with a pinned 342.6-yard, six-anchor
  bridge from northern bypass 17 to the already-proven direct corridor at
  direct 140. The resulting full route is approximately 5,761 yards.
- Canonical-spawn request `xreq_8e24887e-861f-45b4-9747-7be5d6dd101c`
  completed 24/24 without platform failures. Multiple episodes crossed the new
  bridge alive and reached direct 296; the best run covered 5,718 trajectory
  yards with no death and reached x=-6329 before the 270-second episode limit.
  No episode reached the Great Lift. Trace timing isolates the next bottleneck:
  terrain-sensitive direct bands 140--215 and 258--275 still consume
  quarter-second movement pulses, while the supported route itself is viable.

## v352 - start semantic descent from the first downhill polygon (2026-08-10)

- Version UUID: `4914be09-b85f-4aa9-b3db-23c5c597e954` (`wowborg:v352`,
  uploaded inert; not submitted).
- Repairs v351's startup syntax and enters the first confirmed downhill polygon
  manually before invoking native semantic movement.
- Canonical-spawn request `xreq_5f974182-45b8-4a23-951b-1f2970515369`
  was cancelled after repeated live traces rejected the component itself.
  Representative runs reached the entry anchor, but the native follower then
  aborted with `unsafe environmental damage interruption (falling)`; subsequent
  attempts lost the admissible source triangle. The alternate cliff component
  is rejected. A pinned query found a 342.6-yard, six-anchor supported bridge
  from bypass 17 to the already proven old corridor at direct 140, producing a
  5,761-yard full route without the disconnected descent.

## v351 - enter the first downhill polygon before semantic descent (2026-08-10)

- Version UUID: `ebc1cb32-9f3d-4bf0-a764-da2368c21eff` (`wowborg:v351`,
  uploaded inert; not submitted).
- Intended to add one manually proven entry anchor before the scoped native
  descent.
- Canonical-spawn request `xreq_510caf14-c93b-45c7-92e8-fc292fd48ba8`
  exposed an image-startup regression before gameplay: the Traverse module had
  an unmatched parenthesis in the new guidepoint-set expression and exited with
  `SyntaxError`. The request was cancelled and provides no route evidence. A
  narrow container import reproduced the hosted failure; v352 fixes only that
  syntax error and retains the intended v351 behavior.

## v350 - delegate the ridge descent to native Detour movement (2026-08-10)

- Version UUID: `d71a1378-f2b9-41ac-8307-62cc4dfaca31` (`wowborg:v350`,
  uploaded inert; not submitted).
- Scopes semantic `move_to` to the single 63-yard ridge descent; every other
  route leg retains the manual hazard-aware controller.
- Canonical-spawn request `xreq_69b514e5-3fa7-4204-8082-1e026adce70b`
  was cancelled after semantic descent attempts returned a typed refusal rather
  than falling: `no physically admissible source triangle was found near the
  client pose`. The preceding steep-edge rule accepted bypass 20 at x=-7846.2,
  z=23.2, slightly below the first raw descent triangle near z=25. Native
  movement is retained, but now begins after one manually proven entry anchor
  on the downhill polygon.

## v349 - restore the raw Detour descent anchors (2026-08-10)

- Version UUID: `d9da795e-e7eb-4a30-a3d1-51ae14edf6cf` (`wowborg:v349`,
  uploaded inert; not submitted).
- Replaces the invalid bypass-20-to-21 chord with all 20 raw pinned Detour
  points across the 63-yard downhill surface.
- Canonical-spawn request `xreq_cf26f026-0073-47ba-95f2-da3f36b6a688`
  was cancelled after live traces showed material but incomplete improvement.
  A representative run traversed descent 01--13 alive, then accepted point 13
  at the three-yard edge of its radius. Its next turn-only pulse began after
  the character was already sliding; movement continuation carried it below
  the world before point 14. This proves the raw polygon corridor is the right
  geometry but manual vector headings remain an unsafe actuator for the narrow
  vertical seam. The next candidate delegates only this seam to native semantic
  movement, which follows the Detour corridor directly.

## v348 - control the alternate ridge descent exactly (2026-08-10)

- Version UUID: `eae658b8-c5f4-416d-a62f-f1fe685954f2` (`wowborg:v348`,
  uploaded inert; not submitted).
- Makes bypass 20--24 exact, bounded terrain; jumps to the ridge crest and the
  three recovery climbs after its landing.
- Canonical-spawn request `xreq_5c21f123-d003-42f3-bf3e-0ff54f6b6da6`
  was cancelled after multiple live traces reproduced death at bypass 21. The
  new control did reach bypass 20 at the intended ridge crest (x=-7846.2,
  z=23.3, then z=25.0 on the first descent frame), falsifying loose crest
  arrival as the remaining cause. A fresh pinned sub-query exposed the actual
  defect: the whole-route simplifier collapsed 20 downhill Detour points into
  a single 53-yard chord. That chord cuts through empty world and fell to
  z=-63 before death. Exact crest control is retained; the raw descent
  corridor must be restored.

## v347 - take the alternate pinned northern chain (2026-08-10)

- Version UUID: `f28837fc-af1e-4fe2-be6c-105642715de0` (`wowborg:v347`,
  uploaded inert; not submitted).
- Rejects the narrow shelf entirely. The active route now follows the alternate
  exact-spawn Detour chain for 48 anchors, then rejoins the proven route at
  direct 221. The resulting route is 5,650 yards, within the episode's movement
  budget without relying on ineffective rank-1 Prowl.
- Canonical-spawn request `xreq_a02e1f1b-f23c-46a9-b64c-d9e4ddc38333`
  reached bypass 18 in the first sampled runs, but representative runs then
  fell and died at bypass 21. Trace evidence identified a local control seam:
  bypass 20 was accepted about ten planar yards and eight vertical yards below
  its ridge-crest target, after which the long chord to bypass 21 walked off the
  ridge and fell to z=-137. The alternate chain is retained; only its observed
  crest-to-landing seam needs exact bounded control.

## v346 - use ordinary aggro routing on the dense shelf (2026-08-10)

- Version UUID: `051046f3-933e-419c-a37e-79164b713226` (`wowborg:v346`,
  uploaded inert; not submitted).
- Retains the dense exact shelf but removes ineffective shortcut Prowl, using
  ordinary level-scaled hazard routing on broad terrain and hold-on-hazard on
  the shelf.
- Request `xreq_48fadeb9-d430-413c-a225-ba17641f9eb8` was cancelled after live
  samples showed the shelf remained structurally bad: runs reached the denser
  anchors, but still clustered in hazard holds, level-48 engagements, deaths,
  and no-progress around shelf 01--10. No completed episodes are used as
  evidence. The entire shelf corridor is rejected in favor of the alternate
  pinned northern chain.

## v345 - densify the prowled shortcut shelf (2026-08-10)

- Version UUID: `c6d15404-7182-494f-a212-4a73d396528e` (`wowborg:v345`,
  uploaded inert; not submitted).
- Replaces the coarse shortcut-14--23 shelf with 26 exact anchors simplified
  at one yard from a fresh pinned-navmesh sub-query. Full-shortcut Prowl remains
  for this isolated geometry test.
- Canonical-spawn request `xreq_9eb0f3fb-16fb-4bb5-9f19-ac077a7e190c`
  confirmed that rank-1 Prowl is itself unsafe in this fixture. One early run
  was detected by level-46 and level-48 Tanaris mobs while prowled and died at
  shortcut 07; the trace's first engagement began at 5.5 yards after Prowl had
  been active since shortcut 01. This agrees with the pinned VMaNGOS model:
  rank-1 Prowl's 100 stealth value is detectable by these mobs much farther
  away than ordinary level-scaled aggro. Dense shelf geometry is retained;
  shortcut Prowl is rejected.

## v344 - enter Prowl before the shortcut mob field (2026-08-10)

- Version UUID: `d243fece-9ccc-493b-8c6b-4a382fa012d5` (`wowborg:v344`,
  uploaded inert; not submitted).
- Extends Prowl across the complete 34-anchor shortcut and tightens the
  shortcut-14--23 shelf to exact three-yard arrivals.
- Canonical-spawn request `xreq_221c6a49-4772-4221-b0f2-065515c62c93`
  prevented the earlier unstealthed mob-field failures, and one observed weak
  attacker was correctly killed in 3.8 seconds. Runs still clustered in deaths
  and no-progress at shortcut 15--19. A fresh pinned-navmesh sub-query found
  that the three-yard whole-route simplification omitted material bends near
  x=-7979/-7899 and placed shortcut 17 just outside the sub-corridor's exact
  anchor. Full-corridor stealth is retained; the coarse shelf geometry is
  rejected.

## v343 - prowl only on the narrow shortcut shelf (2026-08-10)

- Version UUID: `0248a3c2-5ccc-4271-9aaf-49743339a397` (`wowborg:v343`,
  uploaded inert; not submitted).
- Adds terrain-constrained Prowl from shortcut 14 through 23, leaving the rest
  of the shorter route in Travel Form.
- Canonical-spawn request `xreq_2a6bc12b-6841-4230-90c7-fbb2f26ad0d3`
  showed that the scoped band starts too late: sampled episodes died before it
  at shortcut 02 or entered shortcut 14 already falling/engaged, preventing a
  useful stealth transition. The band's ordinary eight-yard arrival envelope
  also remained wide enough to cut corners on the narrow shelf. Scoped late
  stealth is rejected in favor of entering Prowl before the mob field and exact
  control only on the observed shelf.

## v342 - route around hazards on the northern shortcut (2026-08-10)

- Version UUID: `6a79ac13-fe61-4e2a-9439-dc0ba618f1f1` (`wowborg:v342`,
  uploaded inert; not submitted).
- Removes v341's speculative shortcut terrain tags so the existing live-unit
  router can choose lateral clearance around Tanaris mobs.
- Canonical-spawn request `xreq_3fcf13b4-b7e7-4aa3-81e5-78c77fe4eeb5`
  cleared the old shortcut-07 hold and demonstrated the intended velocity, but
  representative runs died or timed out at shortcut 14--23. A policy trace
  caught ordinary hazard avoidance leaving the narrow shelf near shortcut 18,
  falling from about z=9 to z=-45, and timing out after the off-mesh landing.
  Unconstrained avoidance is rejected only for that observed shelf.

## v341 - take the shorter northern Detour chain (2026-08-10)

- Version UUID: `ea7a103d-47f0-4f3e-b904-099923ae9c7f` (`wowborg:v341`,
  uploaded inert; not submitted).
- Replaces the first 217 anchors of the older partial-path frontier with the
  pinned 0.1.209 Detour chain from the exact movement bootstrap, then rejoins
  the proven route at direct 218. The active route falls from 6,926 to 5,573
  yards while every downstream terrain and hazard control remains unchanged.
- Canonical-spawn request `xreq_9bb5e48e-25e1-466a-981c-2295d4cde210`
  proved the shortcut's early velocity but exposed an encoding error at
  shortcut 07: the candidate speculatively marked a smooth navmesh rise as
  terrain constrained, so a Rabid Blisterpaw 9.6 yards ahead triggered an
  indefinite hazard hold instead of lateral avoidance. The constraint is
  rejected; the shorter route is retained.

## v340 - resume clear-road semantic movement after wire canonicalization (2026-08-10)

- Version UUID: `ff5be9ae-dd04-46aa-94e6-d21a79ce12d5` (`wowborg:v340`,
  uploaded inert; not submitted).
- Re-enables `move_to` only on clear, supported, non-jumping, non-stealth road
  legs after v339 canonicalized destination coordinates to the host's float32
  wire width. Hazard steering, combat, stealth, bounded terrain, and precise
  arrivals retain the proven manual-vector controller.
- The `linux/amd64` image passed the required `/player` and navmesh SDK import
  verification.
- Canonical-spawn request `xreq_566ba3ee-3bb1-4766-b957-9af2b8d38d0f`
  completed all 24 episodes with zero deaths but zero dock arrivals. The
  float32 repair eliminated the v338 settlement deadlock: 5,855 semantic
  actions settled continuously, and host telemetry showed compatible movement
  continuation with no next-action stall. The controller itself is rejected:
  repeated short Detour replans oscillated, median progress fell to direct 55,
  and the best run only activated direct 81 in 270 seconds. Clear-road routing
  returns to the proven manual vector controller; wire canonicalization remains
  because it repairs the general semantic-action contract.

## v339 - canonicalize semantic destinations to the wire float width (2026-08-10)

- Version UUID: `97b57d73-a7ba-4f2a-b28f-c6bb424a21a9` (`wowborg:v339`,
  uploaded inert; not submitted).
- Canonicalizes `move_to` destination coordinates to IEEE-754 float32 before
  submission. The host's Nim contract stores `WorldPoint` coordinates as
  float32, while the packaged Python runtime correlates returned action state
  using exact action equality. Arbitrary route decimals therefore failed
  correlation after a successful bounded semantic prefix and left the player
  waiting past the host's next-action deadline; binary-exact bootstrap
  coordinates concealed the mismatch.
- No route, hazard, combat, stealth, or movement-controller behavior changes.
  Focused contract validation: 9/9 wrapper tests. The `linux/amd64` image passed
  the required `/player` and navmesh SDK import verification after repulling a
  corrupt local base-image cache.
- Request `xreq_da0a07c1-01e1-415d-be8d-48c810a30e14` was cancelled while all
  24 episodes were still pending after noticing that v339 did not yet re-enable
  the reverted clear-road semantic call site. It provides no gameplay evidence.

## v338 - use semantic continuation on clear supported road (2026-08-10)

- Version UUID: `ffe16d87-adc0-49e2-98a7-61233875d625` (`wowborg:v338`,
  uploaded inert; not submitted).
- Uses `move_to` only on clear, non-jumping, non-precise supported-road legs so
  the 0.1.209 semantic continuation controller can move across observation
  horizons. Bounded terrain, hazards, combat, and precise arrivals retain the
  proven vector controller.
- Canonical-spawn request `xreq_49630412-6627-4ca2-8a30-6be7d562af7b` is
  complete with 24 episodes and 24 traces. Every run reached direct 01, issued
  its first semantic `move_to`, and then failed direct 02 with `no_frame`.
  Semantic continuation is rejected on the current canonical route; source is
  restored to the safe manual controller.

## v337 - remove periodic settled-pulse waits (2026-08-10)

- Version UUID: `a2f3ac6a-4eff-42b9-a89f-da3de2f952f9` (`wowborg:v337`,
  uploaded inert; not submitted).
- Restores the safe v332 movement durations, then removes the unconditional
  wait inserted after every eight settled movement pulses. Per-pulse
  observations, hazard holds, collision recovery, and stall detection remain;
  only controller idle frames are removed.
- Canonical-spawn request `xreq_0efbf699-1097-4d6a-acea-2ee910ac6b08` is
  complete with 24 episodes and 24 traces: zero dock arrivals, six deaths, and
  the same direct-292 frontier. Periodic wait removal is safe but provides no
  material throughput gain.

## v336 - use a half-second bounded-terrain stride (2026-08-10)

- Version UUID: `8627e0e0-bbed-4bf7-8719-521ae45e258f` (`wowborg:v336`,
  uploaded inert; not submitted).
- Steps the continuously jumping bounded-terrain input down from v335's failed
  0.75 seconds to 0.5 seconds, halfway between the rejected cadence and the
  proven-safe 0.25-second baseline. All floors, anchors, and near-target/hazard
  precision remain unchanged.
- Canonical-spawn request `xreq_c3a02abc-de61-402f-99c0-cb109c3e1fde`
  reproduced the terrain regression: deaths clustered at direct 100/130 and
  no-progress at direct 96/98. The half-second cadence is rejected, and bounded
  terrain returns to the proven 0.25-second controller.

## v335 - stride continuously through bounded terrain (2026-08-10)

- Version UUID: `e555253b-9224-4a2f-930a-d27891246fcd` (`wowborg:v335`,
  uploaded inert; not submitted).
- Keeps the same bounded floors and dense terrain anchors, but continuously
  jumps through those legs at the existing 0.75-second Traverse input instead
  of forcing every far-from-target pulse to 0.25 seconds. Near-target precision,
  hazard evasion, and terrain hazard holds remain unchanged.
- Canonical-spawn request `xreq_ee95ebf3-b5e3-4d6d-a194-022cfa2667e0`
  exposed a decisive early regression: bounded-band runs clustered in deaths
  and no-progress at direct 91--100. The 0.75-second terrain cadence is rejected.

## v334 - use the accepted clear-road stride limit (2026-08-10)

- Version UUID: `b305a624-cddd-4e5d-8599-2bf208edf0f1` (`wowborg:v334`,
  uploaded inert; not submitted).
- Corrects the v333 clear-road duration from the rejected two seconds to the
  host-proven 1.5-second limit. No route, hazard, form, or terrain behavior
  changes.
- Canonical-spawn request `xreq_c369b998-0509-4d01-8abc-d508152cb86f` is
  complete with 24 episodes. Recovered traces again had zero dock arrivals and
  a maximum of direct 292 despite thousands of accepted 1.5-second clear-road
  strides. The change did not move the frontier, identifying the blanket
  0.25-second bounded-terrain input as the remaining controller bottleneck.

## v333 - lengthen only clear supported-road strides (2026-08-10)

- Version UUID: `86cab30d-fd6f-4c91-9010-8ecdc10c7c60` (`wowborg:v333`,
  uploaded inert; not submitted).
- Uses two-second inputs only on clear, supported road. Hazard steering remains
  one second and bounded terrain remains 0.25 seconds, so the longer stride does
  not weaken either control. Extends bounded control two anchors through direct
  275 after one of 24 v332 runs fell at that first unbounded endpoint.
- Canonical-spawn request `xreq_d9ebf8a9-c47c-4b4d-9f4c-5e288bb4bf41` is
  complete with 24 episodes. Every recovered trace stopped at direct 02 when
  the host rejected `duration=2.0` for vector movement. v333 is rejected; it
  provides no gameplay comparison.

## v332 - separate terrain precision from stealth (2026-08-10)

- Version UUID: `02ebba39-15ca-4ccf-b476-f21617f3d495` (`wowborg:v332`,
  uploaded inert; not submitted).
- Keeps every bounded terrain input, jump floor, and the direct 41--42 Brute
  micro-zone, but uses Travel Form through the bounded bands. The v326 dynamic
  traces recorded no Prowl-triggering hazards from direct 90--215; all dynamic
  stealth starts after direct 80 were isolated at 225, 232--233, and 244 on
  supported road, where the existing avoid/fight router already operated safely.
  This removes blanket Prowl speed loss without reintroducing dynamic switching.
- Canonical-spawn request `xreq_1c77e58c-9b48-4f00-be5b-95c8f4d7f337` is
  complete with 24 episodes and 24 recovered policy traces: zero dock arrivals,
  four deaths, one hazard hold, 27 isolated fights, and a maximum of 292 anchors.
  Median direct-270 time improved from about 254 seconds in v331 to 238 seconds,
  with only one post-80 death beyond the old direct-266/270 seam (at direct 275).
  Removing blanket Prowl is retained, but survivors still exhaust the horizon at
  direct 293.

## v331 - coalesce supported road and bound the direct-266 descent (2026-08-10)

- Version UUID: `c4e7d43a-c72f-4f61-a502-430d5b33e4d7` (`wowborg:v331`,
  uploaded inert; not submitted).
- Coalesces dense Detour samples only on ordinary supported road: 88 longer
  legs skip 162 anchors while remaining within 3.876 yards of the source
  corridor. Every terrain-constrained and named steep/descent anchor remains.
  Extends bounded Prowl through direct 273 after v330 exposed four non-combat
  deaths at direct 266/270 immediately beyond the old band.
- Canonical-spawn request `xreq_2fd6508d-726f-4156-8a12-66d52d410903` is
  complete with 24 episodes and 24 recovered policy traces: zero dock arrivals,
  five deaths, one hazard hold, 829 coalesced-leg events, 427 bounded-edge
  passes, and a maximum of 292 anchors. Coalescing moved the frontier 23 anchors
  beyond v330 and the extended band eliminated deaths at direct 266/270. Four
  deaths occurred at direct 275 immediately after Prowl and bounded control
  ended; the continuing ridge needs bounded support, but blanket Prowl remains
  the dominant route-time cost.

## v330 - restore static terrain stealth with a brute micro-zone (2026-08-10)

- Version UUID: `ee4115ab-8722-48d7-8dc4-9e4a1a14f1ff` (`wowborg:v330`,
  uploaded inert; not submitted).
- Removes dynamic form selection after v326--v329 failed the safety/velocity
  comparison. Restores static Prowl across the proven bounded terrain bands and
  adds only direct 41--42 as a static micro-zone for the Dunemaul Brute. Keeps
  robust form-settlement handling and the vMaNGOS-derived 2.5-yard prowled
  clearance.
- Canonical-spawn request `xreq_ce3d8675-b162-4048-9160-2090b8504b67` is
  complete with 24 episodes and 24 recovered policy traces: zero dock arrivals,
  eight deaths, zero hazard holds, 415 bounded-edge passes, and a maximum of
  269 anchors. The direct 41--42 hold pathology disappeared completely and the
  frontier advanced beyond v325. Four deaths at direct 266/270 had no combat
  events and began after the bounded band ended, exposing the next fall seam.

## v329 - retain stealth through transient hazard dropout (2026-08-10)

- Version UUID: `1c4c8695-8d3a-4fda-95b8-67035106623f` (`wowborg:v329`,
  uploaded inert; not submitted).
- Adds a four-second last-seen grace to the dynamic hazard identity. Once a
  nearby hazard triggers Prowl, transient unit-list dropout no longer clears the
  identity and reopens the form transition; a visible hazard refreshes the
  grace until it is actually beyond the 40-yard exit band.
- Canonical-spawn request `xreq_a745c768-84cf-4b7f-889f-529edac2399d` is
  complete with 24 episodes and 24 recovered policy traces: zero dock arrivals,
  16 deaths, zero hazard holds, and a maximum of 269 anchors. Last-seen grace
  reduced Prowl events from 537 to 328 and stealth exits from 208 to 120, but
  deaths and useful route velocity did not improve. Dynamic form switching is
  rejected in favor of the safer v325 static-band baseline.

## v328 - align dynamic stealth entry and exit bands (2026-08-10)

- Version UUID: `cf0121e9-9a12-4667-aaa7-610abd705378` (`wowborg:v328`,
  uploaded inert; not submitted).
- Only hazards within the 30-yard entry radius now trigger Prowl; their identities
  retain stealth until 40 yards. Cat/caster form transitions wait through up to
  four settled pulses for delayed aura state before failing. This removes v327's
  far-lookahead add/remove loop while preserving its vMaNGOS-derived 2.5-yard
  prowled clearance.
- Canonical-spawn request `xreq_a395a08c-d629-4463-9a75-5a8ac41b94cd` is
  complete with 24 episodes and 24 recovered policy traces: zero dock arrivals,
  16 deaths, zero hazard holds, and a maximum of 269 anchors. Restricting entry
  to 30 yards reduced stealth starts from 1,689 to 284, but transient unit-list
  dropout still cleared identities and reopened form transitions. Ten deaths
  clustered at direct 71, and the frontier did not improve over v327.

## v327 - retain Prowl until the triggering hazard is clear (2026-08-10)

- Version UUID: `22b3322c-c6d5-40a0-a6b8-b515da169d7d` (`wowborg:v327`,
  uploaded inert; not submitted).
- Adds hazard-identity hysteresis: once a unit triggers Prowl, the router remains
  prowled until that unit is at least 40 yards away. Cat Form waits one settled
  pulse before declaring its transition failed, and Travel Form now completes
  the caster-form-to-Travel transition in one helper call. These changes address
  v326's Prowl-clearance oscillation without changing its fight/stealth decision
  or clearance thresholds.
- Canonical-spawn request `xreq_70048874-a283-4631-b19f-5d4d6c4528d2` is
  complete with 24 episodes and 24 recovered policy traces: zero dock arrivals,
  13 deaths, zero hazard holds, and a maximum of 270 anchors. Hysteresis moved
  the frontier 22 anchors beyond v326, but 60-yard lookahead hazards were still
  being added to the stealth set and immediately removed by the 40-yard exit
  rule: 1,689 stealth starts and 1,511 ends. Form transitions also continued to
  see delayed aura updates.

## v326 - switch forms dynamically around live hazards (2026-08-10)

- Version UUID: `b04c53ec-87bd-4c16-8e3f-11918bfbd304` (`wowborg:v326`,
  uploaded inert; not submitted).
- Removes blanket Prowl from the terrain bands. The router now uses Travel Form
  by default, retains the existing isolated-weak-attacker fight gate, enters
  Prowl only when a live route hazard is present, and returns to Travel Form
  once clear. Bounded terrain jumps remain enabled while prowled around a
  hazard. Prowled hazard clearance is 2.5 yards: vMaNGOS floors creature stealth
  detection at 1.5 yards, plus one yard of collision margin for this level-60
  template against ordinary route mobs.
- Canonical-spawn request `xreq_16750d76-56c3-4af0-99c5-a8508b58dc4e` is
  complete with 24 episodes and 24 recovered policy traces: zero dock arrivals,
  14 deaths, zero hazard holds, and a maximum of 248 anchors. The first dynamic
  implementation oscillated between forms: 2,584 Prowl events, 628 Travel-form
  exits, and 559 Travel-unavailable events. Prowl often activated successfully,
  but its lower clearance removed the triggering unit from the immediate hazard
  set, so the router instantly tried Travel Form and rediscovered the hazard.

## v325 - bound the direct-213 and direct-259 fall sites (2026-08-10)

- Version UUID: `76651003-5bba-4508-85c7-c0a97ce94a88` (`wowborg:v325`,
  uploaded inert; not submitted).
- Continues the first bounded Prowl band through direct 215, then adds a separate
  short band from the direct-258 climb through the direct-263/264 descents. The
  long supported road between them remains in Travel Form. In v324, all four
  direct-213 failures began after Prowl ended at 205 and all four direct-259
  failures began immediately after the direct-258 climb; both sites used open,
  non-jumping strides and fell far below their route elevations.
- Canonical-spawn request `xreq_6de10926-77ab-4ff1-a0e6-591f89cf37bf` is
  complete with 24 episodes and 24 recovered policy traces: zero dock arrivals,
  six deaths, 244 terrain holds, 253 bounded-edge passes, and a maximum of 262
  anchors. The direct-213 cluster disappeared. Every non-death `no_frame`
  terminal occurred at the 270-second episode horizon, including the scattered
  direct-221--263 endpoints; these are budget exhaustion, not a new failure
  cluster. All 244 hazard holds occurred at direct 41--42 around a Dunemaul
  Brute, before the old blanket-Prowl range began.

## v324 - keep the direct-188--205 ridge in bounded Prowl (2026-08-10)

- Version UUID: `68a92c45-e5fc-4d46-8aa9-b8dd7f316f65` (`wowborg:v324`,
  uploaded inert; not submitted).
- Extends bounded jump floors and terrain-aware Prowl from direct 188 through
  the known direct-196/200/205 descents, following the route's z-profile. In
  v323, every failure in the new direct-189--196 cluster began after Prowl ended
  at direct 188: the controller issued a 1.0-second open stride without jumping
  and immediately fell 30--60 vertical yards. No failure involved combat or a
  hazard transition.
- Canonical-spawn request `xreq_253f6b98-42ef-4af2-b842-46acd1adca63` is
  complete with 24 episodes and 24 recovered policy traces: zero dock arrivals,
  six deaths, 62 terrain holds, 228 bounded-edge passes, and a maximum of 258
  anchors. The direct-189--196 cluster disappeared completely and the frontier
  advanced by 63 anchors. The new deep clusters were four failures at direct
  213 after Prowl ended at 205, and four at direct 259 immediately after the
  direct-258 climb; both sites used non-jumping open strides and fell far below
  their route elevations. One run also lost its frame at direct 205 and one at
  215.

## v323 - accept supported bounded edges planarly (2026-08-10)

- Version UUID: `b4f2c079-58ed-450c-83f4-3039e59bc0a9` (`wowborg:v323`,
  uploaded inert; not submitted).
- A bounded terrain leg now counts as passed once the character is within that
  leg's planar arrival radius and safely at or above its target elevation. This
  is the bounded analogue of the existing climb-edge acceptance rule: v322's
  deepest direct-178 and direct-183 traces had already reached supported ground
  beside their targets, but exact 3D arrival continued steering toward lower
  navmesh z-coordinates until observations stopped.
- Canonical-spawn request `xreq_22a89c57-161d-44af-ba87-d89b696f1667` is
  complete with 24 episodes and 24 recovered policy traces: zero dock arrivals,
  nine deaths, 59 terrain holds, 222 bounded-edge passes, and a maximum of 195
  anchors. The bounded acceptance eliminated every direct-178/182/183/187
  failure and moved the frontier beyond v321's direct 186. The new cluster was
  five failures at direct 189, two at 191, one at 192, and three at 195--196;
  each trace crossed the direct-188 Prowl boundary into a 1.0-second open stride
  with no jump, then fell 30--60 vertical yards without a combat or hazard
  transition.

## v322 - support the direct-178--188 physical corridor (2026-08-10)

- Version UUID: `5a8f0601-075f-4f2a-a3b1-dbb51e9a33a4` (`wowborg:v322`,
  uploaded inert; not submitted).
- Raises direct 178's bounded jump trigger from z=2 to z=4, adds bounded floors
  across the previously unclassified direct-181--187 descent and climb, and
  keeps Prowl/terrain holds through the direct-188 climb. In v321, all three
  direct-178 failures crossed the edge near z=3 before the old trigger; the
  direct-182 trace fell from z=-24 to z=-114 on its first open stride; and the
  direct-187 trace stalled below the next rise at z=-16. No trace showed a
  hazard or combat transition at failure.
- Canonical-spawn request `xreq_148f6c93-f5c4-4ccf-bd37-770776ecbb60` is
  complete with 24 episodes and 24 recovered policy traces: zero dock arrivals,
  four deaths, 88 terrain holds, and a maximum of 182 anchors. The old clustered
  direct-178/182/187 failures fell to one direct-178 and one direct-183 loss.
  Both deepest traces reached a supported shelf planarly beside the target but
  remained well above its navmesh z-coordinate; exact 3D arrival then kept
  steering until the next observation was lost. This shows the remaining issue
  is bounded-leg acceptance rather than another unsupported gap.

## v321 - support the direct-176 descent through its climb handoff (2026-08-10)

- Version UUID: `5e905ccd-34eb-466f-b7c7-8e085fa56ec9` (`wowborg:v321`,
  uploaded inert; not submitted).
- Adds a bounded direct-176--179 band with a z=2 to z=-2 floor and keeps
  Prowl/terrain holds through the existing direct-180 climb. In the first 23
  recovered v320 traces, six deep runs cleared the entire new 162--174 basin;
  five then died falling at direct 178 and one lost its frame at 177. Those
  traces contain no hazard or combat transition, so this is the next adjacent
  physical gap rather than another routing-mode boundary.
- Canonical-spawn request `xreq_c87daf51-1134-4e8e-984c-814f3ea0a2ff` is
  complete with 24 episodes and 24 recovered policy traces: zero dock arrivals,
  eight deaths, 285 terrain holds, and a maximum of 186 anchors. The new band
  moved the deep frontier from direct 177 to direct 186. Three runs lost their
  next frame at direct 178 after crossing the edge near z=3 before the z=2 jump
  floor activated; one fell to death at direct 182 immediately after its first
  open stride; and one lost its frame below the rise at direct 187. None of the
  five traces contained a hazard or combat transition at failure.

## v320 - support the direct-162 basin through its climb handoff (2026-08-10)

- Version UUID: `238e5b41-61dd-4747-9465-45a65f0cbd73` (`wowborg:v320`,
  uploaded inert; not submitted).
- Classifies direct 162--174 as one bounded physical band, with floors following
  the route's z=22 to z=-2 basin, and keeps Prowl/terrain holds through the
  existing continuous climb at 175. In the first 23 recovered v319 traces the
  prior direct-152/153 failures disappeared completely, but four deep runs died
  falling at direct 162--165. The band starts high enough to activate before
  the observed first drop and ends immediately before the already-classified
  climb controller.
- Canonical-spawn request `xreq_e406dcbd-cbd5-430f-b217-2e415a265895` is
  complete with 23 of 24 policy traces recoverable: zero dock arrivals, ten
  deaths, 76 terrain holds, and a maximum of 177 anchors. Six deep runs cleared
  direct 162--174; five then died falling at direct 178 and one lost its frame
  at 177. The final episode completed but did not expose a policy artifact.
  A recurrent missing cached Docker parent
  snapshot required the same clean-layer rebuild used for v318; the unchanged
  canonical build path then passed before upload.

## v319 - keep the later physical corridor in Prowl (2026-08-10)

- Version UUID: `00a6aa73-9b94-4282-9bad-7eee18b46777` (`wowborg:v319`,
  uploaded inert; not submitted).
- Extends the established later Prowl/terrain-constrained band from direct 151
  through direct 169 without changing geometry or bounded floors. A failing
  v318 trace arrived at 151 under supported Prowl, then canceled Cat Form at
  152, saw a hazard, switched to lateral hazard steering (which correctly
  disables jumping), and immediately fell through the physical corridor.
  Remaining in Prowl makes the level-aware terrain hold authoritative until the
  bounded band and the newly exposed later gaps are clear.
- Canonical-spawn request `xreq_6076bd6d-6682-4f23-b207-f4db502147b5` is
  complete with all 24 traces: zero dock arrivals, seven deaths, 70 terrain
  holds, and a maximum of 164 anchors. The direct-152/153 failure cluster
  disappeared completely. Four deep runs instead died falling at direct
  162--165, validating the later Prowl boundary and isolating the next physical
  basin.

## v318 - bridge the direct-151 descent into the next climb (2026-08-10)

- Version UUID: `3ed29742-e852-49b3-8e7d-bdca5c16ccc2` (`wowborg:v318`,
  uploaded inert; not submitted).
- Adds bounded support across direct 151--155, with floors descending alongside
  the navmesh from z=10 to z=-5. All four v317 deep runs reached direct 150 at
  full health, then immediately fell below the world while targeting 151 and
  died around z=-94; no hostile unit or combat transition was involved. The
  band ends where the existing continuous climb controller begins at direct
  156, so the two controllers meet without overlap or a new uncontrolled gap.
- Canonical-spawn request `xreq_6d80fdd0-81d5-4da1-a21e-5d5430fb8d91` is
  complete with all 24 traces: zero dock arrivals, nine deaths, 309 terrain
  holds, and a maximum of 168 anchors. Three runs failed at direct 152/153
  after the Prowl boundary restored lateral hazard evasion inside the physical
  gap. Three deeper runs died falling at direct 162, 167, or 169, establishing
  the next unsupported band after the existing 156--158 climb. The first
  cached build hit a missing
  Docker parent snapshot during the canonical sanity run; a clean layer rebuild
  repaired the store, after which the unchanged project build path passed.

## v317 - carry bounded support to the far side of the direct-140 void (2026-08-10)

- Version UUID: `fa0a1e89-aa2d-4448-9265-930f826f3f3d` (`wowborg:v317`,
  uploaded inert; not submitted).
- Extends v316's validated z=8 bounded support from direct 140 through direct
  145, the last low anchor before the route returns to a z=14 surface at 146.
  All six deep v316 runs arrived at 140, proving the first supported half, then
  immediately began falling again while targeting 141 and failed there. The
  underlying void therefore spans the far-side acquisition, not just the first
  guidepoint.
- Canonical-spawn request `xreq_a0eec157-95b7-495f-aadf-063a6a003314` is
  complete with all 24 traces: zero dock arrivals, 12 deaths, 193 terrain
  holds, and a maximum of 150 anchors. The support band cleared direct 140--145
  and moved the frontier ten anchors. Four deep runs then fell below the world
  at direct 151 and died; their health stayed full until fall damage, confirming
  another physical gap rather than combat or stealth failure.

## v316 - support the direct-140 collision seam (2026-08-10)

- Version UUID: `5e3f672f-218a-4ebe-b068-00c174e4c0c5` (`wowborg:v316`,
  uploaded inert; not submitted).
- Adds the proven altitude-gated bounded jump controller only at direct 140,
  with a floor matching its z=8 navmesh surface. Five v315 deep runs entered
  the leg around z=14, fell below z=0 within five movement pulses, and then
  either wedged near z=-26 or continued below the world. A rare v311 survivor
  crossed the same void and was reset onto the far-side surface near z=10;
  this turns that nondeterministic fall/reset into the same bounded physical
  crossing already validated at direct 93--112 and 118--129.
- Canonical-spawn request `xreq_55bfa48a-e699-4566-be27-9b1b40bf28ae` is
  complete with all 24 traces: zero dock arrivals, three deaths, 251 terrain
  holds, and a maximum of 140 anchors. All six deep runs arrived at direct 140,
  then all six failed at direct 141. The z=8 support activated as designed and
  moved the frontier exactly one anchor; the physical void continues through
  the next low-surface targets.

## v315 - decouple later Prowl from tight guidepoint arrival (2026-08-10)

- Version UUID: `ca2f1e2a-6448-459f-af39-49bee459203b` (`wowborg:v315`,
  uploaded inert; not submitted).
- Keeps direct 90--129 both Prowled and tight-arrival for the proven collision
  gaps, but lets direct 130--151 use ordinary eight-yard/crossed arrival while
  remaining Prowled and terrain-constrained for hazard holds. In the first 20
  v314 traces the direct-71 death cluster disappeared, but four deep runs
  stopped at direct 139/140 because extending stealth had also imposed a
  three-yard arrival radius on this later non-gap band.
- Canonical-spawn request `xreq_d9359a4b-bb15-4dfe-904b-761557049b5a` is
  complete with all 24 traces: zero dock arrivals, three deaths, 301 terrain
  holds, and a maximum of 139 anchors. Five deep runs again failed at direct
  140. Relaxing the arrival radius therefore preserved v314's survival gain
  but did not move the frontier; direct 140 is a physical collision seam.

## v314 - reject early Prowl in the direct-70 hive (2026-08-10)

- Version UUID: `12c2566e-f037-4238-9a23-9f34acd0c8b8` (`wowborg:v314`,
  uploaded inert; not submitted).
- Restores the Prowl start from direct 70 to direct 90 while retaining v313's
  useful extension through direct 151. Four matched cohorts make the choice
  decisive: v307's Travel plus ordinary hazard routing before direct 90 had
  four deaths, while v308--v311 early-Prowl cohorts had 15--20 deaths. A v312
  social pull began at 10.9 reported yards despite corrected hold hysteresis.
  Travel/avoid-or-fight is therefore safer through this hive; Prowl remains for
  the later collision/hazard band.
- Canonical-spawn request `xreq_823f0236-4a45-45b2-913f-b51b336f1f93` is
  complete with all 24 traces: zero dock arrivals, seven deaths, 225 terrain
  holds, and a maximum of 139 anchors. Only one run died at direct 71, versus
  eleven in v313. Five deep runs failed at direct 139/140, confirming that the
  remaining shared blocker was the overly tight later arrival rule rather than
  early hazard handling.

## v313 - keep Prowl and terrain constraints through direct 151 (2026-08-10)

- Version UUID: `49ff4e27-943f-469d-b2cb-3c384b40283e` (`wowborg:v313`,
  uploaded inert; not submitted).
- Extends the Prowl/terrain-constrained corridor from direct 129 through direct
  151. Three v311 runs cleared the post-117 gap and reached direct 150, then a
  visible Sandreaver triggered ordinary lateral hazard evasion after the
  constrained band ended; all three left the narrow collision surface and died
  falling while targeting 151. The corrected v312 level-aware hold now remains
  active across this observed hazardous band instead.
- Canonical-spawn request `xreq_fcb072d2-7e98-46ae-988c-753ddde9f2cd` is
  complete with all 24 traces: zero dock arrivals, 12 deaths, 151 terrain
  holds, and a maximum of 139 anchors. Eleven runs died at direct 71 under the
  intentionally retained early-Prowl control. Three deep runs failed at direct
  140, so extending the constrained band prevented the earlier direct-151
  hazard-evasion falls but coupled ordinary later terrain to an unnecessary
  three-yard arrival rule.

## v312 - use required clearance for terrain-hold entry and release (2026-08-10)

- Version UUID: `dba534d0-87a9-4f04-bebb-ff25b9c88228` (`wowborg:v312`,
  uploaded inert; not submitted).
- Makes the level-aware required hazard clearance authoritative for both
  terrain-hold entry and release. V310 held level-49 mobs at 7.4--7.9 yards,
  then released them as soon as their projected patrol segment looked clear
  even though their current distance remained seven yards; two then aggroed at
  7.1 and 5.0 yards. Holds now begin at the computed ten-yard clearance and
  release only when both current distance and projected path are clear.
- Canonical-spawn request `xreq_dd897233-796e-4386-b4cc-2a10a46d3f76` is
  complete with all 24 traces: zero dock arrivals, 12 deaths, 137 terrain-hold
  entries, and a maximum of 144 anchors. Ten runs still died at direct 71.
  One representative social pull began with a Silithid Swarm reported at 10.9
  yards and immediately became two attackers. Consistent ten-yard hysteresis
  reduced v310's 19 deaths but remained substantially worse than v307's
  pre-direct-90 Travel behavior, so early Prowl is rejected independently of
  this hold correction.

## v311 - catch the post-ledge fall at its navmesh surface (2026-08-10)

- Version UUID: `f4e82f34-1605-439e-99ee-7fd2a813f653` (`wowborg:v311`,
  uploaded inert; not submitted).
- Raises the bounded physical floor only at direct 118--120 from z=14 to z=20,
  matching those anchors' z=20--22 navmesh surface. Early v309 failures fired
  40--90 jump pulses and reached target x/y, but the z14 gate activated after
  they had already lost collision and they fell to z=-2 through z=-26. The
  lower direct 121--129 band remains at z=14.
- Canonical-spawn request `xreq_c06e22ed-2335-4098-bb69-a009691abc9b` is
  complete with all 24 traces: zero dock arrivals, 20 deaths, and a maximum of
  150 anchors. Thirteen runs died and two exhausted their deadline at direct
  71 under the known early-Prowl regression. Three runs crossed the z20 band,
  reached direct 150, and died falling at 151 after unconstrained hazard
  evasion. The raised catch plane is validated; early Prowl and the post-129
  unconstrained band are independently rejected.

## v310 - retain hazard clearance while moving in Prowl (2026-08-10)

- Version UUID: `73929a33-a889-42d5-bcb0-35566573ba93` (`wowborg:v310`,
  uploaded inert; not submitted).
- Removes the stealth-route bypass around hazard routing. V308 entered Prowl
  successfully before direct 70 but then walked straight within 3.3--5.3 yards
  of level-49 mobs and pulled them, because stealth had disabled all clearance
  logic. The existing terrain-constrained eight-yard hold now remains active in
  Prowl; form selection and all clearance thresholds are otherwise unchanged.
- Canonical-spawn request `xreq_48a27283-a5ab-4123-8492-77b62e7ff2d8` is
  complete with all 24 traces: zero dock arrivals, 19 deaths, 110 terrain hold
  entries, and a maximum of 117 anchors. Seventeen runs still died at direct
  71. A representative trace held mobs at 7.4--7.9 yards, then released because
  their projected path looked clear while their current distance was still
  seven yards; two immediately aggroed at 7.1 and 5.0 yards. Preserving hazard
  routing was necessary but the hold hysteresis remained internally
  inconsistent.

## v309 - maintain a physical floor after the direct-117 ledge (2026-08-10)

- Version UUID: `612d2935-93a4-45b2-bac5-650b31141416` (`wowborg:v309`,
  uploaded inert; not submitted).
- Adds the existing bounded-gap controller across direct 118--129 with a z=14
  physical floor and 64 translating pulses per anchor. Three early v307 traces
  cleared direct 117, entered direct 118 around z=26, then lost collision
  support near z=13--14 and fell below the world before direct 119. Continuous
  climbing ends at 117; this band receives altitude-gated support instead.
- Canonical-spawn request `xreq_4d6bf2af-2965-4e40-aaf8-b901755eefcd` is
  complete with all 24 traces: zero dock arrivals, eight deaths, and a maximum
  of 118 anchors. Six runs repeated v308's direct-71 stealth-clearance death.
  Three deep survivors failed at direct 118 or 119. Those runs fired 40--90
  bounded pulses and reached target x/y, but the z14 gate activated after
  collision was already lost and they fell to z=-2 through z=-26.

## v308 - enter Prowl before the northern Tanaris multi-pull band (2026-08-10)

- Version UUID: `c96f80af-7006-4ed6-945e-2e2c5b3340c8` (`wowborg:v308`,
  uploaded inert; not submitted).
- Extends the local Prowl corridor from direct 90--129 to direct 70--129. V306
  deaths at direct 71--74 began as hostile pulls and often escalated to two to
  four attackers; the character can kill one level-47/48 ordinary mob but the
  resulting multi-add escape is lethal. Route geometry, combat selection, and
  the v307 ledge climb are unchanged.
- Canonical-spawn request `xreq_c3cfdc44-363d-4bd1-9632-4d892328c32d` is
  complete with all 24 traces: zero dock arrivals, 15 deaths, and a maximum of
  118 anchors. Eleven runs died at direct 71 and one at direct 70. Prowl did
  activate successfully, but the stealth branch bypassed hazard clearance and
  walked within 3.3--5.3 yards of level-49 mobs. Starting Prowl earlier without
  respecting its residual detection radius was a severe regression.

## v307 - extend the northern ledge climb through direct 117 (2026-08-10)

- Version UUID: `985330a7-9281-4b6e-b0b8-8ef7efd3890a` (`wowborg:v307`,
  uploaded inert; not submitted).
- Extends the existing continuous climb segment at direct 113--114 through
  direct 115--117. V306 repeatedly reached direct 115 but then stalled or fell
  at the adjacent 115--117 physical ledge despite the nominal navmesh heights
  looking nearly flat at its foot.
- Canonical-spawn request `xreq_455dd7b7-03d9-4fdc-a075-fa255124d031` is
  complete with all 24 traces: zero dock arrivals, four deaths, and a maximum
  of 118 anchors. Fourteen deep runs failed at direct 118 or 119. The added
  climb reliably cleared 115--117, then runs entered direct 118 near z=26,
  lost collision support around z=13--14, and fell below the world. This
  establishes a bounded post-ledge gap rather than another continuous climb.

## v306 - reserve bounded pulse budget for forward crossings (2026-08-10)

- Version UUID: `dea44c7f-49fe-48af-aa7a-d04d72b5d15a` (`wowborg:v306`,
  uploaded inert; not submitted).
- Retains v305's altitude-gated jump support on turn-only frames, but counts
  only translating jump frames against the finite 64-pulse crossing budget.
  In v305, direct 96--98 spent roughly half their pulses rotating and then fell
  after exhausting the budget below the collision floor.
- Canonical-spawn request `xreq_93b7dd09-e591-47ee-9383-da416210e128`
  recovered all 24 traces: zero dock arrivals, eight deaths, and a maximum of
  115 anchors. Three runs failed while targeting direct 116. Reserving the
  budget for translating frames restored v304's frontier, but did not improve
  survival enough; the next independent blocker is the physical ledge from
  direct 115 through 117.

## v305 - preserve collision-gap lift during turn-only steering (2026-08-10)

- Version UUID: `fc256c44-d48e-4fd7-a13b-b0bbe55516c3` (`wowborg:v305`,
  uploaded inert; not submitted).
- Extends bounded physical-floor jumping to turn-only steering frames. Those
  frames previously stripped `jump`, so curved corrections inside a collision
  gap could consume enough unsupported frames to pull the character below the
  world even with an unexhausted pulse budget.
- Canonical-spawn request `xreq_e243aa4e-a449-437f-ac36-4a3efb806b04`
  recovered all 24 traces: zero dock arrivals, six deaths, and a maximum of 114
  anchors. Ten runs reached direct 114 and then failed at 115; four failed at
  direct 96. Deep traces showed direct 96--98 spending 34--35 of their 64
  pulses on turn-only frames before falling, so preserving lift while rotating
  was correct but charging those frames to the forward budget was not.

## v304 - enlarge collision-gap pulse budget (2026-08-10)

- Version UUID: `6c530aab-7f2a-4c31-a3f3-26c4b643c844` (`wowborg:v304`,
  uploaded inert; not submitted).
- Raises the per-anchor physical-floor pulse budget from eight to 64 while
  retaining v303's two calibrated floor bands.
- Canonical-spawn request `xreq_9dcfa9b9-aaa5-4a06-915c-09c7c8cd9918`
  recovered all 24 traces: zero dock arrivals, seven deaths, and a maximum of
  115 anchors. A representative direct-108 failure used all 64 jump pulses and
  202 movement actions yet fell to z=-196. It got within 1.57 planar yards of
  the target, but turn-only steering frames stripped jump and repeatedly lost
  altitude. The larger budget therefore exposed a steering-action bug rather
  than a remaining budget shortage.

## v303 - physical-floor cadence across the two northern collision gaps (2026-08-10)

- Version UUID: `6c0b0c39-47bc-41bb-917f-358fa642f0f8` (`wowborg:v303`,
  uploaded inert; not submitted). Two image-upload attempts returned HTTP 500
  before version creation; the third identical upload succeeded.
- Replaces target-relative bounded jumping with explicit physical floors and up
  to eight cadence pulses per anchor: z=3 across direct 93--99 and z=-8 across
  direct 104--112. Direct 108 leaves the continuous-climb set; direct 113
  remains the next true uphill climb.
- Canonical-spawn request `xreq_86db541c-b200-4433-8557-d1b1b505a786`
  recovered all 24 traces: zero dock arrivals, eight deaths, and a maximum of
  115 anchors. Six runs died at direct 106 or 108 after exhausting all eight
  pulses; three crossed both gaps and reached direct 115 or 116. This proved
  both physical floors and the second collision-gap boundary, while showing
  that eight pulses were insufficient for correction-heavy crossings.

## v302 - altitude-capped bounded jump cadence (2026-08-10)

- Version UUID: `f3ca595f-58e3-4635-b264-36d0a6af531a` (`wowborg:v302`,
  uploaded inert; not submitted).
- Retains v301's signed terrain classes and v300's five-pulse maximum, but
  emits a bounded jump only while no more than five yards above the current
  target. This spreads lift across a gap instead of spending every pulse at its
  start and then falling below the mesh.
- Canonical-spawn request `xreq_54c704f0-6f17-4c0a-9b8d-d44042d4c558`
  recovered all 24 traces: zero dock arrivals, ten deaths, and a maximum of 103
  anchors. Four runs died falling while targeting 104. A successful crossing
  still fell to z=-90 and depended on the host snapping it back near direct99,
  proving target-relative altitude is invalid inside this collision gap.

## v301 - classify generated steep anchors by vertical direction (2026-08-10)

- Version UUID: `b34026a9-e825-4f43-b71d-d713cb7b2b5e` (`wowborg:v301`,
  uploaded inert; not submitted).
- Splits the absolute-grade-generated steep set by sign: uphill anchors retain
  continuous climb steering; 27 downhill anchors remain exact and
  terrain-constrained without jumping. The calibrated direct 92--99 seams are
  unchanged.
- Canonical-spawn request `xreq_6c99c6a5-443c-40e4-9d4f-50769f34cf33`
  recovered all 24 traces: zero dock arrivals, four deaths, and a maximum of 95
  anchors. Eighteen surviving runs failed from direct 94 through 96, so the
  signed descent behavior remained unreachable behind the unchanged upfront
  jump cadence.

## v300 - five bounded jump pulses across northern seams 93--99 (2026-08-10)

- Version UUID: `5075d2d1-623c-4cc2-8b8a-e9b77e2227fe` (`wowborg:v300`,
  uploaded inert; not submitted).
- Raises only the direct 93--99 bounded jump budget from three to five pulses.
  The v299 trace reached the target x but was still 3.3 yards short laterally
  and already below the mesh; two additional supported translations should
  complete the crossing before exact steering releases jump.
- Canonical-spawn request `xreq_36c39dbe-0eac-46b7-87c8-21a29cb7de59`
  recovered all 24 traces: zero dock arrivals, two deaths, and a maximum of 103
  anchors. Five pulses reliably cleared direct 93; three runs failed at 94 and
  fourteen at 95. One run reached 103 and then died landing at 104, confirming
  both that five pulses can bridge the first gap and that remaining downhill
  anchors must not use continuous climb steering.

## v299 - bounded jump pulses across northern seams 93--99 (2026-08-10)

- Version UUID: `55a6ae0d-a2b2-4787-bad8-cf7c65310241` (`wowborg:v299`,
  uploaded inert; not submitted).
- Implements the previously inert bounded-jump budget in the road controller.
  Direct 92 keeps one pulse; direct 93--99 receive three initial jump pulses,
  followed by ordinary exact steering so the character can cross each gap
  without accumulating continuous upward velocity.
- Canonical-spawn request `xreq_3c9b4a76-d199-49d7-9b61-d3f70b51efd0`
  recovered all 24 traces: zero dock arrivals, three early deaths, and a hard
  maximum of 92 anchors. Sixteen runs failed at direct 93. All three bounded
  pulses fired; the final supported trajectory reached target x but fell below
  the mesh before completing the remaining lateral correction.

## v298 - single-pulse the northern 92--99 seams (2026-08-10)

- Version UUID: `73c6b6c0-2249-485f-aca9-41739e7d07ed` (`wowborg:v298`,
  uploaded inert; not submitted).
- Replaces continuous jumping with one jump pulse per exact anchor from northern
  direct 92 through 99. v297 proved that continuous pulses launched the
  character roughly 70 yards above the downhill route before a lethal landing.
- Canonical-spawn request `xreq_ced7de9c-2122-456b-abfb-0ae1f121a0fe`
  recovered all 24 traces: zero dock arrivals, three early deaths, and a hard
  maximum of 92 anchors. Seventeen runs failed at direct 93 (`no_frame`,
  `no_progress`, or deadline). One pulse briefly held altitude, but the
  character fell through the gap after roughly three non-jump translations.

## v297 - repair the northern direct-92 jump seam (2026-08-10)

- Version UUID: `c9e51e97-0c45-49b1-8c58-b132ec55f380` (`wowborg:v297`,
  uploaded inert; not submitted).
- Retains v296's local Prowl band and adds `tanaris-northern-direct-92` to the
  explicit jump seams. In 17/24 v296 traces, the character reached direct 91,
  attempted the rising direct-92 edge without jumping, and fell through the
  cliff mesh; this version changes only that missing jump classification.
- Canonical-spawn request `xreq_f5291be7-1e2c-488f-9e19-ed203730611b` recovered
  all 24 traces: zero dock arrivals and 21 deaths. The missing direct-92 jump was
  repaired and the best run reached direct 103, but 13 runs died landing at
  direct 100 after repeated jump pulses had launched them to z=60--70 on a
  route near z=-5. The failure is terrain control, not combat or broken Prowl.

## v296 - stealth only through the Centipaar cliff band (2026-08-10)

- Version UUID: `eb2ab302-3ecb-454a-be24-f04b2b725d18` (`wowborg:v296`,
  uploaded inert; not submitted).
- Uses Cat Form and Prowl, exact arrivals, and terrain-constrained steering only
  for northern direct anchors 90--129; every other clear segment remains in
  Travel Form with six-yard hazard bypass.
- Canonical-spawn request `xreq_61463e30-2a85-4aa0-898e-ac30acc020b0` recovered
  all 24 traces: zero dock arrivals, three early route deaths, and a maximum of
  92 arrived anchors. Seventeen runs reproduced the same no-progress failure at
  direct 92 after slipping below the world, isolating a missing jump seam rather
  than a stealth or combat failure.

## v295 - exact jump treatment for the first northern cliff seams (2026-08-10)

- Version UUID: `65480360-6b30-4e8d-a2ff-7cbd75e388fa` (`wowborg:v295`,
  uploaded inert; not submitted).
- Retains v294's six-yard hazard router and adds exact continuous-jump steering
  at northern seams 41--42 and 93--99.
- Canonical-spawn request `xreq_7abd5e60-1740-44d4-ae9d-1cf7fced2097` advanced
  the best trace from anchor 95 to 133, but seven of the first eleven recovered
  traces died and many fell below the world around anchors 100--111. The result
  identified the Centipaar cliff band as the next terrain-and-aggro boundary.

## v294 - bounded hazard bypass on the northern route (2026-08-10)

- Version UUID: `24a54f48-922e-48a3-a49c-a92da76a7c91` (`wowborg:v294`,
  uploaded inert; not submitted).
- Re-enables hazard-aware lateral selection with a six-yard bypass/rejoin
  corridor while keeping only computed steep anchors exact.
- Canonical-spawn request `xreq_fdba63bb-9c25-494d-a662-6835fb2e82dc` improved
  survival to three deaths in the first eleven traces and reached anchor 95.
  Deterministic stalls at 41 and falls around 94--95 established the first two
  explicit jump seams.

## v293 - exact northern anchors with full melee fallback (2026-08-10)

- Version UUID: `26a47462-b7eb-4993-a56f-be0cfdc30fd3` (`wowborg:v293`,
  uploaded inert; not submitted).
- Makes every northern direct anchor exact and terrain-constrained, disabling
  broad corridor passing and hazard drift while retaining full melee fallback.
- Canonical-spawn request `xreq_f69c9313-4726-4ae1-abb2-8cc34c69d34b` reached
  anchor 92, but 12 of the first 13 recovered traces died. Individual level
  45--49 fights were winnable in roughly 3--10 seconds; repeated Petrifier,
  Ogre, and Centipaar contacts were cumulatively lethal. Global fight-through
  routing was rejected in favor of local bypass or stealth.

## v292 - collision-faithful current-navmesh northern route (2026-08-10)

- Version UUID: `2f9291fe-9ddc-4fde-ba51-c6509d8d7e60` (`wowborg:v292`,
  uploaded inert; not submitted).
- Expands the old safe opening and the current northern continuation into 419
  one-yard-error navmesh anchors, preserving collision geometry that the coarse
  route discarded.
- Canonical-spawn request `xreq_2325cd0a-d91b-45d5-bdc0-0302b930e12c` survived
  and reached anchor 42, but 20-yard hazard detours drifted outside the narrow
  navmesh corridor and stalled. The route was retained; broad avoidance was not.

## v291 - bootstrap the reconstructed northern route (2026-08-10)

- Version UUID: `d7809458-95d0-48e1-a5ca-04b82056e8fd` (`wowborg:v291`,
  uploaded inert; not submitted).
- Prepends the proven current-host southwest movement bootstrap to v290's
  reconstructed v78 opening.
- Canonical-spawn request `xreq_a42f6646-d31c-40e5-b03c-332f0f61aac9` passed
  the opening timeout, but nine of the first eleven traces died and the best
  reached only anchor 10 before the old sparse bypass chord fell below world.

## v290 - reconstruct the v78 northern opening (2026-08-10)

- Version UUID: `e243b209-4443-48e1-a5ca-04b82056e8fd` (`wowborg:v290`,
  uploaded inert; not submitted).
- Reconstructs v78's historical safe opening endpoints on the current navmesh,
  then joins the dense current northern continuation.
- Canonical-spawn request `xreq_ecd48cc0-49e8-40d4-b23d-46cf549a884b` failed at
  the first target: current-host southwest `move_to` produced a 30-second
  no-frame timeout. The geometry remained useful after adding the known
  movement bootstrap.

## v289 - probe the generated movement-duration contract (2026-08-10)

- Version UUID: `5c46e289-f433-4889-965a-d98a303f4468` (`wowborg:v289`,
  uploaded inert; not submitted).
- Requests 2.5-second clear movement strides on the restored v280 mountain
  route, matching the generated field schema's advertised maximum of five.
- Canonical-spawn request `xreq_4a246a5b-62a1-4699-b272-3a6b79be0c57` imported
  in all 24 episodes but failed at the first 2.5-second translation: the exact
  image has a cross-field `move_vector` validator capped at 1.5 seconds. The
  source returned to one-second Travel Form and 1.5-second stealth strides.

## v287-v288 - first current-navmesh northern-direct candidate (2026-08-10)

- Version UUIDs: v287 `9cac825e-9d76-4338-8364-0b3f49b4beda`; v288
  `a95d0bfd-8e4c-4ee2-8ed9-b4d4669536dc` (uploaded inert; neither submitted).
- v287 introduced the direct northern Detour path but failed policy import
  because a `frozenset` was unioned with a dict. v288 fixed the import without
  changing the route.
- Canonical-spawn request `xreq_041a1f3a-1e49-4f3e-a985-321c13f6a017` recovered
  all 24 v288 traces: zero dock arrivals and 16 deaths. The eight-yard-simplified
  route cut collision corners and exposed too many hazards, motivating a dense
  current-navmesh reconstruction.

## v277-v286 - establish the retained stealth corridor and reject local variants (2026-08-10)

- Version UUIDs: v277 `ce9f6c60-e1f4-4ea4-a48b-e89c7799d2d0`; v278
  `fd85a3f9-2ee8-4bd7-9d51-79598b7e2f5c`; v279
  `3fa82773-261e-4a86-bf25-ca11077a94df`; v280
  `917fe984-05d8-4488-b9be-5b0bc945e9b3`; v281
  `f99511ad-bbd9-48ef-a1d7-9d589f8a67aa`; v282
  `5765dbd5-7483-49a9-9057-9072fd3029f4`; v283
  `2c099e1e-20dc-4cad-b2ac-bac1c4d9a64a`; v284
  `493553ee-9605-4736-b689-50729536c389`; v285
  `848ef3cb-c528-4cb6-b757-78ec97020e29`; v286
  `3425dcf4-20ce-4493-83dd-46f6549296eb` (all uploaded inert; none submitted).
- v277 and v278 progressively extended Prowl across the direct Flats corridor
  and produced 6/24 and 4/24 dock arrivals. v279 extended stealth through the
  central road and west gap, producing 19/24 south-road arrivals with no deaths.
  v280 retained that geometry, used 1.5-second strides only on clear stealth
  legs, and produced 21/24 arrivals with no deaths; this is the retained
  downstream behavior.
- v281's ten-yard ordinary-road precision threshold also produced 21/24 and was
  behaviorally neutral. v282's post-gap long strides regressed to 11/24. Road-9
  combat/stealth variants v283--v286 produced only 1, 0, 0, and 1 arrivals,
  respectively, with eight aggregate deaths. Those variants were rejected.
- Requests: v277 `xreq_a9e02953-d3b5-4131-bd6e-8e043ceef040`; v278
  `xreq_2897605e-9994-4c92-a4d9-6a8c2e8591ec`; v279 south-road
  `xreq_05e35f02-ed69-4042-9369-3e5c8330bacb`; v280 south-road
  `xreq_2ae2ced4-dc21-41c2-b3f4-3c77e9cb6bc8`; v281
  `xreq_3f916f6b-1d72-451c-9582-097802ea7e90`; v282
  `xreq_9721f3dc-207b-4f76-8261-456329b989b4`; and v283--v286 road-9
  `xreq_6d3a26a0-2928-4b1b-ac94-b6484194b213`,
  `xreq_adf270c7-de65-4958-87d5-e3976cc3664f`,
  `xreq_56feae84-96eb-4bc0-b58a-53b27ad38a3f`, and
  `xreq_fc5dcfb6-66fb-424e-964a-7091be2b8f44`.

## v276 - prowl across the direct Flats corridor (2026-08-10)

- Version UUID: `2503acd0-0616-4364-9293-1c70938a102e` (`wowborg:v276`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Retains v275's shorter Detour-derived corridor, but uses Cat Form and Prowl only from direct point
  1 through central road 1 and follows the verified corridor without ordinary enemy detours. Travel
  Form resumes at central road 2. All later route, combat fallback, and terrain control are unchanged.
- South-road evaluation pending.

## v275 - take the direct Detour corridor across Shimmering Flats (2026-08-10)

- Version UUID: `a1fc74c7-0888-40a8-81db-a5fb855a0dc2` (`wowborg:v275`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Replaces the authored 1,427-yard south-road-to-central-road approach, including its collision-heavy
  fence gap and dense central corridor, with eight meaningful turns simplified at three-yard
  tolerance from the real 1,279-yard Detour corridor. The endpoint, controller, hazard behavior,
  central/west roads, west gap, and Great Lift approach are unchanged.
- South-road request `xreq_9bda9df8-8277-42c5-ab28-0a0a76aa735f` completed all
  24 episodes but produced only two trace-confirmed lower-dock arrivals and four route deaths.
  Successful median move actions fell from v261's 662 to 583, proving the corridor is materially
  more efficient, but direct exposure to the Flats hazard field erased the conversion gain. The
  route remains for a corridor-scoped stealth test.

## v274 - hold forward across verified clear road (2026-08-10)

- Version UUID: `6f57cbb3-9d1c-44d1-a4a8-e2a2ca23f874` (`wowborg:v274`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Restores v254's collision behavior after v273. On a non-terrain downstream road leg only, when
  already aligned within 22.5 degrees, more than 70 yards from the target, and with the existing
  60-yard hazard lookahead completely clear, uses the supported raw-input contract to hold W during
  one five-simulation-second wait, then explicitly releases it. All turns, gaps, hazards, combat,
  and nearby arrivals retain the proven per-observation controller.
- South-road request `xreq_3faae541-056b-4ccf-9ad9-9b9265f410b8` completed all
  24 episodes but every run timed out on its first raw-input action without moving. Hosted headless
  observations support `wait`, `move_vector`, `move_to`, `face`, and `invoke`, but not `input`;
  the general contract is unavailable in this runtime. Held input is rejected and removed.

## v273 - recover blocked fence pulses immediately (2026-08-10)

- Version UUID: `73abe1d4-5178-4520-98fe-685ff895da0b` (`wowborg:v273`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Restores v254's quarter-second control on every fence anchor. Extends the existing immediate
  jump-sidestep collision recovery to the five fence legs only, instead of waiting for the
  four-second generic stall detector when a precise crossing pulse moves less than half a yard.
  Geometry, ordinary movement, hazards, and every other terrain segment are unchanged.
- South-road request `xreq_57cbe984-6c59-459c-ba0a-f05fccd5066b` completed all
  24 episodes but produced only five trace-confirmed lower-dock arrivals at a 202.9-second median.
  The new recovery fired a median 139 times in successful runs, inflating median move actions from
  v261's 662 to 967. Sub-half-yard fence movement is normal precise control rather than a collision
  signal, so the special recovery is rejected and removed.

## v272 - midpoint fence-gap control (2026-08-10)

- Version UUID: `fbf3c54a-614c-482f-b22a-ab0dd1df166f` (`wowborg:v272`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Uses 0.375-second precise pulses across all five Shimmering Flats fence-gap anchors, midway
  between v254's stable quarter-second crossing and v270/v271's faster but unstable half-second
  crossing. All route geometry and non-fence behavior remain unchanged.
- South-road request `xreq_42d28b8b-d22a-49e9-84a7-caab23912f3d` completed all
  24 episodes and produced six trace-confirmed lower-dock arrivals at a 175.9-second median. Median
  fence moves fell to 75, but nine runs still failed in the crossing and two characters died later.
  The midpoint remains below baseline reliability, so all fence legs return to quarter-second
  control.

## v271 - acquire the fence before half-second control (2026-08-10)

- Version UUID: `35f6ef3f-9218-4da3-bf65-4a529dbe56fc` (`wowborg:v271`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Retains v270's half-second pulses on fence-gap points 2--5, but restores quarter-second control
  on point 1 where v270 introduced five acquisition failures. All anchors, downstream behavior,
  and non-fence cadence remain unchanged.
- South-road request `xreq_6befc5af-83a4-454c-b490-3dfd0a6f3472` completed all
  24 episodes but produced only three trace-confirmed lower-dock arrivals. Restoring precise entry
  control removed v270's point-1 expiries, but eight runs then expired at point 2 and two died near
  the crossing. Half-second interior control is rejected; the next version tests the midpoint.

## v270 - half-second control only inside the fence gap (2026-08-10)

- Version UUID: `3634b0d2-f7f5-4813-93d0-a6361dae21dc` (`wowborg:v270`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Restores all five fence anchors after v269. Only the five Shimmering Flats fence-gap legs use
  half-second precise pulses; every other precise terrain segment retains v254's quarter-second
  control. This isolates the crossing that consumed roughly 84 precise move actions per successful
  v261 run.
- South-road request `xreq_421708ca-373f-4bde-9ae2-8531bac6c0d1` completed all
  24 episodes and produced six trace-confirmed lower-dock arrivals at a 181.2-second median. Median
  fence move actions fell from v261's 121 to 65 and successful total moves from 662 to 619, but five
  runs expired while acquiring fence-gap point 1 and one character died later. Applying the longer
  pulse at the crossing entry is rejected; point 1 returns to quarter-second control.

## v269 - hold the Shimmering Flats fence-gap bearing (2026-08-10)

- Version UUID: `cab25e7f-46b6-43b3-a7a6-fc550a6ee567` (`wowborg:v269`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Restores v254's one-second cadence after v268. After acquiring fence-gap point 1, skips the three
  collinear interior targets and jumps directly toward point 5. The exact crossing endpoints,
  quarter-second jump control, hazard behavior, and all downstream geometry are unchanged.
- South-road request `xreq_81708ab2-ce00-4bea-83b0-882a4d475b52` completed all
  24 episodes but produced zero lower-dock arrivals. Eighteen traces expired or stalled while
  targeting fence-gap point 5, proving that the three skipped interior anchors are required for
  collision guidance. The fence skip is rejected and removed.

## v268 - lengthen only tightly aligned clear-road pulses (2026-08-10)

- Version UUID: `457469c8-16da-4a5d-bd8d-ec3b99c6aef2` (`wowborg:v268`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Restores every v254 downstream guidepoint after v267. Requests the 1.5-second contract maximum
  only when the character is within 22.5 degrees of the target, remains more than 20 yards away,
  and has no visible hazard; diagonal corrections, hazards, constrained terrain, and precise
  arrivals retain their proven cadence.
- South-road request `xreq_ec860344-69b5-4d43-bf18-0c9723584b25` completed all
  24 episodes but produced only two trace-confirmed lower-dock arrivals and two route deaths.
  Successful runs requested a median 145.5 long pulses yet saved only eight move actions versus
  v261, showing that longer requested duration did not translate into useful controller progress.
  The aligned long stride is rejected and removed.

## v267 - skip redundant central-road bearings (2026-08-10)

- Version UUID: `401f389b-5ee5-42f7-b63f-de9e924df454` (`wowborg:v267`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Restores v254's forms and hazard behavior after v266. Skips five nearly collinear intermediate
  targets in the Thousand Needles central corridor and the 2.7-degree midpoint on the following
  straight road. Movement durations, route endpoints, combat, avoidance, gaps, and terrain control
  are unchanged.
- South-road request `xreq_c3527729-905b-4120-8cb9-232b5728da6d` completed all 24
  episodes but produced only six trace-confirmed lower-dock arrivals at a 195.5-second median. Two
  characters died on the route, and successful median move
  actions rose from v261's 662 to 701 because the longer compressed legs induced extra hazard
  steering. The downstream skips are rejected and removed.

## v266 - stealth only through the central-road hazard belt (2026-08-10)

- Version UUID: `6bd489a1-2978-4e42-8411-ebc950521da4` (`wowborg:v266`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Restores v254's one-second cadence after v265. Uses Cat Form and Prowl with straight bearings only
  on Thousand Needles central road 2, where recovered traces cluster the Snarler/Cougar/Boulderkin
  settlement failures. Exiting Cat does not consume the following leg's single Travel Form attempt.
- South-road request `xreq_1d92d024-04c9-4296-9a2e-80b4af826800` kept all 24
  characters alive but produced only six lower-dock score-band runs. All 24 policy traces were
  recovered: Prowl and Travel Form both activated as intended, yet central road 2 retained its
  characteristic 30-second `no_frame` failures. Narrow stealth is rejected and removed; this
  bottleneck is more consistent with route geometry or terrain than enemy aggro.

## v265 - shorten only timeout-prone road actions (2026-08-10)

- Version UUID: `9859229e-1733-4938-8cf5-a2c6f989f282` (`wowborg:v265`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Restores v254's steering after v264. Only Thousand Needles central roads 2/3 and west road 1 use
  0.75-second open translations; recovered v261 traces attributed 11 of 16 non-arrivals to exact
  30-second settlement timeouts, with these three legs accounting for every terminal intent.
- South-road request `xreq_34e8b0f6-4449-4353-bdf9-1b32ea9dd2c3` produced only seven dock-band
  runs. In 22 recovered traces, central road 2 still caused seven `no_frame` timeouts and two
  deaths; successful arrivals slowed to a 192.0-second median. The shorter cadence is rejected and
  removed from the active source.

## v264 - face hazard detours before translating (2026-08-10)

- Version UUID: `6765a188-5757-44bb-b8fc-08cd6f20d877` (`wowborg:v264`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Restores v254's conservative fixed-corridor hazard admission after v263. Only hazard avoidance
  and evasion waypoints use a 22.5-degree turn-before-move gate, replacing long normalized diagonal
  vectors with stationary alignment followed by full-speed straight movement.
- South-road request `xreq_f27e5f6d-8325-4156-adfb-fb0ffb7781e9` kept all 24 characters alive and
  produced eight lower-dock score-band runs. In recovered arrival traces, median diagonal actions
  fell only from 237 to 222 while turn-only actions rose from 30.5 to 56. Stationary hazard
  alignment is rejected and removed from the active source.

## v263 - compute hazard clearance per enemy (2026-08-10)

- Version UUID: `9a895521-5fde-4fa8-98c1-37ae52638887` (`wowborg:v263`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Completes v262's hazard-admission correction: each enemy's projected path and every lateral
  candidate are compared with that enemy's own level-derived aggro radius. Side selection and
  emergency evasion use the worst per-enemy clearance margin; unknown enemies remain conservative.
- South-road request `xreq_3c05b7b7-51f5-43de-b0cb-b50d043c64b5` kept all 24 characters alive but
  produced only five lower-dock score-band runs. Per-enemy admission converted conservative early
  steering into later emergency evasion and is rejected; the active source restores v254's fixed
  detection corridor and global worst-case clearance.

## v262 - admit only aggro-relevant path hazards (2026-08-10)

- Version UUID: `7ad1baea-a191-4fa5-80d8-627e75130646` (`wowborg:v262`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Restores v254's form and movement behavior after v261. Immediate and lookahead enemies enter
  lateral avoidance only when their projected path clearance is inside the existing level-aware
  aggro requirement (including three yards of slack), rather than an unrelated fixed 18 yards.
- South-road request `xreq_8b198ece-052c-4323-93b1-2c1b7266bf73` kept all 24 characters alive and
  produced nine trace-confirmed lower-dock arrivals at a 182.8-second median. Avoidance activations
  and diagonal actions did not fall because the maximum tracked-unit clearance still governed all
  enemies. The global threshold is rejected; the active source computes per-enemy margins.

## v261 - reacquire Travel Form after combat (2026-08-10)

- Version UUID: `3f336f4f-dce2-4883-b4d2-a799b6fcbcdd` (`wowborg:v261`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Restores v254's movement cadence after v260. The one-attempt-per-leg Travel Form latch now resets
  only after an observed fight or escape ends, allowing one legitimate speed recovery without
  reviving the terrain-seam recast loop fixed in v242.
- South-road request `xreq_939750ae-7750-4c45-8edc-21f420335bad` kept all 24 characters alive and
  produced eight trace-confirmed lower-dock arrivals at a 194.5-second median, versus v243's ten at
  174.2 seconds. Combat recovery is rejected and removed from the active source.

## v260 - keep full cadence through soft bearings (2026-08-10)

- Version UUID: `12d441d6-0684-4823-9b04-3d563e08045e` (`wowborg:v260`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Restores v254's four-pulse lower-ramp acquisition after v259. Ordinary crossed-bearing road legs
  retain their one-second cadence through the final 20 yards instead of slowing to quarter-second
  pulses. Exact terrain, gaps, the final dock approach, active hazards, and evasion remain precise.
- South-road request `xreq_a7470287-42af-440e-9c73-019e3975c8ee` kept all 24 characters alive and
  produced eight trace-confirmed lower-dock arrivals at a 195.6-second median, versus v243's ten at
  174.2 seconds. Soft bearings require their final precision; the cadence change is rejected and
  removed from the active source.

## v259 - shorten the lower-ramp straight acquisition (2026-08-10)

- Version UUID: `a6358f0b-27ee-41a7-b33a-0fd91f068856` (`wowborg:v259`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Restores v254's quarter-second upper-ascent control after v258 and reduces only ascent point 4's
  bounded straight-jump acquisition from four pulses to three. The retained point-4-to-16 skip and
  all downstream route control are unchanged.
- In the first 22 terminal runs from road-9 request
  `xreq_eda2679c-10d5-4a6f-b76e-b41cedd23223`, all characters remained alive but none reached the
  dock and ten collapsed around the ramp-base score band of 311--320. The shorter acquisition is
  rejected, and the active source restores v254's four pulses.

## v258 - lengthen only the stable upper-ascent hold (2026-08-10)

- Version UUID: `f0c86c20-25ab-4012-b8fc-120f3c038d9b` (`wowborg:v258`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Restores v254's lower-ascent control and uses half-second precise pulses only on the direct
  point-4-to-16 upper-ascent hold. All other precise terrain pulses remain quarter-second.
- In the first 20 terminal runs from road-9 request
  `xreq_c6d42a35-026d-4ece-870c-5050fd9590f2`, two scored zero and nine collapsed around score
  319; only one reached the lower dock. The longer upper-ascent pulse is rejected, and the active
  source restores quarter-second precise control.

## v257 - jump straight across each lower-ascent edge (2026-08-10)

- Version UUID: `3988ad5a-280a-4c8b-aa3e-793b6317575b` (`wowborg:v257`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Restores the required lower-ascent points 1--3 after v256, but prohibits jump-strafe while
  traversing each point's shared bearing. V254's upper-ascent skip remains active.
- The first 23 terminal runs in road-9 request
  `xreq_64462c2e-319c-41f7-b53e-5934b7acfad8` all survived but produced zero dock arrivals; the
  maximum score was `1770.6264`. Straightening the lower verified edges is rejected, and the active
  source restores v254's lower-ascent control.

## v256 - hold both collinear ascent bearings (2026-08-10)

- Version UUID: `194c8265-da6c-4a6c-8ee6-e8477e637e4e` (`wowborg:v256`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Retains v254's point-4-to-16 upper-ascent skip and also jumps directly from ramp base to ascent
  point 3 along their single measured bearing. The point-3-to-4 turn remains separately acquired.
- In the first 13 terminal road-9 episodes from request
  `xreq_29362b26-5c1b-412f-8f73-0a2b22794b8f`, all characters survived but none passed the
  ramp-base region; the maximum score was `313.1164`. The lower direct hold is rejected, and the
  active source restores all three height anchors.

## v255 - keep moving through safe downstream turns (2026-08-10)

- Version UUID: `e81429b3-694e-4d46-b64e-ce751bf53fc0` (`wowborg:v255`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Retains v254's collinear ascent skip. On safe, non-jumping, non-terrain downstream turns of at
  most 90 degrees, combines forward motion with the existing quarter-second turn instead of
  rotating in place. Combat, hazards, gaps, and precise terrain turns are unchanged.
- Road-9 request `xreq_8d34f8c6-2b1f-49e1-8514-a24a75932e2b` kept all 24 characters alive but
  produced zero dock arrivals; its best score stopped at the central-road-2 plateau. Moving turns
  are rejected, and the active source restores v254's in-place turn control.

## v254 - hold the collinear upper-ascent bearing (2026-08-10)

- Version UUID: `53de1ad9-2420-423d-bf99-3c2bf3aa586d` (`wowborg:v254`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Retains v250's bounded straight-jump acquisition at ascent point 4, then skips redundant
  collinear points 5--15 and jumps directly to point 16 on the same measured bearing. All other
  route, hazard, combat, and downstream control is unchanged.
- Road-9 request `xreq_70685708-df99-49d3-aa71-6c0c5420f5d5` kept 23 of 24 characters alive and
  produced one lower-dock arrival. Seven runs reached the central-road-2 score plateau. This is the
  first dock arrival from the road-9 fixture, so the collinear skip remains active, but downstream
  conversion is not yet consistent. Canonical request
  `xreq_98cb87c6-ee69-423b-9f33-03abd08ce5b4` kept all 24 characters alive but produced no dock
  arrivals. Four reached the south-road score plateau, matching v250's count but leaving
  insufficient downstream horizon.

## v253 - use navmesh movement on individual open road legs (2026-08-10)

- Version UUID: `15927173-1b73-427f-8998-d971eb3ca269` (`wowborg:v253`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Retains v250's bounded ascent fix and uses the existing supervised server-side navigator only on
  eight individually named, navmesh-connected open downstream road legs. Gaps, corridors, and the
  final dock approach retain the authored precise controller.
- South-road request `xreq_e116a1a3-f35c-4934-929c-af75b58c0214` completed all 24 episodes without
  an infrastructure failure, but every run had the identical near-zero score `4.5371`. Individual
  `move_to` actions are therefore unusable in this fixture just like the longer v246/v251
  navigations. The navmesh branch is rejected and removed.

## v252 - stride only on named open downstream roads (2026-08-10)

- Version UUID: `6cfa9a00-8c38-476e-8461-a36f3e7b6264` (`wowborg:v252`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Retains v250's bounded straight-jump ascent and requests the 1.5-second contract maximum only on
  eight named open downstream road legs. Gaps and narrow corridors retain proven precise control.
- South-road request `xreq_50c05a9b-5a04-43ac-b595-c5d679b4fc92` completed all 24 episodes without
  an infrastructure failure but produced zero dock arrivals. Four runs reached the pre-dock
  1,943--1,947 score plateau; none reached the dock's distinct 1,968.27 score. The selected longer
  strides are rejected; the active source restores one-second vector control.

## v251 - ask Detour to route the full downstream crossing (2026-08-10)

- Version UUID: `9a0fe881-ccf3-4381-a09f-3bd02c61deeb` (`wowborg:v251`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Replaces the authored route from Shimmering Flats road to Great Lift south road with one
  supervised semantic-navigation request.
- South-road request `xreq_8c21c36d-bd3d-437b-8c6e-e94e170c679a` kept all 24 characters alive,
  but all 24 returned the same `no_progress` failure after 30.2--30.3 seconds with zero
  displacement. The planner reported a 2,857.8-yard route but could not execute it. The bypass is
  rejected; the active source restores the authored downstream route.

## v250 - bound straight jumping at the two costly ascent turns (2026-08-10)

- Version UUID: `abd044c8-c2ef-4873-96fe-43f31102d7cf` (`wowborg:v250`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Suppresses jump-strafe for the first four translating pulses at ascent point 4 and for all
  translating pulses at ascent point 11. All other ascent points retain normal steering.
- Canonical request `xreq_fbac3864-e6ab-4e24-8c82-431c139aac0b` kept 19 of 24 characters alive.
  Fourteen reached the ramp crest at a 189.6-second median and five reached south road at 197.3,
  versus v243's five south-road arrivals at 234.4. No character reached the dock, but this is the
  first large canonical upstream speedup and remains active while downstream control is optimized.

## v249 - jump straight only at ascent points 4 and 11 (2026-08-10)

- Version UUID: `46167607-7fcc-40b7-b40e-a852d08ca56f` (`wowborg:v249`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Prohibits jump-strafe at the two ascent turns identified in v248 while retaining ordinary
  steering everywhere else.
- Canonical request `xreq_64a7165f-ed34-44e2-a5d1-53f261ad7181` kept 22 of 24 characters alive but
  produced only two crest arrivals at a 178.1-second median and no south-road or dock arrivals.
  Point 11 improved, while point 4 remained inconsistent and sometimes trapped the route at point
  3. The unbounded point-4 rule is rejected in favor of a short bounded straight-jump phase.

## v248 - prohibit strafe during every jump (2026-08-10)

- Version UUID: `9d3a9ce8-1fba-4b2e-bb8c-51d1c4faf6db` (`wowborg:v248`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Prevents strafe components on all jumping movement while preserving turn-only alignment and all
  non-jump steering.
- Canonical request `xreq_ad6e1f84-0bf2-4c35-a458-3a1f4c46dcf2` kept 19 of 24 characters alive,
  but only three reached the crest, at a 221.9-second median, and none reached south road. Although
  the two pathological ascent turns became much faster, global straight jumping harmed other
  ascent and descent points. The global rule is rejected.

## v247 - tightly align steep jumps (2026-08-10)

- Version UUID: `e39c59ea-a943-4879-baee-f6daa316dec2` (`wowborg:v247`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- Requires an 11.25-degree bearing before steep jumps and prohibits jump-strafe; ordinary road
  steering, route geometry, combat, and hazard handling are unchanged.
- Ramp-base request `xreq_9203ea6b-9687-4f0f-82ed-3559d6c95e58` kept all 24 characters alive but
  produced zero crest crossings. The tighter gate was below the host turn quantum: every run
  alternated turn-only inputs at ascent point 1, then fell from the unsupported exact diagnostic
  spawn. Tight alignment is rejected. The active source restores the proven 45-degree gate while
  retaining zero jump-strafe for a stable ramp-turn diagnostic.

## v246 - ask Detour to bypass the Shimmering Flats cliff (2026-08-10)

- Version UUID: `e396e767-6f48-4b1c-be4f-2d5b93fba0ef` (`wowborg:v246`, uploaded
  inert; not submitted). Built from uncommitted diagnostic source against canonical vanilla-wow
  0.1.209.
- At road 9, replaces the hand-steered cliff ascent and descent with one supervised semantic
  navigation request to the Shimmering Flats south road.
- Road-9 request `xreq_e9617db4-00d9-403e-8375-fd81bc8ae922` kept all 12 characters alive, but all
  12 returned the identical `no_progress` failure after 30.0 seconds with zero displacement. The
  planner was unavailable and the semantic executor refused the cross-component move. The bypass
  is rejected; the active source restores v243's hand-steered crossing.

## v245 - stride through clear downstream roads (2026-08-10)

- Version UUID: `409807f0-71eb-4ec4-a676-f113281612aa` (`wowborg:v245`, uploaded
  inert; not submitted). Built from source `02b7380` against canonical vanilla-wow 0.1.209.
- Restores v243's quarter-second precise control and uses the contract-max 1.5-second stride only
  on downstream frames where the hazard planner reports a clear path.
- South-road request `xreq_e59ca6ca-be1a-4264-ba87-98b5955ad9a1` kept all 24 characters alive but
  regressed to four lower-dock arrivals at a 193.1-second median, versus v243's ten at 174.2.
  Only 11 characters reached central road 3 and four reached corridor 11. The longer clear stride
  is rejected; the active source restores v243's one-second clear-road cadence.

## v244 - lengthen precise route translations (2026-08-10)

- Version UUID: `7e469dc2-802a-4a52-bd3b-93ea40cd255b` (`wowborg:v244`, uploaded
  inert; not submitted). Built from source `0efa160` against canonical vanilla-wow 0.1.209.
- Raises precise movement translations from 0.25 to 0.5 seconds while retaining v243's periodic
  settlement, route geometry, hazard handling, and combat.
- South-road request `xreq_d5369636-4a50-4aa5-9a79-b686b222a61d` kept all 24 characters alive but
  regressed to four lower-dock arrivals at a 182.6-second median, versus v243's ten at 174.2.
  Eight characters stopped on missing frames at central road 2. The longer precise stride is
  rejected. The active source restores quarter-second precision and instead uses the contract-max
  1.5-second stride only on downstream frames where the hazard planner reports a clear path.

## v243 - reduce exact-route settle waits (2026-08-10)

- Version UUID: `8d3acf50-594c-426a-b486-f9c270afeb9d` (`wowborg:v243`, uploaded
  inert; not submitted). Built from source `139a948` against canonical vanilla-wow 0.1.209.
- Uses the historically proven every-eighth-pulse host settlement yield on all route legs instead
  of yielding after every exact-leg movement. Movement durations, geometry, hazards, and combat
  are unchanged.
- South-road request `xreq_96d83269-fde2-4d1f-b8e0-4982d5c352b2` kept 20 of 24 characters alive
  and produced ten living lower-dock arrivals at a 174.2-second median, versus v242's seven at
  198.7 seconds. Median settle waits fell to 44. Canonical request
  `xreq_fb0f2e97-2b23-4bd0-bfac-192667396315` kept 20 of 24 alive but produced no dock arrivals;
  road 9 improved only to a 104.5-second median, crest to 184.6, and south road to 234.4. The
  active source next tests a half-second precise translation, midway between the proven quarter-
  second control and the rejected 0.75-second terrain stride.

## v242 - continue when Travel Form cannot persist (2026-08-10)

- Version UUID: `2bfed214-38ac-4dec-a833-ad9dade1b913` (`wowborg:v242`, uploaded
  inert; not submitted). Built from source `9be9fbf` against canonical vanilla-wow 0.1.209.
- Attempts Travel Form at most once per road leg, then continues that leg on foot if the form does
  not persist. Final Great Lift precision, route geometry, hazard handling, and combat are unchanged.
- Matched south-road request `xreq_7a24423d-aaf2-4779-b64e-55fa0b4f6650` published 23 of 24 policy
  traces. All 23 traced characters survived; eight cleared the formerly blocking west road 1 and
  seven arrived at the lower dock at a 198.7-second median, versus three dock arrivals and zero
  west-road-1 completions for v241. One completed episode's policy trace remained unpublished.
- Canonical-spawn request `xreq_e06d43c6-d9e8-4dec-b3a2-3c21ac94bcf4` published all 24 traces and
  kept 21 characters alive, but produced no lower-dock arrivals. Thirteen reached the ramp crest at
  a 187.5-second median and only four reached south road before the 270-second horizon. Successful
  traces issued 412–730 redundant settle waits; the active source uses the historically proven
  every-eighth-pulse yield cadence on exact legs instead of yielding after every movement pulse.

## v241 - make the final Great Lift corridor precise (2026-08-09)

- Version UUID: `82cc2a03-54b5-4282-9e31-521563ac8cfc` (`wowborg:v241`, uploaded
  inert; not submitted). Built from source `90165b0` against canonical vanilla-wow 0.1.209.
- Uses quarter-second, terrain-constrained movement for Great Lift corridors 12 and 13 and the
  lower dock; route geometry, upstream movement, hazard handling, and combat are unchanged.
- South-road request `xreq_200bb997-f74d-46d7-a974-b839cd352bee` completed all 24 episodes. Three
  characters reached corridor 11, and all three crossed the formerly blocking final corridor and
  arrived at the lower dock alive in 169.1, 171.5, and 193.3 seconds. The dominant remaining
  failure is earlier: eleven characters reached west gap 7 but then stopped at west road 1 because
  Travel Form dropped at the terrain seam and the control loop repeatedly recast it instead of
  continuing on foot. The active source limits reactivation to one attempt per road leg.

## v240 - use level-aware Travel routing downstream (2026-08-09)

- Version UUID: `d0229362-3730-493f-9354-31084ba8bbe6` (`wowborg:v240`, uploaded
  inert; not submitted). Built from source `a58d6b6` against canonical vanilla-wow 0.1.209.
- Uses Travel Form and the level-aware hazard planner on every downstream leg. Terrain-constrained
  gaps hold their bearing instead of detouring; route geometry and combat are unchanged.
- South-road request `xreq_0f7305a8-d34d-4023-ac88-1257de44b4f2` kept all 24 characters alive.
  Twenty cleared fence gap 5 at a 22.2-second median, ten reached central road 3 at 94.4 seconds,
  five reached west road 3 at 158.5 seconds, and five reached Great Lift corridor 11. All five then
  hit an identical 30-second host action timeout on the second one-second Travel stride toward
  corridor 12. The active source makes only the final corridor 12/13/dock approach precise and
  terrain-constrained.

## v239 - size Tanaris detours from enemy aggro (2026-08-09)

- Version UUID: `2a8a29e8-bef6-4c91-939c-b053d8f47074` (`wowborg:v239`, uploaded
  inert; not submitted). Built from source `40a499e` against canonical vanilla-wow 0.1.209.
- Sizes ordinary clearance from VMaNGOS's level-scaled aggro rule plus three yards instead of a
  fixed 20 yards. At wowborg level 60 versus Tanaris level 40–48 enemies, that is eight to nine
  yards. Adds 10/15-yard lateral candidates and restores the proven one-second stride.
- Canonical-spawn request `xreq_def71fca-e7e8-41e4-8f9f-814c7d65bf79` kept 22 of 24 characters
  alive and moved median road-9 arrival from v234's 130.7 to 102.6 seconds; 15 runs reached road 9,
  14 reached the ramp crest at 192.5 seconds, and five reached south road at 236.8 seconds. The two
  deaths and one-fight median require more validation, but the clearance model materially reduces
  route churn. The active source next applies it to hazard-aware downstream Travel Form, first from
  the south-road diagnostic start.

## v238 - use the maximum valid clear-road stride (2026-08-09)

- Version UUID: `95d83b69-72ca-496f-b31e-6c9e65cf6457` (`wowborg:v238`, uploaded
  inert; not submitted). Built from source `1b870d4` against canonical vanilla-wow 0.1.209.
- Keeps v234's Travel Form and hazard avoidance, but allows the contract-max 1.5-second stride
  whenever the planner reports no path hazard even if off-path enemies remain visible.
- Canonical-spawn request `xreq_62f69df2-5537-4447-a74d-f04be1689395` kept all 24 characters alive
  with no policy errors, but produced no lower-dock arrivals and reached road 9 in only eight runs
  at a 155.6-second median. The longer stride reduced one-second movement actions but did not reduce
  route time, matching the earlier v164 result. The active source restores one-second clear strides
  and instead sizes bypass clearance from VMaNGOS's level-scaled aggro formula.

## v237 - stride through clear Tanaris road segments (2026-08-09)

- Version UUID: `125bf950-bfa2-45c0-9a77-565619d33659` (`wowborg:v237`, uploaded
  inert; not submitted). Built from source `39e67dc` against canonical vanilla-wow 0.1.209.
- Restores v234's Travel Form and hazard avoidance on the ordinary Tanaris road, but requests a
  three-second movement stride whenever the hazard planner reports a clear path. Route geometry,
  hazard thresholds, combat, and all downstream behavior are unchanged.
- Canonical-spawn request `xreq_c8804c74-dbc6-4fbd-b8ed-6f6aabcca9bc` stopped all 24 policies at
  road point 1 because the pinned typed action contract admits at most 1.5 seconds for vector
  movement. No action reached the game. The active source uses that exact contract maximum while
  retaining the planner-clear condition, so visible off-path enemies no longer force one-second
  strides.

## v236 - Prowl through the open Tanaris road (2026-08-09)

- Version UUID: `f7f33e24-c5b9-4d40-bed6-b2dd0b0eb414` (`wowborg:v236`, uploaded
  inert; not submitted). Built from source `2ecd389` against canonical vanilla-wow 0.1.209.
- Uses one Prowl phase on the same straight ordinary Tanaris road points 1–8 rejected in Travel
  Form, then returns to Travel Form before the exact detour and climbs. Route bearings, reactive
  combat, escape, and all later behavior are unchanged.
- Canonical-spawn request `xreq_7978d79f-89cb-4552-a919-0668d9eb6898` produced no lower-dock
  arrivals, killed five of 24 characters, and slowed the nine road-9 arrivals to a 156.3-second
  median. Across the batch, straight Prowl triggered 84 fights taking 374.6 seconds. Stealth alone
  therefore does not make an unsafe bearing safe. The active source restores Travel Form plus
  hazard avoidance, but lets a planner-confirmed clear path use a three-second movement stride.

## v235 - hold the canonical Tanaris road bearing (2026-08-09)

- Version UUID: `b10db6bd-f7b3-4de3-901d-0abeb0c027a4` (`wowborg:v235`, uploaded
  inert; not submitted). Built from source `0bb75e3` against canonical vanilla-wow 0.1.209.
- Holds the authored route bearing in Travel Form for ordinary Tanaris road points 1–8, including
  the existing brute/gazer gate anchors, instead of making lateral hazard detours. Reactive
  single-attacker combat and multi-attacker escape remain active; exact detours, climbs, descent,
  and all downstream behavior are unchanged.
- Canonical-spawn request `xreq_dd0b32ec-0acb-441f-93fb-dea77ca655c6` killed ten of 24 characters
  and slowed the six road-9 arrivals to a 147.9-second median. Runs accumulated four to nine fights,
  so the fight-through route is rejected. The active source uses Prowl rather than Travel Form on
  those same straight road bearings, then returns to Travel Form before the exact detour and climbs.

## v234 - use terrain-aware downstream form phases (2026-08-09)

- Version UUID: `c7c4cfde-78d0-456d-8559-a982cab2a2a4` (`wowborg:v234`, uploaded
  inert; not submitted). Built from source `5fcdec0` against canonical vanilla-wow 0.1.209.
- Uses Travel Form on the clear central-to-west approach, Prowl from west gap 1 through west road 3
  for precise terrain control, then Travel Form on the final Great Lift approach. The measured
  hazard-belt Prowl phase and all route, collision, and combat behavior are unchanged.
- Matched 24-episode south-road request `xreq_5a38f7f4-17e4-4056-8360-13f3e26eec6d` produced twelve
  living lower-dock arrivals at a 226.4-second median, versus v230's eleven at 236.6 seconds. Nine
  failures were host-terminal action timeouts; the remaining three were one pre-phase combat death,
  one west-join stall, and one scoring logout. This is the first phased candidate to exceed the
  all-Prowl baseline, so it advances to canonical-spawn evaluation.
- Canonical-spawn request `xreq_760cd3b5-5e4f-494a-b09e-594c4c8e52b2` produced no lower-dock
  arrivals. The best run reached central corridor 9, but median arrival at Tanaris road 9 was 130.7
  seconds, ramp crest 199.9 seconds, and south road 234.8 seconds. Runs reaching road 9 incurred a
  median 38.5 avoidance starts and 37 evasions before only one fight. The active source therefore
  holds the authored canonical bearing on ordinary Tanaris road points 1–8 while retaining reactive
  combat and escape; exact detours, climbs, descent, and downstream routing are unchanged.

## v233 - switch to Travel Form after the danger belt (2026-08-09)

- Version UUID: `3e36e050-ef89-48d2-a091-d843bde99a3a` (`wowborg:v233`, uploaded
  inert; not submitted). Built from source `654305f` against canonical vanilla-wow 0.1.209.
- Uses the stable hosted hazard map instead of per-frame visibility: Prowl from Shimmering Flats
  through central road 3, then make one transition to Travel Form for the west-road and Great Lift
  corridor. Straight bearings, route geometry, collision recovery, and combat gates are unchanged.
- Matched 24-episode south-road request `xreq_54d556f8-54f1-4e96-88d5-223039dbaebf` produced five
  lower-dock arrivals, kept 23 characters alive, and improved median arrival only to 226.0 seconds.
  Five non-timeout runs stopped at west join 7: Travel Form was safe on the open central approach
  but too fast for the west gap and ravine. The active source uses Prowl again from west gap 1
  through west road 3, then returns to Travel Form for the final open lift approach.

## v232 - switch forms around downstream hazards (2026-08-09)

- Version UUID: `099748ed-96ee-48ba-868c-f1818fc880b1` (`wowborg:v232`, uploaded
  inert; not submitted). Built from source `c72c0ea` against canonical vanilla-wow 0.1.209.
- Restores the proven straight downstream bearings. Clear frames use Travel Form, while any living
  hostile visible within 80 yards triggers Cat Form and Prowl; after combat, the current form is
  explicitly cancelled before Travel Form is recast. Route geometry and combat gates are unchanged.
- Matched 24-episode south-road request `xreq_65424c99-250b-49b5-995d-6bdae790aa45` kept all 24
  characters alive but produced only four lower-dock arrivals at a median 228.5 seconds. Repeated
  visibility transitions caused 20–50 form changes in successful runs, erasing most of Travel
  Form's speed and destabilizing narrow bearings. The active source uses the hosted hazard map
  instead: Prowl through central road 3, then make one Travel Form transition for the enemy-free
  west-road and Great Lift corridor.

## v231 - use hazard-aware Travel Form downstream (2026-08-09)

- Version UUID: `06b5b776-ab43-43e9-9f32-7d944ae79843` (`wowborg:v231`, uploaded
  inert; not submitted). Built from source `cf9d6f6` against canonical vanilla-wow 0.1.209.
- Uses Travel Form after the Shimmering Flats descent and activates the existing hostile-unit
  lookahead and avoidance planner instead of Prowl's straight-line bypass. Route geometry, quick
  downstream collision recovery, and reactive combat gates are unchanged.
- Matched 24-episode south-road request `xreq_ad6109fc-f823-42a2-8858-d1c0d5ef8461` produced no
  lower-dock arrivals and two deaths. Lateral hazard detours repeatedly lost the proven narrow
  fence and central-corridor bearings; after combat, repeated Travel Form casts also failed while
  Cat Form remained active. The active source restores straight bearings, exits the current form
  before Travel Form, and chooses Travel only on clear frames or Prowl while a hostile is visible
  within the existing 80-yard hazard radius.

## v230 - use the current combat cast observation (2026-08-09)

- Version UUID: `5474b742-af2f-48d6-8ca5-ac81a9b86d4f` (`wowborg:v230`, uploaded
  inert; not submitted). Built from source `071d6de` against canonical vanilla-wow 0.1.209.
- Replaces the stale `is_casting` and `casting_spell_id` accesses in ranged combat fallback with
  the canonical `active_cast_spell_id` observation. Route, movement, form, and combat selection are
  otherwise unchanged.
- Matched 24-episode south-road request `xreq_c7cf3680-4742-4d0c-942a-664c260d719a` kept all 24
  characters alive, produced eleven lower-dock arrivals, and produced no policy exceptions. Twelve
  non-arrivals terminated on hosted action-settlement timeouts and one reached the lift corridor
  before scoring logout. Successful arrivals still took a median 236.6 seconds, while ten of the
  timeouts struck before central road 3 after only 67–152 seconds of policy control. The active
  source therefore switches the downstream road from Prowl to hazard-aware Travel Form to finish
  before the timeout window; route geometry and combat gates are unchanged.

## v229 - follow the west-road ravine join (2026-08-09)

- Version UUID: `7451bc60-d94c-4a29-a3f1-486e21f98726` (`wowborg:v229`, uploaded
  inert; not submitted). Built from source `17a2b57` against canonical vanilla-wow 0.1.209.
- Adds seven narrow soft bearings from the canonical Detour path between west road 1 and exact west
  road 2. The downstream corridor and all other behavior are unchanged.
- Matched 24-episode south-road request `xreq_7f7b12ad-ce0a-46c5-8913-a567d16b4589` produced ten
  living lower-dock arrivals, doubling v228's five. Of the fourteen non-arrivals, eight terminated
  on a hosted action-settlement timeout, two reached the lift corridor before scoring logout, two
  hit a stale ranged-combat field access, one died in combat, and one ended before the route. The
  active source fixes the ranged-combat field access; settlement timeouts remain host-terminal.

## v228 - anchor the west corridor on walkable ground (2026-08-09)

- Version UUID: `333f7967-bd44-4f64-bd8d-251540b62fa4` (`wowborg:v228`, uploaded
  inert; not submitted). Built from source `0c0cd91` against canonical vanilla-wow 0.1.209.
- Requires ordinary eight-yard arrival at west road 2 instead of accepting it after crossing the
  broad road envelope. The following Detour corridor and all other behavior are unchanged.
- Matched 24-episode south-road request `xreq_9b2963c0-7892-4586-a871-944d92ead048` kept all 24
  characters alive and again produced five lower-dock arrivals. Exact west-road-2 admission moved
  the former join failure one waypoint earlier: ten runs stopped at west road 1. Navmesh recon
  shows a 142-yard steep ravine path between those nominal road points. The active source inserts
  seven narrow soft bearings through that join while retaining exact arrival at its endpoint.

## v227 - keep corridor bearings on the Detour line (2026-08-09)

- Version UUID: `8bb6a28b-9e84-450b-b381-5956156fd5f1` (`wowborg:v227`, uploaded
  inert; not submitted). Built from source `cffe5ca` against canonical vanilla-wow 0.1.209.
- Adds the omitted first west-corridor join and narrows crossed-bearing admission from 60 to 20
  lateral yards for the three Detour-derived corridors only. All non-corridor road, mountain,
  stealth, combat, and movement behavior is unchanged.
- Matched 24-episode south-road request `xreq_322c1f53-128a-48dd-ba54-e4e50f52d4d7` kept all 24
  characters alive and increased lower-dock arrivals from four to five. Five runs still stopped at
  the west-corridor join because ordinary crossed acceptance marked west road 2 complete 13-16
  yards early at an off-navmesh pose, then immediately passed corridor point 1 without correcting
  the source. The active source requires eight-yard arrival at west road 2 only, so the existing
  corridor begins from its canonical walkable point.

## v226 - follow the Thousand Needles west corridor (2026-08-09)

- Version UUID: `b18e8efb-c2bc-4641-9dc4-8633586dfb37` (`wowborg:v226`, uploaded
  inert; not submitted). Built from source `c8cdf94` against canonical vanilla-wow 0.1.209.
- Adds eleven soft bearings sampled at roughly 50-yard intervals from the canonical Detour route
  between west road 2 and west 3, replacing V225's dominant collision-recovery chord. All earlier
  route geometry, stealth, combat, and movement semantics are unchanged.
- Matched 24-episode south-road request `xreq_4630cf15-2346-4958-9414-6a6fb5b93e78` kept all 24
  characters alive and increased lower-dock arrivals from V225's one to four. Median final world X
  was `-5396`, still behind V225, because four runs could not join the west corridor and two more
  drifted off the central corridor after accepting a bearing within the generic 60-yard lateral
  envelope. The active source adds the omitted 16-yard west join and narrows crossed-bearing
  acceptance to 20 lateral yards for Detour corridor points only.

## v225 - treat downstream corridors as soft bearings (2026-08-09)

- Version UUID: `2e6e67d7-c369-44a4-91ff-6525aef6fb2b` (`wowborg:v225`, uploaded
  inert; not submitted). Built from source `1a2c481` against canonical vanilla-wow 0.1.209.
- Keeps V224's Detour-derived corridor geometry, but lets the ordinary road follower accept each
  bearing after crossing it inside the existing lateral and vertical envelope. Proven mountain and
  obstacle-gap points retain exact semantics; stealth, combat, and movement actions are unchanged.
- Matched 24-episode south-road request `xreq_688069ba-a9b1-4158-a467-cb5047252382` kept all 24
  characters alive, produced one verified lower-dock arrival, and put four more leaders into the
  dock corridor. Median final world X improved from V224's `-5698` to `-5324`, but nine runs spent
  98-203 collision recoveries immediately after west road 2. Navmesh recon shows that direct chord
  conceals a 587-yard rolling ground corridor. The active source adds sparse soft bearings along
  that corridor without changing the now-proven dock approach or any combat behavior.

## v224 - follow navmesh corridors to the Great Lift (2026-08-09)

- Version UUID: `c51a1d37-e700-4f25-b98b-11867ecadc2e` (`wowborg:v224`, uploaded
  inert; not submitted). Built from source `17223ba` against canonical vanilla-wow 0.1.209.
- Replaces the direct east-road-3-to-central-road-1 chord and final south-road-to-lower-dock chord
  with sparse anchors sampled from the canonical VMaNGOS Detour route. These preserve the actual
  switchback and three-chunk dock approach while retaining V223's stealth, collision response,
  combat admission, and downstream gap jumps.
- Matched 24-episode south-road request `xreq_235a9e70-494a-4d54-b40b-dc685d01c25e` removed the
  old east-road-3 direct-line timeout and put two leaders onto the real dock corridor, but exact
  checkpoint semantics created a new repeated overshoot lock at central corridor point 11. Median
  final world X regressed from V223's `-5435` to `-5698`, two characters died, and none reached the
  dock. The active source retains the Detour bearings but restores ordinary crossed-edge acceptance
  for them; exact semantics remain only on the proven obstacle-gap and mountain points.

## v223 - jump through downstream gap lanes (2026-08-09)

- Version UUID: `e0e2accd-451b-467c-9c8b-24ca6bf77669` (`wowborg:v223`, uploaded
  inert; not submitted). Built from source `d108842` against canonical vanilla-wow 0.1.209.
- Adds one aligned jump to each authored downstream gap-lane edge after the first Shimmering Flats
  fence anchor. Each jump is consumed by that single route edge, preserving V219's safe behavior
  everywhere else and avoiding V220's persistent-jump cliff hazard.
- Matched 24-episode south-road request `xreq_2c60eb81-123d-4ca3-aa65-100251e98103` cleared the
  formerly deterministic fence blocker in all 24 runs and advanced median final world X from
  V222's `-6216` to `-5435`; four reached Great Lift south road. One character died in a grouped
  hostile contact and none reached the lower dock. Five runs exposed the same direct-line timeout
  between east road 3 and central road 1, while all four leaders spent the remaining horizon
  collision-stepping toward the dock. Navmesh recon shows those straight chords conceal a 334-yard
  switchback and a 382-yard three-chunk dock approach. The active source adds sparse canonical
  corridor anchors to those two legs without changing stealth, combat, or jump policy.

## v222 - follow dense downstream gap lanes (2026-08-09)

- Version UUID: `59bbe367-7411-403b-a0ab-601a8bb961b3` (`wowborg:v222`, uploaded
  inert; not submitted). Built from source `cc95e3e` against canonical vanilla-wow 0.1.209.
- Expands the two V221 gap anchors into the 12-18-yard point sequences observed in V219's successful
  trace, keeping movement inputs precise through each full obstacle band. Intentional precise
  inputs no longer qualify for long-stride collision detection. All other behavior is unchanged.
- Matched 24-episode south-road request `xreq_d4adf554-8fb3-4ca4-a566-4ed00550faa1` kept all 24
  characters alive, but every run stopped at the first fence-gap point near `world_x=-6216` and
  none fought or reached the dock. Frame-level traces showed the next precise forward inputs
  settling with effectively zero translation before a timeout. The active source assigns one
  aligned jump to each remaining point in the two authored gap lanes; unlike rejected V220, the
  jump state cannot persist beyond the current route edge.

## v221 - route through proven downstream gaps (2026-08-09)

- Version UUID: `d5ec4fb8-b2c6-402e-a9c5-8e27ecc98052` (`wowborg:v221`, uploaded
  inert; not submitted). Built from source `9aabf1e` against canonical vanilla-wow 0.1.209.
- Restores V219's safe one-shot collision response and adds tight canonical anchors at the
  Shimmering Flats fence gap and Thousand Needles west-ridge gap observed in V219's successful
  lower-dock trace. Prowl, combat admission, and every other route segment are unchanged.
- Matched 24-episode south-road request `xreq_6917fbf5-6637-4af9-89ab-08b19fa2bf65` kept all 24
  characters alive, but produced zero dock arrivals and a `world_x=-6193` median. Nineteen reached
  the fence-gap anchor, then the next long stride timed out inside the same obstacle band. The
  active source expands each successful gap trace into a dense lane of 12-18-yard exact anchors,
  keeping inputs short through the full band, and excludes those intentional short inputs from
  collision-slowdown admission.

## v220 - persist short collision recovery (2026-08-09)

- Version UUID: `8e9183e9-2377-4520-b60a-a3e5c7e4076d` (`wowborg:v220`, uploaded
  inert; not submitted). Built from source `7459cc6` against canonical vanilla-wow 0.1.209.
- After a downstream slowdown triggers the proven jump-sidestep, keeps eleven further steering
  pulses short and jump-aware before allowing a long stride. This carries collision recovery beyond
  V219's one normal-looking pulse inside the obstacle band; all other behavior is unchanged.
- Matched 24-episode south-road request `xreq_f6fa4427-33d5-44be-af33-e6d4d20a7dc0` killed 10/24
  characters, with deaths clustered near the Great Lift approach, and produced zero dock arrivals.
  Persistent jumping is rejected. The active source restores V219's safe one-shot response and adds
  tight anchors at the two openings proven by V219's successful dock trace instead.

## v219 - calibrate stealth collision slowdown (2026-08-09)

- Version UUID: `6cbf8e2a-7830-4101-8e2c-4c45f26c3942` (`wowborg:v219`, uploaded
  inert; not submitted). Built from source `671567d` against canonical vanilla-wow 0.1.209.
- Raises only the downstream collision slowdown threshold from 0.75 to four yards, below the
  measured 5.47-yard normal one-second Prowl stride and above V218's 2.83-yard first-blocker pulse.
  The jump-sidestep response and all other behavior are unchanged.
- Matched 24-episode south-road request `xreq_6d70fea0-0c8e-4b46-9c78-e3e4f7dd3a10` kept all 24
  characters alive and produced the first verified living Great Lift lower-dock arrival at
  `world_x=-4675.55`; four more reached Great Lift south road. Consistency still failed: the median
  was `-6034` and twelve runs stopped near the first blocker. Their initial jump-sidestep settled,
  but one normal stride later they were still in the obstacle band and the following long action
  timed out. The active source keeps short jump-aware steering active for eleven pulses after each
  detected collision before trusting long strides again.

## v218 - jump-sidestep blocked stealth strides (2026-08-09)

- Version UUID: `29bdc186-4990-4688-acba-34fb6ff410ae` (`wowborg:v218`, uploaded
  inert; not submitted). Built from source `7aa5612` against canonical vanilla-wow 0.1.209.
- On the downstream stealth route only, treats an intended translation under 0.75 yards as direct
  collision evidence and immediately makes a short alternating jump-sidestep before another long
  stride. Mountain precision, hazard admission, combat, route geometry, and Prowl behavior are
  unchanged from V217.
- Matched 24-episode south-road request `xreq_89d9b253-1fd4-4f9e-8eca-7b4ee04dc49f` kept all 24
  characters alive and four reached Great Lift south road near `world_x=-4910`, the closest living
  progress yet. But 19/24 still stopped at the first blocker and the median regressed to `-6216`.
  The jump-sidestep fired 106 times, proving the response can clear collisions, while the remaining
  first-blocker slowdown still moved 2.83 yards and missed the 0.75-yard gate. The active source
  raises that measured slowdown threshold to four yards.

## v217 - exit Travel Form before downstream Prowl (2026-08-09)

- Version UUID: `1bbd9ec6-4155-46cb-a474-6c31c0aac846` (`wowborg:v217`, uploaded
  inert; not submitted). Built from source `95773cf` against canonical vanilla-wow 0.1.209.
- Before entering Cat Form for the downstream stealth route, cancels any observed non-Cat form
  through the environment's typed aura action. This reuses the hosted-proven combat/descent form
  transition and changes no route geometry, stealth routing, or combat admission from V216.
- Matched 24-episode south-road request `xreq_74d335ea-bb74-46c5-b2c8-9e634bea53b5` kept all 24
  characters alive with zero avoidance/evasion activations or escapes. Nine reached Thousand
  Needles central road 3, but the living median `world_x=-6009` did not beat V213's `-5791`.
  Twelve runs stopped near `world_x=-6216` and the leading runs stopped near `-5473`: in both
  clusters a sub-yard translation was followed by a 30-second action timeout. The active source
  uses that movement feedback to trigger a short jump-sidestep before another long road stride.

## v216 - stealth through the Great Lift road (2026-08-09)

- Version UUID: `9492f0e3-0b45-4510-9df5-aff3615e1bb6` (`wowborg:v216`, uploaded
  inert; not submitted). Built from source `4b05ac7` against canonical vanilla-wow 0.1.209.
- From the first Shimmering Flats road leg through the Great Lift lower dock, enters Cat Form and
  Prowl, follows the canonical road without the Travel-Form hazard controller's long lateral
  detours, and reacquires Prowl after reactive contact. General proactive road combat is removed;
  the separately measured constrained-ramp Scorpid exception remains.
- All 24 episodes in south-road request `xreq_9c9aa999-b3bd-47f9-baa6-cfae007203b2` stayed alive
  but moved zero yards. Diagnostic startup entered Travel Form before route resume, and every Cat
  cast then failed to change forms until the deadline. This is a form-transition null result, not
  a stealth/aggro verdict. The active source reuses the proven typed current-form aura cancellation
  before Cat and Prowl.

## v215 - tighten proactive fight admission (2026-08-09)

- Version UUID: `8c82713a-ee8c-4a2a-b074-1d72ef26ad8e` (`wowborg:v215`, uploaded
  inert; not submitted). Built from source `f9bd53a` against canonical vanilla-wow 0.1.209.
- Proactive road combat now requires at least a 30-level advantage and 90% current health, based on
  V214's measured fast and dangerous tiers. Isolation, range, route, reactive combat, and hazard
  avoidance behavior are otherwise unchanged.
- Matched 24-episode south-road request `xreq_e35be3ac-f9ff-4b0d-bec3-5158266926b0` triggered 72
  proactive fights, but still killed 3/24 characters and moved the living-run median backward from
  V213's `world_x=-5791` to `-5800`. It did not reach the lower dock. This rejects general
  proactive road combat: the active source restores avoidance outside the measured ramp-Scorpid
  exception and explores stealth for the downstream hostile road instead.

## v214 - fight isolated weak road hazards (2026-08-09)

- Version UUID: `6ea438f2-dac9-45a8-9941-85ec549e07c7` (`wowborg:v214`, uploaded
  inert; not submitted). Built from source `51a9b27` against canonical vanilla-wow 0.1.209.
- Proactively fights exactly one isolated ordinary hostile within 20 yards when wowborg has at
  least a 20-level advantage. Stronger or grouped enemies retain V213's avoidance behavior; the
  route, climb/descent, reactive combat, and diagnostic resume gate are unchanged.
- Matched 24-episode south-road request `xreq_15ff799e-b3c2-44eb-8395-868aee60cbd8` reduced
  avoidance/evasion activations from V213's 650/1,117 to 129/67 and triggered 63 proactive fights,
  but 7/24 characters died and the living-run median did not improve. Level-28 fights took about 2
  seconds; level-33/34 fights commonly took 5–14 seconds and removed roughly 700–1,100 health. The
  active source therefore requires a measured 30-level advantage and at least 90% health before a
  proactive fight.

## v213 - resume Traverse at diagnostic starts (2026-08-09)

- Version UUID: `260ec6f4-9c81-4f4b-8181-753b36b7dc41` (`wowborg:v213`, uploaded
  inert; not submitted). Built from source `30ff696` against canonical vanilla-wow 0.1.209.
- When an intentional hosted diagnostic starts north of world X -8000 within 50 yards of the
  canonical route, resumes after its nearest waypoint. The canonical league spawn is outside the
  gate. All canonical-spawn behavior matches restored V212.
- A 24-episode south-road diagnostic (`xreq_00d25795-cc6e-41b9-86f9-62c82dc1fc7a`) resumed correctly
  and kept all 24 characters alive, but none reached the Great Lift; median final world X was
  -5791 and the best reached Thousand Needles central road 2. A representative run reached east
  road 3 in 37 seconds, then spent 126 seconds reaching central road 1 amid 60 avoidance and 83
  evasion activations. Its two accidental level-28 fights took only 2.8 and 1.9 seconds. The active
  source proactively fights one isolated ordinary hostile within 20 yards when wowborg has at
  least a 20-level advantage.

## v212 - restore precise ascent pulses (2026-08-09)

- Version UUID: `d95c5502-bec9-4dff-8178-29bef884502e` (`wowborg:v212`, uploaded
  inert; not submitted). Built from source `b1956f8` against canonical vanilla-wow 0.1.209.
- Restores V210's proven 0.25-second precise climb pulse after rejecting V211's longer stride.
  Height-based climb acceptance, descent, route geometry, combat, and hazard thresholds remain as
  in V210.
- The next source revision can resume at the nearest canonical waypoint when an intentional hosted
  diagnostic starts north of world X -8000 and within 50 yards of the route. The canonical league
  spawn is outside the gate, so normal full-route behavior is unchanged.

## v211 - lengthen clear ascent strides (2026-08-09)

- Version UUID: `7e6df24e-87fd-496d-bcc5-0878d31a0be2` (`wowborg:v211`, uploaded
  inert; not submitted). Built from source `dc8604f` against canonical vanilla-wow 0.1.209.
- Hazard-free steep ascent translations use the existing 0.75-second terrain stride instead of the
  0.25-second precise-arrival stride. Edge acceptance, route geometry, descent, combat, and hazard
  thresholds are unchanged from V210.
- Hosted request `xreq_24848439-065f-4eee-8d67-48ee27b03d36` completed all 48 jobs, but no run
  reached the ramp crest and three characters died. Twenty-six runs reached the ramp base, then
  failed ascent point 1: 0.75-second jump inputs carried wowborg off the narrow ledge before it
  could face the climb, after which turn-only corrections continued falling through the terrain.
  The longer stride is rejected; the active source restores V210's 0.25-second precise pulses.

## v210 - accept crossed ascent edges (2026-08-09)

- Version UUID: `b88c0e66-569b-456d-b2ce-fcf376ef0460` (`wowborg:v210`, uploaded
  inert; not submitted). Built from source `e3a0490` against canonical vanilla-wow 0.1.209.
- Keeps continuous climb jumps, but accepts a steep ascent edge after reaching the target height
  with 3 yards of vertical slack inside an 8-yard planar envelope. Descent, route geometry, combat,
  and hazard thresholds are unchanged from V209.
- The first 47 completed jobs in hosted request `xreq_535fa923-7c60-4c62-9da1-9ce9c251b3fa`
  increased crest completions from V209's 5/48 to 31/47 and reduced median base-to-crest time from
  84.7 to 72.5 seconds. One job remained an infrastructure straggler during analysis. Of the 47,
  two died: one to a level-47 Scorpid near spawn and one after falling on descent point 27. The
  active source removes the remaining 0.25-second precise-input cap from hazard-free climb pulses.

## v209 - accept crossed lower descent edges (2026-08-09)

- Version UUID: `50dc3a2d-b8ad-47a9-af22-8490590d7122` (`wowborg:v209`, uploaded
  inert; not submitted). Built from source `e52051f` against canonical vanilla-wow 0.1.209.
- Preserves V208's one aligned jump per dense descent leg, then accepts the edge when wowborg has
  crossed the target northing plane within the measured 8-yard lateral / 10-yard vertical landing
  envelope. Route geometry, combat, and hazard thresholds are unchanged.
- Hosted request `xreq_f8b2d2ff-4a96-4d67-b35d-c332705f6a48` completed all 48 jobs with 48 living
  characters. Four runs chained beyond descent point 10, reaching points 18, 24, 27, and the south
  road respectively. The complete lower descent took 19 seconds in the best run, validating edge
  acceptance. That run spent 86 seconds on the 16 exact ascent points and reached the south road at
  267 seconds, leaving less than a second of the episode horizon for the open road.

## v208 - jump once per lower descent edge (2026-08-09)

- Version UUID: `7453834b-a830-484d-8518-59345c8bc375` (`wowborg:v208`, uploaded
  inert; not submitted). Built from source `a311ca3` against canonical vanilla-wow 0.1.209.
- Keeps continuous jumps on the proven ascent, but each dense lower descent leg now issues at most
  one aligned jump request and then walks precisely to settle the guidepoint. Combat, hazard
  thresholds, and route geometry are unchanged from V207.
- Hosted request `xreq_2f26f69e-3680-4ea5-9c4c-dbb704fa7836` completed all 48 jobs with 48 living
  characters. Three reached descent point 9, and all three failed point 10. The jump crossed the
  edge, but the closest valid downhill landings remained 4.0–4.5 yards from the navmesh coordinate,
  outside the 3-yard exact arrival radius; exact steering then turned back toward the unreachable
  point. The next source revision accepts the crossed edge once northing passes the target plane
  within the measured landing envelope.

## v207 - finish ranged fallback casts (2026-08-09)

- Version UUID: `71d3f6d7-e2fe-4ead-b69d-d0ab58a106c1` (`wowborg:v207`, uploaded
  inert; not submitted). Built from source `c850f8c` against canonical vanilla-wow 0.1.209.
- While ranged fallback is casting, waits instead of immediately selecting the spell again. Failed
  ranged spell families are remembered so fallback can advance from Moonfire to Wrath. Combat
  admission, the V206 route, and hazard thresholds are unchanged.
- Hosted request `xreq_676b4187-42d4-4eb9-81fc-8cd1adbf2946` kept all 48 characters alive. One
  ranged fallback activated without a death. Three runs reached descent point 9, but continuous
  jump input toward point 10 bounced uphill from about z71 to z94 and oscillated until the episode
  horizon. Jumping prevents the fall but must be limited to one edge-crossing pulse per dense leg.

## v206 - jump from the first lower descent edge (2026-08-09)

- Version UUID: `3adcfa93-82c6-4b4b-bc0d-4846b9a74596` (`wowborg:v206`, uploaded
  inert; not submitted). Built from source `f525838` against canonical vanilla-wow 0.1.209.
- Restores the proven 20-yard global clearance after V205 and moves the existing jump-aware lower
  descent boundary from point 16 to point 10, immediately after V202's last repeatedly proven
  walkable point. Dense bearings and every other behavior match V204.
- Hosted request `xreq_a550e0e8-a6d5-4e70-941f-7f3b2d22bde3` kept 47 of 48 characters alive. Three
  runs reached descent point 9 or later and jump-aware movement progressed through point 12 without
  the prior correction loop, but none reached the south road before the horizon. The death followed
  a quick level-42 win: a proactive level-40 Scorpid fled across the ramp while ranged fallback
  repeatedly restarted cast-time spells before they could land.

## v205 - measured twelve-yard road clearance (2026-08-09)

- Version UUID: `b42b0712-9d24-4319-a490-71f41a41d80c` (`wowborg:v205`, uploaded
  inert; not submitted). Built from source `4d38661` against canonical vanilla-wow 0.1.209.
- Retests the measured 12-yard global predicted-clearance floor—roughly twice the observed
  5–7-yard ordinary aggro radius—on top of the repaired combat and dense jump-aware descent.
  Local projected-add admission and multi-attacker escape gates are unchanged.
- Hosted request `xreq_281a428c-895b-4c21-9eb2-09d32355d19f` kept 23 of 24 characters alive and
  regressed median progress despite reducing evasion pulses from 691 to 365 versus V204. It caused
  32 reactive engagements; the death was a level-46 Scorpid fight whose ranged fallback cast-looped
  without damage. The global 12-yard floor remains unsafe and is rejected.

## v204 - jump-aware lower Shimmering Flats descent (2026-08-09)

- Version UUID: `7a4d1034-36ed-4d06-ac31-aa4a0fe78434` (`wowborg:v204`, uploaded
  inert; not submitted). Built from source `a428231` against canonical vanilla-wow 0.1.209.
- Preserves V203's exact dense lower-descent bearings and enables the existing jump-aware terrain
  movement only from point 16 onward, where hosted evidence first showed walk movement falling
  through the lower Detour edge.
- Hosted request `xreq_f5ee6500-f4c1-46f2-b7da-256c87cecd40` completed all 24 runs alive, but only
  one reached the dense descent and it timed out at point 12 before the new jump boundary. Across
  the batch, 876 hazard-avoidance selections and 691 evasion pulses confirmed that conservative
  route churn still prevents consistent activation of late-route behavior.

## v203 - dense lower Shimmering Flats descent (2026-08-09)

- Version UUID: `2344455c-3edd-49d9-80ed-833c8c2437e2` (`wowborg:v203`, uploaded
  inert; not submitted). Built from source `de622a3` against canonical vanilla-wow 0.1.209.
- Keeps V202's proven upper descent through point 9, then follows every roughly three-yard
  canonical Detour waypoint down the steep lower face instead of cutting eight long vertical
  chords. This directly targets V202's first observed server-correction loop without slowing the
  already reliable upper approach.
- Hosted request `xreq_fc162cfb-4b39-416f-bec0-6d35c04565f8` completed all 24 runs with every
  character alive. The best run reached dense point 15 at full health, then walking toward point
  16 fell through empty geometry and repeatedly reset to the lip. Density moved the failure down
  the route but did not make that edge walk-continuous; explicit jumping is required there.

## v202 - canonical connected descent path (2026-08-09)

- Version UUID: `b210792a-fc71-446e-91f6-06782aebe9dc` (`wowborg:v202`, uploaded
  inert; not submitted). Built from source `e634cae` against canonical vanilla-wow 0.1.209.
- Replaces the two fall chords with 17 sampled anchors from the canonical 0.1.209 Detour path.
  The pinned helper returns a complete 528.69-yard smooth path from north-road-9 to the south road;
  the old route skipped roughly 69 of its descent waypoints and cut through the cliff.
- V201 kept all 24 runs alive and removed backtracking, but no run reached the old landing. Its
  median progress improved, supporting local evasion while route geometry remained limiting.
- Hosted request `xreq_8d5d72fa-185a-487b-8fb3-d98676f9716b` kept all 24 runs alive. Three runs
  entered the sampled descent, but none reached the south road. The best run completed descent
  point 9, then overshot the 17-yard vertical chord toward point 10 and repeatedly received server
  position corrections. The canonical path is accepted, but its steep lower segment needs every
  roughly three-yard Detour waypoint rather than every fourth waypoint.

## v201 - local evasion without safe-point backtracking (2026-08-09)

- Version UUID: `d76612f6-1733-4400-83ca-87bd435bec14` (`wowborg:v201`, uploaded
  inert; not submitted). Built from source `5800e1c` against canonical vanilla-wow 0.1.209.
- When a selected hazard detour falls below the unchanged 20-yard clearance floor, uses the
  existing local move-away evasion instead of reversing to a stale last-safe point. Holding and
  terrain-constrained behavior are unchanged.
- V200's 24-run batch produced 1,012 avoidance starts and 838 retreats. It kept 23 runs alive; one
  run passed the descent health gate and began the south-road leg around 268 seconds, still far too
  late for the Great Lift. The repeated backtracking is the dominant measured throughput cost.
- Hosted request `xreq_7e42a29b-2687-40f8-9afc-07cc82cfaf25` kept all 24 runs alive with zero
  backtracks. Median progress improved, though no run reached the old descent landing.

## v200 - far-clear adaptive stride (2026-08-09)

- Version UUID: `287e4a0a-0a72-435e-9357-6ba89cfcb234` (`wowborg:v200`, uploaded
  inert; not submitted). Built from source `1a7f63e` against canonical vanilla-wow 0.1.209.
- Reverts V199's proactive-fight expansion. Keeps the proven one-second open stride whenever any
  hostile is visible within the router's 80-yard tracking radius, and uses the 1.5-second contract
  maximum only when that tracked set is empty.
- V199 kept only 22 of 24 runs alive and did not reach the descent. Proactive wins ranged from
  about 3 to 11 seconds and sometimes ended below 20% health, so ordinary blockers are again
  detoured unless they pull reactively; proactive combat returns to the calibrated ramp Scorpid.
- Hosted request `xreq_ae8794fa-a26f-4c9b-85dd-e00162713779` kept 23 of 24 runs alive. One run
  passed the 80% descent gate and began the south-road leg around 268 seconds. Across the batch,
  328 far-clear strides were outweighed by 1,012 avoidance starts and 838 retreats.

## v199 - isolated healthy blocker fights (2026-08-09)

- Version UUID: `aeebd278-56b2-4ca9-b377-859ae9c16424` (`wowborg:v199`, uploaded
  inert; not submitted). Built from source `cd20e3d` against canonical vanilla-wow 0.1.209.
- Restores V197's proven one-second clear-road stride. When any ordinary level-49-or-lower blocker
  is already inside the eight-yard hold zone, wowborg now fights proactively only if it has at
  least 95% health and every other nearby hostile's projected path preserves the existing 12-yard
  add-clearance floor.
- V198 regressed to 22 of 24 alive and did not reach the descent. One long stride entered a
  multi-attacker state; the other death entered a second reactive fight at 84% health. The
  1.5-second stride is rejected.
- Hosted request `xreq_6749dff1-abb3-4ca1-b399-6aa150135b86` also kept only 22 of 24 alive and did
  not reach the descent. Proactive fight tails reached 8-11 seconds and sometimes ended below 20%
  health. Rejected in V200.

## v198 - maximum clear-road stride (2026-08-09)

- Version UUID: `683b4cac-f2a0-4419-8cc5-d55f9af8faa5` (`wowborg:v198`, uploaded
  inert; not submitted). Built from source `acf6e90` against canonical vanilla-wow 0.1.209.
- Raises only unobstructed, non-terrain-constrained road input from 1.0 to the environment
  contract's 1.5-second maximum. Hazard steering, combat, climbs, and staged descent keep their
  existing precise cadence.
- V197's 24-run batch kept every run alive, but its only descent-landing run arrived around 250
  seconds and ended at 2,002/2,754 health, roughly two simulated seconds short of satisfying the
  80% release gate. This candidate targets the upstream action-roundtrip cost.
- Hosted request `xreq_18d557f7-1330-497c-891a-70a55fb58825` kept only 22 of 24 runs alive and did
  not improve frontier reach. One run entered multiple attackers during a long stride; the other
  died in a second reactive fight entered at 84% health. Rejected in V199.

## v197 - ranged fallback after repeated melee failure (2026-08-09)

- Version UUID: `392971b2-b83d-4d43-a3cc-568a3725f78f` (`wowborg:v197`, uploaded
  inert; not submitted). Built from source `3e4d4ef` against canonical vanilla-wow 0.1.209.
- After a complete feral rotation fails twice against the same exact attacker, leaves Cat Form and
  switches to Moonfire followed by Wrath. The first failed rotation still gets V195's corrective
  re-face; ordinary successful melee fights are unchanged.
- This targets V196's sole death: a level-47 Scorpid Dunestalker took zero damage through two
  failed melee rotations, including the corrective re-face. Hosted request
  `xreq_239086a7-53fc-4c8e-a920-5863683087ab` kept all 24 runs alive. Nineteen fights completed,
  including 12 corrective re-faces across eight runs; no fight exhausted two complete rotations,
  so the ranged fallback remains unactivated. One run reached the intermediate descent landing
  around 250 seconds and exercised the 80% health gate, healing from 1,301 to 2,002 before the
  episode horizon.

## v196 - health-gated second descent (2026-08-09)

- Version UUID: `a71f2f58-6d95-411d-90da-dd099914bcbe` (`wowborg:v196`, uploaded
  inert; not submitted). Built from source `0c6303f` against canonical vanilla-wow 0.1.209.
- On the intermediate Shimmering Flats landing, maintains Rejuvenation and waits until at least
  80% health before moving toward the lower road. This exceeds the 1,780 health that v195's second
  impact killed while retaining a shorter pause than waiting for full health.
- V195 combat, route, hazard clearance, and other action cadence are unchanged. Hosted evaluation
  is pending.

## v195 - re-face after failed combat rotation (2026-08-09)

- Version UUID: `7d531ea7-be09-4a4e-97de-0e52bd5558fd` (`wowborg:v195`, uploaded
  inert; not submitted). Built from source `3bcae44` against canonical vanilla-wow 0.1.209.
- When all usable Rake/Claw/Rip families fail, invalidates the navigator's cached facing, clears
  the per-fight failure memory, and re-engages the exact attacker. This creates a corrective
  re-face before retrying the rotation instead of holding an unproductive auto-attack forever.
- V194's caster descent, route, hazard clearance, and action cadence are unchanged. Hosted
  request `xreq_8188c6ea-768e-4e25-900a-1a129b50ded9` kept 23 of 24 runs alive. Three corrective
  re-face activations across two runs all survived. One run reached the first descent landing and
  remained alive; the sole death reached that landing, began the second drop at 1,321 health, and
  died on impact after Rejuvenation raised it to 1,780. The next candidate waits to 80% health on
  the intermediate landing before committing to the second drop.

## v194 - caster-form staged descent (2026-08-09)

- Version UUID: `866a5479-2aba-4766-8c0c-85fbc1649c7c` (`wowborg:v194`, uploaded
  inert; not submitted). Built from source `6a23423` against canonical vanilla-wow 0.1.209.
- Keeps caster form after applying Rejuvenation and immediately steers through each staged
  Shimmering Flats drop. Cat Form is removed from this seam because hosted evidence proved it does
  not reduce falling damage and its 1.5-second settlement outlasts rank-6 Rejuvenation at 10x.
- V193 combat, routing, hazard clearance, and action cadence are unchanged. Hosted evaluation is
  request `xreq_5e60b2d3-cf8f-4391-be7b-ad2603e5f832` kept 21 of 24 runs alive but did not reach
  the descent. Two deaths exhausted Rake and Claw, then held a cached facing/auto-attack state
  without further damage; the next candidate explicitly re-faces after exhausting the rotation.
  The third death followed a 27.7-second host action gap that returned directly to a dead frame
  amid multiple hazards.

## v193 - continuous combat closing (2026-08-09)

- Version UUID: `a48ff023-0235-451d-b304-388e62bfa532` (`wowborg:v193`, uploaded
  inert; not submitted). Built from source `fd16621` against canonical vanilla-wow 0.1.209.
- Enforces the proven 2.5-yard melee gate throughout each fight, including after auto-attack has
  acquired the target. A target that moves during a spell-settlement window is actively closed on
  again before the rotation or auto-attack continues.
- V192's failed-ability memory remains active. Routing, hazard clearance, staged descent, and
  action cadence are unchanged. Hosted request
  `xreq_7d91032c-62b9-4565-b030-f908cbe1f136` kept all 12 runs alive. Eight runs fought at least
  one attacker, continuous closing activated as many as eight times in a fight, and none repeated
  v192's zero-damage death loop. One run reached the south-ramp descent frontier.

## v192 - failed combat ability fallback (2026-08-09)

- Version UUID: `4d43b00a-971e-4cb7-8529-c77b1e73087c` (`wowborg:v192`, uploaded
  inert; not submitted). Built from source `aa52d2b` against canonical vanilla-wow 0.1.209.
- Remembers an unsuccessful Rake, Rip, or Claw family for the remainder of the current fight, so
  the next frame falls through to another ability or exact-attacker auto-attack instead of
  retrying the same failed cast until death.
- V191 routing, hazard clearance, staged descent, and action cadence are unchanged. Hosted
  request `xreq_d9d6f356-e550-4c19-a2c5-51476ab884ba` kept 10 of 12 runs alive. The fallback
  correctly advanced from one failed Rake to one failed Claw instead of retrying either family,
  but two reactive fights still held an auto-attack target without dealing damage until death.
  Both traces stopped rechecking melee distance once `auto_attack_guid` was populated; the next
  candidate keeps closing whenever the live target moves beyond the proven 2.5-yard gate.

## v191 - narrower safe detour candidates (2026-08-09)

- Version UUID: `7b3ab0cf-2a1a-4a27-ad1c-08845f10bef4` (`wowborg:v191`, uploaded
  inert; not submitted). Built from source `c79c00f` against canonical vanilla-wow 0.1.209.
- Adds 20- and 25-yard lateral candidates ahead of the existing 30/45/60-yard detours. Every
  candidate still must satisfy the proven 20-yard predicted-clearance floor.
- V190 combat, staged descent, route geometry, and cadence are unchanged. Hosted request
  `xreq_d6b13137-05df-4644-9baa-0269e5107de9` kept 11 of 12 runs alive. All 12 selected the new
  20-yard candidate and eight also selected 25 yards while preserving the 20-yard clearance floor.
  One run reached the first descent landing alive, recovered from 1,167 to full health with
  Rejuvenation, then spent the remaining horizon retrying Cat Form. The sole death was a reactive
  Glasshide Basilisk fight that repeated six failed Rakes after auto-attack had engaged; v192
  addresses that combat-loop defect.

## v190 - staged Rejuvenated descent (2026-08-09)

- Version UUID: `e0426ef5-965e-4b6a-b1c6-1ae65b4931b7` (`wowborg:v190`, uploaded
  inert; not submitted). Built from source `5279e9f` against canonical vanilla-wow 0.1.209.
- Restores V188's proven 20-yard road clearance. Splits the Shimmering Flats descent at the
  observed first-impact landing `(-6670.58, -4031.42, 27.69)` and keeps the fixture's maintained
  Rejuvenation rank active across both precise Cat-Form descent legs.
- Pinned-navmesh planning confirms the upper component ends around z75 and does not connect to the
  lower road component; this explicitly manages two drops rather than treating the chord as a
  walkable ramp.
- Hosted request `xreq_e200bf62-71f2-4ab1-90fe-474c4898916e` kept all 12 runs alive but did not
  reach the descent, so the landing/Rejuvenation behavior remains unexercised. Three runs reached
  ascent point 15; safe-route throughput remains the limiting factor.

## v189 - twelve-yard clearance with reactive combat (2026-08-09)

- Version UUID: `405cc7d2-b438-42e4-b684-8406575af9b6` (`wowborg:v189`, uploaded
  inert; not submitted). Built from source `6a53c96` against canonical vanilla-wow 0.1.209.
- Lowers only the global predicted-clearance floor from 20 to 12 yards. V188's validated reactive
  combat/closer, Cat descent, route geometry, and action cadence are unchanged.
- Unlike V183/V184, the policy can now kill a safe single pull instead of turning it into a lethal
  escape. The local projected-add combat gate was already 12 yards.
- Hosted request `xreq_072d26b9-ca22-4feb-b348-29a0f35b4bfd` kept only 9 of 12 runs alive, so the
  global 12-yard floor is rejected again. Two reactive Glasshide fights entered repeated failing
  Rake casts and died. One run reached the south ramp at 231.1 seconds and exercised Cat Form, but
  the direct descent lost 1,491 health on a z27.7 landing and then died on the second fall. Cat
  Form alone does not mitigate this environment's falling damage.

## v188 - active in-combat melee closing (2026-08-09)

- Version UUID: `f2e341fe-45cb-4d16-b5a4-89080938294c` (`wowborg:v188`, uploaded
  inert; not submitted). Built from source `e1e9298` against canonical vanilla-wow 0.1.209.
- Restores the proven 2.5-yard melee gate and uses the existing precise 0.25-second steering action
  to close on the exact attacker while already in combat, rather than waiting for the attacker to
  step closer.
- `_steer_toward` now returns its existing action ID so combat can detect refusal; its established
  route and lift callers remain behaviorally unchanged.
- Hosted request `xreq_5eae26a7-15f0-4431-8505-726aac6403d3` kept all 12 runs alive. Seven ramp
  Scorpid fights and one reactive Glasshide Gazer fight completed or safely released; the closer
  activated 1-3 times in the boundary cases and eliminated both prior wait loops. Five runs reached
  ascent point 15/16, but none reached the Cat descent. Those frontier runs still incurred 38-51
  avoidance starts and 19-37 retreats, making conservative routing churn the next bottleneck.

## v187 - three-yard melee engagement (2026-08-09)

- Version UUID: `9ef2d2d6-0b4a-4e27-961f-06faf57eb0b9` (`wowborg:v187`, uploaded
  inert; not submitted). Built from source `13c001b` against canonical vanilla-wow 0.1.209.
- Raises only the existing melee-engagement gate from 2.5 to 3.0 reported combat yards. V186's
  reactive admission, proactive ramp gate, rotation, route, and hazard behavior are unchanged.
- This addressed V186's 2.652-yard wait loop, but hosted request
  `xreq_a8fcb3ec-48c5-42c6-a8ce-69686fc3f655` kept only 11 of 12 runs alive. A reactive Glasshide
  Basilisk fight attacked from 3.05 yards, dealt zero damage, and then retried a failing Rake every
  1.5 seconds until death. The correct fix is active closing at the proven 2.5-yard gate.

## v186 - reactive single-attacker combat (2026-08-09)

- Version UUID: `1c5e7a88-5b41-42e2-b0ba-fb10ee28c898` (`wowborg:v186`, uploaded
  inert; not submitted). Built from source `e303664` against canonical vanilla-wow 0.1.209.
- Reactively fights exactly one visible, ordinary, non-elite level-49-or-lower attacker with the
  maintained Cat/Rake/Claw/Rip rotation on every route leg. Multi-attacker and unqualified combat
  still escapes.
- Proactive acquisition remains limited to the constrained ramp's isolated level-40/41 Scorpid;
  route geometry, hazard clearance, and movement cadence are unchanged.
- Hosted request `xreq_20f622df-e5c0-42bf-9758-5c36137fd859` kept 11 of 12 runs alive. Reactive
  kills included level-43/44 Scorpid Tail Lashers, a level-49 Searing Roc, a level-46 Glasshide
  Gazer, and a level-42 Glasshide Basilisk, generally in 3.5-4.8 seconds. The only death was a
  proactive level-41 Scorpid that stopped at 2.652 yards, just outside the 2.5-yard attack gate;
  the policy waited there until death. No run reached the Cat descent.

## v185 - Cat descent with conservative road clearance (2026-08-09)

- Version UUID: `639852fd-e3b7-4d49-bffa-efcf58f77165` (`wowborg:v185`, uploaded
  inert; not submitted). Built from source `2295773` against canonical vanilla-wow 0.1.209.
- Retains V184's Cat-Form exact descent while restoring the ordinary road-clearance floor to the
  proven 20 yards. The calibrated Scorpid projected-add gate remains locally 12 yards.
- V184 route geometry, action cadence, combat admission/rotation, and all other behavior are
  unchanged.
- Hosted request `xreq_d0b5f50f-2c79-496f-8ee9-7caab588597d` kept 10 of 12 runs alive but did not
  reach the south-road descent, so Cat Form remains unexercised. The two deaths each began as one
  ordinary attacker: a Glasshide Basilisk at 22.4 yards with 2,633/2,754 health, and a Scorpid
  Dunestalker. Eight other runs entered the existing ramp feral routine without dying. This makes
  reactive single-attacker combat the next attributable safety change.

## v184 - Cat Form exact descent (2026-08-09)

- Version UUID: `1cfe5fa3-18ec-43f6-9c8a-50d151f19d2f` (`wowborg:v184`, uploaded
  inert; not submitted). Built from source `e85a02a` against canonical vanilla-wow 0.1.209.
- Exits Travel Form and enters Cat Form for the Shimmering Flats south-road descent, and makes the
  south-road endpoint an exact three-yard anchor. Travel Form resumes on the flats.
- V183 clearance, route geometry, combat admission/rotation, and all other movement behavior are
  unchanged.
- Hosted request `xreq_bb91cc02-83a0-4c16-a291-4e0b341a2f04` did not reach the descent, so Cat Form
  remains unexercised. Five runs survived; one pulled a Glasshide Gazer at 8.75 yards during an
  evasion, collected additional attackers while escaping, and died. The 12-yard global road floor
  is unsafe and its roughly four-second best road-9 gain does not justify the regression.

## v183 - twelve-yard hazard clearance (2026-08-09)

- Version UUID: `b3bfe4a6-940a-4677-8e43-1dfe4dc07bed` (`wowborg:v183`, uploaded
  inert; not submitted). Built from source `e49641a` against canonical vanilla-wow 0.1.209.
- Lowers the predicted road-clearance floor from 20 to 12 yards, aligning ordinary avoidance and
  ramp add prediction on roughly twice the pinned 5-7-yard aggro radius.
- V182 route geometry, one-second stride, projected-add combat admission, rotation, and constrained
  descent are unchanged.
- Hosted request `xreq_aeff773d-fffe-4815-b84f-2c2cc18e92c7` kept five of six runs alive. One run
  reached the south-road pass at 241.4 seconds, but accumulated fall damage throughout the
  quarter-second descent and died when the final damage landed 1.34 seconds after movement stopped.
  The 12-yard floor improved the frontier but does not by itself make the descent safe.

## v182 - projected-add ramp fights (2026-08-09)

- Version UUID: `a536822a-16cd-4170-b9cc-8ff869198e16` (`wowborg:v182`, uploaded
  inert; not submitted). Built from source `e3e05e3` against canonical vanilla-wow 0.1.209.
- Admits the same single sub-eight-yard level-40/41 non-elite Scorpid when every other hostile in
  the 30-yard observation circle has a projected patrol segment at least 12 yards from the player.
  This uses roughly twice the pinned 5-7-yard ordinary aggro radius while rejecting predicted adds.
- V181 descent cadence, route geometry, combat rotation, and other hazard behavior are unchanged.
  Hosted request `xreq_ecff12e4-6234-466d-950f-8d4171c8d4f8` kept all six runs alive. Two proactive
  fights cleared safely in 5.7 and 6.2 seconds with no extra pull; one reached ramp ascent 16 but
  only about 10 seconds remained in the fixed 270-second horizon. The projected-add gate is safe in
  this batch, and route throughput is now the binding constraint.

## v181 - terrain-constrained south descent (2026-08-09)

- Version UUID: `a7e551aa-538f-4b83-9476-9d8a8baf4cd9` (`wowborg:v181`, uploaded
  inert; not submitted). Built from source `9efa623` against canonical vanilla-wow 0.1.209.
- Treats the existing Shimmering Flats south-ramp to south-road leg as terrain-constrained, using
  the existing 0.25-second precise movement cadence instead of the one-second open strides that
  produced V179's fatal descent.
- V180 route geometry, combat behavior, hazard thresholds, and steep cadence are otherwise
  unchanged.
- Hosted request `xreq_f8160381-9848-4f7b-a1a9-e20c6d5799b2` kept all six runs alive but did not
  reach the south-ramp frontier. Two runs spent about 111 and 130 seconds holding at the ramp turn,
  including roughly 2,000 hold pulses apiece, because a qualifying Scorpid was not the only hostile
  inside V180's 30-yard admission circle. The descent behavior therefore remains unexercised.

## v180 - true single-pull ramp combat (2026-08-09)

- Version UUID: `2e1e0cdb-d12b-46dd-87f3-761fb55fa023` (`wowborg:v180`, uploaded
  inert; not submitted). Built from source `836f8dd` against canonical vanilla-wow 0.1.209.
- Proactively fights a qualifying ramp Scorpid only when it is the sole hostile inside the existing
  30-yard hazard-entry radius, and begins attacking at 2.5 reported combat yards rather than 2.0.
- V179 route geometry, steep cadence, hazard thresholds, and combat rotation are otherwise
  unchanged.
- Hosted request `xreq_15b75738-8083-42fc-b01a-d23834eedeb8` ran six fresh episodes. All six
  survived, neither V179 ramp-combat death recurred, and the only recorded Scorpid fight cleared in
  about 3.4 seconds at full health. Four runs stalled earlier on the Tanaris road, one exhausted the
  episode at the road-9 climb, and one spent about 123 seconds holding a mixed ramp hazard before
  clearing it, so the batch did not retest the V179 south-road frontier.

## v179 - settle steep edges every eight pulses (2026-08-09)

- Version UUID: `f2e48def-d816-4ce0-bb60-8e95ce4e8f85` (`wowborg:v179`, uploaded
  inert; not submitted). Built from source `27a277f` against canonical vanilla-wow 0.1.209.
- Restores v177's retreat behavior and retains the normal post-control observation, while reducing
  only the second steep-edge settle wait from every pulse to every eighth pulse.
- Route geometry, hazard thresholds, combat, and ordinary exact-anchor settling are unchanged.
  Six-run request `xreq_18b0176a-d269-42bf-9e0a-554a1fb71d55` shortened the
  successful mountain ascent from 90.45 to 62.03 seconds. The best run reached the crest at 222.5
  seconds, south ramp at 227.5, and south road at 234.6—the farthest timed progress yet—but three
  runs died and two stopped early.
- Two deaths exposed ramp-combat admission/closing failures: a proactive Scorpid chase admitted a
  Glasshide Basilisk at 2.55 yards, while another looped at 2.177 yards above the 2.0 attack gate.
  The next candidate requires the Scorpid to be the only hostile within 30 yards and attacks from
  2.5 reported combat yards. The third death was explicit falling after south road and remains the
  following route-safety task.

## v178 - count only translated retreat stalls (2026-08-09)

- Version UUID: `6c29b6e2-131f-44c7-8c8b-44219b11622a` (`wowborg:v178`, uploaded
  inert; not submitted). Built from source `69fff04` against canonical vanilla-wow 0.1.209.
- Reports whether each steering control turned or translated, and increments the three-pulse
  blocked-retreat limit only after an actual retreat translation fails to move 0.5 yards.
- Route geometry, hazard thresholds, and combat behavior are unchanged from v177.
- Six-run request `xreq_86a8c77f-c292-4e22-b87a-509d1e2fab52` reduced blocked
  retreats to zero in five runs, but caused 58–107 completed retreats in four full runs. Only one
  reached the road crest, at 264.3 seconds versus v177's 134–150 seconds, and one run died. The
  branch is reverted.
- The next candidate restores v177 retreat behavior and changes only steep-edge settling. V177's
  successful 94-yard mountain ascent took 90.45 seconds, with 509 control pulses and 509 extra waits;
  steep edges now use the existing every-eighth-pulse settle cadence.

## v177 - measured Tanaris crest pass (2026-08-09)

- Version UUID: `829c6ecb-de49-4441-bd04-a163c58a4e94` (`wowborg:v177`, uploaded
  inert; not submitted). Built from source `4a704fd` against canonical vanilla-wow 0.1.209.
- Restores v175's single road-climb crest edge and allows only that crest to use the existing
  northing-pass envelope. The failed v175 climb was already inside all three measured pass bounds.
- All hazard, combat, and remaining route behavior is unchanged.
- Six-run request `xreq_588c79bb-5b5b-429a-a168-6ffb5e21d05f` kept every run
  alive. All four runs reaching the road climb acquired its crest in 1–2 seconds; three reached main
  mountain ascent points 14, 12, and 5, and one completed the mountain crest at 252.2 seconds and
  reached the Shimmering Flats south ramp—the first verified exit from Tanaris.
- The batch still emitted 14–30 false retreat-blocked events per run. The next candidate stops
  counting turn-only retreat controls as failed translations, without changing route geometry.

## v176 - bounded Tanaris road-9 climb (2026-08-09)

- Version UUID: `adb98318-5ce8-40a3-856e-0e8b9feaccc7` (`wowborg:v176`, uploaded
  inert; not submitted). Built from source `25a2666` against canonical vanilla-wow 0.1.209.
- Replaces the single 40-yard road-9 jump edge with six navmesh-measured ascent sub-edges before
  the existing crest, matching the proven bounded-edge controller on the later mountain pass.
- All hazard, combat, and downstream route behavior is unchanged from v175.
- Six-run request `xreq_28f32e93-23b2-4a5e-97a4-6a3251e93513` falsified the
  sub-edge design: no run cleared the climb, two repeated the first short jump to z78–95, and one
  reached the first sub-edge before falling into combat and dying. The other three stopped earlier,
  including two action-settlement timeouts.
- The next candidate restores v175's single crest edge and permits that crest alone to use the
  existing northing-pass envelope. V175's failed climb was already within its 20-yard northing,
  60-yard lateral, and 10-yard vertical bounds.

## v175 - split the road-9 climb at its crest (2026-08-09)

- Version UUID: `069a5fea-de02-4969-afd2-62c6b83f585b` (`wowborg:v175`, uploaded
  inert; not submitted). Built from source `63413c5` against canonical vanilla-wow 0.1.209.
- Ends the new road-9 jump edge at the navmesh's measured z34 crest, then resumes ordinary downhill
  movement to road point 9. All other v174 behavior is unchanged.
- Six-run request `xreq_ea688a49-44e2-4e64-b96f-71301d0e958b` produced three
  correct crest/downhill crossings; those runs reached mountain ascent points 14, 6, and 6. One
  climb run still overshot the 40-yard jump edge, one stopped earlier on an accepted route failure,
  and one died near road point 3 after a Glasshide Gazer closed to 4.05 yards.
- The next candidate replaces the single 40-yard jump with six measured navmesh sub-edges, matching
  the bounded-edge pattern already proven on the later mountain pass.

## v174 - jump the Tanaris road-9 climb (2026-08-09)

- Version UUID: `73f5f8cb-d6e9-41f4-ab30-e43e73208496` (`wowborg:v174`, uploaded
  inert; not submitted). Built from source `fcb8d78` against canonical vanilla-wow 0.1.209.
- Restores v172's conservative swept-path hazard clearance, dropping v173's unsuccessful timing
  branch.
- Adds a navmesh-measured exact anchor at the foot of the separate road-9 climb and enables explicit
  jumps only from that anchor to road point 9. The later mountain-pass jump edges are unchanged.
- Six-run request `xreq_b10b0b04-3bc4-4d63-8264-19353a0b3e5c` kept every run
  alive. Four reached the new climb base and all four crossed the formerly impassable climb; one
  continued through mountain-pass ascent point 15, the best Traverse frontier yet. Three crossed
  but overshot road point 9 vertically at z48–71 instead of z29, and two earlier runs ended on
  action-settlement timeouts.
- The next candidate ends this jump edge at the measured z34 crest, then walks downhill to road
  point 9. This preserves the successful climb while preventing vertical overshoot.

## v173 - time-aligned patrol clearance (2026-08-09)

- Version UUID: `1fdac500-2bbf-4024-87f7-a9fd9be76a22` (`wowborg:v173`, uploaded
  inert; not submitted). Built from source `54459a9` against canonical vanilla-wow 0.1.209.
- Computes route clearance over simultaneous player and observed patrol motion, then treats a
  patrol as stationary at its destination for any remaining player travel time.
- Preserves the 20-yard safety threshold and prior swept-path fallback when timing is unavailable;
  steep-edge jumps, combat, route geometry, and all other behavior are unchanged from v172.
- Six-run request `xreq_80c311ec-8cbf-4e9e-b817-a52772c8bc3d` kept all six
  runs alive, but none reached ramp-base. Three stalled at `tanaris-north-road-9`, two stopped at
  road point 3, and one stopped at road point 2; three ended on action-settlement timeouts. The
  timed-clearance branch is dropped from the next candidate.
- Navmesh recon explains the repeated road-9 stall: the complete maintained route rises from z13
  to z34 with a maximum segment slope of 1.21, while explicit jumps currently begin only at the
  later mountain pass. The next candidate adds the measured foot of this climb and jumps its final
  edge.

## v172 - explicit steep-edge jumps (2026-08-09)

- Version UUID: `be0167b1-0275-4c39-aabf-a50fc8f0be19` (`wowborg:v172`, uploaded
  inert; not submitted). Built from source `772672c` against canonical vanilla-wow 0.1.209.
- Propagates the action contract's explicit `jump` bit through wowborg's movement adapter and
  enables it only on forward translations along the 17 canonical steep-pass edges.
- Hazard handling, combat, non-steep movement, and downstream route geometry are unchanged from
  v171.
- Six-run request `xreq_38156220-9ef8-4f8d-8d85-4454b8347805` kept every run
  alive. One reached ramp-base at 180.9 seconds, then climbed through ascent point 08 (above z111)
  before the 270-second deadline—the first verified progress up the steep pass. It still incurred
  49 avoidance starts, 13 side switches, and 33 retreats; three other runs stalled near Tanaris
  waypoint 3. The next candidate time-aligns player and patrol motion when computing route
  clearance, preserving the 20-yard threshold while removing false, time-separated crossings.

## v171 - edge-bounded native mountain pass (2026-08-09)

- Version UUID: `2b445ece-e7f8-43a5-83cc-f773df84c0d0` (`wowborg:v171`, uploaded
  inert; not submitted). Built from source `3818f5d` against canonical vanilla-wow 0.1.209.
- Combines the canonical 17-point steep-pass path with the host's native jump-aware follower,
  bounding every synchronous `move_to` action to one Detour edge.
- Combat, hazard routing, downstream endpoints, and ordinary-road cadence are unchanged from
  v170.
- Six-run request `xreq_24966ee6-6f57-4ebe-bad2-ce3a5946f9cf` produced one
  ramp-base run. Its first edge-bounded native action also returned the unchanged frame after 30
  seconds, proving native `move_to` cannot execute this steep component. Four runs stopped earlier
  on route progress/frame failures and one died at ramp-turn. The next candidate uses the action
  contract's explicit one-shot `jump` bit on canonical steep-edge vectors; every non-steep vector
  remains unchanged.

## v170 - native jump-aware mountain pass (2026-08-09)

- Version UUID: `8085e4e1-e211-4958-9477-a15a148490b9` (`wowborg:v170`, uploaded
  inert; not submitted). Built from source `2c32d05` against canonical vanilla-wow 0.1.209.
- Delegates only the steep ramp-base-to-crest leg to the host's maintained `move_to` executor,
  which follows Detour polygon keys and infers required jumps. Manual steep ascent points are
  removed.
- Hazard-aware steering, ramp combat, downstream route endpoints, and ordinary-road cadence are
  unchanged from v169.
- Six-run request `xreq_b07f6d6c-b7a5-4c0e-95b1-fa668c05d442` produced one
  ramp-base run. Its native 94-yard pass action was accepted but returned the same frame after the
  fixed 30-second action timeout, so the route was too long for one synchronous action. Two runs
  died earlier in Tanaris and three stopped earlier on route progress/frame failures. The next
  candidate retains native jump inference but bounds each action to one of the 17 canonical
  Detour edges.

## v169 - canonical Detour ramp ascent (2026-08-09)

- Version UUID: `ca5d030f-316e-4644-99d7-6dccb979bb48` (`wowborg:v169`, uploaded
  inert; not submitted). Built from source `b7f1b50` against canonical vanilla-wow 0.1.209.
- Replaces the invalid straight ramp-base-to-crest leg with the canonical 17-point VMaNGOS
  Detour smooth path. Every new point retains exact, three-yard, terrain-constrained steering.
- Combat, hazard clearance, terminal-health handling, and ordinary-road cadence are unchanged
  from v168.
- Six-run request `xreq_5d280a5e-dc35-48ce-927b-ca4f0e86ad4a` reached the first
  ascent point in two runs, then both walked off the edge and failed the second. Two runs died
  earlier in Tanaris, one stalled at the Detour bend, and one lost its observation frame. Source
  recon showed the apparent 17-point corridor consists of `NAV_STEEP_SLOPES`: the public local-step
  wire deliberately omits whether a proved step requires jumping, so static `move_vector` cannot
  execute it. The next candidate replaces the baked points with the host's maintained `move_to`
  follower, which infers jump edges from the Detour polygon keys.

## v168 - full-leg precise ramp cadence (2026-08-09)

- Version UUID: `29b5673e-b414-43c4-ad3a-64d1ff0d5089` (`wowborg:v168`, uploaded
  inert; not submitted). Built from source `54c7b0c` against canonical vanilla-wow 0.1.209.
- Keeps every terrain-constrained anchor on quarter-second translation for its full leg. This
  prevents ramp-rise's large vertical endpoint delta from selecting a one-second clear-road pulse.
- Terminal-health combat handling, route geometry, hazard thresholds, and ordinary-road cadence
  are unchanged from v167.
- Six-run request `xreq_0810a791-b80a-4316-ab58-b427e8f8e231` kept all six runs
  alive. Three reached ramp-base after 4.4-6.3-second fights, but all three still failed the next
  leg; the other three ended earlier on missing observation frames. Quarter-second pulses ruled
  out cadence, because traces still moved diagonally off the ramp from z about 52 to below zero.
  A route against the canonical 0.1.209 VMaNGOS mmaps showed that the endpoint is reachable only
  through a 17-point smooth path that first holds x near -6884 while climbing north, then bends
  east. The next candidate replaces this one invalid straight leg with those Detour points.

## v167 - terminal-health hostile handling (2026-08-09)

- Version UUID: `31e355b8-384d-490b-a274-5f2669eb2c06` (`wowborg:v167`, uploaded
  inert; not submitted). Built from source `7dc278e` against canonical vanilla-wow 0.1.209.
- Applies the maintained owner convention that an observed unit with `health <= 1` is terminal even
  when `is_dead` lags. Such units no longer qualify as route hazards, attackers, or proactive ramp
  fights. The inactive v166 Bite branch is removed; resource tracing remains.
- Route geometry, clearance thresholds, live-unit movement projection, and combat rotation are
  otherwise the safe v162 baseline.
- Six-run request `xreq_4b1d6b73-d335-466a-923b-4af9562cd3e4` kept every run alive.
  Its three ramp fights ended in 4.3, 5.3, and 15.6 seconds, versus v162/v166's 29-36 seconds, and
  each fight-bearing run reached ramp-base. Ramp-rise then used one-second translations because
  its 48-yard 3D distance exceeded the ordinary precision gate, repeatedly fell off the narrow
  ramp, and failed `no_progress`. The next candidate keeps quarter-second translation throughout
  terrain-constrained anchors.

## v166 - Ferocious Bite ramp finisher (2026-08-09)

- Version UUID: `327685d0-0d64-4bd5-a606-322610bff48f` (`wowborg:v166`, uploaded
  inert; not submitted). Built from source `937f6ec` against canonical vanilla-wow 0.1.209.
- Adds the maintained Ferocious Bite family only when the qualifying ramp Scorpid is at or below
  40% health and wowborg has five combo points. Rake, Rip, Claw, fight admission, route geometry,
  and every other-contact behavior are unchanged from the safe v162 baseline.
- Feral spell traces record pre-cast combo points and active power, distinguishing an unknown spell
  or unmet resource gate from a host rejection.
- Six-run request `xreq_21b0b6d6-53dc-4b28-a60d-28661ec36868` produced zero Bite
  activations. Four runs stopped before the ramp; the two ramp-bearing runs admitted two Scorpids
  each and reached maximum combo counts of only two and four. One recorded two 33.6-33.9-second
  fight windows plus 32 failed spell attempts after combo points had reset to zero. Source removes
  the inactive finisher and instead adopts the owner's `health <= 1` terminal-unit convention.

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
