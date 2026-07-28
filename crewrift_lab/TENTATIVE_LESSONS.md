# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-28 09:34. This is THIS SESSION's lesson buffer. Write candidate
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

### Lesson entries MUST use `###` headers — `- ` bullets get silently DROPPED by rotation
Evidence: this session (07-22..28) wrote ~15 lessons as `- **bold**` bullets; rotate_lessons.sh
gates archiving on `grep -q '^### '`, judged the buffer contentless, and overwrote it without
archiving. Reconstructed below from the session transcript. Fix candidates: rotation should
archive any buffer that differs from the template, or warn.

### A stale coworld player session silently breaks artifact fetching AND uploads
Evidence: `softmax status` showed subject_type=player (seedtest-run002, left from an earlier
session). With that token `/v2/experience-requests/{xreq}` 404s (ownership-scoped) and
`/jobs/{job}/policy-logs` 403s. Fix: `auth.clear_active_player_session(server=...)` (skill's
`_delete_player_session` name is stale). It BIT TWICE: later the same session it repopulated
and bound crewborg:v113 to the WRONG player — v113 is a dead orphan, never submit it. Now doing
clear+whoami-assert immediately before EVERY upload/submit/retire; consider a preflight guard.

### League episodes carry no fetchable artifacts — but episode search + public replay_url works
Evidence: telemetry analysis is only possible on experience-request arms; league fetch (40 eps)
yielded episode.json only. For warehouses: `POST /v2/episodes/search` returns inline results
(attributes.coworld.results) AND public S3 replay_url — fetch those into warehouse-shaped dirs
(/tmp/fetch_league_corpus.py). results.names are PLAYER display names ("Aaron (2)" = 2nd seat);
map name→policy via active memberships. Full xreq ids resolvable from episode tags
(tags.experience_request_id) — WORKING_CONTEXT's truncated prefixes are not fetchable.

### The Bedrock 429s are the AWS DAILY pool, structurally oversubscribed — not minute limits, not the sidecar
Evidence: CloudWatch AWS/Bedrock on the tournament acct (`--profile tournament` — we CAN read it;
old "can't read quota" belief STALE): fleet burns ~592M of 714M/day Haiku tokens, 0.9-1.5M
throttles/day, FLAT across 24h. Minute quotas never bind (peak 1.4M/5M TPM, 569/10K RPM).
Sidecar spend-limit ruled out (different message; xreqs have no limit). Demand ~3.2M tok/min vs
~496K/min refill ≈ 6× oversubscribed → predicted 15-25% success = measured 17-28%. Daily quotas
are adjustable=False. Each model has its OWN pool (Sonnet 5: 500M/day); global. vs us. profiles
are separate buckets — global.anthropic.claude-haiku has ZERO fleet traffic (untapped, unverified).

### League meta: crew ballot VOLUME beats precision (mv-model: 1 hit ≈ 2.3 mis-votes)
Evidence: 400-ep league warehouse, n=3200 seats: standardized coefs hit_imp +0.51, mis −0.22,
tasks +0.56, died −0.57; crew win 21.9%/44.4%/62.6% at 0/1/2 correct votes/ep. Crewborg pre-v115:
97.7% precision (corpus-best) at HALF the top-5 volume, skip-only in 43/82 crew eps, corpus-worst
crew WR. The 0.9 bar optimized a metric the league doesn't pay.

### Offline gate replay from suspicion_snapshot telemetry is nearly free and a LOWER bound on live quality
Evidence: 185 crew meetings' posterior rankings + ground truth swept 13 gate configs in seconds
(/tmp/vote_sweep/offline_sweep.py) and correctly picked the live winner. Live precision BEAT
offline at every bar (0.5: 77% live vs 63% predicted) — live ballots add witnessed/pile votes.
Reusable for any traced decision-gate parameter. NOTE: CREWBORG_VOTE_PROBABILITY env clamps at
[0.5, 0.99] — probing below 0.5 needs code.

### Vote-gate sweep verdict: bar=0.5 decisively (shipped v115)
Evidence: 4×100 matched arms; net correct votes/crew-ep 0.836 vs 0.406 (hits p<0.0001), live
precision 77%, crew WR +8.1pp directional, all guards clean. bar=0.6 was anomalously the WORST
arm (non-monotonic mid-band, likely noise at n=58 ballots — flag if recurs). W2's bimodal finding
reconciles: the 0.5 bar harvests the non-witnessed 0.5-0.74 mass the 0.9 bar discarded.

### Wave-2 mining: after fixing volume, the binding constraint moved to BALLOT→EJECTION CONVERSION
Evidence: post-v115 league play: votes/ep 0.54→1.27 (the bar change transferred live) but
conversion 31.9% vs top converters 61-71%. imp-ejected-in-episode is THE crew-win correlate
(r=+0.70). Mechanism: we voted earliest (votes_before_ours 1.71, corpus-low) and alone
(pile_before 0.12 vs 0.7-1.6). Improvement loops move the bottleneck — re-mine after each ship.

### Converter chat study: the emulation target was TIMING, not text
Evidence: ALL players chat before 100% of correct ballots; top converters' texts are terse
("saw red, red sus, vote red") while our verbose cue-format pulls MORE followers/message
(1.13 vs 0.75 social_cue class). What converters do differently: vote 2.5-3.5 votes into the
meeting (we voted at 1.71). Claim-class persuasion: witness_kill 2.28 followers, terse_saw 1.76,
social_cue 0.75.

### Coordination A/B: both levers passed SOLO; the combo FAILED — levers sharing a timeline interfere
Evidence: chat-push conv 32.5% (p=0.009, clean rerun), retime 35.3% (p=0.005, 42 joins/49
expires); combo 24.1% < prereg bar — push fires only post-ballot, retime delays the ballot, so
combo pushes landed too late (47 fires, 27 joins). Two individually-validated levers touching
the same meeting clock need an interaction design, not flag-AND. Shipped retime alone (v116).

### Ops-dirty arms: RERUN, don't salvage
Evidence: push arm run 1 was 32% ops-dirty (platform connect-timeout wave) and skewed the role
draw (16 imp eps vs base 26). The 100-ep rerun cost ~25 min and turned p=0.10 into p=0.009.

### Chat-push text bug (fix before any re-ship of the push lever)
Evidence: push renders "vote orange. orange sus: … vote orange" — build_accusation already
appends the vote call; prefixing "vote X." duplicates it. Cosmetic but sloppy.

### Small-n guard baselines are fragile — pool guards across contemporaneous arms
Evidence: base arm's imposter WR 92.3% (n=26) made combo's normal 64.5% look like a guard fail
(p=0.024) despite both levers being crew-only code paths. Future preregs: imposter-side guards
should pool all same-window arms.

### Platform gotchas that recurred this session
Evidence: membership-list + submission-list routes serve STALE rows after submit — confirm
placements via the division-membership listing (or /v2/policy-membership-events), never the
poller alone (v115 poller ran 40 min reporting 'placed' while the membership was already
competing+champion). Leaderboard switched to Elo scoring ~07-27 (episodes_played now null on
rows — null-guard leaderboard parsing).
