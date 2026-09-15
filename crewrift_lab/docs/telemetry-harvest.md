# League telemetry harvest — accumulating crewborg's policy artifacts locally

**Tool:** [`../tools/harvest_artifacts.py`](../tools/harvest_artifacts.py) ·
**Output:** `crewrift_lab/telemetry_harvest/` (gitignored) ·
The harvest maintains a local analysis corpus.

## What it does

Every run: finds crewborg's current Crewrift Prime entrant version (from recent rounds'
`entrant_policy_version_ids`), lists its newest N league episodes (`ereq_…` rows), and for
each **completed** episode not already on disk downloads `results.json` + all readable
`policy_artifact_*.zip` telemetry bundles (via the lab's
`.claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py`, `--no-replay --no-logs`). Idempotent (skips episodes whose dir already has `artifacts/`),
lockfile-guarded (overlapping runs no-op), and appends one summary line per run to
`telemetry_harvest/harvest.log`.

```
uv run python crewrift_lab/tools/harvest_artifacts.py            # newest 60 episodes (~1 h)
uv run python crewrift_lab/tools/harvest_artifacts.py -n 300     # deeper catch-up
```

Layout (same shape the event-warehouse builder consumes):

```
crewrift_lab/telemetry_harvest/
  harvest.log                          # one line per run
  episodes/
    <episode-request-id>/
      episode.json                     # the ereq row verbatim
      results.json                     # scores/metrics
      artifacts/policy_artifact_{i}.zip  # per-slot telemetry bundles
```

## Running it on a timer

Do **not** rely on an agent to run this; install a crontab (runs finish in seconds once
caught up; the lockfile makes overlap safe):

```
*/10 * * * * cd /Users/jamesboggs/coding/personal_labs/personal_labs_crewrift && /Users/jamesboggs/.local/bin/uv run python crewrift_lab/tools/harvest_artifacts.py >> crewrift_lab/telemetry_harvest/cron.log 2>&1
```

Prereq: `uv run softmax status` must say Authenticated (tokens come from `softmax login`).
If auth expires the run exits 1 with a clear message in `cron.log`.

## Evidence coverage

Download through normal participant access. Missing artifacts can reflect access,
upload failure, incomplete episodes or game support; absence does not establish a
retention limit. Record coverage and failures rather than inferring a storage SLA.

## Where the data feeds

The zips are crewborg's trace telemetry — the input the
[crewrift-event-warehouse](../.claude/skills/crewrift-event-warehouse/) builds from, and
what `crewrift-ab` / `crewrift-experiment` re-analyse. A steadily-growing
`telemetry_harvest/episodes/` means cross-round questions ("how did behaviour shift after
vNNN?") do not depend on having run a fetch at the right moment.

One standing consumer: `tools/harvest_liars.py` scans the corpus for the Honor Society's
`domain.honor_liar` events and (with `--write`) maintains the vendored cross-game distrust
list `crewrift/crewborg/data/honor_distrust.json` (see the
[honor-society design doc](../crewrift/crewborg/docs/designs/honor-society.md) §Reputation).
Run it after (or on the same timer as) `harvest_artifacts.py`.
