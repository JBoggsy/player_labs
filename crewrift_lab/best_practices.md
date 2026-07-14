# Best practices — optimizing crewborg

Battle-tested disciplines for the **evaluate → diagnose → improve** loop, distilled from many
optimization campaigns. **Part 1** is game-agnostic (true of any Coworld player); **Part 2** is
Crewrift-specific (the failure modes of *this* game). Treat them as your defaults, and **warn the
human if a request would contravene one** before proceeding (then do what they decide).

> New here? Read these once, then keep them as a reference. The 🚩-marked items are the ones that
> get violated most — re-read those before you write a "why" or interpret a result.

---

## The non-negotiables (the ones that actually bite)

1. **🚩 No causal claim without the falsifying query.** Every "because / since / due to" in your
   own draft is an un-run query, not a conclusion — and it's wrong about half the time, often
   *backwards*. Before writing a "why": (a) is the effect even real (effect size + a significance
   test)? (b) name what your mechanism *and the competing one* would make observable; (c) run the
   query that separates them and report it, refutations included.
2. **🚩 Decompose by role before judging.** Crewmate and imposter are two different policies; the
   aggregate headline routinely hides one role being broken.
3. **🚩 Meeting ticks are NOT idle time.** A report or button starts a ~1272-tick meeting that
   teleports everyone home (a body/unknown meeting — **not** the emergency button — resets imposter
   kill cooldowns) — exclude it from every idle/latency/ready/gap metric (see Part 2).
4. **🚩 `-100` means DISCONNECT/CRASH, not ejection.** It's an ops failure; filter it out before
   any rate. Getting voted out carries *no* score signal at all — you must read the logs for it.
5. **Upload freely; submit rarely.** Uploading a version is routine and touches no league. Submitting
   is the irreversible, champion-making action — only on a demonstrably-better player + human go-ahead.
   *Not* submitting is your rollback.
6. **Speed first — iterations per day is the KPI.** Write the change fast, rebuild, upload
   *immediately* — no smoke test, no pre-upload gate, no test scaffolding. The next experience
   request catches breakage *and* measures gameplay; a broken upload costs one free eval round.
   Rigor is for *reading* results (items 1–4), not for shipping code. (Full version:
   [`../best_practices.md`](../best_practices.md).)

## Working with the human

- **If you're re-instructed to do the same thing more than once, record it as a preference.** A
  standing instruction — or a correction the human keeps making — belongs in
  [`user_preferences.md`](user_preferences.md); write it there so they never have to say it a third
  time and it persists across sessions. Don't make the human be your memory.

---

# Part 1 — General (game-agnostic)

## Measurement — know whether a change actually helped

- **Evaluate on a batch, never a single game.** Within-game variance (std can exceed the mean),
  role/seat asymmetry, and opponent dependence each swamp one game.
- **Decompose before judging; the aggregate headline is a trap.** Cut by **role** (the most
  important cut), by **opponent/matchup** (pairwise), and by **behavioral sub-metrics** (wins, mean
  *and* median, action counters). Their disagreement localizes *why*.
- **Apply statistical rigor.** Report effect sizes (not just means), run a mean-based *and* a
  rank-based test, apply multiple-comparison correction, and pool matched batches for power. A
  leaderboard that looks cleanly ranked is mostly noise until corrected.
- **🚩 No causal claim without the falsifying query** (see the non-negotiables). This is the
  single most-violated discipline. Observable preconditions exist for *every* mechanism, and the
  query to check them is almost always one cheap join away — it repeatedly overturns the story.
  Watch your own language: borrowed metaphors ("snowball", "momentum") smuggle in a model the game
  doesn't have.
- **Normalize every stat by seat-holding.** When a policy occupies a different number of roster
  seats than others, report **per-seat-game rates, never raw totals** (4 of 8 seats ⇒ ~4× the
  totals for the same skill). Two traps: (1) counting non-events as events (an abstain logged as
  "chat") inflates volume — exclude first; (2) **team-outcome metrics carry a composition confound
  that per-seat normalization does NOT remove** — isolating individual contribution to a team
  result needs a controlled design (vary one seat, hold the rest fixed). Individual stats
  (kills, tasks) are clean per-seat; team stats (win) are not.
