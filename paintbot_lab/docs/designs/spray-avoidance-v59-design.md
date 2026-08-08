# stencil v59 — enemy loadout belief + spray-can avoidance

*2026-08-08. Living document; updated as the implementation reveals new
information.*

Built against canonical **Paintbot 0.7.215 / GameVersion 41**, source
`6c7a4c0e0be35bdcf738137595ccbcb4b4c79bf9` (`tools/versions.env`). Every engine
citation below is `file:line` in that ref.

## Problem

The spray can is the only weapon in Paintbot that kills a healthy player in one
touch, and stencil is blind to it. Two separate gaps:

1. **Stencil does not know what an enemy is holding.** The wire states it
   outright — `identity <color> <name>[ shield][ nade] <weapon>`, one badge per
   visible player — and `perception.nim:92-98` parses the badge, takes the name
   token, and discards the rest. `Enemy`/`PlayerTrack` (`types.nim:22-49`) carry
   no weapon or grenade field at all.
2. **Nothing avoids the cone.** There is no rung, no radius, no term anywhere in
   the objective ladder or the movement resolver that reacts to a spray carrier.

### Why one touch is lethal

| quantity | value | source |
|---|---:|---|
| `PlasmaArcDamage` | **3** | `sim_types.nim:529` |
| `hitPoints` (every deployed variant) | 3 | manifest `config_schema` |
| lethal reach = `PlasmaArcReach` + `PlasmaArcBodyRadius` | 170 + 17 = **187px** | `sim_types.nim:505,517` |
| cone half-width at forward distance `d` | `0.25·d + 17` px (14.0° half-angle) | `sim.nim:732,743` |
| cone direction | **locked at fire** (GV38), origin rides the owner 5 ticks | `sim.nim:713-716` |
| refire cadence | `ActiveTicks 5` + `ResetTicks 20` = **25 ticks** (~1.04s) | `sim_types.nim:532,534` |
| victim gate | `paintPathClear` — walls block, and standing cardboard blocks | `sim.nim:871` |

Three consequences drive the whole design:

- **A shield is the only survival.** `ShieldLayerHp 3` on top of 3 base hp means
  a shield carrier survives exactly one cone (`sim_types.nim:529` says so in
  as many words). Unshielded, a cone touch is death.
- **A spray carrier cannot fire the gun.** `canFire` requires
  `not shooter.hasPlasmaArc` (`sim.nim:699`). Outside 187px a sprayer is
  *completely harmless*, and we outrange it 1300:187. There is no punish for
  retreating — retreat is strictly dominant against that enemy.
- **Both sides move at the same speed.** `MaxSpeed 704` = 2.75 px/tick with no
  per-weapon modifier (`sim_types.nim:320`). A committed chaser therefore never
  loses ground to radial flight; escape comes only from the 20-tick recharge
  window or an LOS break. **The keep-out radius must be preventive, not
  reactive** — this is the single most important constraint on the design.

## Goals / non-goals

- **Goal**: stencil knows every visible enemy's weapon, grenade, barrier, and
  shield state, and remembers it on tracks.
- **Goal**: stencil keeps out of spray range when a hit would be lethal, and
  when it must flee it flees *through terrain its allies cover*, without
  dragging the sprayer onto them.
- **Goal**: the whole thing is a tunable surface, so the flee policy can be
  swept rather than guessed.
- **Goal**: allies who never saw the can still avoid it (shout propagation).
- **Non-goal — team perks.** Team-scope, a different marker
  (`perks <color> <group>…`), no consumer, and off in every deployed variant.
  Noted in `docs/paintbot-gameplay.md`; add when something reads it. `armor`
  (+1 max hp → 4 hp survives a cone) is the one that would change this math.
- **Non-goal — barrier fetch/place behavior.** This change adds the *belief
  field* only; the item economy in `items.nim` is untouched.
- **Non-goal — wiring the unused `danger` grid into A\*.** `belief.danger` is
  built, decayed, dilated and stamped every tick (`belief_update.nim:225-293`)
  and read by nothing but `trace.nim`. That is a real finding, but a global
  path-cost change is unmeasurable folded inside a single-behavior A/B.
