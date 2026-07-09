# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-07 09:38. This is THIS SESSION's lesson buffer. Write candidate
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

### The xp-request top_n/random pool now ranks by the commissioner leaderboard (metta PR #17294)
Evidence: replaced the bespoke 30-day mean-reward ranking (deleted with #17288's query) with the
division's commissioner leaderboard via `load_division_leaderboard_snapshot` — the same order the
league page shows. Division = target division, else league's top competition division. No board:
top_n → 400, random → unranked active champions. Reused the loader in-process (no HTTP self-call,
no duplicate sort). This means our lab's `resolve --division` helper (leaderboard+membership join)
and the backend now agree on ordering. NOTE: commissioner rank ≠ a sort of any single score column
we had — always trust the board's `rank`, not a reward/score sort.

### Gate any LLM-behaviour A/B on the LLM actually FIRING — Bedrock daily token quota kills it silently
Evidence: 2026-07-08. The v102+v103 social-rework A/Bs (1200 LLM-on eps each) showed the meeting
LLM producing decisions only ~2% of the time — 1798/1811 failures were `RateLimitError 429 "Too
many tokens per day"` (shared DAILY Bedrock quota). So the LLM-only prompt doctrine never ran; the
A/B silently tested only the deterministic path, and "the rework didn't help" was UNSUPPORTED (it
was untested). BEFORE trusting any LLM-behaviour A/B: measure `meeting_llm_decision`/`fallback`
ratio; if the LLM isn't firing (>~50%), the result is about the deterministic fallback, not your
LLM change. Running big LLM-on batches (evals + chat labeling) exhausts the day's quota — budget it.

### Never mutate a source-of-truth set against a re-derived, drifting value every tick
Evidence: v102 kill regression (2026-07-08). Added `belief.teammate_colors.discard(belief.self_color)`
run EVERY tick to dedup self. But `self_color` is re-derived per tick (vote cursor / nearest sprite)
and drifts onto a teammate's colour mid-game → the discard permanently deleted the real teammate →
kill gate let crewborg attack its teammate → kills 1.86→0.97 (n=138/143, ~10σ). Fix: exclude self
from the REVEAL SET at ingest only (one-shot, against the authoritative reveal read), never a
per-tick discard against the fuzzy drifting value. Lesson: teammate_colors is source-of-truth,
self_color is an estimate — mutate the truth with the truth, never with the estimate.

### An A/B regression in a path your change can't touch = look for a DIFFERENT change of yours first
Evidence: same. The "social rework" was meeting-only but kills (in-game) regressed — impossible from
meeting code. The culprit was a SECOND change bundled in the same build (the self-dedup). When a
metric moves that your headline change can't mechanically affect, audit every other diff in the
build before theorizing about the headline change. (Also: I over-theorized on partial mid-run data
and was wrong twice; wait for the batch + trace the mechanism.)

### Warehouse vote targets live in vote_cast.target_slot/target_label, NOT .target (.target is skip-only)
Evidence: 2026-07-07 chat study. I nearly concluded the persuasion study was blocked ("vote_cast.target
is always null/skip") — wrong: non-skip votes carry `target_slot`+`target_label`+`secondary_role`,
fully present in `34a97a3`-built warehouses. Only skips use `.target`. This unblocked the whole study
(no extractor fix needed) and also unblocks the crew vote-conversion lever (thread #22 was a false alarm).

### Control for meeting-timing when labelling "did chat X move votes" — late msgs mechanically move fewer
Evidence: chat study. First fit had `f_latency_ticks` dominating every model (−1.7 coef) — a late
message has few subsequent votes to shift, a mechanical confound, not persuasion. Fix: keep timing as
explicit CONTROL features (latency, speak_order, votes_remaining) so content coefficients read "holding
when-in-meeting fixed." Any "did event X change downstream Y" label over a bounded window needs this.

### Trace the BELIEF before "fixing" a perception bug — replay-inferred behaviour ≠ a belief failure
Evidence: 2026-07-07. The "teammate detection is broken" lever rested on a replay-inferred stat
(crewborg-imposter follows its own co-imposter 32.4% — field-worst). James insisted on verifying the
belief before coding. Added a per-game belief trace (`role_resolved`+`teammate_belief_changed`,
v101), cross-referenced claimed teammate_colors vs warehouse ground-truth roles: 0/24 failures, 0/24
false teammates — detection works PERFECTLY. The witnessed-imposter-latch fix would have fixed
nothing. A behaviour measured from the replay (who followed whom) is NOT evidence of what the agent
believed; to diagnose a perception/belief bug you must trace the belief itself. Two consecutive
"mechanistic levers" (wanderer bug, teammate detection) both evaporated on verification against fresh
data — old warehouse-diagnosed memories drift; re-verify every lever before building.

### Get the query plan before blaming a missing index — a timeout is not proof of an unindexed scan
Evidence: 2026-07-06 root-caused the xp-request 500 to "two unindexed predicates" incl.
`job_requests.job ->> 'coworld_id'`, and drafted a migration PR for it. 2026-07-07 ran the
actual `EXPLAIN ANALYZE` (read-only prod via `devops/tools/db-shell.py` target `observatory-ro`,
`SET statement_timeout=0`): `job_requests` is a PK probe, `coworld_id` is a post-fetch Filter
— the proposed index would be dead weight. Real cause was a `rows=1` CTE misestimate driving a
12× nested-loop recompute of a correlated aggregate. The reasoning-from-SQL-text guess pointed
at the wrong table entirely.

### A grouped CTE the planner can't see through → rows=1 misestimate → per-row subquery recompute
Evidence: metta PR #17288. `load_ranked_champion_policy_version_ids` left-joined an
`eligible_champions` grouped CTE to a correlated reward-aggregate subquery in ONE statement.
Planner estimated the CTE at 1 row (really 12), chose a nested loop that re-ran the whole
aggregate `loops=12` → 24s, over the 15s timeout. Fix: split into two queries + drive the
aggregate off a `VALUES` list of concrete keys → planner gets real counts, aggregate runs
once (3.4s). General pattern: when a subquery's cost multiplies by an outer-row count that
"should be 1," suspect a CTE/group barrier hiding the true cardinality — split it.

### Preserve composite key pairing when replacing a correlated join with an IN/VALUES list
Evidence: same PR. The reward join paired `policy_version_id` (uuid, on episode_policies) and
`pv_internal_id` (int, on episode_policy_metrics) to the SAME champion per CTE row. Two
champions can share an episode, so independent `IN (uuids)` + `IN (ints)` filters would
cross-average rewards. Used a `VALUES (uuid, int)` pair list to keep the pairing intact.
Validated the split output row-for-row against the original before shipping.

### A merged index-migration PR ≠ a live index; check alembic_version AND heads
Evidence: #17117 (episode_policy_metrics index) merged 2026-07-06 but the index did NOT exist
in prod until 2026-07-07, because the same PR branched a *second* alembic head off the same
parent as #17177. `alembic upgrade head` (singular) fails with "Multiple head revisions" and
applies NOTHING until a merge migration (#17268) unifies them. Verify deploy by querying the
live DB for the index + checking `alembic_version` advanced, not by "the PR merged."

### Don't fetch replays for large eval batches — telemetry.jsonl is enough, replays balloon /tmp
Evidence: 2026-07-08→09. Two 1200-ep A/Bs fetched WITH replays = 30GB in /tmp (44GB total our
runs), filling a machine already ~85% full → ENOSPC deadlock (every command failed, wrapper
couldn't write its output file). The LLM-rate / ejection / kill measurements only need the policy
`telemetry.jsonl` inside `artifacts/policy_artifact_*.zip` — NOT the multi-MB `replay.json`. Rule:
fetch `--no-replay` unless a warehouse build genuinely needs replays, and delete each batch's
episode dir right after extracting its numbers. Replays only for the qualitative deep-dive on a
handful of episodes.
