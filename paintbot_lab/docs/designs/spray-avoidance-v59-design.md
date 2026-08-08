# stencil v59 — enemy loadout belief + spray-can avoidance

*2026-08-08. Living document; updated as the implementation reveals new
information.*

Built against canonical **Paintbot 0.7.215 / GameVersion 41**, source
`6c7a4c0e0be35bdcf738137595ccbcb4b4c79bf9` (`tools/versions.env`). **Every
engine `file:line` below was re-verified against that ref on 2026-08-08.**

> **Revision 2** — the first draft was reviewed adversarially (by Codex) against
> the engine source and did not survive intact. Corrected here: the shield model
> was wrong (there is no "spent shield" state), the citations were pinned to the
> pre-re-pin ref, "retreat while shooting" was false, the coverage primitive
> measured vision rather than gun coverage, the shout format was ambiguous in
> four-team games, and the flee scoring was underspecified in a dozen places.
> The **Resolved ambiguities** section exists so that gets caught by contract,
> not by review, next time.
>
> **Revision 3** — a second adversarial pass found four more, all verified
> against source before accepting: the fire-freeze exemption has to govern the
> shot's trigger tick as well as the hold ticks; an identical repeat shout is
> swallowed by the receiver's same-text dedup, so a *stationary* sprayer would
> never refresh (hence the epoch); shout-sourced tracks need explicit provenance
> and merge rules or jitter degrades an exact sighting; and `navigate()` routes
> through A\*, so the executed path was not the path being scored.

## Problem

The spray can is the deadliest ordinary weapon in Paintbot and stencil is blind
to it. Two separate gaps:

1. **Stencil does not know what an enemy is holding.** The wire states it
   outright — `identity <color> <name>[ shield][ nade] <weapon>`, one badge per
   visible player — and `perception.nim:89-99` parses the badge, takes the name
   token, and discards the rest. `Enemy`/`PlayerTrack` (`types.nim:22-47`) carry
   no weapon or grenade field at all.
2. **Nothing avoids the cone.** No rung, no radius, no term anywhere in the
   objective ladder or the movement resolver reacts to a spray carrier.

### Why one touch is lethal

| quantity | value | source (`6c7a4c0e`) |
|---|---:|---|
| `PlasmaArcDamage` | **3** | `sim_types.nim:529` |
| `hitPoints` (every deployed variant) | 3 | deployed manifest `config_schema` |
| lethal reach = `PlasmaArcReach` + `PlasmaArcBodyRadius` | 170 + 17 = **187px** | `sim_types.nim:505,517` |
| cone half-width at forward distance `d` | `0.25·d + 17` px (14.0° half-angle) | `sim.nim:855-870` |
| cone direction | **locked at fire** (GV38), origin rides the owner 5 ticks | `sim.nim:839-842,889-892` |
| refire cadence | `ActiveTicks 5` + `ResetTicks 20` = **25 ticks** (~1.04s) | `sim_types.nim:532,534` |
| victim gate | `paintPathClear` — walls block, and standing cardboard blocks | `sim.nim:619,871` |
| gun disabled while carrying a can | `canFire` requires `not hasPlasmaArc` | `sim.nim:820-825` |

Three consequences drive the design. Each is stated with its limit, because the
first draft overclaimed all three:

- **A shield usually survives a cone, but does not provably survive one.**
  `absorbDamage` drains the shield layer first and spills the remainder into base
  hp (`sim.nim:802-810`), so survival needs `hp + shieldHp > 3`. A full layer on
  full hp is 6 and comfortable; 1 hp behind a 1-point layer dies. Stencil cannot
  observe the split — the overhead bar is `lit = min(3, hp + shieldHp)`
  (`global.nim:5953-5954`), so everything from 3 to 6 reads as a full bar.
  **Decision: keep the shield gate anyway** — it is right in the large majority
  of positions — and track the layer properly later (see *Deferred: shield-HP
  tracking*).
- **A spray carrier cannot fire the gun — but is not harmless.** It can carry and
  throw a grenade: `tryPickupGrenades` excludes only another grenade or a barrier,
  never a can (`sim.nim:1796-1807`). Retreat is still strongly favourable (we
  outrange the can 1300:187) but it is not *strictly* dominant.
