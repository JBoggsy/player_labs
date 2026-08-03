# Working context — paintbot_lab

*The live, minimal, high-signal state of what we're working on right now.
Update as you learn; clear/reseed on a pivot.*

## Current objective

**Get `stencil` its first hosted evaluation.** The lab was bootstrapped
2026-08-03 (full adaptation from ctf_lab; recon + design docs in `docs/`).
stencil v1 is implemented and unit-tested but has never been built as an image,
uploaded, or run in a hosted episode. Next concrete steps:

1. `paintbot_lab/tools/build_player.sh stencil` (needs Docker) → upload as
   policy `stencil`.
2. Create an experience request against the Paintbot roster (start with the
   default/2v2-heavy live mix); stream artifacts.
3. First-eval survey: does it connect/play/exit cleanly on ALL variants
   (especially a 4-team board and a giant board)? Then win-path diagnosis.

## Facts worth carrying forward (verified 2026-08-03)

- Live Paintbot league `league_b8fa9b35-ac22-48cf-a03f-07b397aff1c7`, round
  ~514, a round every ~15 min (~22 episodes each). Deployed game **paintbot
  0.7.178** (ahead of the ctf league's 0.7.174).
- Live rotation observed: ~12x `default` (FIXED classic arena!), ~8x `2v2`,
  1x `4ffa`, 1x `4ffa8` per round. Seating is filler-padded (7+7+1+1 etc.).
- Standings: daveey's `paintbot-focusfire` leads (84 pts), richard 10,
  Jordan 6; **`beacon:v67` is auto-mirrored in from CTF (player "James Botts",
  active) and sits at 0** — its fixed-arena bake is blind on generated maps.
- The game repo is the coworld-ctf clone (`~/coding/coworlds/coworld-ctf`),
  synced to main `1633b7e` at lab creation. Paintbot = same binary + wider
  manifest; no paintbot-specific Nim source exists.

## Open threads

- stencil has never seen a real frame — the walkability decode (cramjam raw
  snappy) and marker parsing are tested against synthetic data only; the first
  hosted run validates the real wire.
- WorldMap Dijkstra cost on a giant board (~86k cells) is untested against the
  24 tps frame budget — measure in the first eval; optimize (or precompute
  during startWait) if frames back up.
- Choke/rally fractions (`STENCIL_CHOKE_FRACTION` 0.45 / `RALLY_FRACTION`
  0.65) are educated guesses, not tuned.
- v1 scope cuts to revisit if evals demand: posts (covered fighting
  positions), item-spawn seeding from layout rules, third-party FFA reasoning.
- Consider whether the mirrored beacon entrant should be retired once stencil
  is submitted (human call; `coworld-player-swap` if identity matters).
