# Vanilla WoW player contract

Wowborg uses the game-owned `VanillaWowEnv` and canonical `Observation` and `Action`
types. The policy receives `COWORLD_PLAYER_WS_URL`, connects to the authenticated
`/player` endpoint and calls `reset()` and `step(Action)` synchronously. The game
owns the WoW client, binary protocol, login, settlement and reconnect handling.

An observation's frame identity matters. Use the current offered frame for the next
action, respect terminal state and inspect structured request errors. Join policy
and game telemetry by exact frame and movement identities rather than approximate
timestamps. The same slot must not be opened through a second control connection.
