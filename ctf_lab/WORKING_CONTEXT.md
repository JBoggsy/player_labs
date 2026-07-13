# CTF working context

**What this is.** The live, high-signal state of *what we're working on right now* in the
CTF lab — the minimal cross-session facts to carry into the next session. Read it on
startup to resume; **update it as you learn** (keep it tight).

> Read order for a newcomer: this file → [`README.md`](README.md) →
> [`docs/ctf-gameplay.md`](docs/ctf-gameplay.md). And the lab-wide
> [`../AGENTS.md`](../AGENTS.md) for the operating model.

---

## Status (2026-07-10, session 1): beacon:v4 fixes CAPTURE; v3 is the competing champion

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
  `div_64d9b2dc…` (Qualifiers), league `league_3243d905…`, coworld `cow_325613c1…` (ctf 0.5.4).
  Field: `ctf-baseline-16:v4` (rank 1), `co-gas-ctf-simple-richard:v4` / `-relhalpha:v4` (0.8).
- Build: `ctf_lab/tools/build_player.sh beacon --tag players-beacon:dev`; upload:
  `uv run coworld upload-policy players-beacon:dev --name beacon`.
- beacon behavior knobs are env vars (`BEACON_DEFENDERS`, `BEACON_FF_CORRIDOR_PX`, …) in
  `ctf/beacon/config.py` — set at upload time for A/B.

## Discipline (from [`../AGENTS.md`](../AGENTS.md))

Human sets strategic direction; you build observability, measure, hold the correctness gate.
**Propose-and-pause.** Change one component per iteration. Uploading is routine/ungated;
**league submission is the human's gate** (done this session with explicit go-ahead).