- **Equal speed is a property of today's config, not of the engine.** `MaxSpeed
  704` = 2.75 px/tick (`sim_types.nim:320`), but the effective value is modified
  by heart carrying, per-team handicap, perks (`thruster`), and acceleration
  (`sim.nim:2087-2105`). Under every currently deployed variant the unladen
  matchup is symmetric, so a committed chaser never loses ground to radial
  flight — **the keep-out must be preventive, not reactive** — but the design
  must not assume symmetry as an invariant.

Spray is also not the only one-touch kill: a grenade landing in the victim's own
trench deals `GrenadeTrenchDamage 6` (`sim_types.nim:480`). It is the only
*direct-fire* weapon that one-touches a healthy player in open terrain.

## Goals / non-goals

- **Goal**: stencil knows every visible enemy's weapon, grenade, barrier, and
  shield state, and remembers it on tracks.
- **Goal**: stencil keeps out of spray range when a hit would likely be lethal,
  and when it must flee it flees *through terrain its allies can shoot into*,
  without dragging the sprayer onto them.
- **Goal**: the whole thing is a tunable surface, so the flee policy can be swept
  rather than guessed.
- **Goal**: allies who never saw the can still avoid it (shout propagation).
- **Non-goal — team perks.** Team-scope, a different marker, no consumer, off in
  every deployed variant. `armor` (+1 max hp → 4 hp survives a cone) is the one
  that would change this math.
- **Non-goal — barrier fetch/place behavior.** This adds the *belief field* only.
- **Non-goal — wiring the unused `danger` grid into A\*.** `belief.danger` is
  built, decayed, dilated and stamped every tick (`belief_update.nim:225-293`)
  and read by nothing but `trace.nim`. Real finding, unmeasurable if folded in here.
- **Non-goal — retrofitting `clear_grenade` onto the coverage primitive.** Built
  general, applied to one rung, measured once.
- **Non-goal — fixing spray-carrier over-aggression.** See *Known adjacent defect*.
- **Not a non-goal, contrary to revision 1**: this change *does* alter item-fetch
  and target-scoring behavior as a side effect of repairing dead fields. That is
  declared and flagged, below, rather than denied.

## Part 1 — loadout belief

### The channel

`labelIdentity` (`labels.nim:477-498`) pins the invariant: optional flags first
in a fixed order (`shield` before `nade`), and **the weapon token is always last
and always present**, precisely so an observer never infers "gun" from absence —
absence is also what a truncated or fog-dropped badge looks like. The manifest
carries the suffixed forms (`tests/label_manifest.txt:40-43`), so this is
contract, not chrome. `docs/RULES.md` documents the badge without suffixes and is
stale; RULES itself states the manifest wins.

> **Verification limit.** `global.nim` and the golden manifest were read from the
> repo at this ref, but the *emitted* stream was not observed. The claims that
> badges appear on the player stream for every visible player, and that the
> viewer's own badge is emitted, are read from source
> (`global.nim:5734+`, gate `if viewerIndex >= 0 and i != viewerIndex and not
> visible: continue`), not from a captured episode. The mechanism probe (below)
> is what turns them into observed fact.

### Types

```nim
EnemyWeapon* = enum WeaponUnknown, WeaponGun, WeaponSpray
Loadout* = object
  weapon*: EnemyWeapon
  grenade*, shield*, barrier*: bool
