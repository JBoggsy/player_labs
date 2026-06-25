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

### Vantage-watching (keep crew in sight) >2x'd imposter kills — watch from max-LOS point, not the door (2026-06-25)
James watched v40 replays: the imposter willingly walked OUT of sight of crew (stood at a task spot by the room entrance, didn't keep crewmates in view). Fix: WATCH now holds the in-room VANTAGE POINT with line-of-sight to the most crew (nav._segment_clear over walkability, recomputed as they move); GO_TO_ROOM enters to the room centre. Result vs Aaron/Andre: kills/g 0.60 (v40 door) → **1.50 (v41 vantage)**, imposter win 30%→45%(then 52% mid-run), 0-kill games 6/10→1/20. 1.50 k/g is now ABOVE the top imposters' ~1.05 vs this field. n=20 small but effect huge. LESSON: for an imposter, *staying in visual contact with crew* is the dominant lever — watching replays caught what metrics/unit-tests couldn't.

### Two ops gotchas (2026-06-25): debug trace must be BAKED as ENV (secret-env silently no-ops); arena moved 0.1.54→0.1.58
(1) `CREWBORG_TRACE=debug` via `--secret-env` did NOT enable debug (telemetry stayed lean, no decision_snapshot); bake it as an image `ENV` (thin `FROM ... + ENV`) like the vote-gate sweep. (2) The arena redeployed crewrift to **0.1.58** — the warehouse expander `/tmp/expand-42fed21` (0.1.54) now hash-fails on ALL fresh replays (warehouse near-crew diagnosis blocked until rebuilt from the 0.1.58 commit), AND the local coworld SDK can't validate the 0.1.58 game manifest (`infer_fixed_token_count` crash in run-episode BEFORE the player runs) — local Gate-1 must point `--manifest` at the cached 0.1.54 cow_50ee07cf for now. The cluster runs 0.1.58 fine, so hosted eval is unaffected.

### New imposter SEARCH mode = watch-a-room → follow-the-leaver (built 2026-06-24)
SEARCH is now the imposter's ALWAYS-ON seeking stance (PRETEND removed from the gate, registry, and as a file; cold-stored placeholder deleted). FSM: PICK_ROOM (random nearby task room) → GO_TO_ROOM → WATCH (idle at a task spot near the entrance until a crewmate leaves) → FOLLOW (chase the leaver; once occluded, steer to the PathPredictor's top route position = chase down the hallway) → loop. Never follows the teammate imposter. Gate change in rule_based `_select_imposter`: default is now `search` (no more pretend / SEARCH_LEAD_TICKS lead-window gate). Wired the path_prediction module in directly. 6 new search tests + 2 strategy-gate tests updated; 355 pass; Gate-1 PASS. NOT yet eval'd — next: upload + XP eval vs Aaron/Andre, check the warehouse "near crew" / isolation-opps / kills metrics actually move (that was the whole point — crewborg was near crew ~half as often as the top imposters).

### Build prediction modules replay-driven with a UI + accuracy harness, not in live games (2026-06-24)
The path-prediction module was built/tuned entirely off replays via an event warehouse (per-tick player_state = ground truth; player_visible_interval = what crewborg actually saw). Two tools made it legible: a live browser UI to watch predictions evolve, and an eval that scores predictions at every visible→obscured transition (the moment prediction matters) with destination-room match rate + per-instance overlay PNGs (actual orange vs predicted blue paths). Key signal to report for any predictor: match rate BY CONFIDENCE BUCKET (calibration) — first draft was 43% overall but 86% when pred_prob∈[0.4,0.7], proving the module is informative even when raw accuracy is mediocre. Tools live in crewborg/tools/ (documented in tools/README.md). Faster iteration loop than building→uploading→eval'ing a whole player.

### expand_replay version coupling bites the warehouse too — arena 0.1.54 ⇒ commit 42fed21 (2026-06-24)
The event-warehouse `CREWRIFT_EXPAND_REPLAY` helper must be built from the EXACT crewrift commit the arena ran or replays hash-fail → sparse events (no kills/bodies/following/player_state). Check `manifest.json` trace_warning counts first. `/tmp/expand-42fed21` + checkout `~/coding/coworlds/coworld-crewrift`@42fed21 are set up; built warehouses `/tmp/xp_imp_warehouse` (450 XP imposter eps, 0% hash-fail) + `/tmp/crewrift_warehouse` (2 league rounds). Adapter `/tmp/make_wh_input.py` turns fetch_artifacts dirs → warehouse report_request.json.
