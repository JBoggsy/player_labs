# Stencil v54 top-champions field test — 2026-08-06

## Verdict

Stencil v54 produced a strong tournament-like result against the current
territory leaders: **13 wins, three draws, and two losses in 18 full-seat
episodes**, with six episodes on each live map ref (`1v1`, `2v2`, and `4ffa`).
Its aggregate tournament score was **+26**.

The evidence is strongest on the current `1v1` maps, where v54 swept all three
opposing captains in both colors. The main risks are narrower: the sampled
`2v2` results were side-sensitive, and the two hardest FFA fields containing
both Daveey and relh ended in a draw and a loss.

This evaluation does **not** submit v54. v52 remains the active James Botts
champion until James explicitly opens the submission gate.

## Live field and game contract

The field was resolved from Paintbot campaign round 383. The top eight players
by territory, and the exact champion versions used, were:

| rank | player | territory | policy version |
| ---: | --- | ---: | --- |
| 1 | relh | 20 | `co-gas-ctf-simple-relhalpha:v38` |
| 2 | Alex Smith | 10 | `paintbot-p023:v1` |
| 3 | methnarval | 9 | `methnarval-paintbot:v7` |
| 4 | Max Yankov | 8 | `golergka-paintbot-stock:v2` |
| 5 | NanosaurusX | 8 | `nancy-paintbot:v4` |
| 6 | Ron @ SWGY | 8 | `swgy-paintbot:v11` |
| 7 | RowDaBoat | 7 | `reardenr-paintbot:v12` |
| 8 | daveey | 7 | `paintbot-focusfire:v26` |

Every episode used canonical Paintbot 0.7.206 / GameVersion 40, source
`ec244e6b01485e8c7acd7a7929a9268354d50957`, and Stencil v54 UUID
`cf88a169-2f85-403e-bb54-6b8bdc751ea5`.

Round 383's 100-cell board contained 26 `1v1`, 26 `2v2`, and 48 `4ffa` cells.
There was no current `4ffa8` cell, so adding a synthetic `4ffa8` episode would
not have been tournament-like and was deliberately omitted.

## Experiment design

All 18 episodes reproduced a real round-383 cell's map ref, pinned seed,
nullable map size, campaign mode, and full 16-seat commissioner shape.

- `1v1`: three distinct current cells, each run twice with v54 and the opposing
  captain swapping red/blue while both allied policies stayed fixed.
- `2v2`: three distinct current cells with the same paired captain swap.
- `4ffa`: six distinct current cells, with v54 rotated across red, blue, green,
  and yellow and one complete policy owning each color.

The `1v1` and `2v2` refs both used current campaign mode `2v2`: two captains
plus two allied policies in 7+7+1+1 seat ownership. These were not partial-seat
duels. Final request readback verified all 16 seats, the exact versions, target
game version, variant, and seed before interpreting results.

All 18 requests and episodes completed successfully. All result, replay, and
policy-log bundles were retrieved. Exact-source replay expansion passed the
recorded simulation hashes for every episode.

## Results by map ref

Metrics include only seats owned by v54. A draw is a time-limit draw. Campaign
pot scoring is +2/-2 for two-team games and +4/-1/-1/-1 for FFA; every draw is
-1.

| map ref | record | score | kills / deaths | K/D | hits / shots | hit rate | captures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `1v1` | **6-0-0** | +12 | 136 / 65 | 2.09 | 441 / 571 | 77.2% | 0 |
| `2v2` | **4-1-1** | +5 | 123 / 91 | 1.35 | 386 / 612 | 63.1% | 0 |
| `4ffa` | **3-2-1** | +9 | 92 / 58 | 1.59 | 294 / 356 | 82.6% | 0 |
| **total** | **13-3-2** | **+26** | **351 / 214** | **1.64** | **1,121 / 1,539** | **72.8%** | **0** |

All 13 wins and both losses ended by team wipe. The three draws reached the
time limit. No game ended through a heart capture.

## Two-team paired results

Each line below uses one fixed map and ally pairing, with the two captains
swapped across colors.

