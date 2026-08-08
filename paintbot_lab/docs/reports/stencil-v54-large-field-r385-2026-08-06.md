# Stencil v54 large-field evaluation — campaign round 385

Date: 2026-08-06

Policy: `stencil:v54` (`cf88a169-2f85-403e-bb54-6b8bdc751ea5`)

Game: Paintbot 0.7.206, source `ec244e6b01485e8c7acd7a7929a9268354d50957`, GameVersion 40

## Verdict

Stencil v54 is strong across the current tournament field: **49 wins, three
draws, and eight losses in 60 full-seat episodes** (81.7% win rate, 86.7%
non-loss rate, tournament pot score +124). The 95% Wilson interval for the win
rate is 70.1–89.4%.

The earlier six-game `2v2` red-side concern did not replicate: v54 went 14-2
as red and 15-1 as blue across all 32 paired two-team episodes. FFA remains the
hardest mode at 20-3-5. The clearest focused failure is objective defense on
round-385 `1v1` cell `(3,2)` against Max Yankov: v54 lost by capture in both
captain colors despite winning the combat exchange in each game.

## Design

The batch followed the normative tournament-like request contract and used the
live round-385 campaign board and all 19 other active champions.

- 60 one-episode, full-seat requests: 16 `1v1`, 16 `2v2`, and 28 `4ffa`.
- The 16/16/28 split is the closest paired-seat approximation to the live
  board's 26/26/48 map distribution.
- Two-team play used eight distinct current cells per map ref. Each cell was
  run twice with v54 as red and blue captain, with both allies fixed.
- FFA used 28 distinct current cells and exactly seven episodes in each v54
  color.
- Every opponent was pinned to the champion version resolved before creation.
  Each of the 19 other champions appeared in 8–11 episodes; 16 received a
  direct paired captain matchup.
- Every request body was validated before creation. Final readback verified
  the exact 16-seat roster, policy versions, team assignments, map seed, and
  absence of filler policies.

The set is tournament-shaped, not a literal prediction of campaign scheduling:
cell selection and opponent allocation were deliberately balanced, and games
are not independent where a paired two-team cell shares its map and field.

## Results

| map ref | record | win rate | non-loss | score | kills/deaths | hit rate | captures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `1v1` | 14-0-2 | 87.5% | 87.5% | +24 | 361/178 (2.03 K/D) | 1,135/1,541 (73.7%) | 0 |
| `2v2` | 15-0-1 | 93.8% | 93.8% | +28 | 335/138 (2.43 K/D) | 1,125/1,496 (75.2%) | 1 |
| `4ffa` | 20-3-5 | 71.4% | 82.1% | +72 | 587/197 (2.98 K/D) | 1,797/2,210 (81.3%) | 5 |
| **total** | **49-3-8** | **81.7%** | **86.7%** | **+124** | **1,283/513 (2.50 K/D)** | **4,057/5,247 (77.3%)** | **6** |

Win-rate Wilson intervals were 64.0–96.5% for `1v1`, 71.7–98.9% for `2v2`,
and 52.9–84.7% for `4ffa`. FFA non-loss was 23/28 (82.1%, 95% Wilson interval
64.4–92.1%).

### Side and color checks

| seating | record | score | kills/deaths | hit rate |
| --- | ---: | ---: | ---: | ---: |
| two-team red | 14-0-2 | +24 | 342/164 | 73.0% |
| two-team blue | 15-0-1 | +28 | 354/152 | 75.9% |
| FFA red | 5-0-2 | +18 | 169/62 | 84.6% |
| FFA blue | 4-1-2 | +13 | 173/56 | 80.9% |
| FFA green | 7-0-0 | +28 | 117/29 | 77.7% |
| FFA yellow | 4-2-1 | +13 | 128/50 | 81.4% |

The FFA colors are balanced in count but confounded by map and opponent field;
seven observations per color are not evidence of a causal green advantage.

### How games ended

- 44 wipe wins and five capture wins.
- Five wipe losses and three capture losses.
- Three timeout draws.
- Stencil seats recorded six captures; one occurred before a later wipe win.

## Failure signal

The strongest two-team signal was the paired `1v1` cell `(3,2)` matchup against
`golergka-paintbot-stock:v2` (Max Yankov), with Rohit Mukherjee and richard as
the fixed allies. V54 lost by capture from both colors while recording 21-11
and 22-3 kills/deaths. That is an objective/heart-defense failure rather than
an aiming or general combat failure.

The only other two-team loss was red on `2v2` cell `(6,4)` against
`nancy-paintbot:v4`: a 17-21 wipe loss. The blue captain swap won 23-15. Every
other direct captain pair was a 2-0 v54 sweep.

Two repeated FFA fields produced no wins across two distinct cells/colors:

- Max Yankov + Ron @ SWGY + daveey: 0-0-2.
- relh + Alex Smith + Jordan: 0-1-1.

These are better follow-up targets than the earlier small-sample idea that red
`2v2` seating or the Daveey-plus-relh combination was generally weak.

## Comparison with the earlier 18-game set

The round-383 set was 13-3-2 (72.2% wins, 88.9% non-loss); this set was 49-3-8
(81.7% wins, 86.7% non-loss). FFA non-loss was essentially unchanged, 5/6
(83.3%) versus 23/28 (82.1%), while the larger set converted more games to
wins. These batches should not be pooled as independent samples because some
current cells/seeds overlap and the field designs differ.

