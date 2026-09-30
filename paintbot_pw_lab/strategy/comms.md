# Comms v1: team messages over `shout`

> **Status:** draft policy specification, 2026-09-30. Not implemented. This file is part of the
> policy, not of the strategy file format: we expect to change it often. When `STRATEGY.md` exists,
> its Communication section links here, and each message type below becomes one `COM.`
> component. Engine facts are verified at paintbot-pw `coworld-v0.3.89` (`118e1619`), the league
> build on 2026-09-30.

## 1. Scope

Comms v1 carries tactical facts that teammates cannot see for themselves: enemies, danger,
grenades, glory hearts, pickups, and disguises. It does not carry squad coordination or the
sender's own position; those come later.

Security goal for v1: **scrambling**. A bot that hears our shouts in a match cannot read them or
forge them. We do not defend against offline analysis of public replays (every shout is in the
replay with its tick, true sender seat, and text).

## 2. Transport facts (engine, `coworld-v0.3.89`)

| Fact | Value | Source |
| --- | --- | --- |
| Send | `shout(handle)` queues the text. At most 4 per cog per tick; the 5th returns 0. | `examples/paintbot/bots.nim:56-58` |
| Length | Text over 256 bytes is cut to 256 bytes. | `bots.nim:58` |
| Cost | Flat per call, not per character: `shout` 68 WU. | `bots.nim:58` |
| Delivery | Next tick, to every living cog within `Width div 5` = 1,280 units (12.8 m) of the sender at decision time, **both teams**, no line of sight needed. Dead cogs neither send nor hear. | `examples/paintbot/seat_view.nim:324-333`, `game.nim:601` |
| What a listener gets | `heardText(i)` (text), `heardX/heardY(i)` (sender's **true** exact position), `heardSlot(i)` (sender's **observed** seat: a disguised sender shows its disguise). Messages last one decision only. | `seat_view.nim:312-322` |
| Replay | Every shout is recorded with tick, true seat, and text (first 20,000 per episode). | `game.nim:585-589` |
| Strings | Pool resets every tick: 1,024 handles, 64 KiB, 1,024 bytes per string. `strFromInt` 8 WU, `strCatInt` 68, `strByte` 3, `strLen` 2, `heardText` 4 (allocates a handle), `strChr` 6 (bytes 0-255). | `src/polyworld/basic.nim:3005-3070`, `2747-2748` |
| Arithmetic | Signed int32, wraps on overflow. `AND`/`OR`/`XOR` are logical (0/1), not bitwise. | `docs/policy-surface.md` §2 |
| Disguise | A disguised cog appears to others as seat `slot xor 1` and as the other team. The disguise ends on a gun order, spray burst, grenade release, or death. Hearts use the true team. | `docs/mechanics.md` "Disguise" |

## 3. Principles

1. **Send only what teammates cannot see.** Heart ownership, capture, and contest state are
   public to every cog. We send no heart messages.
2. **The sender's position is free.** Every heard message has the sender's exact position. A
   message about "here" carries no coordinates.
3. **A shout reveals the sender.** Every enemy within 12.8 m gets our exact position, whatever the
   text says. Do not send non-urgent messages while sneaking.
4. **All 8 seats on our team run this policy.** A message from a speaker labeled as a teammate
   that fails our check comes from a disguised enemy.
5. **Received facts are beliefs.** Each received fact goes into Knowledge with source `heard` and
   an age. A seen fact replaces a heard fact about the same thing.

## 4. Message catalogue

