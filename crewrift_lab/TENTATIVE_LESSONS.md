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
Status: CONFIRMED by warehouse (170-ep Prime sweep): crewborg-crew called **97 button meetings**
(notsus: 4), **9% convicted** an imposter, **27% ejected a crewmate**, crewborg itself **voted skip
in 54%** / **silent in 80%** of the meetings it called. Two opposite fixes are being A/B/C-tested.

### Two ways to close the call/convict gap — A/B/C, not a single fix
Evidence: the gap can be closed by aligning the bars EITHER direction. (A "raise") only call when the
tailer is already `top_suspect` — call rarely, convict surely. (B "lower") keep calling at 0.6 but
lower the in-meeting vote bar to 0.6 (`CREWBORG_WEIGHTS_VOTE_P=0.6`) — call readily, convict at the
lower bar. They trade off precision vs. activity: A risks under-calling (the feature goes nearly
dormant), B risks mis-ejecting crew (the fitted intercept puts a no-evidence player at P≈0.57, so 0.6
is barely above baseline). Lesson: when a fix is "align two thresholds," BOTH directions are real
candidates — don't assume raise-to-safe is better than lower-to-active; A/B/C them.
Status: 3-arm A/B/C launched 2026-06-30 (arms crewborg-emr-{base,raise,lower}:v1), 7 Prime champions
× 20 eps each, our policy = 6 crew vs champion = 2 imposters. Verdict pending.

### Build/upload hazard: parallel worktree agents share the global Docker `:dev` tag
Evidence: a concurrent agent (imposter-kill worktree) was rebuilding `players-crewborg:dev` and
uploading under `--name crewborg` at the same time as this session — so `players-crewborg:dev` could
not be trusted to be MY code. Fix: build each arm under a UNIQUE image tag (`players-crewborg:accuse-cand`,
`:emr-base`, `:emr-lower`) and verify the image carries the change (`docker run … grep`) before
uploading. Also: hosted uploads/POSTs were flaky (broken pipe), so wrap them in retry loops and verify
server-side (`versions.py`) rather than trusting one attempt.
