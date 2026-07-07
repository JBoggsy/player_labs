# Crewrift working context

**What this is.** The live, high-signal state of *what we're working on right now* in
the Crewrift lab — the minimal set of cross-session facts worth carrying into the next
session. Read it on startup to resume; **update it as you learn** (keep it tight —
prune anything no longer load-bearing). **Clear and reseed it when we pivot to a whole
new direction**, keeping only the new objective.

This is *not* a log or archive: finished work lives in git history / the
[version log](crewrift/crewborg/version_log.md); durable disciplines live in
[`best_practices.md`](best_practices.md); durable prefs in
[`user_preferences.md`](user_preferences.md). This file is the one-screen "where are we."

> A recorded objective below = onboarding done; resume the loop ([`AGENTS.md`](AGENTS.md)).

---

## 🎯 CURRENT STATE (reseeded 2026-07-06 session end)

**Champion: v100, QUALIFIED + COMPETING + CHAMPION** (`lpm_e11fdaa6…`, clean qualify).
v100 = v99 + two changes, both direct responses to James watching v99 replays:

- **WATCH simplified to one case.** Removed the kill-cooldown-gated camouflage one-shot
  and the single/multiple-crew split; WATCH now always latches onto the best-view **task
  station** (never hovers mid-room) whenever crew are visible. Deleted the now-dead
  `visionbake.py` subsystem entirely (module, `tools/vision_bake.py`, the precomputed
  `map/croatoan_visionbake.pkl.gz` asset) rather than keeping it as a second path.
- **Recon retimed.** Entry trigger changed from a fixed `RECON_WINDOW_TICKS` to computed
  timing (`travel_ticks`: nav-route-aware distance / `AGENT_SPEED_PX`), firing exactly
  when the remaining kill cooldown matches real travel time to the target — start moving
  only once "just in time," not earlier. Target selection changed from most-recently-seen
  to `most_isolated_recon_candidate` (farthest from every other fresh sighting).

Both land on top of the same-day **vision model correction**: traced Crewrift's real
per-player camera (128×128 world-px window + wall occlusion, not a circular radius —
see `docs/designs/vision-model.md`) and fixed two places that approximated it with the
wrong number — the kill-witness gate (now an exact live visible-crew count, since vision
is symmetric) and vantage scoring (`VANTAGE_RANGE` 360→91, the true diagonal reach).

**Witness gate reworked the same day:** replaced the old `BASE_ISOLATION_RADIUS`/
`WITNESS_WINDOW_TICKS` heuristic with an urgency ramp — `witness_tolerance()` allows only
1 witness at zero urgency, ramping to 6 (always-strike ceiling in this 6-crew format) at
full urgency. Always allows a kill with exactly one witness, no hard cutover.

**Version history this session:** v97 (upload mistake — nonexistent env var, no
Bedrock model pin — caught, retired, documented in `version_log.md` as a mistake) → v98
(correct recipe, churned twice for non-quality reasons — account slot eviction, unclear
supersession) → v99 (re-upload of v98's code, clean qualify, champion) → v100 (above).
624 tests green pre-upload on v100; no pre-ship A/B — per James's relaxed-submission call
(see `user_preferences.md` / `[[speed-first-iteration]]` memory: per-version leaderboard
tracking means a bad submit has no lasting cost).

**Also shipped this session (not crewborg gameplay):**
- `ranking_analysis/voting_metrics.py` + `voting_report_gen.py` — per-policy vote rate,
  chat rate, vote accuracy, ejection effectiveness (conversion vs friendly-fire), crew win
  rate, from the event warehouse. See `ranking_analysis/README.md`'s new section.
- `docs/designs/sprite-bridge-migration.md` — plan (not yet implemented) to adopt
  coworld-tools' new `SpriteV1` bridge (`sprite_bridge.py`) instead of our vendored wire
  protocol handling, while keeping crewborg's own reconnect loop (the SDK's
  `message_bridge.py` has no retry — would regress hard-won reliability fixes).

