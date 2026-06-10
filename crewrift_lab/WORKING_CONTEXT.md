# Crewrift working context

**What this is.** The live, high-signal state of *what we're working on right now* in
the Crewrift lab — the minimal set of cross-session facts worth carrying into the next
session. Read it on startup to resume; **update it as you learn** (keep it tight —
prune anything no longer load-bearing). **Clear and reseed it when we pivot to a whole
new direction** (a new objective/hypothesis class), keeping only the new objective.

This is *not* a log or a report archive: reports/replays live with their episodes, and
durable preferences live in [`user_preferences.md`](user_preferences.md). This file is
the one-screen answer to "where are we and why."

> The active policy/version here is also the onboarding signal: a recorded objective
> below means onboarding is done — resume the loop (see [`AGENTS.md`](AGENTS.md)),
> don't restart [`../docs/getting-started.md`](../docs/getting-started.md).

---

## Current objective

Improve **crewborg** (the Python policy under optimization). Newest uploaded version is
**v17** (`policy_version_id bd97b769-57fc-4279-a0b0-fc628e056a2d`); nothing newer has
been shown better, so v17 is the current baseline. Not in a submit-decision yet.

Immediate focus: **find and fix crewborg's biggest score leaks**, starting from a
cheap score-anomaly scan of recent daily-league play (below).

### Active investigation — possible cross-cutting actuation/latency bug

Working hypothesis (human-originated): the vote-cursor non-convergence and the
"slow to leave spawn" symptom share a root cause — **Python per-tick latency**.
Architecture supports it: the engine is **real-time push at ~24 Hz** (not lockstep;
`docs/crewrift-player.md` §"one logical frame per game tick"), and hosted players get
**250m CPU / ¼ core** (`../player-build.md`). If `runtime.step()` exceeds the ~42 ms
tick budget, frames queue and crewborg's inputs land late/coalesced → erratic cursor
stepping + delayed first movement. `scene.tick` is a **local `+=1` counter**
(`coworld/policy_player.py:66`), so "am I behind?" must be measured in **wall-clock**,
not tick numbers. **Caveat that shapes how we read metrics:** the bug likely only
reproduces under the hosted 250m cap — a full-CPU local run may hide it (throttle, or
read from a hosted experience request).

Observability we're standing up to confirm/refute (see WORKING below + the agent
turn that defined it): per-step wall-time vs the 42 ms budget, wall-clock fall-behind
(loop-gap / cumulative drift), and action→effect lag (cursor_slot/skip and self-xy per
tick). Metrics sink already exists (`trace.py` `StderrJsonMetricsSink`, gated by
`CREWBORG_METRICS=1`); the gaps are a few lightweight additions in the **bridge**.

## Working lens — the score-anomaly filter

Flag any episode whose crewborg score is **not** a "clean success" value (see scoring
in [`docs/crewrift-gameplay.md` §6](docs/crewrift-gameplay.md)):

- **Crewmate** clean: **8** (all 8 tasks, lost) or **108** (all tasks, won).
- **Imposter** clean: **20 / 30** (lost, 2–3 kills) or **120 / 130 / 140** (won, 2–4 kills).

Join the score to crewborg by **`policy_version_id`**, never by slot position — the
same league field can contain a *different* player's same-named fork (e.g. a
`crewborg-v23` in another slot).

## Live findings (this direction)

From a scan of the **latest 3 completed daily-league rounds** (262/261/260;
`league_605ff338-0a2e-4e62-aeda-559df9a9198f`) — **312** completed v17 episodes,
**~25% anomalous**, **0 ops/disconnect failures** (crewborg is robust):

1. **Crewmate task-incompletion — 67 eps (dominant).** Score = tasks done (1–7), lost.
   Mixed: "killed/idle/too-slow" (real fault) vs "team lost fast, no chance." Needs a
   killed-vs-idle split from replays/traces before it's actionable.
2. **Vote-timeout (−10) — diagnosed: vote-cursor actuator is fragile.** *Rate is rare*
   — exactly **3/312 (1.0%)**, −30 pts total (corrected: NOT higher than the anomaly
   filter showed). But the mechanism is a real **execution-layer** bug: crewborg picks
   its vote instantly, then drives the ballot cursor by edge-pressing `down` until the
   skip-cursor sprite shows (`action.py:336-339`), then `a`. This **sometimes never
   converges** — observed 6 presses→success vs **120 presses→never reached skip→timeout**
   in matched deterministic-skip votes (note: the league runs the LLM-*off* deterministic
   path). Perception is ruled out (skip is a clean dedicated sprite); decision is instant.
   Same stepping drives targeted player-votes (`cursor_slot==target_slot`), so it likely
   degrades voting reliability more broadly than the 3 timeouts show.
   **Next step to pin it:** add a per-tick Voting trace of `voting.cursor_slot` /
   `skip_cursor_present` / candidate count, re-run (local Gate-1 or forced-meeting XP
   request), watch a timing-out meeting → separates "cursor stuck" (input-cadence desync)
   from "cursor cycles but misses skip" (stepping/layout bug). Fix follows from which.
