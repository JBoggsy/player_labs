# CTF working context

**What this is.** The live, high-signal state of *what we're working on right now* in the
CTF lab — the minimal cross-session facts to carry into the next session. Read it on
startup to resume; **update it as you learn** (keep it tight).

> Read order for a newcomer: this file → [`README.md`](README.md) →
> [`docs/ctf-gameplay.md`](docs/ctf-gameplay.md). And the lab-wide
> [`../AGENTS.md`](../AGENTS.md) for the operating model.

---

## Status (2026-07-14, session 3): LEAGUE REDEPLOYED ctf 0.7.4 — beacon ported to the new wire format

**The league redeployed** (new coworld `cow_e7586b05-3b53-465a-bb87-b9847a1b7bf9`, ctf
**0.7.4**, source ref `d60dc27` = coworld-ctf HEAD 2026-07-14; GameVersion 1→2; NOTE the
live xreqs report "ctf v0.7.4" — 0.7.3/`5450c64` + a disconnect-win fix + bot grenades). The old
`cow_325613c1…`/0.5.4 IDs below are stale. **Division scores RESET** — everyone 0.500 with
0 rounds; our old rank-#2 history is void. Breaking changes since our 761c098 pin:

- **3x observation render scale (0.6.0+):** map-layer object coords + sprite sizes arrive
  at 3x map resolution; recover map px via `(obj.x + sprite.w/2) / 3`. FIXED: perception
  `_center` divides once at the seam (`config.RENDER_SCALE = 3`); everything downstream
  (nav.npz, thresholds, belief, traces) stays in map pixels.
- **Flags → hearts (0.7.0):** capture-object labels now `red heart`/`blue heart`. FIXED in
  perception label lookups (internal names still say "flag").
- **Death no longer lifts fog:** a dead viewer sees only terrain, pedestal hearts, and its
  own `corpse <color> <side>` sprite. Perception already reads dead (no `self …` label);
  belief docs updated — dead frames carry no sightings, tracks just age, danger decays.
- **Grenades (0.7.0):** corner pickups, C-button (mask bit 128) charged throw over walls,
  ~40px blast, 2 dmg, hurts thrower/teammates too. Labels: `grenade`, `grenade air`,
  `grenade carried`, `throw target`, `blast stage N`, `grenade sound`. Beacon IGNORES them
  for now (correctness first) — a later iteration can pick up/throw.
- **Scoring:** WinReward 100 → +1 winners / -1 losers per capture-or-wipe.
- **Arena geometry: UNCHANGED** (sim.nim block byte-identical except exports) — `nav.npz`
  needs no rebake. Slot→team, aim/vision/speed constants, CarriedFlagLift all unchanged.
- `CTF_REF` re-pinned to `d60dc27` in `tools/build_expand_replay.sh` (old replays need the
  old pin). All 36 beacon tests green, incl. new wire-scale/heart/corpse regressions.

**DONE this session:** v6 (the port) built + uploaded; **6 x 10-episode 8v8 field evals
run** vs each current division entrant (ids in `scratch/eval_v6_field/xreq_ids.txt`,
results downloaded there, dashboard on :8765). **v6 post-redeploy baseline:**

