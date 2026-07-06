# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-05 23:01. This is THIS SESSION's lesson buffer. Write candidate
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

### A belief field consumed by a later fold stage must not be set-and-cleared inside the same update
Evidence: types.py latched meeting_caller_color and then, three lines later, cleared it whenever
belief.phase == "Playing" — and derive_phase has no MeetingCall state, so phase stays "Playing" for
the whole interstitial. update_social_evidence runs after update_belief, so _bank_meeting_caller
never saw a non-None caller: reported_bodies/button_calls_made were 0 across all 3,238 v95
telemetry rows. Fix: clear only when the interstitial text is also gone (play truly resumed).
Status: fixed 2026-07-05, end-to-end tests added (test_belief.py, test_social_evidence.py).

### Unit tests that set latch fields directly can't catch latch-lifecycle bugs — add one fold-path test per latched signal
Evidence: test_social_evidence.py's caller tests set belief.meeting_caller_color by hand and passed
for months while the real update_belief path zeroed the feature in every live game. A single test
driving update_belief + update_social_evidence together (the fold order __init__.py uses) would
have caught it on day one.

### Check the fitted weights file before assuming a dead feature needs a refit
Evidence: reported_bodies/button_calls_made were zero at runtime, but v3-runtime
suspicion_weights.json holds healthy NONZERO coefficients (-0.26 / -1.59) because offline training
reads replay ground truth (expand_replay emits the caller slot), not runtime perception. So the
bug was train/serve skew, not a poisoned fit — fixing the runtime parser closes the skew with the
weights already shipped, and the planned refit becomes validation instead of a prerequisite.

### When a perception feature reads as always-zero, diff the claimed wire format against the vendored game source
Evidence: resolve.py's MEETING_CALL_TEXT premise ("<Color> reported" text lines) was actually
CORRECT — global.nim:1030 emits exactly that at ProtocolTextObjectBase 9000. Hours of suspecting
the regex/label were wasted relative to checking the belief-fold consumer first; but the vendored
source (.cache/crewrift-src/<hash>/src/crewrift/global.nim) settled every wire-format question
definitively and ruled out the whole perception layer in one pass.
