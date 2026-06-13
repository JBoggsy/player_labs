# Crewrift tentative lessons — session buffer

**Session started:** 2026-06-12 15:04. This is THIS SESSION's lesson buffer. Write candidate
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

### Crew emergency-button reset-calls are near-universal and run on a ~900-tick rhythm
Evidence: button_runner_study.py over 1,875 croatoan games: 92.5% have ≥1 button call,
mean 2.15/game, 3,740 crew vs 298 imposter callers. Gap-from-prior-meeting median 945t
(clusters 800–1000). So crew re-press ~every 900t — past the 500t kill CD, so the runner
is killable. Validates the button-runner-interception premise + James's "especially 900".

### Button-runners travel solo and funnel through the bridge's eastern (Hydroponics) mouth
Evidence: same study. Runner is median 241px from button 250t before pressing; median 0
other crew within 48px the whole approach (solo). 57.3% of approaches pass through
Hydroponics; chokepoint cells at the Bridge↔Hydroponics corridor mouth (~x270-368, y272 /
y400), ~150-240px east of the button. ~42% are already at the bridge (not interceptable
without camping). → bias imposter Search to the corridor/Hydroponics, NOT the bridge interior.

### A standing positional Search bias toward a chokepoint REGRESSES imposter kills (corridor-camping costs general hunting)
Evidence: button-runner-interception Tier 1 (bias imposter Search toward the bridge↔Hydroponics
button corridor during the kill window) A/B'd controlled 2-imp 100 eps/arm: kills 1.27→0.91/g
(−28%, p=0.000, d=−0.58), no-kill games 7%→23%, 2+kill games 31→13. Mechanism: camping a
chokepoint for the whole kill window sacrifices occupancy-driven isolated-straggler hunting AND
parks the imposter in a witness-dense area (bridge = 5 tasks + spawn) so kills fail `unwitnessed`.
Lesson: capture a rare event (runners ~2×/g) with an EVENT-TRIGGER (detect-then-divert), never a
standing bias that pays a cost every cooldown. Phase-0 opportunity was real; the mechanism was wrong.

### Removing the imposter witness/isolation kill-gate does NOTHING — the kill cap is cooldown+range, not caution
Evidence: CREWBORG_NO_ISOLATION (unwitnessed()→True) traced 2×2 100 eps/arm: kills 1.27→1.24/g
(p=0.80), no-kill 13%→12%, ejection 7%→9%, first-kill-tick ~4500 unchanged. Traces: Hunt spends
~96% of ticks in EVERY arm (incl. iso-off) closing distance to a victim, not waiting out witnesses
— the gate almost never fires at the moment of opportunity. 3rd independent confirmation (BE_DUMB
v23, kill-sooner v24, this) that imposter kills sit at a structural ceiling (~1.27/g). Stop tuning
imposter kill volume; it's cooldown-bound. The lever to move wins is crew/conversion, not kills.

### Hosted trace output goes to artifacts/policy_artifact_<slot>.zip (telemetry.jsonl), NOT the policy_agent log
Evidence: with CREWBORG_TRACE_GROUPS set on a hosted experience request, policy_agent_0.log was 1
line ("game over"); the real per-tick decision_snapshot trace (96k lines/episode) was inside
artifacts/policy_artifact_0.zip → telemetry.jsonl. fetch_artifacts pulls the zip; unzip per episode
to analyze. decision_snapshot.data has phase/role/mode/intent(kind,reason,point); imposter role
flips to 'dead' only on EJECTION (clean ejection detector). 'self' is null until Playing.

### A/B env-flag isolation requires carrying ALL of the champion's runtime env, not just the new flag
Evidence: uploaded v26/v27 with only CREWBORG_FRONT_BIAS (candidate); forgot v25's
CREWBORG_TRACE_GROUPS/METRICS/CHAT_NLP. Result: slot-0 policy logs were empty ("game over" only),
so no trace-level qualitative analysis was possible — had to characterize the mechanism from
results.json kill distributions + replays instead. The A/B stayed valid (both arms equally lacked
those envs, so the only v26↔v27 delta was the flag), but lost observability. Next time: copy the
champion's full --secret-env set and add the new flag on top.

### Corpus study before policy code: the expanded JSONL already has caller-attributed buttons + position snapshots
Evidence: replay_parse.parse_game gives Meeting(kind='button'/'body', caller_slot, call_tick),
per-slot StateSample(tick,x,y,room,alive) every 24t, roles, and map_geometry (rooms+button).
Enough to reconstruct any actor's approach path and aggregate spatially — a Phase-0 "where/how
often" study needs zero policy changes. Reuse suspicion_lab/expanded; pass Path (not str) to parse_game.
