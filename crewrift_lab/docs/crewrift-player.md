# Building a Crewrift player

What **any** Crewrift player policy must do — the I/O contract every Crewrift
player speaks, independent of how it's implemented. This is for building a new
player from scratch as much as for understanding crewborg; it does **not** assume
you're using crewborg.

For the **game-agnostic** image/runner contract (read `COWORLD_PLAYER_WS_URL`,
connect, play one slot, exit clean; amd64; secrets; build/upload/submit), see the
lab-root [`player-build.md`](../../player-build.md). **This doc is only the
Crewrift-specific half: the protocol your bridge speaks over that websocket.**

**Validated 2026-06-08** against crewrift `d9f6b30` (v0.1.40), bitworld `5a4bea1`,
coworld `0.1.20`. Citations are by file + symbol. The two authoritative sources:

- **The wire protocol** — bitworld **Sprite v1**
  (`~/.nimby/pkgs/bitworld/docs/sprite_v1.md`, mirrored on GitHub at
  `Metta-AI/bitworld/blob/master/docs/sprite_v1.md`). Crewrift's manifest points
  every player at this spec via `game.protocols.player`.
- **The Crewrift scene** — what the sprites/objects/labels *mean* — defined by the
  game in `~/coding/coworlds/coworld-crewrift/src/crewrift/{sim,global}.nim`. The
  reference bot **`notsus`** (`players/notsus/notsus.nim`, with a `README.md`) is
  the canonical minimal implementation; crewborg's `perception/constants.py` is a
  second, source-verified decoder you can read in this lab. **Re-derive from the
  game source if anything here doesn't match** — the scene vocabulary is the
  game's to change.

> **Examples below are illustrative.** Concrete object-id bases, offsets, and label
> strings are shown to make the contract legible; they are the *current* Crewrift
> convention, not a frozen API. Treat the game source as truth.

---

## 1. The shape of the problem

Crewrift is a social-deduction game (think *Among Us*): 8–16 players on a
2-D map. Most are **crewmates** completing tasks; a few are **imposters** who kill
crewmates and blend in. Bodies get reported, meetings are called, players chat and
vote someone out. Crew win by finishing tasks or voting out all imposters;
imposters win by killing enough crew. (Full rules, scoring, and strategy:
[`crewrift-gameplay.md`](crewrift-gameplay.md) — the in-lab game reference.)

Your player is **one slot**. It does not get a clean game-state object. It receives
the **same rendering stream a human client would see** — a stream of sprite/object
draw commands (Sprite v1) — and must reconstruct game state from it, then drive its
avatar with **the same button presses a human would use** (a d-pad + A/B). There is
**no semantic action API**: "do the task," "kill," "vote red" are all expressed as
movement + A/B at the right place and time.

So a Crewrift player has three jobs:

1. **Decode** the Sprite-v1 stream into a model of the scene (§3–4).
2. **Decide** what to do given that model and the game phase (§5–6, shaped by the
   scoring in §7).
3. **Encode** that decision as held-button input / chat text (§5).

---

## 2. Transport

- **Binary WebSocket.** Connect to `COWORLD_PLAYER_WS_URL` (a fully-formed
  `ws://<host>:8080/player?slot=<N>&token=<T>`). Frames are **binary**; never
  expect JSON or text frames on this socket. Use a client with no frame-size cap
  (sprite payloads can be large) — e.g. Python `websockets.connect(url,
  max_size=None)`.
- **~24 Hz, one logical frame per game tick.** The server pushes draw commands as
  the game advances; a "tick" of state arrives as a burst of messages.
- **Incremental / retained, not full redraws.** The server sends **deltas** — it
  only re-sends what changed. You **must keep retained tables** (below) and apply
  each message to them; you cannot treat each frame as a fresh complete scene.
- **You drive your own cadence.** You send input packets **when your held state
  changes** (the protocol says emit on change). Most players also re-evaluate and
  emit every tick. There's no request/response handshake — it's two independent
  streams over one socket.
- **The connection closing is "episode over."** Exit cleanly (status 0) when the
  socket closes; don't treat it as an error to retry. (Game-agnostic lifecycle:
  [`player-build.md`](../../player-build.md) §contract.)

---

## 3. Receiving: the Sprite-v1 retained-scene model

Sprite v1 is a **structured scene**, not a framebuffer. The server names every
visual element and gives it a position — so you decode *labeled objects at
coordinates*, not pixels. You keep three retained tables (sprite_v1.md §Rendering
Model) and mutate them per message:

| Table | Key | Holds |
| --- | --- | --- |
| **Layers** | `u8` layer id | layer type, flags, viewport W/H |
| **Sprites** | `u16` sprite id | width, height, **label** (UTF-8), RGBA pixels |
| **Objects** | `u16` object id | x, y, z, layer, sprite id |

