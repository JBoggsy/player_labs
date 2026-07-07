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

## v2–v6 — 2026-07-06/07 (nav foundation + coordinate-system fixes)

The navigation build-out and the self-position bug hunt. See `git log -- heartleaf_lab/cady`
for the per-commit detail; the arc:

- **v2** — baked map + A*-based router (`bf700ff`).
- **v3** — hierarchical router for fast arbitrary-point nav (`f3fefd5`); baked house
  interior + in/out-of-house detection + exit mode + diagnostics; circuit-following
  gather on the baked nav (`63d15e5`, `97db00f`).
- **v4–v6** — the coordinate-system fixes: self = own gnome **foot** (the root cause of
  every zero score, `6a6db67`), then + camera offset because the main map scrolls
  (`8e91650`). After these, Cady moves on the main map and exits the house — but still
  harvests nothing (inventory stays 0); she routes toward gardens but never lands within
  the 40px harvest radius. v7 + the replay tooling exist to diagnose exactly that.

## v7 — 2026-07-07 (announce username 'Cady')

Announce the display name **Cady** via a `?username=Cady` query param on the connection
URL (`76131f5`), so Cady is identifiable in replays. This is the enabling change for
debugging navigation with the replay expander + `viz_replay --player Cady` (see
`../docs/replay-tools.md`): without a stable name we can't spotlight her path. No behaviour
change beyond the announced name.
