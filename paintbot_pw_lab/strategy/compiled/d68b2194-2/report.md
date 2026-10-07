# Build d68b2194-2

Status: **passed**. Intent: behavior_change.

| Gate | Pass | Evidence |
| --- | --- | --- |
| G1 | True | [{'level': 'warning', 'code': 'ste', 'message': '`Spec` uses a semicolon; write two sentences', 'component': 'SK.motor', 'line': 289}, {'level': 'warning', 'code': 'ste', 'message': '`Spec` has a sentence over 25 words', 'component': 'SK.motor', 'line': 289}] |
| G2 | True | {'seats': 16, 'failures': []} |
| G3 | True | {'instructions': 11210, 'work': 18577, 'print_bytes': 395, 'print_events': 64} |
| G4 | True | {'n_seeds': 28, 'mean_outcome': 0.49654464285714284, 'ci95_low': 0.43442916908308293, 'ci95_high': 0.5586601166312027} |
| G5 | True | {'seat_recordings': 16, 'lines': 3484, 'failures': 0, 'unexercised_message_types': []} |

## Units

- `P.walkTo`: reused
- `P.lookAt`: reused
- `P.shootAt`: reused
- `P.chargeGrenade`: reused
- `P.shout`: reused
- `K.self_motion`: reused
- `K.squad_target`: reused
- `K.contacts`: changed
- `K.pickups`: reused
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
- `COM.status_call`: changed
- `COM.grenade_out`: reused

## Guesses

- **G-K.squad_target-1** (low, open): Wrapped the whole stall-memory step in `IF progress_period > 0`, so a tuned value of 0 skips Step 1 instead of dividing by zero. — AGENTS.md rule 5 requires guarding every MOD; progress_period is a tunable param, not a literal.
  Source: When `worldTick MOD progress_period = 0`
- **G-C.take_heart-1** (low, open): Read controlX/controlY(objective) without checking objective >= 0. For an invalid objective, the host returns -1 and the engine clamps the resulting goal. — The spec still requires these reads without an objective guard, and the host safely returns -1 for invalid indices.
  Source: `goal_x = controlX(objective)`
- **G-C.cover_heart-1** (low, open): Read controlX/controlY(objective) without an objective >= 0 guard, preserving the previous unit's behavior. — The spec still omits this guard for the coordinate reads, and invalid objective indices return -1 without a runtime error. The new finish_capture condition separately requires objective >= 0.
  Source: `hx = controlX(objective)`
- **G-C.default_goal-1** (medium, open): Use the legacy carrying, ownHeartStolen, heartX and heartY fields exactly as specified. With the documented current host behavior, the default goal is the enemy home. — The spec explicitly retains these legacy fields; substituting control objectives would change the requested behavior.
  Source: else `(heartX, heartY)`
- **G-COM.grenade_out-1** (low, open): Read sk_motor__threw as left by the most recent SK.motor run before __send. If send runs before motor on a tick, the callout comes one tick late. — Call order is generated and not visible to the unit.
  Source: when threw of `SK.motor` is 1

## Gaps

```json
[]
```

## Budget

```json
{
  "array_cells": 983,
  "array_cells_limit": 4096,
  "arrays": 22,
  "arrays_limit": 256,
  "globals": 303,
  "globals_limit": 512,
  "source_bytes": 58887,
  "source_limit": 131072,
  "telemetry": {
    "bytes": 395,
    "events": 64,
    "limit_bytes": 512,
    "limit_events": 64,
    "lines": {
      "PWB": {
        "bytes": 76,
        "count": 3,
        "events": 11
      },
      "PWC": {
        "bytes": 166,
        "count": 2,
        "events": 23
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
      "K.contacts": 1,
      "K.pickups": 2,
      "K.squad_target": 0
    }
  }
}
```
