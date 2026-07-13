# CTF — game reference

The **self-contained** gameplay reference for **Coworld CTF**, a two-team
capture-the-flag shooter on the **BitWorld Sprite-v1** protocol. Read this to build
a mental model of the game before reasoning about play or setting direction — you
rarely need to leave the lab.

The **authoritative source** is the game repo `Metta-AI/coworld-ctf` (Nim server
`src/ctf.nim` + `src/ctf/`, baseline player `players/baseline/`, rules
`docs/RULES.md`), cloned for reference at **`~/coding/coworlds/coworld-ctf`**. Every
tuning number below is mirrored in that repo's `config.json` and
`coworld_manifest.json`; if this doc and the repo disagree, the repo wins — treat the
mismatch as a finding and reconcile it. CTF is a **fork of Crewrift** and keeps
Crewrift's continuous 2D movement, line-of-sight, Sprite-v1 protocol, websocket
server, and replay infrastructure; it replaces the social-deduction layer (roles,
tasks, voting) with **teams, guns, flags, and fog-of-war vision**.

Engine tick rate: **24 ticks/sec**.

---

## The game in one paragraph

Two teams of eight (**Red** on the left edge, **Blue** on the right) spawn in a
symmetric, cover-dense arena, each guarding a flag on a home pedestal. You **move**
with the d-pad, **aim** a continuous per-player angle (decoupled from movement), and
**shoot** an instant hitscan gun. Vision is **fog-of-war**: the static map is always
visible, but enemies only appear inside your **forward vision cone** (±45° around your
aim, unlimited range, blocked by walls) or a small **omnidirectional bubble** (~90px).
Steal the enemy flag and carry it into your home capture zone — or wipe the enemy team
— to win. **Scoring is win-only: +100 to every player on the winning team, 0
otherwise.** Kills, deaths, and captures are recorded but award no points, so the
objective is purely **team victory**.

---

## Arena & teams

- **Map:** symmetric, **1235 × 659 px**, center **(617, 329)**, mirror line x = 617.
  Dense staggered cover (offset wall stubs, diamonds, discs, diagonal chevrons)
  mirrored across the vertical axis — **no straight sightline crosses the field**;
  every approach is a series of corners. `mapPath: "arena"` (procedurally generated).
- **16 players, 8 v 8.** Team is assigned by **slot parity**: **even slot = Red**
  (left), **odd slot = Blue** (right). Seat within a team = `slot div 2` (0–7).
- **Geometry landmarks** (baseline README): capture zones roughly `x ≤ 206` (Red home)
  and `x ≥ 1029` (Blue home); pedestals at **(186, 329)** Red / **(1049, 329)** Blue.
- **Phases:** Lobby → Playing → GameOver (`startWaitTicks` lobby countdown, then play
  until a win condition or the time limit, then a `gameOverTicks` tail).

## Movement

Continuous — acceleration, friction, max speed, wall-sliding — driven by the
**d-pad** (Up/Down/Left/Right, combinable into 8 octants). Movement is **pure
locomotion**: it *never* changes your aim or your vision. You see where you point, not
where you walk.

## Aim (the dominant lever)

- A continuous per-player **aim angle in brads** (**256 brads = one full turn**,
  integer, deterministic). `0 = east (+x)`, increasing **counter-clockwise on screen**
  (64 = N, 128 = W, 192 = S).
- **Decoupled from movement.** Hold **B** to rotate CCW, **Select** to rotate CW at
  `aimTurnRate` (default **5 brads/tick ≈ 7°/tick; a full turn takes ~2.1 s**). Both
  held cancels out.
- Aim drives three things at once: the **gun** direction, the **vision cone**
  direction, and the sprite flip. **Managing aim = managing both what you can kill and
  what you can see** — this is the single most important tactical variable.
- On spawn/respawn, aim points toward the enemy side (Red → east/0, Blue → west/128).
- A short **aim-indicator line** is drawn from every player you can currently see (and
  from yourself) — readable enemy intel about where an opponent is about to shoot/look.