## ▶ IN PROGRESS: v100 500-episode tournament-style field eval — BLOCKED on platform bug (below)

Composed 5×100-episode tournament-style xreqs (`crewborg:v100` in one seat, every other
seat `{"random": true}`, natural roles) — request bodies at `/tmp/v100_tourney_reqs/`.
**Every creation attempt 500s** on the roster-fill query (see blocker below). A background
retry script was running (`create_v100_xreqs.sh`, 45s cadence) — **killed at session end**
per James, since the failure is structural, not transient; don't resume the naive retry
loop without first checking whether the fix below has landed AND deployed.

**To resume:** re-run `uv run python .claude/skills/coworld-experience-requests/scripts/experience_request.py create /tmp/v100_tourney_reqs/req_0N.json` for N in 1..5 once the platform fix (below) is confirmed deployed; stream via `crewrift-event-warehouse`'s `stream_eval.py`.

## ⛔ PLATFORM BLOCKER (root-caused 2026-07-06, still open)

**xp-request roster `random`/`top_n` seat-fill 500s** on `POST /v2/experience-requests` —
`load_ranked_champion_policy_version_ids()` in metta's
`app_backend/src/metta/app_backend/v2/experience_requests.py:277-364` hits
`psycopg.errors.QueryCanceled: canceling statement due to statement timeout`. This is the
**same symptom** noted 2026-07-03, but now root-caused to **two independent unindexed
predicates in the same query**:

1. `episode_policy_metrics` join on `(pv_internal_id, metric_name)` — **FIXED**, PR #17117
   (`fix(app_backend): add missing pv_internal_id index on episode_policy_metrics`) merged
   to metta `main` today via Graphite queue (commit `10874ebb47`). **Unconfirmed whether
   the migration has actually been *applied* to the production DB** — a merge to `main`
   doesn't run `alembic upgrade` by itself.
2. `job_requests.job ->> 'coworld_id'` — **NOT fixed, no PR yet.** Audited every index ever
   created on `job_requests` across all alembic migrations: none touch the `job` JSONB
   column (only `result->>'episode_id'` has an expression index, a different column/PR
   `a1b2c3d4e5f7`). Reproduced this exact predicate still timing out live, today, in this
   session — including after #17117 merged, so it's very likely the remaining/sole cause
   now. Follow-up issue drafted (full repro SQL + proposed migration) at
   `/private/tmp/claude-501/-Users-jamesboggs-coding-personal-labs/9ba09582-d86d-4b7d-8b42-62a24349a8f9/scratchpad/job_requests_coworld_id_index_issue.md`
   — hand this to an agent on a **separate** metta clone/worktree (never `~/coding/metta`
   directly — read-only hard rule) to open as PR #2.

Gotcha for next time: `gh pr view <n> --json mergedAt` can show `null` even for a PR that
truly merged, if the org uses the **Graphite merge queue** — it closes the original PR and
merges via a synthetic draft PR instead. Check `gh pr view <n> --json comments` for the
Graphite "Merge activity" bot comment, or `git log origin/main --grep "<PR title>"`, not
just `state`/`mergedAt`.

## Load-bearing infra facts

- Player SDK from Metta-AI/coworld-tools tarball (issue #13); coworld CLI 0.1.28 pinned.
- Expander binary must match the exact deployed Crewrift commit (`trace_warning` = version
  skew or genuine replay non-determinism — check which before trusting a warehouse build).
- fetch_artifacts/stream_eval/build_warehouse/xp_dashboard all need `--elevated` when
  pulling another player's (opponent) episode artifacts (metta PR #17028 — team members are
  external-by-default now).
- Bedrock LLM: sidecar-endpoint gating (`USE_BEDROCK` alone doesn't gate it); meeting LLM
  toggle is `CREWBORG_LLM_MEETINGS=1`, upload with `--use-bedrock --bedrock-model <id>`.
