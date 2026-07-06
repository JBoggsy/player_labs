# Cady Version Log

## v1 — 2026-07-06

Deterministic gather-and-host baseline on the SDK SpriteV1 bridge.

- Connects through `players.player_sdk.run_sprite_bridge`.
- Reads labels and positions only; no pixel decoding.
- Navigates to visible food gardens before the gather cutoff.
- Returns to the recorded home anchor and holds there for dinner hosting.
- Sends no chat and uses no LLM.

This is the connect/gather/navigate/host/exit baseline. Coordination through
chat invitations is planned for v2.
