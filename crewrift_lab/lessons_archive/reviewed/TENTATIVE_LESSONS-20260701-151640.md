# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-01 12:56. This is THIS SESSION's lesson buffer. Write candidate
**Session started:** 2026-07-01 11:23. This is THIS SESSION's lesson buffer. Write candidate
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
### Pooled warehouses mis-attribute per-version behavior — always split by policy_version_id
Evidence: I reported "v81 crew votes 19/21 skip" from /tmp/v81_fp_wh, but that pool included v80 seats; split by version UUID, v81 actually voted players 4/27 (3/4 correct) and chatted 14 times. The dead-voting "bug" in v81 was an artifact of pooling with v80.

### The v80 vote/chat blackout was the SAME latch bug, one hop deeper
Evidence: mis-latched crew absorbed reveal icons into teammate_colors → suspicion skips teammates → empty posterior → imposter meeting path finds no target → silent skip. One perception bug produced three surface symptoms (0 tasks, 0 votes, 0 chat). Lesson: multiple weird symptoms in one version = look for one upstream cause before filing three bugs.

### Platform game updates can silently cool fitted models — re-baseline after every game version bump
Evidence: crew vote rate fell 51%→15% with NO crewborg code/weight change; live posteriors stopped crossing the fitted 0.9 vote gate after crewrift_prime 0.4.21→0.4.28/29 (mid-day 06-30), which also changed voteTimerTicks 240→1200 while strategy/meeting/context.py hardcodes 240 (we stop listening ~16% into the meeting). Fitted-threshold behaviors need re-measurement after game bumps.

### Deterministic per-seat failures exist — check slot number before averaging
Evidence: all 3 role-limbo frozen crew seats in the v81 batch were slot 4, every time (CREWMATE reveal text never parses at that seat). A per-seat deterministic condition looks like a ~12% random failure when averaged over 8 seats.
### League telemetry artifacts are EPHEMERAL (~one round's retention) — harvest every round or lose them
Evidence: v82 league eps fetched ~21:10: only the newest round's episodes (21:05+) had policy artifacts, 6/100; rounds from 20:38-20:50 had none. Same pattern in the v80 pull (17/196, all newest-round). With all-telemetry uploads now standard, a per-round artifact harvest (cron/loop every ~10 min) is needed for continuous telemetry.

### v80's broken crew suppressed the WHOLE division's crew win rates — one bad seat in every episode drags all crew teams
Evidence: with v80 (half its crew games thrown) in every league episode, the field's crew win rates read 13-21% ("imposter-favored meta"); in v82's first 100 league eps the field's crew is 25-33%. Part of the "meta" was our bug leaking into everyone's crew teams. Lesson: a champion plays in ~every episode — its pathologies bias every measurement of the field, including the meta itself.
