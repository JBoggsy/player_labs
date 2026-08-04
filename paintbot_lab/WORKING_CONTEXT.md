# Working context — paintbot_lab

*The live, minimal, high-signal state of what we're working on right now.
Update as you learn; clear/reseed on a pivot.*

## Current objective

**The fixed-strategy defensive-mechanics search is complete; decide whether to
relax the strategy constraint.** `stencil:v20` is the accepted upload with full
tracing and is not submitted to the Paintbot league. It keeps the generated
homeward posts, corrected GameVersion 36 five-slot aim, and live-threat cover,
then adds defender-only heart-threat gun-target scoring. Roles, movement,
objectives, post assignment, aim, and the fire gate are unchanged.

Fast local path: `tools/self_play.py` runs native `coworld-ctf`, enables
Sprite-v1 ready pacing, rotates candidate teams, supports candidate-only env
overrides, and parallelizes episodes. Before every batch it resolves the live
canonical Paintbot manifest and fetches/builds its exact source commit in a
managed detached worktree; resolution or verification failure aborts the run.
Measured on this machine at game source
`b6545a3`: 300-tick 1v1 = 2.38s / 129 ticks/s (versus 13.75s / 22.2 ticks/s
without ready); 8 full 5,000-tick 1v1 draws with 4 workers = ~39s wall; full
16-seat 2v2 = 16.17s / 131 ticks/s; full giant 32-seat 4ffa8 = 110.45s / 18.3
ticks/s.

Next concrete steps:

1. Human decision: preserve the fixed strategy and accept that it cannot stop
   one opponent capturing another opponent's heart, or reopen third-party FFA
   positioning/targeting as a strategy change.
2. If strategy remains fixed, use v20 as the fully observable accepted
   mechanics baseline.
3. League submission remains human-gated.

## Facts worth carrying forward (verified 2026-08-04)

- **The Paintbot league runs the CAMPAIGN round brain, not a ladder**
  (`league_b8fa9b35-ac22-48cf-a03f-07b397aff1c7`; `GET .../campaign` →
  enabled, campaign round 202, 10x10 board, 600s rounds, outcomes=episodes,
  strategist claude-sonnet-5). Campaign rounds stamp `purpose: "ladder"` — do
  not be fooled again. Full model: the recon addendum + gameplay doc.
- **Standings = territory**: at round 202 daveey owned 80/100 cells, richard
  8, and six other owners split the remaining 12.
- **Every cell permanently owns a map**: variant mix 29x 4ffa8 / 26x 4ffa /
  25x default / 20x 2v2; ALL 100 cells have pinned `map_seed` + `map_size`
  (40 standard/25 large/14 small/14 huge/7 giant). Battles pin the TARGET
  cell's mapSeed+mapSize (the deployed manifest declares both), so cell
  terrain is stable and offline-reproducible from the public generator. The
  cell size overrides the variant default: the live board includes 16
  standard-size `4ffa8` cells and one giant `4ffa` cell, so size cannot infer
  muster.
- Battle modes: 2-team cells → 2v2 (captains + mirrored allies, both
  seatings); 4-team cells → ffa4 (≤4 policies + recruits/filler). Observed
  seatings (7+7+1+1 etc.) are these rosters.
- Deployed game **paintbot 0.7.184**, source
  `352d0e5408245710874abcfb861ad88491156238` (GameVersion 36). Game repo = the
  coworld-ctf clone (`~/coding/coworlds/coworld-ctf`); no paintbot-specific Nim
  source exists. 0.7.179 added the two-seat generated-map `1v1` variant; 0.7.180
  landed PR #219's reduced bot sprite traffic; 0.7.181 fixed the 32-seat replay
  viewer's hash mask; 0.7.182 added campaign documentation; and 0.7.183 made
  Sprite-v1 object placements retained/delta-encoded plus FOV optimizations.
- Project-local `coworld` is pinned at **0.1.35**, which provides the campaign
  commands (`board`, `history`, `prompt`, `set-prompt`, and related views).

## Open threads

- `stencil:v20` (`bf6f3048-4fa2-4015-bf75-dc7bf0928149`) is the current upload,
  with full artifact tracing and **not submitted**. Against the natural
  top-policy 4FFA field, the v9 aim behavior improved replay hit rate from
  20.9% to 51.5% and kills/episode from 4.63 to 11.13 versus v7. Every one of
  nine observed own-heart thefts was recovered. A six-map locked 4FFA A/B
  rejected v11's forced-forward selector (56 to 23 kills; 54.7% to 43.9% hit
  rate) and restored v9's homeward selection in v12. A fresh replicated
  18-episode field then rejected alignment strafe, exact 14 px fire gating,
  paired-post ducking, home-banded score ranking, and generated-axis sweeping;
  none improved defender outcomes. v20's defender-only heart-threat target
  term then replicated in the same direction across two fresh 18-per-arm
  batches: 2W/1D/33L to 8W/2D/26L, defender kills 5.11 to 6.42 per episode,
  and non-loss Fisher p=0.063. Full report:
  `docs/reports/stencil-defensive-mechanics-2026-08-04.md`.
- **Commander prompt** (new, campaign-specific): each player steers its LLM
  strategist with a private standing-orders prompt — a cheap, high-leverage
  competitive axis independent of the policy image. Needs a first draft when
  stencil is submitted (what cells to prefer: modes/sizes stencil is best at,
  weak owners, adjacency consolidation).
- **Per-cell map-knowledge layer** (optional, now possible): the 100
  (variant, map_seed, map_size) triples are API-readable and the generator is
  deterministic — we could regenerate all cell maps offline, precompute
  walkability/choke data, and ship a map-recognition lookup (keyed by map
  signature) in the image. Decide after first evals whether it beats pure
  online play.
- Navigation startup profiling is complete: 100 maps / 200 seats across all
  five sizes under 16-process contention. Giant p95 is 419 ms, max 454 ms;
  standard p95 is 68 ms. Dijkstra is ~82% of giant startup. Full report:
  `docs/reports/nav-init-profile-2026-08-03.md`.
- Navigation knowledge is now directly inspectable: `self_play.py
  --visualize-nav` enables the opt-in `STENCIL_TRACE_NAVIGATION=1` payload, and
  `tools/render_nav.py` renders its walkability, cover, tactical anchors,
  per-front post scores/fire rays/duck pairs, and cached distance/next-hop
  fields from either JSONL or a hosted artifact ZIP.
  Validated locally on 0.7.182 / `3151a47`, then hosted across all competitive
  variants on 0.7.183 / `95bb768`.
- Choke/rally fractions (`STENCIL_CHOKE_FRACTION` 0.45 / `RALLY_FRACTION`
  0.65) are educated guesses, not tuned.
- Remaining v1 scope cuts to revisit if evals demand: item-spawn seeding from
  layout rules, battle plans, and third-party FFA reasoning. The latter is now
  the observed limit on an all-map draw-or-win target: own-heart defense cannot
  prevent one opponent from ending 4FFA by capturing another opponent's heart.
- Consider whether the mirrored beacon entrant should be retired once stencil
  is submitted (human call; `coworld-player-swap` if identity matters).
