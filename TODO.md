# player_labs — deferred tasks

Tasks intentionally parked to handle later. Add items here when you defer something
mid-session; check them back at the start of focused work.

## Open

- **Paintbot: game-pin review** (2026-08-14). Build pin is 0.7.215/`6c7a4c0e`;
  canonical deployed has advanced to 0.7.229 (`bf0bcc22`) — a 14-release gap.
  Contract compatibility has been assumed per the v58-lineage argument since
  v60; sim-rule constants have not been re-derived since 0.7.215. Re-verify
  manifest/config_schema byte-compat and the spray/aim/movement constants,
  then bump PAINTBOT_GAME_REF or document why not.

- **Stencil navigation rework** (deep dive done 2026-08-08; design started
  2026-08-11). The deep-dive questions are answered in
  [`paintbot_lab/docs/reports/stencil-navigation-deep-dive-2026-08-08.md`](paintbot_lab/docs/reports/stencil-navigation-deep-dive-2026-08-08.md);
  James's review comments set the direction — one planner, no beelining, no 8px
  coarsening for movement, dynamic PoIs, goals validated before nav. Rough
  sketch:
  [`paintbot_lab/docs/designs/nav-rework-sketch-2026-08-11.md`](paintbot_lab/docs/designs/nav-rework-sketch-2026-08-11.md).
  Next: settle the sketch's open questions (planner benchmarks first), then the
  full design doc, then the rework itself.

- **Fire-windup micro** (from the 2026-08-11 nav review; explicitly not-now).
  Strafe/aim while fire is winding up to improve accuracy, or pull the trigger
  from cover and step out so exposure time is minimal. Today `resolveAction`
  just freezes movement during windup (`action.nim` fire-windup freeze).

- **Experimentally validate `belief.danger` semantics** (from the 2026-08-11
  nav review). Hypothesis: it actually tracks *believed enemy locations*, not
  danger per se. Keep it as-is until a dedicated experiment settles what it
  measures; its long-term fate (promote into nav costs vs delete) follows from
  that verdict, not from the rework.

- **Re-sync crewborg's player SDK, or accept the split** (found 2026-08-07 during a
  docs audit). `pyproject.toml` now pins coworld-tools `4dd923d` (paintbot needs it —
  earlier revisions clamped Sprite-v1 masks to `0x7f` and dropped Button C), but
  `crewrift_lab/tools/versions.env` `PLAYERS_SDK_REF` is still `e8921a6`. Local `uv`
  and the crewborg **image** therefore run different SDKs, breaking the "local dev and
  the built image run one SDK" invariant both files document. Left diverged on purpose:
  bumping it rebuilds a live player against an untested SDK. Either rebuild + retest
  crewborg at `4dd923d`, or record the split as permanent and drop the invariant.

- **Decide whether to retire beacon from the CTF league** (found 2026-08-07).
  `ctf_lab/` is archived, but that is a repo action only — Coworld CTF is still
  live (`ctf 0.7.203` canonical) and CTF champions are auto-mirrored into the
  Paintbot league (metta `seed.py`, `("paintbot","ctf")`) under the same **James
  Botts** identity, where beacon's offline arena bake is blind on generated maps
  and scored 0.0. If beacon still holds a CTF seat, it keeps competing in
  Paintbot under the same player as Stencil. Confirm its current league standing,
  then either retire it or accept the visible losses. Retiring is a league action
  and a human call, not a repo change.

- **Evaluate v58's barrage evacuation, then decide on shell-level evasion**
  (updated 2026-08-07). The hazard investigation was pinned to 0.7.211 / GV41
  (`coworld-ctf@9dedac0`). **Re-resolved 2026-08-08:** canonical is 0.7.215 /
  still GV41 (`coworld-ctf@6c7a4c0e`), and `paintbot_lab/tools/versions.env` is
  pinned there.
  V58 implements the coarse half of the recon's P1:
  it parses the `grenade barrage depth/rate/start/sat` marker and evacuates to
  the generated map center once `depth > 0`, tracing `barrage_center_ticks`.
  **Still open:** (a) v58 has only a one-episode mechanism probe — it needs a
  campaign-shaped evaluation targeting episodes that actually reach 4:30 before
  it can be judged; (b) individual airborne `grenade air` shells are still NOT
  tracked, so there is no projected-landing evasion through the `clear_grenade`
  seam with the 58px body-hit reach — centering is a positional heuristic, not
  shell awareness; (c) hold the broader P2 doctrine until (a) settles, so the
  effect stays attributable. Note the marker's rate field truncates downward
  (`rate 9` at the true 9.5/s), so use the schedule math for density. The
  supported project CLI combination is now `coworld 0.1.38` with its required
  `softmax-cli 0.26.27`; stop reusing 0.7.208 A/B results for endgame questions.
  Full analysis: `paintbot_lab/docs/recon/paintbot-gv41-hazards-2026-08-07.md`.

