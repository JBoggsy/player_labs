# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-01 11:34. This is THIS SESSION's lesson buffer. Write candidate
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
### Uploads from parallel sessions leave version_log.md gaps — check before submitting
Evidence: Asked to submit v80 as champion; `versions.py` confirmed v76–v80 uploaded, but version_log.md's newest entry was v75 — the "big imposter fixes" behind v80 have no recorded commits/config in this repo. Submitted anyway (explicit go-ahead + James had tested it), but the submission row I wrote had to say "reconcile from the other session". Lesson: sessions that upload versions must write the log entry in the same breath; a submitting session should check the log covers the version being submitted and flag the gap.

### Killing "all XP dashboards" = pkill -f xp_dashboard.py, but port reuse needs a lsof check first
Evidence: `pkill -f xp_dashboard.py` cleanly killed all six dashboard servers, but restarting on port 8810 failed (Address already in use) — that port was held by an unrelated `path_prediction_ui.py`, and 8809/8812 by other lab viz servers. `lsof -ti tcp:<port>` + inspecting the command line distinguished XP dashboards from other tools sharing the 88xx range before choosing 8814.

### Submission → champion can be near-instant; the qualification monitor may race the placement
Evidence: v80's `monitor --watch` first poll showed the new sub as `pending` with no membership, then the watcher exited on an OLD membership's `competing` status; a direct memberships query minutes later showed v80 already `competing`/`substatus=champion`. The monitor keys on the policy name, so with several placed memberships for the same policy its verdict can come from the wrong one — verify the NEW `lpm_…` id explicitly.
