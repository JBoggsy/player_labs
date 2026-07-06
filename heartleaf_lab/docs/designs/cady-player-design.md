# Cady — Heartleaf player design (v1)

**Status:** proposed (2026-07-06). Living design doc; update as implementation reveals
new facts. **Player:** `cady` (named for Cady Heron, *Mean Girls*). **Build path:**
raw Sprite-v1 on the Coworld Player SDK (`AgentRuntime` + `Mode`s), self-contained wire
layer. **Decision policy:** deterministic (no LLM in v1).

## Problem & goal

Heartleaf has no player of ours yet. We need a first policy that **connects, decodes the
Sprite-v1 scene, navigates the map, gathers food, and hosts dinner at its own house**,
then exits cleanly — enough to pass a hosted eval and start the improvement loop. It must
be a **proper cyborg Player-SDK policy** (uses the SDK's `AgentRuntime`/`Mode` structure,
transport, and observability) and **modular**, so later iterations (chat-based guest
recruitment, smarter routing, host-vs-visit scheduling) drop in without rework.

Game reference: [`../heartleaf-gameplay.md`](../heartleaf-gameplay.md). Scoring is
`hosted food × guests`; only hosts score. v1 gets us on the board; **coordination is the
next iteration**, not this one.

### Goals (v1)
- Connect to the `/player` websocket, decode Sprite-v1 binary frames, exit 0 on close.
- **Navigate** the shared map with a bang-bang movement controller (the reusable core).
- **Gather**: locate gardens holding food, path to them, press A to collect.
- **Host**: stop gathering as dinner nears, return to own house, be inside it at 6pm so
  any gnome who wanders in becomes a scoring guest.
- Emit observability (trace events + metrics) via the SDK sinks.
- Be **modular**: perception, policy, and action are separable units with clear interfaces.

### Non-goals (v1 — deferred to later iterations)
- **Chat / invitations** (parsing `chat @3000`, emitting `encode_chat`) to actively
  recruit guests. This is the real scoring lever and the planned v2 — the architecture
  reserves seams for it (a `ChatIntent` on `Command`, chat lines on the percept) but v1
  does not use them.
- Host-vs-visit scheduling across days; visiting other houses; multi-day food banking.
- Any LLM decision layer.
- Broad test coverage.

## Foundation: what we vendor vs. what the SDK provides

The Player SDK is **engine-agnostic and ships no Sprite-v1 support** — the Sprite-v1
binary substrate exists only in the crewborg example player. So:

- **Vendored (self-contained, ported from crewborg, protocol-level & game-agnostic):** the
  Sprite-v1 byte decoder, the retained `SceneState`, and the input/chat encoders + button
  bits. These are the wire contract, not Crewrift semantics; `cady` owns its copy so it has
  **no dependency on `crewrift_lab`**.
- **Used from the SDK (`players.player_sdk`):**
  - **Transport** — `run_message_bridge` (or the crewborg-style bridge loop) with
    `exit_zero_on_unclean_close`: connect with `max_size=None`, iterate binary frames,
    send-on-change, exit 0 on game-over. `env_ws_url()` resolves
    `COWORLD_PLAYER_WS_URL` (canonical) / `COGAMES_ENGINE_WS_URL` (legacy).
  - **Brain** — `AgentRuntime` generic over cady's six types, `Mode`/`ModeRegistry`/
    `ModeDirective`, `SynchronousStrategyRunner` for the mode-selection strategy.
  - **Observability** — `TraceSink` / `MetricsSink` (+ `TraceOutputs.from_env`).

crewborg's `build_runtime` (`players/crewrift/crewborg/__init__.py`) is the assembly
template; crewborg's `coworld/policy_player.py`, `perception/decoder.py`,
`perception/tables.py`, `coworld/scene.py`, and `action.py` are the port sources.

## Heartleaf wire vocabulary (from `coworld-heartleaf/src/heartleaf/protocol.nim`)

The game exposes a clean, stable object-id + label scheme, which makes raw decoding
tractable. Object-id bases:

