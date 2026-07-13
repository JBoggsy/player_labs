# Vanilla WoW — interface-protocol reference

**The exhaustive, field-level specification of the interface between the Vanilla WoW Coworld
game and its players.** This is the *reference* doc: every message family, every schema, the
transport, the binary tensor/action/replay formats, and the end-to-end sequence — with
verbatim field names and `file:line` citations into the game repo.

Where [`vanilla-wow-player-contract.md`](vanilla-wow-player-contract.md) is the **narrative**
"how to think about being a player" (and the right place to start), this doc is the **spec**
you consult when you need the exact field, type, byte offset, or opcode. When the two differ
in detail, **this doc is authoritative** and the source it cites is the ground truth.

> **Two protocol stacks, one game.** A Vanilla WoW player speaks *two* layered protocols:
> 1. **The Coworld session/handoff + observation/action protocols** (`vanilla_wow.*` messages,
>    the `TelemetrySnapshot`, the `BotAction`) — defined *by this game* and specified here.
> 2. **The real World of Warcraft 1.12.1 binary TCP protocol** (realmd auth + mangosd world
>    packets) — defined by Blizzard/VMaNGOS, spoken over a WebSocket→TCP bridge. This doc
>    specifies the *bridge and the handshake into it*, and names the key WoW opcodes, but the
>    WoW wire format itself is VMaNGOS's, not ours.

Citations are `file:line` into `~/coding/coworlds/coworld-vanilla-wow` (read 2026-07-13). The
authoritative Python schema source is `src/wow_sdk/protocol.py`; the Nim mirrors are in
`player/bots/actions.nim`, `player/bots/tensor_frame.nim`, and `player/game_client/navmeshes.nim`.

---

## 0. Protocol IDs — the master list

Every structured message carries a `protocol` string. The complete set
(`src/wow_sdk/protocol.py:9-27`, plus the binary/format ids):

| Protocol id | Purpose | Defined |
|---|---|---|
| `vanilla_wow.session.v1` | Session handoff (`wow_session`) + `done` | `docs/protocol/player_protocol_spec.md` |
| `vanilla_wow.bot_action.v1` | Player→game typed action envelope | `protocol.py:15`, `actions.nim:13` |
| `vanilla_wow.movement_settlement.v1` | Typed result of a `move` action | `protocol.py:1042`, `actions.nim:15` |
| `vanilla_wow.navmesh_traversal.v1` | Confirmed route-prefix evidence for a move | `protocol.py:986`, `navmeshes.nim:1043` |
| `vanilla_wow.control_adapter_report.v1` | Maps an action to its stock UI source | `protocol.py:27`, `actions.nim:14` |
| `vanilla_wow.bot_tensor_frame.v3` | Canonical binary observation (schema `detour-local-graph-v3`) | `tensor_frame.nim:9`; `bot-tensor-contract.md:2-3` |
| `vanilla_wow.replay.v4` | Replay artifact header | `docs/protocol/cwreplay.md` |
| `vanilla_wow.llm_harness.v1` | LLM decision-context payload | `protocol.py:9` |
| `vanilla_wow.llm_sdk_state.v1` | LLM SDK state payload | `protocol.py:12` |
| `vanilla_wow.social_protocol.v1` / `.social_intent.v1` / `.social_utterance.v1` | Social/chat layers | `protocol.py:18-24` |

Useful module constants (`protocol.py:30-51`): `MOVE_ARRIVAL_DISTANCE = 3.0`,
`ROUTE_GOAL_ARRIVAL_DISTANCE = 5.0`, `MOVE_PROGRESS_EPSILON = 1.0`,
`MAX_PROACTIVE_ENEMY_LEVEL_DELTA = 3`, `HALLWAY_SEGMENT_ROUTE_THRESHOLD = 5.0`,
`DEFAULT_BEDROCK_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"`.

All Pydantic models use `ConfigDict(extra="forbid")` — **unknown fields are rejected**, so the
schemas below are exhaustive, not illustrative.

---

## 1. Session handoff — `vanilla_wow.session.v1`

Source: `docs/protocol/player_protocol_spec.md`.

### Connect

```
WS /player?slot=<slot>&token=<runner-token>
```

