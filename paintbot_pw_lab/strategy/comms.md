# Comms v1: team messages over `shout`

> **Status:** M3 implementation and acceptance complete, 2026-10-05. The codec and compact telemetry
> reader have engine-backed tests; all nine strategy components passed G1–G5 in build
> `18e0aa1f-1`. Local and hosted transport are qualified; the hosted A/B is inconclusive.
> The [qualification record](../docs/designs/2026-10-05-m3-qualification.md) retains failed truth checks. This is a policy specification, not a change to the strategy format.
> Engine behavior is verified at `coworld-v0.3.115`
> (`244dc62b38a8a89721cbb1625f05a99ca60d0c13`, rules49).

## 1. Scope

Comms v1 carries tactical facts that teammates cannot see for themselves: enemies, danger,
grenades, glory hearts, pickups, and disguises. It does not carry squad coordination or the
sender's own position; those come later.

Security goal for v1: **lightweight scrambling**, as chosen by James. The 97-value check
is not authentication: forged or stale messages can pass, and a failed check is uncertain
disguise evidence. Neither successful decoding nor failure proves a speaker's identity.
Public replays expose the text, tick and true sender, so offline analysis can recover the
protocol. Do not use these constants to protect real secrets.

## 2. Transport facts (engine, `coworld-v0.3.115`)

| Fact | Value | Source |
| --- | --- | --- |
| Send | `shout(handle)` queues the text. At most 4 per cog per tick; the 5th returns 0. | `examples/paintbot/bots.nim`, shout host |
| Length | Text over 256 bytes is cut to 256 bytes. | `bots.nim`, shout host |
| Cost | Flat per call, not per character: `shout` 68 WU. | `bots.nim`, shout host |
| Delivery | Next tick, to every living cog within `Width div 5` = 1,280 units (12.8 m) of the sender at decision time, **both teams**, no line of sight needed. Dead cogs neither send nor hear. | `examples/paintbot/seat_view.nim`, `deliverSpeech`; `game.nim`, advance |
| What a listener gets | `heardText(i)` (text), `heardX/heardY(i)` (sender's **true** exact position), `heardSlot(i)` (sender's **observed** seat: a disguised sender shows its disguise). Messages last one decision only. | `seat_view.nim`, heard accessors |
| Replay | Every shout is recorded with tick, true seat, and text (first 20,000 per episode). | `game.nim`, recorded communications |
| Strings | Pool resets every tick: 1,024 handles, 64 KiB, 1,024 bytes per string. `strFromInt` 8 WU, `strCatInt` 68, `strByte` 3, `strLen` 2, `heardText` 4 (allocates a handle), `strChr` 6 (bytes 0-255). | `src/polyworld/basic.nim`, string hosts |
| Arithmetic | Signed int32, wraps on overflow. `AND`/`OR`/`XOR` are logical (0/1), not bitwise. | `docs/policy-surface.md` §2 |
| Disguise | A disguised cog appears to others as seat `slot xor 1` and as the other team. The disguise ends on a gun order, spray burst, grenade release, or death. Hearts use the true team. | `docs/mechanics.md` "Disguise" |

## 3. Principles

1. **Send only what teammates cannot see.** Heart ownership, capture, and contest state are
   public to every cog. We send no heart messages.
2. **The sender's position is free.** Every heard message has the sender's exact position. A
   message about "here" carries no coordinates.
3. **A shout reveals the sender.** Every enemy within 12.8 m gets our exact position, whatever the
   text says. Do not send non-urgent messages while sneaking.
4. **All 8 seats on our team run this policy.** A failed check from a teammate label is
   uncertain evidence only. A malformed, incompatible or forged message is not proof of an
   enemy, and a failed check alone must not trigger friendly fire.
5. **Received facts are beliefs.** Each received fact goes into Knowledge with source `heard` and
   an age. A seen fact replaces a heard fact about the same thing.

## 4. Message catalogue

| Code | Type | Message | Sent when | Receiver effect |
| --- | --- | --- | --- | --- |
| E | 0 | **Enemy sighting** | sender sees an enemy (refresh rules in §7) | Add or refresh the heard track consumed by `K.contacts`; it steers looking, not a fire target. |
| F | 1 | **Focus call: shoot this target** | sender selects a fight target that is wounded or that two or more teammates can engage | Each receiver that sees the target prefers it as its fight target for `focus_ttl` ticks. Focus concentrates fire. It does not spread fire. |
| G | 2 | **Grenade out** | sender starts to charge a grenade at a target | Keep out of `grenade_clear_radius` of the target until the release tick plus 24 ticks. |
| U | 3 | **Under fire, no shooter visible** | sender loses HP and sees no enemy | Mark a danger area at the sender's position (`heardX/Y`) toward the gunfire direction for `danger_ttl` ticks. |
| H | 4 | **Glory heart seen** | sender sees a glory heart | Add it to `K.glory_hearts` with its expiry. |
| K | 5 | **Pickup taken** | sender takes a pickup | Mark the station empty until the ready tick in `K.pickups`. |
| R | 6 | **Pickup ready** | sender sees a ready station that is not marked ready in its memory | Mark the station ready in `K.pickups`. |
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
of that grid square. Cell size follows the map bounds; receivers reconstruct the center of the cell.

