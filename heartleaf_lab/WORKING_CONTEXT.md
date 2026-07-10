# Heartleaf working context

**What this is.** The live, high-signal state of *what we're working on right now* in the
Heartleaf lab — the minimal cross-session facts to carry into the next session. Read it on
startup to resume; **update it as you learn** (keep it tight). This is *not* a log: the full
game reference lives in [`docs/heartleaf-gameplay.md`](docs/heartleaf-gameplay.md); this file
is the one-screen "where are we and why."

> Read order for a newcomer: this file → [`README.md`](README.md) →
> [`docs/heartleaf-gameplay.md`](docs/heartleaf-gameplay.md). And the lab-wide
> [`../AGENTS.md`](../AGENTS.md) for the operating model.

---

## Status (2026-07-08, session 2): cady is the Heartleaf CHAMPION — full deterministic build

`cady` went from "runs but scores 0" to **league champion** this session, fully deterministic
(no LLM). The whole day loop works and is proven in hosted evals:

    gather (39-garden circuit) → invite (door-to-door, 3-4:45 PM) → host (own house, 6:55 resolve)
    + attend (accept an invite when food is low — reciprocity / self-play)

**Champion: `cady:v20`** (rank 1, score ~249) submitted 2026-07-08 (`sub_ed58259d`,
`--auto-champion always`, membership `lpm_1ba945b3`). **`cady:v21` just submitted** (`sub_d860f316`,
adds attend mode) — qualifying async when this was written (watcher: `scratchpad/qual_v21.log`).
**91 tests pass.** Version history + per-version detail: `cady/VERSION_LOG.md`.

Latest field eval (v21, 1 cady + 8 random): **14/15 scored, mean 152, harvest min 161**. Cady
out-hosts the entire villager field combined ~19× (~5 attended parties/game vs their ~0.3).

The game repo is cloned at **`~/coding/coworld-heartleaf`** (reference only). Our expander PR
(#15) is **merged** there (HEAD ~`ffa907e`); it adds `tools/expand_replay.nim` + I added
`tools/export_map_png.nim`.

## Key facts (the hard-won ones — full detail in the docs)

- **Scoring:** `hosted food × guests`, only the host scores, guests score 0. Dinner **RESOLVES at
  6:55 PM (`DinnerTallyMinutes`), not the 6:00 shown on the clock.** Food/variety irrelevant —
  only total item count matters. Exact timing table (minute↔tick, league dayTicks 2400+240=2640):
  `docs/heartleaf-gameplay.md` "Exact timing".
- **Seat identity:** house index == gnome index == perception's `own_house_index` (verified in
  `addPlayer`). Owner display names by house: `config.PLAYER_NAMES` (Ivan…Egor).
- **Villager exploit (`docs/villager-dinner-attendance.md`):** their LLM accepts an invite iff it
  hears one naming a house AND is "free" (not committed/hosting). First invite heard wins (no
  double-booking). Food-rich villagers host (unavailable); food-poor accept. They start their own
  hosting at 4 PM → hit them 3-4 PM while free. **Villager LLM is WORKING in xreq (measured);
  league-path reliability unverified.**
- **Chat hearing = viewport, not radius:** a gnome hears our chat iff our bubble lands on their
  320×200 viewport ≈ they're in view of us. Perception only returns on-screen gnomes.

## What shipped this session (v7→v21, the arc)

Root-cause fixes, each verified by eval: **v8** ws-keepalive disconnect (was dropping ~33s in —
the real cause of every early "0 score"); **v9** reliable harvest (press A in range + retry);
**v10** stop house-oscillation (only press A at real food); **v11** press-and-verify A cadence +
host floor (enter own house); **v16** THE clock fix (game emits "\<Weekday\> 3:00pm"; our parser
rejected the weekday prefix → clock read None → all timed phases dead — first points once fixed);
**v18** door-to-door invite rush (15/15 scored, +33%); **v19** navigator stuck-detection re-plan
(fixed rare ~27-food games); **v20** comprehensive tracing → submitted → CHAMPION; **v21** attend
mode (self-play now produces guests: 435 vs 0; no host regression).

**Tracing (v20+):** `CADY_DIAG` stderr lines — periodic full-state snapshots (belief+nav+social)
+ transition lines (mode/strategy/inventory/invite-tour/party-commit/chat). SDK trace_sink →
episode artifact for mode/strategy/fallback events.

**Analysis tooling (all in `heartleaf_lab/tools/`):** `expand_replay` (build via
`build_expand_replay.sh`) → per-tick positions + tagged events incl. `heard_by` for chat;
`viz_replay.py` (travel lines), `viz_occupancy.py` (per-hour crowd heatmap), `build/viz_flow_field.py`
(movement flow), all over the real map (`export_map_png.nim` in the game repo dumps the art).
Occupancy heatmap baked to `cady/mapdata/occupancy.npz` (178 replays / 16M samples).

## Open threads (next steps)

1. **Confirm v21 qualified** (watcher `scratchpad/qual_v21.log`) — should become champion.
2. **The score lever is now recruiting CONVERSION** (guests-per-party ~1.3; volume already
   dominant). Getting 1→2+ guests/party multiplies score. This is what the **LLM social layer**
   (increment 3, designed in `docs/designs/cady-social-llm-controller.md`) targets: smart
   target selection (food-poor acceptors), authored/persuasive chat, and the deferred
   **PlayerRecord** (track who we invited / who accepted / who reciprocated).
3. **LOCAL SMOKE TESTS BLOCKED:** the heartleaf *game* Docker image got pruned/untagged
   (`heartleaf-0.1.10-N:downloaded` missing though cogames shas present). `coworld download` no-ops
   (manifest cached). Re-tag or force re-pull before relying on `coworld-local-run`. Hosted evals
   are the authoritative test regardless.

## Eval how-to
- Field: Competition div `div_396961a3-58af-4276-abc7-3f45fb7fe337`, league
  `league_f831ba75-e81b-4796-b8c6-cd10be18c0bf` (re-resolve live before submit — ids rotate).
  Roster = 9 seats. Self-play = 9× `cady:vN` (verifies attend / social; the field-eval can't).
  **No -100 here** — detect failures via episode status, not score≤0.
- Identify Cady in replays by **`user="Cady"`**, never display name (game-assigned, varies).
  Measure scoring/competitive questions from the **dinner events** (they ARE the scoring records;
  cross-check vs results.json) — not positional reconstruction.
- Fetch artifacts with `--elevated` (team access is opt-in). CADY_DIAG lands in the stderr
  policy-log now (folded), plus the SDK artifact zip.

## Discipline (from [`../AGENTS.md`](../AGENTS.md))

Human sets strategic direction; you build observability, measure, hold the correctness gate.
**Propose-and-pause.** Change one component per iteration. Uploading is routine/ungated;
**league submission is the human's gate** (public, champion-making, hard to roll back).
