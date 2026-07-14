# player_labs — deferred tasks

Tasks intentionally parked to handle later. Add items here when you defer something
mid-session; check them back at the start of focused work.

## Open

- **Fix `rotate_lessons.sh`: it re-archives UNCHANGED buffers under new timestamps (2026-07-13,
  lessons sweep).** Found independently in 3 labs during the cross-lab lessons review: ctf_lab had
  4 byte-identical archived buffers, heartleaf_lab 4, crewrift_lab 2 pairs — one session minted as
  several "independent" sessions, silently inflating the recurrence signal `/lessons-review`
  graduates on. Fix: the hook (each lab's `tools/rotate_lessons.sh`) should skip rotation when the
  live buffer has no `### ` entries or is byte-identical to the newest archive. Until fixed,
  reviews must dedupe archives by md5 before counting recurrence. Related earlier incidents: the
  hook archived files with unresolved conflict markers verbatim (cue_n_woo 2026-07-05) and a
  stale-branch rotation silently dropped upstream lessons (crewrift 2026-06-15).

- **Imposter incidental co-location with teammate — avoid clustering (2026-07-07, James).** Belief
  trace refuted the "teammate detection is broken" theory (v101: 0/24 detection failures, teammate
  known every game — see [[crewrift-imposter-kill-lever]]). BUT the replay shows crewborg-imposter
  near/following its co-imposter 32% of intervals (field-worst), and since it correctly KNOWS the
  teammate, that's **incidental co-location** — two imposters clustering wastes coverage and reads as
  a tell to crew (two players always together). Not suspected to be a big loss driver (James), so
  LATER. Fix direction: an imposter-side "spread from known teammate" nudge in movement/search
  (repel from `teammate_colors` positions), analogous to crew dispersion. The teammate identity is
  reliable (`teammate_colors`), so the signal to act on is already there.

- **RESOLVED 2026-07-02 (cycle-2 fingerprint): ghost "idle" decomposed** — 70% is meetings/GameOver
  (vote-timer-inflated, unavoidable), 20% is healthy tasking, 8.5% is post-completion parking at home
  (`normal.py:_return_to_start` — bounded, ~-1 score/40 eps, not worth a slot). Decide layer is FINE;
  noclip retest low-value. NEW actionable finding: dead seats consumed 23% of meeting-LLM calls on votes
  that never count → v88 mutes the meeting LLM for dead seats. Original item kept below for context.
- **Ghost idle mechanism — dead crew idles upstream of navigation** (2026-07-02, from the ghost-tasking
  experiment). Dead-task completion 50-64% vs notsus 61-69%; ghosts stand still 72-79% of dead time but
  only ~8-10% of that is at task stations — they idle in the DECIDE layer, not en route. Noclip nav was
  implemented + A/B'd flat (kept unmerged on `worktree-ghost-tasking`, commit b3d8844 — harmless, retest
  if the decide fix lands). Next instrument: per-tick fingerprint of ghost time (held intent + target while
  still) via `CREWBORG_TRACE_GROUPS=decision,action` probe, or read 5 ghost replays from
  /tmp/ab_ghost/cand_wh_episodes. Suspects: post-completion parking, `_pick_target` returning None for
  ghosts in some state, dying with few tasks left (denominator), or a mode ping-pong.

- **Meeting-LLM call failures at 1200-tick meetings (~43% of non-cooldown calls)** (2026-07-02).
  v85's probe: 132 `meeting_llm_decision` vs 100 `llm_call_failed` fallbacks — the 6x-longer
  voting phase (VOTE_TIMER 240→1200, fixed in v84) triples call attempts per meeting and the
  Bedrock sidecar starts failing calls (rate/timeout pressure; v83's short meetings had ZERO
  llm_call_failed). Falls back safely to the A/B-validated deterministic path, so it's lost
  upside, not a correctness risk. Levers: raise `LLM_MIN_CALL_INTERVAL_TICKS` (12 → ~60-100 at
  the new meeting length), batch/skip triggers, or longer `CREWBORG_LLM_TIMEOUT_SECONDS` now
  that the deadline budget is 5x roomier. Related: the pre-existing ~41%-fallback latency item below.

