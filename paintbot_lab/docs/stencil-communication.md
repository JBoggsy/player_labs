# Stencil in-game communication specification

This document specifies the communication protocol implemented by the current
native Stencil player. It is a reference for humans inspecting behavior and for
agents changing or interoperating with Stencil. It describes existing behavior,
not a proposed redesign.

**Implementation baseline:** `stencil:v57`, Paintbot 0.7.208, GameVersion 40.
V57 aligns Stencil's shared sender interval with the engine's 24-tick limit.
The message protocol and behavior otherwise remain inherited from v56/v55 and
the retained v52 consensus core.

The application codec and sender live in
[`chat.nim`](../paintbot/stencil_nim/chat.nim). Message effects are applied in
[`belief_update.nim`](../paintbot/stencil_nim/belief_update.nim), leaderless
consensus lives in [`squads.nim`](../paintbot/stencil_nim/squads.nim), and
focus-claim semantics live in [`fight.nim`](../paintbot/stencil_nim/fight.nim).

## Scope

Stencil communicates by putting compact application messages inside Paintbot's
ordinary player-shout channel. There is no separate private or reliable agent
network.

The protocol carries:

- tactical observations: enemy, thief, carrier, grenade, and under-fire;
- local focus-fire claims;
- squad presence pings;
- leaderless squad proposals, votes, and commit echoes.

It does **not** currently communicate ally vision, the `covered` heatmap, the
danger grid, full tracks, health, inventory, or arbitrary paths. Those remain
local beliefs and trace-only instrumentation.

## Transport contract

The underlying Paintbot shout channel defines these constraints:

| property | deployed behavior |
| --- | --- |
| Payload | Printable ASCII, trimmed, at most 10 characters |
| Sender | A living player while the match phase is `Playing` |
| Engine rate limit | One accepted shout per sender per 24 ticks (one second) |
| Stencil rate limit | One selected shout per 24 policy ticks |
| Lifetime | 72 simulation ticks (three seconds) |
| Replacement | A sender's new shout replaces its previous live bubble |
| Range | `mapWidth / 5`, measured from the sender's position when shouted |
| Occlusion | None; shouts travel through walls and fog |
| Recipients | Every living player in range, including enemies |
| Attribution | Team color plus anonymous team-relative identity (`alpha` through `theta`) |
| Observed position | Shout-time position with deterministic jitter of up to ±20 px on each axis |

Dead players hear nothing. Delivery has no acknowledgment, retry guarantee,
ordering guarantee, authentication, or privacy. A listener repeatedly observes
the same live bubble until it expires or is replaced.

Stencil suppresses repeated rendered observations of the same `(team,
anonymous sender, text)` for 80 ticks. It also ignores an own-team message whose
text exactly equals the last text it sent. That self-echo rule is text-based,
not sender-based, so an ally independently sending the same payload may also be
ignored.

Enemy players can read Stencil's payloads if they are in range. Conversely,
Stencil does not decode enemy-team payloads, but it does use any enemy shout's
jittered bubble location as an approximate enemy sighting when
`STENCIL_CHAT_ENEMY_BUBBLE_FIX=1` (the default).

## Common wire fields

All application messages are ASCII with no separators.

### Position: `<cell>`

`<cell>` is four lowercase base-36 characters:

```text
<x-hi><x-lo><y-hi><y-lo>
```

Each pair encodes one unsigned navigation-grid index in `00..zz`. Stencil's
navigation cell is 8 px. The sender clamps a point to the map grid and the
receiver reconstructs the center of that cell:

```text
x = grid_x * 8 + 4
y = grid_y * 8 + 4
```

For example, point `(100, 200)` maps to grid cell `(12, 25)`, encoded as
`0c0p`, and decodes to cell center `(100, 204)`.

### Seat: `<seat>`

`<seat>` is one decimal digit `0..7`. It is the sender's **team-relative seat
identity**, not its global episode slot and not its policy/entrant identity.

### Epoch: `<epoch>`

