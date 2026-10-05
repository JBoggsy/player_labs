# Build b41ef1fc-1

Status: **passed**. Intent: m1.

| Gate | Pass | Evidence |
| --- | --- | --- |
| G1 | True | [] |
| G2 | True | {'seats': 16, 'failures': []} |
| G3 | True | {'instructions': 10175, 'work': 17298, 'print_bytes': 482, 'print_events': 59} |
| G4 | True | {'n_seeds': 28, 'mean_outcome': 0.5, 'ci95_low': 0.5, 'ci95_high': 0.5} |
| G5 | True | {'seat_recordings': 16, 'lines': 2712, 'failures': 0} |

## Units

- `P.walkTo`: new
- `P.lookAt`: new
- `P.shootAt`: new
- `P.chargeGrenade`: new
- `P.shout`: new
- `K.self_motion`: new
- `K.squad_target`: new
- `K.contacts`: new
- `K.pickups`: new
- `S.losing_fight`: new
- `S.supply_worth`: new
- `S.has_target_heart`: new
- `SK.motor`: new
- `C.take_heart`: new
- `C.cover_heart`: new
- `C.default_goal`: new
- `C.resupply`: new
- `C.fall_back`: new
- `ST.roles`: new
- `ST.rules`: new
- `ST.commitment`: new
- `COM.status_call`: new
- `COM.grenade_out`: new

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
[
  {
    "component": "K.contacts",
    "need": "playerCarrying(i) to find a visible enemy heart carrier (thief)",
    "substitute": "Called playerCarrying as specified. Under rules 47 it always returns 0, so thief stays -1 and carrier_bonus never applies."
  },
  {
    "component": "K.pickups",
    "need": "carrying and playerCarrying to block supply detours while a heart is carried",
    "substitute": "Used the legacy fields as specified. Both are always 0 under rules 47, so the block never triggers."
  },
  {
    "component": "S.losing_fight",
    "need": "carrying (we carry a heart)",
    "substitute": "Used the legacy host field as specified. It is always 0 under rules 47, so NOT carrying is always true."
  },
  {
    "component": "C.default_goal",
    "need": "carrying, ownHeartStolen, heartX/heartY (capture-the-flag state)",
    "substitute": "Used the legacy fields as specified. Under rules 47 they read 0, 0 and the enemy home."
  }
]
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
  "source_bytes": 53951,
  "source_limit": 131072,
  "telemetry": {
    "bytes": 482,
    "events": 59,
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
        "bytes": 130,
        "count": 1,
        "events": 19
      },
      "PWE": {
        "bytes": 192,
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