The server validates `slot`/`token`, idempotently creates the VMaNGOS account, seeds the
character (if the scenario specifies one), starts the realm runtime, and sends **exactly one**
`wow_session` message (`player_protocol_spec.md:1-11`).

### `wow_session` (verbatim, `player_protocol_spec.md:13-30`)

```json
{
  "protocol": "vanilla_wow.session.v1",
  "type": "wow_session",
  "slot": 0,
  "player_name": "Reference Adventurer",
  "character_name": "Nightsun",
  "account_id": 100001,
  "account_username": "COWORLD",
  "account_password": "coworld",
  "realmd": {"host": "coworld-game", "port": 3724},
  "world": {"host": "coworld-game", "port": 8085},
  "realm_name": "Coworld Vanilla Docker",
  "client_build": 5875,
  "deadline_seconds": 100000.0,
  "tower": null
}
```

| Field | Type | Meaning |
|---|---|---|
| `protocol` | str | `"vanilla_wow.session.v1"` |
| `type` | str | `"wow_session"` |
| `slot` | int | slot index |
| `player_name` | str | player display name |
| `character_name` | str \| **null** | seeded character; **null ⇒ no character seeded — the bot chooses if/when/how to create or select** (`:39-41`) |
| `account_id` | int | VMaNGOS account id |
| `account_username` | str | account login |
| `account_password` | str | account password |
| `realmd` | `{host, port}` | auth endpoint; the client authenticates here |
| `world` | `{host, port}` | world endpoint *hint* — the real world address is what realmd returns (`:32-37`) |
| `realm_name` | str | realm name |
| `client_build` | int | `5875` (1.12.1) |
| `deadline_seconds` | float | slot wall-clock budget |
| `tower` | object \| null | dungeon-climb payload (below) |