`<epoch>` is one lowercase base-36 digit `0..z`. The wire epoch is the local
unbounded consensus epoch modulo 36.

### Opponent: `<team>`

`<team>` is one decimal enum digit:

| digit | team |
| ---: | --- |
| `0` | red |
| `1` | blue |
| `2` | green |
| `3` | yellow |

### Directive: `<kind>`

| code | meaning |
| --- | --- |
| `H` | hold near the communicated point |
| `W` | watch from a generated covered post near the point |
| `M` | move to a generated covered post near the point |

## Message catalogue

Lengths below are the emitted lengths. The current decoder generally checks a
minimum length and ignores trailing characters, so implementations should emit
the canonical form even though receivers are permissive.

| message | length | canonical format | receiver effect |
| --- | ---: | --- | --- |
| Enemy sighting | 5 | `E<cell>` | Adds or refreshes an enemy track at the quantized point. |
| Under fire | 5 | `U<cell>` | Stamps danger heat `0.5` in a 32 px radius around the point. |
| Grenade warning | 5 | `G<cell>` | Adds a warning for 72 ticks; nearby agents clear an 80 px area. |
| Heart carrier | 6 | `C<cell><heading>` | Stores a carrier fix for 96 ticks and enables heard-carrier escort. |
| Own-heart thief | 5 | `T<cell>` | Adds an enemy track and stores a thief interception fix for 96 ticks. |
| Presence ping | 6 | `P<seat><cell>` | Marks the embedded seat present now. The point is decoded but otherwise unused. |
| Focus claim, identity | 8 | `FI<seat><identity><cell>` | Claims the identified enemy near the point for local focus-fire deconfliction. |
| Focus claim, coordinate | 7 | `FC<seat><cell>` | Claims an unidentified enemy near the point. |
| Squad proposal | 9 | `Q<seat><epoch><kind><cell><team>` | Adds the sender's directive proposal for the epoch. |
| Squad vote | 9 | `V<seat><epoch><kind><cell><team>` | Adds the sender's locked vote for the epoch. |
| Squad commit echo | 9 | `C<seat><epoch><kind><cell><team>` | Commits only if the directive matches the receiver's locked vote or deterministic local choice. |

The `C` prefix is intentionally overloaded. A nine-character payload matching
the consensus shape is decoded as a commit; otherwise `C<cell><heading>` is a
carrier update.

### Heading octants

Carrier heading is one digit `0..7`:

| value | direction |
| ---: | --- |
| `0` | east, or stationary/unknown |
| `1` | northeast |
| `2` | north |
| `3` | northwest |
| `4` | west |
| `5` | southwest |
| `6` | south |
| `7` | southeast |

The receiver extrapolates a heard carrier for at most 48 ticks at 1.9 px/tick
along this heading.

### Example messages

Using `<cell> = 0c0p`:

```text
E0c0p       enemy near cell (12,25)
C0c0p1      carrier near that cell, moving northeast
P20c0p      team-relative seat 2 is present near that cell
FI230c0p    seat 2 claims enemy identity 3 near that cell
Q2aM0c0p2   seat 2 proposes at epoch 10: move there against green
```

## Sender arbitration

Stencil can send only one message when its 24-tick application cooldown is
open. `chooseShout` uses this strict priority:

1. carrying an enemy heart (`carrier`);
2. own heart stolen with a known thief position (`thief`);
3. consensus commit echo;
4. consensus vote;
5. consensus proposal;
6. active charged-grenade target;
7. under fire without a visible enemy;
8. focus-fire claim;
9. nearest visible enemy sighting;
10. presence ping.

Higher-priority continuous conditions can starve lower-priority protocol
traffic. This is deliberate for carrier/thief emergencies but is not a fair
queue.

Additional default cadences:

- proposal, vote, and commit rebroadcast: every 45 ticks;
- commit echo window after local commit: 120 ticks;
- focus-claim rebroadcast: every 30 ticks;
- enemy sighting: rearmed after 48 ticks without vision, with at least 72 ticks
  between enemy reshouts;
