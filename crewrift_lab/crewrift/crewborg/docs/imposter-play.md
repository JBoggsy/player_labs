# Imposter play

How the imposter converts a game into kills — the subsystem that spans the
per-tick mode selector, the four imposter modes, and the shared victim/witness
logic. This is the narrative tying those files together; for the structural spec
see [`../design.md`](../design.md) §7.2 and §10, and for orientation see
[`../README.md`](../README.md). Per-file behavior lives in each module's
docstring; this page is the cross-cutting view.

## The core thesis

The imposter's job is **conversion, not stealth**: the win is decided by getting
the *second* kill, not by killing perfectly unseen. Two imposters killing twice
is parity-breaking; an imposter that lands one careful kill and then dithers does
not win games. Everything below is shaped around opening and converting kill
windows, and the kill gate (see
[The kill/strike gate](#the-killstrike-gate)) deliberately relaxes — and after
the first kill, abandons — the witness requirement so the second kill actually
fires.

A standing rule follows from this: **imposters never report bodies.**
Self-reporting our own kill opens a meeting that resets the kill cooldown and
kills the snowball. The selector never routes an imposter to Report Body
(`modes/report_body.py`); after a kill the imposter leaves the scene (Evade)
instead.

## Pipeline at a glance

```
                 per tick
  Belief ──► RuleBasedStrategy._select_imposter  (the priority order)
                   │
                   ├─ Voting ──────────────► attend_meeting   (see ./meetings.md)
                   ├─ just killed ─────────► evade            (post-kill re-approach)
                   ├─ ready + visible victim► hunt             (commit ▸ intercept ▸ strike)
                   ├─ travel time ≈ cooldown► recon            (timed pre-ready beeline)
                   └─ otherwise ───────────► search           (always-on seeking FSM)
                                                  │
                          each mode returns a symbolic Intent (navigate_to / kill / idle)
                                                  │
                                          action.py resolves it to a command
```

The selector only *chooses* a mode; the mode object turns belief into a symbolic
`Intent`; `action.py` turns the `Intent` into the actual movement/kill command.
The mode files never move the agent and never press buttons.

## The per-tick selector priority order

`strategy/rule_based.py:RuleBasedStrategy._select` dispatches by phase and role.
A live imposter in the `Playing` phase goes to
`strategy/rule_based.py:_select_imposter`, which applies this order (highest
priority first):

| # | Condition | Mode | Gate function |
|---|-----------|------|---------------|
| 1 | `phase == "Voting"` | `attend_meeting` | (handled in `_select`, before role dispatch) |
| 2 | killed within `EVADE_TICKS` ago | `evade` | `_recent_self_kill(belief)` |
| 3 | kill ready **and** a victim visible | `hunt` | `belief.self_kill_ready and has_visible_victim(belief)` |
| 4 | strictly PRE-ready, a *fresh, unspent* sighting exists, **and** the real travel time to it has caught up with the remaining cooldown | `recon` | `not self_kill_ready and target is not None and ticks_until_kill_ready(belief) <= travel_ticks(belief, self_xy, target_xy)` |
| 5 | otherwise (the literal `else`) | `search` | — no gate of its own — |

Order is the design contract (§10): Evade outranks Hunt so we never instantly
re-hunt over our own fresh body; Hunt outranks Recon because a ready kill on a
visible victim beats pre-positioning; Recon outranks Search because a well-timed
beeline to crew beats undirected seeking. Search is the always-on fallback that
fires whenever nothing above it does — including **every kill-ready tick with no
visible victim** (recon is pre-ready only; a ready blind imposter actively sweeps
rooms rather than beelining to history) **and every pre-ready tick where it isn't
time to move yet** — Search's WATCH holds the best-view task station until gate 4
fires.

Gate 4 (reworked 2026-07-06 — was a fixed `recon_window()` ticks-before-ready,
replaced with computed timing) keeps Recon honest three ways:

- **Isolation, not recency** — the target is `strategy/opportunity.py`'s
  `most_isolated_recon_candidate`: among fresh sightings, the one farthest from
  every OTHER candidate (maximizing the minimum gap), tie-broken toward the more
  recently seen. Least likely another crewmate (or a teammate) complicates the
  approach or the kill.
- **Staleness bound** — the candidate pool behind `recon_target` only includes
  sightings younger than `recon_staleness_ticks()` (default 360, env
  `CREWBORG_RECON_STALENESS_TICKS`); an older last-seen point carries no victim
  information, so we sweep rooms (Search) instead of beelining to it.
- **Timed departure** — `travel_ticks(belief, self_xy, target_xy)` estimates the
  walk via the real nav route when available (straight-line distance / speed
  otherwise) and Recon only fires once `ticks_until_kill_ready(belief)` has
  counted down to that estimate — so we arrive right as the cooldown clears
  instead of camping there early (the over-extension risk a longer fixed window
  used to create).
- **Spent sightings** — the moment we stand at a target's last-known point
  (within `RECON_REACHED_RADIUS_SQ`) without it being visible, that (color,
  last_seen_tick) sighting is marked spent in the selector and stops qualifying;
  only a *fresh* sighting of that crewmate re-arms Recon. This prevents the
  Search→Recon ping-pong back to a point we already know is empty.

The selector re-evaluates every tick — there are no reflex transitions or sticky
mode state in the selector itself (the modes hold their own FSM state). The
meeting branch (Voting) is decided in `_select` before role dispatch, so it
applies to imposter and crewmate alike.

### Selector levers

| Lever | Source | Effect |
|-------|--------|--------|
| `EVADE_TICKS` | env `CREWBORG_EVADE_TICKS`, default `72` (~3s at 24 Hz) | Length of the post-kill Evade window (`_recent_self_kill`). |
| `RECON_STALENESS_TICKS` | env `CREWBORG_RECON_STALENESS_TICKS`, default `360` (~15s) | Max age of a sighting that still qualifies as a recon target (gate 4). |
| `AGENT_SPEED_PX` | `strategy/trajectory.py`, `3.0` px/tick | Movement speed `travel_ticks` divides distance by to estimate recon departure timing (gate 4). |
| `CREWBORG_BE_DUMB` / `BE_DUMB` | env truthy | Replaces the imposter `Playing` order with only Hunt (ready + visible victim) / Search — skips Evade, Recon, Report Body. An isolation experiment for "always prepare to kill". |
| `skip_evade` | LLM commander (`strategy/commander/bias.py:commander_of`) | When the commander signals danger, suppresses Evade so we don't loiter near a body; logged to `belief.commander_danger_events`. See [`./commander.md`](./commander.md). |

The commander is optional and gated; when absent (`commander_of` returns `None`)
the deterministic order above is the whole story.

## Reconstructing the kill cooldown

The HUD exposes only a binary ready/cooldown bit — no countdown — so the
"how soon can I kill" used by gates 3–4 is reconstructed in
`strategy/opportunity.py`:

- `ticks_until_kill_ready(belief)` returns `0` when `self_kill_ready`; otherwise
  `kill_cooldown_start_tick + duration - last_tick`, where `duration` is the
  learned `kill_cooldown_estimate` or, before anything is measured,
  `DEFAULT_KILL_COOLDOWN_TICKS` (500 — Crewrift Prime 0.3.9, the target league;
  regular Crewrift uses 800). With no cooldown start observed yet it assumes a
  full cooldown remains, so a no-information imposter does not falsely trigger
  Recon's timed departure.
- The cooldown start and learned duration are maintained in `types.py` belief
  folding: `last_kill_tick`, `kill_ready_since_tick`, `kill_cooldown_start_tick`,
  and `kill_cooldown_estimate` are updated as `self_kill_ready` transitions are
  observed. `last_kill_tick` is set the tick `self_kill_ready` flips True→False
  (our kill), and the cooldown duration is learned the first time a cooldown runs
  back to ready.

`kill_urgency_ticks(belief)` is `last_tick - kill_ready_since_tick` (0 when not
ready) — how long we have been *able* to kill without doing so. It drives the
witness relaxation below.

## Search — the always-on seeking FSM

`modes/search.py:SearchMode`. Search's job is to keep us *near crew* so a kill
window opens. It does not kill; when the kill is ready and a victim is visible
the selector flips to Hunt. The measured imposter gap that motivates Search is
being near crew about half as often as the strongest imposters.

A small FSM, with all state on the instance (reworked 2026-07-01 to the 5-state
form; see the module docstring for the authoritative transition list):

```
  PICK_ROOM ─► GO_TO_ROOM ─► SEARCH_ROOM ─► WATCH ─► FOLLOW(c) ─┐
      ▲            │              │            │          │      │
      │   (room    │ (crewmate    │ (swept     │ (crew    │ (c settles in
      │   empty)   │  seen ⇒      │  empty)    │ leaves)  │  a room) ─► SEARCH_ROOM
      └────────────┴─ FOLLOW) ────┴────────────┴──────────┘ (c lost) ─► SEARCH_ROOM/PICK_ROOM
```

| State | Behavior |
|-------|----------|
| `pick_room` | **Score every reachable room and commit to the best — never idles.** The score blends (env-tunable weights, `modes/search.py`): live expected-crew occupancy (strongest, `W_OCCUPANCY` 3.0), the **empirical density prior** (`W_PRIOR` 1.5 — see below), unvisitedness (grows with time since visit), a fast-decaying just-visited penalty, travel cost, teammate-pressure subtraction, a task-room blend bonus, and a soft commander hunt-room nudge. Excludes the current room, the spawn room, and a commander avoid-room when possible. Head to the room **center** (go fully inside), not a door/task spot. |
| `go_to_room` | Navigate to the center; seeing ANY live non-teammate — room or hallway — switches to FOLLOW immediately; on arrival, SEARCH_ROOM. |
| `search_room` | Sweep the room's interior scan points so crew hidden from the door are found. Crew in the room → WATCH; a crewmate seen elsewhere → FOLLOW; swept empty → PICK_ROOM. |
| `watch` | Only entered with crew confirmed in the room. **One case** (simplified 2026-07-06 — James: crewborg should just latch onto the best-viewing task and never hover): any crew visible → hold the in-room task station with line-of-sight to the most of them (recomputed as they move), regardless of how many are visible or how close the kill is. Leaver → FOLLOW; no watched crew remain → PICK_ROOM. |
| `follow(c)` | Chase the committed leaver `c` to its next room. When visible, `navigate_to` its live position and feed `strategy/path_prediction.py:PathPredictor`; when occluded, `navigate_to` the predictor's top predicted hallway position. Give up when the target is gone/dead/now a teammate, the lost-ticks budget expires, or the predictor runs out. |

Search never follows the teammate imposter (`belief.teammate_colors`). The path
predictor is fed only what we actually see (the target's position when visible,
`None` otherwise) — the same signal it is scored on offline.

### The empirical density prior

`strategy/room_prior.py` loads `data/room_density.json` once at import (schema
`crewborg-room-density/v1`, built from 247 real episodes by
`crewrift_lab/tools/imposter_movement/room_density.py`): each room's measured
share of all live crew, in 600-tick Playing bands. `room_share_prior(room, tick)`
returns the room's share **max-normalized within the current band** (band =
tick // 600, clamped to the last band) — the same 0..1 scaling PICK_ROOM applies
to live occupancy, so the blend weights compare directly. The blend rule: the
prior's weight (`W_PRIOR` 1.5, env `CREWBORG_PICKROOM_W_PRIOR`) is deliberately
**half** the live-occupancy weight — live evidence dominates 2:1 when the
tracker has mass; when blind (early game, long no-contact stretches) the prior
is the crew-seeking signal that breaks ties between otherwise-equal rooms.
Failure-tolerant: a missing/malformed file (or `CREWBORG_ROOM_DENSITY=0`, or a
room not in the table) makes the prior term 0.0 — never a crash.

### The parked guard

`modes/imposter_common.py:ParkedGuard` — the standing "idling is dangerous"
insurance, wired into Search and Recon. Any run of
`parked_guard_ticks()` (default 12, env `CREWBORG_PARKED_GUARD_TICKS`)
consecutive **kill-ready Playing ticks** whose intent is idle or a zero-length
route (navigation target within `PARKED_ARRIVE_RADIUS_SQ` of self) forces a
state change — Search re-runs PICK_ROOM (the current room is excluded, so the
new target is always elsewhere); Recon abandons its target and heads for the
hottest occupancy point that isn't underfoot — and emits a
`domain.parked_guard` trace event (in the `kill` trace group). Hunt is
deliberately unguarded (its in-range "lying in wait" hold escapes via the
urgency relaxation) and Evade can't be kill-ready. No exemptions: if WATCH's
vantage hold ever fires the guard, the selector should already have switched
to Hunt before Search ran at all — the guard firing anyway is a real bug to
chase, not a case to special-case around.

### Vantage selection (WATCH's one case)

`_refresh_vantage` / `_best_vantage` pick, over the room's **task stations only**
— never an arbitrary room point (2026-07-06, James: replays showed crewborg
hovering mid-room instead of latching onto a task; every room on croatoan has
>=1 task station, so a held vantage is always one, and this is now WATCH's
*only* behavior — no separate camouflage state, no single/multiple-crew split)
— whichever has clear line-of-sight (`nav._segment_clear` over
`belief.nav.walkability`) to the most watchable crew within `VANTAGE_RANGE`
(91 px — the circumscribed-circle radius of the game's real 128×128 camera
window, see `docs/designs/vision-model.md`). It is throttled
(`VANTAGE_REFRESH_TICKS` = 18) and uses hysteresis (`VANTAGE_SWITCH_MARGIN` = 1)
so it only moves when a new vantage sees at least one more crewmate, avoiding
jitter between equal vantages. Returns `None` only for a room with zero task
stations (doesn't happen on croatoan; guards a future map).

A prior version of this ("WATCH camouflage") gated the task-latch behind a
kill-cooldown threshold and split single- vs multiple-crew handling — removed
2026-07-06 in favor of always latching onto the best-view task regardless of
cooldown or crew count. See `docs/designs/watch-camouflage.md` (marked
superseded) for the historical design and why it existed.

| Search constant | Value | Meaning |
|-----------------|-------|---------|
| `ARRIVE_RADIUS_SQ` | `24²` | Arrival tolerance at a goto point/vantage. |
| `FOLLOW_LOST_TICKS` | 120 | Drop an unseen follow after this long with no live prediction. |
| `COMMANDER_FOLLOW_LOST_TICKS` | 240 | Extended follow persistence for a commander-hard-named target. |
| `WATCH_RECENT_TICKS` | 36 | A crewmate is "still watchable" from a vantage if seen within this window. |
| `VANTAGE_RANGE` | 91 px | Line-of-sight range for vantage scoring. |
| `VANTAGE_REFRESH_TICKS` | 18 | Max vantage recompute frequency. |
| `VANTAGE_SWITCH_MARGIN` | 1 | Extra crew a new vantage must see before we move to it. |

An optional commander can bias which room to sweep (`hunt_room`), avoid
(`avoid_room`), or which player to prefer following (`target_player`), and at
`strength == "hard"` force a hunt room and grant the longer follow persistence —
see [`./commander.md`](./commander.md). Movement/pathing mechanics are in
[`./navigation.md`](./navigation.md); path-destination prediction is its own
subsystem in `strategy/path_prediction.py`.

## Recon — the timed pre-ready beeline

`modes/recon.py:ReconMode`. The only *pre-positioning* mode (reworked
2026-07-06 — was a fixed tick-window before ready, now a computed departure
time). When the selector's travel-time gate fires (gate 4), it routes here
instead of Search. Recon does exactly one thing: **beeline to the most
ISOLATED fresh crewmate** (`strategy/opportunity.py:recon_target` — live
position when visible, last-known otherwise) so that the instant the cooldown
clears, a victim is in view and Hunt fires immediately.

The target (commander `target_player` override, else `recon_target`) is
re-derived each tick — the SAME function the selector used to time the entry,
so mode and trigger never disagree about who to approach. Unlike Hunt it does
not require the target to be currently visible or reachable — it is only
pre-positioning, not striking. The selector only routes here for a *fresh,
unspent* sighting whose travel time has caught up with the remaining cooldown
(see gate 4 above), and Recon itself never stands on a ghost position: reaching
the last-known point without the target in view abandons it (`_abandoned`) and
falls back to occupancy seeking, with a `ParkedGuard` as final insurance. It
`idle`s only when we have no self position or no crew signal exists at all.

| Recon constant | Source | Value | Meaning |
|----------------|--------|-------|---------|
| `RECON_STALENESS_TICKS` | env `CREWBORG_RECON_STALENESS_TICKS` via `recon_staleness_ticks()` | 360 | Max sighting age that still qualifies as a recon target (3× the 120-tick follow/track windows ≈ 2-3 room transits); older ⇒ Search. |
| `RECON_REACHED_RADIUS_SQ` | `strategy/opportunity.py` | `24²` | "Reached the last-known point" radius, shared by ReconMode's arrival handling and the selector's spent-sighting check. |
| `AGENT_SPEED_PX` | `strategy/trajectory.py` | `3.0` px/tick | Speed `travel_ticks` divides distance by to decide when it's time to depart. |

Target selection: among fresh sightings, `most_isolated_recon_candidate` picks
the one farthest from every OTHER candidate (max of the min-gap to any other),
tie-broken toward the more recently seen. This replaced plain
"most-recently-seen" targeting — a crewmate standing next to others is more
likely to have a witness or get intercepted, and least useful to pre-position
on. Departure timing: `travel_ticks(belief, self_xy, target_xy)` estimates the
walk via the real nav route when one exists (respects walls/corridors), else
straight-line distance / `AGENT_SPEED_PX`. Gate 4 fires once
`ticks_until_kill_ready(belief) <= travel_ticks(...)` — so Search holds its
best-view task vantage right up until that moment, and Recon departs timed to
arrive as the cooldown clears, not early.

## Hunt — commit, intercept, strike

`modes/hunt.py:HuntMode`. Selected only when the kill is ready and a non-teammate
crewmate is visible. Hunt owns the kill-ready close and strike; Search/Recon own
acquisition and pre-positioning. The flow each tick:

1. **Commit to a victim.** `_resolve_victim` keeps the currently committed victim
   (`_victim_color`, the only Hunt state) while it stays visible, alive, and a
   non-teammate; otherwise it commits to a new one via
   `strategy/opportunity.py:select_victim` (or a commander-forced visible,
   reachable target). Sticking with one target avoids re-picking every frame.
2. **Intercept, don't tail-chase.** Hunt navigates to the victim's *predicted
   intercept* point, not its live position. `strategy/trajectory.py:predict`
   extrapolates the victim's last-known position along its velocity (estimated
   from its two most recent sightings) by `lead_ticks(self_xy, victim_xy)` ticks.
   A tail-chase at equal speed never closes, so before leading, kills only ever
   landed on stopped crewmates. A stationary or unreliable target predicts to its
   current position (a no-op lead).
3. **Strike or lie in wait.** When in range (`action.py:KILL_RANGE_SQ` = 400, a
   20 px radius) and `self_kill_ready` and the strike is allowed, emit a `kill`.
   Otherwise close on the intercept; when already in range but the kill is
   witnessed, shadow ("lie in wait") rather than blow the kill.

### Trajectory (intercept lead) constants

| Constant | Value | Meaning |
|----------|-------|---------|
| `VELOCITY_MAX_DT` | 4 | Only trust a velocity from two sightings at most this many ticks apart (a wider gap means the player was off-screen between them). |
| `AGENT_SPEED_PX` | 3.0 | Assumed travel speed, used to estimate how long it takes us to close. |
| `MAX_LEAD_TICKS` | 24 | Cap on the lead so a stale/noisy velocity can't fling the aim point across the map. |

## The kill/strike gate

The strike condition in `modes/hunt.py:HuntMode.decide` is:

```
in_range  AND  self_kill_ready  AND  (unwitnessed  OR  already_killed  OR  danger_witness_allowed)
```

`in_range` is `dist2(self_xy, victim_xy) <= KILL_RANGE_SQ`. The interesting part
is the third clause — when a witnessed kill is allowed anyway.

### `unwitnessed` — a witness COUNT against an urgency-ramped tolerance

`strategy/opportunity.py:unwitnessed(belief, target)` answers "would killing this
target now go unseen, at the current urgency?" **A kill is unwitnessed iff the
number of live non-teammate crewmates (other than the victim) currently visible
to us — this exact tick — is at or below the current tolerance**
(`witness_tolerance(belief)`). It's not a yes/no gate on any witness at all: a
single onlooker never vetoes a strike, even at zero urgency.

Counting "currently visible" is exact, not an approximation: `belief.roster`
only records another player's position on ticks where *our own* vision actually
saw them, and Crewrift vision is symmetric (same camera-frame + line-of-sight
check run from either side — see `docs/designs/vision-model.md`). So "we
currently see them" and "they can see the kill" are the same fact — no isolation
radius or staleness window is needed to *approximate* "nearby and probably still
watching." (Before 2026-07-06 this used a bespoke `BASE_ISOLATION_RADIUS`/
`WITNESS_WINDOW_TICKS` heuristic that was never derived from the game's real
~64–90px vision reach — see the vision-model doc.) The victim itself and fellow
imposters are never witnesses; dead crewmates can't witness.

### Urgency ramps the tolerated witness count

The witness tolerance is not fixed. The longer the imposter has been *able* to
kill without doing so, the more witnesses it will strike through, so a cautious
imposter that never finds a perfectly clean opening still escalates rather than
stalling forever:

```
frac      = min(1.0, kill_urgency_ticks / URGENCY_FULL_TICKS)
tolerance = int(ALLOWED_WITNESSES_MIN + (ALLOWED_WITNESSES_MAX - ALLOWED_WITNESSES_MIN) * frac)
unwitnessed = (witness_count <= tolerance)
```

At zero urgency, up to `ALLOWED_WITNESSES_MIN` (1) witness is tolerated. By
`URGENCY_FULL_TICKS` (240 ticks, ~10s at 24 Hz) of being kill-ready without
killing, the tolerance reaches `ALLOWED_WITNESSES_MAX` (6) — since this game's
fixed 6-crew format means at most 5 OTHER live crew can ever witness a kill, that
ceiling is an effective "always strike," reached by a ramp rather than a cliff.

| Witness constant | Value | Meaning |
|------------------|-------|---------|
| `URGENCY_FULL_TICKS` | 240 | Kill-ready-without-killing ticks at which witness tolerance reaches its maximum. Env-overridable via `CREWBORG_URGENCY_FULL_TICKS` (clamped to ≥ 1) for sweeps without a rebuild. |
| `ALLOWED_WITNESSES_MIN` | 1 | Witnesses tolerated at zero urgency. Env-overridable via `CREWBORG_ALLOWED_WITNESSES_MIN`. |
| `ALLOWED_WITNESSES_MAX` | 6 | Witnesses tolerated at full urgency (exceeds the max possible in this game's 8-player format — an "always strike" ceiling). Env-overridable via `CREWBORG_ALLOWED_WITNESSES_MAX`. |

### The first-kill witness drop

The decisive override: **after the first kill, the witness requirement is dropped
entirely.** `already_killed = belief.last_kill_tick is not None`, and when true,
the strike fires on any in-range, kill-ready victim regardless of witnesses (the
`unwitnessed` test is bypassed). This is the mechanical expression of the
[core thesis](#the-core-thesis): banking the second kill is the imposter's job,
and at the second ready we are usually already close to crew, so conversion beats
stealth. The reason string distinguishes the two strikes
("striking the 2nd+ kill (witnesses ignored)" vs "striking isolated victim").

`danger_witness_allowed` is the third path: an optional commander danger mode
(`allow_witnessed_kill`) explicitly permits a witnessed kill, emitting a
`commander_danger` trace event when it fires. See
[`./commander.md`](./commander.md).

## Victim selection

`strategy/opportunity.py:select_victim` picks who to commit to: among live
non-teammate crewmates visible *this tick*, filtered to those we can actually
route to (`nav.plan_route` when a nav graph exists), it returns the **most
isolated, tie-broken by nearest to us**:

```
max(candidates, key=lambda t: (_isolation(t, belief), -dist2(self_xy, t)))
```

`_isolation(t)` is the squared distance to `t`'s nearest *other* live
non-teammate — a higher value means a more isolated straggler, the easiest target
to finish off unseen. Ties (and equal isolation) break toward the nearest
candidate so we commit to the one we can reach soonest.

### The teammate-claim heuristic

A soft deconfliction signal so two imposters don't pile onto the same victim.
`_claimed_by_teammate` treats a target as claimed when a recently-seen living
fellow imposter is both *closer* to it than we are and within
`TEAMMATE_CLAIM_RADIUS` (80 px). `select_victim` prefers unclaimed candidates
when any exist, but falls back to the full candidate set if every visible victim
is claimed — it never returns nothing solely because of a claim.

| Victim-selection constant | Value | Meaning |
|---------------------------|-------|---------|
| `TEAMMATE_CLAIM_RADIUS` | 80 px | A teammate closer than us and within this radius "claims" the victim. |
| `TRACK_WINDOW_TICKS` | 120 | Recency for "trackable" (`has_trackable_victim`) and for teammate-claim sightings. |

`has_visible_victim` / `visible_victims` (live non-teammates seen this very tick)
gate Hunt; `most_recent_victim` (the most-recently-seen live non-teammate, by
`last_seen_tick`) is the Recon and cold-start Evade target.

## Evade — post-kill re-approach

`modes/evade.py:EvadeMode`. Selected for `EVADE_TICKS` after our own kill. Despite
the name, **Evade does not flee** — it heads *toward* where the crew most likely
are, so a victim cluster is already nearby when the post-kill window hands back to
Search/Recon/Hunt. This is the inverse of fleeing: blind flight fed the post-kill
drift (lose crew contact, no victim in sight at the next ready), so Evade
re-approaches instead.

Evade is paired with Hunt's first-kill witness drop: re-approaching a *crowd*
would be a poor place to land an *unwitnessed* kill, but once witnesses no longer
veto the second kill, the crowd is target-rich exactly when we need it. The two
are designed to be evaluated together.

Target preference each tick (stateless, re-derived):

1. the densest expected-crew **room** (`agent_tracking.best_pretend_room_target`,
   teammate-pressure-adjusted so two imposters don't pile on the same room);
2. else the hottest occupancy **cell** (`agent_tracking.best_seek_point`);
3. else (cold start, before occupancy has mass) the most-recently-seen crewmate
   (`most_recent_victim`);
4. else `idle`.

When our own position is unknown the room/cell steps are skipped and Evade goes
straight to the last-seen crewmate. The occupancy/densest-crew readouts are the
agent-tracking subsystem — see [`./agent-tracking.md`](./agent-tracking.md).

## Where imposter play touches the rest

| Concern | Lives in | Doc |
|---------|----------|-----|
| Meeting deflect / bandwagon / vote behavior | `modes/attend_meeting.py` | [`./meetings.md`](./meetings.md) |
| Occupancy grid, densest-crew / hottest-cell readouts | `agent_tracking.py`, `strategy/occupancy.py` | [`./agent-tracking.md`](./agent-tracking.md) |
| Movement, routing, line-of-sight, nav graph | `nav.py`, `navbake.py` | [`./navigation.md`](./navigation.md) |
| How belief (roster, sightings, kill bits) is built | `types.py`, `perception/`, `events.py` | [`./perception-and-belief.md`](./perception-and-belief.md) |
| Per-player sighting trail used for tracking | `agent_tracking.py` | [`./agent-tracking.md`](./agent-tracking.md) |
| The suspicion model (crewmate side) | `strategy/suspicion.py` | [`./suspicion.md`](./suspicion.md) |
| The optional LLM commander levers | `strategy/commander/` | [`./commander.md`](./commander.md) |
| Crewmate counterpart of this play | `modes/normal.py`, `modes/accuse.py`, `modes/report_body.py` | [`./crewmate-play.md`](./crewmate-play.md) |
| Trace events for replay/debug | `trace.py` | [`./trace-logs.md`](./trace-logs.md) |