- **Experience requests are your primary eval — they aren't scarce.** They run many episodes in
  parallel on Softmax infra and are currently free; use them liberally, just **target them to the
  question** (matched roles, the specific opponents you struggle against) and harvest async.
- **Pin an explicit identical roster for any A/B — never `top_n`/`random` seats.** Auto-selected
  seats drift between arms (one partner swing alone moved win rate 87%→37%) and can seat **your own
  champion** as opponent/partner; the selectors have also repeatedly 500'd (statement timeout) and
  their semantics keep changing (once-per-request → per-episode redraw → commissioner-leaderboard
  ranking). Make every seat an explicit `{"player": {"policy_ref": "name:vN"}}` and verify the
  seating in the request readback. `random` seats are for tournament-style field reads only.
- **Read an A/B only from complete, verified data.** Before analysis, check the on-disk episode
  count matches `episode_count` and both arms are DONE — partial/mid-run pulls have fabricated a
  fake +20.8pp delta and mis-read a finished A/B as pending (`fetch_artifacts` defaults `-n 10`;
  `--watch` fetchers die silently). Re-pull with `--force` after arms complete. Conversely, a
  directional result on a **confirmed mechanism** is worth powering up, not discarding (+5.9pp
  p=0.20 at n=240 resolved to +14.4pp p<1e-9 at n≈955).
- **Evaluate a fix in the SAME conditions the problem was diagnosed in, and judge against the
  window's field par.** A pinned-favorable-seat config once masked a 30pp imposter gap ("inconclusive"
  ≠ "neutral" — a test that can't see the effect says nothing); self-play validation doesn't
  transfer to the league (80% vs 39% vote accuracy, same code). And the field itself moves: compare
  a version to the SAME-window field average, not the previous version's raw number (v89's "collapse"
  to 24% crew was exactly field par), and re-check window-conditioned lever verdicts after the field
  or game version pivots — several refuted/confirmed levers flipped when the field changed.
- **Cap LLM-on evals at ~400 concurrent episodes.** The hosted Bedrock (Haiku) capacity is a
  **shared pool on the tournament account** (`583928386201`), not our per-account quota (ours is
  714M tokens/day, ~untouched). Under heavy concurrent load it throttles with `429 "Too many tokens
  per day"`. Binary search (2026-07-09): 100/200/400 concurrent all held the meeting LLM ≥60%
  decision rate with **zero 429s**; **800 collapsed to ~52% with 34 throttles**. So run big LLM-on
  A/Bs in **chunks of ≤400 running at once** (e.g. fire 4×100, let them drain, then the next 4) —
  firing 6–8×100 simultaneously self-throttles the pool and silently starves the LLM.
- **🚩 But for MATCHED A/Bs, don't even fire 4×100 together — pace to ONE ~100-ep request at a time.**
  A *second*, distinct contention limit bites well below the Bedrock ceiling: firing 4×100=400
  episodes simultaneously (a 2-arm A/B) made **opponent pods fail to connect** — in the v106-vs-v105
  A/B, **76% of episodes were dead games** (an imposter seat connect-timed-out → no imposters → the
  game sat in Lobby → everyone scored 0), vs **0% dead games** when the same policy ran as a single
  100-ep request. So: fire each arm as a **separate 100-ep request, drained before the next**, not
  all at once. Diagnostic: a spike in all-zero / "stuck-in-Lobby" episodes = platform **connect**
  contention, not a policy bug — check the `connect_timeout` array across ALL 8 seats (it lands on
  the *opponents*, and `connect_timeout rate == dead-game rate == stuck rate`) before blaming crewborg.
- **Drop dead connect-timeout games at the GAME level, never per-seat.** A game where any seat
  connect/disconnect-timed-out is a dead game (auto-scored, no real play); a per-seat filter keeps
  the surviving seats and counts the auto-result as real (crew win rate read 20% contaminated vs
  33.7% clean — a 14pp error). Drop the whole episode if any seat has a timeout, then verify
  "intact" = the full expected roster actually played. Also note: heavy/LLM images cold-start slowly
  (Bedrock + spaCy + seed loads) and miss tightened connect deadlines — crewborg's own
  connect-timeout rate hit ~24% on coworld 0.4.42, i.e. startup latency can be a bigger standing
  lever than any skill change.
