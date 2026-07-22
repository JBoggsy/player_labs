# Squad play for beacon — design (v19 direction)

**Status:** design, not yet implemented. **Goal (human direction):** general-purpose
squad logic — squads of 2-3 agents that form up, stick together, and cover angles,
as the substrate for team tactics (support, flanking, coordinated pushes).

## The constraint that shapes everything: teammates are ANONYMOUS

A visible teammate sprite is labeled `player <color> <side>` — no identity, no seat.
Beacon can count and locate nearby teammates but cannot tell WHICH teammate it sees.
The only identity-bearing observable is a **shout bubble** (`<team> shout <address>:
<text>`), and only within ~247px.

Consequences:
1. **"Follow agent X" is impossible by sight.** Leader-follower designs need the
   leader broadcasting position via chat — expensive (one bubble/sec each) and
   short-ranged.
2. **Anonymous proximity is cheap and robust.** "How many teammates are within R of
   me" and "where is the nearest teammate" need no identity. Cohesion, spacing, and
   wait-for-buddies gating can all run on anonymous counts.
3. **Deterministic-by-seat computation is free and unlimited-range.** Every agent
   knows every seat's ROLE and can compute any pure function of (seat, tick,
   globally-observable state) that every other agent computes identically — the
   proven pattern from roles (v2) and item claims (v10). No radio needed.

So the architecture: **shared-goal convergence** (deterministic squad objectives by
seat table) + **anonymous local flocking** (cohesion/separation on visible/tracked
teammates) + **chat only where identity or non-local state genuinely matters**.

## Components

### 1. Squad membership — static, by seat (squads.py)

A pure function of seat, like roles. Default table (knob `BEACON_SQUADS`):

| squad | seats | role | purpose |
|---|---|---|---|
| D | 0, 1, 2 | defenders | hold line, mutual cover |
| A1 | 3, 4 | attackers | steal pair |
| A2 | 5, 6, 7 | attackers | second wave / escort mass |

Within-squad **rank** = index of my seat in the squad tuple (0 = "point"). Rank
drives formation slots and aim sectors — deterministic, no negotiation.

### 2. Sticking together — shared goal + anonymous flocking

Squadmates already converge by construction (same strategy rung → same goal). Two
local forces keep them TOGETHER en route, both computed from visible/tracked
teammates (anonymous is fine — any teammate nearby is squad-enough):

- **Cohesion:** if fewer than `SQUAD_MIN_BUDDIES` teammates are within
  `SQUAD_COHESION_PX` (~120px), bias movement toward the nearest teammate track /
  known squad rally instead of pushing on alone.
- **Separation:** below ~40px (baseline `MateSpacing`), steer apart — prevents
  stacked bodies eating one grenade (52px blast!) and blocking each other's
  shots (friendly fire).

**Wait-for-squad gating** at phase boundaries: before crossing a rally line (e.g.
our choke for attackers, x≈450), HOLD until the anonymous nearby-teammate count ≥
squad size − 1 (with a timeout so a dead squadmate doesn't deadlock the push —
respawns take 72t, waits cap at ~150t). This alone converts the current dribble-in
attack into wave attacks.

### 3. Covering angles — aim sectors by rank

The lighthouse sweep currently points everyone at the threat axis. Squad version:
offset each member's sweep centre by rank — rank 0 sweeps the axis, rank 1 sweeps
axis + `SECTOR_OFFSET` (~50 brads ≈ 70°), rank 2 axis − offset. Moving squads get
a forward cone + two shoulders; a holding squad covers complementary arcs instead
of three copies of one arc. Zero comms; pure seat math. (Vision cone is 60° half-
angle, so ±70° centres give overlapping but complementary coverage.)

### 4. Squad objectives — globally-observable inputs only

The strategy ladder gains a squad layer: members of a squad compute the SQUAD's
objective, not their own, from inputs every member observes identically — flag
states (never fogged) + static geometry + tick. Personal-belief inputs (enemy
sightings) must NOT pick squad objectives, or members diverge; sightings instead
flow through chat (E/U) and the danger field, which converge beliefs approximately.
Hysteresis (~48t) on squad-objective switches prevents flapping.

Initial squad objectives map onto existing rungs: D holds (spread hold points →
squad hold cluster with sectors); A1 steals as a pair (wait-gated at the rally
line); A2 escorts/second-waves. Carry/intercept/escort overrides stay personal —
they are already correct per-agent.

### 5. Chat's role (v18 layer, reused)

- `C` heartbeat already gathers escorts; squads make the response coherent.
- `E`/`U` become squad-actionable: a squadmate's E within earshot = "support/flank
  toward that cell" for my squad (the human's stated purpose for these).
- Later (deferred): squad-scoped messages — append the sender's seat digit to
  codes (budget: 6 used of 10) so hearers know WHICH squad is talking; and a
  rally call `R<cell>`.

## Build plan (each an attributable iteration)

1. **v19 — formation + cohesion + wait-gating + aim sectors** (this design's core;
   knobs `BEACON_SQUADS`, `BEACON_SQUAD_*`; activation tracing: nearby-teammate
   count histogram, wait ticks, cohesion-bias ticks, sector offsets applied).
   Measure: 1v1s vs h006 (its blitz punishes solo pushes hardest — squad waves are
   the direct counter) + focusfire regression.
2. **v20 — squad response to E/U** (support/flank movement when a squadmate
   reports contact in earshot) — the human's stated payoff for E/U.
3. **v21 — squad-scoped chat** (seat digit, rally calls) if v19/v20 show identity
   or rally gaps in traces.

## Risks / open questions

- **Wait-gating vs tempo:** waves are slower than dribbles; vs focusfire's turtle
  that's fine (its early game punishes solo pushes too), but the timeout knob
  matters. Trace wait-ticks so cost is visible.
- **Cohesion vs item fetch:** rung 3.5 detours split squads; fetchers should be
  exempt from cohesion while fetching (they rejoin at the rally).
- **2-agent D squad in 1v1 mirrors:** seats exist on both sides; fine.
- **Divergence:** if squad objective ever reads per-agent belief, members split
  silently. Enforced by construction (inputs limited to global observables) + a
  trace field for each agent's computed squad objective to verify convergence.
