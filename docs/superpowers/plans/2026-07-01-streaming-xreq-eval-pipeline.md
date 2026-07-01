# Streaming XP-request → Artifacts → Warehouse Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Overlap the three currently-serial eval stages (xreq monitor → artifact fetch → warehouse build) into one continuous background pipeline that pulls each episode's artifacts as it completes and folds them into the event warehouse in batches.

**Architecture:** Decoupled directory-polling loops coupled only through the filesystem. `fetch_artifacts.py` gains a `--watch` mode (game-agnostic, root skill). The vendored `crewrift-event-warehouse` gains incremental (skip-cached, merge-not-clobber) builds. A new `stream_eval.py` orchestrates both as one background process. Spec: `docs/designs/2026-07-01-streaming-xreq-eval-pipeline-design.md`.

**Tech Stack:** Python 3.11+, httpx, pyarrow/parquet, uv, pytest. No new dependencies.

## Global Constraints

- **Synchronous code only** — no `async`/`await` (user's global CLAUDE.md).
- **Minimal diff** — extend existing scripts/functions; do not reorganize surrounding code.
- **Game-agnostic root** — nothing Crewrift-specific may land in `.claude/skills/`; the orchestrator and warehouse changes live under `crewrift_lab/`.
- Everything runs via `uv run` from the repo root (root scripts) or from `crewrift_lab/tools/event-warehouse/crewrift-event-warehouse/` (vendored package, its own uv project).
- Progress/log output goes to **stderr**; stdout stays clean (existing convention in both scripts).
- Retry bound for artifact-less episodes: **3 attempts**. Batching defaults: **10 episodes / 120 seconds**. Poll interval default: **15 seconds**.

---

### Task 1: Incremental warehouse build (vendored package)

**Files:**
- Modify: `crewrift_lab/tools/event-warehouse/crewrift-event-warehouse/crewrift_event_warehouse/warehouse.py`
- Modify: `crewrift_lab/tools/event-warehouse/crewrift-event-warehouse/crewrift_event_warehouse/cli.py` (print cached count)
- Modify: `crewrift_lab/.claude/skills/crewrift-event-warehouse/scripts/build_warehouse.py` (`summarize()` prints the new manifest key)
- Test: `crewrift_lab/tools/event-warehouse/crewrift-event-warehouse/tests/test_warehouse.py` (append)

**Interfaces:**
- Consumes: existing `build_warehouse(episodes, out_dir, *, workers) -> BuildSummary`, `EpisodeResult`, `episode_players_table`, `WAREHOUSE_SCHEMA_VERSION`.
- Produces: `BuildSummary` gains field `episodes_cached: int`. Manifest gains top-level key `"episodes_cached"`. Summary counts (`episodes_total/ok/skipped/failed`, `events_written`) now describe the **merged warehouse totals**, not just this call's batch; `episodes_cached` is this call's cache hits. Manifest `episodes` list is now sorted by `episode_id`. Repeated `build` calls over a growing episode set only reprocess new/failed/trace-warned episodes. Task 3 relies on: manifest at `<out>/manifest.json` with `episodes: [{episode_id, status, ...}]`.

All commands in this task run from `crewrift_lab/tools/event-warehouse/crewrift-event-warehouse/`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_warehouse.py` (it already imports `write_episode`, `ReporterEpisodeInput`, `build_warehouse`, `pq`, `duckdb`, and defines `_two_episode_batch`):

```python
def _third_episode(root: Path) -> dict:
    return write_episode(
        root,
        ereq_id="ereq-3",
        results={
            "scores": [7, 4],
            "names": ["A-name", "D-name"],
            "win": [True, False],
            "tasks": [3, 1],
            "kills": [0, 0],
            "crew": [1, 1],
            "imposter": [0, 0],
        },
        replay_rows=[
            {"ts": 2, "player": 0, "key": "entered_room", "value": {"room": "Engine", "phase": "Playing"}},
        ],
        players=[
            {"slot": 0, "player_id": "polA-v1", "display_name": "polA:v1"},
            {"slot": 1, "player_id": "polD-v1", "display_name": "polD:v1"},
        ],
    )


def _event_counts(out: Path) -> dict[str, int]:
    con = duckdb.connect()
    rows = con.execute(
        "SELECT episode_id, count(*) FROM read_parquet(?, hive_partitioning=true) GROUP BY 1",
        [str(out / "events" / "**" / "*.parquet")],
    ).fetchall()
    return dict(rows)


def test_incremental_build_caches_ok_episodes_and_matches_full_rebuild(
    tmp_path: Path, fake_helper: Path
) -> None:
    root = tmp_path / "eps"
    root.mkdir()
    ep1, ep2 = _two_episode_batch(root)
    ep3 = _third_episode(root)
    batch12 = [ReporterEpisodeInput.model_validate(e) for e in (ep1, ep2)]
    batch123 = [ReporterEpisodeInput.model_validate(e) for e in (ep1, ep2, ep3)]

    out = tmp_path / "wh"
    s1 = build_warehouse(batch12, out, workers=1)
    assert s1.episodes_ok == 2 and s1.episodes_cached == 0

    s2 = build_warehouse(batch123, out, workers=1)
    assert s2.episodes_cached == 2          # ep1+ep2 not reprocessed
    assert s2.episodes_ok == 3              # merged warehouse total
    assert s2.episodes_total == 3

    # the incremental result must equal a from-scratch build of the same set
    fresh = tmp_path / "wh_fresh"
    build_warehouse(batch123, fresh, workers=1)
    inc_players = pq.read_table(out / "episode_players.parquet").sort_by(
        [("episode_id", "ascending"), ("slot", "ascending")]
    )
    fresh_players = pq.read_table(fresh / "episode_players.parquet").sort_by(
        [("episode_id", "ascending"), ("slot", "ascending")]
    )
    assert inc_players.equals(fresh_players)
    assert _event_counts(out) == _event_counts(fresh)

    inc_manifest = json.loads((out / "manifest.json").read_text())
    fresh_manifest = json.loads((fresh / "manifest.json").read_text())
    assert {e["episode_id"] for e in inc_manifest["episodes"]} == {
        e["episode_id"] for e in fresh_manifest["episodes"]
    }
    assert inc_manifest["event_keys"] == fresh_manifest["event_keys"]


def test_incremental_build_unions_prior_episodes_not_in_this_call(
    tmp_path: Path, fake_helper: Path
) -> None:
    root = tmp_path / "eps"
    root.mkdir()
    ep1, ep2 = _two_episode_batch(root)
    ep3 = _third_episode(root)
    out = tmp_path / "wh"
    build_warehouse([ReporterEpisodeInput.model_validate(e) for e in (ep1, ep2)], out, workers=1)

    # building with ONLY ep3 must keep ep1/ep2 in the manifest and players table
    s = build_warehouse([ReporterEpisodeInput.model_validate(ep3)], out, workers=1)
    assert s.episodes_total == 3 and s.episodes_ok == 3
    manifest = json.loads((out / "manifest.json").read_text())
    assert {e["episode_id"] for e in manifest["episodes"]} == {"ereq-1", "ereq-2", "ereq-3"}
    players = pq.read_table(out / "episode_players.parquet")
    assert set(players.column("episode_id").to_pylist()) == {"ereq-1", "ereq-2", "ereq-3"}


def test_incremental_build_reattempts_failed_episodes(tmp_path: Path, fake_helper: Path) -> None:
    root = tmp_path / "eps"
    root.mkdir()
    ep1, ep2 = _two_episode_batch(root)
    batch = [ReporterEpisodeInput.model_validate(e) for e in (ep1, ep2)]
    out = tmp_path / "wh"

    results_path = root / "ereq-2" / "results.json"
    good = results_path.read_text()
    results_path.write_text("NOT JSON")          # -> ereq-2 fails extraction
    s1 = build_warehouse(batch, out, workers=1)
    assert s1.episodes_failed == 1 and s1.episodes_ok == 1

    results_path.write_text(good)                # fixed -> re-attempted next build
    s2 = build_warehouse(batch, out, workers=1)
    assert s2.episodes_failed == 0
    assert s2.episodes_ok == 2
    assert s2.episodes_cached == 1               # only ereq-1 was cached
    players = pq.read_table(out / "episode_players.parquet")
    assert set(players.column("episode_id").to_pylist()) == {"ereq-1", "ereq-2"}
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `uv run pytest tests/test_warehouse.py -v -k incremental`
Expected: FAIL — `BuildSummary` has no `episodes_cached` (TypeError/AttributeError) and/or second build reprocesses everything.

- [ ] **Step 3: Implement the incremental merge in `warehouse.py`**

Replace `build_warehouse`, `_summarize`, `_write_manifest` and add helpers. Add imports `pyarrow as pa`, `pyarrow.compute as pc` at the top (keep the existing `pyarrow.parquet as pq`):

```python
@dataclass
class BuildSummary:
    out_dir: Path
    episodes_total: int
    episodes_ok: int
    episodes_skipped: int
    episodes_failed: int
    events_written: int
    distinct_policies: int
    episodes_cached: int = 0


def build_warehouse(
    episodes: list[ReporterEpisodeInput],
    out_dir: Path,
    *,
    workers: int | None = None,
) -> BuildSummary:
    """Fan extraction out across the batch, collate the dimension table, and
    write the partitioned dataset + manifest. Synchronous and process-parallel.

    Incremental: episodes already in the output manifest with status "ok" and
    no trace_warning are NOT reprocessed (no replay re-expansion); the manifest
    and episode_players.parquet are merged with the prior build rather than
    overwritten, so repeated builds over a growing episode set only pay for
    the new episodes. Prior "failed"/trace-warned episodes are re-attempted.
    """
    out_dir = Path(out_dir)
    events_dir = out_dir / "events"
    events_dir.mkdir(parents=True, exist_ok=True)

    prior = _load_prior_manifest(out_dir)
    prior_entries: dict[str, dict] = {
        e["episode_id"]: e for e in (prior.get("episodes", []) if prior else [])
    }
    cached_ids = {
        eid
        for eid, entry in prior_entries.items()
        if entry.get("status") == "ok" and not entry.get("trace_warning")
    }
    to_process = [ep for ep in episodes if ep.episode_request_id not in cached_ids]
    episodes_cached = len(episodes) - len(to_process)

    # A re-attempted episode's old shards must not survive alongside new ones.
    reprocessed_ids = {ep.episode_request_id for ep in to_process}
    for episode_id in reprocessed_ids & set(prior_entries):
        _remove_episode_shards(events_dir, episode_id)

    results = _run_episodes(to_process, events_dir, workers=workers)

    players_table = _merged_players_table(
        out_dir,
        [row for r in results for row in r.player_rows],
        reprocessed_ids=reprocessed_ids,
    )
    if players_table.num_rows:
        pq.write_table(players_table, out_dir / "episode_players.parquet")

    entries = dict(prior_entries)
    for r in results:
        entries[r.episode_id] = {
            "episode_id": r.episode_id,
            "status": r.status,
            "event_count": r.event_count,
            "trace_warning": r.trace_warning,
            "message": r.message,
        }
    event_keys = sorted(
        set((prior or {}).get("event_keys", [])) | {k for r in results for k in r.keys}
    )

    summary = _summarize(entries, players_table, out_dir, episodes_cached)
    _write_manifest(out_dir, entries, event_keys, summary)
    return summary


def _load_prior_manifest(out_dir: Path) -> dict | None:
    """The prior build's manifest, or None (also on schema mismatch -> full rebuild)."""
    path = out_dir / "manifest.json"
    if not path.exists():
        return None
    try:
        manifest = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if manifest.get("schema_version") != WAREHOUSE_SCHEMA_VERSION:
        return None
    return manifest


def _remove_episode_shards(events_dir: Path, episode_id: str) -> None:
    for shard in events_dir.glob(f"key=*/{episode_id}.parquet"):
        shard.unlink()


def _merged_players_table(
    out_dir: Path,
    new_rows: list[EpisodePlayerRow],
    *,
    reprocessed_ids: set[str],
) -> pa.Table:
    """Prior episode_players rows (minus re-attempted episodes) + new rows."""
    tables: list[pa.Table] = []
    path = out_dir / "episode_players.parquet"
    if path.exists():
        prior = pq.read_table(path)
        if reprocessed_ids:
            keep = pc.invert(
                pc.is_in(
                    prior.column("episode_id"),
                    value_set=pa.array(sorted(reprocessed_ids), type=pa.string()),
                )
            )
            prior = prior.filter(keep)
        tables.append(prior)
    if new_rows:
        tables.append(episode_players_table(new_rows))
    if not tables:
        return episode_players_table([])
    return pa.concat_tables(tables)


def _summarize(
    entries: dict[str, dict],
    players_table: pa.Table,
    out_dir: Path,
    episodes_cached: int,
) -> BuildSummary:
    statuses = [e.get("status") for e in entries.values()]
    policies = (
        {v for v in players_table.column("policy_version").to_pylist() if v}
        if players_table.num_rows
        else set()
    )
    return BuildSummary(
        out_dir=out_dir,
        episodes_total=len(entries),
        episodes_ok=statuses.count("ok"),
        episodes_skipped=statuses.count("skipped"),
        episodes_failed=statuses.count("failed"),
        events_written=sum(e.get("event_count") or 0 for e in entries.values()),
        distinct_policies=len(policies),
        episodes_cached=episodes_cached,
    )


def _write_manifest(
    out_dir: Path, entries: dict[str, dict], event_keys: list[str], summary: BuildSummary
) -> None:
    manifest = {
        "schema_version": WAREHOUSE_SCHEMA_VERSION,
        "episodes_total": summary.episodes_total,
        "episodes_ok": summary.episodes_ok,
        "episodes_skipped": summary.episodes_skipped,
        "episodes_failed": summary.episodes_failed,
        "episodes_cached": summary.episodes_cached,
        "events_written": summary.events_written,
        "distinct_policies": summary.distinct_policies,
        "event_keys": event_keys,
        "episodes": sorted(entries.values(), key=lambda e: e["episode_id"]),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
```

Delete the old `_summarize(results, player_rows, out_dir)` and `_write_manifest(out_dir, results, summary)` bodies — they are fully replaced above. `_run_episodes` is unchanged.

In `cli.py`'s `_run_build`, update the final print to include the cache count:

```python
    print(
        f"wrote {summary.out_dir}: "
        f"{summary.events_written} events across {summary.episodes_ok} episodes "
        f"({summary.episodes_cached} cached, {summary.episodes_skipped} skipped, "
        f"{summary.episodes_failed} failed), "
        f"{summary.distinct_policies} distinct policies"
    )
```

In `crewrift_lab/.claude/skills/crewrift-event-warehouse/scripts/build_warehouse.py`, `summarize()`, add `"episodes_cached"` to the printed keys tuple:

```python
    for k in ("episodes_total", "episodes_ok", "episodes_cached", "episodes_skipped",
              "episodes_failed", "events_written", "distinct_policies"):
```

- [ ] **Step 4: Run the full vendored test suite**

Run: `uv run pytest tests/ -v`
Expected: all PASS, including the three new incremental tests. Note: manifest `episodes` are now **sorted by episode_id** (previously input order) — if a pre-existing test asserts positional order, update that test to sort or key by id; the sorted order is the new contract.

- [ ] **Step 5: Commit**

```bash
git add crewrift_lab/tools/event-warehouse/crewrift-event-warehouse/crewrift_event_warehouse/warehouse.py \
        crewrift_lab/tools/event-warehouse/crewrift-event-warehouse/crewrift_event_warehouse/cli.py \
        crewrift_lab/tools/event-warehouse/crewrift-event-warehouse/tests/test_warehouse.py \
        crewrift_lab/.claude/skills/crewrift-event-warehouse/scripts/build_warehouse.py
git commit -m "event-warehouse: incremental builds (skip cached episodes, merge manifest/players)

Repeated 'build' calls over a growing episode dir now only reprocess
new/failed/trace-warned episodes; manifest + episode_players.parquet merge
with the prior build instead of clobbering it. Groundwork for the streaming
xreq->warehouse pipeline (docs/designs/2026-07-01-streaming-xreq-eval-pipeline-design.md)."
```

---

### Task 2: `fetch_artifacts.py --watch` (streaming fetch, game-agnostic)

**Files:**
- Modify: `.claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py`
- Test: `.claude/skills/coworld-episode-artifacts/scripts/tests/test_watch_selection.py` (new; new `tests/` dir)

**Interfaces:**
- Consumes: existing `EpisodeRef`, `discover_by_xreq(client, xreq_id, want)`, `fetch_episode(...)`, `episode_is_complete(out_dir, want_replay, want_logs)`, `Client`, `load_token`, `default_server`.
- Produces: CLI flags `--watch`, `--interval SECONDS` (default 15.0), `--max-attempts N` (default 3). Pure function `select_watch_fetches(refs, out_root, attempts, *, want_replay, want_logs, max_attempts, xreq_drained) -> tuple[list[EpisodeRef], list[EpisodeRef], list[EpisodeRef], list[EpisodeRef]]` (to_fetch, waiting, exhausted, done). Helper `episode_dirname(ref: EpisodeRef) -> str`. On disk: `watch_state.json` (`{ref_id: attempt_count}`) and a per-pass `index.json` with a `watch: {total, fetched, exhausted, pending, drained}` block. Exit 0 when the xreq is drained and every episode is fetched or exhausted. Task 3 relies on: `uv run python fetch_artifacts.py --xreq <id> --watch --out <dir> --interval <s>` running to completion with that exit contract, logging progress to stderr.

All commands in this task run from the repo root.

- [ ] **Step 1: Write the failing test**

Create `.claude/skills/coworld-episode-artifacts/scripts/tests/test_watch_selection.py`:

```python
"""Unit tests for the --watch selection logic (pure function, no network)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fetch_artifacts import EpisodeRef, episode_dirname, select_watch_fetches


def _ref(ref_id: str, status: str) -> EpisodeRef:
    return EpisodeRef(
        ref_id=ref_id,
        created_at="2026-07-01T12:00:00",
        job_id="job-1",
        replay_url=None,
        label=status,
        record={"id": ref_id, "status": status},
    )


def _complete_dir(root: Path, ref: EpisodeRef) -> Path:
    d = root / episode_dirname(ref)
    (d / "logs").mkdir(parents=True)
    (d / "episode.json").write_text("{}")
    (d / "replay.json").write_bytes(b"")
    return d


def test_selection_partitions_done_waiting_exhausted_and_fetchable(tmp_path: Path) -> None:
    done_ref = _ref("ereq_done00000000000", "completed")
    _complete_dir(tmp_path, done_ref)
    running = _ref("ereq_running0000000", "running")
    fresh = _ref("ereq_fresh000000000", "completed")
    failed_terminal = _ref("ereq_failed00000000", "failed")
    tired = _ref("ereq_tired000000000", "failed")

    to_fetch, waiting, exhausted, done = select_watch_fetches(
        [done_ref, running, fresh, failed_terminal, tired],
        tmp_path,
        {"ereq_tired000000000": 3},
        want_replay=True,
        want_logs=True,
        max_attempts=3,
        xreq_drained=False,
    )
    assert [r.ref_id for r in to_fetch] == ["ereq_fresh000000000", "ereq_failed00000000"]
    assert [r.ref_id for r in waiting] == ["ereq_running0000000"]
    assert [r.ref_id for r in exhausted] == ["ereq_tired000000000"]
    assert [r.ref_id for r in done] == ["ereq_done00000000000"]


def test_drained_xreq_sweeps_episodes_with_nonterminal_row_status(tmp_path: Path) -> None:
    # When the xreq itself reports drained, stale per-row statuses must not
    # strand an episode: everything unfetched becomes fetchable.
    running = _ref("ereq_running0000000", "running")
    to_fetch, waiting, exhausted, done = select_watch_fetches(
        [running], tmp_path, {},
        want_replay=True, want_logs=True, max_attempts=3, xreq_drained=True,
    )
    assert [r.ref_id for r in to_fetch] == ["ereq_running0000000"]
    assert waiting == [] and exhausted == [] and done == []


def test_partial_dir_is_retried_not_done(tmp_path: Path) -> None:
    # An episode dir missing its replay fails episode_is_complete -> refetch.
    ref = _ref("ereq_partial0000000", "completed")
    d = tmp_path / episode_dirname(ref)
    d.mkdir(parents=True)
    (d / "episode.json").write_text("{}")   # no replay.json, no logs/
    to_fetch, _, _, done = select_watch_fetches(
        [ref], tmp_path, {},
        want_replay=True, want_logs=True, max_attempts=3, xreq_drained=False,
    )
    assert [r.ref_id for r in to_fetch] == ["ereq_partial0000000"]
    assert done == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest .claude/skills/coworld-episode-artifacts/scripts/tests/ -v`
Expected: FAIL — `ImportError: cannot import name 'episode_dirname'` (and `select_watch_fetches`). If pytest itself is missing from the root env, add it: `uv add --dev pytest`.

- [ ] **Step 3: Implement the watch machinery**

In `fetch_artifacts.py`:

**(a)** Add `import time` to the imports.

**(b)** Factor the episode dir naming out of `main()` (replace the two inline lines in the download loop with a call):

```python
def episode_dirname(ref: EpisodeRef) -> str:
    stamp = ref.created_at.replace(":", "").replace("-", "").replace(".", "")[:15]
    short = ref.ref_id[:16] if ref.ref_id.startswith("ereq_") else ref.ref_id[:8]
    return f"{stamp}_{short}"
```

In `main()`'s loop, replace:
```python
            stamp = ref.created_at.replace(":", "").replace("-", "").replace(".", "")[:15]
            short = ref.ref_id[:16] if ref.ref_id.startswith("ereq_") else ref.ref_id[:8]
            ep_dir = args.out / f"{stamp}_{short}"
```
with:
```python
            short = ref.ref_id[:16] if ref.ref_id.startswith("ereq_") else ref.ref_id[:8]
            ep_dir = args.out / episode_dirname(ref)
```

**(c)** Add the watch section after `fetch_episode` (before the CLI section):

```python
# --------------------------------------------------------------------------- #
# Watch mode: stream artifacts out of a still-running experience request
# --------------------------------------------------------------------------- #

# Episode-row statuses that mean the episode will never change again. Unknown
# statuses are treated as still-running (rechecked next pass); once the xreq
# itself is drained, row status is ignored so a stale row can't strand us.
TERMINAL_EPISODE_STATUSES = {"completed", "success", "failed", "error", "cancelled", "canceled"}


def select_watch_fetches(
    refs: list[EpisodeRef],
    out_root: Path,
    attempts: dict[str, int],
    *,
    want_replay: bool,
    want_logs: bool,
    max_attempts: int,
    xreq_drained: bool,
) -> tuple[list[EpisodeRef], list[EpisodeRef], list[EpisodeRef], list[EpisodeRef]]:
    """Partition an xreq's episodes into (to_fetch, waiting, exhausted, done).

    Pure disk+status logic so it is unit-testable: an episode is `done` when
    its dir passes episode_is_complete, `waiting` while non-terminal (unless
    the whole xreq is drained), `exhausted` after max_attempts error-laden
    fetches, else `to_fetch`.
    """
    to_fetch: list[EpisodeRef] = []
    waiting: list[EpisodeRef] = []
    exhausted: list[EpisodeRef] = []
    done: list[EpisodeRef] = []
    for ref in refs:
        if episode_is_complete(out_root / episode_dirname(ref), want_replay, want_logs):
            done.append(ref)
            continue
        status = str(ref.record.get("status") or "").lower()
        if status not in TERMINAL_EPISODE_STATUSES and not xreq_drained:
            waiting.append(ref)
            continue
        if attempts.get(ref.ref_id, 0) >= max_attempts:
            exhausted.append(ref)
            continue
        to_fetch.append(ref)
    return to_fetch, waiting, exhausted, done


def _xreq_drained(detail: dict[str, Any]) -> bool:
    total = detail.get("episode_count") or 0
    finished = (detail.get("completed_count") or 0) + (detail.get("failed_count") or 0)
    return total > 0 and finished >= total


def _write_watch_index(
    out: Path,
    xreq: str,
    server: str,
    refs: list[EpisodeRef],
    done: list[EpisodeRef],
    exhausted: list[EpisodeRef],
    pending: int,
    drained: bool,
) -> None:
    index = {
        "server": server,
        "selection": {"xreq": xreq, "watch": True},
        "watch": {
            "total": len(refs),
            "fetched": len(done),
            "exhausted": len(exhausted),
            "pending": pending,
            "drained": drained,
        },
        "episodes": [
            {"ref_id": r.ref_id, "dir": episode_dirname(r), "label": r.label} for r in done
        ]
        + [
            {"ref_id": r.ref_id, "exhausted": True, "label": r.label} for r in exhausted
        ],
    }
    (out / "index.json").write_text(json.dumps(index, indent=2))


def watch_loop(
    client: Client,
    args: argparse.Namespace,
    server: str,
    *,
    want_replay: bool,
    want_results: bool,
    want_logs: bool,
) -> int:
    """Poll the xreq; fetch each episode as it turns terminal; exit when drained.

    Resume-safe by construction: completeness is judged from disk
    (episode_is_complete), so a killed run just picks up where it left off.
    watch_state.json bounds retries for episodes that fetch with errors
    (e.g. ops-failed episodes with no artifacts).
    """
    args.out.mkdir(parents=True, exist_ok=True)
    state_path = args.out / "watch_state.json"
    attempts: dict[str, int] = {}
    if state_path.exists():
        attempts = json.loads(state_path.read_text())

    while True:
        detail = client.get_json(f"/v2/experience-requests/{args.xreq}")
        drained = _xreq_drained(detail)
        refs = discover_by_xreq(client, args.xreq, args.num)
        to_fetch, waiting, exhausted, done = select_watch_fetches(
            refs, args.out, attempts,
            want_replay=want_replay, want_logs=want_logs,
            max_attempts=args.max_attempts, xreq_drained=drained,
        )
        for ref in to_fetch:
            ep_dir = args.out / episode_dirname(ref)
            log(f"  [watch] fetching {ref.ref_id[:16]} {ref.label}")
            s = fetch_episode(
                client, ref, ep_dir,
                want_replay=want_replay, want_results=want_results, want_logs=want_logs,
            )
            for err in s["errors"]:
                log(f"      ! {err}")
            if episode_is_complete(ep_dir, want_replay, want_logs):
                attempts.pop(ref.ref_id, None)
                done.append(ref)
            else:
                attempts[ref.ref_id] = attempts.get(ref.ref_id, 0) + 1
                if attempts[ref.ref_id] >= args.max_attempts:
                    log(f"      ! {ref.ref_id[:16]}: giving up after {args.max_attempts} attempts")
                    exhausted.append(ref)
        state_path.write_text(json.dumps(attempts, indent=2))

        total = detail.get("episode_count") or len(refs)
        pending = max(0, total - len(done) - len(exhausted))
        _write_watch_index(args.out, args.xreq, server, refs, done, exhausted, pending, drained)
        log(f"[watch] fetched {len(done)}/{total} "
            f"(pending {pending}, exhausted {len(exhausted)}, drained={drained})")
        if drained and pending == 0:
            log(f"[watch] done: xreq drained; {len(done)} fetched, {len(exhausted)} without artifacts.")
            return 0
        time.sleep(args.interval)
```

**(d)** Wire up the CLI. In `parse_args`, change `-n`'s default and add the watch flags:

```python
    parser.add_argument("-n", "--num", type=int, default=None,
                        help="Max episodes for policy/xreq/pool/round/division modes (default 10; "
                             "unlimited in --watch mode).")
```
and after `--force`:
```python
    parser.add_argument("--watch", action="store_true",
                        help="With --xreq: poll the experience request and download each episode's "
                             "artifacts as it completes; exit when all episodes are terminal and fetched.")
    parser.add_argument("--interval", type=float, default=15.0,
                        help="Watch mode: seconds between polls.")
    parser.add_argument("--max-attempts", type=int, default=3,
                        help="Watch mode: fetch attempts per episode whose artifacts keep erroring.")
```

At the top of `main()` (right after `args = parse_args(argv)`), resolve the default and divert watch mode:

```python
    if args.num is None:
        args.num = 10**9 if args.watch else 10
    if args.watch and not args.xreq:
        sys.exit("--watch requires --xreq (streaming is per experience request).")
```
and after `server = args.server or default_server()` / `args.out.mkdir(...)`:
```python
    if args.watch:
        with Client(server, load_token()) as client:
            return watch_loop(
                client, args, server,
                want_replay=want_replay, want_results=want_results, want_logs=want_logs,
            )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest .claude/skills/coworld-episode-artifacts/scripts/tests/ -v`
Expected: 3 PASS.

- [ ] **Step 5: Sanity-check the one-shot path still works (no behavior change)**

Run: `uv run python .claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py --help`
Expected: help text shows the new flags; exits 0. (Full one-shot behavior is re-verified live in Task 5.)

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py \
        .claude/skills/coworld-episode-artifacts/scripts/tests/
git commit -m "coworld-episode-artifacts: --watch mode streams artifacts from a running xreq

Polls the experience request and fetches each episode as it turns terminal
instead of waiting for the whole batch; resume-safe from disk state, with
bounded (3-attempt) retries for artifact-less episodes via watch_state.json."
```

---

### Task 3: `stream_eval.py` orchestrator (crewrift_lab)

**Files:**
- Create: `crewrift_lab/.claude/skills/crewrift-event-warehouse/scripts/stream_eval.py`

**Interfaces:**
- Consumes: from sibling `build_warehouse.py` (same dir, so `import build_warehouse` works when run as a script): `FETCH` (path to fetch_artifacts.py), `WH_DIR`, `build_request(dirs, out_dir) -> Path`, `find_episode_dirs(root) -> list[Path]`, `summarize(out) -> int` (returns trace_warning count). From Task 2: the `--watch` CLI contract. From Task 1: incremental `crewrift-event-warehouse build` + manifest shape.
- Produces: `uv run python crewrift_lab/.claude/skills/crewrift-event-warehouse/scripts/stream_eval.py --xreq xreq_… [--xreq …] --out /tmp/wh --expand-replay <bin> [--batch-n 10] [--batch-secs 120] [--interval 15] [--workers N]`. Episodes land in `<out>_episodes/` (sibling of `--out`, matching `build_warehouse.py`'s convention); the warehouse builds incrementally into `--out`. Exit 0 on full success; 1 if any watcher failed.

No unit test — this is orchestration glue over two already-tested components; it is verified live in Task 5 (spec's testing section).

- [ ] **Step 1: Write the script**

```python
#!/usr/bin/env python3
"""Streaming eval pipeline: xreq(s) -> artifacts -> event warehouse, overlapped.

The serial flow (monitor the whole xreq -> fetch everything -> build the whole
warehouse) wastes wall clock: episodes finish one by one and each finished
episode's artifacts + extraction are independent of the episodes still running.
This orchestrator overlaps all three stages in ONE background-runnable process:

  - spawns `fetch_artifacts.py --watch` per xreq (episodes stream to disk as
    they complete),
  - periodically folds newly complete episode dirs into the warehouse via the
    INCREMENTAL `crewrift-event-warehouse build` (cached episodes are skipped,
    so each batch only pays for the new ones),
  - exits when every watcher has drained and the final build has caught up.

Crash/Ctrl-C safe: rerun the same command; the watchers resume from disk state
and the incremental build skips everything already in the warehouse.

Usage (run from the repo root; auth from `softmax login`):

    uv run python crewrift_lab/.claude/skills/crewrift-event-warehouse/scripts/stream_eval.py \\
        --xreq xreq_... [--xreq xreq_...] --out /tmp/wh --expand-replay /tmp/expand-<commit>

`--expand-replay` has the same hard version-coupling requirement as
build_warehouse.py (see the SKILL.md); skew is detected and warned after the
FIRST batch, minutes in, instead of after the whole xreq drains.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from build_warehouse import FETCH, WH_DIR, build_request, find_episode_dirs, summarize


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _pump(prefix: str, stream) -> None:
    """Relay one watcher's stderr through our stderr with an xreq prefix."""
    for line in iter(stream.readline, ""):
        log(f"[{prefix}] {line.rstrip()}")


def spawn_watcher(xreq: str, ep_dir: Path, interval: float) -> subprocess.Popen:
    proc = subprocess.Popen(
        ["uv", "run", "python", str(FETCH), "--xreq", xreq, "--watch",
         "--interval", str(interval), "--out", str(ep_dir)],
        stderr=subprocess.PIPE,
        text=True,
    )
    threading.Thread(target=_pump, args=(xreq[:13], proc.stderr), daemon=True).start()
    return proc


def episode_id_of(ep_dir: Path) -> str:
    meta = json.loads((ep_dir / "episode.json").read_text())
    return str(meta.get("id") or ep_dir.name)


def warehouse_episode_ids(out: Path) -> set[str]:
    """Episode ids the warehouse already holds successfully (status ok)."""
    manifest_path = out / "manifest.json"
    if not manifest_path.exists():
        return set()
    manifest = json.loads(manifest_path.read_text())
    return {e["episode_id"] for e in manifest.get("episodes", []) if e.get("status") == "ok"}


def run_build(ep_dirs: list[Path], out: Path, expand_replay: Path | None, workers: int | None) -> None:
    req = build_request(ep_dirs, out.parent / (out.name + "_input"))
    env = dict(os.environ)
    if expand_replay:
        env["CREWRIFT_EXPAND_REPLAY"] = str(expand_replay)
    cmd = ["uv", "run", "crewrift-event-warehouse", "build", "--input", str(req), "--out", str(out)]
    if workers:
        cmd += ["--workers", str(workers)]
    subprocess.run(cmd, cwd=WH_DIR, env=env, check=True)


def trace_warning_count(out: Path) -> int:
    manifest_path = out / "manifest.json"
    if not manifest_path.exists():
        return 0
    manifest = json.loads(manifest_path.read_text())
    return sum(1 for e in manifest.get("episodes", []) if e.get("trace_warning"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xreq", action="append", required=True, metavar="xreq_…",
                    help="Experience request to stream. Repeatable.")
    ap.add_argument("--out", type=Path, required=True, help="Warehouse output directory.")
    ap.add_argument("--expand-replay", type=Path, required=True,
                    help="Version-matched expand_replay binary (CREWRIFT_EXPAND_REPLAY).")
    ap.add_argument("--batch-n", type=int, default=10,
                    help="Build when this many new episodes have landed (default 10).")
    ap.add_argument("--batch-secs", type=float, default=120.0,
                    help="…or when this long has passed since the last build with >=1 new episode.")
    ap.add_argument("--interval", type=float, default=15.0, help="Poll cadence, seconds.")
    ap.add_argument("--workers", type=int, help="Warehouse build workers (default: CPU count).")
    args = ap.parse_args()

    ep_dir = args.out.parent / (args.out.name + "_episodes")
    ep_dir.mkdir(parents=True, exist_ok=True)
    procs = {x: spawn_watcher(x, ep_dir, args.interval) for x in args.xreq}
    log(f"[stream] watching {len(procs)} xreq(s) -> episodes in {ep_dir}, warehouse in {args.out}")

    last_build = time.monotonic()
    first_build_done = False
    while True:
        alive = any(p.poll() is None for p in procs.values())
        in_warehouse = warehouse_episode_ids(args.out)
        ready = find_episode_dirs(ep_dir)
        new = [d for d in ready if episode_id_of(d) not in in_warehouse]
        overdue = (time.monotonic() - last_build) >= args.batch_secs
        if new and (len(new) >= args.batch_n or overdue or not alive):
            log(f"[stream] building warehouse: +{len(new)} new episodes ({len(ready)} fetched total)")
            try:
                run_build(ready, args.out, args.expand_replay, args.workers)
                last_build = time.monotonic()
                if not first_build_done:
                    first_build_done = True
                    warned = trace_warning_count(args.out)
                    if warned:
                        log(f"[stream] ⚠️  {warned} trace_warning episode(s) IN THE FIRST BATCH — "
                            f"the --expand-replay binary is likely version-skewed vs the arena. "
                            f"Kill this run, rebuild the binary from the arena's deployed crewrift "
                            f"commit (see the SKILL.md), and rerun — it will resume from disk.")
            except subprocess.CalledProcessError as exc:
                log(f"[stream] ! warehouse build failed ({exc}); retrying next tick")
        if not alive:
            in_warehouse = warehouse_episode_ids(args.out)
            remaining = [d for d in find_episode_dirs(ep_dir) if episode_id_of(d) not in in_warehouse]
            if not remaining:
                break
        time.sleep(args.interval)

    watcher_rcs = {x: p.returncode for x, p in procs.items()}
    if (args.out / "manifest.json").exists():
        summarize(args.out)
        manifest = json.loads((args.out / "manifest.json").read_text())
        log(f"[stream] done: {manifest.get('episodes_ok', 0)} episodes in warehouse, "
            f"{manifest.get('episodes_failed', 0)} failed extraction; "
            f"{len(find_episode_dirs(ep_dir))} fetched; watcher exits: {watcher_rcs}")
    else:
        log(f"[stream] done with EMPTY warehouse (no complete episodes fetched); "
            f"watcher exits: {watcher_rcs}")
    return 1 if any(rc for rc in watcher_rcs.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Static sanity check**

Run: `uv run python crewrift_lab/.claude/skills/crewrift-event-warehouse/scripts/stream_eval.py --help`
Expected: usage text with all flags, exit 0 (this also proves the `import build_warehouse` sibling import works under `uv run`).

- [ ] **Step 3: Commit**

```bash
git add crewrift_lab/.claude/skills/crewrift-event-warehouse/scripts/stream_eval.py
git commit -m "crewrift: stream_eval.py — overlapped xreq->artifacts->warehouse pipeline

One background process: per-xreq fetch --watch subprocesses stream episode
artifacts to disk as episodes complete, while a build loop folds them into
the warehouse in incremental batches (10 eps / 120s). Early trace_warning
alarm after the first batch; crash-safe resume from disk state."
```

---

### Task 4: Documentation — make streaming the default flow

**Files:**
- Modify: `.claude/skills/coworld-experience-requests/SKILL.md` (step 4)
- Modify: `.claude/skills/coworld-episode-artifacts/SKILL.md` (workflow + notes)
- Modify: `crewrift_lab/.claude/skills/crewrift-event-warehouse/SKILL.md` (build section)
- Modify: `crewrift_lab/tools/event-warehouse/crewrift-event-warehouse/README.md` (incremental builds)
- Modify: `AGENTS.md` (loop step 1)

**Interfaces:** none (docs only). Wording below is the required content; adjust surrounding prose minimally to fit.

- [ ] **Step 1: `coworld-experience-requests/SKILL.md`** — replace the "## Step 4 — monitor, then pull & analyze" section body with a streaming-first version:

```markdown
## Step 4 — stream, don't wait (the default)

"Created" ≠ "done" — but **do not wait for the xreq to drain before starting
the next stage.** Immediately after `create` returns the `xreq_…`, launch the
streaming pipeline **in the background** and let all stages overlap:

- **Crewrift deep-dig (warehouse wanted — the common case):** hand the fresh
  `xreq_…` id(s) to the `crewrift-event-warehouse` skill's `stream_eval.py`
  (see that SKILL.md). It watches the request, pulls each episode's artifacts
  as it completes, and folds them into the event warehouse in incremental
  batches — the warehouse is ready (or nearly) the moment the last episode ends.
- **Artifacts only:** `fetch_artifacts.py --xreq xreq_… --watch` (the
  `coworld-episode-artifacts` skill) streams the downloads the same way.

Both are crash-safe: rerun the same command and it resumes from disk.

For a quick status glance (or several requests at once), the old serial tools
remain: `uv run python "$S" monitor xreq_…` polls one request;
`scripts/xp_dashboard.py xreq_… [...]` serves the browser dashboard
(completion/ETA, win-rate leaderboard, heatmap; ops-filtered). Serial
monitor → fetch → build is the **fallback**, not the default.

When everything is terminal, compute the stats the question needs,
**decomposed by role and opponent**.
```

- [ ] **Step 2: `coworld-episode-artifacts/SKILL.md`** — in the "## Workflow" section step 2's command block, add after the `--xreq` line:

```markdown
   # …or STREAM them while the experience request is still running (exits when drained):
   uv run python "$F" --xreq xreq_... --watch --out /tmp/xreq_eps
```

and add to "## Notes":

```markdown
- **`--watch`** (with `--xreq` only) polls the request and downloads each
  episode as it turns terminal instead of requiring the batch to be done —
  the streaming half of the default eval flow (see
  `coworld-experience-requests` step 4). Resume-safe: completeness is judged
  from disk, so a killed watch just picks up where it left off;
  `watch_state.json` bounds retries (3) for episodes whose artifacts error.
```

- [ ] **Step 3: `crewrift-event-warehouse/SKILL.md`** — in "## Build it", add after the existing command block:

```markdown
**Streaming (the default for fresh experience requests):** don't wait for the
xreq to finish — `stream_eval.py` overlaps fetch + build, so the warehouse is
ready as the last episode ends:

```bash
S=crewrift_lab/.claude/skills/crewrift-event-warehouse/scripts/stream_eval.py
uv run python "$S" --xreq xreq_A [--xreq xreq_B] --out /tmp/wh --expand-replay /tmp/expand-<commit>
# episodes land in /tmp/wh_episodes/; the warehouse builds incrementally into /tmp/wh
# batches: every 10 new episodes or 120s (--batch-n / --batch-secs); crash-safe rerun
```

Builds are **incremental**: episodes already in the manifest as `ok` are never
re-expanded, so repeated builds over a growing episode dir only pay for the
new ones (this also makes re-running `build_warehouse.py` after a partial
failure cheap). A version-skewed `--expand-replay` is warned after the FIRST
batch, minutes in.
```

- [ ] **Step 4: vendored README** — in `crewrift-event-warehouse/README.md`, add a short "Incremental builds" subsection under the build docs stating: repeated `build` runs against the same `--out` skip episodes already recorded `ok` (no replay re-expansion), re-attempt `failed`/`trace_warning` ones (their old shards are deleted first), and merge `manifest.json` + `episode_players.parquet` with the prior build; `episodes_cached` in the manifest counts this run's cache hits; delete the `--out` dir for a from-scratch rebuild.

- [ ] **Step 5: `AGENTS.md`** — in loop step 1 (Evaluate), after the sentence about experience requests being the primary instrument, add:

```markdown
   Run evals **streaming by default**: right after creating an experience
   request, launch the streaming pipeline in the background (the
   `coworld-experience-requests` skill, step 4) so artifact download and
   analysis prep overlap the still-running episodes instead of waiting for
   the batch to drain.
```

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/coworld-experience-requests/SKILL.md \
        .claude/skills/coworld-episode-artifacts/SKILL.md \
        crewrift_lab/.claude/skills/crewrift-event-warehouse/SKILL.md \
        crewrift_lab/tools/event-warehouse/crewrift-event-warehouse/README.md \
        AGENTS.md
git commit -m "docs: streaming xreq->artifacts->warehouse is the default eval flow

SKILL.md updates route agents to stream_eval.py / fetch --watch right after
xreq create; serial monitor->fetch->build demoted to fallback."
```

---

### Task 5: Live end-to-end validation

**Files:** none (validation). Requires `softmax login` auth, Docker not required.

**Interfaces:** consumes everything above. Success criteria are the spec's: overlap observed, reconciliation correct, resume works.

- [ ] **Step 1: Prepare a version-matched `expand_replay` binary**

Follow the existing recipe in `crewrift-event-warehouse/SKILL.md` ("the one hard part"): find the arena's deployed crewrift version via `uv run coworld episodes --json` on a recent episode (`coworld_version`), and build/reuse `/tmp/expand-<commit>`. A binary from a recent prior session may already exist under `/tmp` — verify it exits 0 with `trace_complete:true` on a recent replay before trusting it.

- [ ] **Step 2: Create a small live xreq**

Use the `coworld-experience-requests` skill's script with a self-play crash-test shape (~8 episodes, crewborg in all seats — cheap, no opponent-field concerns). Compose `/tmp/stream_test_req.json` per that skill's `references/api.md`, then:

```bash
S=.claude/skills/coworld-experience-requests/scripts/experience_request.py
uv run python "$S" create /tmp/stream_test_req.json --check-schema
uv run python "$S" create /tmp/stream_test_req.json     # note the xreq_… id
```

- [ ] **Step 3: Launch the streaming pipeline immediately (background)**

```bash
uv run python crewrift_lab/.claude/skills/crewrift-event-warehouse/scripts/stream_eval.py \
  --xreq xreq_<id> --out /tmp/stream_test_wh --expand-replay /tmp/expand-<commit> \
  --batch-n 3 --batch-secs 60 2>&1 | tee /tmp/stream_test.log
```

(`--batch-n 3` so a small run exercises multiple batches.)

- [ ] **Step 4: Verify overlap**

While the run is live, confirm from the log that episode dirs appear in `/tmp/stream_test_wh_episodes/` **and** at least one `[stream] building warehouse` line fires **before** the watcher logs `drained=True` — that is the overlap the whole feature exists for. Record the evidence (log excerpt).

- [ ] **Step 5: Verify resume**

Kill the process mid-run (after the first build), rerun the identical command; confirm it resumes: already-fetched episodes are skipped by the watcher, the next build reports a nonzero `episodes_cached`, and the run completes.

- [ ] **Step 6: Verify the final state**

```bash
cat /tmp/stream_test_wh/manifest.json | uv run python -c "import json,sys; m=json.load(sys.stdin); print({k:m[k] for k in ('episodes_total','episodes_ok','episodes_cached','episodes_failed')})"
```
Expected: `episodes_ok` == number of episodes that produced artifacts; zero `trace_warning` (else the binary from Step 1 is wrong); the count reconciles with the watcher's final `fetched N / total` line. Spot-check the warehouse answers a query (e.g. the `entered_room` count per policy via duckdb, per the SKILL.md recipes).

- [ ] **Step 7: Record and commit any fixes**

Fix anything the live run surfaces (commit each fix with a message naming the observed failure). Note the validated xreq id and results in `crewrift_lab/WORKING_CONTEXT.md` per living-docs discipline.
