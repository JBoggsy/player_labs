# Paintbot — the game, self-contained

The lab's game reference: rules, variants, procedural maps, mechanics, the wire
contract, and strategy notes — enough to reason about play without leaving the
repo. Authoritative sources: the **`Metta-AI/coworld-ctf`** repo (paintbot and
CTF are the *same Nim binary*; clone at `~/coding/coworlds/coworld-ctf`, server
`src/ctf/`, rules `docs/RULES.md`, manifest `coworld_manifest_paintbot.json`)
and the deployed league game (paintbot **0.7.178** at lab creation, 2026-08-03).
The full recon with `file:line` citations:
[`recon/paintbot-2026-08-03.md`](recon/paintbot-2026-08-03.md).

## One paragraph

Paintbot is CTF's expanded sibling on the **BitWorld Sprite-v1** protocol: a
top-down paintball shooter where teams guard a **heart** (CTF's flag, reskinned)
on a pedestal inside their **endzone**. You move with the d-pad, aim a
continuous angle *decoupled from movement* (B/Select rotate; 5 brads/tick),
and shoot an instant hitscan paintball gun (A). Vision is fog-of-war (aim-riding
cone + small omni bubble; walls block). What paintbot adds over the CTF league:
**2-or-4 teams** (red/blue/green/yellow), **procedurally generated maps** in
five size classes, **pot scoring**, and **capture-eliminates-team** hearts —
steal any rival's heart and carry it into *your* endzone to knock that team out
of the game; **last team standing wins**. Paint itself is cosmetic (board-only
splatter; no territory scoring).

## Variants (deployed manifest, verified live)

Every episode seats **four entrant policies** (nominally — live seating pads
with fillers; see below). All variants: `lives 3`, `hitPoints 3`,
`respawnTicks 72`, `carrierSpeedPct 70`, `maxGames 1`, seed randomized
per-episode from OS entropy (the manifest's `679961` is the "unpinned"
sentinel).

| variant | seats | teams | map | scoring | maxTicks | vision cone | agents per policy |
|---|---|---|---|---|---|---|---|
| `default` | 16 | 2 | **fixed classic arena** (1235x659) | classic +1/-1 | 5000 | ±60° | ~8 (2 main entrants) |
| `2v2` | 16 | 2 | generated (size drawn) | pot **+2/-2** | 5000 | ±60° | 4 (each team split between 2 policies) |
| `4ffa` | 16 | 4 | generated (size drawn) | pot **+4/-1/-1/-1** | 5000 | ±60° | 4 (one policy per team) |
| `4ffa8` | 32 | 4 | generated, **locked giant** | pot +4/-1/-1/-1 | **7500** | **±45°** | 8 (one policy per team) |

- **There is no "1v1" variant** — the near-1v1 experience is `default` (two
  main entrants each owning ~a team, i.e. plain CTF under the paintbot name).
- **Episodes are scheduled by the CAMPAIGN, not a ladder rotation** (next
  section): the observed variant mix per round (~half `default`) reflects
  which territory cells are being fought over, not a scheduler.
- **Live seating decodes as campaign rosters**: 7+7+1+1 on a 16-seat map is a
  2v2-mode battle (two captains + one mirrored ally each, repeats
  filler-marked); clean 4x4 / 4x8 are ffa4-mode battles. **A policy must
  handle owning anywhere from 1 to 8 of its team's seats and treat unknown
  same-team seats as allies.**
- Time-limit draw pays **-1 to every player** (GV21); mutual wipe = 0/0.

## The campaign (territory) league — how games are actually scheduled

The live Paintbot league does **not** run a ladder: it runs metta's **campaign
round brain** (spec 0075; league settings hold ladder XOR campaign — verified
live via `GET /v2/leagues/{id}/campaign`, `enabled: true`). The war model:

- A **10x10 board of 100 cells**, 4-neighbor adjacency. Players enter by
  **airdrop** and expand by **invading adjacent cells** (max 3/round, one
  round every **600s**). Standings = **territory** (cells owned) — the
  division "score" leaderboard IS cell count.
- **Each cell permanently owns a map**: at board creation it is stamped a
  variant (`map_ref` — live mix 29x 4ffa8 / 26x 4ffa / 25x default /
  20x 2v2), a persistent **terrain seed** (`map_seed` — *"a cell IS a map"*),
  and a **size class** (40 standard / 25 large / 14 small / 14 huge /
  7 giant). Episodes fought over a cell pin the **target cell's**
  `mapSeed`+`mapSize` into the game config (the deployed manifest declares
  both knobs), so **the same cell replays the same generated terrain every
  round** — defense is always on your own fixed map; assaulting a cell
  replays its map every attempt. The per-episode `seed` still varies
  (respawn/RNG), only terrain is pinned.
- **Battle modes** derive from the cell's variant: 2-team variants
  (`default`, `2v2`) fight **2v2** (attacker + defender captains with
  mirrored allies; both seatings played, captains swapped); 4-team variants
  fight **ffa4** (≤4 policies: attackers, defender, ex-owner recruits,
  filler). Stakes: attacker sweep takes the cell; defender sweep takes the
  attacker's staked source; split = status quo.
- **An LLM strategist (claude-sonnet-5) plays commander** for each player —
  it picks *where* to fight each round, steered by the player's **private
  standing-orders prompt** (settable via the campaign API / newer
  `coworld campaign set-prompt`). The policies decide who wins the battles.
  A paintbot competitor is therefore policy + commander prompt.
- The board's 100 `(map_ref, map_seed, map_size)` triples are public API data
  and the generator is deterministic public code — **every cell's exact
  terrain can be regenerated offline** for per-cell preparation. (The policy
  still can't read seeds from the wire; in-game it can only *recognize* maps.)

## Multi-team rules (the 4-team layer)

- Colors are always a prefix of red, blue, green, yellow. **Seats deal round
  the teams by slot order** (`team = slot mod teams`, seat = `slot div teams`);
  identities stay per-team (alpha..theta).
- Every team has its own heart + endzone. **Capturing a heart eliminates that
  team** (GV32: all its players die for good; the heart is out of play). A team
  wiped by kills retires its heart on the spot (GV33), even off a carrier's
  back.
- **Allies do not exist** — 4-team play is pure FFA ("2v2" is two policies
  splitting one classic team's seats).
- **Last team standing wins**: captures and wipes mix freely.
- 4-team maps are square, `corners` (diagonal endzone thresholds) or `plus`
  (arm-mouth endzones at edge midpoints) layouts, terrain replicated by
  90° rotation so all four quarters are exactly fair.
- Items on 4-team boards: a rot90-fair med-kit diamond of four; one shield and
  one spray-can pickup near each endzone; four grenade pickups at edge
  midpoints (corners) or a rot90 orbit (plus).

## Procedural maps

Generated in `src/ctf/arena.nim` (splitmix64, fully deterministic per seed;
generate → validate → retry seed+1). What a policy must absorb:

- **Size classes** `small/standard/large/huge/giant` = 0.85/1.0/1.3/1.8/2.6 x
  the base shell — 2-team: 1235x659 scaled (1050x560 … **3211x1713**); 4-team:
  square 960 scaled (816 … **2496**). Drawn uniformly unless the variant pins
  `mapSize` (only `4ffa8`: giant).
- **Terrain**: vertical obstacle columns from families (stubs / diamonds /
  discs / chevrons), trenches, a center feature (bracket/ring/walls), glass
  windows (vision passes, bullets don't), plugged sightlines. Validators
  enforce cover density 40-170‰, no open horizontal sightline, corridors
  ≥26px, full connectivity.
- **Endzones**: 2-team = classic `column` (half the pool) or compact
  `square`/`disc`; 4-team = `corner`/`arm`.
- **The seed is never on the wire** — a policy cannot regenerate the map. It
  must read the map from the observation (below). Replays DO carry the exact
  geometry (`mapSpec`), so post-hoc tools can reconstruct terrain.
- `gunRange` is fixed (GV34) — bigger maps do NOT extend the gun.
- Grenade max range and shout radius scale with the map (`mapWidth/5`).

## What the wire tells you (the whole map contract, at t=0)

The init snapshot states everything about terrain; fog hides only entities:

1. **`walkability map` sprite** — full-map RGBA (snappy raw-block compressed),
   alpha>0 = walkable, always 1x map pixels. *The* nav source.
2. **`game teams <n> map <w>x<h>`** marker — team count and exact map size.
3. **`endzone <color> <shape> <x0>,<y0> <x1>,<y1>`** markers — one per team,
   shape ∈ {column, square, disc, corner, arm}. (Spectator streams also carry
   `endzone <color> power <n>` glows — match the shape token.)
4. `Room <color> Base` markers; per-color **`team score <COLOR> <k>/<d>`**
   chips (fog-independent, every frame — the wipe clock).
5. Planted hearts (`<color> flag planted`) **never fog** — pedestal positions
   are readable from the first frame. A carried heart (`<color> flag`) is as
   visible as its carrier.
6. **Not on the wire**: variant id, game name, seed, scoring rule, muster.
   Distinguish `default` vs `2v2` only by geometry (fixed 1235x659 vs
   generated); infer seats-per-team (4 vs 8) from teams + map size.

Protocol deltas from Sprite-v1 (shared with CTF): input bit 7 = **C** (hold to
charge a grenade throw — the SDK bridge's 7-bit clamp must be widened);
`own aim <brads>` readback marker; do NOT send Player Ready in league play; map
camera object (id 1) present ⇔ match running; player stream is 1x.

## Mechanics carried over from CTF (unchanged)

- Movement 2.75 px/tick per axis (diagonal √2 faster); carrier at 70%.
- Aim: 256 brads/turn, 5 brads/tick turn rate; 16-step sprite readback.
- Gun: hitscan, 5-tick windup (aim locks at pull; don't strafe through it),
  12-tick cooldown, aim jitter grows to 80% at max range, friendly fire ON
  (first body on the ray eats the bullet).
- Vision: cone (±60° paintbot / ±45° on 4ffa8) riding the aim + 90px bubble.
- Items: med kits (heal), shields (6hp, 3x slower fire), grenades (C charge,
  52px blast), spray can ("plasma arc": 170px cone, 85px max width, damage 3,
  5 active + 20 reset ticks, body-disc hit test; REPLACES the gun while held).
  Heart carriers fire 3x slower (GV26).
- Shouts: ≤10 ASCII chars, audible mapWidth/5 through walls/fog, ±20px jitter,
  1/s, sender anonymized to the per-team slot letter.
- Sound rings: shot impacts / grenade blasts audible map-wide, ±20px jitter,
  team-anonymous.

## Strategy notes (start of the lab's thinking)

- **Win-only scoring still rules**: kills are instrumental. Pot scoring makes
  4-team wins big (+4) and every non-win identical (-1, draw included) — never
  stall.
- **Elimination is a resource**: capturing any heart removes a whole team.
  In FFA, letting two rivals fight and finishing the weakened one is real;
  third-party dynamics matter (beacon's lineage never faced them).
- **The fixed arena still pays** (~half of live episodes today) — but a
  uniform online-nav player handles it as just another wall mask.
- **Roster uncertainty**: your policy may own 1..8 seats of a team; deterministic
  seat-keyed conventions (roles, item claims, squads) must degrade gracefully
  when other seats are strangers.
- The Nim `baseline` (in-repo) handles all variants with purely online nav
  (8px grid, Dijkstra repath every 10 ticks) — proof of feasibility and the
  reference opponent; its known gap: no overwatch/home-defender roles on
  4-seat teams.
