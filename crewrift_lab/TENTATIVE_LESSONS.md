# Crewrift tentative lessons

**What this is.** An *eager, deliberately noisy* buffer of candidate lessons from
Crewrift work — things that *might* be durably true but haven't earned a place in
[`best_practices.md`](best_practices.md) yet. Write here freely the moment something
*looks* like a reusable lesson; most entries will be noise, and that's fine — the value
is the occasional gem.

**The graduation rule.** Each lesson carries a **hit count** — bump it (and add a dated
note) every time the lesson recurs and holds up. **Once a lesson has hit enough (≈3
independent confirmations) and still holds, promote it** to the right `best_practices.md`
(Crewrift-specific → [`best_practices.md`](best_practices.md); game-agnostic → the
root [`../best_practices.md`](../best_practices.md)) and delete it here. Cull entries
that get contradicted.

**Entry format.** `### <lesson, one line>` then: `Hits:` (count + dates), `Evidence:`
(what you observed), `Status:` (`candidate` / `promote?` / `contradicted`). Keep it terse.

---

### `top_n` opponent auto-selection makes the partner/roster UNCONTROLLED — pin an explicit identical roster for any A/B.
- **Hits:** 1 (2026-06-11)
- **Evidence:** A v22-vs-v24 imposter A/B (2-imp, slot 0 = crewborg + slot 7 = partner)
  used `player_selection: top_n`. The auto-selected **slot-7 partner differed between
  arms** — v22 got Kyle Herndon (weak) / Aaron's Optimizer (strong) across batches, v24
  got a "James Boggs" crewborg — and the crew drifted too. That confounded everything:
  v22's *win rate swung 87%→37% with its partner alone*, so the "+23% win for v24" was a
  partner artifact, not a policy effect. Worse: once your own policy is a league member,
  `top_n` can seat **your own crewborg as the opponent/partner** (v24 was rank 10 in the
  division right after submission). **Fix:** for any A/B, pin an **explicit identical
  opponent roster** (`opponents: [{policy_version_id…}]`, NOT `top_n`) so the only
  difference between arms is slot 0; verify the seating in the request readback
  (`xp-request get … .episodes[0].policy_version_ids`) — `opponents[]` seats in list order
  into slots 1..N. (The kills metric was more robust — v24 led in both batches even as the
  partner-strength direction flipped — but only a controlled roster makes it clean.)
- **Status:** candidate (strong methodology lesson — promote on next confirmation)

