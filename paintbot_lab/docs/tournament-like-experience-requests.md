# Campaign-shaped Paintbot experience requests

This is the normative specification for representative gameplay evaluation in
`paintbot_lab`. Paintbot is a campaign league, so the target is the live
campaign commissioner contract—not the disabled ladder configuration and not a
variant name interpreted as a roster description.

## The two independent layers

Every campaign cell has both:

- a **`map_ref`**, selecting the Coworld variant, seat count, teams, and map;
- a **campaign `mode`**, derived from that variant's actual team/seat structure
  and selecting the commissioner roster algorithm.

This distinction matters now. Paintbot 0.7.205 changed variant `1v1` to 16
seats. Because it is a two-team variant with at least four seats, the current
commissioner classifies it as mode `2v2`. On the round-381 board, both `1v1`
and `2v2` map refs therefore have mode `2v2`; `4ffa` has mode `ffa4`.

## Normal invasion seating

For a normal occupied-cell invasion, reproduce the commissioner's roster:

| campaign mode | current map refs | seats | normal roster |
| --- | --- | ---: | --- |
| `2v2` | `1v1`, `2v2` | 16 | four policies in 7+7+1+1 captain/ally seating |
| `ffa4` | `4ffa` | 16 | four policies, one complete four-agent color each |
| `ffa4` if `4ffa8` returns | `4ffa8` | 32 | four policies, one complete eight-agent color each |

For `2v2`, each side has a captain and one allied entrant. The captain owns its
team's first seat and every seat after the second; the ally owns only the
team's second seat. With alternating red/blue slots, seating A is:

| global slots | owner |
| --- | --- |
| 0, 4, 6, 8, 10, 12, 14 | red captain |
| 2 | red ally |
| 1, 5, 7, 9, 11, 13, 15 | blue captain |
| 3 | blue ally |

The campaign authors a second seating with captains swapped between red and
blue while allies remain on their original sides. With current `best_of: 1`,
that is one episode per seating. This cancels captain-side and ally-strength
bias; an evaluation that uses four equal modulo-four blocks is the disabled
ladder shape, not the campaign shape.

Claims and degraded battles are different: an empty-cell claim seats the
claimant once against baseline-filled seats, and a two-team invasion without
available allies falls back to two interleaved captains. Use those shapes only
when explicitly testing those situations.

## Representative episode definition

An episode is **campaign-shaped** only when all of these conditions hold:

1. **Current target.** Resolve the live Paintbot league/division and canonical
   Coworld immediately before creating the request. Pin exact game and policy
   versions; do not infer them from a local checkout.
2. **Current campaign cell.** Copy one cell's `map_ref`, `mode`, `map_seed`, and
   any non-null `map_size`. Do not mix fields from different cells, invent a
   seed, or substitute only the generic episode seed. Omit `mapSize` when the
   cell leaves it unset.
3. **Correct battle kind and roster.** State whether the test represents a
   normal invasion, claim, or degraded no-ally battle, then use that exact
   commissioner seating. Normal invasion is the default.
4. **Current opponents.** Resolve allies/opponents from current active champion
   memberships immediately before the batch and pin their exact versions.
5. **Both captain seatings for `2v2`.** Keep allies fixed to their sides and
   swap the two tested captains. Use the same map and episode count per seating.
6. **Final rows verified.** Treat created participant rows and runtime config as
   the final truth; reject evidence if they differ from the preregistration.

As of round 381, the 100-cell board has 26 `1v1`, 26 `2v2`, and 48 `4ffa` map
refs, corresponding to 52 `2v2`-mode and 48 `ffa4`-mode cells. All cells have a
non-null `map_seed`; all currently leave `map_size` unset. Re-resolve these
dated values for every study.

## Batch construction

For a broad campaign substitute:

- sample cells in the current board's proportions, or preregister a narrower
  cell/mode cut that answers the hypothesis;
- copy each selected cell's complete map contract;
- construct both captain seatings for every `2v2` matchup;
- sample remaining active champions without replacement as allies/FFA parties;
- create one-episode requests when cell maps or seatings differ;
- launch artifact streaming as soon as requests are accepted.

For a focused controller A/B, a valid small design is one current `2v2`-mode
cell, candidate and control as the opposing captains, two pinned live champion
allies, and equal repetitions of both captain seatings.

## Fail-closed validation

Inspect created episode rows before treating any result as evidence. Reject or
cancel the batch if any invariant fails:

- canonical Coworld/version differs from the one resolved at creation time;
- variant or map fields do not match the preregistered live cell;
- `mapSize` was invented when the cell supplied no value;
- participant count or policy placement differs from the chosen battle kind;
- a normal `2v2` invasion uses equal four-seat blocks instead of 7+7+1+1;
- captain-swapped arms do not keep allies fixed to their original sides;
- any seat contains an unintended filler or obsolete Stencil version.

Partial-seat, arbitrary-map, stale-game, and local scenarios can answer narrow
debugging questions. Label them **debug probes**, exclude them from gameplay
claims, and obtain the verdict from a batch satisfying this specification.

## Source of truth

Current Metta `campaign/episodes.py` owns this contract: `variant_modes`
classifies variants from actual teams/seats; `_duo_roster` creates the captain
plus one-seat ally layout; and the invasion planner authors both swapped
captain seatings. The live league description and disabled ladder settings
still describe equal four-agent entrant blocks for `2v2`; those surfaces are
stale for campaign episodes.