- **Gate any LLM-behaviour eval on the LLM actually firing.** Before trusting an A/B of a
  prompt/doctrine change, measure the `domain.meeting_llm_decision` vs `domain.meeting_llm_fallback`
  ratio in crewborg's telemetry. If it's low (throttled/timed-out), the A/B silently tested only the
  deterministic fallback path — the LLM change was never exercised. Target ≥60%. Also check the
  ratio (and `llm_call_failed`/429 counts) **per arm**: even matched same-window arms drain the
  shared daily quota against each other asymmetrically (observed 78% vs 25% failure between
  concurrent arms) — note the bias direction relative to your verdict before trusting a delta.
- **Don't fetch replays for large eval batches — `telemetry.jsonl` is enough.** The LLM-rate /
  ejection / kill / vote measurements only need the policy `telemetry.jsonl` inside
  `artifacts/policy_artifact_*.zip`; the multi-MB `replay.json` is only for warehouse builds /
  single-episode deep-dives. Fetch `--no-replay` for batch measurement and delete each batch's
  episode dir right after extracting its numbers — two 1200-ep A/Bs fetched WITH replays filled the
  disk (30GB) and deadlocked the session (ENOSPC). Reserve replays for the qualitative pass on a
  handful of episodes.
- **Local runs are a debugging tool — not a gate, never comparative.** Don't run locally before
  uploading; upload and let the eval speak. Drop to a local run only when an eval shows the
  artifact can't connect/play. You generally can't run other users' policies locally anyway, so
  all competitive judgment comes from experience requests.

## Diagnosis — from "it lost" to "it does X in situation Y because Z"

- **You can't debug an outcome, only a trace.** Pivot immediately from the result to the player's
  internal reasoning stream (see [`crewrift/crewborg/docs/trace-logs.md`](crewrift/crewborg/docs/trace-logs.md)).
- **Observability is something you build, not something you're given** — reason traces (mode /
  options / choice + a *why*), belief snapshots, tick-keyed lines, tiered verbosity, replays. If you
  can't see the behavior you can't improve it; building the instrument often precedes the fix.
- **Triage by failure class; chase the surprise.** Aggregate, then sample the worst case per class.
  The most informative game is the one that "should have been a win."
- **Variance carries the mechanism — and the lucky wins are findings too.** Look at *which* episodes
  moved and what they share; a change that helps one cluster and hurts another points at the gating
  fix, and positive outliers are a hypothesis source — find the mechanism and make it fire on purpose.
- **Don't optimize the obvious intermediate metric.** Confirm it maps to the objective first;
  counterintuitive correlations (dying *more* while scoring *more*) are signal, not noise.
