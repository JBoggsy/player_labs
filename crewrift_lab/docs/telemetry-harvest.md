# League telemetry harvest — accumulating crewborg's policy artifacts locally

**Tool:** [`../tools/harvest_artifacts.py`](../tools/harvest_artifacts.py) ·
**Output:** `crewrift_lab/telemetry_harvest/` (gitignored) ·
**Status:** retention scare resolved 2026-07-21 — artifacts are durable; the harvest exists
to keep a continuous local corpus, not to race deletion.

## What it does

Every run: finds crewborg's current Crewrift Prime entrant version (from recent rounds'
`entrant_policy_version_ids`), lists its newest N league episodes (`ereq_…` rows), and for
each **completed** episode not already on disk downloads `results.json` + all readable
`policy_artifact_*.zip` telemetry bundles (via the lab's
`.claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py`, `--elevated
--no-replay --no-logs`). Idempotent (skips episodes whose dir already has `artifacts/`),
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
    20260721T232433_ereq_eca6ce19-87/
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

## The retention story (why this exists, and what turned out to be true)

**The 2026-07-01 scare:** with all-telemetry uploads standard
(`CREWBORG_TRACE_GROUPS=all`), a 21:10 fetch of v82's league episodes found policy
artifacts only in the newest round's episodes (6/100); a v80 pull showed the same
(17/196, all newest-round). It looked like artifacts were deleted after ~one round
(~10–15 min).

**Re-measured 2026-07-21:** artifacts are **durable, not ephemeral**. Probing the v2
routes (`GET /v2/episode-requests/{ereq}/policy-artifacts` +
`…/{pvid}/policy-artifact/{idx}`) across episode ages: 1 min → 3.7 h all HTTP 200, and the
*very episodes from the July-1 observation* (v80/v82, ~20 days old) still list
`has_artifact: true` and download fine. Platform-side (metta, read-only):

- Storage is plain S3 (`observatory-private`, `EVAL_S3_BUCKET` in
  `devops/app-manifests/values.yaml:30`), keys
  `jobs/{job_id}/policy_artifact_{idx}.zip`
  (`app_backend/src/metta/app_backend/job_runner/job_artifacts.py:98`).
- **No TTL, no cleanup job**: the only S3 lifecycle-expiry in the observatory terraform is
  on the *secrets* bucket (`devops/tf/observatory/policy-secrets.tf:52`); the only
  artifact-adjacent delete in the backend is the per-job secrets bundle
  (`job_runner/event_processor.py:791`). Nothing deletes `jobs/{id}/policy_artifact_*`.

**What the July-1 observation was:** a *read-path* failure, not deletion — proven by the
fact that the very artifacts that looked gone are still downloadable today (nothing with a
~15-min TTL could return them 20 days later). The exact mechanism is no longer
reconstructable, but the observation sat squarely in a window of API/auth churn on the
artifact read path: the fetch tooling then used the v1 `GET /jobs/{job_id}/policy-artifact`
routes (`TEAM_AUTH`-gated, `routes/job_routes.py` @ metta 9d788e14ce), whose failures the
script swallowed into "no artifacts" (`get_text_or_none` → None on any 4xx); opt-in
elevation flipped team members to external-by-default 2026-07-02 (metta ee7a3e27c2,
#17028), the ownership-scoped v2 routes + manifest-403 fix landed 2026-07-08 (b548b013a4,
#17413), public-league artifact reads were aligned with list visibility 2026-07-09
(3c3fdb4f17, #17466), and the v1 routes were deleted outright 2026-07-10 (c4ddebd857,
#17603). **No platform-side fix is needed** — the current v2 routes + `--elevated` return
everything, weeks back.

Practical residual: per-slot artifact coverage is organically incomplete (typically 4–8 of
8 slots have `has_artifact` — some opponents don't upload artifacts, and a crashed pod
uploads nothing). That is upload-side, not retention.

## Where the data feeds

The zips are crewborg's trace telemetry — the input the
[crewrift-event-warehouse](../.claude/skills/crewrift-event-warehouse/) builds from, and
what `crewrift-ab` / `crewrift-experiment` re-analyse. A steadily-growing
`telemetry_harvest/episodes/` means cross-round questions ("how did behaviour shift after
vNNN?") no longer depend on having run a fetch at the right moment.
