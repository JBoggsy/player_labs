# Streaming XP-request → artifacts → warehouse pipeline

**Status:** IMPLEMENTED + live-validated 2026-07-01 (xreq_307f10d6, 8 episodes:
overlap, resume, and the first-batch skew alarm all confirmed). Components:
`fetch_artifacts.py --watch` (root skill), incremental builds in the vendored
warehouse, `stream_eval.py` (crewrift-event-warehouse skill scripts/).
**Date:** 2026-07-01

## Problem

The eval half of the improvement loop runs three stages strictly serially today:

1. Create experience request(s) (`coworld-experience-requests`), poll `monitor`
   until **every** child episode is terminal.
2. Then download all artifacts (`coworld-episode-artifacts` /
   `fetch_artifacts.py`), wait for **all** downloads.
3. Then build the event warehouse (`crewrift-event-warehouse` /
   `build_warehouse.py`), wait for the **full** build.
4. Then start analyzing.

Each stage waits for the previous stage to fully drain, even though episodes
finish one by one over many minutes and each finished episode's artifacts and
warehouse extraction are independent of the episodes still running. The wall
clock is roughly the sum of the three stages when it could be close to the max.

## Goal

One continuous, background-runnable pipeline: create the XP request(s), then —
while episodes are still running — pull artifacts for each episode as it
completes and fold fetched episodes into the event warehouse in small batches,
so the warehouse is ready (or nearly ready) the moment the last episode ends.

**This becomes the documented default.** When a human tells an agent "launch an
XP request", the standard flow is: compose + `create` (unchanged), then
immediately kick off the streaming pipeline in the background and monitor it —
never serial monitor → fetch → build.

### Non-goals

- Composing/creating experience requests (stays in
  `coworld-experience-requests`; the pipeline takes already-created `xreq_…` ids).
- Changing the analysis skills (`crewrift-survey`, `crewrift-ab`,
  `crewrift-diagnose`) — they consume the same on-disk episode dirs and
  warehouse, which now simply exist sooner.
- Push/event-based transport. Polling with filesystem coupling is deliberate
  (see Architecture decision).

## Architecture decision

**Decoupled directory-polling loops, coupled only through the filesystem**
(chosen over an NDJSON streaming subprocess protocol and over in-process
imports across skill directories):

- Matches the codebase idiom — "is this done?" is answered by disk state
  everywhere here (`episode_is_complete`, `find_episode_dirs`, the warehouse
  manifest), never by an event stream.
- Crash/Ctrl-C resumable for free: rerun the same command, everything rescans
  disk and continues.
- No new IPC protocol to maintain; latency (one poll interval, ~15s) is
  irrelevant for a background eval pipeline.

Layering follows the repo's game-agnostic-root rule: the streaming *fetch*
(stages 1→2) is game-agnostic and lives in the root skills; the warehouse
stage and the orchestrator are Crewrift-specific and live in `crewrift_lab`.

## Components

### 1. `fetch_artifacts.py --watch` (root, game-agnostic)

Extend `.claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py`:

- New flag `--watch`, valid only with `--xreq` (other discovery modes stay
  one-shot). `--interval SECONDS` (default 15) controls the poll cadence.
- Loop each pass: poll `/v2/experience-requests/{xreq}` + its episode list →
  for each child episode whose status is terminal and whose dir isn't complete
  on disk, run the existing `fetch_episode()` → rewrite `index.json` (which
  gains a `watch: {done, fetched, total, drained}` progress block) → sleep.
- Exit 0 when every child episode is terminal and fetched (or exhausted its
  retries). Progress goes to stderr, same as today.
- Resume mechanism is the existing `episode_is_complete()` idempotency check —
  a partial dir (fetch died mid-episode) fails that check and is retried next
  pass. No new state is needed for the happy path.
- **Bounded retries for artifact-less episodes:** a terminal episode whose
  fetch recorded errors (e.g. an ops-failed episode with no artifacts) must
  not be retried forever. A `watch_state.json` in the out dir records
  `{ref_id: attempt_count}` for episodes fetched-with-errors; retry up to
  **3 attempts**, then record as exhausted in `index.json` and stop retrying.
  This is the only new state file.

### 2. Incremental warehouse build (vendored tool patch)

In `crewrift_lab/tools/event-warehouse/crewrift-event-warehouse`:

- **Skip already-built episodes.** `build_warehouse()` loads the existing
  `manifest.json` (if present) before fanning out; episodes whose prior status
  is `ok` **and** `trace_warning == false` are not reprocessed (no replay
  re-expansion — the expensive part). They return a cheap
  `EpisodeResult(status="cached")` carrying their prior manifest entry.
  Episodes previously `failed` or `trace_warning` are re-attempted.