- **Non-goal — retrofitting `clear_grenade` onto the new coverage primitive.**
  The primitive is built general and grenade-flee is an obvious follow-up; doing
  it here makes the A/B unattributable.
- **Non-goal — fixing spray-carrier over-aggression.** See "Known adjacent
  defect" below. Real, separate, measured separately.

## Part 1 — loadout belief

### The channel

`labelIdentity` (`labels.nim:406`) pins the invariant: optional flags first in a
fixed order (`shield` before `nade`), and **the weapon token is always last and
always present**, precisely so an observer never has to infer "gun" from
absence — absence is also what a truncated or fog-dropped badge looks like. The
manifest carries the suffixed forms (`tests/label_manifest.txt:40-43`), so this
is contract, not chrome. `docs/RULES.md` documents the badge without suffixes
and is stale; RULES itself states the manifest wins.

Badges are emitted on the **player stream** for every visible player
(`global.nim:5734`, called with `viewerIndex = playerIndex` at `global.nim:6223`);
only the sprite rotation differs from the board stream, never the label.

### Types

```nim
EnemyWeapon* = enum WeaponUnknown, WeaponGun, WeaponSpray
Loadout* = object
  weapon*: EnemyWeapon
  grenade*, shield*: bool
```

`Enemy` and `PlayerTrack` each gain `weapon`, `hasGrenade`, `hasBarrier`,
`shielded` (re-sourced, below) and `shieldDown`. Tracks persist last-known
loadout through the existing copy sites (`belief_update.nim:84,92`), so a
fogged sprayer stays feared. Staleness self-heals on re-sighting, and a
respawn comes back gunless.

### Parsing

`identityBadges` returns the parsed `Loadout` alongside `(identity, pos)`;
`playersOfColor` attaches it on the **existing** badge→body proximity match —
no second pass and no new matcher.

**Self-badge exclusion is required.** Our own badge is emitted too (the
`i != viewerIndex` visibility gate passes self), but our body is labeled
`self <color> <side>`, not `player <color> <side>` — so `playersOfColor` never
consumes it, and the orphan badge can proximity-attach to a nearby teammate.
That is a latent identity bug today which loadout would inherit. Fix: take the
own-color badge nearest `selfXy` as ours, use it for own loadout, exclude it
from teammate matching — the same idiom as the existing `selfHpMarker`
exclusion (`perception.nim:241-250`).

`hasBarrier` has no badge token; it comes from the `barrier carried` overhead
marker folded into the existing `carried` table in `attachOverheadState`, the
path `shield carried` already uses. Costs nothing while `barrierPickups`
defaults to 0.

### The shield-semantics fix

The engine emits `shield carried` **only when `shieldHp <= 0`**
(`global.nim:5216`) — a *spent* shield, where the armor is gone but the 3×
fire slowdown persists. An active shield draws the bubble instead. Stencil
sources both `enemy.shielded` (`perception.nim:281-286`) and `iHaveShield`
(`perception.nim:337`) from that marker, so **both mean the opposite of what
their names claim**.

| field | new source | meaning |
|---|---|---|
| `Enemy.shielded` | badge `shield` token | has a shield at all |
| `Enemy.shieldDown` | `shield carried` marker | layer spent |
| `iHaveShield` | own badge `shield` token | has a shield at all |
| `iShieldUp` | own badge token ∧ ¬`shield carried` | bubble actually up |

Protected ⟺ `shielded and not shieldDown`.

**`items.nim:71` must gate shield refetch on `iShieldUp`, not `iHaveShield`.**
Verified against the engine: `tryPickupShields` returns early only on
`shieldHp >= ShieldLayerHp` (`sim.nim:1632`) — a worn carrier *is* allowed to
refill, and the docstring says so explicitly. The current gate declines to
refill exactly when the shield is spent, and burns detours fetching one while
the bubble is up. Precisely backwards.

## Part 2 — the `clear_spray` rung

Placed in `decideObjective` immediately after `clear_grenade`, above barrage
centering — **below `carry_home` and `intercept_thief`**. Rationale for not
putting it on top: a heart carrier moves at `carrierSpeedPct 70` (1.925
px/tick) and cannot outrun a sprayer anyway, so fleeing both forfeits the win
condition *and* probably still dies. Stated as a known gap rather than hidden.

