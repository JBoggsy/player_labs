# Build c03010be-1

Status: **passed**. Intent: behavior_change.
G5 event coverage: **not exercised**: COM.disguise_alert, COM.disguise_friend. Their semantic checks remain unproven.


| Gate | Pass | Evidence |
| --- | --- | --- |
| G1 | True | [] |
| G2 | True | {'seats': 16, 'failures': []} |
| G3 | True | {'instructions': 21185, 'work': 31811, 'print_bytes': 434, 'print_events': 63} |
| G4 | True | {'n_seeds': 28, 'mean_outcome': 0.5717142857142857, 'ci95_low': 0.4943390384520709, 'ci95_high': 0.6490895329765006} |
| G5 | True | {'seat_recordings': 16, 'lines': 8532, 'failures': 0, 'unexercised_message_types': ['COM.disguise_alert', 'COM.disguise_friend']} |

## Units

- `P.walkTo`: reused
- `P.lookAt`: reused
- `P.shootAt`: reused
- `P.chargeGrenade`: reused
- `P.shout`: reused
- `K.self_motion`: changed
- `K.squad_target`: reused
- `K.contacts`: changed
- `K.pickups`: changed
- `K.comms_danger`: new
- `K.glory_hearts`: new
- `S.losing_fight`: changed
- `S.supply_worth`: changed
- `S.has_target_heart`: reused
- `SK.motor`: changed
- `C.take_heart`: changed
- `C.cover_heart`: changed
- `C.default_goal`: changed
- `C.resupply`: changed
- `C.fall_back`: changed
- `ST.roles`: reused
- `ST.rules`: reused
- `ST.commitment`: reused
- `COM.disguise_friend`: new
- `COM.disguise_alert`: new
- `COM.focus_call`: new
- `COM.glory_seen`: new
- `COM.enemy_sighting`: new
- `COM.grenade_warning`: new
- `COM.under_fire`: new
- `COM.pickup_taken`: new
- `COM.pickup_ready`: new
- `COM.status_call`: removed
- `COM.grenade_out`: removed

## Guesses

- **G-K.squad_target-1** (low, open): Wrapped the whole stall-memory step in `IF progress_period > 0`, so a tuned value of 0 skips Step 1 instead of dividing by zero. — AGENTS.md rule 5 requires guarding every MOD; progress_period is a tunable param, not a literal.
  Source: When `worldTick MOD progress_period = 0`
- **G-C.take_heart-1** (low, open): Read controlX/controlY(objective) without checking objective >= 0. If the activation runs with objective = -1, the host returns -1 (invalid index), so there is no runtime error. The goal is then (-1, -1), which the engine clamps. — The spec has no objective >= 0 guard here, unlike the default_goal/resupply/fall_back steps. The selector presumably runs this only when S.has_target_heart is on, and controlX(-1) is safe.
  Source: `goal_x = controlX(objective)`
- **G-C.cover_heart-1** (low, open): Same as C.take_heart: no objective >= 0 guard, relying on controlX(-1) = -1 being safe. — Literal reading of the spec. The host returns -1 for invalid indices instead of raising an error.
  Source: `hx = controlX(objective)`
- **G-C.default_goal-1** (medium, open): Used the legacy host fields carrying, ownHeartStolen, heartX and heartY exactly as written. Under rules 47 carrying and ownHeartStolen are always 0 and heartX/heartY read the enemy home, so in practice the goal is the thief (never set, see gaps) or the enemy home. — The spec names these fields explicitly and matches base.bas; I did not substitute control* fields.
  Source: else `(heartX, heartY)`
- **G-COM.grenade_out-1** (low, possibly resolved): Read sk_motor__threw as left by the most recent SK.motor run before __send. If send runs before motor on a tick, the callout comes one tick late. — Call order is generated and not visible to the unit.
  Source: when threw of `SK.motor` is 1
- **G-K.pickups-1** (medium, open): Kept the literal HP thresholds (medkit wanted below 3 HP, armor only at exactly 3 HP, medkit cost quartered at 1 HP) even though rules 49 HP runs 0-10. — The numbers are written into the Spec, not Params; changing them would be inventing behavior. Under rules 49 armor is rarely wanted and medkits only when nearly dead.
  Source: (kind = 2 AND selfHp < 3)
- **G-K.pickups-2** (low, open): Step 0 tests mem_tick(j) = worldTick literally, so a take is detected only when the station was in view on the immediately previous tick (mem_tick = previous tick + 1). The pickupVisible, prev_ and host state values are read once per tick and reused for Step 0c. — Literal reading; the runtime runs every living tick, so worldTick advances by 1 between updates.
  Source: `mem_tick(j) = worldTick` (previously visible and ready)
- **G-K.contacts-1** (low, open): Own evidence (and so xe_label) is evaluated only for teammate-parity bodies that reached Step 0c, that is not matched by a live friend record and not enemy parity. — Own evidence is defined inside Step 0c, and a body matched in Step 0a skips to the next i.
  Source: whose own evidence holds and where
