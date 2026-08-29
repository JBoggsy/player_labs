# Recon: the threat-axis idle-aim mechanism (stencil v68)

## Mission

Map everything the "threat axis" idle-aim mechanism in
`paintbot/stencil_nim/action.nim` touches — definitions, state, consumers,
tick ordering, and telemetry — so its removal and mind-side re-homing (the
nav-rework sketch §1/§4 kill that only half-landed) can be designed with no
surprises. Consumer: the design doc for the removal (same session) and its
Codex-collab implementation. All paths below are relative to `paintbot_lab/`
unless noted; verified against the v68 working tree on 2026-08-29.

## The mechanism, end to end

**Axis selection** — `threatAxis` (`paintbot/stencil_nim/action.nim:62-77`),
un-exported, body-side, reads strategy-level belief state directly:

1. If `belief.squadOrderPostActive` and `squadOrderPostSightlineAim` is set →
   aim at the squad-order post's median sightline ray end (action.nim:64-66).
   Those fields are reset at the top of every `decideBaseObjective` and set
   only by the squad-order rung (strategy.nim:308-313, 421-428) — so they are
   live at act time **only when the squad-order rung won the ladder** that tick.
2. Else if `belief.role == Defender`, own heart not stolen, and
   `defensivePostOpponent` is set → aim at that opponent's pedestal
   (action.nim:67-69). `defensivePostOpponent` is assigned in the orient
   station (policy.nim:62, 80), before strategy runs.
3. Else if `belief.stealTarget` is set → aim at the steal target's pedestal
   (action.nim:70-71). `stealTarget` is chosen during belief fold.
4. Else → `belief.worldmap.center` (action.nim:72-73).
5. Degenerate delta (|dx|<1 and |dy|<1) → `spawnAim(team)` (action.nim:74-77).
6. Nil worldmap → current `aimBrads` (action.nim:63) — unreachable in
   practice: `resolveAction` early-outs on nil worldmap (action.nim:431-435).

**Sector offset + oscillation** — `sweepTarget` (action.nim:79-89):
when `Squads` is on and the agent holds **no** squad-order post and **no**
defensive post, the axis is rotated by `sectorOffsetBrads` — a squad-rank
fan-out, ±`SquadSectorBrads`·⌈rank/2⌉ (squads.nim:39-43). Then a triangle-wave
oscillation: `sweepOffset` steps by `sweepDir * AimSweepStepBrads` per call
and reflects at ±`SweepHalfArc` (action.nim:84-88).

**The one consumer** — the idle-aim branch of `resolveAction`
(action.nim:546-552): when no combat target was selected (`enemy.isNone`),
aim target = the micro override's aim if one fired, else `belief.sweepTarget`.
Because Nim evaluates the `else` lazily, **the oscillator advances only on
idle ticks where no override aim fired** — a coupling to body-side outcomes
(combat target selection, micro override) that matters for the re-homing
design.

## State, constants, telemetry

- `sweepOffset`, `sweepDir` live on `Belief` (belief_state.nim:58; `sweepDir`
  initialized 1 at belief_state.nim:143). Reset to 0/1 on respawn, alongside
  `aimBrads := spawnAim(team)` (belief_update.nim:394-398).
- `AimSweepStepBrads* = AimTurnRate` (config.nim:76, compile-time);
  `SweepHalfArc* = envInt("STENCIL_SWEEP_HALF_ARC", 32)` (config.nim:111).
  `SquadSectorBrads` feeds only `sectorOffsetBrads`.
- Telemetry: `replay.nim:85-86` records `sweep_offset`/`sweep_dir`;
  `trace.nim:265` records `spawn_aim_brads` (a worldmap product, not sweep
  state).

## Consumer census (grep, whole repo)

- `threatAxis`: defined action.nim:62; called only by `sweepTarget`
  (action.nim:80). No other code, test, or tool hit.
- `sweepTarget`: defined action.nim:79; called only at action.nim:549.
- `sectorOffsetBrads`: defined squads.nim:39; called only at action.nim:83.
  **If the aim-side keying dies and nothing mind-side adopts it, it is dead.**
- `spawnAim`: defined worldmap.nim:1160; also used by belief_update.nim:396
  (respawn aim reset) and trace.nim:265 — **survives regardless**.
- No Nim unit tests exist for action.nim; the property harnesses are
  `tools/nav_v67_properties.nim` / `tools/nav_v68_properties.nim`
  (posts/follower, untouched by this change).

