# Working context — paintbot_lab

*The live, minimal, high-signal state of what we're working on right now.
Update as you learn; clear/reseed on a pivot.*

## Current objective

**Review `stencil:v5`'s generated firing/duck posts, then decide whether to tune
the metric or wire posts into one behavior.** v5 is uploaded with full tracing
but is not submitted to the Paintbot league. Post knowledge is diagnostic only:
no role, objective, or movement behavior consumes it yet.

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

1. Review the five pinned-map post viewers with James, including each
   per-opponent front in the four-team maps.
2. Human-led choice: tune the static post metric, or make one defender behavior
   consume it with activation tracing.
3. Run a matched hosted evaluation for that one behavioral change. League
   submission remains human-gated.

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
- Deployed game **paintbot 0.7.183**, source `95bb768`. Game repo = the
  coworld-ctf clone (`~/coding/coworlds/coworld-ctf`); no paintbot-specific Nim
  source exists. 0.7.179 added the two-seat generated-map `1v1` variant; 0.7.180
  landed PR #219's reduced bot sprite traffic; 0.7.181 fixed the 32-seat replay
  viewer's hash mask; 0.7.182 added campaign documentation; and 0.7.183 made
  Sprite-v1 object placements retained/delta-encoded plus FOV optimizations.
- Project-local `coworld` is pinned at **0.1.35**, which provides the campaign
  commands (`board`, `history`, `prompt`, `set-prompt`, and related views).

## Open threads

- `stencil:v5` (`6f571639-7a5b-42b7-bf2e-113be8377602`) is the current upload,
  with full artifact tracing and **not submitted**. It adds online, own-team,
  per-opponent firing/duck post knowledge. Five pinned hosted probes (small and
  large sides; standard corners; huge plus; giant corners) completed on
  0.7.183 with zero failures. The final post pass measured 20 ms / 109 ms /
  164 ms / 1.16 s / 2.78 s respectively. `stencil:v1` remains the accepted
  bootstrap/parity baseline; the Nim replay oracle matched **169,235** captured
  decisions exactly.
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
  layout rules, battle plans, and third-party FFA reasoning (relevant: ffa4 battles have a
  defender + recruits — "which team is the real enemy" now has an answer).
- Consider whether the mirrored beacon entrant should be retired once stencil
  is submitted (human call; `coworld-player-swap` if identity matters).
