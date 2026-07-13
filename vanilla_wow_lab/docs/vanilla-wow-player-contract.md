# Vanilla WoW — player contract

**What any Vanilla WoW Coworld player must do over the wire, and how it's shipped.** This
is the counterpart to [`vanilla-wow-gameplay.md`](vanilla-wow-gameplay.md) (the game
itself): here we cover how a player *connects*, what it *observes*, what it *emits*, the
integrity rules it must obey, and what a submittable image looks like.

The single most important fact, up front: **a Vanilla WoW player is not a Python SDK
policy on a sprite/text protocol like the other labs' players (crewborg, cady, mentalist).
It is a Nim, packet-level WoW 1.12.1 client** that speaks the real World of Warcraft binary
protocol to a VMaNGOS server. That makes this contract heavier and lower-level than the
sibling labs' — closer to "write a WoW client" than "call an action API."

Citations are `file:line` into `~/coding/coworlds/coworld-vanilla-wow` at the state read on
2026-07-13. Re-verify against the code before trusting prose.

> **Need the exact schema?** This doc is the *narrative* contract. For the exhaustive,
> field-level spec — every message's full field list, the 64-byte action record's byte layout,
> the complete `TelemetrySnapshot`, the `CWBT`/`CWREPLAY` binary formats, and the WS↔TCP tunnel
> — see the companion reference [`vanilla-wow-protocol.md`](vanilla-wow-protocol.md).

---

## The shape of a player

- **Language:** Nim. `player/player.nim` is a thin GUI wrapper around
  `runPlayerClient()`; `player/bot_player.nim` is the bot-enabled variant
  (`{.define: playerBotControl.}`) (`player/player.nim:1-10`, `player/bot_player.nim:1-11`).
