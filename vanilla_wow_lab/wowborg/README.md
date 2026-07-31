# wowborg

`wowborg` is the lab's synchronous Python policy for Vanilla WoW. It uses the
game-owned Gymnasium environment directly:

```text
policy -> VanillaWowEnv.step(AgentAction) -> WS /env -> game-owned WoW client
       -> read-only progress samples       -> WS /player
```

The policy image contains no WoW client and no client adapter. The game owns login,
observation projection, action admission and execution, settlement, reconnects, and
the binary WoW protocol. Wowborg receives canonical `AgentFrame` observations and
submits canonical actions such as `MoveAction`, `CastAction`, and
`AreaTriggerAction`.

The exact environment contract is copied from the deployed accelerated-wow game image
pinned in [`../tools/versions.env`](../tools/versions.env). Source-level dependency
resolution is pinned to the matching owner commit in the root `pyproject.toml`.

## Layout

- `environment.py` — hosted endpoint derivation and the thin `GymSession` convenience
  around `VanillaWowEnv.reset()` / `step()`. It also calls the upstream read-only
  navmesh SDK. If the game advances past a submitted frame, the hosted runtime
  drains any queued typed request errors, consumes the current frame already
  pushed on that `/env` connection, and traces `frame_refresh` before continuing.
- `main.py` — resets the environment, runs one synchronous policy loop, closes the
  session, and uploads evidence.
- `player_progress.py` — opens the owner-supported `/player` observer channel and
  projects canonical frames into live level/XP/displacement progress. It never
  submits gameplay actions; `/env` remains the sole controller. The policy stops
  35 seconds before the handed-off session deadline so it can send `done` and
  leave the game time to finalize replay/results, matching the owner reference
  player.
- `policies/` — policy registry selected by `WOWBORG_POLICY`; `world_race` is the
  image default. World Race retries one station journey once when its first
  attempt ends in transient `no_progress`.
- `nav/` — local movement supervision, route planning, and world-graph journeys.
- `trace.py` and `artifact.py` — structured `trace.jsonl` output and optional
  session-end artifact upload.
- `Dockerfile` — copies only `environment/` and `player/sdk/` from the pinned game
  image into a small Python policy image.

## Runtime inputs

The hosted runner provides `COWORLD_PLAYER_WS_URL`. Wowborg derives:

- the authenticated WebSocket `/env` endpoint used by `VanillaWowEnv`; and
- the authenticated WebSocket `/player` endpoint used for live session identity
  and progress reporting; and
- the authenticated HTTP `/player/navigation` endpoint used by
  `player.sdk.navmesh`.

Useful knobs:

- `WOWBORG_POLICY` (`world_race`, `waypoint_race`, or `random_walk`)
- `WOWBORG_DURATION_SECONDS` (default `86400`)
- `WOWBORG_STARTUP_TIMEOUT_SECONDS` (default `240`)
- `WOWBORG_STEP_TIMEOUT_SECONDS` (default `30`)
- `WOWBORG_RUNTIME_DIR` and `WOWBORG_TRACE_FILE`
- `WOWBORG_STATIONS` for a JSON world-race station catalog

## Validation and build

```bash
uv run pytest vanilla_wow_lab/wowborg/tests -q
vanilla_wow_lab/tools/route_lab.sh stations
vanilla_wow_lab/tools/build_player.sh
```

The tests cover the direct `/env` wrapper and navigation behavior. The route lab
mounts current wowborg source into the pinned deployed game image and uses its real
navmesh data and helper. The build check verifies the canonical environment imports
and rejects an image containing either historical bundled WoW client.

Historical adapter designs and results remain in `docs/designs/`, `docs/recon/`, and
[`VERSION_LOG.md`](VERSION_LOG.md); they are not part of the current runtime.