The **server→client** messages you must handle (every message starts with a 1-byte
type; all multi-byte ints are **little-endian**; coordinates are signed `i16`):

| Byte | Message | Effect on your tables |
| ---: | --- | --- |
| `0x01` | **Define Sprite** | upsert sprite `id` → (w, h, **label**, Snappy-compressed RGBA). The **label is the semantic key** (§4) — you rarely need the pixels. |
| `0x02` | **Define Object** | upsert object `id` → (x, y, z, layer, sprite id). This is how entities **appear and move**. |
| `0x03` | **Delete Object** | remove object `id` (entity left view / despawned). |
| `0x04` | **Clear Objects** | drop **all** objects (sprites stay). A scene reset — e.g. a phase transition. |
| `0x05` | **Set Viewport** | set a layer's viewport W/H. |
| `0x06` | **Define Layer** | declare a layer's type (map vs. a UI corner) + flags. |

**The decode that matters: labels, not pixels.** You almost never need to render
RGBA. The game attaches a human-readable **label** to each sprite (`"player red
right"`, `"body blue"`, `"walkability map"`, `"progress bar 45%"`, …). An object
points at a sprite; the sprite's label + the object's position + the object's **id
range** tell you what the object *is* and where. That triple — **(id range, label,
xy)** — is the whole game-state-reconstruction problem.

> Decoding the pixels is only needed for two map sprites — the **walkability map**
> and the **shadow/vision** overlay (§4) — whose *content* is the data. Everything
> else is read from labels.

The compressed pixel payload (when you do need it) is a **Snappy** stream that
decompresses to exactly `W*H*4` bytes of RGBA (sprite_v1.md §Define Sprite).

---

## 4. The Crewrift scene vocabulary

This is the Crewrift-specific layer on top of Sprite v1: which object-id ranges and
labels mean what. **All of this is defined by the game** in `sim.nim` / `global.nim`
and is the part most likely to drift — the values below are the current convention
(cross-checked against crewborg's `perception/constants.py`, itself verified against
game source). Verify against the game if perception misbehaves.

### Self and world coordinates

- **You are the camera, not an object.** There is no "me" object in the stream. The
  `/player` view is centered on your avatar. The **map object** (object id `1`,
  sprite id `1`, label `"map"`) is drawn at `(-cameraX, -cameraY)`, so
  **`cameraX = -mapObject.x`**, `cameraY = -mapObject.y`.
- **Your world position** is the camera plus a fixed center offset:
  `self_world ≈ (cameraX + 60, cameraY + 66)` (the offset is the screen-center
  back-out of the 128×128 view; `SELF_OFFSET_X/Y` in `constants.py`, derived from
  `sim.nim` camera math). Use this to compute distances/headings to everything else.
- **On-screen test:** a world point `(wx,wy)` is visible iff
  `camera ≤ (wx,wy) < camera + (128,128)` (the `/player` window is 128×128).
- **Collision vs. draw point.** Players/bodies are *drawn* a few pixels up-left of
  their true collision/interaction point. To make range checks (kill, report, task)
  match the server, add `(+3, +9)` to a decoded entity's object xy to recover its
  collision point (`ENTITY_COLLISION_DX/DY`; `global.nim` draw offset + `sim.nim`
  `CollisionW/H=1`).

### Entities, by object-id range + label

Object **id ranges are stable** and disjoint, so the same label (e.g. `"player
red"`) in two ranges means two different things (a live player vs. a voting-grid
cell). The current bases (`constants.py`, from `sim.nim`/`global.nim`):

| id range | What it is | Label form | Read |
| --- | --- | --- | --- |
| `1000–1999` | **Live players** in view (base + slot) | `player <color> left\|right` (or `ghost <color> …` when dead) | who is near you, their color, facing, alive/ghost |
| `2000–2999` | **Bodies** on the floor | `body <color>` | a killable-report target; align with the kill you saw |
| `3000+` | **Task bubble** over a task you can do | `"task bubble"` | a task location near you |
| `7000+` | **Task arrow** (radar pointer to your next task) | `"task arrow"` | direction to an off-screen task |
| `9000–9199` | **Chat line text** (meetings) | label = the raw message text | what was said |
| `9200–9299` | **Chat speaker icon** | `player <color> <facing>` | who said the line at the same screen-y |
| `9300+` | **Voting candidate grid** (base + player index) | `player <color>` if alive, `body <color>` if dead | an authoritative **alive/dead census by color**, every meeting |
| `9500+` | **Role-reveal icons** (base + slot) | normal `player <color>` sprites | during RoleReveal, an **imposter** is shown its *teammates'* icons here — i.e. the imposter team |
| `9600` | **Vote-result** ejected-player icon | `player <color> <facing>` | who got ejected (absent if vote skipped) |
| `10100+` | **Vote dots** (who voted for whom: base + target·16 + voter) | `vote dot <color>` | live vote tally during a meeting |
| `10400+` | **Skip-vote dots** (base + voter) | `vote dot <color>` | who voted skip |

