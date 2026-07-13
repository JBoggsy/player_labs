# Cady — Heartleaf player design (v1)

**Status:** proposed (2026-07-06, rev 2 — now on the SDK's SpriteV1 bridge). Living design
doc; update as implementation reveals new facts. **Player:** `cady` (named for Cady Heron,
*Mean Girls*). **Build path:** raw Sprite-v1 on the Coworld Player SDK — using the SDK's new
`run_sprite_bridge` (no vendored wire layer), with an `AgentRuntime` + `Mode` brain.
**Decision policy:** deterministic (no LLM in v1).

> **Rev 2 change (2026-07-06):** the Player SDK now ships a BitWorld/SpriteV1 transport bridge
> (`players.player_sdk.sprite_bridge`, coworld-tools PR #20, merged at `e8921a6`). Cady uses it
> instead of vendoring a Sprite-v1 decoder from crewborg. This removes the entire `wire/` layer
> from the plan. **Prerequisite:** our pinned SDK tarball is stale (`6dcd022…`, predates the
> bridge) — bump it to `e8921a6…` (see §2).

## Problem & goal

Heartleaf has no player of ours yet. Cady v1 exists to prove the loop end to end: connect,
read the garden village off the sprite stream, **navigate**, **gather food**, and **host
dinner** at its own house — then exit cleanly. Enough to pass a hosted eval and start the
improvement loop. It must be a **proper cyborg Player-SDK policy** and **modular**, so later
iterations (chat-based guest recruitment, smarter routing, host-vs-visit scheduling) drop in
without rework.

Game reference: [`../heartleaf-gameplay.md`](../heartleaf-gameplay.md). Scoring is
`hosted food × guests`; only hosts score. v1 gets us on the board; **coordination is the next
iteration**, not this one.

### Goals (v1)
- Connect via the SDK's sprite bridge, react to each changed frame, **exit 0** on close.
- **Navigate** the shared map with a bang-bang movement controller.
- **Gather**: locate gardens holding food, path to them, press A to collect.
- **Host**: stop gathering as dinner nears, return to own house, be inside it at 6 PM.
- Emit trace events + metrics via the SDK sinks.
- Be **modular**: perception, policy, and action are separable units with clear interfaces.

### Non-goals (v1 — deferred)
- **Chat / invitations** to recruit guests — the real scoring lever, and the reserved **v2**.
  The architecture reserves the seam (the bridge's `decide` can return `(mask, chat)`; a
  `ChatIntent` on `Command`) but v1 sends no chat.
- Host-vs-visit scheduling; visiting; multi-day food banking.
- Any LLM decision layer.
- A* routing / any sprite-**pixel** decoding (v1 reads labels + positions only — see §7).
- Broad test coverage — the hosted eval is the test.

## Foundation: the SDK now owns the Sprite-v1 transport

The Coworld Player SDK now includes `players.player_sdk.sprite_bridge` — the BitWorld
`/sprite_player` transport bridge. It is the SpriteV1 peer of the cogweb and mettagrid JSON
bridges, built on `run_message_bridge`. **Cady no longer vendors a wire layer.** What the SDK
gives us, all imported from `players.player_sdk`:

- **`run_sprite_bridge(url, decide, *, on_frame, trace_outputs, on_close, teardown, **kw)`** —
  owns the whole transport envelope: connects (verbatim URL), accumulates the binary
  sprite/object record stream into a `SpriteWorld`, calls `decide` once per **changed** frame,
  packs the returned mask/chat into wire packets, and **exits 0** when the server closes.
- **`SpriteWorld`** — the raw accumulated render state handed to `decide`: `sprites: dict[id →
  SpriteDef(sprite_id, width, height, label, data)]`, `objects: dict[id → SpriteObject(object_id,
  x, y, z, layer, sprite_id)]`, a `frame` counter, and `sprite_for(obj)`. It **deliberately does
  not decode sprite pixels/palette or any game semantics** — that is our job.
- **`Button`** (`IntFlag`: UP/DOWN/LEFT/RIGHT/SELECT/A/B) and `pack_input_packet` /
  `pack_chat_packet` — the controller vocabulary; OR buttons into a mask. No vendored button bits.
- **`env_ws_url()`** — resolves `COWORLD_PLAYER_WS_URL`. Pass its result to `run_sprite_bridge`
  verbatim.

`decide(world: SpriteWorld, ctx: SpriteContext) -> mask | (mask, chat) | None` is the single
callback the game supplies (sync or async). Return a `Button`/int mask to hold those buttons,
`(mask, chat)` to also broadcast chat, or `None` to send nothing (the server holds the last
mask); `0` releases all buttons. The bridge is robust by construction — undecodable frames and
invalid `decide` outputs are skipped, never raised, so the process survives the whole episode.

**What we still write is only the game:** interpreting the `SpriteWorld` into Heartleaf state
(perception), deciding what to do (policy), and turning that into a `Button` mask (action).
That is the point of the bridge — the transport and the raw decode are no longer our code.

### Prerequisite: bump the pinned SDK (mechanical, but shared)

Our pinned SDK tarball is stale and predates the bridge:

- `pyproject.toml` `[tool.uv.sources]` pins `players` to coworld-tools archive
  `6dcd022e013febffb0043b5f625f853c5cc36e0f`. **Bump to `e8921a6b18484030d8704277e4c52d3aae5c8917`**
  (current `main`, includes PR #20), then `uv lock`.
- Mirror the bump in `crewrift_lab/tools/versions.env` (`PLAYERS_SDK_REF`) so the hosted image
  builds against the same SDK, and Cady's own `Dockerfile` installs that ref.
- **Shared-SDK caution:** crewborg (crewrift) imports the same `players.player_sdk`. Bumping the
  pin moves crewborg's SDK too. Before relying on the bump, do a quick crewborg import/test pass
  (`uv run pytest crewrift_lab/crewrift/crewborg/tests`) to confirm no SDK-surface regression;
  if something breaks, that is a crewrift concern to resolve alongside, not a blocker for Cady's
  design. This is the first build step (§10).

## Architecture

Package `heartleaf_lab/cady/cady/` (installable module `cady`), mirroring how
`crewrift_lab/crewrift/crewborg/` and `cue_n_woo_lab/mentalist/` vendor their players — but
**without a `wire/` layer**, because the SDK owns the wire now.

```
heartleaf_lab/cady/
  cady/
    perception.py     # SpriteWorld -> HeartleafState (the Percept): self/gnomes/gardens/
                      #   houses/clock-time/inventory  [reads labels + object positions]
    belief.py         # long-lived Belief: own seat/house, learned garden/house geometry,
                      #   time-of-day, inventory, current target
    modes/
      __init__.py
      gather.py       # GatherMode: nearest food garden -> navigate -> press A
      host.py         # HostMode: navigate home -> enter house -> hold through 6 PM
      idle.py         # IdleMode: neutral fallback
    strategy.py       # deterministic mode-selection: clock-driven Gather -> Host
    action.py         # resolve Intent -> Button mask: bang-bang nav + gather-press + enter-house
    types.py          # Observation(world, frame), Percept(=HeartleafState), Belief,
                      #   ActionState, Intent, Command; perceive/update_belief pure functions
    runtime.py        # build_runtime(): assemble AgentRuntime from the six types + modes
    decide.py         # the bridge callback: SpriteWorld -> runtime.step() -> (mask, chat)
    main.py           # run_sprite_bridge(env_ws_url(), decide, trace_outputs=...); __main__
    tools/
      capture_scene.py# a decide that logs world.sprites/objects labels+positions (vocab probe)
    tests/            # perception (label->state) + policy tests
  Dockerfile
  README.md
  VERSION_LOG.md
```

### How the SDK bridge and the AgentRuntime compose
The bridge calls `decide(world, ctx)`; the `AgentRuntime` exposes `step(observation) -> command`.
`decide.py` is the thin adapter between them: it wraps the SDK's `SpriteWorld` + `ctx.frame` in
Cady's `Observation`, calls `runtime.step(obs)`, and unpacks the returned `Command` into the
`(mask, chat)` the bridge expects. So Cady is a genuine cyborg policy (perceive → belief →
strategy → mode → resolve) **and** rides the SDK transport — the adapter is the only glue.

### The six SDK types (mirrors crewborg's cyborg shape)
- **Observation** — `{world: SpriteWorld, frame: int}` (the SDK's raw world, by reference).
- **Percept = `HeartleafState`** — resolved this-tick view built by `perceive(world)`:
  `self_world (x,y)`, `time` (day-minutes parsed from the clock glyphs → an `is_dinner` /
  `past_gather_cutoff` flag), `gardens: [(pos, has_food)]`, `gnomes: [(pos, index, facing)]`,
  `own_house_index`, `houses: [(entrance_pos)]`, `inventory_count`.
- **Belief** — long-lived: own seat/house index, accumulated **garden positions** and **house
  entrance geometry** (the map is static — learn once, cache), `last_time`, `inventory_count`,
  `current_target`.
- **ActionState** — nav route + cursor, `held_mask`, last self position (for velocity),
  edge-press bookkeeping (fresh-A).
- **Intent** — symbolic: `gather_at(garden_pos)` | `navigate_to(point)` | `enter_house(index)`
  | `hold` | `idle`.
- **Command** — `{held_mask: int, chat: str | None = None}`; `decide.py` unpacks it for the
  bridge (chat reserved for v2).

### Per-tick data flow
`/sprite_player` frame → **`run_sprite_bridge`** decodes it into **`SpriteWorld`** (SDK) →
**`decide`** → `perceive()` → `HeartleafState` → `update_belief()` → strategy picks a Mode →
`Mode.decide()` → `Intent` → `resolve_action()` → `Command` → `decide` returns the `Button`
mask → the bridge sends it (on change) and exits 0 on close. Everything left of `decide` is the
SDK's; everything right of it is Cady's.

### Deterministic policy (v1)
Clock-driven, mirroring the villagers' time policy without an LLM:
- **Before ~5:00 PM:** `GatherMode` — target the nearest garden labeled `"garden marker"`,
  navigate, press A; repeat. (Gathering + navigation = the v1 core.)
- **~5:00 PM onward:** `HostMode` — stop gathering, navigate to own house entrance, enter, hold
  inside through 6:00 PM dinner so any visiting gnome scores us.
- **Fallback:** `IdleMode` (neutral mask) before self/clock resolve or when no garden is visible.
The thresholds (gather-stop time, arrive radii) are constants in one config block so each
iteration is attributable.

### Action resolution
The bang-bang d-pad controller is an *algorithm* (not vendored code): steer toward a target
world point with a release-near-target deadband and a predictive stop, emitting a `Button` mask
(crewborg's `action.py` is the reference to reimplement). Intents map directly —
`navigate_to` → mask toward the point; `gather_at` → navigate to the garden then a fresh **A
press** in range; `enter_house` → navigate to the entrance then A to go inside;
`hold`/`idle` → neutral mask.

## Heartleaf wire vocabulary — readable from labels alone (no pixel decode in v1)

The SDK bridge hands us `world.objects` joined to `world.sprites[id].label`; Heartleaf's
`src/heartleaf/protocol.nim` + `heartleaf.nim` encode everything v1 needs **in those labels and
object positions** — so v1 needs **no** sprite-pixel decoding:

| Object base | Meaning | Label (verified in `heartleaf.nim`) |
|---|---|---|
| `1000` | **Gnomes** | `"gnome <index> <direction>"` (e.g. `gnome 3 south`) — index + facing |
| `2000` | Name tags | `"name <PlayerName>"` (e.g. `name Sasha`) |
| `3000` | Chat bubbles · v2 | `"chat …"` |
| `4000` | **Gardens** | `"garden marker"` on a garden that holds food |
| `5000` / `6000` | Inventory items / counts | rendered UI |
| `7000` | **Clock** | per-glyph sprites labeled `"clock <char>"` — concatenate by x → `3:00pm` |
| `7100` | Score panels | `"score …"` |

Reading the **time** is therefore a string join, not a pixel read: collect the clock-glyph
objects (base `7000`), sort by `x`, concatenate their single-char labels, and parse with the
inverse of `clockName` (`parseClockMinutes`). Fixed gnome names by house 0–8: Ivan, Anton,
Yura, Sasha, Maxim, Nikita, Vova, Dima, Egor. `talking_villager.nim` is the reference for
turning these into behaviour.

## Risks & open questions
1. **Self / seat identification** — the sprite stream doesn't announce our seat, and self is not
   a distinct object. crewborg's answer: self = the camera centre (the world-map object's
   placement, base `1`), because the camera follows our gnome. *Mitigation:* the capture probe
   (`tools/capture_scene.py`, a logging `decide`) confirms the camera→self relationship and which
   `"gnome <i>"` is ours before nav is trusted. First implementation milestone.
2. **House / garden trigger geometry** — where exactly to stand and press A to collect / enter.
   Mirror `talking_villager.nim`; confirm with the probe.
3. **SDK pin bump is shared with crewborg** — bumping `6dcd022…→e8921a6…` moves crewborg's SDK
   too; run its tests after the bump (§2). Low risk (the bridge PR is additive), but verify.
4. **Local run path** — the bridge's `PROTOCOL_PATH` is `/sprite_player`, but the local Heartleaf
   server serves `/player`; the bridge uses the injected URL verbatim, so a local run points at
   the server's actual path. Confirm the hosted `COWORLD_PLAYER_WS_URL` path for this game.
5. **Python-image upload path** — the manifest's player `run` is `/bin/<name>`; confirm a Python
   image uploads cleanly for this game (as crewborg does) before the first upload.
6. **League existence / game version** — verify via the Observatory API before the first
   experience request. Carried over from lab creation.
7. **Pixel decode is deferred, not free** — A* over the walkability sprite would need
   pixel/palette decode (the bridge exposes raw `SpriteDef.data`; mettagrid has
   `snappy_decompress` + palette). v1 avoids it entirely by steering straight-line.

## Build order (feeds the implementation plan)
1. **Bump the SDK pin** (`6dcd022…→e8921a6…`) in `pyproject.toml` + `uv lock` + `versions.env`;
   confirm `from players.player_sdk import run_sprite_bridge, SpriteWorld, Button, env_ws_url`
   and run crewborg's tests (shared-SDK check).
2. **Capture probe** — a `decide` that logs `world.sprites`/`objects` labels + positions from a
   real Heartleaf stream; calibrate self/seat + garden/house geometry.
3. `perception.py` + `types.py` — the six types, `perceive` (labels → `HeartleafState`,
   clock-glyph join), `update_belief`.
4. `action.py` — bang-bang nav + gather-press + enter-house, emitting `Button` masks.
5. Modes + strategy (Gather → Host), `runtime.build_runtime`, `decide.py` adapter.
6. `main.py` (`run_sprite_bridge(env_ws_url(), decide, trace_outputs=…)`), `Dockerfile`,
   `README`, `VERSION_LOG`.
7. Build image → local smoke (connects / plays / exits) → upload → **first hosted eval**.

## Testing (minimal, per lab discipline)
- **Perception** — a synthetic `SpriteWorld` with a `"garden marker"` object and `"clock 3"`,
  `"clock :"`, … glyph objects → assert garden position, food flag, and parsed time. (The
  SDK owns + tests the frame decoder, so we don't re-test the wire.)
- **Policy** — assert the clock threshold flips `GatherMode → HostMode`, and no-food falls back
  cleanly.
No coverage for its own sake — the hosted eval is the real test.