```

`Enemy` and `PlayerTrack` each gain `weapon`, `hasGrenade`, `hasBarrier`, and a
corrected `shielded`. Tracks persist last-known loadout through the existing copy
sites (`belief_update.nim:79-110`), so a fogged sprayer stays feared.

### Parsing

`identityBadges` returns the parsed `Loadout` alongside `(identity, pos)`;
`playersOfColor` attaches it on the **existing** badge→body proximity match — no
second pass, no new matcher.

**Self-badge exclusion.** Our own badge is emitted, but our body is labeled
`self <color> <side>`, not `player <color> <side>`, so `playersOfColor` never
consumes it and the orphan can proximity-attach to a nearby teammate. Take the
own-color badge nearest `selfXy` as ours, use it for own loadout, exclude it from
teammate matching — the `selfHpMarker` idiom (`perception.nim:241-250`). This is
defensive correctness, not a verified-from-capture bug.

`hasBarrier` has no badge token; it comes from the `barrier carried` overhead
marker (`labels.nim:63`) folded into the existing `carried` table in
`attachOverheadState`, the path `shield carried` already uses. Costs nothing
while `barrierPickups` defaults to 0.

### The shield model — corrected, and a dead observable

**There is no "spent shield" state.** When the layer breaks, `absorbDamage` sets
`hasShield = false` and re-clamps the cooldown: *"A broken shield is GONE: the
carry icon, the ' shield' label, and the fire slowdown all end with the bubble"*
(`sim.nim:802-818`). So `hasShield` ⟺ `shieldHp ≥ 1` ⟺ the badge's `shield`
token (`labels.nim:244-247`).

**Consequence: `shield carried` is unreachable.** Its emit site guards on
`hasShield` and then requires `shieldHp <= 0` (`global.nim:5255-5270`) — a
combination the engine cannot produce, since pickup sets both together
(`sim.nim:1850-1866`) and the break clears the flag. The label is dead.

Stencil sources **both** `enemy.shielded` and `iHaveShield` from that marker
alone (`perception.nim:266-286,333-338`). Both are therefore **permanently
false**, and three consumers are dead code today:

| consumer | today | after |
|---|---|---|
| `fight.nim:133-141` shield term in `scoreTarget` | always 0 | live |
| `action.nim:336-338` grenade-target gate | always false | live |
| `items.nim:69-72` "already hold a shield, skip it" | never skips | skips correctly |

The fix is one line of source change — read `shielded` from the badge token — but
it **reactivates three behaviors at once**, which is a confound for a v58-vs-v59
A/B that is nominally about spray avoidance. Mitigation: `STENCIL_SHIELD_AWARENESS`
(default on). It gates the three **consumers** and the flee exemption — never the
parsing or the trace. Belief and telemetry always carry the truthful shield state,
or the flag would make the trace lie about what stencil could see. `shieldDown` and `iShieldUp` from revision 1 are dropped
— they described a state that does not exist.

### Deferred: shield-HP tracking (TODO, not in v59)

The gate wants `hp + shieldHp > 3`; stencil can observe neither term exactly. The
hp bar saturates (`lit = min(3, hp + shieldHp)`, `global.nim:5953-5954`), so it
is useless while shielded. **Hit detection is available**: every absorbed hit
pushes a `BubbleImpactFx` (`sim.nim:961` gun, `:1327` grenade, `:1666` spray)
which renders the bubble as `"shield bubble hit"` for `BubbleImpactTicks 8`
(`global.nim:5316`, `sim_types.nim:605`).

A later change can therefore estimate the layer: start at `ShieldLayerHp 3` on
pickup, decrement once per bubble-hit episode (deduplicating within the 8-tick FX
window), reset on pickup and on death/respawn, and treat the badge's `shield`
token vanishing as authoritative proof the layer is gone. Caveat to record now:
`"shield bubble hit"` is an **inline label, absent from `labels.nim` and the
golden manifest** — usable, but an unpinned dependency the engine owes no
stability promise for.

## Part 2 — the `clear_spray` rung

Placed in `decideObjective` immediately after `clear_grenade`, above barrage
centering — **below `carry_home` and `intercept_thief`**. A heart carrier moves
at `carrierSpeedPct 70` and cannot outrun a sprayer anyway, so fleeing forfeits
the win condition *and* probably still dies. Stated as a known gap, not hidden.

- **Threat set**: spray-weapon enemies, taken from `enemyTracks` only (visible
  enemies already have age-0 tracks; using both double-counts). A track is a
  threat while `tick - track.lastTick <= SprayThreatTtlTicks`.
- **Threat position**: `track.pos` advanced by `track.vel` over the track's age,
  clamped to the map, when `vel` is known and the track is stale by more than one
  tick; otherwise `track.pos`. A 48-tick-old track is otherwise up to 132px wrong.
- **Gate**: skipped when `iHaveShield` (per the decision above), and skipped
  entirely when `not SprayAvoid`.
- **Keep-out disc with hysteresis**: a `sprayFleeActive` latch on `Belief` (not
  inferred from the previous objective — `decideObjective` is stateless across
  ticks). Set when the nearest threat is within `SprayFleeTriggerPx`; cleared
  when the nearest threat exceeds `SprayFleeReleasePx`, when the threat set
  empties, when `iHaveShield` becomes true, or on death. **A `Hold` fallback does
  not clear it** — holding is still fleeing.
- **Not the cone.** Enemy aim in a player view is 16-step sprite quantization,
  and at `aimTurnRate 5` a sprayer re-aims 90° in ~13 ticks. The cone describes
  the last 5 ticks, not the next 25.

### The fire-freeze rule

Revision 1 claimed "we retreat while shooting". **False.** Every shot does
`mask = mask and not MovementMask; state.fireHoldTicks = FireWindupTicks`
(`action.nim:519-522`), and `let freeze = state.fireHoldTicks > 0 and not
carrying` then discards all movement for those 5 ticks (`action.nim:445-449`).
Firing at the sprayer *stops the retreat*.

Stutter-stepping is acceptable **only while the pause cannot be punished**. A
5-tick freeze lets a chaser close `FireWindupTicks × MaxSpeedPxTick` = 13.75px,
so the freeze is permitted only when

```
nearestThreatDistance > SprayLethalReachPx
                      + FireWindupTicks · MaxSpeedPxTick
                      + SprayFireFreezeMarginPx