### HUD / overlay sprites (fixed labels, not id-keyed)

Read these by **label**:

- `"walkability map"` — a sprite whose **pixels** encode which cells are walkable.
  Decode it (one of the two pixel-decodes you need) to drive pathfinding around
  walls.
- `"shadow"` — a screen-sized **vision/occlusion** overlay, re-sent on camera move:
  opaque pixels are *occluded*, transparent pixels are *visible* (line of sight).
  Decode to a per-frame visibility mask if you reason about what you can/can't see.
- `"imposter icon"` / `"imposter icon cooldown"` — present only when **you are the
  imposter**; the cooldown variant means your kill isn't ready yet. Their presence
  is how you learn your own role mid-game (besides the role-reveal interstitial).
- `"ghost icon"` — present when **you are dead** (a ghost). You keep receiving the
  stream; dead crew can still finish tasks (worth points), but can't vote.
- `progress bar <N>%` (e.g. `"progress bar 45%"`) — the active task **or** kill
  progress bar; parse the trailing percent to know how far along holding A has got.
- `task counter <N>` — how many tasks remain.
- `vote cursor` / `vote skip cursor` / `vote timer` / `vote self marker <color>` —
  the voting UI: where your selection cursor is, the skip option, time left, and a
  marker on your own locked-in choice.

### Phase / result text (interstitials)

The game shows big center text at transitions; **read the phase from which text is
present** (`global.nim` interstitialTextItems): `WAITING` / `NEED MORE!` /
`STARTING` (lobby), `IMPS` / `CREWMATE` (role reveal — `IMPS` means you're an
imposter), `SKIP` / `NO ONE` / `<color> WAS KILLED` (vote result), `CREW WINS` /
`IMPS WIN` / `DRAW` (game over).

---

## 5. Sending: input is buttons, not commands

There is **no high-level action API**. You play Crewrift the way a human does — a
held-button bitmask (movement + A/B) and, in meetings, typed chat. Two client→server
messages (sprite_v1.md §Client to Server):

### `0x84` Player Input — the held-button bitmask

One byte after the `0x84` header: the **currently held** buttons (bit 7 reserved,
must be 0). Emit **whenever the held set changes**; omitted bits are treated as
released.

| Bit | Value | Button | Crewrift meaning |
| ---: | ---: | --- | --- |
| 0 | `0x01` | D-pad up | move up |
| 1 | `0x02` | D-pad down | move down |
| 2 | `0x04` | D-pad left | move left / cycle vote selection |
| 3 | `0x08` | D-pad right | move right / cycle vote selection |
| 4 | `0x10` | Select | — |
| 5 | `0x20` | **A** | **the universal "interact"**: do task / kill / report body / press emergency button / confirm vote (context-dependent) |
| 6 | `0x40` | **B** | **vent** (imposter only): enter/exit/move through vents |

**Action = the right button at the right place.** Examples (illustrative):

- **Do a task:** navigate onto the task tile (follow the `task arrow`, then the
  `task bubble`), then **hold A and stand still** until `progress bar` reaches 100%.
  Any movement resets it (README §Crewmate).
- **Kill (imposter):** when `imposter icon` (not cooldown) is up, stand adjacent to a
  victim and press **A**.
- **Report a body / press emergency:** stand on the `body` (or the emergency button)
  and press **A** to start a meeting.
- **Vote:** during Voting, use **left/right** to move the `vote cursor` across
  candidates (or onto `vote skip cursor`), then **A** to lock it in. **A vote can't
  be changed once cast** — and **not voting at all costs −10** (§7), so always cast.
- **Vent (imposter):** **B** at a vent to use the vent network.

Movement/interaction nuance: some actions want a **held** button (walking, charging a
task), others a **single edge press** (stepping the vote cursor, a one-shot
report/kill). A working pattern for edge presses is to release the bit for one tick
between presses — see crewborg's `action.py` (`_edge_press`, `_movement_mask`,
`_navigate_mask`) for a concrete implementation.

### `0x81` Input Text — meeting chat

`0x81` + `u16` length + printable-ASCII bytes. Used **only during meetings
(Voting)** to talk. Keep gameplay input and text input separate (don't let chat
characters leak into the button mask). Social play — accusing, defending, coordinating
— happens here and materially affects who gets voted out.

