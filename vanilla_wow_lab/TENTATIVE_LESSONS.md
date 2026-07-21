# Vanilla WoW tentative lessons — session buffer

**Session started:** 2026-07-21 09:23. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`vanilla_wow_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Vanilla-WoW-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### The game repo's origin/main gets FORCE-REWRITTEN — sync the read-only checkout with `git reset --hard origin/main`, not merge

Evidence: 2026-07-21 pull: HEAD and origin/main had diverged by ~12k/~15k commits with
the SAME author/content (history rewrite upstream); `git pull` produced thousands of
add/add conflicts. Since the checkout is read-only reference, `git fetch && git reset
--hard origin/main` is the correct sync (stash untracked .recon/ first).

### wow_sdk's file-bridge contract DRIFTS at HEAD — validate bridge code against the PINNED base image's SDK, not the checkout

Evidence: HEAD (0.1.31-era) removed `action_file` from EmbeddedClientRuntimePaths
("Move live bot control into Nim", cc4ad8843) — bridge tests importing wow_sdk from the
checkout broke while our digest-pinned 0.1.19 base is unchanged and still deployed...
EXCEPT `coworld list` now shows vanilla_wow 0.1.31 deployed, so the NEXT pin bump must
re-verify the whole file-bridge contract (action.json may be gone at 0.1.31 — the
Python-policy seam may have moved). Fix applied: tests import from
vanilla_wow_lab/.sdk-snapshot/ extracted from the pinned image (recipe in conftest).

### The full evidence stack is CONFIRMED working hosted — elevated fetch returns logs+artifacts+results; all 10 slot-audits pass

Evidence: 2026-07-21 elevated re-fetch of xreq_c530da3b (both eps completed, 0 failed).
Per slot: `policy_agent_N.log` (~140 KB stdout incl. 122 WOWBORG-TRACE lines + the
"evidence bundle: [trace.jsonl, action-results.jsonl, state.json, heartbeat.json]"
confirmation), `policy_artifact_N.zip` (the bundle itself), AND `results.json` (retained
this time). `trace_audit.py` on every slot × its own episode: 10/10 agree (e.g. Freshwar
claimed 269.6 yd settled vs 273.5 yd observed). Root causes of session-3/4 gaps: 403
without `--elevated` + upstream deletion of v1 /jobs routes (fixed in 7130f40 on main).

### In same-brain self-play, identify "our" replay member by BEST breadcrumb overlap, not first match — and per-episode, artifacts only pair with their own replay

Evidence: trace_audit's first-match member detection misattributed slots (every slot
says similar "wowborg leg N" texts); fixed to max-overlap scoring, but explicit
`--member` (from trace session_start.character) is the reliable path. Also: a sloppy
audit loop cross-matched ep-1 traces against ep-2's replay → phantom findings. The
session_end "done:" say is often rate-limit-suppressed in-game but present in the trace
— a 1-say discrepancy is expected noise, not a violation.