- **Expand Paintbot RL replay/expert diversity, then refine temporal state**
  (updated 2026-08-07). A matched 2x2 showed transition-centered sampling alone
  is flat while four-tick causal delta history is informative. The selected
  combined arm improved sealed-GV40 changed-action exact from 1/309 to 12/309
  and changed-component accuracy from 0.7% to 8.8%, but overall exact fell to
  74.7% and change precision to 45.2%. Keep history; do not deploy this seed
  checkpoint. Add substantially more high-performing replay and policy
  diversity, then compare compact deltas with short full self/nearby-state
  history and report movement/turn/fire/grenade changes separately. See
  `paintbot_lab/docs/reports/rl-transition-temporal-2x2-2026-08-07.md`.
  **In progress:** all 327,188 replay downloads and exhaustive preprocessing are
  complete. The first 250k-unique x 3-epoch arm reached a 59.17% teacher-forced
  exact-action proxy on the frozen 10k balanced sealed test (27.19% changed,
  91.14% held). That evaluator did not feed generated slots back into the model,
  so it is not autoregressive; corrected autoregressive evaluation is now the
  only final-gate metric. Validation diagnosis rejected decoder calibration and
  localized the main error to movement transitions. A matched-compute 750k-
  unique x 1-epoch arm is running
  under `training-v2-diversity`; it stops after validation and keeps the sealed
  test closed. If diversity is flat, compare compact deltas against short full
  self/nearby snapshots or greater adaptation capacity. A validation-only
  residual press/release screen is queued behind diversity after validation
  logits showed 71.85% of changed-movement errors simply repeat the prior
  movement. It runs one schedule-matched epoch and promotes only on a
  preregistered exact/movement/held gate. If rejected, a spatial-semantics
  screen adds egocentric bearing and self-width-normalized range to the nearest
  16 entities under the same staged gate. Report:
  `paintbot_lab/docs/reports/rl-exhaustive-baseline-2026-08-14.md`.

- **Make Stencil squads roster-aware under campaign 7+7+1+1 seating** (found
  2026-08-06). Current `squadTable` partitions two-team identities by parity,
  which matched the disabled ladder's equal four-agent entrant blocks. Normal
  campaign invasions instead give each captain seven team seats and its ally
  only the team's second seat. Static parity can therefore wait on the foreign
  ally or omit owned Stencil seats. Preserve v52 behavior during the GV40 aim
  test; redesign membership from observed Stencil chat/presence before the next
  squad iteration.

- **Redesign Paintbot fixed-squad reconnection over proximity chat** (deferred
  2026-08-06). v51 made same-epoch consensus conflict-free, but giant-map live
  drift lasted 1,226 ticks; v52's static timeout rendezvous improved that to
  555 ticks, and v53's continuously refreshed target regressed to 967 ticks.
  Before another implementation, specify how separated living members discover
  one another, rendezvous, and rejoin without a designated leader, plus a
  preregistered concurrent-live drift bound. Start from
  `paintbot_lab/docs/reports/stencil-squad-consensus-retrospective-2026-08-06.md`;
  do not resume v53 target tuning.

- **Generalize event-warehouse outcomes beyond red/blue** (found 2026-08-04).
  `paintbot_lab/tools/event_warehouse.py` (moved from ctf_lab) projects only `red_score`, `blue_score`,
  and a red/blue `winner`; on four-team Paintbot it labels green/yellow wins as
  draws. Add all-team score/win projection or a game-agnostic result table.
  Until then, compute Paintbot W/D/L directly from each `results.json` team/win
  vector.