| Base | Meaning | Label prefix / label |
|---|---|---|
| `1000` `PlayerObjectBase` | gnomes (players) | `"gnome "` |
| `2000` `NameObjectBase` | name tags | `"name "` |
| `3000` `ChatObjectBase` | chat bubbles | `"chat "` (v2) |
| `4000` `GardenObjectBase` | gardens | `GardenMarkerLabel = "garden marker"` (food present) |
| `5000` `InventoryObjectBase` | inventory items | — |
| `6000` `InventoryCountObjectBase` | inventory counts | — |
| `7000` `ClockObjectBase` | clock | `"clock "` |
| `7100` `ScoreObjectBase` | score panels | `"score "` |
| `1`/`2` | bottom / overhang world layers | `"heartleaf main/home bottom/overhang…"` |

Walkability sprites: `"heartleaf main walkability"`, `"heartleaf home walkability"`.
Fixed gnome names by house index 0–8: Ivan, Anton, Yura, Sasha, Maxim, Nikita, Vova, Dima,
Egor. Chat cap `ChatMaxChars = 48`. The reference for *interpreting* these into behavior is
the game's own `players/talking_villager/talking_villager.nim` (perception + nav + the
`stand_at_house_garden` / `go_home` / gather logic to mirror deterministically).

**Two facts the scheme does not give us, to confirm empirically (see Risks):** the
**self-position camera offset** (self is the camera center + a fixed offset, as in crewborg
— value TBD from a real stream) and the **house entrance geometry** (where to stand / press
A to enter your house).

## Architecture

Package `heartleaf_lab/cady/cady/` (installable module `cady`), mirroring how
`crewrift_lab/crewrift/crewborg/` and `cue_n_woo_lab/mentalist/` vendor their players.

```
heartleaf_lab/cady/
  cady/
    wire/
      decoder.py      # Sprite-v1 byte decode -> SceneState tables (ported)
      scene.py        # retained SceneState dataclass (ported)
      encode.py       # encode_input / encode_chat + button bits (ported)
    perception.py     # SceneState -> HeartleafState (the Percept): self/gnomes/gardens/
                      #   houses/clock/inventory/chat  [Heartleaf-specific]
    belief.py         # long-lived Belief: own house, learned garden/house geometry,
                      #   time-of-day, inventory, current target
    modes/
      __init__.py
      gather.py       # GatherMode: nearest food garden -> navigate -> press A
      host.py         # HostMode: navigate home -> enter house -> hold through 6pm
      idle.py         # IdleMode: neutral fallback
    strategy.py       # deterministic mode-selection: clock-driven Gather -> Host
    action.py         # resolve Intent -> Command (button mask): nav + gather + enter house
    types.py          # Observation, Percept(=HeartleafState), Belief, ActionState,
                      #   Intent, Command; perceive/update_belief pure functions
    runtime.py        # build_runtime(): assemble AgentRuntime from the six types + modes
    main.py           # SDK transport bridge + trace/metrics wiring; __main__ entry
    tools/
      capture_scene.py# decode a stream/replay and dump labels/ids/positions (vocab probe)
    tests/            # wire-frame decoder tests + a few perception/policy tests
  Dockerfile
  README.md
  VERSION_LOG.md
```

### The six SDK types (mirrors crewborg's cyborg shape)
- **Observation** — `{scene: SceneState, tick: int}` (thin, by-reference).
- **Percept = `HeartleafState`** — resolved this-tick view: `self_world (x,y)`, `time`
  (decoded clock → minutes-since-8am + an `is_dinner`/`past_dinner` flag), `gardens:
  [(pos, has_food)]`, `gnomes: [(pos, name?)]`, `own_house_index`, `houses: [(entrance_pos)]`,
  `inventory_count`, `chat_lines` (populated, unused in v1).
- **Belief** — long-lived: `own_house_index`, accumulated **garden positions** and **house
  entrance geometry** (learned once and cached; the map is static), `last_time`,
  `inventory_count`, `current_target`.
- **ActionState** — nav route + cursor, `held_mask`, last self position (velocity),
  edge-press bookkeeping (fresh-A). Ported from crewborg's `ActionState`.
- **Intent** — symbolic: `gather_at(garden_pos)` | `navigate_to(point)` |
  `enter_house(index)` | `hold` | `idle`.