```

Below that, `clear_spray` joins `carrying` in the freeze exemption: keep moving
and accept the accuracy cost, because a cone touch is fatal and a missed shot is
not.

**The exemption must govern two sites, not one.** `action.nim:446` skips movement
during the *following* hold ticks, but the shot's own trigger tick independently
zeroes the mask at `action.nim:519-521`. Exempting only the first leaves one
frozen tick per shot — enough to matter at a boundary this tight.

### Suppression is mandatory, not cosmetic

`action.nim:491-496` lets spray pursuit **overwrite the movement mask** whenever
we hold a can and a target sits in the 100-400px band. Without adding
`"clear_spray"` to that exclusion list the rung is silently overridden and the
feature does nothing. Same for peek-duck (`action.nim:227-231`) and Hold-state
separation drift (`action.nim:464-471`). This mirrors what v58 did for
`barrage_center`.

### Flee-point scoring

Candidates: 16 directions × 2 radii (`SprayFleeStepPx`, 2×). Each term is
normalized to `[0, 1]` so the weights are comparable in a sweep — revision 1 left
`clumpPenalty` as an unbounded count, which broke that.

```
score(P) = W_threat · threatGain(P)
         + W_cover  · coverPath(P)
         − W_clump  · clumpRisk(P)
         + W_center · centerTerm(P)
