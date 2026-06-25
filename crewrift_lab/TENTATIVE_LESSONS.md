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

### WHY AARON BEATS US: we DITHER on ready kills (1929 idle-ready ticks/g vs his 567) + make 2.5× fewer isolations (warehouse head-to-head, 2026-06-25)
Built /tmp/v42_warehouse (200 v42 imposter eps vs Aaron+Andre LATEST, expand-0159, 10M events) and compared crewborg:v42 vs crewborg-aaln:v17 (Aaron's fork of crewborg, now ahead) AS IMPOSTER. Scripts: /tmp/aaron_compare.py, /tmp/kill_latency.py.
- **KILL DITHER (James's hypothesis, CONFIRMED — the big one):** dither = Playing-ticks between kill_cooldown hitting 0 and the kill. Us median 28 / mean 256; **Aaron median 1 / mean 47** — he kills the instant he's able. **idle-ready ticks/game (alive+cooldown-ready+NOT killing): us 1929 vs Aaron 567 (3.4×).** This IS the kill→win conversion gap, quantified. Likely cause: Hunt's witness-bar ("wait for unwitnessed, relax with urgency") too conservative. → next experiment: kill faster when ready.
- **Isolations/game (alone w/1 crew = kill setup): us 1.35 vs Aaron 3.41 (2.5×).** Follows/g: us 2.76 vs 4.33. Aaron manufactures far more kill chances.
- **Movement:** room-entries/game us 34.2 vs Aaron 13.4 (we wander; he's patient). Presence: Aaron camps Bridge (28%, central hub) we barely use; we spread task rooms (Science Bay 31%/Storage 21%/Hydroponics 18%).
- **Ejection (imposter-ended-dead): us 24% vs Aaron 39%** — WE get caught LESS. Aaron trades stealth for aggression and wins. Kills, not stealth, win here.
- Method now durable: kill_cooldown already in player_state (NO expander fix needed); ejection = imposter ended dead. Queries in the two /tmp scripts (candidate to graduate into a crewrift analysis skill).

### CONFIRMED (n=180): vantage-SEARCH kills/g 1.23±0.10 — kills up, but win 34% (kill→win conversion is now the gap, NOT kills) (2026-06-25)
200-ep confirmation vs Aaron+Andre LATEST (truecrew:v25, crewborg-aaln:v17 — note Aaron jumped v3→v17, a stronger field). v42 (vantage, non-debug): **kills/g 1.23±0.10** (vs v40 0.60, v38 0.85 — robust win), 0-kill only 11% (was 60% at v40), ≥2k 30%. BUT imposter **win 34%** [CI 27-41], DOWN from v38's 43% despite more kills. ⚠️ CORRECTION (James): my "zero ejections" claim was WRONG — `-100` = disconnect/crash only; EJECTION CARRIES NO SCORE PENALTY, so you can't infer ejection rate from scores at all (must read logs/replay — see best_practices Scoring). So ejection rate is UNKNOWN/unchecked; it could be contributing to the lower win. What IS true: kills in wins (1.33) ≈ kills in losses (1.20) → kills are no longer the bottleneck. Next: warehouse the 200 eps (expand-0159) to check (a) did "near crew" rise [mechanism] and (b) ejection rate via logs, then attack kill→win CONVERSION. Vantage fix = keep (kills robustly up). v42 shipped to Crewrift PRIME league 2026-06-25.

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