- idle presence ping: every 60 ticks.

All cadences still pass through the shared 24-tick sender cooldown.

## Focus-claim semantics

Focus claims allow focusing targets or reducing duplicated target selection during a local firefight.

- Identity form (`FI`) is preferred when an enemy badge is known; coordinate
  form (`FC`) is the fallback.
- A receiver accepts a claim only when the target or matching recent track is
  within 400 px of itself.
- Claims match by identity when both identities are known, otherwise within
  96 px or through a currently visible matching target.
- A claim lasts 72 ticks and is refreshed every 30 ticks by its owner.
- If conflicting claims first arrive on the same tick, lower `(squad rank,
  seat)` wins. Later conflicting claims are suppressed.
- A claim is released when it expires, its target is missing for 36 ticks, or a
  correlated scoreboard death occurs after at least eight missing ticks. A
  dying agent also releases its own locally held claim; receivers are not
  notified of the claimant's death and clear that remote claim through the
  other rules.

Focus claims coordinate shooting only. They do not create squad orders.

## Squad membership

Squads are fixed functions of team-relative seat, team count, and inferred
muster. They are not discovered from the actual entrant roster.

### Two-team games

Each agent uses its seat parity to select one of these two-seat squads:

```text
even seats: A = [0,2], B = [4,6]
odd seats:  A = [1,3], B = [5,7]
```

This matched the old equal four-agent entrant blocks. It does **not** match the
current campaign's 7+7+1+1 captain/ally seating: a squad may include the foreign
ally or omit Stencil-owned seats. Roster-aware membership is an explicit open
task.

### Four-team games

For four seats per team:

```text
A = [0,1]
B = [2,3]
```

For eight seats per team:

```text
A = [0,1,2]
C = [3,4]
B = [5,6,7]
```

Quorum is `floor(squad_size / 2) + 1`: two votes for every current two- or
three-member squad.

## Leaderless consensus

Consensus runs only when `STENCIL_SQUAD_COMMAND=1`. With v55/v56's early
defense enabled, it is additionally paused until the early-defense gate
finishes.

### 1. Start

An agent starts an epoch when it has no order or its order becomes due:

- any order at 720 ticks old;
- `M` after arrival and at least 120 ticks;
- `W` after 240 ticks;
- `H` after 180 ticks.

It computes a local `H`, `W`, or `M` proposal, quantizes the point to the same
8 px representation used on the wire, and stores its own proposal locally.

### 2. Choose

After receiving proposal quorum, every agent deterministically chooses:

1. the directive kind with the most proposals;
2. on a kind-count tie, safety order `H` before `W` before `M`;
3. among proposals of that kind, the coordinate medoid;
4. on a medoid tie, lowest `(opponent enum, x, y)`.

### 3. Lock and vote

The first local vote for an epoch is immutable. The same locked value is used
for local storage, quorum counting, and rebroadcast. This is the retained v51
safety fix.

### 4. Commit

Matching-vote quorum commits the directive. A commit echo from another member
is accepted only if it matches either the receiver's locked vote or the
receiver's deterministic choice from proposal quorum. Committing:

- installs the order with source `consensus`;
- increments the local epoch;
- clears proposal/vote state;
- echoes the commit for up to 120 ticks.

There is no designated leader and no privileged sender.

### Epoch resynchronization

Epochs are compared on a 36-value ring. A received epoch is accepted as
forward progress when its modular delta is `1..18`. The receiver advances,
clears in-progress state, and records a resync. Deltas `19..35` are treated as
stale/backward and rejected.

### Timeout and physical rejoin

An uncommitted epoch times out after 480 ticks. A living member then moves for
up to 360 ticks toward its most recently observed squadmate position; if none
exists, it takes a homeward step. Rejoin ends on timeout or when a visible
squadmate is within 160 px.