## Vision / fog-of-war

- The **full static map is always drawn** (terrain is permanent knowledge). Moving
  entities are fogged.
- Your vision = a **forward cone**, half-angle `visionConeDeg` (default **±45°**)
  around your **aim**, **unlimited range**, **plus** a small **omnidirectional bubble**
  `visionBubble` (default **~90 px**). **Walls block vision** (the same walls block
  bullets).
- **Always visible regardless of fog:** the static map, **both flag pedestals**, your
  **own flag's state** (an empty own pedestal = it's been stolen — but the thief is
  fogged), and **yourself** (a distinct self marker).
- **Teammates ARE fogged — there is no team radio.** You cannot see allies unless they
  fall in your cone/bubble, and there is no shared position channel.
- Unseen gunshots leave a brief (~0.5 s) semi-transparent **sound ring** near the
  muzzle, deterministically **offset up to ~20 px** — it tells you someone fired
  *roughly there*, never the exact spot, never which team.
- No global flag tracking. Dead players spectate as ghosts (inputs ignored, see whole
  map).

## Combat

- **`hitPoints` = 3 per life.** Each hit removes 1; at 0 you die; HP resets to full on
  respawn.
- Press **A** to fire (there is a cooldown between shots — not continuous fire).
- **Windup:** firing has a `fireWindupTicks` = 5 (**~0.2 s**) windup — the aim
  **locks at the trigger pull**, and the bullet leaves at the end of the windup. A
  target that ducks back behind cover before release survives.
- **Bullet = hitscan** along the locked aim ray: it hits the **first player whose
  footprint crosses its narrow corridor** (~14 px half-width in the baseline), never
  passes through a body, and is **stopped by walls**. Range is effectively map-wide
  (`gunRange` = 1300 px).
- **Friendly fire is ON** — a shot hits the first valid target regardless of team.
- **Same-tick shots resolve simultaneously** against the same snapshot (mutual duels
  kill both; no input-order advantage).
- Brief **spawn protection** (`spawnProtectTicks` = 24, ~1 s invulnerability) on
  respawn.

## Lives & respawn

Each player has a fixed number of **`lives` = 3**. On death you respawn at your home
edge after `respawnTicks` = 72 (~3 s). When your lives run out you are out for the
round.

## Flags

- Each flag sits on its home pedestal. **Touch the ENEMY flag to steal it**; you
  cannot interact with your own flag.
- Carrying the flag makes you **slower** (`carrierSpeedPct` = 70, ~70% speed) but you
  can **still shoot**.
- If the carrier is killed or disconnects, the flag **returns instantly to its own
  pedestal**. A flag is never loose on the ground — it is always either on a pedestal
  or carried.
- Your own flag's state is always observable (empty pedestal = stolen), but the thief
  carrying it is fogged unless in your cone/bubble.

## Winning & scoring

The round ends immediately on either:
1. **Capture** — carry the enemy flag into your own home capture zone; or
2. **Wipe** — the entire enemy team is out of lives.

Otherwise, at the time limit (`maxTicks`), tiebreak by: most **total lives
remaining** → **closest flag progress toward home** → **draw**.

**Scoring is sparse and win-only:** the winning team gets **+100** to every player;
losing team and draw get **0**. Kills/deaths/captures are recorded in the results but
**award no points**. The whole objective is team victory (capture or wipe).

## Tuning defaults (config.json / manifest)

