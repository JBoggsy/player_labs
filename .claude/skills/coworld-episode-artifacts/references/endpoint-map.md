# Episode artifact endpoints

Routes checked against [current OpenAPI](https://softmax.com/api/observatory/openapi.json), 2026-09-14. Base: the authenticated API server's `/observatory` gateway.

| Purpose | Route |
| --- | --- |
| Request child rows | `/v2/experience-requests/{id}/episodes` |
| Policy versions | `/stats/policy-versions?name_exact=…` (cursor pages, optional exact `version`) |
| Recorded policy episodes | `/v2/policy-versions/{id}/episodes` (cursor pages); detail `/episodes/{id}` |
| Explicit episode request | `/v2/episode-requests/{id}` |
| Legacy job to request | `/v2/episode-requests/by-job/{job_id}` |
| Round episodes | `/v2/rounds/{id}/episodes` (cursor pages) |
| Division rounds | `/v2/rounds?division_id=…` (cursor pages) |
| Results/replay/game logs/error | `/v2/episode-requests/{id}/artifacts/{type}` |
| Accessible seat diagnostics listing | `/v2/episode-requests/{id}/policy-artifacts` |
| Seat log | `/v2/episode-requests/{id}/{policy_version_id}/policy-logs/{position}` |
| Seat ZIP | `/v2/episode-requests/{id}/{policy_version_id}/policy-artifact/{position}` |

Artifact types include `results`, `replay`, `logs`, `error-info`, `spec`, `player-status`, `game-config`. The old `/jobs/...` and bare `/v2/episode-requests` listing are absent from the public schema; absence alone does not establish removal. The lab uses the verified v2 routes. Its pool-discovery mode is unsupported: choose a round, division or experience request. A `replay_url` is a watch link and must not be downloaded as replay bytes.

## Coverage and resume

`episode.json` retains the discovery source row. Legacy jobs also save the resolved `episode_request.json`. Results and replay must exist when requested. `policy_logs_checked.json` and `policy_artifacts_checked.json` record the successful accessible listing; each advertised available file must exist. A partial ZIP/log failure does not mark that category complete. Empty accessible listings are valid but do not imply all opponents are visible. Combined game logs and error-info are optional diagnostics.

Watch mode checks that all child episodes are completed/failed/cancelled; the parent status alone is insufficient. Exhausted downloads return a nonzero exit status and remain visible in `index.json`; terminal is not equivalent to complete evidence. One-shot downloads also return nonzero when requested artifacts are incomplete. Older directories without the log coverage marker are checked again.

Use normal participant access. A 403 is a coverage limitation, never a reason to fetch private opponent intelligence with elevated privileges.

Validation: route/schema inspection, local regression tests, and a subsequent authenticated read-only download of an owned evaluation's results, replay, seat log and ZIP (2026-09-14). This sample does not establish universal artifact availability, viewer compatibility or a retention SLA. See the [fact-check evidence](../../../../docs/reports/platform-fact-check-2026-09-14.md).

## Attempts, bundles and optional evidence

Use `/v2/policy-versions/{id}/episode-requests` to find attempts, including ones without a recorded episode. The helper's policy discovery currently uses recorded `/episodes`; do not treat it as a failure-complete denominator. XP/round request rows retain failed attempts.

`/v2/episode-requests/{id}/bundle` can package selected evidence; `include` supports `results,replay,events,error_info,game_logs,player_logs,player_artifact`. This is a schema/source-verified optional alternative, not exercised by the current downloader. Reporter output/trace routes are separate from raw game/player files.

Replays are optional. If a game emits none, use `--no-replay` deliberately and report that limitation. The helper otherwise requires requested results/replay files and will mark terminal failures without them incomplete, even when that absence is expected. Never infer a storage TTL from missing artifacts.
