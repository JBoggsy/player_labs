# Paintbot game-contract audit — 2026-08-06

## Scope

Audited all repository-owned Markdown and controller-facing comments under
`paintbot_lab` against the latest deployed Paintbot source. Current references
were corrected; immutable request fixtures, version history, dated reports,
and recon evidence were retained as history and labeled where a former game
contract could mislead a current reader.

## Authoritative snapshot

- Canonical game: `paintbot:0.7.206`, Coworld
  `cow_eb4a0cde-ee3e-4d4d-9b4c-d001fbcd2495`, manifest
  `sha256:06c7fc29c740b1ff5fbca33089170336a50b526e9788085963d6a2a3d4a19351`.
- Exact deployed source: `ec244e6b01485e8c7acd7a7929a9268354d50957`
  in `Metta-AI/coworld-ctf`; GameVersion 40.
- Project-local CLI: `coworld 0.1.35`; a lockfile dry-run found no newer
  resolved `coworld` package.
- Campaign: enabled, round 381, 10x10, 600-second rounds, at most three
  invasions per player, episode outcomes, Claude Sonnet 5 strategist.
- Board: 26 `1v1`, 26 `2v2`, and 48 `4ffa` refs, resolving to 52 mode-`2v2`
  and 48 mode-`ffa4` cells; all 100 cells have map seeds and previews, while
  all 100 `map_size` values are null.

Live facts above are a dated verification snapshot. Operational docs require a
fresh resolution before each experiment.

## Source history reviewed

The audit compared deployed 0.7.206 with the lab's previous 0.7.199 pin and
traced the intermediate releases:

- 0.7.199 was already GameVersion 39 and included polygon/trench terrain,
  GV38 spray-direction locking, and GV39 `quadmirror` symmetry.
- 0.7.203 temporarily configured one aim slot per tick under the discrete
  model.
- 0.7.204 introduced GV40, restored continuous integer-brad aim, and restored
  `aimTurnRate=5` as five brads per tick.
- 0.7.205 changed the `1v1` game variant from two seats to 16, split into two
  eight-agent teams. Policy ownership of those seats is imposed later by the
  scheduler; current campaign invasions use 7+7+1+1, not one policy per team.
- 0.7.206 changed viewer behavior and retains the GV40/seating contracts.

## Findings and resolutions

| priority | finding | resolution |
| --- | --- | --- |
| P0 | Stencil still solved aim on GV36's 32-slot ring and treated one input as 40 brads | Replaced it with signed shortest-angle steering at 5 brads/tick and a 2-brad deadband; removed slot-only state and traces. |
| P1 | Current docs still named 0.7.199 and sometimes GV36 | Updated live provenance to 0.7.206/GV40 and pinned the exact source in `tools/versions.env`. |
| P1 | Evaluation docs treated the disabled ladder's four-entrant 3:1:1 rotation as live | Rewrote the normative contract around current campaign cells and final participant rows. |
| P1 | `1v1` was documented as a two-seat, debug-only duel | Documented 0.7.205's 16-seat game format and its current campaign classification as mode `2v2`. |
| P1 | Initial audit work inferred two clean eight-agent policies from variant `1v1` | Traced current Metta `variant_modes` and `_duo_roster`: normal invasions actually use four policies in 7+7+1+1 captain/ally seating, with captains swapped in a paired episode. |
| P1 | Docs required `mapSize` even though every current campaign value is null | Require the full cell tuple but omit `mapSize` when the selected cell leaves it unset. |
| P2 | Terrain docs omitted polygon/mapkit shapes, trenches, pits, and `quadmirror` | Expanded the reference while preserving the baked walkability raster as Stencil's authoritative input. |
| P2 | Spray behavior implied the cone could follow turning | Documented that aim locks at trigger pull for all five active ticks; only the origin moves. |
| P2 | The new per-team handicap init marker was undocumented | Added its wire format and recorded that Stencil does not yet consume it. |
| P2 | Current champion/status docs still named v47 | Updated them to the verified v52 champion and kept v53 labeled rejected. |

## Intentionally historical surfaces

`VERSION_LOG.md`, dated recon and reports, checked-in request/result JSON, and
lesson archives retain the versions, rules, maps, and outcomes that actually
produced their evidence. The two aim reports and the archived GV36 lesson now
carry explicit GV40 supersession notes. Historical 0.7.199 audit claims remain
unchanged because that audit is itself provenance.

## Remaining gaps

- Stencil does not parse the new `handicap ...` marker, so policy decisions do
  not yet adapt to asymmetric HP, lives, speed, or miss chance.
- Stencil's current static parity squads match the disabled ladder's equal
  entrant blocks, not campaign 7+7+1+1 seating. This controller iteration
  preserves v52 behavior; the roster-aware fix is recorded in `TODO.md`.
- The Sprite-v1 init contract still does not state roster muster. Stencil must
  infer it from observed identities; the durable task remains in `TODO.md`.
- Current campaign evaluation tooling must resolve the cell, battle kind, and
  exact commissioner roster at request creation time; no checked-in
  adapter automates the whole contract yet.

## Validation

- Read the exact deployed manifest, sim implementation, rules, and upstream
  tests at source `ec244e6b01485e8c7acd7a7929a9268354d50957`.
- Compared every deployed source change from 0.7.199 through 0.7.206.
- Queried the live league/campaign snapshot and project-local CLI version.
- Traced the up-to-date Metta campaign commissioner on clean `main`
  (`a1de9cc49ca51a27d49e41d09836b9cdd885b477`), including `variant_modes`,
  `_duo_roster`, claim fallback, and paired captain seatings.
- Searched all Paintbot Markdown, Nim, and version-pin files for obsolete aim,
  version, seating, scheduler, and map-size claims; historical hits were
  classified rather than silently rewritten.
- Built the corrected native player image against the exact 0.7.206 source pin
  and ran repository documentation/link checks.
- Expanded six hosted v54/v52 replays with a temporary reader compiled against
  that exact source. All six replay hashes passed through game over; observed
  heading deltas, gun events, impacts, hits, kills, and deaths were derived from
  the re-simulated engine state rather than policy belief alone.