| map ref | opposing captain | v54 red | v54 blue | pair result |
| --- | --- | --- | --- | ---: |
| `1v1` | relh | win, 24/8 K/D | win, 23/14 | **2-0-0** |
| `1v1` | Alex Smith | win, 19/9 | win, 22/18 | **2-0-0** |
| `1v1` | methnarval | win, 23/7 | win, 25/9 | **2-0-0** |
| `2v2` | daveey | draw, 19/13 | win, 24/14 | **1-1-0** |
| `2v2` | NanosaurusX | win, 23/16 | win, 24/12 | **2-0-0** |
| `2v2` | Ron @ SWGY | loss, 14/21 | win, 19/15 | **1-0-1** |

Across the three `2v2` pairs, v54 was 3-0 as blue captain but 1-1-1 as red
captain. Because the opponent, allies, map, and seed were held fixed within
each pair, this is meaningful evidence of side sensitivity in this sample,
though three pairs are too few to estimate its size reliably.

## Four-team results

| cell | v54 color | opposing field | result | v54 K/D |
| --- | --- | --- | --- | ---: |
| `(4,4)` | red | relh, Alex Smith, methnarval | win | 22/10 |
| `(5,4)` | blue | Max Yankov, NanosaurusX, Ron @ SWGY | win | 12/10 |
| `(2,5)` | green | RowDaBoat, daveey, relh | draw | 12/11 |
| `(3,5)` | yellow | Alex Smith, methnarval, Max Yankov | draw | 18/5 |
| `(4,5)` | red | NanosaurusX, Ron @ SWGY, RowDaBoat | win | 18/10 |
| `(5,5)` | blue | daveey, relh, Alex Smith | loss | 10/12 |

The color cut was red 2-0, blue 1-1, green 0-1-0, and yellow 0-1-0. It is too
small and confounded by field strength to support a color claim. The more
actionable observation is that the two FFA lineups containing both daveey and
relh were the draw and loss; the other four fields yielded three wins and one
draw.

## Request provenance

| episodes | request IDs |
| --- | --- |
| `1v1` | `xreq_9fa68ccb-2eb8-40d5-acee-8d9ae70ff2e6`, `xreq_e4d8cc14-95f3-4572-b064-b68e619a63a2`, `xreq_66e429ab-0175-44d4-a3ba-1073146e5130`, `xreq_966c6267-da32-4b56-a0ed-c7a89c3df1c0`, `xreq_a46e1343-6f64-4f97-b5ee-ae983492363e`, `xreq_58d96d46-3a05-4d3e-84e0-95da9a545437` |
| `2v2` | `xreq_49ac8de0-b28c-48ba-9eb5-2e84b04873e0`, `xreq_52da115a-6f68-497b-a968-651e7f1d0156`, `xreq_3dfe1456-0aeb-4391-ae03-9cb7140f268d`, `xreq_f820f623-6a38-46f3-9de8-006e1d77753a`, `xreq_56d0b8c5-676c-4cda-86a0-f5e02a165ecb`, `xreq_7a03f3c3-578b-44eb-8fe4-cbea48508f2a` |
| `4ffa` | `xreq_37d883d0-5e3f-4545-9c07-8c1a719db1cb`, `xreq_3dc68db3-ff26-48b8-b2d7-ce1434c7ca82`, `xreq_8806f9cb-8217-415d-ab18-24983b949ecf`, `xreq_05703728-2bdd-4545-a50b-9a0f9e08ed5b`, `xreq_3e4d0019-c8de-4da1-807b-d9ed365475da`, `xreq_11561bff-7f4b-4a53-a811-918352755ed7` |

## Interpretation

This batch clears the practical question raised after the controller fix: v54
can turn, shoot accurately, and win across every map type currently present in
the campaign. The `1v1` sweep is especially persuasive because each opposing
captain was tested in both captain seatings.

It does not prove uniform superiority over v52, because this was a current
field test rather than a matched v54-v52 A/B. Before any future strategy
change, the best next diagnostic target is the current `2v2` red-side weakness
and the Daveey-plus-relh FFA field—not the corrected aim controller.
