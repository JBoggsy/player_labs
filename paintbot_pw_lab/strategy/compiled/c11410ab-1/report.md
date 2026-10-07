# Build c11410ab-1

Status: **passed**. Intent: behavior_change.

| Gate | Pass | Evidence |
| --- | --- | --- |
| G1 | True | [{'level': 'warning', 'code': 'ste', 'message': '`Spec` uses a semicolon; write two sentences', 'component': 'K.squad_target', 'line': 77}, {'level': 'warning', 'code': 'ste', 'message': '`Spec` has a sentence over 25 words', 'component': 'K.squad_target', 'line': 77}, {'level': 'warning', 'code': 'ste', 'message': '`Memory` uses a semicolon; write two sentences', 'component': 'K.squad_target', 'line': 132}, {'level': 'warning', 'code': 'ste', 'message': '`Rationale` uses a semicolon; write two sentences', 'component': 'K.squad_target', 'line': 159}, {'level': 'warning', 'code': 'ste', 'message': '`Spec` uses a semicolon; write two sentences', 'component': 'K.nearby_glory', 'line': 269}, {'level': 'warning', 'code': 'ste', 'message': '`Spec` has a sentence over 25 words', 'component': 'S.glory_worth', 'line': 330}, {'level': 'warning', 'code': 'ste', 'message': '`Spec` uses a semicolon; write two sentences', 'component': 'SK.motor', 'line': 347}, {'level': 'warning', 'code': 'ste', 'message': '`Spec` uses may/should/would/might/could; state the requirement', 'component': 'SK.motor', 'line': 347}, {'level': 'warning', 'code': 'ste', 'message': '`Spec` has a sentence over 25 words', 'component': 'SK.motor', 'line': 347}, {'level': 'warning', 'code': 'ste', 'message': '`Spec` has a sentence over 25 words', 'component': 'C.cover_heart', 'line': 437}, {'level': 'warning', 'code': 'ste', 'message': '`Rationale` uses a semicolon; write two sentences', 'component': 'C.cover_heart', 'line': 455}, {'level': 'warning', 'code': 'ste', 'message': '`Rationale` uses may/should/would/might/could; state the requirement', 'component': 'C.cover_heart', 'line': 455}, {'level': 'warning', 'code': 'ste', 'message': '`Spec` uses a semicolon; write two sentences', 'component': 'ST.roles', 'line': 539}, {'level': 'warning', 'code': 'ste', 'message': '`Rationale` uses a semicolon; write two sentences', 'component': 'ST.rules', 'line': 554}] |
| G2 | True | {'seats': 16, 'failures': []} |
| G3 | True | {'instructions': 14852, 'work': 23660, 'print_bytes': 396, 'print_events': 64} |
| G4 | True | {'n_seeds': 28, 'mean_outcome': 0.5438750000000001, 'ci95_low': 0.4694375916737201, 'ci95_high': 0.6183124083262801} |
| G5 | True | {'seat_recordings': 16, 'lines': 3939, 'failures': 0, 'unexercised_message_types': []} |

## Units

- `P.walkTo`: reused
- `P.lookAt`: reused
- `P.shootAt`: reused
- `P.chargeGrenade`: reused
- `P.shout`: reused
- `K.self_motion`: reused
- `K.squad_target`: changed
- `K.contacts`: reused
- `K.pickups`: reused
- `K.nearby_glory`: reused
- `S.losing_fight`: changed
- `S.supply_worth`: reused
- `S.has_target_heart`: changed
- `S.glory_worth`: reused
- `SK.motor`: changed
- `C.take_heart`: changed
- `C.cover_heart`: changed
- `C.default_goal`: changed
- `C.resupply`: changed
- `C.fall_back`: changed
- `C.collect_glory`: changed
- `ST.roles`: changed
- `ST.rules`: reused
- `ST.commitment`: reused
- `COM.status_call`: changed
- `COM.grenade_out`: changed

## Guesses

- **G-K.squad_target-1** (low, open): Wrapped the whole stall-memory step in `IF progress_period > 0`, so a tuned value of 0 skips Step 1 instead of dividing by zero. — AGENTS.md rule 5 requires guarding every MOD; progress_period is a tunable param, not a literal.
  Source: When `worldTick MOD progress_period = 0`
- **G-C.take_heart-1** (low, open): Read controlX/controlY(objective) without checking objective >= 0. For an invalid objective, the host returns -1 and the engine clamps the resulting goal. — The spec still requires these reads without an objective guard, and the host safely returns -1 for invalid indices.
  Source: `goal_x = controlX(objective)`
- **G-C.cover_heart-1** (low, open): Read controlX/controlY(objective) without an objective >= 0 guard, as required by the current direct-capture spec. — Invalid objective indices return -1 without a runtime error. The inherited spec_quote is retained exactly as required for previous guesses; the current source removes its backticks.
  Source: `hx = controlX(objective)`
- **G-C.default_goal-1** (medium, open): Retain the specified legacy carrying, ownHeartStolen, heartX and heartY fields. The fallback remains the enemy home under documented host behavior; the current spec removes the prior pursuit override. — The legacy-field interpretation still applies. The new Step 2 calls sk_motor__act directly, so retaining the previous pursuit logic would contradict the current source.
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
  "array_cells": 987,
  "array_cells_limit": 4096,
  "arrays": 23,
  "arrays_limit": 256,
  "globals": 327,
  "globals_limit": 512,
  "source_bytes": 65739,
  "source_limit": 131072,
  "telemetry": {
    "bytes": 396,
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
        "bytes": 51,
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
