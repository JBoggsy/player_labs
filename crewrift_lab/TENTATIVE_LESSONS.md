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
Status: 3-arm A/B/C DONE 2026-06-30 (420 clean eps, our policy=6 crew vs each of 7 Prime champions
=2 imposters, 20 eps/cell). **VERDICT — neither bar-alignment moves crew win rate; "lower" is
actively dangerous:**
- crew win: base **23.6%** (33/140), raise **25.0%** (35/140, +1.4pp p=0.78 NS), lower **20.0%**
  (28/140, −3.6pp p=0.47 NS). All three statistically indistinguishable at the arm level.
- "lower" (convict at 0.6) is a high-variance TRAP: +35pp vs notsus (50% — notsus imposters cross
  0.6 on real evidence) but COLLAPSES to **0/20** vs three aaln-lineage imposters (crewborg-aaln,
  crewborg-mv, jordan-aaln) + 10% vs aaln-richard. Mechanism (highly significant): lowered-bar crew
  cast **6.06 player-votes/g** (base 3.02, raise 2.06) and **65% of their losses are crew-on-crew
  self-ejections** (imp kills≤3 ⟹ a crewmate was voted out; base 26%, p=7e-9). Against stealthy
  (crewborg-derived) imposters that stay under 0.6, the 0.6 crew vote each OTHER out → parity gift.
  Empirically validates exactly why the fitted crew vote bar is 0.9 (precision).
- "raise" (call only when convictable) is a SAFE no-op: neutral win rate, fewer crew player-votes
  (3.02→2.06 — it stops spending the button on unconvictable tails), no downside. It implements the
  documented intent and removes the warehouse-confirmed waste (97 calls, 9% convict, 27% mis-eject)
  at zero cost — but the emergency meeting is NOT the crew-winrate lever.
- BIG-PICTURE lesson: the crew emergency-meeting bar doesn't move crew outcomes in EITHER direction.
  Crew lose ~76-80% regardless; **77/140 base games were "nearly done (≥36/48 tasks) but lost"** — the
  real crew lever is the PARITY RACE (surviving kills / finishing tasks faster / voting imposters on
  STRONG evidence), not the tail-meeting threshold. Recommend: keep "raise" (safe waste-removal),
  reject "lower" (dangerous), look elsewhere for crew win rate. [[crewborg-crew-weakness]]

### Commitment to the button run must be gated on convictability, not just "alive"
Evidence: with "raise", acquisition is safe (we only START an Accuse run when the tailer is
`top_suspect`), but the OLD stickiness (`rule_based._sticky_accuse_target`) kept walking to the
one-shot button as long as the committed target was merely ALIVE — never re-checking the vote was
still winnable. A suspect exculpated mid-walk (the fitted model lowers P when a player does tasks /
is observed) still got the button spent on a meeting that now silent-skips. Fix: keep the committed
target only while it is alive AND still `top_suspect` (the player the meeting would eject). Suspicion
has no time decay, so this still survives the tail lapsing as we walk away from the suspect — but a
suspect that drops below the vote bar / is overtaken / voted / killed releases the run → back to
tasks. Lesson: a "commit through transient noise" rule must re-validate on the END CONDITION that
makes the action worth it (here: convictability), not a proxy (alive) that stays true long after the
action stopped paying off.

### Convictability flickering (≥0.9 → <0.9 mid-game) is suspicion-MODEL volatility, not a meeting bug
Evidence: the only reason the abandon-the-run guard above is needed is that a player we judged
near-certain (`top_suspect`, P≥0.9) can later fall below the bar. If the suspicion posterior were
stable, a convictable suspect would STAY convictable and the guard would rarely fire. So the guard is
DEFENSIVE against suspicion noise — the durable fix is in the suspicion components (the fitted model /
`suspicion_lab`), which is owned elsewhere. Lesson: when a downstream consumer needs a "don't act on
stale confidence" guard, note it as a SYMPTOM pointing at upstream model instability — fix the guard
to stay safe now, but flag the root cause rather than papering over it silently. [[crewborg-v70-equals-base]]

### Build/upload hazard: parallel worktree agents share the global Docker `:dev` tag
Evidence: a concurrent agent (imposter-kill worktree) was rebuilding `players-crewborg:dev` and
uploading under `--name crewborg` at the same time as this session — so `players-crewborg:dev` could
not be trusted to be MY code. Fix: build each arm under a UNIQUE image tag (`players-crewborg:accuse-cand`,
`:emr-base`, `:emr-lower`) and verify the image carries the change (`docker run … grep`) before
uploading. Also: hosted uploads/POSTs were flaky (broken pipe), so wrap them in retry loops and verify
server-side (`versions.py`) rather than trusting one attempt.