- **Command** — `{held_mask: int, chat: str | None = None}` (chat reserved for v2).

### Per-tick data flow
`binary frame → SceneState.apply() → perceive() → HeartleafState → update_belief()
→ strategy picks a Mode → Mode.decide(belief, action_state) → Intent → resolve_action()
→ Command → send held_mask on change`. Runtime `step()` is synchronous; the SDK bridge
owns the async websocket loop and the exit-0-on-close contract.

### Deterministic policy (v1)
Clock-driven, mirroring the villagers' time policy without an LLM:
- **Before ~5:00 PM:** `GatherMode` — target the nearest garden showing `"garden marker"`,
  navigate to it, press A to collect; repeat. (Gathering + navigation = the v1 core.)
- **~5:00 PM onward:** `HostMode` — stop gathering, navigate to own house entrance, enter,
  and hold inside through 6:00 PM dinner so any visiting gnome scores us.
- **Fallback:** `IdleMode` (neutral mask) before the camera/clock are up or when no garden
  is visible.
The thresholds (gather-stop time, arrive radii) are constants in one config block so each
iteration is attributable.

### Action resolution
Port crewborg's bang-bang d-pad controller (`_movement_mask` / `_axis_input`: move toward
a target world point with a release-near-target deadband and predictive stop). Heartleaf
intents:
- `navigate_to(point)` → movement mask toward the point (straight-line steering first; A*
  over the walkability grid is a later optimization if straight-line wedges).
- `gather_at(garden)` → navigate to the garden, then a fresh **A press** in range to
  collect (edge-triggered, like crewborg's report/task press).
- `enter_house(index)` → navigate to the house entrance, then **A press** to go inside
  (exact trigger geometry confirmed via the capture probe).
- `hold` / `idle` → neutral mask.

## Testing (minimal, per lab discipline)
- **Decoder**: hand-built Sprite-v1 frames (port crewborg's `tests/sprite_wire.py` helpers)
  → assert `SceneState` tables decode (define-sprite, define-object, tick marker,
  walkability).
- **Perception**: a synthetic scene with a `"garden marker"` object and a `"clock "` sprite
  → assert `HeartleafState` extracts garden position, food flag, and parsed time.
- **Policy**: assert the clock threshold flips `GatherMode → HostMode`, and that with no
  visible food the mode falls back cleanly.
No broad coverage; the hosted eval is the real test.

## Risks & open questions
1. **Self-position offset** — self is the camera center + a fixed offset (crewborg pattern);
   Heartleaf's exact offset is unknown. **Mitigation:** `tools/capture_scene.py` dumps the
   camera + object positions from a real stream (via a local run) to calibrate before
   trusting nav. First implementation milestone.
2. **House/garden trigger geometry** — where exactly to stand and press A to collect / enter.
   Mirror `talking_villager.nim`'s logic and confirm with the capture probe.
3. **Straight-line nav vs. A\*** — v1 uses straight-line steering; if the map has walls that
   wedge it, add A* over the streamed `"heartleaf main walkability"` grid (crewborg has the
   pattern). Deferred until an eval shows wedging.
4. **How a custom (non-Nim) player uploads for this game** — the manifest's player `run` is
   `/bin/<name>`; confirm the Python-image upload path (`../player-build.md` + the
   build-and-upload skill) works for Heartleaf, as it does for crewborg. Verify before the
   first upload.
5. **League existence / game version** — verify via the Observatory API before the first
   experience request (open thread from lab creation).

## Build order (feeds the implementation plan)
1. Vendor + test the Sprite-v1 wire layer (`wire/`), with the capture probe.
2. **Calibrate** self-offset + garden/house geometry from a captured Heartleaf stream.
3. `perception.py` + `types.py` (the six types, `perceive`, `update_belief`).
4. `action.py` (nav + gather-press + enter-house), ported controller.
5. Modes + strategy (Gather → Host), `runtime.build_runtime`.
6. `main.py` (SDK bridge + tracing), `Dockerfile`, `README`, `VERSION_LOG`.
7. Build image → local smoke (connects/plays/exits) → upload → first hosted eval.