When raw TCP can't be published, the message also advertises a **`tcp_proxies`** field routing
each service through the WS byte tunnel (see [§6](#6-transport--the-websockettcp-bridge)).

### `tower` sub-object (dungeon-climb variants, `:68-72`)

Present (non-null) only for generated tower/dungeon-climb runs. Fields: `run_id`, `seed`,
`floor_count`, `active_floor`, `graph_id`, `graph_path`, `world_overlay_path`, `route_goal_id`,
`reward_policy`. The bot loads the generated graph from `graph_path`, follows `route_goal_id`,
and must not invent coordinates.

### `done` (verbatim, `:76-84`)

```json
{
  "protocol": "vanilla_wow.session.v1",
  "type": "done",
  "slot": 0,
  "success": true,
  "detail": "created and entered character"
}
```

Fields: `protocol`, `type:"done"`, `slot:int`, `success:bool`, `detail:str`. The server also
finishes the slot when `deadline_seconds` is reached, then scores from start/end character-DB
snapshots (`:86-89`).

### `/client/player` handoff variants

- `GET /client/player?slot=&token=` — human-readable text handoff: account, endpoints, launch
  guidance, and WoW.exe `realmlist.wtf` values (`:47-49`, `:64-66`).
- `GET /client/player?slot=&token=&format=browser` — the **browser bridge console**; the page
  connects to `WS /client/player/ws` and drives the character through the telemetry bridge
  (`:51-62`):
  - `POST /telemetry/snapshot`
  - `GET /telemetry/actions/{slot}?after=<sequence>`
  - `POST /telemetry/action-results`
  - `GET /telemetry/action-results/{slot}?after=<sequence>`

---

## 2. Observation — `TelemetrySnapshot`

The authoritative observation container (`src/wow_sdk/protocol.py:859-908`). It is reduced from
the Nim `PlayerStateMirror` and projected to policies via `.to_observation()` →
`ObservationMessage` (`:887`, `:922-938`). **Every field, top level:**

| Field | Type | Note |
|---|---|---|
| `slot` | int (≥0) | |
| `tick` | int (≥0) | |
| `character` | `CharacterSnapshot` | required (below) |
| `nearby_units` | `list[NearbyUnit]` | visible units |
| `nearby_objects` | `list[NearbyObject]` | game objects |
| `objectives` | `list[QuestObjectiveSnapshot \| ObjectiveState]` | current objectives |
| `quest_log` | `list[QuestLogEntry]` | |
| `rewarded_quest_ids` | `list[int]` | |
| `economy` | `EconomySnapshot \| None` | money truth |
| `resources` | `PlayerResources` | mana/rage/energy/combo/shards |
| `auras` | `PlayerAuras` | self buffs/debuffs |
| `honor` | `HonorSnapshot \| None` | PvP honor tree |
| `spells` | `list[KnownSpell]` | known spells + ranges/costs |
| `trainer` | `TrainerSnapshot \| None` | trainer offers when at a trainer |
| `inventory_items` | `list[InventoryItemSnapshot]` | |
| `inventory_summary` | `InventorySummary \| None` | bag/durability/repair-cost rollup |
| `planner` | `PlannerStatus \| None` | King Richard planner state |
| `party` | `PartySnapshot` | group members |
| `chat_inbox` | `list[ChatInboxEntry]` | |
| `friends` | `list[FriendStatusEntry]` | |
| `last_who_results` | `WhoResultsSnapshot` | |
| `guild` | `GuildSnapshotState` | |
| `petition` | `PetitionSnapshotState` | guild-charter petition |
| `stuck` | `StuckSnapshot \| None` | stuck detection verdict |

### `CharacterSnapshot` (`:166-195`) — the self

`guid:str|None`, `name:str`, `class_name:str|None`, `level:int (1..60)`, `xp:int`,
`next_level_xp:int`, `rested_xp:int`, `map_id:int`, `zone:str`, `x/y/z:float`,
`orientation:float`, `health:int (≥0)`, `max_health:int (>0)`, `target:str|None`,
`in_combat:bool`, `is_casting:bool|None`, `is_channeling:bool|None`, `is_dead:bool|None`,
`is_ghost:bool|None`, `death_state_known:bool`, `can_reclaim_corpse:bool|None`,
`corpse_position:WorldPoint|None`, `corpse_map_id:int|None`, `corpse_distance:float|None`,
`corpse_reclaim_delay_seconds:float|None`.

### `NearbyUnit` (`:198-233`) — each visible unit

`guid:str`, `entry_id:int|None`, `display_id:int|None`, `name:str`,
`unit_kind:"creature"|"npc"|"player"|None`,
`observation_source:"world_object"|"party_frame"|"world_object+party_frame"|None`,
`observed_at_s:float|None`, `distance:float (≥0)`, `position:WorldPoint|None`,
`line_of_sight:bool|None`, `target:str|None`, `level:int|None`, `creature_type:str|None`,
`creature_rank:str|None`, `is_casting:bool|None`, `is_channeling:bool|None`,
`tapped_by_other:bool|None`, `not_attackable:bool|None`, `player_can_attack:bool|None`,
`player_controlled:bool|None`, `is_dead:bool|None`, `is_lootable:bool|None`,
`dynamic_flags:int|None`, `npc_flags:int|None`, `is_questgiver:bool|None`,
`buffs:list[AuraSummary]`, `debuffs:list[AuraSummary]`,
**`reaction:"friendly"|"neutral"|"hostile"` (required)**, `reaction_known:bool|None`,
`health:int (≥0)`, `max_health:int (>0)`.

> Note the `reaction` vs `not_attackable`/`player_can_attack` split — reaction color is
> *separate* from attackability (see the spell-lab discussion in
> [`vanilla-wow-gameplay.md`](vanilla-wow-gameplay.md#combat-briefly)).

### Other nested types (field lists in `protocol.py`)

- **`WorldPoint`** `:151-163` — `map_id, x, y, z, orientation`; `distance_to()` returns `inf`
  across map_ids.
- **`NearbyObject`** `:236-247` — `guid, entry_id, display_id, name, observation_source,
  observed_at_s, distance, position, object_type`.
- **`AuraSummary`** `:342-356` — `name, spell_id, slot, applications` (name may be empty; the
  Nim mirror knows only spell id/slot).
- **`PlayerResources`** `:325-339` — `mana, max_mana, rage, energy, combo_points,
  money_copper, active_aspect_spell_id, shard_count, active_power_known, active_power_type,
  active_power, active_max_power`.
- **`ObjectiveState`** `:250-265` — the semantic objective: `id, description, complete,
  progress, goal, quest_id, objective_kind ("kill"|"loot"|"object"|"event"|"explore"|
  "unknown"), target_names, target_entries, object_entries, item_entries, source,
  route_goal_id`.
- **`QuestObjectiveSnapshot`** `:268-322` (client truth) — `quest_id, entry, item_id, current,
  required, complete, failed, timer_failed, requirement_known, requirement_index, text`.
- **`QuestLogEntry`** `:410-419`, **`KnownSpell`** `:366-383`, **`TrainerSnapshot` /
  `TrainerSpellOffer`** `:386-407`, **`InventorySummary`** `:422-450`,
  **`InventoryItemSnapshot`** `:453-479`, **`EconomySnapshot`** `:482-488`, **`PlannerStatus`**
  `:491-523`, **`PartySnapshot` / `PartyMemberSnapshot`** `:526-557`, **`StuckSnapshot`**
  `:744-758`, chat/friends/who/guild/petition `:646-741`, the honor sub-tree `:761-856`.

There is no Python class literally named `PlayerStateMirror`; `TelemetrySnapshot` **is** the
canonical mirror (the Nim `PlayerStateMirror` is its source, reduced by
`player/bots/adapters/player_leveling.nim`, per `docs/architecture.md:136-140`).

---

## 3. Action — `vanilla_wow.bot_action.v1`

Source: `player/bots/actions.nim`; Python mirror `protocol.py:941-948`.

### The JSON action envelope (`actions.nim:759-765`)

```json
{ "protocol": "vanilla_wow.bot_action.v1", "type": "action",
  "request_id": "<id>", "kind": "<action-kind>", "args": { ... } }
```

`request_id:str`, `kind:AllowedBotAction`, `args:dict`. `AllowedBotAction` is the wire-name
Literal (`protocol.py:54-99`).

### The action vocabulary — `BotActionKind` → wire name

Full set (`actions.nim:52-96`, names `:164-209`): `noop`, `move`, `face`, `target`, `attack`,
`interact`, `loot`, `cast`, `train_spell`, `use_item`, `release_spirit`, `reclaim_corpse`,
`area_trigger`, `sell_junk`, `accept_quest`, `turn_in_quest`, `invite_party`, `accept_party`,
`follow`, `assist`, `chat_say`, `chat_yell`, `chat_whisper`, `chat_emote`, `join_channel`,
`leave_channel`, `channel_say`, `add_friend`, `remove_friend`, `who_query`, `guild_invite`,
`guild_accept`, `guild_motd`, `take_taxi`, `interrupt_watch`, `learn_talent`,
`buy_guild_charter`, `sign_guild_charter`, `offer_guild_charter`, `turn_in_guild_charter`,
`spirit_healer_resurrect`, `auto_equip_item`, `stop_attack`, `unsupported`.

Code mapping (`:588-596`): `botActionKindCode` returns `255` for `unsupported`, else the enum
ordinal; `botActionKindFromName` falls back to `unsupported`.

### Per-kind `args` (`botActionArgsJson`, `:767-862`)

Emitted only when the field is set. Common: `target_guid` (string), `spell_id` (int),
`item_guid` (string), `quest_id` (int), `trainer_guid` (string). Per-kind:

| Kind(s) | `args` keys |
|---|---|
| `chat_say/yell/emote`, `who_query`, `guild_motd` | `text` |
| `chat_whisper` | `text`, `target_name` |
| `join_channel`/`leave_channel`/`add_friend`/`remove_friend`/`guild_invite` | `text` |
| `channel_say` | `text`, `target_name` |
| `interrupt_watch` | `target_entry`, `interrupt_spell_id` |
| `learn_talent` | `talent_id`, `talent_rank` |
| `buy_guild_charter` | `guild_name`, `text`, `target_name` |
| `offer_guild_charter` | `target_name`, `text` |
| `turn_in_quest` | `quest_reward_choice` |
| `use_item` | `bag`, `slot` |
| `take_taxi` | `taxi_node_id` |
| (has destination) | `destination:{map_id,x,y,z}`, optional `target_z_known:false`, `source_projection_recovery:true`, `arrival_radius` |
| (movement extras) | `water_column_move`, `move_step_limit`, `route_goal:{…}`, `route_label`, `route_leg_label`, `route_node_id`, `orientation`, `jump`, `jump_xy_speed` |
| (else) | `target_name` |

The inbound parser `botActionFromJson` (`:628-722`) accepts many aliases (e.g. `message`→`text`,
`name`/`channel_name`→`target_name`, `spell`→`spell_id`, `rank`→`talent_rank`,
`target`/`target_guid`→target). The full typed `BotAction` record is at `actions.nim:98-149`.

### The 64-byte binary action record (12×u32 + 4×f32)

Defined in `player/bots/tensor_frame.nim` (`ActionVectorByteLength = 64`, `:30`);
encode `:1188-1236`, decode `:1238-1272`. Little-endian:

| Slot | Offset | Type | Meaning |
|---|---|---|---|
| 0 | 0 | u32 | opcode = `botActionKindCode(kind)` (255 = unsupported) |
| 1 | 4 | u32 | flags — bit0 `HasTarget` (=1), bit1 `HasPoint` (=2) (`:31-32`) |
| 2 | 8 | u32 | target GUID low (if HasTarget) |
| 3 | 12 | u32 | target GUID high (if HasTarget) |
| 4 | 16 | u32 | `spellId` |
| 5 | 20 | u32 | `questId` |
| 6 | 24 | u32 | `talentId` |
| 7 | 28 | u32 | `talentRank` |
| 8 | 32 | u32 | `bag` |
| 9 | 36 | u32 | `slot` |
| 10 | 40 | u32 | `taxiNodeId` |
| 11 | 44 | u32 | reserved (always `0`) |
| f0 | 48 | f32 | destination `x` |
| f1 | 52 | f32 | destination `y` |
| f2 | 56 | f32 | destination `z` |
| f3 | 60 | f32 | `orientation` (falls back to `destination.o`) |

Text-only kinds zero the target/numeric/point slots and carry their text over the JSON path
(`:1189-1193`; `bot-tensor-contract.md:83-84`). On decode, `train_spell` copies the target GUID
into `trainerGuid` (`:1257-1258`). GUIDs split into low/high u32 via
`splitEngineGuid`/`joinEngineGuid`.

---

## 4. Action results — movement settlement & navmesh traversal

Every `move` result is *typed*; policies classify movement **only** from these, never by
parsing human-readable text (`bot-tensor-contract.md:97-99`). The outcome bundle
`BotActionOutcome` (`actions.nim:151-155`) carries `success`, `message`, `navmeshTraversal`, and
`movementSettlement`.

### `vanilla_wow.movement_settlement.v1`

**Kinds** (`actions.nim:27-37`, names `:434-445`): `not_applicable`, `reached_target`,
`advanced_corridor`, `combat_interrupted`, `blocked_edge`, `environmental_hazard`,
`off_corridor`, `projection_failed`, `no_progress`, `world_transition_required`. The Python
Literal (`protocol.py:1024-1034`) lists the 9 real kinds (dropping `not_applicable`).

**Record** (`actions.nim:39-51`; Python `:1037-1062`): `protocol`, `kind`, `source_poly_key`,
`settled_poly_key`, `target_poly_key`, `attempted_source_poly_key`, `attempted_target_poly_key`,
`continuation_required:bool`, `displacement_yards:float (≥0)`, `interruption_guid:str|None`,
`environmental_damage_type:int (0..255)`. Validators: an attempted edge needs both keys or
neither; `combat_interrupted` needs an interruption guid or nonzero displacement;
`environmental_hazard` needs a nonzero damage type.

> **Intentional asymmetry to know:** the "successful" set differs between languages — Python
> `SUCCESSFUL_MOVEMENT_SETTLEMENT_KINDS` = {`reached_target`, `advanced_corridor`,
> `combat_interrupted`} (`protocol.py:1065-1067`), while the Nim "use last confirmed edge" set
> adds `environmental_hazard` (`actions.nim:537-540`).

### `vanilla_wow.navmesh_traversal.v1`

The confirmed route-*prefix* through the settled polygon (`protocol.py:983-1021`;
`navmeshes.nim:109-114`): `protocol`, `status`
(`"confirmed_prefix"|"settled_off_route"|"projection_unavailable"|"unavailable"`), `map_id`,
`source_poly_key`, `settled_poly_key`, `visited_poly_keys:list[str]`,
`traversed_edges:list[{source,target}]`, `message`. Validators: every poly key must start with
`"{map_id}:"`; `source_poly_key` == first visited; a confirmed prefix ends at the settled poly
with ordered edges; an unconfirmed status may not declare edges.

### `vanilla_wow.control_adapter_report.v1`

Maps a queued action to the **stock UI/binding source** that a human client would use — the
mechanism behind "every action anchors to something a human could do"
(`protocol.py:1166-1174`; Nim builders `actions.nim:864-984`). Fields: `protocol`, `lane_id`,
`feature_label`, `stock_source:{kind,name,detail}`, `selected_action:{option_id, selector,
rationale, kind, args}`, `runtime_transition:{backend, runtime_dir, state_file, action_file,
result_file, state_slot, state_tick, queued, sequence, request_id, action_kind}`. The per-kind
stock-source table is `BotActionStockSources` (`actions.nim:214-423`) — e.g. `move`→a movement
binding, `cast`→`CastSpell`, `chat_say`→`SendChatMessage(...,"SAY")`,
`buy_guild_charter`→`CMSG_PETITION_BUY`.

---

## 5. Observation (binary) — `vanilla_wow.bot_tensor_frame.v3`

The canonical binary observation for scripted/learned consumers; schema `detour-local-graph-v3`
(`docs/bot-tensor-contract.md:2-3`). It is **not** a rendered grid — it is fixed
self/entity planes + a variable-length local Detour navmesh graph.

### Files & the `CWBT` header (`:12-19`; `tensor_frame.nim:9-11`)

Each slot writes double-buffered `tensor-frame.0.bin` / `tensor-frame.1.bin` and an atomically
replaced `tensor-frame.json` manifest. **16-byte little-endian header:** ASCII `CWBT` · version
`3` (u32) · slot (u32) · tick (u32). Readers verify header↔manifest agreement; a mismatch
rejects that generation; an inactive buffer is never decoded under the active manifest.

### Fixed planes (`:28-40`)

- `self_f32[12]`, `self_u32[16]` — pose, vitals, resources, progression, durability, inventory,
  identity, map, class, flags, and the self known-feature mask (bits in `tensor_frame.nim:64-74`:
  Identity, Position, Health, Power, TargetDistance, Experience, Durability, CorpseDistance,
  BagSpace, Money, RestedExperience).
- `entities_f32[128,8]` — egocentric position, distance, normalized health/power, observation
  age.
- `entities_u32[128,17]` — identity, kind, reaction, level, raw vitals, map, target slot,
  provenance, known-feature mask, group order, flags.
- `entities_mask[128]` — populated-row mask.
- **Row layout:** rows 0–39 stable group slots (subgroup, normalized name, GUID); rows 40–127
  other visible entities prioritized current target → units targeting the group → hostiles →
  friendlies → neutrals → objects.

### Detour graph planes (`:42-79`) — nodes = polygons, edges = `dtLink` adjacency

- `nav_nodes_f32[N,4]` — centroid `x,y,z`, `distance_from_source`.
- `nav_nodes_u32[N,8]` — `tile_x, tile_y, layer, poly_index, flags, area, predecessor_index,
  is_current`.
- `nav_edges_f32[E,7]` — `distance`, left portal `xyz`, right portal `xyz`.
- `nav_edges_u32[E,2]` — source, destination node index.
- `nav_sources_f32[P,4]` / `nav_sources_u32[P,2]` — alternate projected source (+ projection
  distance) and its node index / selected-excluded flags (overlapping-floor recovery).
- `nav_node_keys[N]` (manifest) — stable `map:tile_x:tile_y:layer:poly_index` identity per row.
- `nav_history_nodes_u32[H,3]` / `nav_history_edges_u32[T,5]` — durable **client-confirmed**
  movement history (visit/traversal counts + first/last action sequence), reconstructed from
  `action-results.jsonl`, not from planned routes.

### The masking rule (critical, `:40`, `:59-62`)

**"Unknown facts remain masked; zero is not silently promoted to observed truth."** An
unavailable graph has zero rows and a manifest reason — consumers must **not** treat it as a
walkable empty world.

---

## 6. Transport — the WebSocket↔TCP bridge

Sources: `docs/coworld-extra-tcp-ports.md`, `coworld_extra_tcp_ports_contract.json`,
`player/tools/wsproxy.nim`, `docs/architecture.md`.

### The two planes

- **Control plane** (Coworld FastAPI, HTTP/WS) — account assignment, `/client/player`,
  `/player`, `/telemetry/*`, leaderboard, replay. **Does not proxy gameplay packets**
  (`architecture.md:38-40`).
- **Game plane** (VMaNGOS TCP) — realmd **3724** (login/auth/realm list), mangosd **8085**
  (world), MariaDB **3306** (`architecture.md:29-35`).

### Port publishing

`COWORLD_LOCAL_EXTRA_PORTS` is a comma-separated `container_port:host_port` list. Canonical
value (`coworld_manifest_template.json:10`; `architecture.md:71-72`; `README.md:319`):

```
COWORLD_LOCAL_EXTRA_PORTS = "3724:23724,8085:28085,3306:3307"
```

→ realmd `3724→23724`, mangosd `8085→28085`, MariaDB `3306→3307`. The
`coworld_extra_tcp_ports_contract.json` (`game_id: "vanilla_wow"`, `status:
"platform_required"`) declares the two required extra TCP ports (`vmangos-realmd`,
`vmangos-world`) with `public_host_env`/`public_port_env` = `VMANGOS_PUBLIC_REALMD_HOST/PORT`
and `VMANGOS_PUBLIC_WORLD_HOST/PORT`, defaults 3724/8085; the runner injects those and the game
reads them to build the session handoff.

### `wsproxy.nim` (native + browser transport)

Defaults (`player/tools/wsproxy.nim:5-17`): listen `127.0.0.1:6932`, login target
`127.0.0.1:23724`, game target `127.0.0.1:28085`, `MaxWsMessageBytes = 16 MiB`,
`LogonProofBytes = 75`. Browsers connect to one endpoint `ws://HOST:PORT/`; each binary WS
message is routed to login or game — **by upgrade path** (`/login|/realmd|/realm`→login;
`/game|/world`→game; `:318-327`) or **by packet shape** (`looksLikeWorldPacket` /
`looksLikeRealmPacket` sniffing; `:281-316`). Client→server: WS payload unwrapped and written
raw to the upstream TCP socket; server→client: raw TCP bytes wrapped in a single **unmasked
Binary WS frame** (`:493-633`). Upstream TCP opens lazily; EOF closes the client with a Close
frame.

### The WS byte tunnel (when raw TCP can't be published, `coworld-extra-tcp-ports.md:68-92`)

```
GET /tcp
WS  /tcp/realmd?slot=<slot>&token=<token>   → VMANGOS_REALMD_HOST/PORT (default 127.0.0.1:3724)
WS  /tcp/world?slot=<slot>&token=<token>    → VMANGOS_WORLD_HOST/PORT  (default 127.0.0.1:8085)
```

Overridable via `COWORLD_TCP_PROXY_{REALMD,WORLD}_{HOST,PORT}`. The `/player` session message
advertises these as `tcp_proxies`; `vanilla-wow-reference-player` exposes local TCP listeners
from them and rewrites the realmd realm-list world address to the local world listener.

> **Enforced constraint:** the Nim *player* build rejects raw-TCP and file-asset modes at
> compile time (`player/config.nims:126-142`) — a player must use the WS transport.

---

## 7. Replay — `CWREPLAY` / `vanilla_wow.replay.v4`

Source: `docs/protocol/cwreplay.md`. VMaNGOS is authoritative; v4 records the *decrypted world
protocol at the VMaNGOS session boundary* and puppets the Nim player packet path with one
recorded character's server stream (`:11-14`).

### Binary layout (`:16-29`) — unsigned little-endian; strings = `u16` length + UTF-8

| Field | Encoding | Contract |
|---|---|---|
| Magic | 8 bytes | ASCII `CWREPLAY` |
| Format version | u16 | `1` |
| Game | string | `vanilla_wow_local` |
| Game version | string | `0.1.4` |
| Start time | u64 | Unix ms (`0` when no RFC session) |
| Header length | u32 | JSON byte count |
| Header | bytes | Typed replay-artifact JSON |
| Records | until EOF | Typed binary records |

**Header JSON** (`:31-36`): `protocol=vanilla_wow.replay.v4`, game/version, scope,
scenario/session identity, complete sanitized effective config, lifecycle events, stream
descriptors, and episode results when scored.

### Records

- **`0x02` — canonical party world packets** (mandatory, `:37-56`): payload is `CWPARTY4` =
  instance identity + intact VMaNGOS PKT 2.1 segments per character GUID/POV (each retaining
  direction, Unix time, server time, opcode, post-auth body; outbound captured
  pre-encryption, inbound post-decryption). Playback feeds **one** POV's server→client packets
  through the normal reducer stack; client→server kept for audit, never replayed.
- **`0x01` — RFC camera/boundary sidecar** (`:58-72`): zlib-compressed JSONL (raw size,
  compressed size, SHA-256, payload) for the first-entry/all-left boundary + optional
  party-centroid camera. Not gameplay truth.

Truncation, decompression errors, byte-count or digest mismatch, and unknown/duplicate record
types are **fatal**. Readers accept only `vanilla_wow.replay.v4`; every replay requires a
`0x02`; RFC writers also emit `0x01` (`:74-98`). Files: clean `.cwreplay`, interrupted
`.truncated.cwreplay`. Coworld lifecycle env: `COGAME_SAVE_REPLAY_URI` / `COGAME_LOAD_REPLAY_URI`,
served via `/client/replay` and `/replay` (`:146-158`). v4 stores no structured bot-policy
record — a bot's rationale is visible only if it sent a real `/say` chat message (`:159-164`).

---

## 8. The end-to-end sequence

Assembled from `docs/architecture.md` and `docs/protocol/player_protocol_spec.md`:

1. **WS connect** — `WS /player?slot=&token=` through `wsproxy` (native + browser).
2. **Validation + provisioning** — server validates slot/token, idempotently creates the
   VMaNGOS account, seeds the character if specified, starts the realm runtime.
3. **Session message** — server sends one `vanilla_wow.session.v1` `wow_session` (credentials,
   `realmd`/`world`, `deadline_seconds`, `tower`, and `tcp_proxies` if raw TCP is unavailable).
4. **realmd auth** — WoW TCP to `realmd`: AUTH_LOGON_CHALLENGE → AUTH_LOGON_PROOF → REALM_LIST
   (through wsproxy: TCP 3724 / local 23724). realmd returns the world address.
5. **World login** — world session (TCP 8085 / local 28085): SMSG_AUTH_CHALLENGE →
   CMSG_AUTH_SESSION → SMSG_AUTH_RESPONSE → CMSG_CHAR_ENUM → (create/select character if
   `character_name` was null) → CMSG_PLAYER_LOGIN → SMSG_NEW_WORLD →
   SMSG_(COMPRESSED_)UPDATE_OBJECT. (Opcode names in `wsproxy.nim:353-389`.)
6. **Play loop** — observe the `TelemetrySnapshot`/mirror each tick; emit typed `BotAction`s;
   **wait for the settled authoritative result** (`action-results.jsonl` / typed mirror
   transition / `movement_settlement.v1` + `navmesh_traversal.v1`) before treating an action as
   done — "sent is not accepted" (`architecture.md:113-141`). Browser control uses the
   `/telemetry/*` bridge endpoints.
7. **done / deadline** — the bot sends `done` (`success`, `detail`), or the server finishes the
   slot at `deadline_seconds`.
8. **Results + replay** — server compares start/end character-DB snapshots and writes scores
   (highest total XP + per-session XP gained); replay bytes go to `COGAME_SAVE_REPLAY_URI` and
   are served via `/client/replay` / `/replay`.

---

## Relationship to the other docs

- [`vanilla-wow-player-contract.md`](vanilla-wow-player-contract.md) — the **narrative** version
  of §§1–6 (start there for the mental model; this doc is the exact spec).
- [`vanilla-wow-gameplay.md`](vanilla-wow-gameplay.md) — what the observations/actions *mean* in
  game terms.
- [`vanilla-wow-rfc-roles.md`](vanilla-wow-rfc-roles.md) — the support-role protocols
  (commissioner `/round` WS, grader/diagnoser/optimizer env-var IO, reporter) that live *around*
  the player↔game interface.
