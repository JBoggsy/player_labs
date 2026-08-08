# Paintbot — the game, self-contained

The lab's game reference: rules, variants, procedural maps, mechanics, the wire
contract, and strategy notes — enough to reason about play without leaving the
repo. Authoritative sources: the **`Metta-AI/coworld-ctf`** repo (paintbot and
CTF are the *same Nim binary*; clone at `~/coding/coworlds/coworld-ctf`, server
`src/ctf/`, rules `docs/RULES.md`, manifest `coworld_manifest_paintbot.json`)
and the deployed league game (paintbot **0.7.211**, source
`9dedac0ed6011aeca92bf2c6403b0e70c955f461`, verified 2026-08-07,
**GameVersion 41**). Re-resolve the canonical game before relying on these live
values; Paintbot redeploys frequently.
The full recon with `file:line` citations:
[`recon/paintbot-2026-08-03.md`](recon/paintbot-2026-08-03.md); the GV41
barrage/puddle recon is
[`recon/paintbot-gv41-hazards-2026-08-07.md`](recon/paintbot-gv41-hazards-2026-08-07.md).

## One paragraph

Paintbot is CTF's expanded sibling on the **BitWorld Sprite-v1** protocol: a
top-down paintball shooter where teams guard a **heart** (CTF's flag, reskinned)
on a pedestal inside their **endzone**. You move with the d-pad and aim a
continuous integer-brad turret *decoupled from movement*. A full turn is 256
brads; every deployed variant sets `aimTurnRate=5`, so B/Select rotates
5 brads / 7.03125 degrees per held tick. A fires the hitscan paintball gun.
Vision is fog-of-war (aim-riding
cone + small omni bubble; walls block). What paintbot adds over the CTF league:
**2-or-4 teams** (red/blue/green/yellow), **procedurally generated maps** in
five size classes, **pot scoring**, and **capture-eliminates-team** hearts —
steal any rival's heart and carry it into *your* endzone to knock that team out
of the game; **last team standing wins**. Paint itself is cosmetic (board-only
splatter; no territory scoring).

Player code must read the exact `own aim <brads>` marker. The self soldier has
only 16 visual rotations, so deriving aim from its sprite discards most of the
turret's 256 legal headings and makes the controller act on false state.

## Variants (deployed manifest, verified live)

The manifest determines seats and teams; the campaign commissioner separately
determines which policies occupy those seats. Normal invasions use four
policies. All variants:
`lives 3`, `hitPoints 3`, `gunRange 1300`,
`respawnTicks 72`, `carrierSpeedPct 70`, and `maxGames 1`. The public variant
config carries `seed: 679961`; hosted scheduling and explicit map overrides are
separate concerns, so do not use that value as terrain identity.

| variant | seats | teams | map | scoring | maxTicks | vision cone | agents per policy |
|---|---|---|---|---|---|---|---|
| `1v1` | 16 | 2 | generated | pot +2/-2 | 5000 | ±60° | campaign mode `2v2`; normally 7-seat captain + 1-seat ally per team |
| `default` | 16 | 2 | generated | classic +1/-1 | 5000 | ±60° | campaign mode `2v2` if used |
| `2v2` | 16 | 2 | generated (size drawn) | pot **+2/-2** | 5000 | ±60° | normally 7-seat captain + 1-seat ally per team |
| `4ffa` | 16 | 4 | generated (size drawn) | pot **+4/-1/-1/-1** | 5000 | ±60° | 4 (one policy per team) |
| `4ffa8` | 32 | 4 | generated, manifest defaults giant | pot +4/-1/-1/-1 | **7500** | **±45°** | 8 (one policy per team) |

- **`1v1` changed meaning in 0.7.205.** It was a literal two-agent debug duel
  through 0.7.204 and is now a 16-seat two-team variant. That does not imply two
  policies: the campaign classifies any two-team variant with at least four
  seats as mode `2v2` and normally inserts one allied entrant per side.
- **The campaign, not the disabled ladder, selects contested cells** (next
  section). Its current board uses `1v1`, `2v2`, and `4ffa`; the disabled
  ladder's older four-entrant 3:1:1 rotation is not the live sampling model.
- **Normal campaign assignment:** on a 16-seat two-team map, each captain owns
  seven seats and its ally owns the team's second seat: global slots 0/2 are
  red captain/ally, 1/3 blue captain/ally, and later same-color slots repeat
  the captain. A paired seating swaps captains across colors while allies stay
  fixed. Four-team modes give one complete color to each of four policies.
- Time-limit draw pays **-1 to every player** (GV21); mutual wipe = 0/0.

## The GV41 endgame barrage (new in 0.7.210 — changes how games end)

**Reaching 0:00 no longer ends a barrage-enabled game.** Every current gameplay
variant ends in an escalating grenade barrage that fires from the map edges
inward until someone dies or the heart falls.

| Variant | Clock | Latches at | Saturates | Rate |
|---|---:|---:|---:|---:|
| `1v1`, `2v2`, `4ffa`, `default` | 7,200 ticks = 5:00 | 4:30 elapsed | 5:00 | 4/s → 15/s |
| `4ffa8` | 7,500 ticks = 5:12.5 | 4:42.5 elapsed | 5:12.5 | 4/s → 15/s |

After the latch, both rate and depth follow the same linear 30-second ramp
`p(t) = clamp(t / 30s, 0, 1)`:

```text
rate(t)  = 4 + 11·p(t)  shells/s
depth(t) = 40 + (D - 40)·p(t)  pixels,  D = floor(min(W, H) / 2) + 1
```

So the true midpoint rate is **9.5/s**, and the 30-second ramp launches about
**285 shells**. Each shell picks one of the four edges uniformly, an inset in
`[0, depth)`, and a coordinate along that edge — so the danger zone is a union
of four edge bands contracting toward center, reaching full-board eligibility at
saturation. On a giant 2-team map that is 7.0% of possible centers at the latch
and ~65.6% by 15 seconds. **Center is the safe region early, and eligibility is
not a flood wall** — blasts are stochastic and their radius reaches past the band.

What a policy can observe every rendered state:

```text
grenade barrage depth <n> rate <n> start <n> sat <n>
```

Depth and rate are zero before the latch. ⚠️ The marker publishes
`ratePermille div 1000`, so it **truncates downward** — at the true 9.5/s
midpoint the label reads `rate 9`. Use the schedule math for exact density and
the marker only as a coarse readback. Airborne shells appear as ordinary
fog-gated `grenade air` objects flying linearly from edge to landing over ten
ticks; blasts use `blast stage <n>` and unseen landings produce the usual
jittered `grenade sound` ring.

Stencil's response (v58) is to evacuate toward map center on the marker and hold
a central ring; see `VERSION_LOG.md`.

## Paint puddles (implemented, NOT active in current campaign episodes)

Puddles exist in 0.7.211 but **no deployed variant config sets `mapPuddles`, and
the engine default is zero — so normal campaign episodes have none.** Documented
here so the mechanic is not rediscovered from scratch if it is ever enabled.

A puddle is a **union of discs** — one 26-30px core plus 2-4 smaller lobes, hard
capped at 45px reach from the anchor. Its init marker `puddle <x0>,<y0> <x1>,<y1>`
is a **conservative bounding box, not exact membership**, so treating the box as
the hazard over-avoids. For each full **24 ticks of continuous center-point
occupancy**, the game rolls a **10% chance of 1 damage** (shield first); leaving
for even one tick, dying, or respawning resets the clock. Puddles do **not** slow
movement or firing, and do not block shots or vision. `mapPuddles` is an exact
0-64 count on **generated two-team maps only** — four-team generation rejects a
positive request.

## The campaign (territory) league — how games are actually scheduled

The live Paintbot league does **not** run a ladder: it runs metta's **campaign
round brain** (spec 0075; league settings hold ladder XOR campaign — verified
live via `GET /v2/leagues/{id}/campaign`, `enabled: true`). The war model:

- A **10x10 board of 100 cells**, 4-neighbor adjacency. Players enter by
  **airdrop** and expand by **invading adjacent cells** (max 3/round, one
  round every **600s**). Standings = **territory** (cells owned) — the
  division "score" leaderboard IS cell count.
- **Each cell permanently owns a map.** At live round 381 the public board has
  26 `1v1`, 26 `2v2`, and 48 `4ffa` map refs: 52 campaign-mode `2v2` and 48
  `ffa4` cells.
  Every cell has a persistent `map_seed` and preview; `map_size` is currently
  unset for all 100 cells, so the variant/generator resolves size. Episodes
  fought over a cell pin the target cell's map identity, while per-episode RNG
  may still vary. Re-read the board before designing an evaluation because the
  commissioner can regenerate it.
- **Battle mode derives from variant structure, not its name.** Both current
  `1v1` and `2v2` refs are 16-seat, two-team variants and therefore campaign
  mode `2v2`. Normal invasions use four policies in 7+7+1+1 seating; claims and
  missing-ally fallback have different rosters. Created participant rows are
  the final truth.
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
- **A four-team color has one policy owner** — unlike campaign `2v2` mode,
  there is no same-color allied entrant. The four colors are pure FFA.
- **Last team standing wins**: captures and wipes mix freely.
- 4-team maps may use square rot90 symmetry or rectangular `quadmirror`
  symmetry. Their `corners` and `plus` endzones remain team-congruent; the
  walkability sprite, rather than a locally reconstructed shape vocabulary,
  is Stencil's navigation truth.
- Items on 4-team boards: a rot90-fair med-kit diamond of four; one shield and
  one spray-can pickup near each endzone; four grenade pickups at edge
  midpoints (corners) or a rot90 orbit (plus).

## Procedural maps

Generated in `src/ctf/arena.nim` (splitmix64, fully deterministic per seed;
generate → validate → retry seed+1). What a policy must absorb:

- **Size classes** `small/standard/large/huge/giant` = 0.85/1.0/1.3/1.8/2.6 x
  the base shell — 2-team: 1235x659 scaled (1050x560 … **3211x1713**); 4-team:
  square 960 scaled (816 … **2496**). The generator selects a size unless the
  request pins `mapSize`; standalone `4ffa8` defaults to giant, while current
  campaign cells leave `map_size` unset.
- **Terrain**: authored/generated rectangles, discs, diamonds, diagonals, and
  polygon rings; trenches, glass windows, pits, and generated/mapkit styles
  including caves. Stencil deliberately consumes the baked walkability raster,
  so new authored shape types do not require a policy-side parser.
- **Endzones**: 2-team = classic `column` (half the pool) or compact
  `square`/`disc`; 4-team = `corner`/`arm`.
- **The seed is never on the wire** — a policy cannot regenerate the map. It
  must read the map from the observation (below). Replays DO carry the exact
  geometry (`mapSpec`), so post-hoc tools can reconstruct terrain.
- `gunRange` is fixed per episode (GV34) — bigger maps do NOT extend the gun.
  The engine stock default is 1050px, but every deployed Paintbot 0.7.211
  variant explicitly overrides it to **1300px** (vision reach is therefore
  1950px except for the 90px omnidirectional bubble).
- Grenade max range and shout radius scale with the map (`mapWidth/5`).

## What the wire tells you (the whole map contract, at t=0)

The init snapshot states everything about terrain; fog hides only entities:

1. **`walkability map` sprite** — full-map RGBA (snappy raw-block compressed),
   alpha>0 = walkable, always 1x map pixels. *The* nav source.
2. **`game teams <n> map <w>x<h>`** marker — team count and exact map size.
3. **`endzone <color> <shape> <x0>,<y0> <x1>,<y1>`** markers — one per team,
   shape ∈ {column, square, disc, corner, arm}. (Spectator streams also carry
   `endzone <color> power <n>` glows — match the shape token.)
4. One **`handicap <color> <permille> hp <n> lives <n> spd <n> miss <n>`**
   marker per team, including unhandicapped teams. Absence means an older
   engine, not a zero handicap. Stencil does not yet consume these markers.
5. `Room <color> Base` markers; per-color **`team score <COLOR> <k>/<d>`**
   chips (fog-independent, every frame — the wipe clock).
6. Planted hearts (`<color> flag planted`) **never fog** — pedestal positions
   are readable from the first frame. A carried heart (`<color> flag`) is as
   visible as its carrier.
7. **Not on the wire**: variant id, game name, seed, scoring rule, muster.
   Do **not** infer `default` from the old fixed geometry: canonical 0.7.207
   generates it too. Do **not** infer seats-per-team from map size. Stencil
   starts from the minimum roster consistent with its own seat and grows the
   estimate only from observed identity badges.

Protocol deltas from Sprite-v1 (shared with CTF): input bit 7 = **C** (hold to
charge a grenade throw — the SDK bridge's 7-bit clamp must be widened);
`own aim <brads>` readback marker; do NOT send Player Ready in league play; map
camera object (id 1) present ⇔ match running; player stream is 1x.

## Mechanics carried over from CTF (unchanged)

- Movement 2.75 px/tick per axis (diagonal √2 faster); carrier at 70%.
- Aim: every integer heading in a 256-brad turn is legal; B/Select moves
  ±5 brads per held tick, and `own aim <brads>` is authoritative.
- Gun: 1300px hitscan in the deployed manifest, 5-tick windup (aim locks at
  pull; don't strafe through it), 12-tick cooldown, aim jitter grows to 80% at
  max range, friendly fire ON
  (first body on the ray eats the bullet).
- Vision: cone (±60° paintbot / ±45° on 4ffa8) riding the aim + 90px bubble.
- Items: med kits (heal), shields (6hp, 3x slower fire), grenades (C charge,
  52px blast), spray can ("plasma arc": 170px cone, 85px max width, damage 3,
  5 active + 20 reset ticks, body-disc hit test; REPLACES the gun while held).
  A spray locks its direction when A is pressed for the entire five-tick burst;
  its origin continues moving with the carrier, but turning cannot sweep it.
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
- **Historical default-arena tuning no longer describes the canonical game.**
  Treat every current map as wire-derived geometry.
- **Ally uncertainty matters in 2v2**: a normal campaign captain owns seven
  agents while another entrant owns one teammate seat. Deterministic seat-keyed
  conventions must tolerate that teammate not speaking Stencil's protocol.
- The Nim `baseline` (in-repo) handles all variants with purely online nav
  (8px grid, Dijkstra repath every 10 ticks) — proof of feasibility and the
  reference opponent; its known gap: no overwatch/home-defender roles on
  4-seat teams.
