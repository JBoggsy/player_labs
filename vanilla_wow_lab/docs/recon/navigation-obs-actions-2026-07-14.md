# Recon: navigation observations & movement action space (Vanilla WoW)

**Date:** 2026-07-14. **Consumer:** the next implementation step — giving `wowborg` a
navigate-to-a-random-nearby-point sub-goal. Citations are into
`~/coding/coworlds/coworld-vanilla-wow` (pulled 2026-07-14, HEAD `312d1d0c7`) and this lab.

## Mission

Establish, from source, (1) every observation a player policy can use for navigation and
(2) the complete action space for movement, including packet formats, timing constraints,
and server tolerance — so we can design wowborg v2's movement layer without guessing.

## The one framing fact

**There is no structured observation or action API for a hosted policy.** The adapter's
`/player` WebSocket carries only lifecycle messages (`wow_session` credentials/endpoints/
deadline, `pong`, `final` — `src/vanilla_wow_coworld/session.py:99-175`), and the manifest
says explicitly "The v1 Vanilla WoW Coworld does not stream gameplay over /global"
(`coworld_manifest_template.json:390`). The `/tcp/realmd` and `/tcp/world` tunnels are pure
byte pipes with zero parsing or filtering (`src/vanilla_wow_coworld/tcp_proxy.py:66-78`).
Everything below — observations *and* actions — is the raw WoW 1.12.1 (build 5875) binary
protocol that we must parse/emit ourselves. The typed `TelemetrySnapshot`/`BotAction`/
`movement_settlement` protocols documented in
[`../vanilla-wow-protocol.md`](../vanilla-wow-protocol.md) exist **inside the bundled Nim
player's own container** (file-bridge between the Nim client and its bot policy,
`src/wow_sdk/nim_client.py:2404`); they are not served to us unless we run that Nim stack.

A key consequence: **1.12 movement is client-authoritative.** The client integrates its own
physics and *tells* the server where it is in each movement packet; the server relays it and
applies sanity checks. There is no "request move, server moves you" — we self-report
positions at legal speeds. The adapter adds no packet policing (searches for opcode
filtering/anticheat in `src/vanilla_wow_coworld/` came up empty); VMaNGOS itself, with the
account at gmlevel 0, is the only enforcement layer.

## Q1: Observations usable for navigation

### Own position & orientation (the pose)

| Source | Opcode | What it gives | Parse reference |
|---|---|---|---|
| `SMSG_LOGIN_VERIFY_WORLD` | 566 | `map_id:u32, x,y,z,o:f32` — first authoritative pose | already in `wowborg/world.py:144-154`; Nim: `game_client/packets/lifecycle.nim:255-269` |
| `SMSG_UPDATE_OBJECT` / `SMSG_COMPRESSED_UPDATE_OBJECT` | 169 / 502 | on create-block for our own GUID: `movementFlags:u32, time:u32, x,y,z,o:f32` + conditional transport/pitch/fallTime/jump blocks + 6 speed floats (walk, run, runback, swim, swimback, turn) | `game_client/protocol.nim:464-534` (compressed = zlib body, `:629-654`) |
| `MSG_MOVE_TELEPORT_ACK` | 199 | server relocates us: packed GUID + counter + full MovementInfo — **must be ACKed** | `game_client/packets/movement.nim:685-699`; handling `viewers/session_classifier.nim:864-881` |
| `SMSG_NEW_WORLD` | 62 | map transfer: `map_id, x,y,z,o` — reply `MSG_MOVE_WORLDPORT_ACK` + `CMSG_SET_ACTIVE_MOVER` | `lifecycle.nim:334-348`; `session_classifier.nim:825-848` |

Position convention: WoW world yards, `o` = orientation in radians (0 = +X, counterclockwise,
normalized to [0, 2π)). `MovementInfo` layout (client and server share it,
`movement.nim:156-176`, wire format `:553-592`):

```
flags:u32, time:u32(ms), x:f32, y:f32, z:f32, o:f32,
[if flags & TRANSPORT(0x02000000): transportGuid:u64 + local x,y,z,o],
[if flags & SWIMMING(0x00200000): pitch:f32],
fallTime:u32,
[if flags & JUMPING(0x00002000): jumpZSpeed, cos, sin, xySpeed:f32],
[if flags & SPLINE_ELEVATION(0x04000000): f32]
```

Between packets we know our pose by **dead reckoning**: we sent it, so we know it. The Nim
client integrates full collision physics client-side and treats a server MovementInfo >1.5 yd
from prediction as a correction event (`movement_authority.nim:7`, `:483-500`).

### Nearby entities

`SMSG_UPDATE_OBJECT` create/update blocks give every visible unit/player/gameobject a GUID,
position, and movement flags (Nim's object store keeps `Table[Guid, Object]` with
`location`, `serverPath`, `moveSpline`, etc. — `game_client/objects.nim:308-716`).
`SMSG_MONSTER_MOVE` (221) carries NPC spline paths — start xyz, duration, waypoint list
(`packets/monster_move.nim:495-583`). `MSG_MOVE_*` broadcasts from other players parse with
the same MovementInfo. Not needed for the first navigate-to-point goal, but this is the
"what's around me" channel.

