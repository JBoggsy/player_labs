# WATCH camouflage — fake a task instead of hovering (2026-07-02)

**Status: SUPERSEDED 2026-07-06.** Replays showed crewborg still hovering
mid-room in WATCH — this design's kill-cooldown gate (only latch onto a task
when the kill was far from ready) and single/multiple-crew split meant the
task-latch didn't apply most of the time; the multi-crew "vantage hold" path
fell through to a bare coarse-grid room scan instead (see
`docs/designs/vision-model.md` and the `search.py` module docstring). James's
fix: drop the gating and the crew-count split entirely — WATCH now has exactly
one case, always latch onto the best-view task station, regardless of cooldown
or how many crew are visible. The camouflage mechanism described below (and
`visionbake.py`, `tools/vision_bake.py`, the vendored per-task visibility bake)
was removed rather than kept as a second code path — this doc is kept as the
historical record of the problem and the first (partial) fix.

**Problem (James, from replays):** while Search is shadowing crew in a room, the
imposter acts suspicious — it hovers at a vantage or trails a lone crewmate at
35px with nothing to do. Real crewmates in a room are *at task stations doing
tasks*. When the kill is far from ready there is nothing to convert anyway, so
the hovering is pure suspicion cost.

**Behaviour:** a new step layered on Search's WATCH state. When we are watching
a room with crew and the kill is still far from ready, walk to the task spot in
the room with the best visibility over the crew we can see, and fake a task
there (idle) for one crewmate task duration plus a small buffer — blending in
while keeping eyes on the future victims.

## Trigger conditions (all must hold)

| # | Condition | Where enforced |
|---|-----------|----------------|
| a | In **Search** mode | the camo lives inside `SearchMode._watch` — Search only |
| b | In a room with **≥1 visible crewmate** (seen this tick, in the watched room) | `_watch`'s `visible_here` |
| c | **> `CREWBORG_CAMO_MIN_CD_TICKS` (100) ticks** until the kill comes off cooldown | `ticks_until_kill_ready(belief) > camo_min_cd_ticks()` |
| d | The current room has ≥1 task station | `_room_task_indices` |
| e | No camo already completed this WATCH visit (one fake task per room entry) | `_camo_done` flag, reset on room re-entry |

Note on (c): `ticks_until_kill_ready` returns the full default cooldown (500)
when no cooldown start has been observed yet, so early-game camo fires — that
is intended (early game is exactly when we cannot kill and look suspicious).
The default of 100 equals `RECON_WINDOW_TICKS`, so camo never overlaps the
Recon window: at ≤100 ticks the selector prefers Recon/Hunt and Search's own
close-in behaviour takes over.

## Spot selection

Among task stations **in the current room**, pick the one whose *baked
visibility* covers the most **currently-visible crewmates** (crew seen this
tick); tie-break by larger total baked visible area (cell count). If the vision
bake is missing/invalid, fall back to the **nearest task spot in the room** —
never crash, never stall. The stand-point is the station's baked reachable
anchor (`imposter_common.task_point`), same as Pretend used.

## The vision bake (`visionbake.py` + `tools/vision_bake.py`)

Vision in Crewrift is the per-player shadow overlay: pure line-of-sight
occlusion by walls (perception/decoder.py `_decode_shadow`), with an effective
range bounded by the screen. Crewborg's established LOS proxy is
`nav._segment_clear` over the walkability mask within `VANTAGE_RANGE` (360px) —
the same scoring WATCH's vantage already uses. The bake reuses exactly that
model so camo and vantage agree on what "can see" means.

- **Format:** per task station, a boolean visibility mask over the occupancy
  grid (`agent_tracking.GRID_CELL_SIZE` = 32px cells): cell is `True` iff the
  cell centre is within 360px of the station anchor, the cell contains walkable
  pixels (someone could stand there), and the anchor→centre segment is clear.
  Array shape `(41 tasks, 21 rows, 39 cols)` + per-task visible-cell counts +
  a SHA-1 fingerprint of the walkability mask it was baked against.