Additional census facts (repo-wide subagent sweep, 2026-08-29):

- `defensivePostOpponent` (belief_state.nim:25) is the one Belief field whose
  **only live consumer is the idle-aim path** (action.nim:68-69) — everything
  else is trace (trace.nim:482) and the offline renderer
  (tools/render_nav.py:49). It stays (the mind-side helper adopts the read),
  but its consumer graph moves entirely to the mind.
- `SweepHalfArc` (env-tunable) and `AimSweepStepBrads` (const) are consumed
  only inside `sweepTarget`.
- `emergant_lab/emergant/stencil_ant_nim/` is a near-verbatim fork with the
  same symbols at the same line numbers (minus the `stealTarget` branch).
  **Out of scope here** — do not accidentally edit it, and note the drift.
- Closest test prior art: the Python ancestor's
  `ctf_lab/ctf/beacon/tests/test_beacon.py:1349-1355,1648-1655,1852`
  (sector offsets, baked threat axis, sweep value).

## Tick ordering (policy.nim:22-109) — what a mind-side computation would see

Per tick: perceive → (maybe) build WorldMap → `updateBeliefCore` (sets
`stealTarget`, tracks, `aimBrads`) → orient (roles + `defensivePost*`,
only when flagged stale) → `decideObjective` (the ladder; sets/clears
`squadOrderPost*`) → `resolveAction` → `chooseShout`. Everything
`threatAxis` reads is final **before strategy returns**, and nothing mutates
it between `decideObjective` and `resolveAction`. A computation at the end
of `decideObjective` therefore sees bit-identical inputs to today's act-time
computation.

**One wrinkle: dead ticks.** When `belief.alive` is false, policy.nim
bypasses strategy entirely and hand-builds `makeIntent(Hold, none(Point),
"not_alive")` (policy.nim:99-102). `resolveAction` still runs (its early-out
is only selfXy-none / worldmap-nil, action.nim:431), so today a dead agent
with a stale `selfXy` still sweeps. Any design that stamps idle aim only in
`decideObjective` changes dead-tick masks (rotation buttons) — irrelevant to
gameplay but visible to `tools/compare_stencil.py` parity checks.

## Not in scope (verified untouched)

- `peekDuckOverride`'s use of `squadOrderPostSightlineAim` and the post/duck
  stance points (action.nim:215-284) — a separate, working mechanism; its
  aim wins over the sweep in the idle branch via `override.get.aim`.
- Combat target aiming (action.nim:493-545) and the respawn `spawnAim` reset.

## Cross-references and surprises

- The nav-rework close-out addendum records the half-landed kill honestly
  (docs/designs/nav-rework-sketch-2026-08-11.md:416-419); the body/mind
  report lists it as leak #1 with the "aim-intent produced where the strategy
  context lives" direction (docs/reports/stencil-policy-loop-2026-08-29.md §8.1).
- Because `squadOrderPost*` is reset every tick and set only when the
  squad-order rung *wins*, the axis priority is already entangled with the
  ladder: e.g. a carrier (carry_home returns before the squad-order rung)
  never aims at its order post today. A post-ladder mind-side transcription
  preserves this automatically; per-rung stamping would not.
- The Intent contract (types.nim:205-214) has no aim field today; `makeIntent`
  (strategy.nim:13-72) is the single construction helper, also called by
  policy.nim's dead-tick branch.

## Files read (full or significant section)

- paintbot/stencil_nim/action.nim (full), strategy.nim (full), types.nim
  (full), policy.nim (full), squads.nim:1-80, belief_update.nim:385-409
- docs/designs/nav-rework-sketch-2026-08-11.md,
  nav-layer4-intent-contract-2026-08-13.md (full)
- docs/reports/stencil-policy-loop-2026-08-29.md (full)
- paintbot_lab/AGENTS.md, WORKING_CONTEXT.md, VERSION_LOG.md head/tail

## Next steps

Design the replacement: a typed idle-aim product on the Intent, axis
computed post-ladder in strategy (transcribing rules 1-6 + the sector-offset
gate), oscillator staying body-side to preserve its idle-tick-only stepping.
Files an implementer opens first: action.nim:62-89,546-552; strategy.nim:475-489
(decideObjective wrapper); types.nim:205-214; policy.nim:99-102.