- **The submittable bot is King Nimrod, compiled headless** (`-d:noGui -d:release`) — see
  [The submittable image](#the-submittable-image) below.
- **It plays real WoW.** It authenticates to `realmd`, enters the world via `mangosd`, and
  drives a character through genuine movement/combat/quest/loot/death physics — the same
  packet protocol a human's 1.12.1 client (build 5875) speaks.

---

## 1. Connecting: the `/player` handshake

A player connects to a Coworld WebSocket endpoint
(`docs/protocol/player_protocol_spec.md:5-11`):

```
WS /player?slot=<slot>&token=<runner-token>
```

The server validates `slot`/`token`, **idempotently** provisions the VMaNGOS account,
starts the local realm runtime, and sends **exactly one** `wow_session` message
(protocol `vanilla_wow.session.v1`, type `wow_session`,
`docs/protocol/player_protocol_spec.md:13-30`). Every field:

| Field | Example | Meaning |
|---|---|---|
| `protocol` | `"vanilla_wow.session.v1"` | protocol id |
| `type` | `"wow_session"` | message type |
| `slot` | `0` | slot index |
| `player_name` | `"Reference Adventurer"` | player display name |
| `character_name` | `"Nightsun"` **or `null`** | seeded character, or none (see below) |
| `account_id` | `100001` | VMaNGOS account id |
| `account_username` | `"COWORLD"` | account login |
| `account_password` | `"coworld"` | account password |
| `realmd` | `{"host":"coworld-game","port":3724}` | auth/realm-list endpoint |
| `world` | `{"host":"coworld-game","port":8085}` | world/mangosd endpoint hint |
| `realm_name` | `"Coworld Vanilla Docker"` | realm name |
| `client_build` | `5875` | 1.12.1 client build number |
| `deadline_seconds` | `100000.0` | slot wall-clock budget |
| `tower` | `null` or object | dungeon-climb variant payload (see below) |

After that message, the client speaks **normal WoW TCP**: authenticate on
`realmd.host:realmd.port`, then open the world session at the realm address realmd returns
(usually matching the `world` hint) (`player_protocol_spec.md:32-37`).

- **`character_name == null`** means the scenario seeded no character — the player "chooses
  if, when, and how to create or select characters" (`player_protocol_spec.md:39-41`).
- **`tower`** (dungeon-climb variants only) carries `run_id`, `seed`, `floor_count`,
  `active_floor`, `graph_id`, `graph_path`, `world_overlay_path`, `route_goal_id`,
  `reward_policy`; bots load the generated graph from `graph_path`, follow `route_goal_id`,
  and **must not invent coordinates** (`player_protocol_spec.md:68-72`).
- **Finishing:** the player sends a `done` message (`{slot, success, detail}`); the server
  also finishes the slot when `deadline_seconds` is reached, then compares start/end
  character-DB snapshots to write the XP scores (`player_protocol_spec.md:74-89`).

---

## 2. Two network planes + the WebSocket→TCP bridge

The architecture cleanly separates *identity/evidence* from *gameplay*
(`docs/architecture.md:11-43`):

- **Control plane — Coworld FastAPI (HTTP/WebSocket).** Account assignment, player handoff,
  status, telemetry, scoring, replay artifacts. It owns `/client/player`, `/player`,
  `/telemetry/*`, leaderboard, and replay routes. Crucially, **it does *not* proxy live
  gameplay packets** — "it assigns accounts, publishes connection details, collects
  telemetry/results, and exposes evidence surfaces" (`architecture.md:38-40`, `:50-52`).
- **Game plane — VMaNGOS TCP.** `realmd` on TCP **3724** (login/auth/realm list) and
  `mangosd` on TCP **8085** (world packets), backed by MariaDB (`architecture.md:29-35`).
  Desktop `WoW.exe`, WoWee, and packet-level bots may connect directly to these.

**The bridge — `player/tools/wsproxy.nim`.** Both Nim player targets (native and
browser/wasm) do their networking over **WebSocket**, and `wsproxy` forwards the *same
Vanilla packet bytes* to VMaNGOS over TCP for login, realm selection, and gameplay
(`architecture.md:13-17`, `:40-41`). It listens on `127.0.0.1:6932` and forwards to a login
target (default `127.0.0.1:23724`) and a game target (default `127.0.0.1:28085`)
(`player/tools/wsproxy.nim:5-45`). Those local ports (23724/28085) are the host-published
mappings of the in-container 3724/8085 — see `COWORLD_LOCAL_EXTRA_PORTS` in
[the image section](#the-submittable-image).

**Raw-TCP and file-asset modes are rejected by the player build.** `player/config.nims`
raises a compile-time assertion if the old `-d:useTCP` / `-d:useFileAssets` escapes are set
for the `player` project, and forces WebSocket transport + HTTP assets
(`architecture.md:42`, `:105`; `player/config.nims:126-142`). So a player *must* go through
the WS→TCP bridge; it can't shortcut to raw TCP.

---

## 3. What a policy observes

Two observation surfaces, both **client-honest** (they report what the real client knows;
unknowns are marked unknown, never faked).

### (a) `TelemetrySnapshot` / `PlayerStateMirror` — the typed state

A file-backed `state.json` carries the same `TelemetrySnapshot` contract shared by the Nim
player, WoWee, and headless bots (defined in `wow-sdk/wow_sdk/protocol.py`)
(`docs/player-observability.md:71-74`). It is the **authoritative** view of
(`player-observability.md:74-78`; `docs/king-richard-three-lane-prompt.md:91-95`):

- **position** (world XYZ), map/phase, identity
- **vitals**: hp, and the active resource(s) — **mana / rage / energy**
- **xp** and **rested xp**
- **buff/debuff spell ids with durations**
- **in-combat / dead / ghost** flags
- **target**, **active cast**
- **nearby units** (each with position, target, cast, auras)
- party/group state, spells, quests, inventory/equipment, corpse, cooldowns

Companion files: `heartbeat.json` (live fps), and a history ring sampling phase/fps/hp/
position/in-combat/nearby-count/target (`player-observability.md:81`, `:96-99`).

### (b) Tensor Frame v3 — the canonical binary observation

For scripted/learned/LLM consumers, the canonical binary frame is
`vanilla_wow.bot_tensor_frame.v3`, schema `detour-local-graph-v3`
(`docs/bot-tensor-contract.md:3-4`). It is **not** a rendered grid; it is a structured
tensor + a real navigation graph. Key facts:

- **Files:** double-buffered `tensor-frame.0.bin` / `tensor-frame.1.bin` + an atomically
  replaced `tensor-frame.json` manifest. 16-byte little-endian header: ASCII `CWBT`, then
  version `3`, slot, tick. Readers verify header↔manifest agreement before use; GUIDs stay
  split into low/high `uint32` (`bot-tensor-contract.md:12-26`).
- **Fixed self planes:** `self_f32[12]` (pose, vitals, resources, progression, durability,
  inventory, identity, map, class, flags, feature mask) and `self_u32[16]`
  (`bot-tensor-contract.md:28-30`).
- **Fixed entity planes:** `entities_f32[128,8]` (egocentric position, distance, normalized
  hp/power, observation age), `entities_u32[128,17]` (identity, kind, reaction, level, raw
  vitals, map, target slot, provenance, feature mask, group order, flags), and
  `entities_mask[128]` (which rows are populated) (`bot-tensor-contract.md:31-36`).
- **Row layout:** rows **0–39** are stable group slots (ordered by subgroup, normalized
  name, GUID); rows **40–127** are other visible entities, prioritized: current target →
  units targeting the group → hostiles → friendlies → neutrals → objects
  (`bot-tensor-contract.md:38-41`).
- **Variable-length Detour navmesh graph** — nodes are actual walkable **polygons**, edges
  are actual **`dtLink`** adjacency (`bot-tensor-contract.md:42-62`): `nav_nodes_f32[N,4]`
  (centroid XYZ + distance-from-source), `nav_nodes_u32[N,8]` (tile/layer/poly/flags/area/
  predecessor/is-current), `nav_edges_f32[E,7]` (distance + left/right portal XYZ),
  `nav_edges_u32[E,2]` (src/dst node indices), plus `nav_sources_*` for overlapping-floor
  recovery and `nav_node_keys[N]` mapping rows to stable
  `map:tile_x:tile_y:layer:poly_index` identities. Two durable planes retain
  **client-confirmed** movement history reconstructed from `action-results.jsonl` (not from
  planned routes) (`bot-tensor-contract.md:64-73`).
- **The masking rule (critical):** "Unknown facts remain masked; **zero is not silently
  promoted to observed truth**." An unavailable graph has zero rows and a manifest reason —
  consumers must **not** treat that as a walkable empty world
  (`bot-tensor-contract.md:40-41`, `:59-61`; `docs/bot-world-state.md:28`).

---

## 4. What a policy emits

### The action vocabulary — `BotActionKind`

A policy emits **typed actions** (protocol `vanilla_wow.bot_action.v1`). The full
vocabulary (`player/bots/actions.nim:52-96`, wire names `:164-209`):

- **Movement/targeting:** `noop`, `move`, `face`, `target`, `stop_attack`
- **Combat:** `attack`, `cast`, `interrupt_watch`
- **Interaction/economy:** `interact`, `loot`, `use_item`, `sell_junk`, `auto_equip_item`,
  `area_trigger`
- **Progression:** `accept_quest`, `turn_in_quest`, `train_spell`, `learn_talent`
- **Death recovery:** `release_spirit`, `reclaim_corpse`, `spirit_healer_resurrect`
- **Grouping:** `invite_party`, `accept_party`, `follow`, `assist`
- **Social/chat:** `chat_say`, `chat_yell`, `chat_whisper`, `chat_emote`, `who_query`,
  `add_friend`, `remove_friend`
- **Channels:** `join_channel`, `leave_channel`, `channel_say`
- **Guild:** `guild_invite`, `guild_accept`, `guild_motd`, `buy_guild_charter`,
  `sign_guild_charter`, `offer_guild_charter`, `turn_in_guild_charter`
- **Travel:** `take_taxi`
- plus `unsupported` (sentinel)

Every kind maps to a real stock UI command via `BotActionStockSources`
(`actions.nim:214-423`) — e.g. `move`→a movement binding, `cast`→`CastSpell`,
`take_taxi`→`TakeTaxiNode`. This anchors each action to something a human client could do,
not a synthetic capability.

**Wire encoding.** The action vector is a **64-byte v1 record: twelve `u32` values then
four `f32` values** (`docs/bot-tensor-contract.md:82-83`); the kind is a `uint8` code
(`bakUnsupported` = 255) (`actions.nim:588-596`). **Text-bearing actions** (chat, whisper,
guild/channel names, target names) travel over a **JSON path** — `vanilla_wow.bot_action.v1`,
type `action`, with `request_id`/`kind`/`args` (`bot-tensor-contract.md:83-84`;
`actions.nim:759-862`). The `tools/bot_control.nim` data plane also accepts shared option
ids like `target:<guid>`, `attack:<guid>`, `cast:<spell_id>:<guid>`, `loot:<guid>`,
`use_item:<bag>:<slot>`, `release_spirit`, `reclaim_corpse`, `move:corpse`
(`player/readme.md:308-311`).

### Typed action results — "sent is not accepted"

This is the core integrity rule of the whole engine, and it distinguishes a *legal* WoW bot
from a cheating one:

> A policy **reads snapshots and returns intent.** It never mutates client state, sends
> packets itself, drains client actions, writes action results, or marks a request
> successful — "canonical truth changes only through the normal client/server event"
> (`player/bots/README.md:19-22`). "A bot… cannot fabricate canonical client state or treat
> a dispatched request as server confirmation" (`player/readme.md:265-267`).

So the loop is strictly: **read a snapshot → queue one typed action → wait for the settled
authoritative result → repeat.** Every cast, item use, attack, movement, interaction,
invite, loot, reclaim, or boss transition must be confirmed by `action-results.jsonl`, a
typed mirrored state transition, or both — **"'action selected' is not success"**
(`docs/king-richard-three-lane-prompt.md:80-82`).

**Movement gets its own typed settlement.** A `move` returns a
`vanilla_wow.movement_settlement.v1` `MovementSettlement` whose `kind` is one of:
`not_applicable`, `reached_target`, `advanced_corridor`, `combat_interrupted`,
`blocked_edge`, `environmental_hazard`, `off_corridor`, `projection_failed`, `no_progress`,
`world_transition_required` — plus source/settled/target polygon keys, displacement, and
hazard/interruption detail (`actions.nim:15`, `:27-51`; `bot-tensor-contract.md:94-96`).
Move results also emit a `vanilla_wow.navmesh_traversal.v1` for the confirmed route prefix.
**Policies update navigation memory from the typed settlement, never by parsing
human-readable result text** (`bot-tensor-contract.md:88-99`).

---

## 5. The submittable image

The player Docker image is a **two-stage build** (`player/Dockerfile`):

1. **Stage 1 (`king-nimrod-builder`, `python:3.12-slim`)** — installs the Nimby `0.1.27` /
   Nim `2.2.6` toolchain, copies `player/{config.nims,bots,game_client,king_nimrod}` +
   `nimby.lock`, and compiles **headless King Nimrod**:
   ```
   nim c --parallelBuild:8 -d:release -d:noGui --path:/opt/coworld-player \
         -o:/usr/local/bin/king_nimrod king_nimrod.nim
   ```
   (`player/Dockerfile:1-33`).
2. **Stage 2 (`python:3.12-slim`)** — installs `libgl1`/`libx11-6`, copies the compiled
   `king_nimrod` binary from stage 1, `pip install .`s the Python package, and sets
   `CMD ["python3", "-m", "vanilla_wow_coworld.player"]` (`player/Dockerfile:35-48`).

So the image = **the Python `/player` handoff service (`vanilla_wow_coworld.player`) + the
compiled Nim King Nimrod bot binary** side by side. King Nimrod supports `--mode=follow` and
`--mode=farm` (`player/readme.md:252-257`; `player/king_nimrod/README.md:1-16`).

**Manifest wiring** (`coworld_manifest_template.json`):
- The `game` runnable (`name: vanilla_wow`) publishes VMaNGOS TCP to host ports via
  `COWORLD_LOCAL_EXTRA_PORTS: "3724:23724,8085:28085,3306:3307"` — realmd 3724→23724,
  mangosd 8085→28085, MariaDB 3306→3307 (matching the wsproxy defaults)
  (`coworld_manifest_template.json:2-27`, esp. `:10`; `docs/architecture.md:70-72`).
- The `player` entry `manual-wow-player` ("Nim Player Handoff", image
  `{{COWORLD_PLAYER_IMAGE}}`) is the bundled reference player that prints the account
  handoff and keeps the session alive (`coworld_manifest_template.json:425-437`).
- The five RFC support roles (commissioner/grader/diagnoser/optimizer) ship in a separate
  `{{COWORLD_SUPPORTING_IMAGE}}`; the reporter is a checked-in Rust/Wasm component. See
  [`vanilla-wow-rfc-roles.md`](vanilla-wow-rfc-roles.md).

> **Where this differs from the other labs.** In crewrift/heartleaf/cue-n-woo, a "player"
> is a Python package that imports `players.player_sdk` and speaks a sprite/text protocol,
> and the image is a thin Python build. Here the *player logic is compiled Nim* and the
> Python layer is just the handoff/session service. Any player we build in this lab will
> need a Nim build path (and, if it forks the bundled engine, a pinned game commit — the
> `versions.env` pattern from `crewrift_lab/tools/`). We add that only when a first policy
> is chosen; see [`../AGENTS.md`](../AGENTS.md#player-build-paths).

---

## 6. Client-honesty constraints (the non-negotiables)

Every player in this game must obey these — they are what makes a run *legitimate WoW play*
rather than a simulation or an exploit (`docs/king-richard-three-lane-prompt.md:69-86`;
`player/bots/README.md:19-22`; `docs/architecture.md:116-117`):

- **All gameplay through the real client and normal movement.** No Shift fast-travel, no
  direct coordinate assignment, no packet injection/interception, no optimistic synthetic
  state, no disabled collision, no database intervention.
- **DB seeding is allowed only while a fixture character is logged out**, and only to
  create the declared *starting* fixture. After login, **never** repair health, mana,
  death, corpse, position, inventory, equipment, spells, party state, boss state, or
  progress through the DB. On the hosted persistent character, never seed or query the DB —
  observe only through the real client-state ladder.
- **"Action selected" is not success.** Every action is confirmed by `action-results.jsonl`
  and/or a typed mirrored state transition; a boss kill is certified by client-observed
  death/disappearance + the typed boss record, not by a DB row or a position change.
- **The evidence ladder** (highest first): the typed `player_state_mirror` (`state.json`),
  then `action.json` + `action-results.jsonl`, then run-level metrics/heartbeat, then
  `observe_player.py`, and read-only DB only after fixtures are offline (never for the
  hosted character). On disagreement between sources, **stop the claim and fix provenance**
  rather than pick the convenient value (`king-richard-three-lane-prompt.md:88-108`).