- **Name the layer first** — perception / belief / strategy / execution — because the layer
  determines where the fix goes. Keep **operations** failures (can't connect/build) strictly
  separate from **behavior** failures (plays badly).
- **Ground truth beats inference.** When the player's view or the tooling could be lying, verify
  against the game's authoritative source/logs before building on it.

## Hypothesis discipline — make a diagnosis actionable

- **Name a specific mechanism and predict an observable effect.** Pin it to a rule/timer/threshold
  and the trace line that proves it; propose a scoped change to *that* mechanism only.
- **Plausibility is not evidence.** "This should obviously help" is a reason to *test*, never to
  assert or ship — roughly half of "obviously good" ideas regress.
- **Pre-register the expected effect**, ideally as a test written *before* the run — the test is the
  hypothesis made falsifiable.
- **"Capability exists" ≠ "capability is used."** A signal the policy never consults is a silent
  no-op; verify it's consumed, not just emitted.
- **Validate from the trace, not the scoreboard.** A win can be noise; confirm the intended
  mechanism actually fired.

## Provenance — never trust an unverified green result

- **Change one component at a time** so the next evaluation is attributable.
- **Rebuild after every change** — a stale artifact reads as "the change did nothing."
- **Upload freely; submit rarely** (see the non-negotiables). *Not* submitting is your rollback.
- **Keep a version log** (`crewrift/crewborg/version_log.md`) mapping each uploaded version to the changes
  it carries, so you always know what each version is testing. **Write the entry in the same breath
  as the upload** — parallel sessions have left gaps, and a submitting session must confirm the log
  covers the version being submitted (or flag the gap) before submitting.
- **Parallel sessions clobber shared build/upload identity.** The Docker tag `players-crewborg:dev`
  is host-global and `--name crewborg` uploads interleave version numbers — a sibling worktree's
  build silently overwrites the bits you then upload (observed with 3 concurrent agents). When
  fanning out: build each candidate to a **unique `--tag`**, upload under a **unique `--name`**
  (`crewborg-<slug>`), and verify the image actually carries your change
  (`docker run … grep`) before uploading.
- **Env flags bake at UPLOAD, and same-image uploads dedup by digest.** `--secret-env` is fixed per
  policy version (not settable per experience request), and uploading the same image N times with
  different secret-env collapses to ONE version. To A/B a config flag you need **distinct images** —
  thin `FROM <base>` + `ENV X=…` layers, one per arm — and verify the bake inside the image before
  launching. Bake the **trace env on the candidate** for any behaviour-path A/B, or you can't
  confirm the new path ever fired.
- **Check unmerged branches and current main before re-diagnosing or building.** Finished evidence
  hides on unmerged worktree branches (`git branch --no-merged` — a refuted lever was nearly
  re-proposed from scratch), and a diagnosis measured on a stale base can prescribe a fix main
  already shipped (cost: a full build+A/B cycle). `git merge-base HEAD main` + fast-forward before
  reading code or cutting an A/B baseline; and **re-verify any old warehouse-diagnosed lever against
  fresh data before building on it** — two "mechanistic levers" (the wanderer bug, teammate
  detection) evaporated on re-verification.
- **Use explicit positive/negative controls** — a silent fallback can run a reference player, not
  yours; a verified A/B beats a source review.
- Stay alert to **local↔live drift**, **stale rotating IDs / docs**, **over-reading a small batch**,
  and **position-based score joins** — the classic looked-like-success failures.

---

# Part 2 — Crewrift-specific

These layer on Part 1; they're the failure modes of *this* game. Add to this part as we learn more.

## Scoring (read before interpreting results)

- **🚩 `-100` means DISCONNECT/CRASH only — NOT ejection.** It's an ops failure (the container
  disconnected or crashed). Filter these out before computing any rate. Do **not** read `-100` as
  "got voted out."
- **Getting EJECTED (voted out) carries NO points penalty — there is no score signal for it at
  all.** A loss after ejection looks identical in `results.json` to any other loss, so you
  **cannot** infer the ejection rate from scores. To know whether/when crewborg was ejected you
  **must read the logs/replay** (the meeting outcome / `player_died`-by-vote / `expand_replay`
  ejected-by-vote). Always check the logs, not the score, for ejection.
- **Cleanest ejection signal for an IMPOSTER: it ended dead.** An imposter cannot be killed (only
  crew can), so an imposter dead at game end was **necessarily ejected by vote** — so *imposter
  ejection rate = fraction of imposter games the policy ended dead*. (Crew deaths are ambiguous —
  killed vs ejected — and need the vote events.)
- **🚩 Meeting/voting ticks are NOT idle time — exclude them from EVERY idle / latency / ready / gap
  metric.** A report or button press starts a meeting: `MeetingCallTicks` (72) + `VoteTimerTicks`
  (1200) ≈ ~1272 ticks during which nobody moves or kills, everyone is teleported home, and a
  body/unknown meeting **resets imposter kill cooldowns**. **Two layers, both required:** (1) filter
  `phase == 'Playing'` to drop meeting *samples*; (2) **never subtract a raw tick delta across a
  Playing-filtered series** — the delta between two consecutive Playing samples still spans any
  meeting in between (~1272 ticks). Instead **count Playing+ready samples × snapshot interval**, or
  bound the window at the next meeting. A ready→kill window **ends at the next body/unknown meeting**
  (which resets the cooldown — the emergency **button** no longer does; `buttonResetsKillCooldowns=false`,
  see [`docs/crewrift-gameplay.md`](docs/crewrift-gameplay.md)). This has bitten the analysis
  repeatedly ("~2000-tick inter-kill gap" and "2077-tick wander" were both *meetings*, not hunting).

## Evaluation

- **Crewmate and imposter are two different policies — never judge them merged.** The same code in
  the two roles has different objectives, different action sets (kill/vent only exist for imposters),
  and different score structures. An aggregate win-rate routinely hides one role being broken.
  **Always decompose eval by role**, and target experience requests at matched roles when a change
  was role-specific. Force your policy's role by pinning its roster `slot` +
  `game_config_overrides.slots` (an array of `{"role": …}` objects, not bare strings — the common
  mistake; see [`docs/crewrift-gameplay.md`](docs/crewrift-gameplay.md)).