- **Expose player muster in Paintbot's Sprite-v1 init contract** (found
  2026-08-04). The current marker states teams and map dimensions but not
  `num_agents`/seats per team. Current campaign `1v1` means eight seats per
  team, while `2v2`/`4ffa` mean four per entrant and historical `4ffa8` means
  eight; `mapSize` is not a reliable proxy and is currently unset on every
  campaign cell. Stencil grows a conservative roster estimate from observed
  identity badges, but low-index seats cannot know muster until they see an
  epsilon-or-higher identity. Add muster to the owner game's init marker, then
  consume it directly and delete the estimate.

- **REFUTED-PREMISE 2026-07-22 (Thread 9): imposter co-location — do NOT build the spread nudge.**
  Re-measured on 200 fresh v107/v110 eps (`/tmp/wh_anchor_base_v110`; scripts `/tmp/t9_spread/`).
  The 32%-field-worst figure does not reproduce: crewborg-imposter's co-imposter share of proximity
  intervals is **13.7% — field-BEST among the 7 crewborg-family policies** (field 15.0%, z=-1.08
  p=0.28; per-seat Mann-Whitney p=0.33; following-interval share 10.2%, 2nd-lowest, only notsus-family
  near). And the consequence claim fails too: per-episode imposter-pair co-location has **no
  correlation with imposter win (r=0.017, p=0.82)** and the ejection trend is the WRONG direction for
  the tell theory (high-co-location tercile has FEWER imposter ejections, spearman r=-0.14 p=0.06;
  imposter win by co-location tercile 85/74/83%). The 32% was measured ~v101 (2026-07-07) with a
  different metric window/field; on today's data there is nothing to fix and repulsion would risk the
  hunt for zero expected gain. Original item kept below for context.
  <details><summary>Original item (2026-07-07, superseded)</summary>
  Belief trace refuted the "teammate detection is broken" theory (v101: 0/24 detection failures, teammate
  known every game — see [[crewrift-imposter-kill-lever]]). BUT the replay shows crewborg-imposter
  near/following its co-imposter 32% of intervals (field-worst), and since it correctly KNOWS the
  teammate, that's **incidental co-location** — two imposters clustering wastes coverage and reads as
  a tell to crew (two players always together). Not suspected to be a big loss driver (James), so
  LATER. Fix direction: an imposter-side "spread from known teammate" nudge in movement/search
  (repel from `teammate_colors` positions), analogous to crew dispersion. The teammate identity is
  reliable (`teammate_colors`), so the signal to act on is already there.</details>

- **Finish wowborg's hosted retest on the corrected successor to accelerated-wow 0.1.127** (2026-07-31).
  PR #7394 published `accelerated-wow:0.1.127`
  (`cow_be2dfbf4-ad71-40a3-b6e1-9dfe21a2b586`) from frozen source `59497e551`, which
  contains PR #7391 commit `3203b9c766aa892f9db449c999a96767dffa2991`. Its certification
  remained `certifying` with no transcript through 20:27 UTC. Direct hosted request
  `xreq_15ac079a-2f19-4b3c-8ac1-17f4dddfe4da` was admitted while certification was still
  running, but episode `ereq_31ac43dd-788b-483d-91b0-72288fb5784e` failed before `/env`
  hello: WebSocket 1011 `environment session ended before hello`; zero actions, zero progress
  reports, and no replay/results were produced. A second fresh request
  (`xreq_6a93f6a2-174c-4311-b46b-597c715b7357`, episode
  `ereq_5fd1d140-dfe9-4c66-bc1b-8db65a61b446`) reproduced the identical pre-hello 1011
  after an 8.4-second `/env` wait, again with zero observations/actions and no replay; 0.1.127
  was still non-canonical and `certifying`. An exact-image local reproduction then proved v59 is
  contract-incompatible with 0.1.127: it receives hello, but rejects the first AgentFrame with 128
  `extra_forbidden` validation errors because 0.1.127 added strict frame fields without a negotiated
  contract revision. Wowborg v60 (`99a2c257-bbad-4bb2-9eb5-1eefa8920f06`) was rebuilt and
  uploaded against the exact 0.1.127 SDK. A complete exact-image local episode passed with score 1.0,
  replay, 312 observations / 311 intents, and 1,391.080 trajectory yards. Movement packets fell
  4,097 -> 1,376 versus the hosted v59 baseline, with forward starts 239 -> 22 and stops 243 -> 25,
  proving the continuation fix locally. Its hosted request
  (`xreq_d2255259-ee1b-4647-bc71-2ea93133ab54`) never dispatched because 0.1.127 certification
  ultimately failed the smoke episode after 3,600 seconds (`ereq_8f12b169-dff2-4c73-b9ef-f316f50e805b`).
  Once a corrected Coworld certifies, rebuild v60 only if that successor changes the SDK, run one
  `custom-fresh-start-10x` episode, stream artifacts, and compare the replay
  against baseline episode `ereq_422085f1-9ec7-4554-b2ba-9942947e5dc2`: 4,097 movement
  packets, 239 forward starts, 243 forward stops, 326 turn starts, 356 turn stops, 2,907
  heartbeats, and 1,309.923 yards displacement. Report the new request/episode/Coworld IDs
  and before/after counts. Spell 7355 cooldown spam is a separate wowborg issue.

