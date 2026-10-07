# Build 3d0f8a4f-1

Status: **passed**. Intent: m1.

| Gate | Pass | Evidence |
| --- | --- | --- |
| G1 | True | [] |
| G2 | True | {'seats': 16, 'failures': []} |
| G3 | True | {'instructions': 10521, 'work': 17785, 'print_bytes': 313, 'print_events': 51} |
| G4 | True | {'n_seeds': 28, 'mean_outcome': 0.5, 'ci95_low': 0.5, 'ci95_high': 0.5} |
| G5 | True | {'seat_recordings': 16, 'lines': 3098, 'failures': 0} |

## Units

- `P.walkTo`: reused
- `P.lookAt`: reused
- `P.shootAt`: reused
- `P.chargeGrenade`: reused
- `P.shout`: reused
- `K.self_motion`: reused
- `K.squad_target`: reused
- `K.contacts`: reused
- `K.pickups`: reused
- `S.losing_fight`: reused
- `S.supply_worth`: reused
- `S.has_target_heart`: reused
- `SK.motor`: reused
- `C.take_heart`: reused
- `C.cover_heart`: reused
- `C.default_goal`: reused
- `C.resupply`: reused
- `C.fall_back`: reused
- `ST.roles`: reused
- `ST.rules`: reused
- `ST.commitment`: reused
- `COM.status_call`: reused
- `COM.grenade_out`: reused

## Guesses

- **G-K.squad_target-1** (low, open): Wrapped the whole stall-memory step in `IF progress_period > 0`, so a tuned value of 0 skips Step 1 instead of dividing by zero. — AGENTS.md rule 5 requires guarding every MOD; progress_period is a tunable param, not a literal.
  Source: When `worldTick MOD progress_period = 0`
- **G-C.take_heart-1** (low, open): Read controlX/controlY(objective) without checking objective >= 0. If the activation runs with objective = -1, the host returns -1 (invalid index), so there is no runtime error. The goal is then (-1, -1), which the engine clamps. — The spec has no objective >= 0 guard here, unlike the default_goal/resupply/fall_back steps. The selector presumably runs this only when S.has_target_heart is on, and controlX(-1) is safe.
  Source: `goal_x = controlX(objective)`
- **G-C.cover_heart-1** (low, open): Same as C.take_heart: no objective >= 0 guard, relying on controlX(-1) = -1 being safe. — Literal reading of the spec. The host returns -1 for invalid indices instead of raising an error.
  Source: `hx = controlX(objective)`
- **G-C.default_goal-1** (medium, open): Used the legacy host fields carrying, ownHeartStolen, heartX and heartY exactly as written. Under rules 47 carrying and ownHeartStolen are always 0 and heartX/heartY read the enemy home, so in practice the goal is the thief (never set, see gaps) or the enemy home. — The spec names these fields explicitly and matches base.bas; I did not substitute control* fields.
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
  "globals": 275,
  "globals_limit": 512,
  "source_bytes": 54045,
  "source_limit": 131072,
  "telemetry": {
    "bytes": 313,
    "events": 51,
    "limit_bytes": 512,
    "limit_events": 64,
    "lines": {
      "PWB": {
        "bytes": 64,
        "count": 3,
        "events": 9
      },
      "PWC": {
        "bytes": 96,
        "count": 2,
        "events": 12
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