- **Threat set**: visible enemies plus tracks fresher than
  `SprayThreatTtlTicks` whose `weapon == WeaponSpray`.
- **Gate**: skipped entirely when `iShieldUp` — 6 effective hp survives a cone,
  and burning the objective to dodge a survivable hit is a bad trade.
- **Keep-out disc, with hysteresis**: trigger at `SprayFleeTriggerPx`, release
  at `SprayFleeReleasePx` (release > trigger, so the bot bounces off the
  boundary instead of orbiting it).
- **Not the cone.** Enemy aim in a player view is 16-step sprite quantization,
  and at `aimTurnRate 5` a sprayer re-aims 90° in ~13 ticks. The cone is a
  fact about the last 5 ticks, not about the next 25. The disc is the honest
  model of "can reach me before I can react".

### Flee-point scoring

16 directions × 2 radii (`SprayFleeStepPx`, 2×), rejecting any candidate
failing `walkableSegment(self, P)` (`worldmap.nim:194`). For each survivor:

```
score(P) = W_threat · threatGain(P)   // min distance to any spray threat, normalized
         + W_cover  · coverPath(P)    // ally coverage sampled ALONG self→P
         − W_clump  · clumpPenalty(P) // allies I would drag the sprayer onto
         + W_center · centerTerm(P)   // only while the barrage has latched
```

Each term is normalized to `[0, 1]` (`clumpPenalty` to `[0, ∞)` in ally counts)
so the weights are directly comparable in a sweep:

| term | definition |
|---|---|
| `threatGain(P)` | `clamp(min over threats of dist(P, threat) / SprayFleeReleasePx, 0, 1)` |
| `coverPath(P)` | weighted mean of `coverageAt` at `SprayCoverSamples` points evenly spaced along self→P, sample `i` of `n` weighted `1 + (SprayCoverFarBias − 1)·i/(n−1)` |
| `clumpPenalty(P)` | count of allies (visible or fresh track) within `SprayClumpRadiusPx` of P |
| `centerTerm(P)` | `clamp(1 − dist(P, map.center) / BarrageCenterRadiusPx, 0, 1)`, and **0 unless `belief.barrage.depth > 0`** |

Fallback when every candidate is rejected: pure radial (today's `clear_grenade`
shape), then `Hold`.

**Why coverage is a path term and not an endpoint term.** The naive version —
"prefer allies who have line of sight to the sprayer *right now*" — fails the
case that matters: an agent peeks, sees a can, and retreats past cover behind
which allies sit. Those allies have no ray to the sprayer at flee time; they
gain one when the sprayer follows through the gap. The right question is not
"does an ally see the threat" but **"is this cell covered by an ally"** — a
property of terrain plus allies, independent of where the threat currently
stands. The pursuer walking into fire then falls out of the primitive instead
of needing to be predicted. Sampling *along* the path, weighted toward the far
end (`SprayCoverFarBias`), is what encodes "lead them through our guns": the
far end is where we stand while the pursuer is mid-path.

This also cleanly separates two geometries that the endpoint formulation
conflated:

- **coverage is about vision** — lead them through our guns;
- **clumping is about bodies** — do not lead them onto our friends
  (`clumpPenalty` counts allies within `SprayClumpRadiusPx` of P).

### `coverageAt` — promote, do not invent

The coverage function already exists: `trace.nim:95` `coveredGrid` — conservative
instantaneous ally vision from the observable 16-step heading, the narrowest
deployed cone (`GuaranteedVisionConeHalfDeg 45`), and exact pixel-wall LOS. It
is trace-only: downsampled ×4, boolean, computed only when tracing is on,
consumed by nothing. Same fate as the danger grid.

This change extracts a single primitive, `coverageAt(belief, point): float`, and
makes `trace.nim` fill its existing grid from it — so the belief viewer keeps
working unchanged and now provably renders the function the behavior uses.

**It must stay point-wise, not a grid.** `rayClear` samples every 2px
(`worldmap.nim:180-192`), so a 1300px ray is ~650 wall lookups; a full grid on a
giant map is ~84k cells × up to 7 allies every tick. The flee scorer needs ~100
distinct points per tick, not 84k. Cost control:

- the range and cone pre-filters `coveredGrid` already applies reject most
  ally×point pairs before any ray is cast;
- first covering ally wins (existing `break`);
- memoize per tick by nav cell — the 16 candidate rays overlap heavily near the
  origin.

Coverage becomes a **float**, not a bool: visible allies with known aim count
full, fresh teammate *tracks* count `SprayCoverTrackDiscount` — "believed ally
covering fire", not merely currently-seen. Aim goes stale fast at 5 brads/tick,
hence a discount rather than equal weight. **Only gun-holding allies count**: a
can-carrying ally cannot cover anyone (`sim.nim:699`), which is the new `weapon`
field paying for itself immediately.

### Suppression is mandatory, not cosmetic

`action.nim:491-495` lets spray pursuit **overwrite the movement mask**
(`mask = (mask and not MovementMask) or octantToward(…enemy.pos)`) whenever we
hold a can and a target sits in the 100-400px band. Without adding
`"clear_spray"` to that exclusion list the flee rung is silently overridden and
the feature does nothing. Same for peek-duck (`action.nim:230`) and Hold-state
separation drift (`action.nim:465`). This mirrors exactly what v58 did for
`barrage_center`.

Aim and fire are deliberately untouched: we retreat *while shooting*. That is
the whole point — a 1300px gun against a 187px can that cannot shoot back.

## Part 3 — the spray shout

The channel is tight: **10 printable ASCII chars, one accepted shout per sender
per 24 ticks, 72-tick lifetime, range `mapWidth/5`, ±20px position jitter, and
every living player in range hears it — enemies included**
(`docs/stencil-communication.md`).

- **Encoding**: new kind `spray`, prefix `S` + the existing 4-char cell code +
  an identity digit = 6 chars, mirroring `encodeFocusClaim`'s shape
  (`chat.nim:83`).
- **Send**: slotted into `chooseShout` after `grenade`, before `under_fire`.
  The consensus block (commit/vote/proposal) keeps its priority untouched —
  starving it would break the squad protocol. Armed/re-shout cadence copied
  from the `enemy` shout so one sprayer cannot monopolize the channel.
- **Receive**: `belief_update` creates or refreshes an enemy track at the
  decoded cell with `weapon = WeaponSpray`, exactly as the `enemy` message
  already seeds tracks (`belief_update.nim:164,201`). **This is what makes "all
  agents know" true.**
- **Uncertainty**: ±20px engine jitter plus 8px cell quantization ≈ ±28px, so
  shout-sourced threats get `SprayShoutThreatPadPx` added to their radius. Well
  inside the trigger's margin.
- **Leak**: enemies learn we have spotted their sprayer. The protocol already
  broadcasts enemy, carrier, and thief positions in clear, so this changes
  nothing structurally.

## Part 4 — spray carriers as priority targets

`scoreTarget` (`fight.nim:124-142`) weighs wound, range band, claim,
shootability, aim cost, and shield. There is **no weapon term** — spray carriers
are not prioritized today. Add `+ FirefightSprayWeight · (weapon == WeaponSpray)`
to the existing weighted sum: three lines in the established idiom, tunable like
every other weight.

Scope caveat, stated plainly: this affects the **gun path only**. An
arc-carrying stencil bypasses target scoring entirely (below), so this improves
how *gunners* pick targets — which is the case that matters, since a sprayer is
helpless at range and a free kill for anyone holding a gun.

## Known adjacent defect (NOT fixed here)

Stencil is badly over-aggressive while holding a can, from three compounding
causes:

1. `fight.nim:359-364` — with a can, `firefightActive` is forced false and
   target selection, scoring, and focus claims are skipped wholesale (the
   bypass is even counted as `firefightArcExemptTicks`).
2. `sprayTarget` (`action.nim:56-68`) picks by smallest **aim error**, then
   distance² — nearest-to-crosshair within 400px with clear LOS. Not by threat,
   wound, or objective value.
3. `action.nim:491-495` then overwrites the movement mask for anything in the
   100-400px band, and `hasViableEngagement` is just `sprayTarget.isSome`.

Net: holding a can, stencil abandons its objective and sprints up to 300px at
whatever is nearest its crosshair — into a 1300px weapon, while holding one that
needs 187px and cannot shoot. It is the mirror image of the defect this design
fixes. Separate change, separate measurement.

