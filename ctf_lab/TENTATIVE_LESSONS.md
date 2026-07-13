# CTF tentative lessons — session buffer

**Session started:** 2026-07-10 12:52. This is THIS SESSION's lesson buffer. Write
candidate lessons here **as you go** — eagerly and noisily; most will be noise and
that's fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you write
here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`ctf_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (CTF-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### CTF is a Crewrift fork → reuse crewrift_lab tooling + cady's SDK bridge, don't rebuild
Evidence: coworld-ctf keeps Crewrift's Sprite-v1 protocol, continuous movement, LoS, and
replay infra verbatim; only the game layer (teams/guns/flags/fog) differs. So `crewborg`'s
perception decoder + movement controller and `cady`'s `run_sprite_bridge` wiring transfer
directly to a CTF Python player. Confirmed while scaffolding the lab (2026-07-10).
Status: prior for build-path choice; unverified against a real CTF build yet.

### Scoring is win-only (+100/0) → optimize win rate, never K/D
Evidence: RULES.md + results_schema record kills/deaths/captures but award 0 points; only
the winning team scores. A kill-farming bot that never captures/wipes scores 0. Metric for
evals must be win rate by team/seat, and the win *path* (capture vs wipe vs timeout).

### CTF games (vs baseline) are decided by WIPE, not capture — so survival wins
Evidence: beacon:v1 vs ctf-baseline-16:v4, 12 episodes: captures 0 on BOTH sides every
game; beacon lost 0-12 by being fully wiped (288 deaths = 8×3 lives × ~12 games) vs
baseline's 110. Since nobody captures, the team that keeps its lives wins (wipe, or the
time-limit tiebreak on lives-remaining). Implication: defense/survival is at least as
valuable as attacking; 8 identical rushers into a defended pedestal is a losing shape.

### beacon is field-relative: crushes co-gas opponents, loses to the elite Nim baseline
Evidence: beacon:v2 vs co-gas-ctf-simple-richard:v4 = 3-0 (early), wiping co-gas every game
(co-gas 24 deaths/game = full wipe; beacon only 6), kills 90-0. But beacon:v2 vs
ctf-baseline-16:v4 = 0-10 (beacon wiped). The baseline is a purpose-built Nim bot (tracks,
cover model, Dijkstra exposure-cost nav, peek-fire-duck) — beating it head-to-head is the
hardest bar in the division. "Doing well" should be judged field-relative (beats 2 of 3
opponents decisively), not solely vs the champion. CTF league uses team_blocks seating so
these 8v8 head-to-heads ARE the league matchup shape.

### The real gap vs the baseline is COVER USE, not roles
Evidence: v2 defenders correctly hold their line + intercept visible thieves (diag confirms
the logic), yet still get wiped by the baseline (24 deaths/game). They lose firefights
because they stand/sit in the OPEN while the baseline peek-fires from behind obstacles. The
next lever after roles is cover-seeking (snap hold points to walkable cells hugging an
obstacle; the bake already has the grid to compute cover cells offline). Deeper than roles.

### v1 minimal-loop was mechanically sound but strategically naive — roles are the gap
Evidence: beacon:v1 diag traces show clean nav (spawn x=193 → enemy pedestal x=1050),
aim, fire (180 kills), respawn, zero stuck. It just rushed solo to the enemy's DEFENDED
pedestal and died on enemy turf (far respawn walk-back) while its own flag sat undefended.
The deferred "roles" capability is exactly what's missing. Confirms the design call to ship
the minimal loop first: the eval pinpointed the highest-leverage next change in one round.

### Friendly fire was beacon's biggest silent cost — the FF gate flipped co-gas 7-8 → 19-0
Evidence: v2 vs co-gas 7-8 with beacon losing 6.1 deaths/game while co-gas got 0 KILLS
(all beacon deaths were self-inflicted friendly fire; FF is ON). Adding a teammate-in-
corridor fire gate (v3) dropped beacon deaths to 3.4/game and the record went to 19-0.
Perceiving teammates ("player <own_color>") + not firing when one is within ~22px of the
shot ray, closer than the target. Lesson: with FF on, an un-gated snap-fire overlay is a
major self-own; gate it before anything else.

### Cover-seeking + better trades narrowed the baseline gap but didn't close it (still 0-20)
Evidence: v3 vs baseline still 0-20, but beacon deaths 24→22.8/game and kills 162→345 vs
v2. The baseline (purpose-built Nim: tracks, exposure-cost nav, peek-fire-duck) is a very
high bar head-to-head. beacon is now clearly the 2nd-best policy in the division (crushes
both co-gas variants) — "doing well" field-relative, not vs the champion.

### The "stuck on the flag" bug: carried flag rides ~10px above carrier, missed a 6px check
Evidence: attackers reached the enemy pedestal but never brought the flag home (watched
replays). Root cause: sim emits a carried flag at carrier.y - CarriedFlagLift(10px), so the
flag's observed centre is ~10px from our self-sprite centre — but perception's _CARRY_DIST
was 6px, so i_carry was NEVER true (confirmed: 0 True across 38,204 logged snapshots). The
carrier stayed in "steal" mode and the steal flow-field treats the pedestal-it-stands-on as
"arrived" → it sat there. Fix: _CARRY_DIST 6→24px, pedestal-test-before-carry-test ordering.
Result: beacon:v4 vs co-gas went 19-0 (wipe/tiebreak, 3.4 deaths/game, 496 kills) → 20-0 by
CAPTURE (20 captures, 0.0 deaths, 5 kills — games end instantly). Lesson: when reading a
game's rendered objects, account for sprite draw-offsets/lifts vs the logical entity centre;
a threshold tuned to logical distance silently fails on the rendered offset.