| Parameter | Default | Meaning |
|---|---|---|
| players | 16 (8v8) | `num_agents` / `minPlayers` = 16 |
| `lives` | 3 | lives per player per round |
| `hitPoints` | 3 | HP per life |
| `respawnTicks` | 72 (~3 s) | respawn delay |
| `spawnProtectTicks` | 24 (~1 s) | post-respawn invulnerability |
| `gunRange` | 1300 px | effectively map-wide |
| `fireWindupTicks` | 5 (~0.2 s) | aim locks at pull, bullet leaves after windup |
| `fireCooldownTicks` | 12 (~0.5 s) | between shots |
| `carrierSpeedPct` | 70 | flag carrier speed (% of normal) |
| `aimTurnRate` | 5 brads/tick | ~7°/tick; full turn ~2.1 s |
| `visionConeDeg` | 45 | forward cone **half-angle** |
| `visionBubble` | 90 px | omnidirectional vision radius |
| `startWaitTicks` | 120 | lobby countdown |
| `gameOverTicks` | 360 | game-over tail |
| `maxTicks` | 10000 | round time limit (0 = no limit) |
| map | 1235 × 659 | arena size, center (617, 329) |
| `seed` | 679961 | default map/game seed |

Controls (browser): D-pad = move, **A** = fire, **B** (or X / K) = rotate aim CCW,
**Select** (or Space / L) = rotate aim CW.

---

## How a policy plugs in — the Sprite-v1 protocol

A CTF policy speaks the shared **BitWorld Sprite v1** protocol. Authoritative spec:
`https://github.com/Metta-AI/bitworld/blob/master/docs/sprite_v1.md` (also on this
machine at `~/coding/bitworld/docs/sprite_v1.md`). The runner starts every policy with
a **`COWORLD_PLAYER_WS_URL`** environment variable; the policy connects to that
websocket, plays until the game ends, and exits when the runner stops it. A slot's URL
looks like `ws://host:port/player?slot=$i&token=0xBADA55_$i` — **slot parity is your
team; `slot div 2` is your seat.**

**Perception (server → client):** the engine streams a binary render stream of
**sprite definitions** (id → width/height/**label**/compressed RGBA pixels) and
**object placements** (object id at x,y,z,layer,sprite id). The map object sits at
(0,0), so **object x,y are map coordinates directly**. Perception is done by **sprite
label lookup** — the baseline reads labels like `"self <color> right|left"` (own
avatar; absent when dead), `"player <color> right|left"` (visible players), `"aim dot
<color>"` (aim readback), `"<color> flag"` (flag state), `"fire icon"` (gun ready),
and the `"walkability map"` sprite (decoded into a nav mask). The SDK bridge accumulates
this stream but does **not** decompress pixels or resolve palettes — decoding labels /
the walkability mask is the policy's job (see the SDK notes below).

**Input (client → server):** each world-changing frame, the policy emits a single
**8-bit gamepad button mask**. Button bits: `UP=1, DOWN=2, LEFT=4, RIGHT=8,
SELECT=16, A=32, B=64`. So: d-pad = move, **A** = fire, **B** = aim CCW, **Select** =
aim CW. Send only when the mask changes (the server holds the previous mask).

### The Player SDK (Python) — the recommended build path

The shared **`players.player_sdk`** package (imported from the `Metta-AI/coworld-tools`
monorepo; see the root README and `pyproject.toml`) provides a **SpriteV1 bridge** that
is the cleanest way to write a new Python policy:

```python
import asyncio
from players.player_sdk import (
    env_ws_url, run_sprite_bridge, Button, SpriteWorld, SpriteContext,
)

def decide(world: SpriteWorld, ctx: SpriteContext):
    # world.sprites / world.objects hold the accumulated scene (query by label).
    # Decode perception, decide, then return a button mask:
    return Button.UP | Button.A          # or (mask, "chat text"), or None to hold

asyncio.run(run_sprite_bridge(env_ws_url(), decide, max_size=None))
```

- `env_ws_url()` reads `COWORLD_PLAYER_WS_URL` (canonical; legacy fallback
  `COGAMES_ENGINE_WS_URL`) and returns the URL verbatim (slot/token already encoded).
- `run_sprite_bridge(url, decide, ...)` owns connect, per-frame dispatch, mask/chat
  packing, and **exit-0-on-clean-close**. Pass `max_size=None` — sprite frames can be
  large.
- `decide(world, ctx)` is called once per world-changing frame and returns an
  `int`/`Button` mask, a `(mask, chat)` tuple, or `None` (hold previous). Sync or async.