| Code | Type | Message | Sent when | Receiver effect |
| --- | --- | --- | --- | --- |
| E | 0 | **Enemy sighting** | sender sees an enemy (refresh rules in §7) | Add or refresh the track in `K.enemy_contacts` with source `heard`. |
| F | 1 | **Focus call: shoot this target** | sender selects a fight target that is wounded or that two or more teammates can engage | Each receiver that sees the target prefers it as its fight target for `focus_ttl` ticks. Focus concentrates fire. It does not spread fire. |
| G | 2 | **Grenade out** | sender starts to charge a grenade at a target | Keep out of `grenade_clear_radius` of the target until the release tick plus 24 ticks. |
| U | 3 | **Under fire, no shooter visible** | sender loses HP and sees no enemy | Mark a danger area at the sender's position (`heardX/Y`) toward the gunfire direction for `danger_ttl` ticks. |
| H | 4 | **Glory heart seen** | sender sees a glory heart | Add it to `K.glory_hearts` with its expiry. |
| K | 5 | **Pickup taken** | sender takes a pickup | Mark the station empty until the ready tick in `K.pickup_memory`. |
| R | 6 | **Pickup ready** | sender sees a ready station that is not marked ready in its memory | Mark the station ready in `K.pickup_memory`. |
| X | 7 | **Disguise alert: this label is fake** | sender identifies a disguised enemy (§8) | Treat the body with that label near that position as an enemy for `disguise_ttl` ticks. |
| D | 8 | **I am in disguise, and I am on your team** | sender is disguised and a teammate can shoot it (§8) | Do not shoot the body with the sender's apparent label within `friend_radius` of the sender's position, for `friend_ttl` ticks. Do not raise X for that body. |

Types 9-15 are free for later messages.

## 5. Wire format

A message is **20 decimal digits**: block A then block B. Each block is written as the integer
`1,000,000,000 + s`, where `s` is the scrambled payload (`0 <= s < 1,000,000,000`), so every
block has exactly 10 digits and starts with `1`. The largest block, 1,999,999,999, fits in int32.

Build: `h = strFromInt(blockA)`, then `h = strCatInt(h, blockB)`, then `shout(h)`.

### 5.1 Payloads (before scrambling)

All packing uses multiplication and `MOD`, because BASIC has no bit operations.

```text
pA = check + 100 * (type + 16 * (senderSeat + 16 * fieldsA))     fieldsA in 0 .. 39,061
pB = cell + 65,536 * fieldsB                                      fieldsB in 0 .. 15,257
cell = gx + 256 * gy
gx = (x - mapMinX()) * 256 / (mapMaxX() - mapMinX() + 1)          gy the same with Y
```

`senderSeat` is the sender's true seat (`selfId`, 0-15). A receiver decodes a cell to the center
of that grid square. On Heartwick (16,000 x 9,600 playable) a square is 62.5 x 37.5 units.

| Code | fieldsA | fieldsB | cell |
| --- | --- | --- | --- |
| E | `enemySeat + 16 * (hp + 4 * heading)`; `heading` 0-7 octant, 8 unknown | age of the sighting in ticks, max 255 | enemy position |
| F | `targetSeat + 16 * hp` | 0 | target position |
| G | ticks until release, 0-24 | 0 | grenade target |
| U | `myHp + 4 * gunDir`; `gunDir` 0-7 from `soundDirection`, 8 unknown | gunfire distance class 0-2 from `soundDistance`, 3 unknown | 0 (use `heardX/Y`) |
| H | ticks left, 0-720 | 0 | glory heart position |
| K | pickup id, 0-255 | ticks until ready, 0-720 | pickup position |
| R | `pickupId + 256 * kind` | 0 | pickup position |
| X | fake label seat | age of the evidence in ticks, max 255 | position of the fake body |
| D | apparent label seat (`selfId xor 1`, computed as `selfId + 1 - 2 * (selfId MOD 2)`) | 0 | 0 (use `heardX/Y`) |

Enemy seats are observed seats (what `visible`/`playerX` answer to).

### 5.2 Check

```text
core  = type + 16 * (senderSeat + 16 * fieldsA)
check = ((core MOD 97) + 7 * (pB MOD 97) + ((sendTick MOD 9973) * k5) MOD 97 + k6) MOD 97
```

`k5` and `k6` are secret constants below 97. The check ties a message to its send tick, so a
copied message fails on any later tick.

### 5.3 Scrambling