### A teammate imposter's kill→report RESETS our kill cooldown — the cost of a sloppy partner is our lost CD window, not "stolen" victims.
- **Hits:** 1 (2026-06-11, James's correction)
- **Evidence:** In 2-imposter games crewborg's kills (1.73) trail its solo-pinned rate
  (2.25). The tempting read is "the partner steals our victims." The real mechanism
  (per James): a partner that kills in an **obvious location** gets its body **reported
  quickly**, and a report/meeting **resets every imposter's kill cooldown** — so if the
  partner kills early and it's reported before we've converted our own ~500-tick CD into
  a kill, we simply lose that window. It's not victim contention; it's CD loss we can't
  control from our side. **Only lever on our end: get our kill in ASAP** (leave Pretend
  earlier, don't waste the CD idling without an audience) so a kill is banked before a
  report zeroes the clock. Parked: nothing we can do about the partner's behaviour itself.
- **Status:** candidate

### The agent's OWN sprite is in the perception roster (camera-centre) — exclude `self_color` from suspicion/tailing/votes or it suspects and ejects itself.
- **Hits:** 1 (2026-06-11)
- **Evidence:** crewborg's camera is locked to itself, so its own sprite resolves into
  `belief.roster` like any other player, sitting at our position every tick. The
  `tailing_self` detector then logged *self-on-self* tailing every tick → our own colour
  saturated suspicion at p≈0.72 → `top_suspect` returned **self** → in crew games with no
  stronger real suspect, crewborg accused and **voted to eject itself** ("red sus: they
  were tailing me"; the sim recorded red voting red). Latent in *every* crew game; it was
  the dominant cause of crew losses (the best crewmate throwing its vote on / ejecting
  itself). Fix (v22): learn `belief.self_color` from the camera-centre sprite + the voting
  self-marker, and exclude it everywhere — tailing log, suspicion scoring, `top_suspect`,
  `active_tail_suspect`, and a hard ballot guard. General form: in any ego-centric
  perception view, the self is an entity in the world model — special-case it out of every
  "other players" computation, and verify with a self-vote/self-target regression test.
- **Status:** candidate (strong — promote toward best_practices on next confirmation)

### Platform connect/disconnect-timeout episodes (−100) corrupt win-rate conclusions — filter them before calling a matchup "saturated".
- **Hits:** 1 (2026-06-11)
- **Evidence:** Earlier mixed-role batches looked **win-rate saturated** (everyone ~5%
  crew / ~100% imp) and we nearly concluded the roster couldn't discriminate. But those
  batches were ~48% corrupted by platform-wide connect-timeouts, which score −100 and read
  as losses, dragging *every* player's win rate to a false floor. A later **clean** 50-game
  batch (0 connect failures) showed the real distribution: crew 29–40%, imp 38–80% —
  perfectly discriminating. The "saturation" was mostly a failure artifact, not a property
  of the matchup. Lesson: count `connect_timeout`+`disconnect_timeout` per episode and drop
  any nonzero ones from rate stats; if a whole batch looks flat/degenerate, suspect a
  failure wave before a real conclusion. (Crew win is a *team* outcome + noisy at n~40, so
  even clean it barely separates players — the imposter role discriminates far better.)
- **Status:** candidate

### `expand_replay` kill *attribution* is unreliable at simultaneous-body ticks — trust `results.json` for kill COUNTS, the replay for timing/movement.
- **Hits:** 1 (2026-06-11)
- **Evidence:** Expanded replays showed crewborg "killing" two different players in two
  different rooms on the **same tick** (physically impossible under the kill cooldown), and
  the per-game kill totals disagreed with `results.json` (e.g. 4 kill-lines vs the
  authoritative 3). The re-sim attributes a kill to whichever imposter is near the body
  when it appears, so when two bodies surface together it mis-assigns. `results.json`
  (`kills[i]`, server-authoritative) is correct for counts; the replay is still reliable
  for *when* kills happen and player positions/rooms over time. Use each for what it's good at.
- **Status:** candidate

### Diagnose "low output" agents by splitting **attempt rate** from **conversion** before assuming a skill/aim problem.
- **Hits:** 1 (2026-06-11)
- **Evidence:** crewborg's imposter "under-kills" (1.7 vs 2.0). The instinct is "it misses
  kills / picks bad victims". The trace said the opposite: `kill_attempted == kills` (≈100%
  conversion) — it just *attempts* far too rarely (1–3/game vs a ~4–5 cooldown ceiling),
  because it sits in `pretend` 54–74% of ticks and `hunt` 0.1–2.9%. The fix space is
  "attempt more" (position earlier in the cooldown), not "aim better". Always pull the
  per-tick mode-time distribution and an attempts-vs-successes split from the artifact
  `telemetry.jsonl` before theorising about decision quality. Pair it with "is the agent
  even surviving long enough to act?" (here it never got ejected — pure passivity headroom).
- **Status:** candidate

### The SDK runtime keeps its OWN tick counter; `observation.tick` is ignored — override `runtime.tick` to inject ground truth.
- **Hits:** 1 (2026-06-10)
- **Evidence:** `players.player_sdk` `AgentRuntime.step` does `self.tick += 1; self.emit.tick = self.tick;
  perceive(observation, self.tick)` — so perception, `belief.last_tick`, mode/directive timing, AND every
  trace/metric tick all flow from the runtime's internal counter, and the `observation.tick` the bridge passes
  is dead. To thread the engine's ground-truth tick (Crewrift's `"tick <N>"` marker sprite) through everything
  in ONE place, set `runtime.tick = server_tick - 1` before `step()` (it increments to the server tick).
  Changing only crewborg's `perceive` to read `observation.tick` would fix belief but NOT tracing.
- **Status:** candidate

### One latency/init stall can masquerade as several unrelated-looking gameplay bugs.
- **Hits:** 1 (2026-06-10)
- **Evidence:** crewborg's ~14s first-tick nav/substrate build (under the 250m cap) was the
  shared root cause of BOTH the "slow to leave spawn" symptom AND the rare early-meeting
  vote-timeout: the spawn freeze backlogs ~330 frames, and a meeting landing in that
  catch-up window makes the vote-cursor perceive→press loop run on a stale cursor → never
  converges (120 presses, no `a`). Fixing the stall (offline nav bake, v19) cleaned up the
  voting too — the vote actuator itself was sound (cursor advances 1 slot/press, converges
  in ~8, verified in the uncapped artifact). Lesson: when two odd symptoms cluster in the
  SAME early-game window, suspect one shared timing cause before modelling each separately.
  (The human suspected this at the outset — trust that instinct.)
- **Status:** candidate

### Local `coworld run-episode` does NOT pass host env to player containers.
- **Hits:** 1 (2026-06-10)
- **Evidence:** Setting `CREWBORG_METRICS=1` / `CREWBORG_CAPTURE_WALKABILITY=1` in the shell
  before `smoke.py`/`run-episode` had no effect — the player container never saw them (no
  metrics, no capture line). The local runner doesn't forward host env. Workarounds: bake a
  one-off `ENV` layer (`FROM <image>` + `ENV X=1`) for a local run, or set it hosted via
  `coworld upload-policy --secret-env X=1` (which DOES reach the pod). Hosted secret-env is
  the reliable channel for runtime env.
- **Status:** candidate

### Join league scores to a policy by `policy_version_id`, never by slot position.
- **Hits:** 1 (2026-06-10)
- **Evidence:** A daily-league round's `scores`/`participants` for crewborg v17 also
  contained a *different player's* `crewborg-v23` fork in another slot — a name- or
  position-based join would have mixed them. The episode-row `policy_version_id` is the
  authoritative handle. (Mirrors the root best-practice against position-based score
  joins; this is the concrete Crewrift instance.)
- **Status:** candidate (likely already covered by root best_practices — promote-or-cull on next hit)

### "Finished all 8 tasks" does **not** guarantee a clean crewmate score (8/108).
- **Hits:** 1 (2026-06-10)
- **Evidence:** An all-8-tasks crewmate scored **−2** (lost) and another **98** (won)
  because of a **vote-timeout (−10)**; idle penalties (−1/~20s) can also erode it. So
  the "clean success" score set means *clean play*, not *objective met*. Upside: a pure
  score-anomaly filter therefore *catches* these penalty cases for free.
- **Status:** candidate

### A moving-branch build-arg (`REF=main`) + remote tarball install = silently stale Docker layer.
- **Hits:** 1 (2026-06-10)
- **Evidence:** crewborg's image "tracks `main`" for the players SDK, but the
  `pip install …/archive/main.tar.gz` layer caches on the unchanged URL string — after
  upstream merged the TraceOutputs SDK, a fresh `build_player.sh crewborg` produced an
  image whose SDK **didn't have it** (ImportError in-container). Classic
  looked-like-success: build "succeeded", artifact stale. Fix shipped: build_player.sh
  resolves `main` → the uv.lock commit and passes the SHA, so cache busts exactly when
  the lock moves and image == dev SDK. General form: never feed a mutable ref to a
  cached fetch step; resolve to a digest first.
- **Status:** candidate (mechanism verified once; promote after it saves us again)

### Player artifact upload: a `…@artifact` trace spec **crashes the player** if the upload URL is unset.
- **Hits:** 1 (2026-06-10)
- **Evidence:** `players.player_sdk.TraceOutputs.from_specs` raises `ValueError` when a spec
  targets `artifact` but `COWORLD_PLAYER_ARTIFACT_UPLOAD_URL` is absent — which would crash
  the bridge before connect (= failed episode / −100). The metta contract says the player
  should *skip* uploading when the var is absent, so the SDK's raise is sharper than the
  contract; wrap adoption with a fallback to `stderr`. The metta-main local runner sets a
  `file://` URL (runner.py) — but the **published** coworld client (0.1.20) predates this
  and sets nothing (verified in Gate-1 smoke 2026-06-10: all slots fell back), so local
  smokes exercise the fallback until the client ships the runner change. Hosted sets a
  presigned PUT (metta #15290). Retrieval:
  `GET /jobs/{job_id}/policy-artifact[/{idx}]`. 200 MB cap; jsonl/csv stream to disk,
  json/parquet buffer in RAM (mind the 256Mi pod).
- **Status:** candidate (promote to a build/ship practice once we've shipped it once)

### Static derived data (nav graph, route polylines) is image-build work, not per-run work.
- **Hits:** 1 (2026-06-10)
- **Evidence:** crewborg rebuilt its nav graph + occupancy substrate (O(anchors^2)=1806-poly
  A* sweep) on the FIRST TICK every game — pure functions of the one static map. Fine at full
  CPU (~2s), but ~13.7s under the hosted 250m cap, freezing the agent at spawn while the
  24Hz engine streamed ~330 frames ahead. Baking once offline into a vendored asset +
  loading (with a mask-match validation + live-build fallback) cut tick-1 ~200x hosted
  (13,700ms -> ~65ms), play byte-identical. General lesson: profile the FIRST tick under the
  real CPU budget, and move any input-independent precompute to build time. Watch for lazy
  one-time builds triggered by the first stream frame — they hide from steady-state metrics
  AND from line-capped logs (the start is what gets truncated).
- **Status:** candidate (promote toward best_practices — strong, generalizable)

### The `/jobs/{job}/policy-artifact` listing returns filenames, not slot ints — and the start-of-game is ONLY in the artifact.
- **Hits:** 1 (2026-06-10)
- **Evidence:** Listing returns `["policy_artifact_0.zip","policy_artifact_1.zip"]`; a naive
  `int(s)` parse drops everything (looked like "no artifacts"). Bigger lesson: the hosted
  stderr policy log is capped at 10k lines and keeps the **tail**, so tick 1 is gone — but the
  artifact zip is the **whole game**. crewborg's slow-start (a ~14s first-tick init) was
  invisible in logs and obvious in the artifact on the first look. Always prefer the artifact
  for anything time-series, especially the start. (Verified live after metta #15409.)
- **Status:** candidate

### `docker pull` 403 from `public.ecr.aws` → `docker logout public.ecr.aws` first.
- **Hits:** 1 (2026-06-10)
- **Evidence:** `coworld download crewrift` failed pulling the game image with `403
  Forbidden` from ECR Public. Cause: a stale cached ECR auth token (anonymous pulls
  work; expired credentials poison them). `docker logout public.ecr.aws` fixed it
  immediately. Also: transient `SerializationFailure ... conflict with recovery`
  500s from the XP-request API are read-replica conflicts — just retry.
- **Status:** candidate

### Daily-league *round* episodes are queryable (with scores inline) without downloading artifacts.
- **Hits:** 1 (2026-06-10)
- **Evidence:** `coworld episodes --round <round_id> --policy <name> --json` returns the
  commissioner round's episode rows — including `participants` and `scores` — so a
  cheap score-level sweep needs no artifact pull. Note this hits `/v2/episode-requests`
  by `round_id`; the episode-artifacts `endpoint-map.md` frames league episodes as a
  population *disjoint* from `/v2/episode-requests`, yet these commissioner-run league
  rounds appear there. Possibly the endpoint-map is partially stale for commissioner
  rounds, or "league episode" there means something narrower. **Verify before relying
  on the disjointness claim** — and if confirmed, fix the endpoint-map.
- **Status:** candidate (also a doc-accuracy flag)