- **Project large CTF snapshot fields during warehouse ingestion (found 2026-07-30).**
  A 60-episode `BEACON_DIAG_EVERY_TICKS=1` build reached 12 GB and about
  9.5 GB RSS because every snapshot stores the full danger grid in `data_json`.
  Add an ingestion projection/side table or omit `danger.rows` from the general
  trace table while retaining the small decision fields. Until then, stream
  cumulative activation fields directly from telemetry ZIPs for full-tick
  batches.

- **Fix CTF A/B team-outcome significance units (found 2026-07-30).**
  `ctf-ab` repeats one episode's team win/loss across all eight Beacon result
  rows, then treats those 80 rows as independent. In the v58 Nancy replication
  it reported `p=0.002` for 9/10 → 7/10, while the correct episode-level
  two-sided Fisher test is `p=0.582`. Team outcomes must use one record per
  episode; per-seat kills/deaths can remain seat-level.

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

- **DONE (2026-07-22, Thread 10) — Meeting-LLM call failures at 1200-tick meetings** (2026-07-02).
  Re-measured on the v110 A/B arms (199 seats, 2084 calls): 74.5% call-fail, but 1536/1553 errors
  are the SHARED Bedrock daily-token-pool 429 — failure is uniform across triggers and NOT
  pacing-correlated (fail/success inter-call intervals identical), so the TODO's interval/trigger
  levers were refuted by the data; retries are the coverage mechanism (45/561 meetings got their
  first decision only at call 4-5). The real self-waste: the 3.0s timeout client-aborted 40% of
  ultimately-successful calls (latency median 2.8s/p90 4.0s) into token-double-spending SDK
  retries. SHIPPED: meeting timeout 3.0→6.0s (`CREWBORG_LLM_MEETING_TIMEOUT_SECONDS`) +
  `CREWBORG_LLM_MIN_CALL_INTERVAL_TICKS` knob (default 120 unchanged). Probe
  `crewborg-llmcadence:v1` (xreq_f5e7a285, 100 eps) — all pre-registered criteria pass: abort-retry
  waste eliminated (0 >6.05s, 0 timeout fails), coverage flat vs contemporaneous arms, fails/meeting
  lowest of the night, vote_timeouts 0. Rides into the next crewborg version. Residual 429s are
  fleet-level pool contention — only cheaper tokens/call or a bigger pool helps. Design + verdict:
  `crewrift_lab/docs/designs/2026-07-21-meeting-llm-cadence-design.md`. The ~41%-fallback latency
  item below is largely the same root cause (throttling + aborts), partially addressed here.

- **Small fix: the `vote_bar` telemetry field lies** (split out of the resolved retention item,
  2026-07-21): logs legacy 0.8; the live crew gate is `WEIGHTS_VOTE_PROBABILITY=0.9` —
  `crewrift/crewborg/events.py:449`.

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

