# Cue-n-Woo tentative lessons — session buffer

**Session started:** 2026-06-15 10:28. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`cue_n_woo_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Cue-n-Woo-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### The game switched from 61 named styles to axis_combo (4 of 15 axes, ~287M combos) — the 61-style classifier is dead.
Evidence: Fresh league replay (job a36f76ff, 2026-06-15) `config_public.concept_type=axis_combo`, `concept_axis_count=4`, `hidden_concept.components=[{register:technical},{rhetoric:evidence-first},{time:frontier town},{sensory:sterile}]`. Game source `Metta-AI/cue-n-woo@545ec46` `game.py:select_axis_combo_concept` samples 4 of 15 axis files (data/concept_axes/, 326 values total), one value each, joins with "; ". Also changed: round_timeout 300->600, worker url -worker -> cue-n-woo-fleet, reveal_concept_to_clients=false (concept hidden from live state, still in replay). Scoring (`answer_score`) UNCHANGED. mentalist v3 classifier returned a 3-way tie (haiku 0.354/urban-planning 0.347/sermon 0.341) on a concept not in the 61-list at all. Full writeup: docs/axis-combo-system.md.
Status: confirmed. The judge now rewards concrete terse nouns ("A brass key" p=0.95) over florid in-style prose; mentalist authored-question p=0.00-0.17. Rank 3/3.

### Verify what's in main with `git fetch` FIRST — a local ref can be stale and produce a confidently-wrong "not merged" claim.
Evidence: I checked `git branch -r --contains <sha>` and `origin/main` log BEFORE fetching, concluded P1-P5 SDK PRs were "on sdk-gen-p5, not merged to main," and wrote that into the design doc as a build blocker. After `git fetch origin`, origin/main clearly contained #67-#71 (P1-P5) at tip fdf2987 — they HAD been merged. The user corrected me. Same family as the cnw "verify success not capability" methodology lesson: confirm against fresh ground truth, don't infer from a stale local snapshot.
Status: corrected. Relocked lab 146905e->fdf2987, venv synced, all P1-P5 helpers import, 385 tests green.

### The Player SDK telemetry core is already grid-free; only coworld_json_bridge imports mettagrid (and __init__ never imports it).
Evidence: SDK report `players/player_sdk/docs/designs/generalizing-the-sdk-for-turn-based-games.md` + source: a turn-based text player can `from players.player_sdk import TraceOutputs` with no cogames extra and zero gridworld surface. My rev-1 mentalist design doc claimed "adopting telemetry pulls in mettagrid types" — FALSE against main. P1 (test_sdk_core_grid_free.py) makes the boundary a tested contract. The right SDK adoption for cue-n-woo: run_message_bridge (P2, bakes in the exit-0-on-code-1006-close rule) + player_sdk.llm (P3, client/model/usage — but it's text/JSON, NOT tool-forced, so mentalist keeps its own tool path) + TraceConfig (P5) + TraceEvent.step (P4) + telemetry namespace (P1). NOT the tick-based AgentRuntime (built for gridworlds; crewborg and suspectra both bypass it).
Status: candidate.
