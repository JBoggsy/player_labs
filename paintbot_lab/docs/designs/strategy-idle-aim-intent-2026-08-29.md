# Idle aim as a mind product — finishing the threat-axis kill

**Status: IMPLEMENTED as v69, 2026-08-29.** Design v2 after a two-round
Codex design review (all five required review changes adopted or
reconciled; the task brief authorized implementation on cross-agent
convergence — James's after-the-fact review welcome). Implemented by the
same Codex session under orchestration; recorded-wire parity proof and the
hosted verdict live in `VERSION_LOG.md` v69. Governing: nav-rework sketch §1/§4 ("Kill the threat axis
— the concept is outdated; remove it and everything keyed on it") and its
2026-08-29 close-out honesty note; leak #1 of
[the body/mind report](../reports/stencil-policy-loop-2026-08-29.md).
Recon with full consumer census:
[threat-axis-idle-aim recon](../recon/threat-axis-idle-aim-2026-08-29.md).

## Problem

`threatAxis`/`sweepTarget` (action.nim:62-89) decide *where to look when
idle* — a mind decision — inside the body, by reading strategy-level belief
state directly (squad-order post sightline, defender's post opponent
pedestal, steal-target pedestal, else map center; squad-rank sector offset;
±`SweepHalfArc` oscillation). Sole consumer: the idle-aim branch of
`resolveAction` (action.nim:546-552). The v66 Intent contract says the body
dispatches on typed fields only; this is the one place it still doesn't.

## Options

**A (recommended) — typed `idleAimCenterBrads` on the Intent; axis mind-side,
sweep body-side.** `Intent` gains `idleAimCenterBrads*: Option[int]`
(types.nim). A new exported helper in strategy.nim — `idleAimAxis(belief):
Option[int]` — transcribes today's axis rules exactly (priority chain,
degenerate-delta → `spawnAim`, and the sector-offset gate `Squads and not
squadOrderPostActive and defensivePost.isNone`, consuming
`squads.sectorOffsetBrads` mind-side where it belongs); `none` when
worldmap/selfXy are absent. The field is the **unswept center** of the
body-executed scan, not a final per-tick aim — hence the name.

Stamping contract (review change #1): `decideObjective` selects its final
`Objective` first — the base ladder result **or** the arc-pursuit override,
one exit path — and stamps the field exactly once on whichever won, so it
sees the same post-ladder state `threatAxis` sees today; policy.nim's
dead-tick `not_alive` intent gets the same one-line stamp (dead agents
currently still sweep, and parity keeps that; no `alive` guard anywhere in
the helper).

`none` contract (review change #2): `none` is valid **only** when worldmap
or selfXy is absent, in which case `resolveAction` has already returned at
its early-out before consuming aim. On the reachable idle path the body
consumes `.get` — absence there is a producer bug, not a case to handle —
and the body never recomputes the center from Belief (that would silently
reintroduce the leak).

The body keeps only the dumb execution: the idle branch becomes *"sweep
around the center I was given"* — a renamed `idleSweepAim(belief, center)`
that steps `sweepOffset`/`sweepDir` (unchanged state, respawn reset, and
replay telemetry) and stays inside the lazily-evaluated `else` of the
target expression, so the oscillator advances exactly when it does today
(no combat target AND no override aim — including the override-without-aim
and corridor-rejected-override cases, which fall through to the sweep).
`threatAxis`, `sweepTarget`, and every strategy-state read in the idle-aim
path are deleted from action.nim. The implementation plan pins the exact
transcriptions (review change #3): the `bradsOf` formula
(`floorMod(pyRound(arctan2(-dy, dx) / (2.0 * PI) * AimBradsTurn.float),
AimBradsTurn)`, duplicated privately in strategy.nim exactly as fight.nim,
items.nim, and worldmap.nim already duplicate it), the integer
degenerate-delta test before `arctan2`, the sector gate `Squads and not
squadOrderPostActive and defensivePost.isNone` (NOT
`defensivePostOpponent.isNone` — the geometric-fallback defender must keep
its offset), the modulo order (offset folded before the sweep), and the
oscillator's inclusive clamps.

**Intended behavior change: none — bit-identical policy output (command
masks + chat)** on recorded wire (`tools/compare_stencil.py`). The claim is
policy-output parity, not helper-level equivalence: the old helpers had
unreachable branches (nil-worldmap, missing selfXy) that the early-out in
`resolveAction` shields, and the new shape represents those as `none`
instead.

**B — mind emits the fully swept per-tick aim (oscillator moves to
strategy).** Maximally dumb body, but the oscillator's stepping is coupled
to a body-side outcome (it advances only when no combat target and no
override aim fired — recon §"the one consumer"). The mind would either step
unconditionally (a behavior change with no hypothesis behind it) or need
the body to report idleness back (a new reverse channel). Rejected:
strategy gains execution state and the contract gains a leak in the other
direction.

**C — rethink idle-aim policy while moving it** (per-rung contextual aim
stamped by each ladder producer, or aim derived from believed tracks /
post reach profiles instead of pedestals). This is the actually-interesting
strategy-rework work, but it is a real behavior change that deserves its
own hypothesis and A/B — and it becomes *cheap* once the computation lives
mind-side. Deferred; A is its enabling move.

Sub-decisions under A: the field carries **brads, not a point** — the
sector offset and degenerate-delta fallback are angular, and strategy runs
every tick so mind-computed brads are exactly as fresh as today's act-time
computation; the name "threat axis" dies with the body code (`idleAimCenterBrads`
/ `idleAimAxis` say what it is).

## Consequences and kills

- Deleted: `threatAxis`, `sweepTarget` (action.nim:62-89); action.nim's
  reads of `stealTarget`, `defensivePostOpponent`, `spawnAim`,
  `sectorOffsetBrads`. Grep gate:
  `grep -n "threatAxis\|sweepTarget\|stealTarget\|defensivePostOpponent\|sectorOffsetBrads\|spawnAim" action.nim`
  → 0 hits. (`squadOrderPostSightlineAim` legitimately remains in
  `peekDuckOverride` — out of scope, per the task.)
- Kept: `sectorOffsetBrads` in squads.nim (now consumed by strategy);
  `spawnAim` (respawn reset + trace); `sweepOffset`/`sweepDir` on Belief
  with their respawn reset and replay fields; `SweepHalfArc` /
  `AimSweepStepBrads` knobs.
- Touched files: types.nim (+1 field), strategy.nim (helper + stamp),
  action.nim (delete + idle-branch rewrite), policy.nim (+1 stamp line).
  No new dependencies; deterministic; build pin stays 0.7.215.
- Docs in the same task: sketch close-out addendum updated to record the
  kill as complete; WORKING_CONTEXT leak list reconciled; VERSION_LOG entry
  on upload. The emergant fork mirrors this code and is explicitly NOT
  touched (drift noted in recon).

## Validation plan (preregistered)

The recorded-wire comparator is **the falsifier** for this refactor: a
pre-change baseline PASS on a fresh v68 self-play wire corpus (1v1 /
4ffa / forced-active 1v1; 48 seat-files), then the identical run
post-change must PASS exactly. A comparator failure is a design/impl bug —
the later aggregate steps cannot rescue it. The later steps are not
parity proofs; they are the loop's standing evidence contract for any
upload (the corpus is self-play, so hosted coverage gaps are real).

1. Clean compile; `tools/compare_stencil.py` on the pre-captured baseline
   corpus — **expect exact policy-output (mask/chat) parity**.
2. Upload (inert, v69) → local forced-active self-play gates (post-upload,
   per the lab loop — this is not a pre-upload gate): duck% in the 7-13%
   forced-active band; peek% watched (both standing v68 watch metrics).
3. Matched campaign-shaped hosted A/B vs v68 per
   `docs/tournament-like-experience-requests.md`, v68's 58-episode/arm
   shape if the credit budget allows (2500/wk; say so explicitly if cut).
   Preregistered metrics: hits/shots, kills, duck%, peek%. **Preregistered
   expectation: parity** (any significant aim-metric delta is a red flag
   to investigate, not a win to claim).
4. Champion submission remains James's call only.
