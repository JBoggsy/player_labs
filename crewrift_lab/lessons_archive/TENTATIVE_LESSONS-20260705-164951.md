# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-02 17:05. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`crewrift_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Crewrift-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### "Tournament is broken" = dispatch OK, artifact routes still 403 — not a dispatch outage
Evidence: fired 2x100-ep xreq (v93 vs pinned top-7 Crewrift Prime field, explicit
policy_refs, natural roles) as a tournament substitute. Episode DISPATCH works fine
(submitted/running counts climb normally, started ~2min after create). But
`fetch_artifacts.py --watch` immediately fails every episode: "results artifact
unavailable / replay unavailable / no policy logs listed" — the same `/jobs/*`
403 "not a softmax team member" blocker already logged in WORKING_CONTEXT.md
(since 2026-07-02 ~22:20Z) is still live ~1.5-2.5h later. So "episodes aren't
running" as reported likely means "results/replays never surface" (which looks
identical to broken from the league leaderboard's perspective, since it also reads
those routes) rather than the k8s dispatch path being down.
Status: xreq_742da7f5-9107-450d-8f63-f7a73ed4af59 + xreq_7d1ccc1f-ba16-4fe6-819a-0ece28d76562
(100 ep each, v93 vs top-7) running; dashboard on :8811; fetchers backgrounded and
crash-safe — will backfill once /jobs/* unblocks. Re-login/relogin still untried-successfully
per WORKING_CONTEXT; may need platform-side escalation.

### FIXED: /jobs/* 403 was metta PR #17028 (opt-in elevation), not an outage
Evidence: PR #17028 ("feat(auth): opt-in elevation model") landed on origin/main —
Softmax team members are now treated as EXTERNAL by default; TEAM_AUTH-gated routes
(incl. per-episode job artifacts: results/replay/policy-logs for another player's
policy) need `X-Use-Elevated-Privileges: true`, sent via `coworld --elevated` (or
`softmax status --elevated`; no env-var form, flag-per-invocation only, refused for
ply_* tokens). Our local coworld pin was 0.1.27 (stale — no `--elevated` support);
bumped to 0.1.28 via `uv lock --upgrade-package coworld && uv sync`. Verified fix:
`fetch_artifacts.py --elevated` pulled results+replay+8 policy-logs cleanly for
episodes that 403'd moments earlier without the flag.
Action taken: added `--elevated` to fetch_artifacts.py (Client header), xp_dashboard.py,
and passthrough in crewrift-event-warehouse's build_warehouse.py/stream_eval.py.
NOT yet added: crewrift-survey/scripts/survey.py's replay-session-mint call (different
route, no evidence yet it needs elevation — don't add speculatively).
Status: OPEN — none of these scripts default `--elevated` to on; every future
invocation needs the flag explicitly until/unless we decide non-team-member-log
access is desired by default (the PR's whole point was to make that an explicit choice).

### `random`/`top_n` roster-fill query still 500s — NOT flaky, 3/3 reproduced
Evidence: fired a true tournament-style request (crewborg:v93 + 7x `{"random": true}`
seats, no game_config_overrides) against Crewrift Prime Competition division — 500
"canceling statement due to statement timeout" on the `eligible_champions` CTE
(joins policy_versions -> league_policy_memberships -> ... -> episode_policy_metrics,
computing mean_reward per champion since a ~1-month floor). Retried 3x back-to-back,
identical failure every time — this is a deterministic query-plan/timeout problem, not
transient contention. Confirms `WORKING_CONTEXT.md`'s existing "pin explicit
policy_refs" mitigation is still necessary, but note that mitigation is NOT equivalent
to "tournament-style" (random field) — it's a different, narrower question (see the
new tournament-style definition added to `coworld-experience-requests/SKILL.md`).
The division-leaderboard endpoint used by `experience_request.py resolve --division
--top N` is unaffected (different, cheap query) — only the xp-request roster-fill
path is broken. Worth reporting to platform: this may be a big part of why the
league/tournament itself looked "broken" (round dispatch/rostering may hit the same
query for the commissioner's own matchmaking).
