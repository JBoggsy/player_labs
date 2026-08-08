# wowborg

`wowborg` is the lab's synchronous Python bot for Vanilla WoW. A thin strategy
layer selects the competition objective while shared capabilities use the
game-owned Gymnasium environment directly:

```text
strategy -> shared navigation/recovery -> VanillaWowEnv.step(Action)
         -> WS /player -> game-owned WoW client
```

The policy image contains no WoW client and no client adapter. The game owns login,
observation projection, action admission and execution, settlement, reconnects, and
the binary WoW protocol. Wowborg receives canonical `Observation` values and
submits canonical flat `Action` values for movement, invocation, input, and
waiting.

The exact environment contract is copied from the deployed traverse-wow game image
pinned in [`../tools/versions.env`](../tools/versions.env). Source-level dependency
resolution is pinned to the matching owner commit in the root `pyproject.toml`.

## Layout

- `environment.py` — hosted endpoint derivation and the thin `GymSession` convenience
  around `VanillaWowEnv.reset()` / `step()`. It also calls the upstream read-only
  navmesh SDK. If the game advances past a submitted frame, the hosted runtime
  drains any queued typed request errors, consumes the current frame already
  pushed on that `/player` connection, and traces `frame_refresh` before continuing.
  The host can emit open-ended spell intent labels such as `threat_reduction`
  despite its packaged `SpellObservation` retaining a closed literal set; Wowborg
  widens only that field to `list[str]` before parsing frames.
- `main.py` — resets the environment, runs one synchronous strategy, closes the
  session, and uploads evidence.
- `player_progress.py` — retained legacy progress projection. The semantic policy
  does not open a second connection because the canonical `/player` session owns
  the slot.
- `strategies/` — competition-level objectives selected by `WOWBORG_STRATEGY`.
  `traverse` activates Travel Form immediately and follows the semantic route to
  the Great Lift lower dock. It waits for an actually observed lift platform,
  boards with bounded ordinary movement input, confirms transport attachment,
  rides without piloting, and walks onto the upper dock before resuming normal
  navmesh travel. If the prefix is unavailable, or after the lift completes, the
  strategy falls back to the safest untried reachable frontier with the greatest
  authoritative Kalimdor world X. Route, lift, and frontier activations are traced.
- `policies/` — retained experiment and navigation-benchmark policies; they are
  not selected by the production entry point.
- `nav/` — local movement supervision, route planning, and world-graph journeys.
- `trace.py` and `artifact.py` — structured `trace.jsonl` output and optional
  session-end artifact upload. Every submitted action records `frame_age_ms`
  (policy processing time from receipt of the offered frame to submission),
  `step_round_trip_ms`, submitted/returned frame IDs, raw action status, and whether
  stale-frame refresh occurred. An `action_skipped` event records a locally rejected
  stale or terminal frame. These fields prove whether Wowborg answered each
  offered frame promptly. The 0.1.208 game also retains environment-owned JSONL
  telemetry for `stalls`, `rejected_requests`, `detached_frames`, continuation
  preparation/release, prefix settlement, and forward-control transitions. Join a
  replay stop to that game log by the exact client `movement_time_ms`; do not infer
  host causes from policy timing or wall-clock proximity.
- `Dockerfile` — copies only `environment/` and `player/sdk/` from the pinned game
  image into a small Python policy image.

## Runtime inputs

The hosted runner provides `COWORLD_PLAYER_WS_URL`. Wowborg derives:

- the injected authenticated WebSocket `/player` endpoint used by `VanillaWowEnv`; and
- the authenticated HTTP `/player/navigation` endpoint used by
  `player.sdk.navmesh`.

Useful knobs:

- `WOWBORG_STRATEGY` (`traverse`)
- `WOWBORG_DURATION_SECONDS` (default `86400`)
- `WOWBORG_STARTUP_TIMEOUT_SECONDS` (default `240`)
- `WOWBORG_STEP_TIMEOUT_SECONDS` (default `30`)
- `WOWBORG_RUNTIME_DIR` and `WOWBORG_TRACE_FILE`

## Validation and build

```bash
uv run pytest vanilla_wow_lab/wowborg/tests -q
vanilla_wow_lab/tools/route_lab.sh stations
vanilla_wow_lab/tools/build_player.sh --strategy traverse
```

The tests cover the direct `/player` wrapper and navigation behavior. The route lab
mounts current wowborg source into the pinned deployed game image and uses its real
navmesh data and helper. The build check verifies the canonical environment imports
and rejects an image containing either historical bundled WoW client.

Historical adapter designs and results remain in `docs/designs/`, `docs/recon/`, and
[`VERSION_LOG.md`](VERSION_LOG.md); they are not part of the current runtime.
