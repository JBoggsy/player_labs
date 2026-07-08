# Cady

Cady is Heartleaf's player policy — a **deterministic** cyborg Player-SDK policy
on the SDK SpriteV1 bridge (no LLM yet). It reads labeled sprites and plays the
full day on a clock-driven schedule:

- **Gather** (until 3 PM): follow a baked 39-garden circuit, harvesting food.
- **Invite** (3–4:45 PM): rush a door-to-door tour of the 8 other houses,
  broadcasting a chat invite ("Party at *\<owner\>*'s house at 6!") to any
  villager in view — this trips their commitment logic to attend *our* party.
- **Host** (5 PM → the 6:55 PM dinner resolve): enter our own house and hold
  inside, where the game scores us `food × guests`.

It is the **Heartleaf league champion** (v20). The scoring, timing, and villager
mechanics it exploits are documented in `../docs/heartleaf-gameplay.md` and
`../docs/villager-dinner-attendance.md`; the social-controller design (incl. the
planned LLM layer) is in `../docs/designs/cady-social-llm-controller.md`.

## Layout

```
cady/
  perception.py        SpriteWorld labels/positions -> HeartleafState (self, gnomes, clock)
  belief.py            long-lived home, self, food, clock, gardens, gnomes, invite/nav state
  action.py            Intent -> Button mask; press-and-verify A cadence (no spam)
  navigator.py         cached waypoint follower + stuck-detection re-plan
  nav.py               hierarchical A* pathfinder over the baked walk grid
  modes/               idle / exit_house / gather / invite / host mode decisions
  strategy.py          clock-driven mode selection (gather -> invite -> host)
  occupancy.py         baked per-hour occupancy heatmap lookup (crowd-seeking fallback)
  mapdata.py           loads baked walk grids, garden circuit, house targets, occupancy.npz
  runtime.py           AgentRuntime assembly (perceive -> belief -> strategy -> mode -> action)
  decide.py            Sprite bridge adapter + CADY_DIAG tracing (snapshots + transitions)
  main.py              run_sprite_bridge entry point (announces username, disables ws keepalive)
  tools/               capture_scene, bake_map, build_occupancy_heatmap
```

## Tracing

Set `CADY_DIAG=1` (default on) to log `CADY_DIAG` lines to stderr (folded into
the episode's policy log): periodic full-state **snapshots** (belief + nav +
social + scene) and immediate **transition** lines on any mode / strategy /
inventory / invite-tour / party-commit / chat change. The SDK trace sink also
writes mode/strategy/fallback events to the episode artifact.

## Test

```bash
uv run pytest heartleaf_lab/cady/tests -q
```

## Capture Probe

```bash
COWORLD_PLAYER_WS_URL=ws://... uv run python -m cady.tools.capture_scene --frames 40
```

## Run

```bash
COWORLD_PLAYER_WS_URL=ws://... uv run python -m cady
```

## Image

Build with context `heartleaf_lab/cady`. The Dockerfile installs the pinned
`players[bedrock]` SDK from `coworld-tools`, copies this package to `/app/cady`,
and runs `python -m cady`.

Design: [`../docs/designs/cady-player-design.md`](../docs/designs/cady-player-design.md)  
Plan: [`../docs/plans/2026-07-06-cady-player.md`](../docs/plans/2026-07-06-cady-player.md)
