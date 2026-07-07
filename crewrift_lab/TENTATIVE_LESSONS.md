# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-06 09:11. This is THIS SESSION's lesson buffer. Write candidate
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

### A SessionStart rotation hook that reads a stale branch can silently drop lessons added upstream after the hook's base commit
Evidence: today's `git pull` conflicted because the SessionStart hook had already rotated
`TENTATIVE_LESSONS.md` (archiving whatever was on the local, stale `1e2abfc` base) before the pull
ran. Origin had appended 8 real lessons to the live buffer in commits after that base — those
lessons existed nowhere in the local archive and would have been silently lost by taking either
merge side naively. Recovered by hand-diffing the conflict's "upstream" content out and appending
it to the archive before accepting the reset buffer. General risk: any hook that snapshots/rotates
a file on session start is unsafe to trust blindly when the branch is behind origin — pull (or at
least fetch+compare) before rotating, or the rotation should diff against origin's tip, not the
stale local `HEAD`, before archiving.
Status: recovered by hand this time; the hook itself is unchanged and will do this again on the
next stale-branch + concurrent-edit collision.

### `gh pr view <n> --json mergedAt/state` can read `null`/`CLOSED` for a PR that genuinely merged, if the org uses the Graphite merge queue
Evidence: PR #17117 (`fix(app_backend): add missing pv_internal_id index on episode_policy_metrics`)
showed `{"state":"CLOSED","mergedAt":null}` via `gh pr view --json state,mergedAt`, which reads as
"abandoned." It actually merged — Graphite's merge queue closes the original PR and lands the
commit via a synthetic draft PR (here, #17262), so GitHub's native merge fields never populate on
the PR the author actually opened. The real signal is the "Merge activity" bot comment
(`gh pr view <n> --json comments`) or checking `git log origin/main --grep "<PR title>"` for the
commit directly. Don't conclude "not merged" from state/mergedAt alone in a Graphite repo.

### A slow/timing-out query can have more than one independent unindexed predicate — fixing one doesn't mean the query is fixed
Evidence: `load_ranked_champion_policy_version_ids` (metta `app_backend/v2/experience_requests.py`,
backs Coworld's `random`/`top_n` xp-request roster fill) had TWO separate unindexed JSONB filters
in the same statement: `episode_policy_metrics(pv_internal_id, metric_name)` (fixed by PR #17117,
merged 2026-07-06) and `job_requests.job ->> 'coworld_id'` (still unindexed — audited every
migration on the table, confirmed no expression index exists for that column). The query still
timed out identically after #17117 merged. Root-causing a timeout by reading the query plan/SQL
text for ALL its filters — not stopping at the first plausible unindexed one — is what caught this;
a single fix landing is not evidence the symptom is resolved until re-reproduced.