| Code | fieldsA | fieldsB | cell |
| --- | --- | --- | --- |
| E | `enemySeat + 16 * (hp + 16 * heading)`; `heading` 0-7 octant, 8 unknown | age of the sighting in ticks, max 255 | enemy position |
| F | `targetSeat + 16 * hp` | 0 | target position |
| G | ticks until release, 0-24 | 0 | grenade target |
| U | `myHp + 16 * gunDir`; `gunDir` 0-7 from `soundDirection`, 8 unknown | gunfire distance class 0-2 from `soundDistance`, 3 unknown | 0 (use `heardX/Y`) |
| H | ticks left, 0-720 | 0 | glory heart position |
| K | pickup id, 0-255 | ticks until ready, 0-720 | pickup position |
| R | `pickupId + 256 * kind` | 0 | pickup position |
| X | fake label seat | age of the evidence in ticks, max 255 | position of the fake body |
| D | apparent label seat (`selfId xor 1`, computed as `selfId + 1 - 2 * (selfId MOD 2)`) | 0 | 0 (use `heardX/Y`) |

Enemy seats are observed seats (what `visible`/`playerX` answer to). HP uses base16
because the active engine starts cogs at 10 HP. HP is 0–15, pickup kind 0–15; encoders reject
values outside the catalogue. The largest fieldsA is 4095 (R), so pA is at most 104857599.

### 5.2 Check

```text
core  = type + 16 * (senderSeat + 16 * fieldsA)
check = ((core MOD 97) + 7 * (pB MOD 97) + ((sendTick MOD 9973) * k5) MOD 97 + k6) MOD 97
```

`k5` and `k6` are constants below 97. The check depends on the send tick, but collisions
are possible; this is not a replay-prevention or authenticity guarantee.

### 5.3 Scrambling

For block `b` (0 = A, 1 = B) and send tick `t`:

```text
h1   = ((t MOD 30011) * k1 + k2 + b * k3) MOD 30011
h2   = (h1 * h1 + k4) MOD 32749
mask = h1 * 32768 + h2                                  (always below 1,000,000,000)
s    = (p + mask) MOD 1,000,000,000                     send
p    = (s - mask + 1,000,000,000) MOD 1,000,000,000     receive
```

`k1`–`k4` are constants below 30011. Every product stays below 2^31. The initial constants
are 7919, 17431, 23117, 1907, 31, 73, in that order; they are protocol parameters, not credentials.
The compiler records them in the immutable build map. The independent reference is
`tools/strategy_comms.py`; the authored BASIC implementation is
`strategy/compiler/runtime/comms.bas`.

## 6. Receive procedure (each tick, before Knowledge updates)

1. `sendTick = worldTick - 1` (delivery is always the next tick).
2. Scan the heard list in engine order. Read each text once. Skip texts whose length is not 20
   or whose bytes 0 and 10 are not 49. `strByte` is zero-based; check length first.
3. Attempt full decode on at most `max_decode` matching candidates. Validate every remaining
   digit, unscramble, check the catalogue bounds and recompute the check.
4. Accept only a decoded sender on our own team, excluding our own seat (speech is not
   delivered to its sender). Keep accepted payloads and call that type's receiver immediately,
   in heard order. Save the true-sender claim and heard position with a tick.
5. A failed check from a teammate label may update uncertain disguise evidence. A message
   skipped because the decode capacity was exhausted is not a failed check.
6. A seen fact replaces a heard fact about the same object. Heard facts carry their age.

Shape filtering prevents ordinary enemy chatter from consuming full-decode capacity.
The audit reports capacity exclusions separately from accepted and rejected packets; near 100%
decode acceptance is measured over eligible deliveries, not all audible texts.

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
  This reports the intended target, not a guaranteed landing. In the first local sample,
  early charge release caused two throws to land 530 and 929 cm from that target.
  The declared 150 cm landing check fails those cases; it is not weakened to hide them.
  The baseline motor can stop charging when its target or safety conditions change.
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
  `friend_ttl` ticks without a D, The host does not expose a teammate's attack or uniform state, so this implementation
  cannot reliably invalidate the record at the instant of an attack; it expires by TTL.
  A different body under the same label can therefore be protected incorrectly. The audit
  must report that as uncertain or false protection, not guaranteed identity.
- Risk: an enemy that hears D sees its "teammate" shout text that it cannot read. A policy that
  checks its own messages can use this to find our disguised cog. Send D only when the
  friendly-fire risk is real (a teammate is visible within range).

### X: find a disguised enemy

A cog raises disguise evidence for label `k` (one of our seats) at position `p` when either is
true:

1. A speaker with label `k` sends text that fails our check (§6 step 4).
2. A body with label `k` is visible at `p`, and a valid message from our real seat `k` in the last
   `x_window` ticks came from a position more than `x_distance` units from `p`.

Either evidence type can cause an X alert. Targeting a teammate-labeled body requires
one of these stronger conditions:

- Our own visible conflicting-position evidence from case 2.
- Matching X reports from two distinct teammate sender claims, within `x_radius` of the same
  body and within `disguise_ttl`. Repeats from one sender do not count as two witnesses.

A failed check alone does not change targeting. Reports expire according to their evidence
age; receiving one does not reset its age. A matching D record overrides X. These are still
uncertain beliefs: scrambling does not authenticate the two claimed witnesses, and spatial
conflict can be mistaken. Telemetry must retain the evidence needed to audit this distinction.

## 9. Parameters

All become `' @tune` constants where a range is given.

| Name | Default | Range | Units |
| --- | --- | --- | --- |
| `max_decode` | 8 | 4-8 | full-decode attempts per tick |
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
| `x_distance` | 1000 | 700-1500 | units |
| `x_radius` | 300 | 100-600 | units |
| `disguise_ttl` | 72 | 24-240 | ticks |
| `k1`-`k6` | see §5.3 | fixed per build | scrambling constants |

Defaults are first guesses, not measured values. The initial conflict threshold is 1000,
above 24 ticks of normal walking (672 units) plus position uncertainty; the earlier 600 draft
could flag a moving teammate. This is a new communication parameter, not baseline tuning.

## 10. Budget

| Part | Work units per tick |
| --- | --- |
| Send (`strFromInt` 8 + `strCatInt` 68 + `shout` 68, plus arithmetic) | about 150 |
| Receive, per message (`heardText` 4 + `strLen` 2 + 20 x `strByte` 3, plus arithmetic) | about 150 |
| Worst case (1 send + `max_decode` 8 receives) | about 1,350, 1% of 125,000 |

String pool use: 2-3 handles per send, 1 per received message. Far below the 1,024-handle limit.

## 11. Verified engine details and remaining choices

- Duplicate apparent labels resolve to the nearest visible body, except querying the
  observer's own label always returns self. The near-agent surface uses the same deduplication.
- Heard positions are the true speaker's coordinates; heard labels use observed disguise.
  The usual disguise is `slot xor1`, but when that equals the observer's own label the engine
  uses `(alias+2) MOD16`. D/X receivers must account for this remapping.
- `strByte` is zero-based. Runtime string handles are not printable text: BASIC PRINT
  prints their integer handle. Numeric fixed-width batch records avoid that problem.
- There is no teammate aim surface for the optional D aim trigger; omit that trigger.
- Pickup-taking notices need an observable attribution rule; disappearance alone does not
  prove that we took a pickup.
- James chose corroboration before targeting: our own conflicting-position evidence or
  matching reports from two distinct teammate sender claims. A failed check alone never
  authorizes friendly fire. D protection for the same body takes precedence.

## 12. Measure

Compact batches retain every accepted decoded payload and actual outgoing payload while
keeping the 512-byte and 64-event telemetry limits. The physical line is:

```text
PWC v=3 t=<decision tick> b=<concatenated 20-digit records>
```

Each receive record is `(1000000000+pA)(1000000000+pB)`; the optional final send record is
`(2000000000+pA)(1000000000+pB)`. Each parenthesized integer has exactly 10 digits. Catalogue
bounds keep the send marker inside signed int32. A batch has at most 8 receives and 1 send;
an empty batch emits no line. The receive check uses decision tick minus 1; the send check
uses decision tick. The build map binds wire types to COM codes and records the six constants.

Flush once after the tick's priority snapshots. Reserve its print budget when adding records,
before optional snapshots consume spare capacity. The reader expands each batch into ordinary
PWC events with `d=[pA,pB]`; the audit places those receives before Knowledge and the send after
the capability. It rejects duplicate batches or later same-tick telemetry. Ordinary v2 events
retain their existing order validation. G5 charges physical bytes once while covering all
expanded events. Old immutable builds retain their v2 reader.

This is lossless for accepted packets and the actual send. Rejected messages, capacity skips
and heard-list indices are reconstructed from replay delivery and the deterministic scan;
they are not invented from an absent log entry.

Acceptance requires eligible teammate decode rate near 100% in local recordings and a hosted
A/B against the qualified unchanged baseline `567feb38-1` on the same release. Checks include
send eligibility and arbitration; E/H/K/R truth; receiver effects; and F/D/X outcomes, with
unmeasurable causal claims left explicit. A/B uses the live ranking's verified score margin
scale (600 at the current lookup), with no claim of improvement from an inconclusive result.

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


## 14. Telemetry coverage for rare events

James chose event-based coverage for M3. G5 still requires valid logs, unconditional fields
and priority snapshots from every candidate seat. Across the recording set it must exercise
both the communication send and receive paths. It reports counts for each message type;
a type with no event is `not_exercised`, not a failed wire-format check and not a passed
semantic check. Missing unconditional fields, malformed batches, wrong sender/team claims
in our own logs, and wholly unexercised send or receive paths still fail G5.

Catalogue engine fixtures verify the codec for all types but are not evidence that an exact
compiled strategy triggered those types. Local qualification and hosted evaluation expand
exact-build evidence; any remaining absence stays visible in the build and audit reports.