- **Merge instead of clobber.** The manifest's per-episode entries become the
  union of prior + new (new results win on episode-id conflict); summary
  totals are recomputed from the union. `episode_players.parquet` is rebuilt
  as prior rows (re-read from the existing parquet, minus episodes being
  re-attempted) + new rows.
- Event shards are already incremental-safe (one
  `events/key=<k>/<episode_id>.parquet` file per episode per key); a
  re-attempted episode's shards are overwritten by episode-id, so no stale
  shards survive.
- Net effect: repeated `build` calls over a growing episode dir only pay for
  new episodes. This also makes re-running after a partial failure cheap in
  the existing non-streaming flow.

### 3. `stream_eval.py` — the orchestrator (crewrift_lab)

New script in `crewrift_lab/.claude/skills/crewrift-event-warehouse/scripts/`,
next to `build_warehouse.py`:

- **Inputs:** one or more `--xreq` ids (repeatable), `--out` root,
  `--expand-replay` binary (same hard version-coupling requirement as today),
  `--batch-n` (default 10), `--batch-secs` (default 120), `--interval`
  (default 15).
- **Fetch stage:** spawns `uv run python fetch_artifacts.py --xreq … --watch`
  as a subprocess per xreq (parallel), all writing into one shared episode
  dir; streams their stderr through with an `[xreq-short-id]` prefix.
- **Build loop:** each poll, `find_episode_dirs()` over the shared dir, diffed
  against the warehouse manifest's episode ids. When ≥ `batch-n` new complete
  episodes, or ≥ `batch-secs` elapsed since the last build with ≥ 1 new
  episode, invoke `crewrift-event-warehouse build` over the whole dir (cheap,
  thanks to component 2).
- **Exit:** when all watch subprocesses have exited **and** a final build has
  folded in every remaining episode. Prints the manifest summary (including
  the `trace_warning` check from `build_warehouse.py`'s `summarize()`) plus a
  final reconciliation line: episodes total / fetched / in-warehouse /
  failed-no-artifacts.
- **Early skew warning:** after the **first** batch build, if `trace_warning`
  episodes appear, warn loudly immediately — the operator finds out the
  `expand_replay` binary is version-skewed minutes in, not after the whole
  xreq drains. (An improvement over today, where skew surfaces only at the
  end.)
- Designed to be launched as a background process right after `create`
  returns; an agent checks its streamed progress periodically.

## Error handling

- **Fetch:** unchanged best-effort per-artifact semantics; bounded retries via
  `watch_state.json` (above). One bad episode never aborts the run.
- **Build:** `failed` manifest episodes are retried on subsequent batches
  (they may have been partial downloads that later completed); after the
  final build, persistent failures are listed, never silently dropped.
- **Crash anywhere:** rerun the same `stream_eval.py` command; both loops
  resume from disk state (idempotent fetch, incremental build).

## Default-flow documentation changes

The mechanism only pays off if agents reach for it by default:

- **`coworld-experience-requests/SKILL.md`** — step 4 ("monitor, then pull &
  analyze") is rewritten: immediately after `create`, launch the streaming
  pipeline in the background — `stream_eval.py` when the analysis wants the
  warehouse (the common Crewrift deep-dig case), or
  `fetch_artifacts.py --xreq … --watch` when only artifacts are needed.
  Serial `monitor` → fetch → build becomes the explicit fallback, not the
  default.
- **`coworld-episode-artifacts/SKILL.md`** — document `--watch`.
- **`crewrift-event-warehouse/SKILL.md`** + the vendored README — document
  incremental builds and `stream_eval.py` as the preferred path from "xreqs
  created" to "warehouse ready".
- **`AGENTS.md` (root) loop step 1 / `crewrift_lab` docs** — name the
  streaming path as how the Evaluate step is executed.

Caveat, stated openly: "default" is enforced by skill documentation (the
operating procedure agents route on), not by code — the same enforcement model
as every other discipline in this repo.

## Testing & validation

- **Warehouse incremental merge — unit tests** (vendored package's test
  suite): build over episodes {A,B}, then {A,B,C} → only C is processed;
  resulting manifest + `episode_players.parquet` are equal to a from-scratch
  {A,B,C} build; a `failed`/`trace_warning` episode is re-attempted and its
  shards overwritten.
- **Watch selection — unit test:** factor the "terminal, not yet complete on
  disk, retries not exhausted" selection into a pure function and test it.
- **Live end-to-end:** run one small real xreq (~8 episodes) through
  `stream_eval.py` and verify overlap (artifacts appearing before the xreq
  drains), the final reconciliation line, and resume-after-kill.
