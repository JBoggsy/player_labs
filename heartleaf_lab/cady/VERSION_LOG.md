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

## v9 — 2026-07-07 (fix: reliable harvesting — press A in real range, retry until picked up)

v8 finally stayed connected and gathered, but only harvested in 13/15 games and converted
just ~60% of its garden approaches to food. Cause: a threshold/target mismatch. `gather.py`
fired `gather_at` (and advanced the circuit) within 40px of the garden **rect** — matching
the game's `InteractionRadius` — but `action.py` only pressed A within a stale
`GATHER_RANGE=12` of the **approach point**, otherwise it emitted a *movement* mask. So in
the 12–40px band `gather_at` walked instead of pressing A, and the circuit had already
advanced, losing that garden. Confirmed in the logs: the held mask at every `gather_at`
tick was a movement bit, never A (`1<<5`).

Fix: (1) `gather_at` now presses A every frame (and nudges toward the approach point to
settle a small perception offset) — `action.py`; (2) `gather.py` stays on the garden and
retries until a pickup is confirmed (inventory rose) or a short timeout (`MAX_GATHER_TICKS`),
instead of firing once and moving on. Local self-play (9 clones colliding on one circuit)
went from 0 harvests to real pickups; hosted eval to confirm.

## v8 — 2026-07-07 (fix: disable websocket keepalive — Cady stayed connected only ~33s)

**The bug that made every prior version score 0.** Cady disconnected ~20–48s into
*every* game (tick ~456–1152) and was absent for ~97% of it — not a navigation bug, a
connection bug. Root cause: the SDK bridge connects with the `websockets` default
keepalive (ping 20s / timeout 20s), and Cady's per-frame `decide` runs synchronously in
the async loop, delaying pong handling past the timeout → `websockets` tears down the
connection (reported as "server closed the connection"). Reproduced locally: all 9 self-play
instances dropped at tick ~800; with `ping_interval=None` all 9 survived to game end.

Fix: pass `ping_interval=None` to `run_sprite_bridge` (`main.py`) — the game's continuous
frame stream is the liveness signal, so library pings aren't needed. Diagnosed with the
replay expander + `viz_replay` and `coworld-local-run` (see `../docs/replay-tools.md`).

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
