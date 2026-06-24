# Crewrift tentative lessons — session buffer

**Session started:** 2026-06-24 16:19. This is THIS SESSION's lesson buffer. Write candidate
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

### Build prediction modules replay-driven with a UI + accuracy harness, not in live games (2026-06-24)
The path-prediction module was built/tuned entirely off replays via an event warehouse (per-tick player_state = ground truth; player_visible_interval = what crewborg actually saw). Two tools made it legible: a live browser UI to watch predictions evolve, and an eval that scores predictions at every visible→obscured transition (the moment prediction matters) with destination-room match rate + per-instance overlay PNGs (actual orange vs predicted blue paths). Key signal to report for any predictor: match rate BY CONFIDENCE BUCKET (calibration) — first draft was 43% overall but 86% when pred_prob∈[0.4,0.7], proving the module is informative even when raw accuracy is mediocre. Tools live in crewborg/tools/ (documented in tools/README.md). Faster iteration loop than building→uploading→eval'ing a whole player.

### expand_replay version coupling bites the warehouse too — arena 0.1.54 ⇒ commit 42fed21 (2026-06-24)
The event-warehouse `CREWRIFT_EXPAND_REPLAY` helper must be built from the EXACT crewrift commit the arena ran or replays hash-fail → sparse events (no kills/bodies/following/player_state). Check `manifest.json` trace_warning counts first. `/tmp/expand-42fed21` + checkout `~/coding/coworlds/coworld-crewrift`@42fed21 are set up; built warehouses `/tmp/xp_imp_warehouse` (450 XP imposter eps, 0% hash-fail) + `/tmp/crewrift_warehouse` (2 league rounds). Adapter `/tmp/make_wh_input.py` turns fetch_artifacts dirs → warehouse report_request.json.