For block `b` (0 = A, 1 = B) and send tick `t`:

```text
h1   = ((t MOD 30011) * k1 + k2 + b * k3) MOD 30011
h2   = (h1 * h1 + k4) MOD 32749
mask = h1 * 32768 + h2                                  (always below 1,000,000,000)
s    = (p + mask) MOD 1,000,000,000                     send
p    = (s - mask + 1,000,000,000) MOD 1,000,000,000     receive
```

`k1`-`k4` are secret constants below 30011. Every product stays below 2^31. The keys live only in
our source, which is not public. This is scrambling, not cryptography.

## 6. Receive procedure (each tick, before Knowledge updates)

1. `sendTick = worldTick - 1` (delivery is always the next tick).
2. For `i` from 0 to `min(heardCount(), max_decode) - 1`:
   1. `h = heardText(i)`. Skip it if `strLen(h) <> 20`.
   2. Read the 20 bytes with `strByte`. Skip it if byte 1 or byte 11 is not `"1"` (49) or any byte
      is not a digit. (Confirm whether `strByte` indexes from 0 or 1 at build time.)
   3. Build `sA` and `sB` from the digits after each leading `1`. Unscramble both. Split `pA`.
   4. Recompute the check. If it fails: when `heardSlot(i)` is a teammate label, record
      "fake teammate label at `heardX/Y`" as disguise evidence (§8). Skip the message.
   5. Apply the receiver effect from §4.
3. A seen fact replaces a heard fact about the same object. Heard facts carry their age.

## 7. Send rules

- At most **1 shout per cog per tick**. Non-urgent types (F, H, E, U, K, R) at most once per
  `min_gap` ticks per cog.
- Priority, highest first: **G, D, X, F, H, E, U, K, R**.
- While sneaking, send only G, D, and X.
- E: repeat a sighting of the same enemy only after `e_refresh` ticks, or when it moved more than
  `e_move` units since the last E about it. Choose the enemy nearest to a teammate's last heard
  position; if none, the nearest to the sender.
- F: repeat every `focus_refresh` ticks while the target is the sender's fight target.
- G: send once when the charge starts. Send again if the target moves more than `g_move` units.
- H: send once per glory heart, and again when a teammate's H for it has not been heard for
  `h_refresh` ticks.
- K: send once per pickup taken. R: send once per station when it changes from not-ready to
  ready in the sender's memory.
- X and D: see §8.

## 8. Disguises

Two cases produce a body with a label that is not its team:

- **An enemy in disguise** appears as one of our seats (`enemySeat xor 1`).
- **Our cog in disguise** appears as one of their seats (`ourSeat xor 1`).

### D: our disguised cog protects itself

- Send D on the first tick that `hasUniform()` becomes 1, if a teammate is visible within
  1,280 units.
- While disguised, send D every `d_refresh` ticks while a teammate is visible within 1,280
  units, and at once if a visible teammate aims at us (inferred from its aim over 2 ticks, if
  possible, else skip this trigger).
- Receivers keep a friendly-disguise record: the apparent label, the position from `heardX/Y`,
  and the tick. A body with that label within `friend_radius` of the record position is a
  friend. Update the record position from the visible body each tick. Drop the record after
  `friend_ttl` ticks without a D, or when the label body attacks (a disguise ends on an attack).
- Risk: an enemy that hears D sees its "teammate" shout text that it cannot read. A policy that
  checks its own messages can use this to find our disguised cog. Send D only when the
  friendly-fire risk is real (a teammate is visible within range).

### X: find a disguised enemy

A cog raises disguise evidence for label `k` (one of our seats) at position `p` when either is
true:

1. A speaker with label `k` sends text that fails our check (§6 step 4).
2. A body with label `k` is visible at `p`, and a valid message from our real seat `k` in the last
   `x_window` ticks came from a position more than `x_distance` units from `p`.