- **Paintbot RL mettabox1 canary, sweep, and full training (DONE 2026-08-07).**
  Provisioned a locked CUDA 12.8/BF16 environment on the RTX 4090, passed two
  canaries, swept 1e-4/2e-4/4e-4, selected the full three-epoch 2e-4 arm, and
  evaluated the sealed GV40 split. The artifact is archived locally and
  remotely with matching SHA-256. It is a pipeline control, not a live-policy
  candidate, because it did not beat previous-mask persistence. Report:
  `paintbot_lab/docs/reports/rl-mettabox1-sft-2026-08-07.md`.

- **Paintbot Sprite-v1 `sprites off` landed upstream and deployed (2026-08-03).**
  coworld-ctf PR #219 is in canonical Paintbot 0.7.180 at source `052b058`.
  The self-play harness now resolves that canonical version before every batch
  and opts stencil into `0x87`, adopting the optimization without a private
  fork. A fresh giant-board benchmark remains useful when optimization work
  targets 4ffa8.

- **League telemetry artifacts "ephemeral" — investigated + harvest built** (flagged 2026-07-01;
  DONE 2026-07-21). Verdict: artifacts are **durable, not deleted** — the July-1 "vanishing"
  (v82 6/100, v80 17/196, newest-round-only) was a read-path/auth failure during metta's
  artifact-route churn (v1 TEAM_AUTH routes + opt-in elevation #17028 + v2 migration #17413/#17466,
  v1 deleted #17603); the very same v80/v82 episodes still serve their zips 20 days later, and
  metta has no artifact TTL (only the secrets bucket has lifecycle expiry —
  `devops/tf/observatory/policy-secrets.tf:52`). No platform ask needed. Built anyway (for
  continuous local accumulation): `crewrift_lab/tools/harvest_artifacts.py` — idempotent,
  lockfile-guarded, cron-able (~10 min) puller of crewborg's league `policy_artifact_*.zip` into
  gitignored `crewrift_lab/telemetry_harvest/`. How-to + retention findings:
  `crewrift_lab/docs/telemetry-harvest.md`. Crontab not installed — line is in the doc/script header.

- **CTF item capability 4: tactical grenade selection (DONE 2026-07-30).**
  `beacon:v58` (`8fcbbb68-949d-48cd-8c66-11cbd1a9b660`) now prioritizes
  wall-blocked enemies and tight groups, permits only narrow single-target
  finishes, predicts teammate positions for a safety veto, and never releases
  while carrying the flag. Against current `deltashot:v5`, v57 and v58 both
  went 10-0 with 239 kills; v58's 43 ground-truth throws produced 35 enemy hits,
  70 enemy HP removed, 9 multi-target impacts, and 3 friendly hits versus
  v57's 45 / 33 / 66 / 7 / 4. Mechanism-positive non-regression, not a proven
  outcome improvement. Uploaded inertly; not submitted.

- **Fix `rotate_lessons.sh` re-archiving UNCHANGED buffers under new timestamps** (found 2026-07-13
  lessons sweep — 3 labs had byte-identical duplicate archives inflating the recurrence signal;
  DONE 2026-07-14). All five labs' hooks now md5-compare the buffer against every existing archive
  (incl. `reviewed/`) and skip re-archiving byte-identical restores (e.g. from a git sync), with a
  distinct additionalContext message. Verified end-to-end in a scratch repo: new content archives,
  identical content skips, resume never rotates. Remaining related history (conflict-marker
  archiving cue_n_woo 2026-07-05; stale-branch drop crewrift 2026-06-15) — no repro since, watch.

- **LLM-based meeting chat for crewborg** (flagged 2026-06-25; DONE 2026-06-25, `crewborg:v47`).
  Lit up the dormant LLM meeting brain for the hosted league: Bedrock backend (SDK helpers),
  per-role `memory/{crewmate,imposter}.md` prompts, full LLM chat+vote authority, timeout-derived
  deadline guard. Design `crewrift/crewborg/docs/designs/llm-meetings.md`; details in
  `crewrift_lab/WORKING_CONTEXT.md`. **Nuance vs the original ask:** the original framing was "LLM
  chat *in addition to* the templated path"; what shipped (per James's ux.link-page decision) makes
  the **LLM the primary chat+vote path when enabled**, with the templated/deterministic path as the
  **fallback** (LLM disabled or call fails) — not both running simultaneously. Eval pending before
  any Gate-2 submit.
