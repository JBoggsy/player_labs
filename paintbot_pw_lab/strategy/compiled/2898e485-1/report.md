# Build 2898e485-1

Status: **passed**. Intent: m1.

| Gate | Pass | Evidence |
| --- | --- | --- |
| G1 | True | [] |
| G2 | True | {'seats': 16, 'failures': []} |
| G3 | True | {'instructions': 10241, 'work': 17329, 'print_bytes': 313, 'print_events': 51} |
| G4 | True | {'n_seeds': 28, 'mean_outcome': 0.4503571428571429, 'ci95_low': 0.3842883820427039, 'ci95_high': 0.5164259036715819} |
| G5 | True | {'seat_recordings': 16, 'lines': 3477, 'failures': 0, 'unexercised_message_types': []} |

## Units

- `P.walkTo`: changed
- `P.lookAt`: changed
- `P.shootAt`: changed
- `P.chargeGrenade`: changed
- `P.shout`: changed
- `K.self_motion`: changed
- `K.squad_target`: changed
- `K.contacts`: changed
- `K.pickups`: changed
- `S.losing_fight`: changed
- `S.supply_worth`: changed
- `S.has_target_heart`: changed
- `SK.motor`: changed
- `C.take_heart`: changed
- `C.cover_heart`: changed
- `C.default_goal`: changed
- `C.resupply`: changed
- `C.fall_back`: changed
- `ST.roles`: changed
- `ST.rules`: changed
- `ST.commitment`: changed
- `COM.status_call`: changed
- `COM.grenade_out`: changed

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
    "need": "Identify a visible enemy carrying a heart.",
    "substitute": "Retained playerCarrying as specified; the current host returns 0, so thief remains -1 and the carrier bonus does not apply."
  },
  {
    "component": "K.pickups",
    "need": "Suppress supply selection while we or a visible enemy carry a heart.",
    "substitute": "Retained carrying and playerCarrying as specified; both are legacy fields returning 0 in the current game."
  },
  {
    "component": "C.default_goal",
    "need": "Choose between the stolen-heart carrier, our home, and the enemy heart using capture-the-flag state.",
    "substitute": "Retained the specified legacy host fields. carrying and ownHeartStolen are 0, and heartX/heartY identify the enemy home."
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
  "source_bytes": 54125,
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
