# player_labs — deferred tasks

Tasks intentionally parked to handle later. Add items here when you defer something
mid-session; check them back at the start of focused work.

## Open

- **Move the Coworld websocket transport/bridge into the player SDK** (flagged by James,
  2026-06-24). Today each player carries its own transport: crewborg's lives in
  `crewrift_lab/crewrift/crewborg/coworld/policy_player.py` (`run_bridge` — connects to the
  engine `/player` ws, drives the per-tick loop), and the SDK's `message_bridge.py` /
  `cogweb_bridge.py` are separate, neither with reconnect. The Coworld transport (Sprite-v1
  binary ws, the runner's `COWORLD_PLAYER_WS_URL` contract, the abrupt-close=game-over
  semantics, and now reconnect) is a *shared* concern: it should be ONE importable module in
  the multiplayer SDK that any Coworld-style player builds on, so future players inherit a
  transport we know works. Scope: factor crewborg's `run_bridge` + the aggressive-reconnect
  logic (added 2026-06-24, see below) into `players.player_sdk`, leaving the game-specific
  scene decode / action encode as injected callbacks. Deferred because it's a cross-cutting
  SDK refactor (the SDK is a pinned git dep — needs an upstream change + relock), distinct
  from the immediate crewborg reconnect fix. The reconnect code added to crewborg now is the
  reference implementation to lift.

## Done

_None yet._