### Movement speeds

The wire truth: defaults **run 7.0 yd/s, walk 2.5, run-back 4.5, swim 4.722, swim-back 2.5,
turn rate π rad/s** (`game_client/viewers.nim:216-221`; `locomotion.nim:9-13`). Changes
arrive as `SMSG_FORCE_RUN_SPEED_CHANGE` (226) etc. — packed GUID, counter, `speed:f32` —
and **each must be ACKed** with the counter plus a MovementInfo echo
(`movement.nim:780-788`; ACK flow `viewers/movement_emitters.nim:250-270`).

### Terrain and obstacles: NOT observable over the wire

No packet carries geometry. The Nim client knows terrain only from **extracted client-side
data files**: height maps (`maps/`), collision (`vmaps/` → `.vmtile`), and Detour navmesh
tiles (`mmaps/` → `.mmtile`, magic `MMAP` v6) under `local_data/vmangos-5875-data`
(`simulation/terrain.nim:15,105`; `formats/vmtile.nim:6`;
`simulation/navmesh_collision.nim:24-27,457`). Pathfinding shells out to a Detour helper
(`navmeshes.nim:571-610`; helper source `wow-sdk/helpers/vmangos_navmesh_helper.cpp`). The
server container ships the same data and its image build fails without mmaps
(`docker/coworld-vmangos/Dockerfile:55-59`), so the server runs full pathfinding/collision.
**wowborg has none of this** unless we bundle those files or accept blind movement.

## Q2: Action space for movement

Movement "actions" are client→server `MSG_MOVE_*` packets, each carrying our full
self-reported MovementInfo. Opcode constants (`game_client/packets/movement.nim:19-126`):

| Intent | Opcode | # |
|---|---|---|
| start/stop moving | `MSG_MOVE_START_FORWARD` / `START_BACKWARD` / `STOP` | 181 / 182 / 183 |
| strafe | `START_STRAFE_LEFT` / `RIGHT` / `STOP_STRAFE` | 184 / 185 / 186 |
| jump | `MSG_MOVE_JUMP` (jumpZSpeed **7.95797334**, `movement.nim:153`) | 187 |
| turn (continuous) | `START_TURN_LEFT` / `RIGHT` / `STOP_TURN` | 188 / 189 / 190 |
| run/walk toggle | `SET_RUN_MODE` / `SET_WALK_MODE` | 194 / 195 |
| set facing (instant) | `MSG_MOVE_SET_FACING` — MovementInfo with new `o` | 218 |
| position update while state unchanged | `MSG_MOVE_HEARTBEAT` | 238 |
| landing after a fall | `MSG_MOVE_FALL_LAND` (carries fallTime) | 201 |
| swim | `START_SWIM` / `STOP_SWIM` | 202 / 203 |

Movement flags in the body (`objects.nim:9-14`, `movement.nim:127-152`): FORWARD 0x1,
BACKWARD 0x2, STRAFE_LEFT 0x4, STRAFE_RIGHT 0x8, TURN_LEFT 0x10, TURN_RIGHT 0x20,
WALKING 0x100, JUMPING 0x2000, SWIMMING 0x200000, ONTRANSPORT 0x02000000.

The client packet-builder reference is `buildMovement` (`movement.nim:1057-1103`) — exactly
the MovementInfo layout above. Opcode choice = the flag *transition* (forward newly set →
START_FORWARD; cleared → STOP; nothing changed → HEARTBEAT), and the stock client sends
**one flag transition per packet** (`movementOpcodeForFlags` `:1225-1304`,
`movementControlTransitionSteps` `:1502-1529`).

### How "go to a point" works with these primitives

The engine's own steering law (`bots/locomotion/controller.nim:241-329`):
`desired = atan2(wp.y - y, wp.x - x)`; turn toward it (deadband 0.06 rad); press forward
while |heading error| ≤ 0.70 rad. In packet terms the minimal legal walk-to-point is:

1. `MSG_MOVE_SET_FACING` with `o = desired` (bots snap facing rather than TURN_LEFT-ing).
2. `MSG_MOVE_START_FORWARD` at the current position.
3. Every Δt: integrate `pos += speed·Δt·(cos o, sin o)`, send `MSG_MOVE_HEARTBEAT` with the
   new position and `time += Δt(ms)`.
4. Within arrival radius, `MSG_MOVE_STOP` at the final position.

The `time` field is a per-session millisecond counter incremented by the step size — the
Nim viewer path uses a synthetic counter, not wall clock (`viewers/movement_emitters.nim:30`).
Arrival radius convention in the engine: **3.0 yd** (`src/wow_sdk/protocol.py:39`,
`MOVE_ARRIVAL_DISTANCE`); minimum meaningful move 0.25 yd (`movement.nim:154`).

### Timing / tolerance constraints (from the reference client)