This mechanism does not guarantee liveness. Shout retries cannot repair a
physical partition, and hosted tests observed concurrently living members
remaining multiple epochs apart. The static last-known-position rejoin is the
retained v52 checkpoint, not a validated solution.

## Presence

Presence is updated by:

- direct visual observation of an identified squadmate;
- accepted proposal, vote, or commit from an embedded squad seat;
- any decoded same-team `P` ping.

A squadmate is considered live/present for 190 ticks after the latest update.
The embedded seat is trusted; the transport provides no proof that the
physical sender owns that seat.

## Trust and interoperability

The protocol assumes cooperative Stencil senders but does not authenticate
them.

- Any same-team policy can emit a syntactically valid Stencil message.
- Proposal/vote/commit handlers reject embedded seats outside the receiver's
  fixed squad and reject the receiver's own seat, but do not bind the embedded
  seat to the anonymous bubble author.
- Pings and focus claims similarly trust the embedded seat.
- Foreign allies normally ignore Stencil messages and may unknowingly emit
  text that parses as one.
- Enemy listeners can decode the entire protocol from observed text.
- Enemy/thief tactical messages currently create an enemy track with a
  placeholder `red` color. In four-team games this does not preserve the
  reported enemy's actual team identity.

These are current implementation facts, not desired security properties.

## Telemetry and diagnosis

V56 artifacts expose communication through:

- snapshot fields: `squad_consensus`, `squad_order`, `presence_age`,
  `orders_sent`, `orders_heard`, `pings_sent`, and `pings_heard`;
- counters: `chat_sent`, `chat_heard`, proposal/vote/commit counts, consensus
  commits/timeouts/resyncs, and focus-claim counts;
- point events: `squad_consensus`, `squad_order`, and related follow-state
  transitions.

Use the [belief replay viewer](../tools/viewer.html) to inspect one
agent's local state. Do not infer delivery from a visible speech bubble alone:
the receiver may be dead, outside range, deduplicating the bubble, ignoring a
self-text echo, rejecting its embedded seat/epoch, or prioritizing a different
outgoing message.

## Configuration switches

The principal gates and timings are defined in
[`config.nim`](../paintbot/stencil_nim/config.nim):

- `STENCIL_CHAT` — all Stencil shouts;
- `STENCIL_CHAT_MIN_INTERVAL_TICKS` — sender arbitration interval;
- `STENCIL_FOCUS_CLAIMS` — focus-claim send/receive behavior;
- `STENCIL_SQUAD_COMMAND` — proposal/vote/commit and presence-ping behavior;
- `STENCIL_CONSENSUS_REBROADCAST_TICKS`;
- `STENCIL_CONSENSUS_COMMIT_ECHO_TICKS`;
- `STENCIL_CONSENSUS_TIMEOUT_TICKS`;
- `STENCIL_PING_INTERVAL_TICKS`;
- `STENCIL_PRESENCE_STALE_TICKS`;
- `STENCIL_REJOIN_TIMEOUT_TICKS` and `STENCIL_REJOIN_CONTACT_PX`.

Changing a default changes protocol timing and therefore requires a new player
version and hosted validation.

## Known limitations requiring design decisions

1. **Campaign roster mismatch:** fixed two-team parity squads do not represent
   7+7+1+1 ownership.
2. **No bounded reconnection:** retries and epoch resync do not restore physical
   shout contact.
3. **No authentication or version field:** same-team spoofing and accidental
   cross-policy parsing are possible.
4. **Public payloads:** enemies in range hear every tactical and consensus
   message.
5. **Single-channel starvation:** emergency traffic can indefinitely delay
   consensus and presence traffic.
6. **Lossy coordinates:** every point is quantized to an 8 px cell and then
   observed at a jittered bubble position; only the encoded cell is meaningful
   to a cooperating receiver.
7. **Incomplete multi-team identity:** `E` and `T` do not carry enemy team.

Any redesign should state which of these it addresses, preserve a compatibility
story for mixed Stencil versions, and define a falsifiable safety and liveness
gate before implementation.