- A Sprite-v1 player needs **no SDK extras** (base deps numpy/pydantic/websockets/
  cramjam suffice); `[bedrock]` is only for LLM-via-Bedrock policies.
- The best worked reference is Crewrift's **`crewborg`** (in coworld-tools
  `players/players/crewrift/crewborg/`, and vendored in `crewrift_lab/crewrift/crewborg/`)
  — borrow its perception decoder (`perception/`, uses `cramjam.snappy` to decode sprite
  alpha masks), its d-pad movement controller (`action.py`), and its perceive → belief →
  strategy → modes → action architecture. Heartleaf's **`cady`** (`heartleaf_lab/cady/`)
  is a smaller, from-scratch example that actually uses `run_sprite_bridge` — the closest
  structural model for a new Sprite-v1 SDK player.

### The baseline (Nim) — the reference bot to beat

`players/baseline/` in the game repo is a **strong, fully-featured Nim policy**
(`baseline.nim`, ~1440 lines) and the natural comparison target. It implements the
Sprite-v1 loop (`runBot`) and a per-frame policy (`decide`): perception via label
lookups + persistent enemy **tracks** (position/velocity/last-seen, TTL ~5 s); a
deterministic **role per team-seat** (rushers, flankers, an overwatch sniper, a home
defender); navigation on an eroded 8px grid with a **Dijkstra cost field** that adds
soft exposure cost for cells a remembered enemy can shoot; peek/duck/serpentine micro;
and a turret controller that composes the 8-bit mask (movement octant + B/Select to
close the shortest aim arc + A only on a fresh press behind a geometric fire gate,
never rotating on the pull tick so the locked aim is settled). Its tuning constants
(`baseline.nim:79–149`) are the knobs — note `AimRate=5` must equal the server's
`aimTurnRate`.

---

## Reading replays

`tools/expand_replay.nim` in the game repo re-simulates a `.bitreplay` through the CTF
sim and emits a **structured event timeline**: `PlayerJoined, PhaseChanged, Kill,
FlagSteal, FlagReturnHome, Capture, Respawn, ScoreChanged, GameOver`, each with tick,
actor/victim slot+label, phase, score delta, flag team, winner/draw. It has three
renderers — human text, event-log keys, and **JSON rows** (`{ts, player, key, value}`)
suitable for machine analysis. Because it validates a per-tick hash, it must be built
from the **same game version that recorded the replay**; the lab's
`tools/build_expand_replay.sh` builds a host-native, version-matched binary (see that
script; the pinned `CTF_REF` must match the deployed league game — a `hash failed` on a
*fresh* replay is the signal to bump it).

---

## Strategy notes (starting intuitions — to be replaced by evidence)

These are prior intuitions from the ruleset, not measured findings; the loop will
confirm or kill them.

- **Aim is vision.** Because the ±45° vision cone rides your aim, where you point is
  both your gun and your eyes. A policy that only aims at movement targets is blind to
  its flanks; a policy that sweeps aim to scan trades away shot readiness. This
  tension is likely the richest tuning surface.
- **Win-only scoring means team play, not K/D.** Kills are instrumental (enable a
  capture or a wipe), never the point. A bot that farms kills but never captures/escorts
  scores exactly 0. The two win paths — capture and wipe — should both be first-class.
- **The flag carrier is a fragile, slow, high-value asset.** Killing a carrier returns
  the flag instantly. Escorting your own carrier and hunting the enemy carrier (whom you
  can't see through fog until they enter your cone) are both core.
- **Cover-dense map + hitscan + windup ⇒ peek-fire-duck.** No straight sightline
  crosses the field; the windup lets a target duck. Corner discipline and pre-aiming
  likely dominate raw reflex.
- **No team radio.** Coordination must be emergent from a shared deterministic role/
  plan (like the baseline's seat-based roles), not communicated — chat exists in the
  protocol but the game gives no team channel.
