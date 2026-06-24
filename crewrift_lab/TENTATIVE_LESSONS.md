# Crewrift tentative lessons — session buffer

**Session started:** 2026-06-23 18:12. This is THIS SESSION's lesson buffer. Write candidate
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

### Imposter under-kills because MEETINGS reset the kill cooldown before our first window (2026-06-24, v39 debug trace, 40 games)
Evidence: imposter loss = under-killing, NOT ejection (no −100s; 31% of games 0-kill). Debug trace shows: role resolves at tick 0 (not a lag), victims visible ~93% of ticks, conversion is ~1-tick when Hunt fires — but **Hunt ≈0% of the game**. Why: `self_kill_ready` (HUD-decoded) doesn't turn on until **median tick 4741** while games END at median 6091. Cause: **a median of 4 meetings (range 2-6) happen before our first kill-ready** — each return-to-Playing from a meeting resets the ~500-tick kill cooldown (engine behavior, types.py:722). Partners/others kill early (first body med tick 3620, min 1427) → meeting → our cooldown resets → repeat. Correlation: 0-kill games avg 4.4 meetings-before-ready vs 2-kill games 3.8. So the lever is NOT "hunt harder/be aggressive" (conversion is fine) — it's that the cooldown is repeatedly reset before we use it. Old WORKING_CONTEXT parked this as "nothing we can do from our side"; the debug trace makes the magnitude undeniable and worth a real direction decision. Candidate angles: kill in the FIRST post-meeting window before the next body drops; suppress partner over-killing (team coordination); or accept it's structural and pivot. NEEDS James's direction.

### Always work the HIGHEST-LEVERAGE gap, don't dig for slight improvements (James, 2026-06-24)
Evidence: after the vote-gate sweep + reconnect fix, role-split eval showed crewborg crew 52% but imposter 43% (vs field-leader 54% imposter). James's call: stop refining the thing we just touched; the eval itself names the weak half (imposter), so pivot there. Principle: when a measurement surfaces a clearly weaker dimension, that dimension IS the next objective — don't keep optimizing the half that's already competitive for diminishing returns. Re-ask "where's the biggest gap?" after every eval, not "how do I improve what I just changed?"

### Nightly champion loop silently broke: smoke.py picks newest manifest in the SHARED coworld/ dir, not Crewrift's
Evidence: nightly_refit.sh Gate-1 failed every night 06-16→06-20 ("exit code 1 CRASH, champion unchanged"); last good submit was v31 on 06-15. Root cause: `coworld-local-run/scripts/smoke.py:ensure_manifest()` globs `coworld/*/coworld_manifest.json` and takes `max(mtime)`. With three labs (Crewrift, Cue-n-Woo, Agricogla) all downloading into the one shared `coworld/` dir, the 06-20 smoke ran a `cue_n_woo-0.2.14-2` game container (cow_96aa062b) — it timed out at 240s and reported CRASH. So the refit/test/build all PASSED; only the wrong-game smoke aborted the ship. The nightly never errored loudly — it just quietly stopped shipping for a week.
Status: champion frozen at v31 (rank 11/18, score 46.2). Field advanced — leader Andre Jr 63.2. Fix candidates: pass `--manifest <crewrift cow_id>` (or `--coworld <cow_id>` not the name) in nightly_refit.sh; or make smoke.py filter manifests by game name. NOT yet fixed — pending James's call.

### `top_n`/`random` roster selectors now 500 (statement timeout) — pin explicit policy_refs instead
Evidence: 2026-06-23, both standing-eval xreqs with `{"top_n": 7}` opponent seats failed HTTP 500 "QueryCanceled: canceling statement due to statement timeout" — the champion-ranking CTE (joins policy_versions × memberships × episode_policy_metrics over all episodes since 05-25) has gotten too slow as the stats tables ballooned (586 rounds × growing corpus). Workaround that worked: `resolve --division … --top 7` to get the ranked list, then pin each as an explicit `policy_ref: "name:vN"` (skips the ranking query entirely). Bonus: explicit pins are reproducible across both A/B arms. Worth telling James — this likely breaks any nightly/skill that leans on top_n.

### The -100 connect_timeout is an INITIAL-connect race (0 frames seen), not a mid-game drop — fixable with connect-retry
Evidence: 2026-06-24, inspected crewborg's policy-artifact telemetry + stderr for episodes where seat0 (us) timed out: 0–1 telemetry lines, NO stderr log, episode `running_at: None`. crewborg never received a frame. Its bridge (`coworld/policy_player.py:run_bridge`) did a SINGLE `connect()` with no retry — if the container starts before the engine's /player ws accepts, connect throws → process exits → −100. Fix: retry the initial connect with capped backoff until the first frame arrives, bounded by a deadline; discriminate game-over (a close AFTER ≥1 frame) from a connect race (close/error BEFORE any frame) via `frames_seen`. Of the 2026-06-24 −100s, ~half were crewborg's own connect (fixable), ~half were opponents failing (seat pattern [0,0,1,1,1,1,1,1] = opponents, unfixable from our side). NOTE crewborg's transport is its OWN policy_player.py, NOT the player SDK — the SDK isn't even on its connection path; James flagged moving transport into the SDK as future work (root TODO.md).