- **Offline artifact, not startup compute:** measured bake cost is 0.10s
  locally (~0.5–1s under the hosted 250m-CPU throttle — borderline against the
  <1s budget, and it would compete with the already-tight first tick). We bake
  once offline into a vendored asset (`map/croatoan_visionbake.pkl.gz`,
  0.8 KiB) exactly like the nav bake: zero first-tick cost, one tiny committed
  file. `tools/vision_bake.py` reads the walkability + task anchors out of the
  existing vendored **navbake** (no separate capture step) and writes the
  asset.
- **Runtime load + validation:** `load_visionbake(walkability, task_count)`
  validates the walkability fingerprint and task count; any mismatch, missing
  file, or unpickle error returns `None` → nearest-task-spot fallback. Loaded
  once per process and memoized (`modes/search._camo_vision`).

## Idle duration and escapes (every idle must have an escape)

Hold = `FAKE_TASK_TICKS` (72 — the one-task hold constant Pretend used, moved
to `imposter_common`) + `CREWBORG_CAMO_BUFFER_TICKS` (12, ~0.5s). The hold
starts when we *arrive* at the spot; the walk there is separately capped.

| Escape | Trigger | Exit reason |
|--------|---------|-------------|
| Done | idled hold+buffer ticks at the spot | `done` |
| Kill soon | `ticks_until_kill_ready ≤ camo_min_cd_ticks()` (covers the estimate shrinking AND the kill becoming ready outright) | `kill_soon` |
| Crew lost | no live non-teammate seen within `CREWBORG_CAMO_CREW_LOST_TICKS` (36) ticks | `crew_lost` |
| Travel cap | not arrived within `CAMO_TRAVEL_CAP_TICKS` (120) of camo start | `travel_timeout` |
| Preempted | selector switches modes (meeting → attend_meeting, kill window → Recon/Hunt/Evade): the SDK replaces the mode instance; `SearchMode.on_exit` emits the exit | `preempted` |
| Parked guard | guard fires anyway (should be unreachable — see below) | camo state cleared by the guard's full reset |

After any exit, `_camo_done` is set and normal WATCH behaviour resumes
(vantage hold / single-target close / leaver follow). While camo is active we
deliberately do **not** chase leavers — the crew-lost escape covers the room
emptying.

## ParkedGuard interaction

The camo idle is *intentional* idling, so it is explicitly exempt from
`ParkedGuard`: `fires(..., intentional_idle=True)` resets the streak instead of
accruing. In practice the exemption is unreachable insurance — the guard only
counts **kill-ready** ticks, and the `kill_soon` escape ends camo before any
kill-ready tick can carry a camo intent. If that invariant is ever violated,
Search emits a `camo_guard_exempt` trace event on each suppressed tick (a loud
bug signal), and the guard itself remains fully active for every non-camo
intent.

## Telemetry

One event name, `domain.camo_idle`, phase-tagged, in the `kill` trace group
(`domain.camo_*`):

- enter: `{phase: "enter", spot, task_index, visible_crew, planned_hold_ticks,
  ticks_until_ready, bake_used}`
- exit: `{phase: "exit", reason, held_ticks, arrived}`

## Knobs

| Env | Default | Meaning |
|-----|---------|---------|
| `CREWBORG_CAMO` | `1` | Kill switch (set `0` to disable camo entirely). |
| `CREWBORG_CAMO_MIN_CD_TICKS` | `100` | Camo only when the kill is more than this many ticks from ready; doubles as the kill-soon escape threshold. |
| `CREWBORG_CAMO_BUFFER_TICKS` | `12` | Extra idle ticks past the 72-tick task duration. |
| `CREWBORG_CAMO_CREW_LOST_TICKS` | `36` | All crew unseen this long ⇒ abandon the camo. |

## Composition with v91

- Density prior / PICK_ROOM: untouched — camo only affects WATCH.
- Ready-state re-search + parked guard: camo runs strictly *outside* the
  ready/near-ready window (gate c), so it never eats the kill window Recon/Hunt
  own; the guard exemption is explicit and traced.
- Crewmate path: untouched (Search is imposter-only).

## Pre-registered A/B (100 eps/arm, imposter-pinned, prime top-7 roster)

PRIMARY: imposter-ejected rate DOWN and/or kills/game UP. MECHANISM:
`camo_idle` fires in >30% of imposter games; WATCH-with-crew time shifts from
hovering to task spots. GUARDS: imposter win not worse; first-kill Playing
ticks not worse by >15%; ops/timeouts 0; crewmate path untouched.
