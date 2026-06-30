# player_labs — deferred tasks

Tasks intentionally parked to handle later. Add items here when you defer something
mid-session; check them back at the start of focused work.

## Open

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
  fallback). The proactive-chat change itself is done + committed on branch `meeting-chat-proactive`.
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
  rate, teammate-follow rate. Branch `worktree-imposter-kill-to-win` is the starting point (it
  fixed the *parse/timing* miss but not the *never-saw-the-reveal* miss).

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
