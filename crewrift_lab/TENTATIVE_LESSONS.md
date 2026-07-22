# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-14 18:47. This is THIS SESSION's lesson buffer. Write candidate
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

### Before "fixing" a flagged bug, check whether a past commit already fixed it — date the evidence

Evidence: Direction 2 said reported_bodies/button_calls_made "never fire" (all-zero across
398 live meetings). That evidence was from the v90 trace batch (pre-2026-07-06); commit
`0fe80c8` (v96) had already fixed the belief-latch self-clear, and a fresh scan of TODAY's
v107 league telemetry showed the features firing (10 rb>0 + 19 bc>0 rows in 21 meetings;
85% capture vs replay ground truth). `git log -S <symbol>` on the flagged code path found the
prior fix in one command. A weekly-context direction can be stale the day you pick it up —
re-validate the headline number against current data before writing any code.

### Validate detectors against replay ground truth, not just "nonzero telemetry"

Evidence: counting nonzero feature rows proved the caller parse fires, but only the
per-event cross-check (expand_replay vote_called_body/button + slot→color map vs the seat's
cumulative snapshot counts) measured CAPTURE (17/20) and exposed the residual failure mode:
all 3 misses were the caller color colliding with crewborg's stale palette-derived self-color
(pre-`2a13256`), which silently excludes that color from banking + ranking. The
miss PATTERN (who gets missed) carried the diagnosis, not the miss rate.

### Importing another team's methodology: filter through the operating model, not topical overlap

Evidence: Pulled from `Metta-AI/optimizer-skills` (an *autonomous*-optimizer library) into
this *human-gated, speed-first* lab. What transferred cleanly: executable engines fitting
our shared-engine + per-lab-adapter pattern (their variance miner → `coworld-hypothesis-miner`),
durable engineering doctrine (`docs/player-engineering.md`), and dense measurement heuristics
(eval sizing from variance, opponent-field-from-goal → root `best_practices.md`). What was
deliberately rejected despite topical fit: promotion-gate / continuous-optimizer /
defend-leaderboard (their replacement for our human gate — importing would fight the lab's
model), the local-sim harness (probe deltas reverse on the live field), game-strategy
snapshots (stale vs our live labs). Where an import diverges from its source's posture,
state it in the imported doc (e.g. "uploads stay ungated here") so readers don't inherit
the source repo's caution.