## Tunables

All via the existing `envTunableBool` / `envTunableInt` / `envTunableFloat`
validators in `config.nim`, which raise on malformed or out-of-range input.

| env var | default | meaning |
|---|---:|---|
| `STENCIL_SPRAY_AVOID` | on | feature flag for the whole rung |
| `STENCIL_SPRAY_FLEE_TRIGGER_PX` | 240 | enter the flee state inside this |
| `STENCIL_SPRAY_FLEE_RELEASE_PX` | 300 | leave it outside this (hysteresis) |
| `STENCIL_SPRAY_THREAT_TTL_TICKS` | 48 | how long a track stays a threat |
| `STENCIL_SPRAY_SHOUT_PAD_PX` | 40 | radius pad for shout-sourced threats |
| `STENCIL_SPRAY_FLEE_STEP_PX` | 96 | inner candidate ring (outer is 2×) |
| `STENCIL_SPRAY_W_THREAT` | 1.0 | weight: distance gained from threats |
| `STENCIL_SPRAY_W_COVER` | 1.0 | weight: ally coverage along the path |
| `STENCIL_SPRAY_W_CLUMP` | 1.0 | weight: penalty for allies near the endpoint |
| `STENCIL_SPRAY_W_CENTER` | 0.5 | weight: barrage centering tie-break |
| `STENCIL_SPRAY_CLUMP_RADIUS_PX` | 187 | = lethal reach; ally inside this at P is a liability |
| `STENCIL_SPRAY_COVER_SAMPLES` | 4 | coverage samples along self→P |
| `STENCIL_SPRAY_COVER_FAR_BIAS` | 2.0 | how much the far end outweighs the near |
| `STENCIL_SPRAY_COVER_TRACK_DISCOUNT` | 0.5 | remembered ally vs seen ally |
| `STENCIL_FIREFIGHT_SPRAY_WEIGHT` | 1.0 | target-score bonus for a spray carrier |

Engine-derived constants (not tunable, cited to source): `SprayLethalReachPx`
187, half-width `0.25·d + 17`. The **offense** constants `ArcFireRangePx 170` /
`ArcMaxWidthPx 85` stay untouched — they omit the body pad deliberately, so
stencil only fires when a target is solidly inside its own cone.

## Trace

Both the track dump (`trace.nim:63-68`) and the visible-enemy dump
(`trace.nim:377-385`) gain `weapon`, `grenade`, `barrier`, `shielded`,
`shield_down`. Belief adds `spray_flee_ticks`, live threat count, and the
winning candidate's per-term score breakdown — without the breakdown a sweep
cannot attribute a weight's effect. `covered` keeps its current grid shape,
now filled from `coverageAt`.

## Validation

Following v58's proven path (`VERSION_LOG.md`), not unit tests — `stencil_nim`
has none, and the lab's loop is probe-then-A/B:

1. `nim c` clean compile, `linux/amd64` image builds.
2. **Mechanism probe**: one 16-seat hosted episode with full tracing. Assert
   from the trace that (a) weapon tokens parse and appear on enemies,
   (b) `clear_spray` activates when a spray threat enters the trigger radius,
   (c) agents actually exit the disc, (d) no agent activates it while
   `iShieldUp`.
3. **A/B v58 vs v59** via `coworld-ab`, matched fresh runs.
4. **Sweep** the flee weights once the mechanism is confirmed — that is what the
   tunable surface is for.

## Risks

- **Passivity.** A sprayer parked on a heart pedestal could stall captures. The
  counter-play is sound (hold outside 187px and shoot — they cannot answer), but
  whether the ladder expresses it is exactly what the A/B measures.
- **Thrash** between flee and objective at the boundary. Hysteresis is the
  mitigation; `spray_flee_ticks` and objective transitions in the trace are how
  it gets detected.
- **Coverage cost.** Point-wise plus pre-filters should keep it cheap, but it is
  the one part of this change with a real per-tick budget. Measure in the probe
  before the A/B.
- **Barrage interaction.** `clear_spray` sits above barrage centering, so a
  latched barrage plus a sprayer could pull an agent off center. The
  `W_center` term is the mitigation and it only engages once `depth > 0`.