- **League telemetry artifacts are EPHEMERAL (~one round's retention) — investigate + build a harvest**
  (flagged 2026-07-01, James). With all-telemetry uploads now standard (`CREWBORG_TRACE_GROUPS=all`,
  see `user_preferences.md`), policy artifacts from league rounds vanish after roughly one round
  (~10-15 min): v82's 21:10 fetch found artifacts only in the newest round's episodes (6/100); same
  pattern in the v80 pull (17/196, all newest-round). Two threads: (a) find where/why they're
  deleted (Observatory retention? dispatch-runner cleanup?) and whether retention can be extended;
  (b) until then, stand up a per-round artifact harvest (cron/loop every ~10 min pulling the newest
  round's artifacts) so continuous telemetry actually accumulates. Related small fix: the
  `vote_bar` telemetry field lies (logs legacy 0.8; the live crew gate is `WEIGHTS_VOTE_PROBABILITY=0.9`)
  — `crewrift/crewborg/events.py:449`.

- **Meeting-LLM latency / fallback — ~41% of meeting-LLM calls fall back to the silent
  deterministic floor** (held 2026-06-30, from the proactive-chat work). In a 16-game Prime XP
  probe of `crewborg-chat:v1` (LLM on, proactive doctrine), the LLM fired but **~41% of decisions
  hit `domain.meeting_llm_fallback`** — the Bedrock round-trip can't finish inside the in-pod budget
  (¼-core + the 3.0s `CREWBORG_LLM_TIMEOUT_SECONDS`; the diagnosis's H4). Consequence: even with the
  doctrine fixed, ~41% of intended chats/votes never land (warehouse chat 1.92/g vs telemetry intent
  4.5/g). Levers to make the LLM *land* consistently: faster model / shorter serialized context /
  async pre-warm or pipelining of the call / more timeout headroom. **Also re-check
  `VOTE_TIMER_TICKS=240`** (`strategy/meeting/context.py`) — the game's voting period went **6×
  longer** (`coworld-crewrift` b78e400, merged 2026-06-29), so the latency guard's timer model may
  now be stale (crewborg thinks it has far less time than it does, over-triggering the deadline
  fallback). The proactive-chat change itself is done + **merged to main** (`b050768`; the
  `meeting-chat-proactive` branch is gone).
- **Make crewborg's imposter teammate detection BULLETPROOF** (flagged by James, 2026-06-30).
  Diagnosis (warehouse `/tmp/sweep_wh`): crewborg frequently does NOT know its teammate — it
  votes the teammate **21–23%** of imposter casts (top imposters 0%) and **follows** the teammate
  46% of intervals (notsus 26%), both impossible if `teammate_colors` were populated. Root cause:
  teammate identity is a **single brittle capture** from the RoleReveal icons (`types.py` ~L716;
  the `worktree-imposter-kill-to-win` branch widened it to latch the `9500+` reveal-icon range
  on sight, but that still only helps if the reveal frames are SEEN — a connect race that joins
  after RoleReveal never sees them). The whole imposter game (Search/Hunt/opportunity/recon/
  meeting voting + the new parity-push) gates on `teammate_colors`, so a miss is expensive.
  **Make it un-missable:** add inference fallbacks that don't depend on the reveal frame — e.g.
  latch any color we **witness killing or venting** into `teammate_colors` (definitional imposter,
  already tracked by `suspicion.witnessed_imposters`; gate on `self_role=="imposter"`); consider
  process-of-elimination at endgame from the census + known `imposter_count`. Upload a
  **trace-enabled** build (`CREWBORG_TRACE_GROUPS`) and MEASURE the teammate-known rate per game
  (the current branch couldn't, because traces weren't on). Targets to drive to ~0: teammate-vote
  rate, teammate-follow rate. The `worktree-imposter-kill-to-win` branch is merged/deleted — its
  parity-push + latch work is on main (`strategy/meeting/imposter.py:parity_closing_vote_target`);
  start from main (it fixed the *parse/timing* miss but not the *never-saw-the-reveal* miss).

- **Improve crewborg's imposter SOCIAL DECEPTION — make it stronger and fire more often** (flagged
  by James, 2026-06-30). The validated kill→WIN lever is the **meeting**: crewborg under-creates
  suspicion on crew. It skips far more than the top imposters (vote skip-rate ~39% vs notsus 5%),
  chats ~half as much (0.84 vs 1.83 lines/imposter-slot), and only acts on a *real* suspect or an
  *existing* heat pile. The `worktree-imposter-kill-to-win` branch added a narrow first step — a
  parity-closing manufactured vote (`strategy/meeting/imposter.parity_closing_vote_target`, fires
  ONLY at gap==1 with a known teammate; A/B +14.4pp imposter win) — but deception is still mostly
  reactive. **Go further:** (a) **self-defense / counter-deflection** when crewborg itself is the
  heat target (it currently has none — just deflect/bandwagon/skip), which directly attacks the
  64%-of-losses ejection axis; (b) build crew suspicion EARLIER, not only at parity (a notsus-style
  alive-count-scaled vote threshold + active accusations, carefully — voting aggression is lower-
  risk than the reverted *killing* aggression, but still gate it); (c) richer fabricated-evidence
  variety so repeated accusations don't read as a tell; (d) lean on the **meeting LLM** (already
  wired, `CREWBORG_LLM_MEETINGS=1`) for genuinely persuasive chat, and measure whether it out-
  deceives the deterministic path. Reference: notsus `socials.nim`/`votereader.nim` (trust matrix,
  brigade voting, plain-English chat parsing) in `~/coding/coworlds/coworld-crewrift/players/notsus`.
  Validate every step with the pinned-champion 1v1 A/B harness used on the parity-push.

- **Move the Coworld websocket transport/bridge into the player SDK** (flagged by James,
  2026-06-24). Today each player carries its own transport: crewborg's lives in
  `crewrift_lab/crewrift/crewborg/coworld/policy_player.py` (`run_bridge` — connects to the
  engine `/player` ws, drives the per-tick loop), and the SDK's `message_bridge.py` /
  `cogweb_bridge.py` are separate, neither with reconnect. The Coworld transport (Sprite-v1
  binary ws, the runner's `COWORLD_PLAYER_WS_URL` contract, the abrupt-close=game-over
  semantics, and now reconnect) is a *shared* concern: it should be ONE importable module in
  the multiplayer SDK that any Coworld-style player builds on, so future players inherit a
  transport we know works. Scope: factor crewborg's `run_bridge` + the aggressive-reconnect
  logic (added 2026-06-24, see below) into `players.player_sdk`, leaving the game-specific
  scene decode / action encode as injected callbacks. Deferred because it's a cross-cutting
  SDK refactor (the SDK is a pinned git dep — needs an upstream change + relock), distinct
  from the immediate crewborg reconnect fix. The reconnect code added to crewborg now is the
  reference implementation to lift.

- **Investigate turn-end signalling added to Crewrift for game speed** (flagged by James,
  2026-06-24). Crewrift has reportedly added a turn-end / ready signal (a way for a player
  to declare it's done acting this tick) to speed games up. Look into what it is in the
  game source (`~/coding/coworlds/coworld-crewrift`, currently at `42fed21` for arena 0.1.54
  — check newer master), whether crewborg should emit it, and the expected speedup / any
  contract change to the Sprite-v1 transport. Not yet scoped.

- **Drop `CREWBORG_LLM_TRACE_RAW=1` after the first LLM-meetings eval** (added 2026-06-25).
  v47 was uploaded with raw LLM request/response tracing on so the first eval can inspect the
  model's actual decisions/chat. It's verbose (full serialized context per call) — re-upload
  without it once the eval confirms the path works, to keep trace artifacts lean.

- **Commit/PR the ux.link DX feedback left in `metta_7`** (added 2026-06-25). Two feedback
  entries were appended (uncommitted) to `~/coding/metta_checkouts/metta_7/agent-plugins/
  default/skills/ux.link/FEEDBACK.md` (the protected `~/coding/metta` can't be written). Decide
  whether to commit/PR them upstream or discard.

## Done

- **LLM-based meeting chat for crewborg** (flagged 2026-06-25; DONE 2026-06-25, `crewborg:v47`).
  Lit up the dormant LLM meeting brain for the hosted league: Bedrock backend (SDK helpers),
  per-role `memory/{crewmate,imposter}.md` prompts, full LLM chat+vote authority, timeout-derived
  deadline guard. Design `crewrift/crewborg/docs/designs/llm-meetings.md`; details in
  `crewrift_lab/WORKING_CONTEXT.md`. **Nuance vs the original ask:** the original framing was "LLM
  chat *in addition to* the templated path"; what shipped (per James's ux.link-page decision) makes
  the **LLM the primary chat+vote path when enabled**, with the templated/deterministic path as the
  **fallback** (LLM disabled or call fails) — not both running simultaneously. Eval pending before
  any Gate-2 submit.
