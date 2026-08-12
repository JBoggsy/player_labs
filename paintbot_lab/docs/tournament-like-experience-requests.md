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

This distinction matters now — and the coupling loosened further in the
current commissioner: a cell's mode is a **policy layout chosen independently
of the variant** (a 16-seat two-team variant hosts both `1v1` head-to-head
and `2v2` duo cells; the variant owns only the ground and headcount). Never
infer the mode from the map ref — read it off the board cell.

## Normal invasion seating

> **BOARD ROLLED BACK later on 2026-08-11:** hours after the round-967
> re-verification below, the live board was RESTORED to the pre-migration
> **10×10 square board** (100 cells, all `map_size` null again, authored
> map_specs and owners refilled from the pre-migration snapshot — the board
> `events` feed records the restore; `round` read 957 afterwards). The
> roster algorithms below (true `1v1` mode, even `_duo_roster` split,
> mode-decoupled-from-ref) come from metta code and still apply — the live
> `modes` list still shows mode↔ref decoupling on the restored board. The
> hex-specific counts in this doc are historical. As always: **re-resolve
> the board live for every study**; it drifted twice in one day.
>
> **Re-verified 2026-08-11 (round 967, metta `84e13cb799`).** The commissioner
> contract changed materially since the round-381 snapshot this doc first
> recorded: the board migrated to a 16×16 hex (round 955), a true `1v1`
> head-to-head mode exists, and `_duo_roster` now splits each team **evenly**
> between captain and ally — the old 7+7+1+1 seating is gone. A cell's mode is
> now a policy layout **independent of its variant** (`variant_arenas` /
> `variant_campaign_modes`): the variant owns only the ground and headcount.

For a normal occupied-cell invasion, reproduce the commissioner's roster:

| campaign mode | round-967 occupied refs | seats | normal roster |
| --- | --- | ---: | --- |
| `1v1` | `1v1`, `2v2`, `default` (mixed) | 16 | two policies head-to-head, each owning one team's every seat; teams swap for the second seating |
| `2v2` | mostly `default` | 16 | four policies; per team the **captain owns the leading half** of that team's seats in slot order and the **ally the trailing half** (4+4 on 8-seat teams; captain gets the extra seat on odd counts) |
| `ffa4` | `4ffa`, `4ffa8` | 16 / 32 | four policies, one complete color each (seats interleaved mod 4) |

Two-team variants seat teams on alternating global slots (one team even, the
other odd — verified from live round-967 episode rows). For `2v2` on an
alternating 16-seat variant, seating A is:

| global slots | owner |
| --- | --- |
| 0, 2, 4, 6 | red captain |
| 8, 10, 12, 14 | red ally |
| 1, 3, 5, 7 | blue captain |
| 9, 11, 13, 15 | blue ally |

The campaign authors a second seating with captains swapped between red and
blue while **allies remain on their original sides**; head-to-head battles
likewise swap the two policies' teams. With current `best_of: 1`, that is one
episode per seating. This cancels captain-side and ally-strength bias; an
evaluation that uses four equal modulo-four blocks on a two-team variant is
the disabled ladder shape, not the campaign shape.

Campaign episodes also carry **per-player perk loadouts** (equipped perks, or
the coworld's default loadout) and can carry per-cell `game_config` overrides
(`resolve_perk_loadouts`, `_roster_perks`, `_cell_overrides` in metta
`campaign/episodes.py`). An experience request that omits them diverges from
campaign conditions; matched A/B arms cancel the divergence, but label
absolute-strength claims accordingly.

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

As of round 967, the 16×16 hex board has 169 occupied cells: 107 `ffa4`-mode
(58 `4ffa8` + 49 `4ffa` refs), 49 `1v1`-mode, and 13 `2v2`-mode. Every occupied
cell has a non-null `map_seed` **and a set `map_size`** (observed classes:
small, standard, large, huge, giant) — copy both exactly. Deployed canonical
Paintbot was 0.7.227 at verification. Re-resolve these dated values for every
study.

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
- a normal `2v2` invasion does not use the even captain/ally split (captain
  leading half, ally trailing half of each team's seats);
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
