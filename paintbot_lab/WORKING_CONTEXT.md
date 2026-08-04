# Working context — paintbot_lab

*The live, minimal, high-signal state of what we're working on right now.
Update as you learn; clear/reseed on a pivot.*

## Current objective

**Run the native Nim `stencil` through its first hosted evaluation.** The
Python-to-Nim port is complete and exact under the local differential corpus;
the release image connects and completes canonical local play. It has never
been uploaded or run in a hosted episode.

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

1. `paintbot_lab/tools/build_player.sh stencil` (needs Docker) → upload as
   policy `stencil`.
2. Create an experience request against the Paintbot roster (start with the
   default/2v2-heavy live mix); stream artifacts.
3. First-eval survey: does it connect/play/exit cleanly on ALL variants
   (especially a 4-team board and a giant board)? Then win-path diagnosis.

## Facts worth carrying forward (verified 2026-08-03)

- **The Paintbot league runs the CAMPAIGN round brain, not a ladder**
  (`league_b8fa9b35-ac22-48cf-a03f-07b397aff1c7`; `GET .../campaign` →
  enabled, campaign round ~123, 10x10 board, 600s rounds, outcomes=episodes,
  strategist claude-sonnet-5). Campaign rounds stamp `purpose: "ladder"` — do
  not be fooled again. Full model: the recon addendum + gameplay doc.
- **Standings = territory**: daveey owns 84/100 cells, richard 10, Jordan 6;
  everyone else (incl. the mirrored `beacon:v67` as "James Botts") 0.
- **Every cell permanently owns a map**: variant mix 29x 4ffa8 / 26x 4ffa /
  25x default / 20x 2v2; ALL 100 cells have pinned `map_seed` + `map_size`
  (40 standard/25 large/14 small/14 huge/7 giant). Battles pin the TARGET
  cell's mapSeed+mapSize (deployed 0.7.181 manifest declares both), so cell
  terrain is stable and offline-reproducible from the public generator.
- Battle modes: 2-team cells → 2v2 (captains + mirrored allies, both
  seatings); 4-team cells → ffa4 (≤4 policies + recruits/filler). Observed
  seatings (7+7+1+1 etc.) are these rosters.
- Deployed game **paintbot 0.7.181**, source `347deef`. Game repo = the
  coworld-ctf clone (`~/coding/coworlds/coworld-ctf`); no paintbot-specific Nim
  source exists. 0.7.179 added the two-seat generated-map `1v1` variant; 0.7.180
  landed PR #219's reduced bot sprite traffic; 0.7.181 only fixes the 32-seat
  replay viewer's hash mask and does not alter simulation or player traffic.
- Our pinned `coworld` CLI predates `coworld campaign ...`; direct API calls
  with `softmax.auth.load_current_token(server="https://softmax.com/api")`
  work (see the recon addendum).

## Open threads

- Exact canonical local episodes now validate real Sprite frames, walkability
  decode, marker parsing, navigation construction, and the packaged native
  image. The Nim replay oracle matched all **169,235** captured decisions
  exactly, including feature-disabled and squads/command configurations. A
  hosted run is still needed to validate the upload/runtime boundary.
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
- Choke/rally fractions (`STENCIL_CHOKE_FRACTION` 0.45 / `RALLY_FRACTION`
  0.65) are educated guesses, not tuned.
- v1 scope cuts to revisit if evals demand: posts, item-spawn seeding from
  layout rules, third-party FFA reasoning (relevant: ffa4 battles have a
  defender + recruits — "which team is the real enemy" now has an answer).
- Consider whether the mirrored beacon entrant should be retired once stencil
  is submitted (human call; `coworld-player-swap` if identity matters).
