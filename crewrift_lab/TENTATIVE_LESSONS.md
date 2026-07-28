# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-28 10:15. This is THIS SESSION's lesson buffer. Write candidate
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

## belief-audit build (2026-07-28)

- **`build_warehouse.py --expand-replay` must be an ABSOLUTE path** — it subprocess-runs
  `crewrift-event-warehouse build` with `cwd=` the vendored package dir, so a repo-relative
  binary path fails per-episode with FileNotFoundError while the manifest still says
  "✓ no trace_warning". Failure mode looks like "0 events, 8 failed", not an error. (The
  SKILL.md examples use /tmp paths, which is why this never bit before.)
- **`--policy crewborg -n N` league episodes have NO policy artifacts** — the fetcher says
  "no v2 route for league episodes (only episode requests)". Belief-audit (any artifact-
  telemetry consumer) needs xreq/ereq episodes, not league rounds. Fetch by `--xreq`.
- **The xreq listing route is `GET <api>/observatory/v2/experience-requests` → `{entries: […]}`**;
  short ids from notes (xreq_61f440b3) must be resolved to full UUIDs before `--xreq` fetch
  (the episodes sub-route 422s on a short id).
- **`imposter_unranked` needs an alive filter** — a dead imposter legitimately drops out of
  the suspicion ranking; comparing rankings to the full-roster imposter set produced 4 false
  divergences in an 8-seat smoke (all were post-death meetings). Filter live_imposters by
  `truth_death_ts > snapshot_ts`.
- **Real-data smoke check found real signal immediately**: crewborg's belief notices deaths
  via census 300-650 ticks late (`death_belief_lag`, source=census), and `ranking_top_crew`
  at p≈0.5-0.53 barely over the current 0.5 vote bar — both plausible hypothesis fuel.