| Opponent | Result | Notes |
|---|---|---|
| ctf-focusfire:v5 (daveey, #1) | **0-9** | beacon 0 captures, dies 23.9/game vs 13.3 — same gap as the old baseline bot |
| Picasso:v1 (softmaxwell, #3) | **10-0** | all by capture, 0 deaths |
| daf-actinf-ctf-v4:v1 (docxology, #4) | **10-0** | scores ±1 with 0 kills/0 captures/0 deaths — opponent likely never connected/abandoned; weak signal |
| ctf-flankfire:v1 (Aaron, #5) | **10-0** | all by capture, 0 deaths |
| co-gas relhalpha:v7 (#6) | **10-0** | all by capture, 0 deaths |
| co-gas richard:v7 (#7) | **10-0** | all by capture, 0 deaths |

The port restored full function: v6 cleanly beats everyone except daveey's new
**ctf-focusfire:v5**, which replaced ctf-baseline-16 as the wall (0-9, out-fought ~2:1
on kills).

**v6 SUBMITTED (human go-ahead) and QUALIFIED — now the competing champion entry**
(`sub_f319957b…`, membership `lpm_08989373…`, qualified in ~12 min, v5 benched).
Standings at submission: rank #2 of 7 (0.497, 64 mostly-v5 rounds) behind daveey
(0.679). Expect the score to climb as correct-wire v6 rounds accumulate.

**Next levers** (one per iteration): grenades (we ignore them; focusfire may not),
gate a behavior on tracks/danger (pursuit / exposure-aware routing), or
peek-fire-duck micro to close the focusfire gap.

## (prior) Status (2026-07-14, session 2): belief groundwork — player tracks + danger field (uncommitted)

Toward open thread 3 (close the baseline gap), beacon's belief state grew two folded,
**not-yet-gated** structures (`ctf/beacon/belief.py`, config knobs `BEACON_TRACK_*` /
`BEACON_DANGER_*`):
- **Player tracks** (`Belief.enemy_tracks` / `teammate_tracks`, `PlayerTrack` in types.py):
  last-seen pos/tick/facing per player, greedy nearest-neighbour association under a
  reachability gate (Chebyshev, since velX/velY clamp per-axis: MAX_SPEED_PX_TICK = 704/256
  = 2.75 px/tick/axis from sim.nim), EMA velocity across close sightings, TTL 120 ticks
  (~5 s, matches the baseline's). Updated while dead too (ghosts see the whole map).
- **Danger field** (`Belief.danger`, float32 [GRID_H, GRID_W] 0..1): init hot on the enemy
  half / cold on ours; visible enemies stamp 1.0; spreads one walkable-masked 3x3-max ring
  per NAV_CELL/(0.75 x max speed) ticks (~every 3.9 ticks — deliberately slower than a
  fleeing player so the zone lingers); exponential decay half-life 48 ticks.
- **Tracing:** every `snapshot` trace event now carries `enemy_tracks`/`teammate_tracks`
  (pos, age, facing, vel, frames_seen) and `danger` (block-max 4x-downsampled 38x20 grid,
  quantized 0..255, `cell_px: 32`) — renderable as a heatmap; warehouse ingests it as-is.
  Cost: ~3.6 KB/snapshot, update_belief ~15 us/tick.
- Nothing reads these yet — next iteration gates ONE behavior on them (pursuit,
  exposure-aware routing, or aim-at-danger) as its own attributable A/B.
- Known limits (documented in belief.py): no kill percept, so dead enemies' tracks linger
  to TTL; own vision doesn't clear danger (a swept-empty corridor stays hot until decay).

**Replay-overlay upstream change (2026-07-14): PRs OPEN.** Sprite-v1's 0x86 debug-sprite
channel is now implemented end-to-end for CTF; design doc at
`docs/designs/ctf-debug-sprite-overlay-design.md`. Two PRs (designed here, implemented by
Codex under review, both test-green):
- **Metta-AI/bitworld#235** — debug-sprite codec (master's 87724ba) cherry-picked onto
  `daveey/hd-client-pin` (the branch CTF pins; master lacks the HD client). Includes a fix
  for the branch-tip test failure (stale 0x7f mask assertion after ButtonC).
- **Metta-AI/coworld-ctf#6** — server validates (structure + snappy pixels,
  32 KiB/player/tick cap) → records (replay record 0x06) → folds into per-player
  DebugOverlay; keyframes SNAPSHOT overlays (leaves shift indices, so prefix re-fold is
  inexact); global viewer renders the selected player's overlay (map layer, z=29000, id
  pools 40000+idx*1024, payload ids 0..1023). 8 new tests; full suite 67 green.
  DEPENDS on #235: after it merges, bump nimby.lock's bitworld SHA on the PR branch
  (worktrees live at /tmp/codex-ctf-overlay/{bitworld,coworld-ctf}).
Still needed after merge: SDK `pack_debug_sprites_packet()` (coworld-tools), beacon
emitting overlays (danger heatmap + tracks + path), league redeploy for hosted replays.

## (prior) Status (2026-07-14): beacon:v5 SUBMITTED, qualified, competing — rank #2 of 6

**v5 was submitted** (`sub_fb788e45…`, membership `lpm_d5d2e3dc…`) after the session below,
qualified, and is now **competing as our champion entry** in Competition
(`div_37361341…`): **rank #2 of 6, score 0.298** (46 rounds) behind daveey's champion
(0.434). The field grew to 6 entrants — a new #3, Aaron's `ctf-flankfire:v1` (0.274,
173 rounds), sits close behind us. Recent-round form (last 20 rounds, 2026-07-14):
beacon avg round-score ≈0.34 vs daveey ≈0.38 — closer than the cumulative scores suggest.

## (prior) Status (2026-07-10, session 1): beacon:v5 takes games off the baseline (4-11)

**v5 (latest, uploaded — NOT yet submitted):** carrier escort + attack bias. v4 diag vs the
baseline showed attackers grabbed the flag but died solo before delivery, while 5 defenders
sat idle (baseline barely attacks; captures ~0 both sides). v5 adds an **escort rung**
(attackers converge on a teammate carrier and move home WITH it) and shifts **DEFENDER_COUNT
5→3** (5 attackers push+escort). Results:
- **vs baseline: 4-11 (26% win), 4 captures** — up from v4's 0-20/0 captures. First version to
  take games off the champion. Still dies 20.9/game — it wins by CAPTURING before being wiped,
  not by out-fighting.
- **vs co-gas: 16-0, 16 captures, 0 deaths** — no regression (cleaner than ever).

**v4 is the currently-submitted/competing version** (`sub_b7fe5799…`). **v5 is a strict
improvement — re-submitting it is the human's gated call.**

## (prior) Status: beacon:v4 fixes CAPTURE; v3 is the competing champion

**v4 (latest, uploaded, NOT yet submitted):** fixed the "stuck on the flag" bug — a carried
flag renders ~10px above its carrier (`CarriedFlagLift`), but perception's carry threshold was
6px, so `i_carry` was NEVER true (0/38,204 snapshots); the carrier sat on the pedestal in
"steal" mode. Fix: `_CARRY_DIST` 6→24px + pedestal-before-carry ordering + 3 regression tests.
- **vs co-gas: 20-0 by CAPTURE** (1 capture every game; kills 496→5, deaths 3.4→0.0/game —
  games now end instantly by grab-and-run instead of attrition). Bug fully resolved, confirmed live.
- **vs baseline: still 0-~7** (0 captures either side, beacon wiped 24/game). Against the elite
  Nim champion beacon dies before completing a grab-and-run; capturing didn't crack it.

**v3 is the SUBMITTED, qualified, competing entry** (`sub_6f0eb779…`, membership `lpm_d3691543…`).
v4 is a clear improvement (real captures) — **re-submitting v4 is the human's gated call.**

## (prior) Status: beacon:v3 built, uploaded, SUBMITTED — qualifying

The first CTF player, **`beacon`**, is live. A deterministic Player-SDK SpriteV1 cyborg
(design: [`docs/designs/ctf-player-v1-design.html`](docs/designs/ctf-player-v1-design.html)),
vendored at `ctf_lab/ctf/beacon/`. Three iterations shipped this session:

- **v1** minimal loop — lost 0-12 to the baseline (rushed solo, got wiped).
- **v2** seat-based roles (5 defenders hold our turf / 3 attackers push) — 0-10 vs baseline,
  7-8 vs co-gas.
- **v3** friendly-fire gate + cover-seeking defenders + teammate perception — **19-0 vs
  co-gas** (FF was the big cost: beacon deaths 6.1→3.4/game), still 0-20 vs the baseline.

**Submitted `beacon:v3`** to the CTF league (`league_3243d905…`), submission
`sub_6f0eb779…`, membership `lpm_d3691543…`, `--auto-champion always`. **Status: placed,
qualifying async** in Qualifiers(staging) — the commissioner runs qualifier rounds on a
~30-min schedule, so qualification is not instant. Check with:
`uv run python .claude/skills/coworld-policy-lifecycle/scripts/policy_lifecycle.py monitor --name beacon`

**Where beacon stands:** clear **#2 of 3** in the division — dominates both co-gas variants,
loses only to the elite purpose-built Nim `ctf-baseline-16` (rank 1). "Doing well"
field-relative; not the champion.

## Key facts (hard-won this session — full detail in TENTATIVE_LESSONS.md)

- **Games are decided by WIPE, not capture** — captures are ~0 on both sides every game;
  the team that keeps its lives wins (wipe, or time-limit tiebreak on lives remaining). So
  survival ≥ attacking. Metric = win rate + deaths/game, not K/D.
- **Friendly fire is ON and was beacon's biggest cost** — v2 lost 6/game to its own bullets.
  The teammate-in-corridor fire gate (v3) fixed it → co-gas 7-8 → 19-0. Gate snap-fire
  before anything else.
- **The baseline is a very strong Nim bot** (tracks, exposure-cost nav, peek-fire-duck).
  Beating it head-to-head is the division's hardest bar; beacon hasn't yet.
- **beacon never actually CAPTURES** — attackers reach the enemy pedestal (x≥1049) but
  `i_carry` never fires. Either the touch/carry-detection is too tight (perception uses
  ≤6px; baseline uses ≤4px and works) or attackers die/get blocked before the grab. This is
  the top open thread — capturing would win the wipe-stalemate games outright.
- Eval infra: matched 8v8 head-to-heads (team_blocks seating = the real league shape).
  `ctf_lab/tools/agg_eval.py <dir>` aggregates a results dir. Streaming `--watch` fetch got
  stuck "pending" once; a one-shot `--no-replay --no-logs --no-artifacts` results fetch is
  the reliable fallback.

## Open threads (next steps, human-directed)

1. **Confirm beacon qualified** (monitor above) — should enter Competition as #2.
2. **Make beacon CAPTURE** (highest-leverage next lever): fix carry detection / push more
   attackers / escort the carrier. Winning the wipe-stalemate games vs co-gas is already
   done; capturing is how you start taking games off the baseline.
3. **Close the baseline gap**: enemy-track memory (remember foes after they leave the cone),
   exposure-aware routing (avoid cells a remembered enemy covers), peek-fire-duck micro —
   the baseline's remaining edges. Each is one attributable iteration.
4. Ereq ids + results for this session live under `ctf_lab/scratch/` (gitignored).

## Eval how-to
- Division `div_37361341-2970-4dac-9528-55398bab0d1a` (Competition),
  `div_64d9b2dc…` (Qualifiers), league `league_3243d905-d32d-4ec6-978b-fa94751d4a37`,
  coworld `cow_e7586b05-3b53-465a-bb87-b9847a1b7bf9` (ctf **0.7.4**, redeployed 2026-07-14;
  scores reset). Field (7 entrants): daveey, Aaron (`ctf-flankfire`), us, softmaxwell,
  docxology, Richard Higgins, RelhAlpha.
- Build: `ctf_lab/tools/build_player.sh beacon --tag players-beacon:dev`; upload:
  `uv run coworld upload-policy players-beacon:dev --name beacon`.
- beacon behavior knobs are env vars (`BEACON_DEFENDERS`, `BEACON_FF_CORRIDOR_PX`, …) in
  `ctf/beacon/config.py` — set at upload time for A/B.

## Discipline (from [`../AGENTS.md`](../AGENTS.md))

Human sets strategic direction; you build observability, measure, hold the correctness gate.
**Propose-and-pause.** Change one component per iteration. Uploading is routine/ungated;
**league submission is the human's gate** (done this session with explicit go-ahead).
