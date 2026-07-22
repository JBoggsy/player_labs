# Worktree results — Thread 8: Honor Society ecosystem follow-ups

> **Temporary handoff doc for the merging agent.** (Replaces a stale copy from the
> already-merged `worktree-imposter-kill-to-win` branch.) Safe to delete after merge —
> the durable knowledge lives in `crewrift_lab/docs/designs/2026-07-22-hs-isolated-ab-prereg.md`,
> `crewrift_lab/crewrift/crewborg/docs/designs/honor-society.md`, `version_log.md`
> (`crewborg-hsoff:v1` row), `crewrift_lab/docs/hs1-ecosystem-notes.md`,
> WORKING_CONTEXT/WEEKLY_CONTEXT Direction 6, and TENTATIVE_LESSONS.

## TL;DR — three deliverables, all done

1. **HS isolated A/B (first ever).** `crewborg-hsoff:v1` probe (v110's byte-identical
   image + recipe + `CREWBORG_HONOR_SOCIETY=0`; 114/114 in-image files sha256-verified
   vs main `9b9606c`) vs the pooled 200 v110 HS-on eps from Thread 1's matched arms.
   Pre-registered before launch. **Verdict: HS-NEUTRAL at episode level (crew 28% vs
   28%, z=+0.02), mechanism-positive** — OFF arm emitted exactly 0 HS events in
   200/200 artifacts (disable path verified), ON arm's HS members vote against our
   crew **3× less** (0.31 vs 0.97 votes/ep, z=−7.1), vote-veto accuracy **20/20**
   (every spared seat truly crew). Keep HS on; monetize via Direction-1 vote
   coordination. Artifacts `/tmp/ab_hsoff/`; arms `/tmp/wh_hsoff{,_episodes}` vs
   `/tmp/hs_on_baseline_eps` (symlink dir of version-verified v110 eps).
2. **Liar-ledger consumer built** (the standing TODO): `crewrift_lab/tools/harvest_liars.py`
   (+`tools/tests/test_harvest_liars.py`) scans harvested telemetry for
   `domain.honor_liar`, gates every event on results.json ground truth, writes vendored
   `crewrift/crewborg/data/honor_distrust.json`; agent-side seam in `honor_society.py`
   (`is_distrusted` → pre-ledgered in `process_chats`, never trusted, traced
   `honor_distrusted_announce`; env `CREWBORG_HONOR_DISTRUST`). **Finding that forced
   the ground-truth gate: the in-game witness false-positived 6× on alex-smith's key
   in 199 baseline eps — all accused seats actually crew.** 0 confirmed liars in 234
   eps scanned — the vendored list ships empty (the normal state).
3. **Alex note written:** `crewrift_lab/docs/hs1-ecosystem-notes.md` — same-key
   multi-seat vs first-poster-wins, encoding canonicalization, publish-the-compact-form,
   palette pinning, verifier cost at scale, the witness-false-positive warning for
   Rule 4, registry/liar-ledger interop. **For James to send; nobody was contacted.**

## Merge notes

- All changes additive; no behavioral change unless `honor_distrust.json` gains entries.
- 669 passed + 14 skipped at HEAD (`uv run pytest crewrift_lab/crewrift/crewborg/tests crewrift_lab/tools/tests`).
- This branch merged `main` @ `113fac3` early (needed the HS1 compact-protocol code).
- Commits: `94a0777` (prereg), `525dc91` (liar consumer), `da6f490` (Alex note),
  `335005a` (ground-truth gate), `3a85529` (verdict + context updates).
- WORKING_CONTEXT / WEEKLY_CONTEXT Direction 6 edits may need union-merge against
  parallel threads (a kill→WIN "survive" thread was running concurrently).
- Disk gotcha recorded in lessons: `/tmp/wh_anchor_base_v107_episodes` actually holds a
  v110 arm and `/tmp/wh_anchor_base_v110_episodes` is half v107 — verify versions per
  episode.json, never trust dir names.