(Mouse messages `0x82`/`0x83` exist in Sprite v1 but Crewrift play is keyboard-style;
a player needs only `0x84` and `0x81`.)

---

## 6. Game phases & what each demands

Detect the phase from the interstitial text (§4) and the UI sprites present, then
behave accordingly:

- **Lobby** (`WAITING`/`NEED MORE!`/`STARTING`) — wait for enough players; you spawn
  next to the emergency button.
- **Role reveal** (`IMPS`/`CREWMATE`) — learn your role. As imposter you also see
  your teammates' role-reveal icons (id `9500+`) and gain `imposter icon` + vent (B).
- **Playing** — the main loop. Crew: complete tasks, watch for kills, stick together
  (a witnessed kill identifies the imposter; README §Strategy). Imposter: blend in,
  fake tasks, kill on cooldown, flee bodies, use vents.
- **Voting** (a body was reported or the emergency button pressed) — chat (`0x81`),
  then select + confirm a vote with the cursor + A. Don't vote out crew on weak
  evidence; **always** cast *some* vote (skip is a valid, penalty-free vote).
- **Vote result** (`SKIP`/`NO ONE`/`<color> WAS KILLED`) — who (if anyone) was
  ejected; update beliefs.
- **Game over** (`CREW WINS`/`IMPS WIN`/`DRAW`) — the socket will close; exit.

Death isn't the end of the stream: a dead crewmate becomes a **ghost** (`ghost icon`)
and can still walk and **finish tasks for points**, but cannot vote or interact with
the living.

---

## 7. Scoring — what good play optimizes

Per-player scoring (README §Scoring) — this is the reward your policy should be
built around, not just "win":

| Event | Points |
| --- | ---: |
| Win the game | **+100** |
| Complete a task | **+1** |
| Kill a crewmate (imposter) | **+10** |
| **Not** voting and not skipping in a meeting | **−10** |
| Standing still while you still have tasks | **−1 per 10 s** |

Consequences worth designing for:

- **Always cast a vote** (even skip). Abstaining is a hard −10 — never let a meeting
  end with no vote from you.
- **Don't idle.** Standing still with tasks outstanding bleeds points; keep moving or
  keep doing a task.
- **Tasks are cheap, steady points** even when you can't win; killing is high-value
  for imposters; **winning dwarfs everything** (+100), so don't trade the game to
  farm +1s.

---

## 8. Build, test, ship

The container/build/upload/submit flow is **game-agnostic** —
[`player-build.md`](../../player-build.md) covers the Dockerfile (linux/amd64), the
bridge skeleton, secrets/Bedrock, and the `coworld-local-run` (Gate-1 smoke) and
`coworld-policy-lifecycle` (upload→submit) skills. The Crewrift-specific part is only
what's above: **a bridge that connects, decodes Sprite v1 into the scene model (§3–4),
decides (§6–7), and emits `0x84`/`0x81` (§5).**

For building Crewrift player images **in this lab** (the concrete Dockerfile +
toolchain wiring for Python vs. Nim players, and how to build a new one whether or
not it's vendored), see [`designs/building_players.md`](designs/building_players.md) — its
general-case section is the guide for new players. The build command is
`crewrift_lab/tools/build_player.sh <policy>`.

Starting points for a new Crewrift player (README §Policy Starting Points):

- **Reference baseline** — `notsus` (`players/notsus/notsus.nim` in the crewrift
  repo, with its own `README.md`); the public image `…/players/notsus:latest` runs it.
  The minimal "decode Sprite v1, move, press A" implementation.
- **A worked Python player** — crewborg, vendored in this lab
  (`crewrift_lab/crewrift/crewborg`): `perception/` is a full Sprite-v1 → scene
  decoder, `action.py` the input encoder, `coworld/policy_player.py` the bridge.
  Heavier than you need to start, but it's the source-verified reference for every
  id range / label / offset cited here.

Once the player runs, evaluate it through the lab loop ([`AGENTS.md`](../../AGENTS.md))
— experience requests, then read the replays/logs
([`crewrift-replays.md`](crewrift-replays.md)) to see what it did and why.

---

## See also

- [`crewrift-gameplay.md`](crewrift-gameplay.md) — the game from a gameplay
  perspective (rules, scoring, strategy); the *why* behind what the player decodes/does.
- [`player-build.md`](../../player-build.md) — game-agnostic image/build/ship contract.
- [`crewrift-replays.md`](crewrift-replays.md) — reading a finished Crewrift game
  (objective replay timeline + crewborg's subjective logs) to diagnose play.
- bitworld `docs/sprite_v1.md` — the wire protocol, authoritative.
- crewrift `src/crewrift/{sim,global}.nim` — the scene vocabulary, authoritative.
- crewrift `players/notsus/` — the reference player.
</content>
</invoke>