### Connect-timeout ops-failures can spike to ~65% and silently gut statistical power — watch the ops-filter count
Evidence: sweep2 (2026-06-24, 1800 eps vs Aaron+Andre) had 1177/1800 (65%) episodes degenerate (some seat connect_timeout=1 → −100 across the board), vs the ~8% norm. Per-arm clean n dropped from 300 to 63–94, turning a planned high-power sweep into an underpowered one (v33-vs-rest p=0.39 where sweep1 had p=0.031). The xp_dashboard surfaces this as "ops-filtered N" — always read it; a big number means your effective n is far below num_episodes. Mitigation James flagged: more aggressive reconnect in the player SDK. Also: connect_timeout flag propagates/cascades across seats within a degenerate episode (seat 0→7 monotonic increasing count), so it reads as platform/episode-level, not one player's fault.

### crewborg trace lives in the policy-artifact ZIP, NOT the per-agent log — and `--no-logs` drops BOTH
Evidence: 2026-06-24, a downloaded `logs/policy_agent_0.log` for a hosted episode was ONE line ("game over: server closed the connection") — zero JSON. The real trace (per-tick `domain.decision_snapshot` w/ `role`, `domain.vote_cast`, `domain.player_died`, `domain.meeting_decision`, `domain.suspicion_snapshot`) is in `artifacts/policy_artifact_<slot>.zip` → `telemetry.jsonl` (~10MB), uploaded via the SDK TraceOutputs `jsonl@artifact` path (since v18). In fetch_artifacts.py, `--no-logs` gates the policy-artifact-zip download too (`if want_logs:` wraps it, ~line 458) — so a `--no-logs` fetch loses the traces entirely. To get tracing: fetch WITHOUT --no-logs, then `unzip -o artifacts/policy_artifact_0.zip telemetry.jsonl` and `grep '^{'` (last line is plain text). sweep1 used --no-logs → no traces; sweep2 must not.

### Crew vote threshold: lowering it RAISES crew win — the v25 P>=0.9 restraint over-corrected for the current field
Evidence: 2026-06-23 sweep, crewborg slot0=crew vs live top-7, 2 imp, 138-141 clean eps/arm (ops-filtered). Crew win% by CREWBORG_WEIGHTS_VOTE_P: 0.9=31.9% (control) / 0.8=35.5% / 0.7=40.4% / 0.6=31.4% (noisy dip) / **0.5=44.5% (+12.6pp vs control, p=0.031)**. Mechanism is unambiguous and holds across ALL arms: when crewborg casts >=1 player-vote it wins 58-72%; when it skips the whole game it wins 9-28%. Lowering the gate moves games from the skip bucket into the vote bucket (35 voting games at 0.9 -> 81 at 0.5), and that is where wins come from. The 0.6 dip is noise (its win|voted=60% is on-trend; bad win% draw). v25 adopted P>=0.9 vote-restraint because the OLD field voted accuse-heavy crewborg out; the field evolved and passivity now loses the parity race. NB: this sweep measured crew win only — did NOT measure the v25 risk (own-ejection / team crew-ejections climbing as the gate drops); confirm that before shipping a low gate (needs logs/replay, dropped here for fetch speed).

### Uploading the SAME image with different --secret-env does NOT create distinct versions (dedup by image digest)
Evidence: 2026-06-23, uploaded players-crewborg:dev 5× with 5 different `--secret-env CREWBORG_WEIGHTS_VOTE_P` values → all collapsed to ONE version (v32). The platform dedups by container-image digest; per-upload secret-env does not fork a version. To run N config arms you need N DISTINCT IMAGES. Fix that worked: thin derived images `FROM players-crewborg:dev` + `ENV CREWBORG_WEIGHTS_VOTE_P=<p>` (one ENV line → distinct digest → distinct version). Built 5 tags vote0.9..vote0.5, each uploaded to its own version (v33–v37). VERIFY the bake with `docker run --rm --entrypoint python <img> -c "import …suspicion as s; print(s.WEIGHTS_VOTE_PROBABILITY)"` before launching the sweep.

### experience-request num_episodes is capped at 100 by the API — fan out for more
Evidence: 2026-06-23 a 150-ep body got HTTP 422 "Input should be less than or equal to 100". For 150/arm fired two requests (100 + 50) and pool the episodes at analysis time. (Also: creating ~5 requests in one bash loop timed out >2min — each create does a live schema round-trip; fire them as separate calls.)

### Leaderboard score is per-PLAYER, not per-version — every crewborg membership shows the same score
Evidence: `policy_lifecycle.py monitor` printed identical "rank 11 score 46.23 rounds 586" for v1..v31 memberships. The division leaderboard aggregates by player_id (James Boggs), so you cannot read a single version's standing off it. Use per-version results.json / experience requests to attribute version-level performance.