On evidence, the cog treats that body as an enemy and sends X (label `k`, position `p`, age).
Receivers treat the body with label `k` within `x_radius` of `p` as an enemy for `disguise_ttl`
ticks. A D record for the same label and position overrides X.

## 9. Parameters

All become `' @tune` constants where a range is given.

| Name | Default | Range | Units |
| --- | --- | --- | --- |
| `max_decode` | 8 | 4-16 | messages per tick |
| `min_gap` | 6 | 2-24 | ticks |
| `e_refresh` | 12 | 6-48 | ticks |
| `e_move` | 300 | 100-800 | units |
| `focus_ttl` | 36 | 12-72 | ticks |
| `focus_refresh` | 24 | 12-48 | ticks |
| `grenade_clear_radius` | 450 | 250-700 | units |
| `g_move` | 200 | 100-400 | units |
| `danger_ttl` | 48 | 24-120 | ticks |
| `h_refresh` | 120 | 48-240 | ticks |
| `d_refresh` | 24 | 12-72 | ticks |
| `friend_radius` | 250 | 100-500 | units |
| `friend_ttl` | 48 | 24-120 | ticks |
| `x_window` | 24 | 12-72 | ticks |
| `x_distance` | 600 | 300-1500 | units |
| `x_radius` | 300 | 100-600 | units |
| `disguise_ttl` | 72 | 24-240 | ticks |
| `k1`-`k6` | secret | — | — |

Defaults are first guesses, not measured values.

## 10. Budget

| Part | Work units per tick |
| --- | --- |
| Send (`strFromInt` 8 + `strCatInt` 68 + `shout` 68, plus arithmetic) | about 150 |
| Receive, per message (`heardText` 4 + `strLen` 2 + 20 x `strByte` 3, plus arithmetic) | about 150 |
| Worst case (1 send + `max_decode` 8 receives) | about 1,350, 1% of 125,000 |

String pool use: 2-3 handles per send, 1 per received message. Far below the 1,024-handle limit.

## 11. Verify before build

1. **Duplicate labels.** When a disguised body and the real cog answer to the same seat, which
   one do `visible(k)`, `playerX(k)`, and `nearAgent*` return? X and D depend on the answer.
2. **`heardSlot` for our own disguised cog** as heard by a teammate: its disguise or its true
   seat? The message carries the true `senderSeat`, so decoding works either way, but X
   evidence rule 1 must not fire on our own disguised cogs.
3. **`strByte` index base** (0 or 1).
4. ~~The 0.3.89 documentation audit~~ Done 2026-09-30: speech, string costs, disguise, and
   budgets are unchanged at 0.3.89. New reserved name `rnd` (a host builtin): do not use it as a
   variable, array, or SUB name.

## 12. Measure

Telemetry v2 `PWC` lines log every send and every decode (type, fields, sender seat). Checks to
build: sent when it should be; decoded by teammates in range; E/H/K/R facts true against the
replay; F raises kills of the called target; D lowers friendly-fire damage on disguised
teammates; X lowers damage from disguised enemies. The field has no A/B evidence on comms yet
(Stencil was never tested with comms off).

## 13. Sources and prior art

- Stencil protocol (old Paintbot, native Nim player):
  `personal_labs_main/paintbot_lab/docs/stencil-communication.md`. Carried over: enemy sighting
  (E), under fire (U), grenade warning (G), focus claims (F, changed to concentrate fire).
  Dropped: spray carrier (no item visibility here), carrier/thief (no carrying in rules 47),
  presence and squad consensus (out of scope for v1).
- Field protocols ([league field analysis](../docs/reports/2026-09-29-league-field-analysis.md)):
  Aaron's `FIRE22 x z` (enemy call-out at the shooter's aim, about 170 per episode) and
  `ITEM23 k` (pickup taken). Both are plain text and readable by any enemy in range.
- Disguise mechanics: [mechanics.md](../docs/mechanics.md) "Disguise"; the uniform lessons in
  [TENTATIVE_LESSONS.md](../TENTATIVE_LESSONS.md).
