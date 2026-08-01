# CTF — game reference

The **self-contained** gameplay reference for **Coworld CTF**, a two-team
capture-the-flag shooter on the **BitWorld Sprite-v1** protocol. Read this to build
a mental model of the game before reasoning about play or setting direction — you
rarely need to leave the lab.

The **authoritative source** is the game repo `Metta-AI/coworld-ctf` (Nim server
`src/ctf.nim` + `src/ctf/`, baseline player `players/baseline/`, rules
`docs/RULES.md`), cloned for reference at **`~/coding/coworlds/coworld-ctf`**. If this
doc and the repo disagree, the repo wins — treat the mismatch as a finding and
reconcile it. **But "the repo" means the *deployed* ref, and the *league's* config:**
league episodes run the manifest's **Default variant** `game_config`, which overrides
`config.json` where they differ (notably `visionConeDeg`: the variant says **45**,
`config.json` says 60 — episodes run **45**). To verify what's live, read a fresh
episode's `episode.json` (`coworld_version` + full `game_config`) or `coworld show
<cow_id> --json`. **Deployed at last audit (2026-07-23): ctf 0.7.69 = repo commit
`72fb1b1` (GameVersion 21).** CTF is a **fork of Crewrift** and keeps
Crewrift's continuous 2D movement, line-of-sight, Sprite-v1 protocol, websocket
server, and replay infrastructure; it replaces the social-deduction layer (roles,
tasks, voting) with **teams, guns, flags, and fog-of-war vision**.

Engine tick rate: **24 ticks/sec**.

---

## The game in one paragraph

Two teams of eight (**Red** on the left edge, **Blue** on the right) spawn in a
symmetric, cover-dense arena, each guarding a flag (drawn as a **heart** since 0.7.0)
on a home pedestal. You **move** with the d-pad, **aim** a continuous per-player angle
(decoupled from movement), and **shoot** an instant hitscan gun. Vision is
**fog-of-war**: the static map is always visible, but enemies only appear inside your
**forward vision cone** (±45° around your aim in league play, unlimited range, blocked
by walls) or a small **omnidirectional bubble** (~90px). Pickups dot the arena —
grenades, med kits, shields, plasma arcs — and players can **shout** short messages
heard nearby. Steal the enemy flag and carry it into your home capture zone — or wipe
the enemy team — to win. **Scoring is win-only: +1 to every winner, -1 to every loser
on a decisive round (capture or wipe); a time-limit draw is -1 for EVERYONE**
(GameVersion 21 — stalling out the clock is never better than losing). Kills, deaths,
and captures are recorded but award no points, so the objective is purely **team
victory before the clock**.

---

## Arena & teams

- **Map:** symmetric, **1235 × 659 px**, center **(617, 329)**, mirror line x = 617.
  Dense staggered cover (offset wall stubs, diamonds, discs) mirrored across the
  vertical axis — **no straight sightline crosses the field**; every approach is a
  series of corners. `mapPath: "arena"` (procedurally generated). GameVersion 16
  reshaped it: the midline chevrons became a **square-bracket wall pair framing the
  flag ring**, and the column-3 discs were thinned to every other disc. **Glass
  windows** (GameVersion 15): the second stub from the top and bottom of each half's
  outer stub column, plus the middle of each bracket bar on the center row, block
  movement and bullets like stone but **pass vision** — cover you can be seen behind
  is not cover. A **second map exists** (`arena-large`, 1606×858, gunRange 1690) in
  the multi-map registry — the league still deploys `arena`; a `mapPath` flip
  requires a full geometry rebake (see WORKING_CONTEXT watch items).
- **16 players, 8 v 8.** Team is assigned by **slot parity**: **even slot = Red**
  (left), **odd slot = Blue** (right). Seat within a team = `slot div 2` (0–7).
- **Player identities** (0.7.69): each seat gets a fixed Greek identity `alpha`…`theta`
  by slot order within the team — deterministic across matches. A badge object labeled
  `identity <color> <name>` rides each living player's sprite, fog-gated with the
  player: seeing a player means seeing who it is.
- **Geometry landmarks** (baseline README): capture zones roughly `x ≤ 206` (Red home)
  and `x ≥ 1029` (Blue home); pedestals at **(186, 329)** Red / **(1049, 329)** Blue.
- **Phases:** Lobby → Playing → GameOver (`startWaitTicks` lobby countdown, then play
  until a win condition or the time limit, then a `gameOverTicks` tail).

## Movement

Continuous — acceleration, friction, max speed, wall-sliding — driven by the
**d-pad** (Up/Down/Left/Right, combinable into 8 octants). Movement is **pure
locomotion**: it *never* changes your aim or your vision. You see where you point, not
where you walk. **Player bodies are solid** (GameVersion ~14): you cannot drive
through another live player, friend or foe — contact is a slightly elastic collision
(`playerBouncePct` = 40% restitution); glancing contact slides around the body like
wall-sliding. Corpses never block.

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
- **The old floating aim-dot indicator is retired** (0.7.8 renderer restore): a
  player's facing is shown by the soldier sprite itself — the held gun sweeps to the
  aim angle, and the sprite label reports a coarse `right`/`left` side. For anyone you
  can see, the lane their body faces is exactly where they can shoot.

## Vision / fog-of-war

- The **full static map is always drawn** (terrain is permanent knowledge). Moving
  entities are fogged.
- Your vision = a **forward cone**, half-angle `visionConeDeg` (**±45° in league
  play** — the manifest's Default-variant `game_config`, confirmed in live episode
  configs; the repo's `config.json` says 60, but the variant wins) around your
  **aim**, **unlimited range**, **plus** a small **omnidirectional bubble**
  `visionBubble` (default **~90 px**). **Stone walls block vision** (the same walls
  block bullets) — but **glass windows pass vision while blocking bullets** (see
  Arena above).
- **Always visible regardless of fog:** the static map, **both flag pedestals**, your
  **own flag's state** (an empty own pedestal = it's been stolen — but the thief is
  fogged), and **yourself** (a distinct self marker).
- **Teammates ARE fogged — there is no team radio.** You cannot see allies unless they
  fall in your cone/bubble, and there is no shared position channel.
- **Sound marks landings, not muzzles.** Firing itself is silent; every shot leaves
  every living player a brief (~0.5 s) **impact ring** (label `shot impact`) near
  where the bullet *landed*, deterministically **offset up to ~20 px** — audible
  through walls and fog, team-anonymous, never the shooter's position. Grenade blasts
  leave a similar `grenade sound` ring. **Bullets themselves are invisible to
  players** — tracers and muzzle flashes are spectator/replay rendering only.
- No global flag tracking. Dead players spectate as ghosts (inputs ignored, whole
  map unfogged, corpses visible — labeled `corpse <color> <side>` so they never read
  as live soldiers). NOTE: the game repo's RULES.md claims death no longer lifts the
  fog, but the deployed renderer (0.7.69/`72fb1b1`, `buildSpriteProtocolPlayerUpdates`)
  draws ghost viewers no fog overlay and all players — the code wins.

## Combat

- **`hitPoints` = 3 per life.** Each hit removes 1; at 0 you die; HP resets to full on
  respawn.
- Press **A** to fire (there is a cooldown between shots — not continuous fire).
- **Windup:** firing has a `fireWindupTicks` = 5 (**~0.2 s**) windup — the aim
  **locks at the trigger pull**, and the bullet leaves at the end of the windup. A
  target that ducks back behind cover before release survives.
- **Bullet = hitscan** along the locked aim ray: it hits the **first player whose
  footprint crosses its narrow corridor** (8 px half-width, `BulletHalfWidth`), never
  passes through a body, and is **stopped by stone walls and glass alike**. Range is
  effectively map-wide (`gunRange` = 1300 px on `arena`; per-map since 0.7.69).
- **Cover is partial, not binary** (GameVersion 20): the target's body is sampled
  across its silhouette — only the part both inside the bullet corridor AND visible
  from the shooter can be hit. A corner-hugger showing a sliver is exactly as hittable
  as that sliver; the poking shoulder is fair game even when the center is covered.
- **Friendly fire is ON** — a shot hits the first valid target regardless of team.
- **Same-tick shots resolve simultaneously** against the same snapshot (mutual duels
  kill both; no input-order advantage).
- **NO spawn protection** (removed in GameVersion 20): a freshly respawned player can
  shoot and be shot (and blocks bullets) from their first tick.

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

## Items & shouts

All pickups are taken by **touch**, are **fog-gated** (visible only where you have
vision), never block movement/bullets/sight, and respawn at a fixed spot after their
interval. Carried items are **lost on death** (nothing drops). Full mechanics:
RULES.md at the deployed ref; the numbers are in the tuning table below.

- **Grenades** (4, one per arena corner; refill 5 s): hold **C** to charge, release
  to throw along your aim — a lob **over every obstacle** up to ~247 px, bursting a
  fixed ~0.4 s after release. Blast (~52 px radius) removes 2 hp from *everyone*
  inside — enemies, teammates, the thrower. Throwing is silent; an unseen landing
  leaves a jittered `grenade sound` ring. One carried grenade max.
- **Med kits** (2, on the center line; respawn 30 s): touching one while hurt heals
  to full; a healthy player walks over it untouched.
- **Shields** (2, one deep in each endzone, bottom half; respawn 30 s): pickup heals
  +3 (up to a **6 hp ceiling**) and raises your ceiling to 6, but your fire cooldown
  triples while carried.
- **Plasma arcs** (2, side back columns, top half; respawn 30 s): while carried, **A**
  ignites a forward cone (136 px reach, 68 px tip width) instead of the gun — 3 hp
  per touch (lethal to a bare cog), 5-tick burn, 20-tick reset, needs line of sight,
  hits teammates too.
- **Shouts**: any living player can send a ≤10-char chat message; everyone (both
  teams) within ~247 px hears it as a bubble labeled `<team> shout <player>: <text>`
  at jittered (~±20 px) coordinates. One shout/second; bubbles fade after 3 s. This
  is the only in-game communication channel — short-range and public.

## Winning & scoring

The round ends immediately on either:
1. **Capture** — carry the enemy flag into your own home capture zone; or
2. **Wipe** — the entire enemy team is out of lives.

Otherwise, at the time limit (`maxTicks` = 5000, ~3.5 min), the round is a
**lose-lose draw** — **there is no tiebreak** (the old lives-remaining → flag-progress
tiebreak was removed in the 0.7.6x era).

**Scoring is sparse and win-only** (GameVersion 21):
- **Decisive round** (capture or wipe): every winner **+1**, every loser **-1**.
- **Time-limit draw: -1 for BOTH sides** — running out the clock is never better
  than losing, so stalling has no upside for anyone.
- **Mutual-wipe draw** (both teams eliminated same tick): 0 for both.

Kills/deaths/captures are recorded in the results but **award no points**. The whole
objective is team victory (capture or wipe) **before tick 5000**.

## Tuning values (league Default-variant `game_config`, verified vs live episodes)

| Parameter | League value | Meaning |
|---|---|---|
| players | 16 (8v8) | `num_agents` / `minPlayers` = 16 |
| `lives` | 3 | lives per player per round |
| `hitPoints` | 3 | HP per life (6 while carrying a shield) |
| `respawnTicks` | 72 (~3 s) | respawn delay |
| spawn protection | **none** | removed GameVersion 20 — live from first tick |
| `gunRange` | 1300 px | per-map since 0.7.69 (`arena-large`: 1690) |
| `fireWindupTicks` | 5 (~0.2 s) | aim locks at pull, bullet leaves after windup |
| `fireCooldownTicks` | 12 (~0.5 s) | between shots (3x while carrying a shield) |
| `carrierSpeedPct` | 70 | flag carrier speed (% of normal) |
| `playerBouncePct` | 40 | player-player collision restitution (bodies solid) |
| `aimTurnRate` | 5 brads/tick | ~7°/tick; full turn ~2.1 s |
| `visionConeDeg` | 45 | forward cone **half-angle** (variant; `config.json` says 60 — variant wins) |
| `visionBubble` | 90 px | omnidirectional vision radius |
| `startWaitTicks` | 120 | lobby countdown |
| `gameOverTicks` | 360 | game-over tail |
| `maxTicks` | **5000** (~3.5 min) | round time limit → lose-lose draw (was 10000 pre-0.7.66) |
| map | 1235 × 659 | `arena`; `arena-large` (1606×858) exists but is not deployed |
| `seed` | 679961 | default map/game seed |

Item tuning (sim.nim constants at the deployed ref): grenade blast radius 52 px /
2 hp damage / corner pickups refill 5 s; med kits ×2 on the center line, heal to
full, respawn 30 s; shields ×2 (endzone back columns, bottom half), 6 hp ceiling +
3x slower fire, respawn 30 s; plasma arcs ×2 (side back columns, top half), forward
cone 136 px reach / 68 px tip width / 3 hp per touch / 5-tick burn / 20-tick reset,
respawn 30 s; shouts ≤10 chars, heard within ~247 px (map width / 5), 1/s rate limit.

Controls (browser): D-pad = move, **A** = fire (plasma cone while carrying an arc),
**B** (or X / K) = rotate aim CCW, **Select** (or Space / L) = rotate aim CW, **C** =
hold to charge a grenade throw, Enter = shout.

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
label lookup** — key labels at 0.7.69: `"self <color> right|left"` (own avatar; absent
when dead), `"player <color> right|left"` (visible players), `"identity <color>
<name>"` (per-player Greek identity badge, fog-gated), `"<color> flag planted"` (flag
on its pedestal) vs `"<color> flag"` (centered on its carrier), `"fire icon"` /
`"fire icon cooldown"` (gun readiness), `"hp N/M"` (overhead HP pips), item labels
(`"grenade"`, `"med kit"`, `"shield"`, `"plasma arc"`, carried variants like
`"grenade carried"`), sound rings (`"shot impact"`, `"grenade sound"`), shout bubbles
(`"<team> shout <player>: <text>"`), `"corpse <color> <side>"` (ghost view only), and
the `"walkability map"` sprite (decoded into a nav mask). The old `"aim dot"` readback
is retired (0.7.8 renderer restore) — read facing from the self sprite's coarse
right/left instead, or dead-reckon the aim. The SDK bridge accumulates this stream but
does **not** decompress pixels or resolve palettes — decoding labels / the walkability
mask is the policy's job (see the SDK notes below).