3. **Imposter 1-kill games — 10 eps.** Under-killing; otherwise a strong imposter
   (≥2 kills in ~87% of imposter games, never 0).

## Pinned — return to later

- **Perception-vs-replay validation (augment the latency metrics).** Once the per-tick
  actuation trace exists, cross-check *what crewborg perceived* (its belief: self-xy,
  cursor_slot, scene) against *what the replay says actually happened* (the objective
  `expand_replay` timeline). Catches perception lies and confirms action→effect lag
  against ground truth, not just crewborg's own view. Builds on what we already do with
  `expand_replay`; do it after the metrics land.

## Current tangent (in progress) — tracing rework

**Why we paused the latency work:** crewborg's per-tick tracing writes to stdout/stderr,
but Observatory **caps policy logs at 9,999 lines**, which we blow once metric tracing is
on. The Coworld player contract recently added a way for players to emit **full artifacts
(a zip)**, not just stdout/stderr logs, and the **latest player SDK** should expose
primitives for it. **Goal:** rework crewborg tracing to write a compact/efficient format into a zip and
upload via the new artifact method instead of flooding stderr (Observatory caps player
logs at 9,999 lines).

**Mechanism — fully understood (player SDK + metta both landed):**
- **SDK primitive** (`players.player_sdk.TraceOutputs` / `TraceOutputSpec`, in
  `player_sdk/trace_outputs.py`; players repo #63, *not* in our pinned `18ec2788` — needs
  `uv lock --upgrade-package players`). Env-driven: `CREWBORG_TRACE_OUTPUTS` = list of
  `format@destination` (`jsonl|json|csv|parquet` @ `stderr|stdout|file:<p>|artifact[:name]`),
  default `jsonl@stderr`; `CREWBORG_METRICS` toggles metric fanout. `artifact` writers
  stream to temp files; on `close()` → `manifest.json` + **ZIP_DEFLATED** zip → PUT/copy to
  `COWORLD_PLAYER_ARTIFACT_UPLOAD_URL`.
- **Runner contract** (metta #15290, now on HEAD): runner injects
  `COWORLD_PLAYER_ARTIFACT_UPLOAD_URL` — local = `file://` workspace path
  (`runner.py:341`), hosted = per-slot presigned S3 PUT (`kubernetes_runner.py:296`,
  dispatcher `_policy_artifact_env_var`). **Max 200 MB**, one `.zip` per slot, stored at
  `jobs/{job_id}/policy_artifact_{slot}.zip`. If the env var is absent the player should
  skip (but the SDK *raises* if a spec says `artifact` and the URL is unset → crash risk).
- **Retrieval:** `GET /jobs/{job_id}/policy-artifact` (lists slots) +
  `/policy-artifact/{agent_idx}` (the zip). Policy-scoped (we own crewborg → can fetch).
- **Reference adoption:** upstream crewborg #64 already did this swap (use
  `TraceOutputs.from_env`, drop the Stderr sinks, keep `TraceConfig` as event_filter) —
  our porting template.

**BUILT (branch `jboggs/trace-artifact-outputs`, decisions: default `jsonl@artifact`,
no parquet):** players pin bumped to `146905e3`; bridge ported to
`TraceOutputs.from_env(default_outputs="jsonl@artifact")` with stderr fallback when the
upload URL is absent (pre-connect crash would −100); `trace.py` trimmed to selection only
(`TraceConfig`; Stderr sinks deleted); `fetch_artifacts.py` + endpoint-map now pull
`/jobs/{job}/policy-artifact[/{idx}]` → `artifacts/policy_artifact_{N}.zip`; docs synced
(design/AGENTS/README/trace-logs/crewrift-replays/player-build/building_players).
**Verified:** 265 tests pass; in the rebuilt amd64 image both paths work (zip with
manifest+telemetry.jsonl via file:// URL; warning+stderr without). **Also fixed en route:**
`PLAYERS_SDK_REF=main` was a Docker layer-cache trap (stale SDK in "fresh" builds) —
build_player.sh now resolves `main`→uv.lock commit.
**REMAINING:** hosted-deploy probe — upload as new version, run a tiny XP request, confirm
`GET /jobs/{job}/policy-artifact` returns crewborg's zip (runner code is on metta main;
deploy status unverified).

**Return point after this:** build the 3 latency metrics (step.duration_ms,
loop_gap/tick_drift, action→effect fields) — now emitted via the artifact path — and read
them under the 250m cap.

## Open threads / awaiting direction

- **Vote-timeout: DIAGNOSED** (finding 2 above) — awaiting direction on whether to fix
  now. Fix path: build the per-tick Voting cursor trace → re-run → pin "stuck" vs
  "misses skip" → repair the actuator (press-cadence or stepping). Low scoreboard
  upside (−30/312) but a clean, attributable execution fix that likely helps voting
  reliability broadly. **Change one thing** if we do it.
- **(B) The big fish — crewmate task-incompletion (67 eps):** `crewrift-report` on round
  262 to split killed-vs-idle. Largest volume; most scoreboard upside.
- **(C) Widen the scan:** all of today's completed rounds; include 286/263 once done.
- Tooling follow-up: codify the score-anomaly filter into `crewrift-report`.
