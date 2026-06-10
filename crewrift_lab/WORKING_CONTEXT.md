# Crewrift working context

**What this is.** The live, high-signal state of *what we're working on right now* in
the Crewrift lab — the minimal set of cross-session facts worth carrying into the next
session. Read it on startup to resume; **update it as you learn** (keep it tight —
prune anything no longer load-bearing). **Clear and reseed it when we pivot to a whole
new direction** (a new objective/hypothesis class), keeping only the new objective.

This is *not* a log or a report archive: reports/replays live with their episodes,
finished work lives in git history / the [version log](crewrift/crewborg/version_log.md),
and durable preferences live in [`user_preferences.md`](user_preferences.md). This file
is the one-screen answer to "where are we and why."

> The active policy/version here is also the onboarding signal: a recorded objective
> below means onboarding is done — resume the loop (see [`AGENTS.md`](AGENTS.md)),
> don't restart [`../docs/getting-started.md`](../docs/getting-started.md).

---

## Current objective

Improve **crewborg** (the Python policy under optimization). Submitted champion is **v19**
(`358ec5fb…`, `sub_2d6d92bf`) = v17 brain + the spawn-freeze fix, behavior-identical.
**Uncommitted-to-league behavior changes now sit on `main` but are NOT built/uploaded yet**
(would be a v20): ground-truth tick everywhere + kill-CD 500 (see shipped below). Build +
A/B v20-vs-v19 before any submit (kill-CD 500 is a real imposter-timing change).

**Between directions:** awaiting the next direction (candidate threads at the bottom).
Parked, ready when wanted: the **role-rotation eval** (v19, 42 eps, imposter-vs-crewmate
with opponents rotated — `/tmp/v19_imp`, `/tmp/v19_crew` were the *confounded* top_n run;
the corrected manual-role-RR run completed but its readout hasn't been pulled/analyzed).

## Working lens — the score-anomaly filter

Cheap signal: flag any episode whose crewborg score is **not** a "clean success" value
(scoring in [`docs/crewrift-gameplay.md` §6](docs/crewrift-gameplay.md)):

- **Crewmate** clean: **8** (all 8 tasks, lost) or **108** (all tasks, won).
- **Imposter** clean: **20 / 30** (lost, 2–3 kills) or **120 / 130 / 140** (won, 2–4 kills).

Join the score to crewborg by **`policy_version_id`**, never by slot position — the same
league field can contain a *different* player's same-named fork (e.g. a `crewborg-v23`).
Daily-league round episodes (with inline scores) are queryable cheaply via
`coworld episodes --round <id> --policy crewborg --json` — no artifact pull needed.

## Recently shipped (this session — context, not a to-do)

- **Slow-start FIXED.** The "slow to leave spawn" symptom was a **~13.7s first-tick init
  stall** (nav graph + occupancy substrate built live on tick 1; ~14s under the 250m cap →
  frozen at spawn while the engine streamed ~330 frames ahead). Fixed by baking both
  **offline** (`tools/nav_bake.py` → vendored `map/croatoan_navbake.pkl.gz`; loaded +
  validated at runtime by `navbake.py`, live-build fallback on mask mismatch). Hosted v19:
  tick-1 `step_ms` ~65ms vs ~13,700ms (~200×), play byte-identical. Re-bake only when the
  league redeploys a changed map (capture via `CREWBORG_CAPTURE_WALKABILITY=1`).
- **Vote-timeout: same root cause, resolved by the above.** The rare early-meeting
  vote-timeout (3/312 in v17) was the spawn-freeze backlog making the vote-cursor run on a
  stale reading; the actuator itself is sound (v19 artifacts: cursor advances 1 slot/press,
  converges in ~8). Accepted as resolved by the v19 fix; a v18-vs-v19 A/B to *confirm* the
  rate dropped to ~0 was offered but not run (optional).
- **Tracing reworked** to the SDK's `TraceOutputs`, default `jsonl@artifact` — per-tick
  traces/metrics now upload as an **uncapped player-artifact zip** (escapes the 9,999-line
  log cap), with stderr fallback. New bridge latency metrics (`bridge.step_ms` /
  `loop_gap_ms` / `tick_drift`) + a per-tick `voting` actuation snapshot. Pull the zips with
  the `coworld-episode-artifacts` skill (`policy_artifact_{N}.zip`).
- **Ground-truth tick (on `main`, not yet uploaded).** The game now streams its
  authoritative tick as a `"tick <N>"` marker sprite (id 5016); `scene.server_tick()` parses
  it and the bridge drives the SDK runtime from it (`runtime.tick = server_tick-1`), so
  perception, `belief.last_tick`, and **all tracing/metrics** use the engine's true tick
  (not the local frame counter); `tick_drift` is now ground-truth. Other new-game signals
  (config display, who-reported) are *future* — not yet streamed.
- **Kill-CD 500 (on `main`, not yet uploaded).** `DEFAULT_KILL_COOLDOWN_TICKS` 900→500 to
  match the live game; imposter no longer idles on a phantom 900-tick cooldown pre-measure.

## Pinned — return to later

- **Perception-vs-replay validation.** Cross-check what crewborg *perceived* (belief:
  self-xy, cursor_slot, scene — now in the artifact trace) against what the replay says
  *actually happened* (`expand_replay`). Catches perception lies; the actuation trace to do
  it now exists.
- **Bimodal steady-state step.** ~half of v18 games ran ~5× heavier per tick (p99 ≈22ms vs
  ≈5ms), unexplained by role/mode/meeting/kills — likely nav route-planning geometry or
  perception (the `nav.route_len`/`visible_players` decision fields were trimmed, so unseen).
  Well under the 42ms budget, so low urgency.

## Candidate next directions (awaiting the human's pick)

- **The big fish — crewmate task-incompletion (~67/312 eps, the dominant anomaly).** Score =
  tasks done (1–7), lost. Needs a killed-vs-idle split (replays/traces) to know if it's a
  real crewborg fault vs "team lost fast." Most scoreboard upside — never tackled.
- **Imposter under-killing (~10/312 eps, 1 kill).** Otherwise a strong imposter (≥2 kills in
  ~87% of imposter games, never 0).
- Tooling: codify the score-anomaly filter into the `crewrift-report` skill.