## Reading games (replays & logs)

- **Investigate the game, don't infer from the scoreboard** — pivot from the result to what
  *happened* (the objective timeline) and *why* (the policy's logs).
- **Go batch-first, then drill.** Start with the distribution across the whole batch; open
  individual episodes only once it flags the interesting ones (the should-have-been-wins). Match the
  tool to the altitude — each tool's own docs cover how to run it (see the tool library):
  - *Triage a batch* → the **`crewrift-survey`** skill (role-decomposed stats; flags interesting episodes).
  - *Cross-episode behavioral data ("all the data")* → a **`crewrift-event-warehouse`** (queryable event store, re-keyed by policy/role).
  - *One game's objective ground truth* → **`expand_replay`** (the single-game primitive the others build on).
- **Policy logs are version-independent — the primary source for hosted/league episodes** (no replay
  or version match needed; crewborg writes a rich per-tick JSON trace).
- **crewborg's trace lives in `artifacts/policy_artifact_<slot>.zip` → `telemetry.jsonl`, NOT the
  per-agent log.** Hosted `policy_agent_N.log` is typically one line ("game over"); the per-tick
  decision/vote/suspicion trace is only in the artifact zip. Beware fetch flags: `--no-logs` has
  (twice) silently gated the artifact-zip download too — after any filtered fetch, verify the zips
  actually landed before concluding "no telemetry."
- **League episodes are a disjoint population — `coworld episodes -p crewborg` returns `[]`.**
  Discover them via the policy-versions → episodes path (the `coworld-episode-artifacts` skill);
  never read `[]` as "no episodes." For outcome-level reads (win rates, role splits), skip artifact
  fetching entirely: `POST /v2/episodes/search` returns per-seat `results` inline for any policy
  version — it's also a cross-user "has anyone already run this config" check. `/jobs/*` artifact
  routes need `--elevated` (opt-in elevation model). And **league telemetry artifacts are ephemeral
  (~one round's retention)** — harvest every round or lose them.
- **Confirm what's in a log before querying it** (crewborg's trace level varies — an empty `select`
  can mean "wrong level," not "didn't happen"), and **🚩 attribute by `policy_version_id`, never by
  display name or list position.** Your own champion gets drawn as an opponent under the same
  "James Boggs" name, one policy can hold two seats ("Name (2)"), and pooled warehouses mis-attribute
  per-version behavior unless split by version UUID — all three have produced phantom findings.
  Map seat→policy from `episode.json` participants.

## Perception & the scene contract

- **The game owns the scene vocabulary; re-derive from source when in doubt.** The Sprite-v1
  object-id ranges, labels, and camera offsets (in [`docs/crewrift-protocol.md`](docs/crewrift-protocol.md) and
  `crewrift/crewborg/perception/constants.py`) are verified against `Metta-AI/coworld-crewrift`:
  `src/crewrift/{sim,global}.nim`, but they are the **game's to change**. If perception misbehaves
  after a game bump, suspect drift and check the Nim source before trusting the decoder (see
  [`crewrift/crewborg/docs/perception-and-belief.md`](crewrift/crewborg/docs/perception-and-belief.md)).
- **Game versions bump frequently and silently — re-verify tooling and re-baseline behavior after
  every bump.** Constants are variant- AND version-specific (`killCooldownTicks` 500 vs 800,
  `voteTimerTicks` 240→1200) and config-overridable: the authoritative value is the episode's baked
  `game_config` / the deployed ref's sim source, never a doc or a hardcoded constant. For the
  expander: don't assume a bump changed the sim (0.4.3–0.4.29 were sim-identical) or that it didn't
  (0.4.21→0.4.28 changed vote timing and collapsed the vote rate with zero crewborg changes; 0.4.42
  stopped zlib-compressing replays) — **test the existing expander binary empirically on several
  fresh replays including a button game** and trust the per-episode `trace_warning` count, not one
  exit-0 smoke. Fitted-threshold behaviors (vote gates, timing models) need re-measurement after
  any game bump.
- **Self-ID and role/teammate latching must come from authoritative one-shot sources, never
  re-derived fuzzy estimates.** The connection slot IS the colour index (`?slot=` in the WS URL —
  zero-variance ground truth); role/teammate identity comes from the IMPS reveal text (with its
  discriminating gate — dropping it caused crew to latch "imposter" and wear three masks at once:
  0 tasks, 0 votes, 0 chat); `self_alive` needs the meeting-census backstop (HUD icons can skip a
  phase transition). **Never mutate a source-of-truth set against a drifting estimate** — a per-tick
  `teammate_colors.discard(self_color)` deleted the real teammate and cratered kills ~10σ. Exclude
  self at ingest, one-shot, against the authoritative read. And when one version shows several weird
  symptoms at once, look for ONE upstream belief bug before filing three; any build lineage forked
  before a critical belief fix must be checked for that fix before submitting.

## Idling is dangerous — every idle needs an escape

- **Standing still is almost always the wrong move**, and it is where crewborg's worst bugs hide. Every
  multi-thousand-tick freeze we've found was a disguised idle with **no way out**: a WATCH parked at a
  vantage, a `pick_room` "no task rooms" dead-end, and a RECON that `navigate_to`s a stale last-known
  crew position it has already reached (navigate-onto-self ⇒ velocity 0 for thousands of ticks).
- **Rule: any mode that can emit `idle` MUST have a clear escape** — a fallback action, a timeout, or a
  transition that guarantees motion resumes. A mode that can return `idle` (or `navigate_to` its own
  current / an unreachable point) with no guaranteed exit is a latent freeze.
- Idle is legitimate only for a **narrow, deliberate** purpose (a genuine multi-crew vantage stakeout)
  and the unavoidable startup no-op (no camera/map yet). Everything else should move toward crew /
  re-search instead. Concretely: RECON with no live target → fall back to SEARCH (never idle); PICK_ROOM
  → always pick a room. When auditing the FSM, check every `idle` **and** every `navigate_to` that could
  resolve to the agent's current position.
- **An escape must change persistent state — a one-tick escape is no escape.** An escape that only
  returns a different intent for one tick gets re-derived away next tick (the mode recomputes the
  same parked target); real escapes mutate FSM state or a sticky waypoint. Likewise "a stall the
  mode can react to" is a freeze unless some mode actually reacts — every idle path needs an owner
  with a timeout.
- **Actuator near-miss loops are the same disease.** Any repeated-press loop (kill A-press,
  task-station A-hold) that can sit just outside the interaction boundary is a permanent freeze:
  a ~6px perception offset held a kill-press deadlock for 9,000+ ticks, and an `ARRIVE_RADIUS`
  deadband settling one pixel outside a task rect wedged crew at specific stations for whole games.
  Gate on **progress** (N presses with no state change ⇒ treat as out-of-range, step/nudge toward
  the target's center), not on believed-in-range.

## Gameplay levers — what the evidence keeps saying

Distilled from many refuted and confirmed experiments; check these before proposing a direction.

- **The whole game is the parity race.** Ghosts keep tasking, so crew can't lose task capacity by
  dying — imposters' only resource is removing crew (kills + ejections) before tasks finish, and a
  crew mis-ejection is a free parity step for the imposters. Both roles' levers derive from this.
- **Imposter kill VOLUME is structurally capped — stop tuning it.** Kills are bound by the cooldown
  and by body-meetings resetting it (refuted ≥3× independently: BE_DUMB, kill-sooner, isolation-gate
  removal; witness-gate relaxations refuted 3× more). The recurring real levers: (a) **contact** —
  keep/regain sight of crew through the post-kill cooldown so the next ready window lands on a
  visible victim; (b) **kill→win conversion** — meeting play (the parity-push vote was +14.4pp win,
  p<1e-9, with kills flat); condition win on kill count to see this gap. And **never a standing
  positional bias** — camping a chokepoint or seeking the densest room regressed kills both times
  it was tried (capture rare events with an event-trigger, not a standing bias).
- **Crew voting: precision beats participation, and the suspicion model has a train→serve gap.**
  Offline/self-play precision does not transfer live (~94% offline / 80% self-play vs ~39% league —
  the offline replay reconstruction diverges from live perception, which is also why weight refits
  alone never moved outcomes). Mis-votes are parity gifts (2.2× more crew than imposters ejected),
  so vote-bar tuning in either direction is a validated dead end until the live ranking improves —
  and any voting change must be A/B'd against the live league field, never self-play.