```

| term | definition |
|---|---|
| `threatGain(P)` | `clamp(min over threats of dist(P, threat) / SprayFleeReleasePx, 0, 1)` |
| `coverPath(P)` | weighted mean of `coverageAt` over `SprayCoverSamples` points at `i/n` for `i` in `1..n` — **the self point is excluded**, since including it adds an identical constant to every candidate. Sample `i` is weighted `1 + (SprayCoverFarBias − 1)·(i−1)/(n−1)` |
| `clumpRisk(P)` | **path-sampled, not endpoint-only**: over the same sample points, take the largest count of **visible teammates** within `SprayClumpRadiusPx` of any single sample, normalized `clamp(maxAlliesAtAnySample / SprayClumpNormAllies, 0, 1)`. Visible teammates only — clumping is about bodies actually there, and a remembered position is not evidence of one |
| `centerTerm(P)` | `clamp(1 − dist(P, map.center) / BarrageCenterRadiusPx, 0, 1)`, and **0 unless `belief.barrage.depth > 0`** |

Endpoint-only clumping fails the stated goal: the chosen path can run straight
through allies even when its endpoint is clear, and a pursuer hits them en route.
Path sampling is the fix. **This remains a heuristic** — seats score against
allies' *current* positions, not their simultaneous destinations, so two stencil
seats can still pick the same covered corridor. Genuine collective non-clumping
needs destination coordination through the squad protocol; out of scope, recorded.

Deterministic tie-break on equal score: smaller direction index, then inner ring
before outer. Fallback when every candidate is rejected: move directly away from
the *nearest* threat (not a sum, which can cancel to zero with two opposed
sprayers); if that too is unwalkable, `Hold`, leaving the latch set.

### The scored path must be the executed path

`navigate()` routes non-flow reasons through `astarWaypoint`
(`action.nim:450-453`), so an A\* route can bend away from the straight segment
that coverage and clump were scored on — scoring one path and walking another.
Since the candidate segment is validated walkable in the first place, the flee
step **steers directly along the scored segment** rather than re-planning
through A\*. Short hops (96-192px) are exactly the case where A\* adds nothing.

### Candidate validation must not use `walkableSegment`

`walkableSegment` re-checks a 13×13 pixel footprint at every 2px sample
(`worldmap.nim:194-213`). Validating 32 candidates costs on the order of 400k
wall lookups per fleeing agent per tick — ~6M across 16 seats — which dwarfs the
coverage rays this design did budget.

It is also **redundant**: `map.walkable` is already footprint-eroded by
summed-area `erode` (`worldmap.nim:79+`), so walking the nav cells along the
segment answers the same question. ~24 cell lookups for a 192px candidate versus
~16k pixel lookups. Candidate validation samples the eroded nav grid; the
per-pixel test is not used here.

This is a **discrete approximation, not an equivalence** — an 8px cell grid is
coarser than a 2px pixel walk, so the validator must use supercover traversal
(every cell the segment touches, not just one per step) and enforce the same
no-corner-cut rule the A\* neighbour expansion already applies
(`nav.nim`, diagonal moves require both orthogonals walkable). Without those it
will pass segments that clip a wall corner.

## Part 3 — `coverageAt`: promote, and change the contract

The coverage function exists as `trace.nim:95-151` `coveredGrid`, but it measures
**conservative ally *vision***, which is not what this design needs:

| current behavior | why it is wrong here | source |
|---|---|---|
| reaches `1.5 × 1300 = 1950px` | past the gun's 1300px range — vision, not fire | `trace.nim:111-114` |
| skips the heading check inside a 90px bubble | an ally who cannot bring its gun round is not covering fire | `trace.nim:125-140` |
| counts every headed teammate | a spray-carrying ally cannot shoot at all (`sim.nim:820-825`) | `trace.nim:102-105` |
| wall-only `rayClear` | the engine's paint path also stops at barriers | `trace.nim:141`, `sim.nim:619-635` |

The extracted primitive is therefore **potential gun coverage**, not vision:
gun-holding allies only, range capped at `PostGunRangePx` (1300), a
`GuaranteedVisionConeHalfDeg` (45°) half-cone checked at *every* range, wall LOS
— with a documented approximation that barriers are ignored, which is exact while
`barrierPickups` is 0 and conservative-in-the-wrong-direction if it is ever
enabled. Ally tracks contribute at their velocity-projected position, using the
same projection as threat tracks.

`trace.nim` fills its grid from the same function, so the behavior and the viewer
can never diverge. **Its meaning changes**, so the grid's `source` metadata and
the viewer's documentation must say so — revision 1's claim that the viewer stays
semantically unchanged was false.

Coverage is a **float**: visible allies with known aim count 1.0, allies known
only from a track fresher than `SprayCoverTrackTtlTicks` count
`SprayCoverTrackDiscount`. Sources are combined by **maximum, not
first-wins** — otherwise a discounted track encountered first masks a visible
ally standing right there.

**Cost.** *Behavior* never precomputes a grid — the trace still renders its
existing downsampled one for the viewer, which is diagnostics, not the hot path.
Point-wise means ~`16 × 2 × SprayCoverSamples` requests per
fleeing agent, memoized per tick by nav cell (the 16 rays overlap heavily near
the origin), with the range and cone pre-filters rejecting most ally×point pairs
before any ray is cast. For scale, a full grid would be 85,814 nav cells on a
3211×1713 two-team map and 97,344 on a 2496×2496 four-team map — hence never.

## Part 4 — the spray shout

The channel is tight: **10 printable ASCII chars, one accepted shout per sender
per 24 ticks, 72-tick lifetime, range `mapWidth/5`, ±20px position jitter, and
every living player in range hears it — enemies included**
(`docs/stencil-communication.md`).

- **Encoding**: `S<team><identity><epoch><cell>` — 8 chars. Revision 1's
  `S<cell><identity>` omitted the team, and team-relative identities repeat
  across red/blue/green/yellow, so in FFA it names no unique enemy. Worse than
  incomplete: existing chat-seeded tracks already fall back to placeholder red
  (`belief_update.nim:199-204`), so an identity-bearing report with the wrong
  team creates a *confidently misidentified* track that visual matching may
  refuse to reconcile.
- **The epoch is not decoration.** A receiver drops a repeat of the same
  `(team, sender, text)` inside `ChatBubbleDedupTicks`
  (`belief_update.nim:151-157`), and the transport re-renders one live bubble
  rather than delivering discrete messages. A *stationary* sprayer therefore
  encodes to identical text every time and its refresh is silently swallowed —
  the report would go stale and expire while the threat is still standing there.
  A base-36 epoch, incremented only when a spray report is actually sent, makes
  each refresh textually distinct.
- **Cadence**: dedicated `chatLastSprayTick`, reshout every
  `SprayReshoutTicks` (default 48), which must be `<= SprayThreatTtlTicks` or the
  track expires inside the refresh gap. Explicitly **not** the `enemy` shout's
  arming scheme: that arms once and rearms only after all enemies have been
  absent for 48 ticks (`chat.nim:212-241`), so it would never re-report a sprayer
  that stays visible.
- **Backward compatibility**: a v58 teammate's decoder has no `S` prefix and
  ignores the message (`chat.nim:130-136`); it still detects spray visually.
- **Send**: slotted into `chooseShout` after `grenade`, before `under_fire`, and
  gated by `SprayChat` so channel contention can be isolated in a sweep. The
  consensus block keeps its priority — starving it would break the squad protocol.
- **Receive**: `belief_update` upserts an enemy track at the decoded cell with
  `weapon = WeaponSpray`. **This is what makes "all agents know" true.**
- **Uncertainty**: ±20px jitter plus 8px cell quantization ≈ ±28px.
  `SprayShoutThreatPadPx` is added to the **trigger and release radii** for
  shout-sourced threats — not to the scoring distance, which stays geometric.

### Track provenance and merge rules

A radius pad that depends on where a track came from requires the track to know.
`PlayerTrack` gains `source: TrackSource` (`TrackVisual`, `TrackTeamShout`,
`TrackEnemyBubble`), and merging follows fixed rules — without them a jittered
shout can degrade an exact sighting:

- **Visual beats chat on the same tick.** Visual tracks are updated before chat
  (`belief_update.nim:358-364`), and a shouted report must not overwrite an exact
  pose and badge-read loadout with jittered data.
- **Absent ≠ false.** A shout carries no grenade/shield/barrier state. A partial
  report preserves every field it does not speak to; only a badge observation may
  set a boolean to `false`.
- **`WeaponUnknown` never clears a known weapon.**
- **Identity matching first.** A spray report matches an existing track on exact
  `(team, identity)` regardless of jitter distance, falling back to spatial
  matching only when identity is unavailable — otherwise ±28px of jitter spawns
  a phantom second sprayer.
- **Nearest threat means `distance − sourcePad`**, not the geometrically nearest
  followed by that track's own threshold. With mixed visual and shouted threats
  the two orderings disagree.

## Part 5 — spray carriers as priority targets

`scoreTarget` (`fight.nim:124-142`) weighs wound, range band, claim,
shootability, aim cost, and shield — there is **no weapon term**. Add
`+ FirefightSprayWeight · (weapon == WeaponSpray)` to the existing weighted sum.

Gun path only: an arc-carrying stencil bypasses target scoring entirely
(`fight.nim:338-365`), which is the defect below. This improves how *gunners*
pick targets — the case that matters, since a sprayer is a free kill at range.

## Resolved ambiguities

Every one of these was underspecified in revision 1 and would have produced two
different implementations.

| question | resolution |
|---|---|
| Hysteresis state | explicit `sprayFleeActive` latch on `Belief`; cleared on release radius, empty threat set, gaining a shield, or death |
| Does `Hold` clear the latch? | No |
| Threat set duplicates | tracks only; visible enemies already have age-0 tracks |
| Stale track position | velocity-projected over track age, clamped to map |
| Shout pad applies to | trigger and release radii only |
| Ally track TTL for coverage | `SprayCoverTrackTtlTicks`, separate from threat TTL |
| Combining coverage sources | maximum, not first-wins |
| Path sampling endpoints | self point excluded; samples at `i/n` for `i` in `1..n` |
| Tie-break | direction index, then inner ring before outer |
| Fallback direction | away from the *nearest* threat, never a summed vector |
| Unknown loadout | `WeaponUnknown` never overwrites a known track weapon; only a parsed token updates it |
| Stale spray track after a respawn | not solvable from the wire (deaths are not attributable to anonymous tracks); TTL is the only clearing mechanism, so `SprayThreatTtlTicks` is the whole safety margin |
| Nearest threat with mixed sources | ordered by `distance − sourcePad`, not raw distance |
| Shout vs visual on the same tick | visual wins; a shout never overwrites an exact pose or badge-read loadout |
| Missing fields in a shouted report | preserved, never defaulted to `false`; only a badge observation may clear a boolean |
| Shout match against an existing track | exact `(team, identity)` first, spatial only as fallback |
| Which allies count for clumping | visible teammates only |
| Which allies count for coverage | gun-holders, visible or track-fresh, at velocity-projected positions |
| Coverage cone | `GuaranteedVisionConeHalfDeg` (45°), applied at every range |
| Flee-state clearing while dead | cleared on the alive→dead transition in `updateBeliefCore`, since `decideObjective` never runs while dead |

## Tunables

All via the existing `envTunableBool` / `envTunableInt` / `envTunableFloat`
validators in `config.nim`, which raise on malformed or out-of-range input.

| env var | default | meaning |
|---|---:|---|
| `STENCIL_SPRAY_AVOID` | on | feature flag for the whole rung |
| `STENCIL_SHIELD_AWARENESS` | on | repair the dead shield fields (isolates the A/B confound) |
| `STENCIL_SPRAY_FLEE_TRIGGER_PX` | 240 | enter the flee state inside this |
| `STENCIL_SPRAY_FLEE_RELEASE_PX` | 300 | leave it outside this (hysteresis) |
| `STENCIL_SPRAY_THREAT_TTL_TICKS` | 48 | how long a track stays a threat |
| `STENCIL_SPRAY_SHOUT_PAD_PX` | 40 | radius pad for shout-sourced threats |
| `STENCIL_SPRAY_CHAT` | on | send spray reports (isolates channel contention) |
| `STENCIL_SPRAY_RESHOUT_TICKS` | 48 | spray reshout interval; must be `<=` threat TTL |
| `STENCIL_SPRAY_FLEE_STEP_PX` | 96 | inner candidate ring (outer is 2×) |
| `STENCIL_SPRAY_FIRE_FREEZE_MARGIN_PX` | 40 | extra clearance required before a firing pause is allowed |
| `STENCIL_SPRAY_W_THREAT` | 1.0 | weight: distance gained from threats |
| `STENCIL_SPRAY_W_COVER` | 1.0 | weight: ally gun coverage along the path |
| `STENCIL_SPRAY_W_CLUMP` | 1.0 | weight: penalty for allies along the path |
| `STENCIL_SPRAY_W_CENTER` | 0.5 | weight: barrage centering tie-break |
| `STENCIL_SPRAY_CLUMP_RADIUS_PX` | 187 | = lethal reach; an ally inside this is a liability |
| `STENCIL_SPRAY_CLUMP_NORM_ALLIES` | 3 | ally count that saturates the clump term |
| `STENCIL_SPRAY_COVER_SAMPLES` | 4 | coverage/clump samples along self→P |
| `STENCIL_SPRAY_COVER_FAR_BIAS` | 2.0 | how much the far end outweighs the near |
| `STENCIL_SPRAY_COVER_TRACK_TTL_TICKS` | 24 | ally-track freshness for coverage |
| `STENCIL_SPRAY_COVER_TRACK_DISCOUNT` | 0.5 | remembered ally vs seen ally |
| `STENCIL_FIREFIGHT_SPRAY_WEIGHT` | 1.0 | target-score bonus for a spray carrier |

Engine-derived constants (not tunable, cited to source): `SprayLethalReachPx`
187, half-width `0.25·d + 17`. The **offense** constants `ArcFireRangePx 170` /
`ArcMaxWidthPx 85` stay untouched — they omit the body pad deliberately, so
stencil fires only when a target is solidly inside its own cone.

## Trace

Track and visible-enemy dumps (`trace.nim:63-68`, `:377-385`) gain `weapon`,
`grenade`, `barrier`, `shielded`. Belief adds `spray_flee_ticks`, live threat
count, whether the fire-freeze was suppressed, and the winning candidate's
**per-term score breakdown** — without the breakdown a sweep cannot attribute a
weight's effect. The `covered` grid keeps its shape but its `source` metadata
must state the new gun-coverage contract.

## Validation

Following v58's path (`VERSION_LOG.md`), not unit tests — `stencil_nim` has none,
and the lab's loop is probe-then-A/B:

1. `nim c` clean compile; `linux/amd64` image builds.
2. **Mechanism probe**: one 16-seat hosted episode, full tracing. Assert from the
   trace that (a) weapon tokens parse and appear on enemies — this is also what
   converts the badge-emission claims above from source-read to observed,
   (b) `shielded` is now sometimes true, proving the dead observable is repaired,
   (c) `clear_spray` activates when a spray threat enters the trigger radius,
   (d) agents actually exit the disc, (e) no agent activates it while shielded,
   (f) the per-tick cost of coverage plus candidate validation is acceptable.
3. **A/B v58 vs v59** via `coworld-ab`, matched fresh runs.
4. **Sweep** the flee weights once the mechanism is confirmed.

## Risks

- **Passivity.** A sprayer parked on a heart pedestal could stall captures. The
  counter-play is sound (hold outside 187px and shoot) but whether the ladder
  expresses it is what the A/B measures.
- **A/B confound.** Repairing `shielded` reactivates three dormant behaviors.
  `STENCIL_SHIELD_AWARENESS` exists to separate them; if the A/B moves, the
  attribution question is real.
- **Thrash** at the boundary — hysteresis mitigates; `spray_flee_ticks` and
  objective transitions detect it.
- **Cost.** Coverage plus candidate validation is the one part with a real
  per-tick budget. Measure in the probe before the A/B.
- **Barrage interaction.** `clear_spray` sits above barrage centering, so a
  latched barrage plus a sprayer can pull an agent off centre. `W_center`
  mitigates and only engages once `depth > 0`.
- **Shield gate is a heuristic**, knowingly: it is wrong for a chipped layer on
  low hp. *Deferred: shield-HP tracking* is the repair.

## Known adjacent defect (NOT fixed here)

Stencil is badly over-aggressive holding a can, from three compounding causes:

1. `fight.nim:338-365` — with a can, `firefightActive` is forced false and target
   selection, scoring, and focus claims are skipped wholesale.
2. `sprayTarget` (`action.nim:56-68`) picks by smallest **aim error**, then
   distance² — nearest-to-crosshair within 400px. Not by threat or objective value.
3. `action.nim:491-496` then overwrites the movement mask for anything in the
   100-400px band, and `hasViableEngagement` is just `sprayTarget.isSome`.

Net: holding a can, stencil abandons its objective and sprints up to 300px at
whatever is nearest its crosshair — into a 1300px weapon, while holding one that
needs 187px and cannot shoot. The mirror image of the defect this design fixes.
Separate change, separate measurement.