- **Cadence:** while moving, the GUI client sends at most one packet per **80 ms**
  (`PlayerMoveSendSeconds 0.08`, `player_runtime.nim:136-140`); the raw-TCP bots use fixed
  **200 ms** steps (`FollowStepSeconds 0.20`, `packets.nim:192-193`). Stationary heartbeat
  every **1.0 s**. 200 ms is the proven-comfortable bot cadence.
- **Speed honesty:** integrate at ≤ the server-granted speed (7.0 run). VMaNGOS movement
  anticheat is active by default (no config override in
  `docker/vmangos/configure_vmangos.py:130-157` — stock conf.dist applies).
- **ACK discipline:** every server force (speed / root / knockback / teleport / feather-fall
  / water-walk) must be ACKed with the echoed counter and MovementInfo
  (`movement_emitters.nim:154-290`), or the server desyncs/ignores us.
- **Server splines outrank us:** while a server-driven spline is pending (charge, taxi,
  knockback), the server ignores client movement; the client must send
  `CMSG_MOVE_SPLINE_DONE` from within **10 yd** of the spline end
  (`tools/proof_local_player_charge_spline.nim:1-27`).
- **Root:** translation flags while rooted are invalid; VMaNGOS rejects the combination
  (`movement.nim:380-393`).
- `CMSG_SET_ACTIVE_MOVER` must have been sent post-login — wowborg v1 already does
  (`wowborg/world.py:198-199`).

### What we deliberately don't get

- **No z truth while moving.** Without heightmap/collision data we must carry z forward and
  rely on the ground being flat, or bundle extracted terrain data. On slopes our reported z
  will drift; the failure mode is desync or (worst case, water/cliffs) a wrong movement
  state. The orc start area (Valley of Trials) is topographically gentle — good first arena.
- **No typed settlement.** The `movement_settlement.v1` result exists only inside the Nim
  stack. Our success signal is our own dead-reckoned arrival plus, where visible, the
  absence of server corrections (teleport-ack packets addressed at us).

## Cross-references and surprises

- The adapter imposes **no tick structure** on gameplay: `max_ticks/tick_rate` is converted
  once into wall-clock `deadline_seconds` (`session.py:94,131`) and nothing gates the
  tunnels per tick. The realm runs real time.
- The "sent is not accepted" / no-teleport rules in the game docs are **authoring norms,
  not runtime enforcement** (`AGENTS.md:52`); the runtime gate is VMaNGOS itself.
- The update-object create block *contains* the six speeds but the reference client skips
  them (`protocol.nim:499`) and trusts force-speed packets + stock defaults instead. Mirrors
  a nice simplification for us: hardcode 7.0 until an `SMSG_FORCE_RUN_SPEED_CHANGE` arrives.
- Jump physics constants if we ever need them: gravity 19.29110527, jumpZ 7.95797334,
  terminal velocity 60.148 (`simulation/physics.nim:36-48`).

## Unresolved

- **Which VMaNGOS anticheat thresholds are active** (exact speed-tolerance/desync-kick
  values in `mangosd.conf.dist` at the pinned ref) — unverified; we know only that no
  override is applied. Resolve by reading the pinned VMaNGOS conf or empirically via a
  hosted smoke.
- **Whether/how the server corrects silent z-drift on gentle slopes** (vs. only on gross
  violations) — needs a live experiment.
- Per-agent policy log retention on hosted episodes (session-3 open thread) — still the
  blocker for observing any of this from artifacts.

## Files read (full or significant section)

- Lab: `docs/vanilla-wow-protocol.md`, `docs/vanilla-wow-player-contract.md`,
  `docs/designs/wowborg-player-design.md`, `WORKING_CONTEXT.md`, `wowborg/world.py`,
  `wowborg/run.py`, `wowborg/opcodes.py`
- Game repo: `player/game_client/packets/movement.nim` (opcodes, MovementInfo,
  buildMovement, parseMovement), `player/game_client/viewers/movement_emitters.nim`,
  `player/game_client/player_runtime/movement_{frame,actions}.nim`,
  `player/game_client/locomotion.nim`, `player/game_client/movement_authority.nim` (skim),
  plus subagent sweeps over `player/bots/`, `player/king_richard/`, `player/king_nimrod/`,
  `src/vanilla_wow_coworld/`, `src/wow_sdk/protocol.py`, docker/manifest files.

## Next steps (handoff)

The implementer's first files: `wowborg/world.py` (replace `_drain_loop` with a real packet
dispatcher; add own-GUID pose tracking from LOGIN_VERIFY_WORLD + teleport acks),
`wowborg/opcodes.py` (add the MSG_MOVE_* family + force-speed opcodes), and a new
`wowborg/movement.py` (MovementInfo build/parse — pure and unit-testable against
`buildMovement`, plus the dead-reckoning walk-to-point loop at 200 ms cadence). The typed
per-kind acceptance test is a hosted smoke on `orc-fresh-start`: pick a random point within
~20 yd, walk, confirm displacement via a subsequent own-position observation.
