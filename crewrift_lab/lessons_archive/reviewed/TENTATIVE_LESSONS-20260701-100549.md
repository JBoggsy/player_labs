# Crewrift tentative lessons — session buffer

**Session started:** 2026-06-30 23:23. This is THIS SESSION's lesson buffer. Write candidate
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

### The `versions.env` expander pin (`CREWRIFT_REF=d9f6b30`) is STALE for 0.4.29 replays — use `expand_replay-8710aa6`
Evidence: xreq_3411 episodes ran crewrift `0.4.29`. Ran all cached expander bins with
`--format jsonl --snapshot-every 1` on a real 0.4.29 replay: `expand_replay-d9f6b30` (the
versions.env pin) exits rc=1 / 0 rows (hash-fails); `expand_replay-8710aa6` (current
`tools/bin/expand_replay` symlink target), `-7aad90e`, `-26ee08c`, `-043` all expand cleanly
(rc=0, 52,940 rows, max_ts=4700, no trace_warning). So the sim is unchanged across 0.4.3–0.4.29
for these later bins, and 8710aa6 is the right expander for current replays. `versions.env`'s
`CREWRIFT_REF` should be bumped from d9f6b30 → 8710aa6 (its own comment says "bump when it starts
hash-failing on fresh replays" — it now does).

### crewborg "IDLE action" = internal `Intent(kind="idle")` → `Command(held_mask=0)` = stand still
Evidence: `crewborg/action.py:_resolve` maps `intent.kind in ("idle","loiter")` to
`Command(held_mask=0)` (no movement input). `modes/idle.py` = "stand still" default/stall stance.
So an idle action is observable in the event warehouse as ~zero velocity while alive; the sim's
`score` event `reason='standing still'` is the matching penalty. Intent is NOT in telemetry.jsonl
(that build only traces `domain.suspicion_tick`), so the warehouse velocity signal is the query path.

### crewborg-as-imposter idles ~23% of live play (median), connected the whole time — a real behavioral leak
Evidence: warehouse over xreq_3411 (100 eps, crewborg v76=586d606f, natural roles rotating seat).
24 imposter games. Per-game Playing-phase (non-meeting), alive, zero-velocity ("idle" intent →
held_mask=0) ticks: median 299 idle ticks = ~23% of live play (range 6–8843; idle_frac 0.01–0.88).
`connected` field = 1.0 across all Playing ticks in every game → NOT disconnects, genuine idle stance.
23/24 games have >a-handful of idle ticks (only ereq_e91, a 573-tick early loss, sits at 6). Outlier
ereq_582: crewborg stood frozen 8,394 consecutive ticks (88% of a 10,000-tick timeout game) while
connected+alive — pathological imposter freeze. Ties to the standing "imposter kill lever" / idle
concern; worth a targeted look at why Search/Hunt fall back to idle for so long.

### crewborg imposter idle root cause: ready-but-blind WATCH — selector never enters Hunt without CURRENT-tick LOS
Evidence: warehouse over xreq_3411. 83% of imposter idle ticks are kill-READY; 79% are ready + a crewmate
within 360px (median 267px) but NOT in current line-of-sight → `has_visible_victim()` false → selector
(`strategy/rule_based._select_imposter`) stays in Search → `SearchMode._watch` idles at a vantage
("watching the crew from a vantage") instead of closing the ~250px. crewborg-v76 idles-while-ready 26% of
live imposter play vs 1-3% for the maintained aaln forks (crewborg-aaln/relhalpha/softmaxwell) → a
crewborg-specific regression in the current vantage-SEARCH FSM (introduced ~v42, "SEARCH replaces Pretend").
The 267px == the known acquisition gap (memory: crew-in-view-at-ready 53% vs Aaron 83%). Hydroponics is the
freeze room in 4/5 top-idle games. Fix under test = v77 (re-acquire on ready) / v78 (+ watch-timeout).

### crewborg's rich per-tick trace (action_intent/strategy/perception/belief) is NOT in the v70/v76 artifact
Evidence: v76's `policy_artifact_<slot>.zip` telemetry.jsonl records ONLY `domain.suspicion_tick` (per-color
probs) + a few one-off domain events — no intent/mode. The verbose trace (act_command, action_intent,
strategy_evaluated, belief_updated, perception, mode_entered) is present only in the AALN-lineage forks'
artifacts (crewborg-aaln/mv/jordan). Hosted crewborg stderr logs are truncated to ~1 line. To get the
subject's tick-by-tick reasoning you must run a trace-enabled build (`CREWBORG_TRACE=debug`), else pair the
objective warehouse with the suspicion trace + reconstruct mode from the selector code.

### GOTCHA: `uv run` from a git worktree imports crewrift from the SHARED checkout, not the worktree
Evidence: in worktree `.claude/worktrees/crewborg-idle-warehouse`, `uv run python -c "import
crewrift.crewborg.modes.search as s; print(s.__file__)"` resolved to
`/Users/.../personal_labs/crewrift_lab/...` (SHARED), so worktree edits were invisible to `uv run pytest`
(tests silently ran against shared code; new-method tests failed with AttributeError). The Docker build
(`build_player.sh`, context = worktree) DID pick up the edits (verified `docker run ... python -c` shows
H1 method + WATCH_IDLE_TIMEOUT present in the image). Workarounds: verify behavior in the built image, or
force `PYTHONPATH=<worktree>/crewrift_lab` (sys.path.insert) to shadow the shared copy. Don't trust local
`uv run pytest` in a worktree to validate worktree source changes.

### Idle-fix A/B outcome: H1 (re-acquire on ready) works; watch-timeout doesn't; freeze is a pick_room dead-end (H3)
Evidence: 3 matched imposter-pinned A/Bs (60 eps each, crewborg slot0 + v70 partner). Base v76 idle&ready=0.68,
kills=1.18, freezes≥1k=23, timeout-draw=0.38. **v77 (H1)**: idle&ready 0.59 (−9pp), kills **1.43 (+21%, p≈0.08)**,
0-kill games 11→5, freezes 23→14, timeout-draw 0.28. Win flat (kill→win bottleneck + weak v70 partner). **v78
(H1+CREWBORG_WATCH_IDLE_TIMEOUT=200)**: idle-bout histogram unchanged vs v77 (201-500-tick bouts 10 vs 11, >1000
14 vs 15) → the watch-timeout had NO effect. Root cause = **H3**: the worst freeze (9,437 ticks, Hydroponics,
kill ready) had crew in crewborg's own room only 1% of ticks → it was stuck in `SearchMode._pick_room` returning
idle "search: no task rooms" (all nearby task rooms excluded, no crew in view), NOT in WATCH — so a watch-scoped
timeout can't catch it. NEXT FIX: make `_pick_room` never dead-end to idle (roam any reachable room / toward
nearest-known-crew) or a mode-agnostic global idle-timeout. SHIP H1; replace H2 with the H3 fix and re-A/B.
