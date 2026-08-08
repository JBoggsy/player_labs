# Stencil v54 GV40 aim validation — 2026-08-06

## Verdict

Accept the controller correction as a candidate improvement. Stencil v54 turns
in coherent five-brad steps, no longer exhibits v52's one-tick left/right limit
cycle, and shoots effectively under the deployed GameVersion 40 engine. It won
all six matched hosted episodes in both captain seatings.

This verdict does **not** submit v54 to the league. v52 remains the James Botts
champion until the human submission gate is explicitly opened.

## Question and preregistered control

The question was whether replacing Stencil's obsolete 32-slot controller with
continuous shortest-angle steering preserved practical movement, turning, and
straight shooting. v52 was the unchanged control. v54 retained v52's accepted
squad behavior and changed the aim model only:

- engine heading domain: every integer from 0 through 255 brads;
- held turn input: exactly five brads per simulation tick;
- controller: signed shortest-angle error;
- stop condition: within two brads, the closest guaranteed residue when moving
  in five-brad increments.

## Hosted design

Both requests used canonical Paintbot 0.7.206 / GameVersion 40, source
`ec244e6b01485e8c7acd7a7929a9268354d50957`, and round-381 campaign cell
`(0,0)`: map ref `1v1`, seed `344807463`, nullable map size omitted. The current
campaign classifies this 16-seat game as mode `2v2`, so each episode used the
real 7+7+1+1 captain/ally seating rather than treating `1v1` as a two-agent
duel.

The allied policies were fixed in both arms:

- red ally, slot 2: `co-gas-ctf-simple-relhalpha:v38`;
- blue ally, slot 3: `paintbot-focusfire:v26`.

The captains swapped sides while the allies stayed fixed:

| arm | red captain seats | blue captain seats | episodes | request |
| --- | --- | --- | ---: | --- |
| A | v54 at 0,4,6,8,10,12,14 | v52 at 1,5,7,9,11,13,15 | 3 | `xreq_c1d087cb-e14e-4002-89be-747ebceee30e` |
| B | v52 at 0,4,6,8,10,12,14 | v54 at 1,5,7,9,11,13,15 | 3 | `xreq_ed344056-08b7-43be-b5a3-be500aa29479` |

All six episodes completed and all 96 policy artifacts were retrieved. There
were no episode or artifact failures.

## Results

Metrics below include captain-owned seats only; allied seats are deliberately
excluded.

| metric | v54 | v52 control |
| --- | ---: | ---: |
| captain-side episode wins | 6 / 6 | 0 / 6 |
| kills | 137 | 17 |
| deaths | 24 | 126 |
| shots | 565 | 120 |
| hits | 436 | 87 |
| hit rate | 77.2% | 72.5% |
| live per-tick heading transitions | 83,560 | 66,009 |
| turning transitions | 42,987 | 38,838 |
| non-five-brad turning transitions | **0** | **0** |
| immediate direction reversals | 3,733 | 30,382 |
| reversals / turning transitions | **8.7%** | **78.2%** |
| median same-direction turn run | 4 ticks | 1 tick |
| p95 same-direction turn run | 13 ticks | 2 ticks |
| longest same-direction turn run | 28 ticks | 10 ticks |

The win and combat differences are large, but the controller diagnosis does
not depend on score. The exact per-tick headings show the mechanism directly:
every v54 turn was one legal five-brad step, while v54 sustained useful turns
instead of alternating direction nearly every tick as v52 did.

## Straight-shot evidence

The deployed engine separates trigger pull from projectile creation by five
ticks. All 565 completed v54 gun actions preserved exactly the same heading
between `gun_trigger` and `gun_fire`, and every delay was exactly five ticks.
The engine registered 436 hits from 565 shots.

The richer impact stream recorded 432 damaging v54 impacts. At impact time,
413/432 (95.6%) were within three brads of the damaged player's centerline and
423/432 (97.9%) were within eight brads. The nine larger centerline differences
were all point-blank collisions at no more than 39.2 pixels, where intersecting
the player's collision body does not require aiming through its center. This is
consistent with straight projectile travel and effective target alignment.

## Evidence method

The analysis did not trust Stencil's belief trace as ground truth. A temporary
host-native `expand_replay_json` was compiled from the exact deployed source
commit and used to re-simulate every replay with position output every tick.
All six simulations passed their per-tick replay hashes through game over.
Counts came from engine `pos`, `gun_trigger`, `gun_fire`, `shot_impact`, `shot`,
`hit`, and kill/death state transitions. Policy telemetry was used only to
confirm the v54 artifact identity and controller-facing fields.

## Audit finding outside the controller

The evaluation trace also corrected a documentation misconception: a current
campaign cell whose map ref is `1v1` is not a literal two-player or two-policy
match. The game has 16 seats, and the current campaign commissioner supplies
two captains plus two allies in 7+7+1+1 ownership with a paired captain swap.
The normative evaluation docs now describe that contract.

Stencil's static parity squad table predates this scheduler shape and can group
a captain-owned seat with the one foreign allied seat. That is a real but
separate coordination issue, recorded in the root `TODO.md`; it was not folded
into this controller-only iteration.
