# Cady

Cady is Heartleaf's first player policy: a deterministic cyborg Player-SDK policy
on the SDK SpriteV1 bridge. It reads labeled sprites, gathers visible food during
the day, returns to its recorded home anchor to host at 6:00 PM, and sends no
chat or LLM calls in v1.

## Layout

```
cady/
  perception.py        SpriteWorld labels/positions -> HeartleafState
  belief.py            long-lived home, self, food, clock, and garden cache
  action.py            Intent -> Button mask movement and interaction
  modes/               gather / host / idle mode decisions
  strategy.py          clock-driven mode selection
  runtime.py           AgentRuntime assembly
  decide.py            Sprite bridge callback adapter
  main.py              run_sprite_bridge entry point
  tools/capture_scene.py
```

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