**Input (client → server):** each world-changing frame, the policy emits a single
**8-bit gamepad button mask**. Button bits: `UP=1, DOWN=2, LEFT=4, RIGHT=8,
SELECT=16, A=32, B=64, C=128`. So: d-pad = move, **A** = fire, **B** = aim CCW,
**Select** = aim CW, **C** = charge/release a grenade throw. Send only when the mask
changes (the server holds the previous mask). NOTE: the SDK `Button` enum stops at B —
beacon widens the bridge's 7-bit mask clamp to 0xFF in `main.py` to reach C. Shouts go
out as a chat packet (`0x81`), e.g. the `(mask, "text")` return from `decide`.

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
  still loses points. The two win paths — capture and wipe — should both be first-class.
- **The clock is an opponent** (GameVersion 21): a timeout draw pays -1 to *everyone*,
  same as losing. Banking lives has no terminal value — preserved strength must be
  *converted* into a capture or wipe before tick 5000. "Play safe and hold" is only
  half a strategy; the other half is a convert trigger.
- **The flag carrier is a fragile, slow, high-value asset.** Killing a carrier returns
  the flag instantly. Escorting your own carrier and hunting the enemy carrier (whom you
  can't see through fog until they enter your cone) are both core.
- **Cover-dense map + hitscan + windup ⇒ peek-fire-duck.** No straight sightline
  crosses the field; the windup lets a target duck. Corner discipline and pre-aiming
  likely dominate raw reflex. Cover is partial (GameVersion 20): the exposed sliver
  of a corner-hugger is hittable, so *how much* body you show matters, not just
  whether you're "behind" cover.
- **Limited team radio: shouts.** Coordination rests on shared deterministic
  roles/plans (like the baseline's seat-based roles) plus the **shout channel** —
  ≤10 chars, heard within ~247 px by BOTH teams at jittered coordinates. Short-range,
  public, and rate-limited, but real (beacon's v22+ leader orders ride it).