- **G-K.contacts-2** (low, open): Kept the literal 3 in the cost even though rules 49 HP is 0-10; the term still ranks wounded bodies first, offset by a constant. — The value is in the Spec, not a Param.
  Source: `cost = d2 - (3 - playerHp(i)) * hp_weight`
- **G-COM.disguise_alert-1** (medium, open): When a report fills witness 1 (expired slot) and the live witness 2 has the same speaker, witness 2 is expired (xa_t2 = 0). — The explicit witness-1 rule does not check witness 2, so without this one sender could hold both slots and block a real second witness. Expiring the duplicate keeps the stated invariant; K.contacts also requires xa_s1 <> xa_s2.
  Source: one sender never fills both witnesses
- **G-COM.disguise_alert-2** (low, open): The reset is done in __recv for label L, before this message is applied, when both xa_t1(L) and xa_t2(L) are <= worldTick. — COM units have no per-tick SUB, and send/recv may not run on a given tick. A stale amb is harmless while both witnesses are expired, because K.contacts also requires live witnesses.
  Source: Set `xa_amb(L) = 0` again when both witnesses
- **G-COM.disguise_alert-3** (low, open): A message whose cm__fa is outside 0..15 is ignored. In __send, the strong label is used only when 0 <= xe_label < 16. — This keeps every array index in range (AGENTS.md rule 5); the wire field width is not visible to the unit.
  Source: In `__recv`: set `L = cm__fa`, `amb = 0`
- **G-COM.disguise_friend-1** (low, open): Within means squared distance <= d_range_sq. In __recv, a cm__fa outside 0..15 is ignored. — Inclusive bound, plus the index guard required by rule 5.
  Source: visible within `d_range_sq`
- **G-COM.enemy_sighting-1** (low, open): Teammate seats are s <> selfId with s MOD 2 = selfTeam. The cost of a body is its squared distance to the nearest such recently heard teammate, or to us when there is none. — cm__heard_* is kept per claimed sender seat, which may include enemy-parity labels; the spec says teammate.
  Source: Choose the one nearest to any teammate seat s with
- **G-COM.glory_seen-1** (low, open): Position matching for gl_* (in __recv) and hs_* (after a send) considers only slots in use (gl_until > 0, hs_t > 0), taking the lowest matching slot. Otherwise it takes the slot with the smallest gl_until or hs_t, lowest index on a tie. — Without this, an empty slot at (0, 0) would match a heart near the origin.
  Source: Use the slot j that is within h_match of `(px, py)`
- **G-COM.grenade_warning-1** (low, open): release_in is sent unclamped, exactly as SK.motor reports it. — The spec gives no clamp; the runtime owns encoding.
  Source: call `cm__send(2, release_in, 0, cell, quiet)`

## Gaps

```json
[
  {
    "component": "C.take_heart",
    "need": "sk_motor__sneak(1), declared in the SK.motor interface and named by every C.* quiet-approach step",
    "substitute": "Called sk_motor__sneak(1) as declared. The read-only context copy units/SK.motor.bas defines no sk_motor__sneak (nor quiet, charging, charge_x/y, charge_started or release_in), so the build depends on the assembled SK.motor matching its declared interface. The same applies to C.cover_heart, C.default_goal, C.resupply and C.fall_back."
  },
  {
    "component": "COM.grenade_warning",
    "need": "sk_motor__charging, charge_started, charge_x, charge_y, release_in and quiet outputs of SK.motor",
    "substitute": "Read them as declared in the SK.motor interface; the context copy of units/SK.motor.bas does not set them yet."
  },
  {
    "component": "C.default_goal",
    "need": "a heart carrier / thief and carrying state",
    "substitute": "Used the legacy carrying, ownHeartStolen, heartX/heartY and K.contacts thief (from playerCarrying) as written; under rules 47+ these are constant (0 / enemy home), so thief is always -1."
  }
]
```

## Budget

```json
{
  "array_cells": 2324,
  "array_cells_limit": 4096,
  "arrays": 105,
  "arrays_limit": 256,
  "globals": 354,
  "globals_limit": 512,
  "source_bytes": 127897,
  "source_limit": 131072,
  "telemetry": {
    "bytes": 434,
    "events": 63,
    "limit_bytes": 512,
    "limit_events": 64,
    "lines": {
      "PWB": {
        "bytes": 76,
        "count": 5,
        "events": 11
      },
      "PWC": {
        "batch": true,
        "bytes": 205,
        "count": 1,
        "events": 22
      },
      "PWD": {
        "bytes": 50,
        "count": 1,
        "events": 11
      },
      "PWE": {
        "bytes": 103,
        "count": 3,
        "events": 19
      },
      "PWP": {
        "bytes": 0,
        "count": 0,
        "events": 0
      }
    },
    "log_offsets": {
      "K.comms_danger": 3,
      "K.contacts": 1,
      "K.glory_hearts": 4,
      "K.pickups": 2,
      "K.squad_target": 0
    }
  }
}
```