## Integrity and provenance

All 60 requests completed with no operational failures. Every artifact bundle
contained `episode.json`, `results.json`, and `replay.json`. The replay was
expanded against the exact deployed GameVersion-40 source and every recorded
state hash passed. Results counters are authoritative for captures; a temporary
analysis-only replay reader tolerated GV40 clearing a carried heart during the
post-step capture transition, which does not affect shots, hits, positions, or
hash validation.

Experience-request IDs, in request order:

```text
xreq_4a9bcc9e-d7c9-4fb5-a7f3-7b0817746779 xreq_f664a420-f8fd-4c58-a8d5-e5a803e66b85
xreq_fb9ab6f9-b35e-420b-8d5e-9e71928000e2 xreq_87f6548f-4e99-431d-b806-9c7f032eaebd
xreq_203ef3a2-7303-4c62-8fa2-d5adf7c16329 xreq_b5d782d7-f2f3-4ecc-a736-dbff582c4b2a
xreq_c8aec153-0802-4b3e-bdf1-dc820616914d xreq_c004d55c-0fd4-45b5-8216-64191495584c
xreq_929e832c-750a-4f22-ba71-2d7723c42373 xreq_55f0386d-64cc-423a-acb6-9cb0e9200677
xreq_16fde856-57a4-4df2-a75d-6fa6c3c04f35 xreq_fd5b5bc0-393c-4131-b4a4-2326c309a84c
xreq_5f271f9d-8c97-4c5c-99a2-453a710e809f xreq_2276286e-39aa-48c4-bc1a-55fe2e0f34c7
xreq_284af98b-c31c-4a95-9270-5b1340d18b33 xreq_ed48609f-4950-4ca6-aba7-3fad9c8b70e1
xreq_518a15f1-7c00-4e48-b26a-5e16c2132b56 xreq_53fc9e83-8ab3-4ba7-93e3-5f13afbf91e9
xreq_4e3b7d3c-7085-46a8-986e-75d5df1b53c5 xreq_0edf786d-0063-415f-a14e-c586a3851c6b
xreq_37aeaef3-8b12-4273-8bab-a53c2238a58f xreq_4f45e3ac-ff20-4773-a9d3-5d17e39d07a4
xreq_559c2252-0bc9-47ec-907e-02cf35e83bea xreq_f3ab99fa-9475-491b-a533-314479298431
xreq_6aa82a98-1559-4d7d-9c26-2d64f89ebdfd xreq_b443bead-139c-489a-a1e9-82167a5c593a
xreq_d3ec6989-c5a9-4301-a47f-45ce45859c88 xreq_d135d8bc-768b-4186-a448-602b79eebba8
xreq_b1c39402-8117-448d-a9fa-ddf935c4a4c7 xreq_6d2ee264-9fac-44e8-bc87-9e89451b0cd7
xreq_ab269c76-4130-41ed-8fe9-70896c064d8f xreq_76b89a61-e39a-4285-b038-9afc3321986a
xreq_e985f8be-efce-422a-bd5d-016a652bbedf xreq_7ea10d2d-9d26-4a79-802d-e195886356fb
xreq_f3020804-8e90-4edf-aa0d-e462e7ea961a xreq_2211fe76-6fe6-4147-8eab-205d45853446
xreq_b63279f3-e62c-46db-978d-e0b888c3e15a xreq_c2bb7ba7-d1ef-4966-ab57-94b4f45116b6
xreq_871856e7-4171-45f4-95fe-73a39e5c7a0f xreq_035462bc-712c-465e-8bde-aeaeab212564
xreq_5ee1c2af-e349-4f70-b57f-bbf0d0f3e985 xreq_56c6914e-9009-4d4d-a29d-142d94fa6dc4
xreq_44beed06-6438-4cf1-b860-4a19d8dc2d52 xreq_1bf1842f-7b03-4c18-9d43-fcc4f1298bf9
xreq_875e266f-2a33-4249-8112-aa54703855db xreq_3e97e6a7-1dfa-4378-bce5-a5bf89cc5798
xreq_61abd707-6a05-4690-809c-5b5a4c8e9d72 xreq_eef21fd4-3906-40b3-9833-0db13049fcae
xreq_d417c7a8-b55c-4cb0-9fa2-861467c4c5b2 xreq_c7165047-7cc0-4bad-b9c7-ea3d67232c5e
xreq_b0b425d8-e090-4f4f-9d3d-0e4146cc3533 xreq_ab4910bc-d00d-4d7c-ac5b-25a7973c6c05
xreq_4c85a9a8-2832-4877-a012-85a825803549 xreq_a1b83105-3f7c-4780-a557-647bedb7f825
xreq_b0eb2146-fa4f-41bb-b5c3-cd3472866020 xreq_aa628417-2a41-4a65-94fa-7fcf4d332ba6
xreq_1ef30f06-01ec-4551-9069-3b6ed5d209b6 xreq_515e1ba6-9a38-434b-819a-609d1d9cbcf2
xreq_49272579-74cd-4df0-bb49-66b045483a44 xreq_d3af2659-c9bf-4f62-9e2e-3519004c37bd
```
