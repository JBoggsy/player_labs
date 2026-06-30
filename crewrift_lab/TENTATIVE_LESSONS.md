# Crewrift tentative lessons — session buffer

**Session started:** 2026-06-26 23:22. This is THIS SESSION's lesson buffer. Write candidate
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

### Crew emergency meetings can't convict the tailer: call bar (0.6) << conviction bar (0.9)
Evidence: `AccuseMode` calls a button meeting when `active_tail_suspect` clears `ACCUSE_THRESHOLD=0.6`
(suspicion.py:134), but the meeting that opens runs `AttendMeetingMode._decide_crewmate`, which
re-derives `top_suspect(belief)` — under the vendored FITTED weights (the default) that returns a
target only at `WEIGHTS_VOTE_PROBABILITY=0.9` with NO clear-leader rule (suspicion.py:583-590). A
tail-only suspect peaks ~0.28-0.7 under the fitted model (`tail_obs_max_run` is NEGATIVE in every
bin: -0.525..-0.574; `tail_obs_samples__gt20` only +0.293), so `top_suspect` returns None →
**silent_skip**: crewborg burns its one-shot button + the whole team's task-time and says/votes
nothing. The accuse.py + design §7.1 docstrings claim "the meeting accuses + votes the tail" — but
the code never threads the called suspect into the meeting; `Intent.target_color` on `call_meeting`
is explicitly "forensics only — the meeting vote re-derives the target from suspicion" (types.py:446).
Documented-but-unimplemented = a real bug.
Status: diagnosed from code; quantifying frequency/conversion in the event warehouse; fix = thread
the called-suspect into the meeting and commit (chat+vote) rather than re-deriving top_suspect.
