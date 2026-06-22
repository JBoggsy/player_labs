# agricogla_lab

Player lab for **Agricogla** (4-player Agricola coworld; `cogweb.player.v1` protocol).

## Policy: `agricogla.farmhand`
A PARAMS-weighted heuristic scorer on the Player SDK:
- Wire envelope handled by the SDK's `run_cogweb_bridge` (cogweb engine bridge).
- Decision logic in `farmhand/brain.py` — food-safety first, room-before-grow,
  grow-only-with-a-food-engine, breadth (flip −1 categories), sow-before-bake.
- `farmhand/params.py` is the beam-search surface; variants in `candidates/`.
- Per-decision telemetry emitted via `TraceOutputs` → episode artifact (for the reporter).

Entry point: `python -m agricogla.farmhand` (reads `COWORLD_PLAYER_WS_URL`).

## Candidates (seed beam)
A family-growth-race · B renovation-stone · C breadth-fill · D food-sequencing.
Bake one with `AGRICOGLA_PARAMS=$(cat candidates/<X>.json)` or build-time ARG.

Strategy basis: see cubi-boses memory `agricola-strategy` + STRATEGY.md.
