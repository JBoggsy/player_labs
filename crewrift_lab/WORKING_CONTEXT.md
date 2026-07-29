# Crewrift working context

**What this is.** The live, high-signal state of *what we're working on right now* in
the Crewrift lab — the minimal set of cross-session facts worth carrying into the next
session. Read it on startup to resume; **update it as you learn** (keep it tight —
prune anything no longer load-bearing). **Clear and reseed it when we pivot to a whole
new direction**, keeping only the new objective.

This is *not* a log or archive: finished work lives in git history / the
[version log](crewrift/crewborg/version_log.md); durable disciplines live in
[`best_practices.md`](best_practices.md); durable prefs in
[`user_preferences.md`](user_preferences.md). This file is the one-screen "where are we."

> A recorded objective below = onboarding done; resume the loop ([`AGENTS.md`](AGENTS.md)).

---

## 🔁 RUNNING (2026-07-28): improvement-loop alpha — autonomous ~5-loop run (spec: `docs/designs/2026-07-28-improvement-loop-alpha.md`)

**Loop 1 DONE — NO-SHIP (lever closed, honestly refuted).** Step-1 batch: 4×100 matched
xreqs (`xreq_f42ce4c9/83cae9d4/fd660882/c48a86c2`, 397 clean eps, v116 slot 0, Thread-1
roster) → warehouse `/tmp/loop1/wh` + belief log + divergence scan. Key reads:
- **v116 WATCH satisfied:** crew WR 28.9% (ship-time 25.5%), conversion 27.5%; retime
  decomposes join 53.1% / expire **0.8%** conv — the expire path is dead weight.
- Both fresh smoke signals (census death-lag 0.178/seat, ranking_top_crew 0.186/seat)
  verified REAL but mined INVARIANT (not win/loss separators) → closed, don't design on them.
- L1 hypothesis (pre-vote push during retime hold, probe `crewborg-coord:v5`
  `fa075cb9…`, prereg `docs/designs/2026-07-28-prevote-push-prereg.md`): **REFUTED** —
  mechanism fired 136×/84 eps, but late-join share 21.0% vs 21.2%: a second explicit
  vote call recruits nobody; the field locks on the first accusation wave. The whole
  "more chat calls" channel on the conversion axis is closed (2× with the combo failure).
- Gotchas: warehouse `chat` caps at 6/meeting (extractor sees only the visible buffer
  grow — mechanism reads need telemetry counters); within-arm pushed-vs-unpushed is
  selection-biased.
Next lever candidates for the conversion axis: make the FIRST accusation harder
(suspicion-v5 refit — the W2 measured ceiling AUC 0.82). Loop 2 starting.

## 🎯 OBJECTIVE (2026-07-23): v114 submitted — v112's code with LLM meetings OFF (deterministic)

**James's call: "turn off LLM meetings for now and use our deterministic fallback."** v114 =
v112's byte-identical code (main `64abdab`), recipe minus `--use-bedrock`/`CREWBORG_LLM_MEETINGS`
(everything else kept: HS secret, chat evidence + 0.9 floor, NLP, traces). Submitted to Crewrift
Prime 2026-07-23 (`sub_82aa6f35…`, placed; v112's `lpm_78d02983…` retired first). Poller template:
`/tmp/poll_v114_qualify.py`. ⚠️ v113 is an ORPHAN (bound to wrong player `seedtest-run002` by a
stale player session — see version_log + TENTATIVE_LESSONS); never submit it.

**Why (2026-07-23 Bedrock investigation, CloudWatch on the tournament acct — we CAN read it,
`--profile tournament`):** the 429s are the AWS DAILY pool, structurally oversubscribed — fleet
burns ~592M of 714M/day Haiku tokens with 0.9–1.5M throttles/day, FLAT across all 24h (not
eval-driven; something burns ~23.5M input tokens/hour around the clock). Minute quotas never bind
(peak 1.4M/5M TPM, 569/10K RPM); sidecar spend-limit ruled out (different message; xreqs have no
limit). Demand ~3.2M tok/min vs ~496K/min refill ≈ 6× oversubscribed → predicted 15-25% success =
measured 17-28%. Daily quotas are `adjustable=False` — the standard quota-raise ask may be
ungrantable; update `docs/bedrock-quota-ask.md`.

## 🔧 BUILT (2026-07-28): crewrift-belief-audit skill — belief↔ground-truth sync + divergence scan

New skill `crewrift_lab/.claude/skills/crewrift-belief-audit/` (tests:
`tools/tests/test_belief_audit.py`, 2 green; smoke-verified on 8 real crewborg-coord seats
from `xreq_61f440b3-828c-…`): `build_belief_log.py` extracts crewborg's belief telemetry
from policy-artifact zips into native warehouse `belief_*` partitions (each row enriched
with `truth_roles` for every mentioned color + self identity; per-seat phase-alignment
clock check → `belief_sync_report.json`), and `scan_divergences.py` flags 11 divergence
kinds (confirmed_crew, ranking_top_crew, phantom_death, vote_crew_over_imposter, …) with
per-kind rates → `belief_divergences.jsonl`. This is loop-step-3+5 tooling for the
tournament-scale improvement loop. Smoke findings worth a real batch: census death-lag
300-650 ticks; ranking_top_crew at p≈0.5 right at the vote bar. Gotchas learned →
TENTATIVE_LESSONS (absolute --expand-replay path; league eps have no artifacts — xreq only).

## 👑 SHIPPED (2026-07-28): v116 = v115 + BALLOT RETIME — competing/active + CHAMPION

`crewborg:v116` (`23b03ef8…`, main `565a1ea`, v115 recipe + `CREWBORG_VOTE_BALLOT_RETIME=1`)
submitted 2026-07-28 (James: "go for it"); v115's membership retired first → v116
`lpm_288949ba…` competing/active + champion. Version_log has the full row. League at ship:
rank 12/18, Elo 1451, WR 37.7% (fresh 3k window 07-25..27), imposter 78.3% (FIELD-BEST),
crew 25.5% (15th — retime's target). WATCH: crew WR + ballot→ejection conversion over the
next ~100 rounds (A/B predicted conv 13.8%→35.3%, crew +8.4pp directional). Follow-ups
queued: pre-vote chat-push variant (fix "vote X… vote X" dup text first), sub-0.5 bar probe
(env clamp floors at 0.5, needs code), suspicion-v5 refit (precision at volume).

## ✅ DONE (2026-07-24): vote-coordination A/B — VERDICT: SHIP RETIME ALONE

**Full verdict in prereg doc (`docs/designs/2026-07-24-vote-coordination-prereg.md` §VERDICT).**
Both singles passed (clean arms): chat-push conv 32.5% vs base 13.8% (p=0.009; first arm 32%
ops-dirty → RERUN per rule), retime conv **35.3% (p=0.005)**, impEj-eps/cep 0.523 (+62%,
p=0.08), crew WR +8.4pp directional, all guards clean. **COMBO FAILED its prereg bar** (conv
24.1% < 35.3%−noise): the levers interfere — push fires only post-ballot, retime delays the
ballot → pushes land too late (47 fires but 27 joins vs retime-solo 42). Per decision rule:
**next ship = `CREWBORG_VOTE_BALLOT_RETIME=1` added to v115's recipe** (needs James's gate).
Chat-push validated as mechanism; revisit later as PRE-vote push + fix duplicated "vote X…
vote X" text. Arms: base `xreq_8c20ec6d`, push1 `xreq_e6c817ca` (invalid), push2
`xreq_0f6b2542`, retime `xreq_61f440b3`, combo `xreq_ed97ed89`; probes crewborg-coord:v1-v4.

## 🔬 superseded header: vote-coordination A/B — 3 arms firing (P, R, baseline)

**Both levers BUILT + committed (main `565a1ea`, both flags default OFF, 721 tests):**
`CREWBORG_VOTE_CHAT_PUSH` (post-vote "vote X. <evidence>" push when target vote-less <480
ticks; persuasion only) + `CREWBORG_VOTE_BALLOT_RETIME` (hold ballot after accusation; cast
on first co-vote or at early-submit; timing only). Prereg BEFORE firing:
`docs/designs/2026-07-24-vote-coordination-prereg.md`. Probes `crewborg-coord:v1/v2/v3`
(baseline/push/retime, all on v115 recipe + bar 0.5), 100 eps each, Thread-1 roster:
baseline `xreq_8c20ec6d`, push `xreq_e6c817ca`, retime `xreq_61f440b3`. PRIMARY: correct-
ballot→ejection conversion up (crewborg 31.9% vs top 61-71% in league). Per James: test
separately; if BOTH pass, fire the P+R combination arm; chat-push is the priority lever.
Chat study result: everyone chats pre-ballot; converters differ by VOTING LATER (2-3 votes
in) not by text — our verbose cue-format already pulls above-field followers (1.13 vs 0.75
social_cue class). Artifacts → /tmp/coord/eps_{base,push,retime}.

## 🎯 WAVE 2 (2026-07-24): mining rerun post-v115 — next lever = BALLOT→EJECTION CONVERSION

v115 (bar 0.5) shipped + champion, but leaderboard WR ~flat (42.6% @ 742 eps; note score/WR
rebuilds — v114+v115 pooled, not pure v115). Fresh 400-ep league warehouse (`/tmp/wh_league2`,
corpus2, 07-24 16:44-17:55Z window; analysis `/tmp/league_ds2`):
- **The bar change WORKED mechanically:** crew votes/ep 0.54→1.27, hits/ep 0.52→0.76,
  skip-rate 0.81→0.52 (live league telemetry-free measurement via warehouse).
- **Crew WR still bottom-tier (17.6%)** — field crew WR also dropped (34%→30%) this window;
  imposter share ran unlucky (18.8% vs ~23%).
- **NEW FINDING: imp-ejected-in-episode is THE crew-win correlate (r=+0.70) and we are LAST
  at converting correct ballots→ejections: 31.9% vs top 61-71%.** Mechanism measured: we vote
  EARLY (votes_before_ours 1.71, lowest) and ALONE (pile_before 0.12 vs field 0.7-1.6),
  pulling only ~1.5 followers → our correct target ends ~2.6 total votes vs converters' ~3.4.
- **NEXT LEVER: vote coordination (Direction 1)** — (a) chat-accuse with evidence cue
  before/with every correct ballot ("vote X" + cue = 64% persuasion, chat-study), (b) prefer
  joining forming piles / retime our ballot vs seeding lone ones. Design + probe next session.

## ✅ DONE (2026-07-23): vote-gate sweep — VERDICT: bar=0.5 SHIP RECOMMENDED

**All 4 arms completed 100/100, verdict in prereg doc
(`docs/designs/2026-07-23-vote-gate-sweep-prereg.md` §VERDICT): bar=0.5 passes the
pre-registered PRIMARY + all guards** — net correct votes/crew-ep **0.836 vs 0.406** (hits
p<0.0001), live precision 77%, crew WR 34.2% vs 26.1% (+8.1pp directional, underpowered),
imposter side better, vote_timeouts 0, self-votes 0. bar=0.8 modest (NS), bar=0.6 worst arm
(non-monotonic mid-band — noise at n=58 ballots, flag if recurs). NEXT: carry
`CREWBORG_VOTE_PROBABILITY=0.5` in the next `crewborg` version's recipe (needs James's
submit gate as usual; upload + confirmatory A/B vs v114 first). Env clamp floors at 0.5 —
probing lower needs code. Analysis `/tmp/vote_sweep/`; arms in eps_{base,bar08,bar06,bar05}.

## 🔬 superseded header (kept for arm ids): vote-gate sweep — 4 matched arms firing

**The mining wave found the lever** (400 fresh league eps, `/tmp/wh_league`, `/tmp/league_ds`):
crew ballot VOLUME beats precision — mv-model coefs hit_imp +0.51 / mis −0.22 / tasks +0.56 /
died −0.57; crew win 22%→44%→63% at 0/1/2 correct votes/ep. Crewborg as crew: 97.7% precision
(corpus-best) at HALF the top-5's ballot volume, skip-only in 43/82 crew eps, corpus-worst crew
WR 22%. Offline gate replay over 185 real crew meetings (`/tmp/vote_sweep/offline_sweep.py`):
bar=0.8 dominates 0.9 (87.5% precision, +30% hits); 0.6 → 74% prec / +70% hits; 0.5 → 63% / 2.2×.

**Live sweep (prereg BEFORE firing: `docs/designs/2026-07-23-vote-gate-sweep-prereg.md`):**
4 arms × 100 eps, Thread-1 pinned roster slot 0 natural roles, v114's image, arms differ ONLY in
`CREWBORG_VOTE_PROBABILITY`: baseline crewborg:v114 (0.9) `xreq_5f3cf7b7`, crewborg-votebar:v1
(0.8) `xreq_d91a92cb`, :v2 (0.6) `xreq_78bbd3d5`, :v3 (0.5) `xreq_8a4df2c6`. Probes NEVER
submitted. PRIMARY: net correct votes/crew-ep + imposter-ejections/crew-ep beat baseline (p<0.05
on one). GUARDS: crew win not worse, mis-ejections-we-voted ≤2× base, vote_timeouts 0, imposter
untouched, ops ~0. Artifacts streaming to `/tmp/vote_sweep/eps_{base,bar08,bar06,bar05}`.
NOTE: env bar clamps at [0.5,0.99] — deeper sweep needs code.

Near-term:
1. **Watch v114 qualify → competing** — DONE: competing/active + CHAMPION (`lpm_d5217689…`);
   tournament eval (xreq_b63cde8b, 100 eps): 45% overall (3rd/16 in sample), imposter 80%,
   crew 33%, 0 vote timeouts, telemetry verified 0 LLM calls.
2. **LLM re-entry options when wanted:** `global.anthropic.claude-haiku-4-5…` inference profile
   (separate ~714M/day pool, currently ZERO fleet traffic — needs a probe) or Sonnet 5
   (`us.anthropic.claude-sonnet-5`, own 500M/day pool, ~2× cost, needs latency probe vs 6s timeout).
   Attribution of the 24/7 592M/day burner (CloudTrail / sidecar S3 completions) would tell us if
   per-tenant budgets fix everyone.
3. **Open lever candidates:** suspicion-v5 refit (ML ceiling AUC 0.82 — W2's key measurement);
   vote coordination to monetize HS trust (Direction 1).
4. **W5 watch item:** the warm-pile/chat-evidence double-count channel is real but benign (5/5 true
   imposters). If warm volume grows, re-measure interaction (b) (`/tmp/w5_ab/interaction_b.py`).

---

## 👑 DONE (2026-07-22, W5): v112 SHIPPED — combination A/B CLEAN → SUBMITTED → COMPETING + CHAMPION

**crewborg:v112 is `competing/active` and CHAMPION** (`lpm_78d02983…`, submission `sub_e61b68a1…`,
"Selected as champion." 22:52Z; v111's `lpm_329ad382…` retired first with the audit reason —
the superseded gotcha honored). Leaderboard: rank 17 / score 5.0 at 1 round played (score resets
per-membership and rebuilds). **VERDICT: ALL pre-registered gates + mechanisms PASS** (cand
`xreq_adf9eb36`+`xreq_f5cd7186`, 200/200 eps, 1 ops-excluded → 199 clean, per-episode verified
v112 `0feddca8` slot 0, identical roster to W1's re-verified v111 baseline arms):
- Gate 1 no-regression ✅ crew 28.9% vs 26.4% (p=0.69, direction UP), imposter 62.5% vs 63.3% (p=1.0).
- Gate 2 mis-votes/crew-ep ✅ **0.185 vs 0.243** (bar was ≤0.232).
- Gate 3 warm-vote precision ✅ **5/5 = 100%** (16 warm fires, 11 lone ballots gated to skip,
  3+2 pile escalations all true imposters).
- Gate 4 ✅ vote_timeouts 0/0, self-accusations 0, ops 1 vs 7.
- Mech 5 anchor ✅ **0.377/ep vs 0.218** (hard 0.296 + warm 0.080, poisson p=0.004) — ABOVE W2's
  solo 0.266/ep: interaction (a) confirmed, chat evidence pushes suspects onto the bar; hard-route
  accuracy 91.5% vs 100% (p=0.07 NS — the new hard fires are chat-evidence bar-clearers, W3b-priced).
- Mech 6 chat evidence ✅ 378 applied / 44 changed votes @ 79.5% imposter-hit (vs 71.5%
  suspicion-alone; W3b solo was 92.1%, dilution NS p=0.13); HS sources 83/316 nonzero meetings.
- Mech 7 spend ✅ llm_spend 2015 = meeting_llm_call 2015, exactly 1:1.
- **Interaction (b) — the double-count channel is REAL: all 5 pile escalations had chat-evidence
  contribution to the same warm target.** But all 5 ejected true imposters; no innocent pile-on:
  total crew-ej/crew-ep 0.748 vs 0.674 (p=0.46), crew-ej-we-voted 0.104 vs 0.069 (p=0.39),
  self-ejected 22 vs 27. WATCH ITEM for the next wave: if warm volume grows, re-measure (b).
- Directional: crew vote precision **79.8% vs 71.5%**; imp-ej/crew-ep 0.519 vs 0.514 (flat).
Full row: version_log.md v112. Analysis `/tmp/w5_ab/` (w5_metrics.py, interaction_b.py,
cand/base_metrics.txt); warehouse `/tmp/wh_v112_cand` (200 eps), episodes `/tmp/wh_v112_cand_episodes`.
Platform note: the membership-LIST route returned only 2 stale rows post-submit — confirm
placements via `/v2/policy-membership-events` + the division leaderboard instead.

### The W5 prereg as registered (verdict above)

**PRE-REGISTERED A/B (combination confirmatory — W2 and W3b were validated SEPARATELY vs v111
and both touch the suspicion posterior + meeting vote path), registered BEFORE firing the cand arms:**
- **Design:** cand = 2×100 eps v112, Thread-1 pinned roster (slot 0, natural roles:
  daf-actinf-crewborg-v3:v1, softmaxwell-crewborg:v34, sasmith-crewborg-hs1:v15, notsus:v130,
  scott-crewborg-hs1:v13, crewrift-prime-crewborg-aaln-hunter-relhalpha:v6, crewborg-aaln:v25).
  Baseline = W1's v111 arms `xreq_fab85490`+`xreq_2f42f740` — RE-VERIFIED per-episode this session
  (`/tmp/wh_v111_episodes`: 200/200 episode.json say crewborg v111 `8ec5a454`, slot 0, identical
  roster, all completed). Ops-fail eps excluded both sides; compare both arms' ops profiles first
  (the W2 platform-window gotcha).
- **GATES (all must hold):**
  1. No regression: crew win AND imposter win each not worse than v111 beyond noise (2-sided
     p < 0.05 against no-difference; point dips within noise OK).
  2. Mis-votes/crew-ep ≤ v111's measured baseline **0.232** (the combined-volume guard; W3b solo
     measured 0.127).
  3. **Warm-vote precision ≥ 85%** in warm-anchored meetings (the interaction guard: chat evidence
     + pile clause could double-count one HS speaker — an HS accusation is only ~63.8% precise —
     eroding W2's 100% warm-vote story).
  4. vote_timeouts ≈ 0 (slot 0); zero crew self-accusations; ops ~0 both arms.
- **MECHANISMS (must fire):**
  5. Anchor fires ≥ v111's 0.22/ep (expect ≥0.26 from W2; possibly higher if chat evidence pushes
     below-bar suspects onto eligibility — rate UP is fine, precision is what's guarded).
  6. `chat_evidence_applied` firing with HS-source predominance (W3b: 76% HS).
  7. `llm_spend` events 1:1 with LLM call attempts.
- **DIRECTIONAL (not gates):** crew vote precision toward 80%+ (W3b: 83.6%); imp-ejections/crew-ep up.
- **Interaction analyses to report regardless:** (a) warm fire-rate delta vs W2's 0.266/ep;
  (b) count of meetings where ONE external speaker both warm-eligibled the target AND satisfied
  the pile clause (the double-count channel) and their vote outcomes; (c) mis-ejections-per-crew-ep
  vs v111 (the W3b batch-drift yellow flag, now with a same-day-fresh cand arm).
- **Decision rule:** all gates + mechanisms pass → retire v111's membership `lpm_329ad382…` FIRST
  (audit reason), then SUBMIT v112 to Crewrift Prime (James's standing "submit at will" on a clean
  pre-registered verdict; league `league_a12f5172-0907-4d04-8bcb-ca02f5360e3a`), then targeted-poll
  the new pv to competing/active. Any gate fails → NO SUBMIT, diagnose.

## 👑 DONE (2026-07-22, W1): v111 SHIPPED — pre-registered confirmatory A/B CLEAN → SUBMITTED → QUALIFIED + CHAMPION

**crewborg:v111 is `competing/active` and CHAMPION** (`lpm_329ad382…`, submission `sub_c2f76ee6…`,
rank 14 / score 6553 at submit; v110's `lpm_cd2e6cbc…` retired first — the superseded gotcha).
**VERDICT: ALL pre-registered gates + mechanisms PASS** (cand `xreq_2f42f740`+`xreq_fab85490`,
200/200 eps 0 ops, verified v111 `8ec5a454` slot 0, identical roster to baseline):
- Gate 1 no-regression ✅ crew 25.2% vs 28.5% (p=0.52), imposter 63.3% vs 54.5% (p=0.37) — all noise.
- Gate 2 vote_timeouts ✅ **0/200 vs 2/199**. Gate 3 self-accusations ✅ **0**.
- Mech 4 anchor ✅ 44 fires/28 eps (0.22/ep), 44/44 accuracy, spoke-first 70.5% vs 14.3% (z=4.2).
- Mech 5 timeout ✅ APITimeoutError fallbacks **0/1482 vs 27/1505 (p=2e-7)**; success max 6.23s vs
  7.26s (9 over 6.05s in base).
- Mech 6 spend cadence ✅ **45.9 vs 1135.9 events/ep (−96%)**.
- Directional: accuse→ejection conversion 40.9% vs 28.6% (+12.3pp, p=0.34 — underpowered as
  pre-registered; direction confirms).
Full row: version_log.md v111. Analysis `/tmp/v111_ab/`, warehouses `/tmp/wh_v111` + `/tmp/wh_v110_base`.
The original prereg (registered before firing) is preserved below for the record.

### The W1 prereg as registered (verdict above)

## 📪 CLOSED (2026-07-22, W3): chat-provided evidence, trust-weighted — REFUTED as-shipped; mechanism validated; flag default OFF

James's directive (incorporate other players' chat into the posterior, weighted by
speaker trust, HS members ≈ full weight) is BUILT and A/B'd. Audit + design + verdict:
`docs/designs/2026-07-22-chat-evidence-incorporation.md`. What shipped in code (branch
`worktree-agent-abca9449cedbf8d00`): trust-weighted chat log-LR term in
`strategy/suspicion.py` (`chat_evidence_log_lr`, both scoring paths, LLM on/off
identical; capped ln 40 ≪ witnessed; applied before witnessed floor + HS pin), a
deterministic anchored-template extraction pass in `chat_evidence.py` (new `kill`
claim type; fixes the spaCy victim-accusation + "X killed Y"→nothing bugs), the
spaCy-loading defer fix in `social_evidence.py`, and the
`domain.chat_evidence_applied` counterfactual trace. 689 tests green.
**A/B (crewborg-chatev:v1 `0873f708`, xreq_a63252e9+xreq_d38011ed 200 eps vs v111
xreq_fab85490+xreq_2f42f740 200 eps): mechanism decisive (384 events, 47 chat-changed
votes) but chat-changed votes hit imposters 67.4% ≈ suspicion-alone 69.0% — field chat
adds vote VOLUME not precision; imp-ejections/crew-ep 0.490 vs 0.517 (primary fail);
total crew ejections 0.848 vs 0.662/ep (p=0.066, gullibility borderline).**
`CREWBORG_CHAT_EVIDENCE` now defaults OFF. Follow-up lever (unprobed): floor the trust
gate — testimony only from trust ≥ ~0.9 speakers (HS members + near-cleared), zeroing
the fabrication-prone stranger path. W5: do NOT fold chatev:v1 into the next ship.

## 📬 CLOSED (2026-07-22, W3b): chat-evidence TRUST FLOOR — SHIP RECOMMENDED (recipe-carried flags)

The W3 follow-up, probed. `CREWBORG_CHAT_EVIDENCE_TRUST_FLOOR` (default 0.9 when the
term is on): speakers below the floor contribute ZERO testimony — HS-verified (1.0)
and near-cleared (susp ≤ 0.1) only; `=0` reproduces v1; contradicted-self-alibi
un-floored. Offline power check on W3's retained cand telemetry FIRST: would-fire
0.57/crew-ep; claim precision by class HS kill/vent 22/22=100% vs strangers 64.4%
vs imposter-speakers 0/158=0% — the floor keeps exactly the perfect class.
**A/B (crewborg-chatev:v2 `977fc445`, xreq_eccbde9d+xreq_aea1ed31 200 eps 0-ops vs
the same v111 baseline arms): chat-changed votes hit imposters 92.1% (35/38) vs
v1's 67.4% (p=0.006); our mis-votes/crew-ep 0.127 vs 0.232 (−45%, p=0.030); vote
precision 83.6% vs 72.2% (p=0.031); crew win flat; imposter side untouched;
vote_timeouts 0/0.** Caveat handled: total crew-ejections elevation (p=0.089)
decomposes ENTIRELY into field ejections with no crewborg fingerprint (our voted-for
crew ejections 0.057/ep BELOW base; accusing chats DOWN p=0.013) — batch drift, not
the feature. **NEXT SHIP: carry `CREWBORG_CHAT_EVIDENCE=1` (+ default floor) in the
next `crewborg` version's recipe** — the confirmatory pre-ship A/B validates it
in-composition. Full verdict: design doc §W3b; version_log chatev:v2 row.

## 🚢 IN FLIGHT (2026-07-22, W1): v111 confirmatory A/B → ship

**v111** (`8ec5a454-4fea-43a1-a639-1efe30a8ca42`, uploaded 2026-07-22T16:41Z from main
`1018642`, v110 recipe exactly: LLM meetings + Haiku 4.5 + `CREWBORG_HS_SECRET`) = champion
v110's code + four merged, individually-validated changes: (1) first-mover anchoring accusation
(Thread 3, SAFE-POSITIVE), (2) vote-deadline fix — `SPEND_READ_CACHE_TICKS=24` +
`AUTO_SUBMIT_REMAINING_TICKS` 48→96 (Thread 5), (3) meeting-LLM timeout 3.0→6.0s (Thread 10,
SHIP-WITH-NEXT-VERSION), (4) palette cross-check test (no runtime effect). 666 tests green.

**PRE-REGISTERED A/B (confirmatory — a combination of individually-validated changes), registered
BEFORE firing the candidate arms:**
- **Design:** cand = 2×100 eps v111, Thread-1 pinned roster (slot 0, natural roles:
  daf-actinf-crewborg-v3:v1, softmaxwell-crewborg:v34, sasmith-crewborg-hs1:v15, notsus:v130,
  scott-crewborg-hs1:v13, crewrift-prime-crewborg-aaln-hunter-relhalpha:v6, crewborg-aaln:v25).
  Baseline = the 200 verified v110 eps in `/tmp/hs_on_baseline_eps` (`xreq_774a384d` +
  `xreq_edd0f75e`; per-episode verified: 200/200 crewborg v110 = `028ba9f3`, slot 0, identical
  roster). Ops-fail eps (score ≤ 0 connect/disconnect) excluded both sides.
- **PRIMARY (gates — all must hold):**
  1. No regression: crew win and imposter win each not worse than v110 beyond noise
     (2-sided p < 0.05 against the null of no difference; point estimate may dip within noise).
  2. vote_timeouts (slot-0) rate ≤ v110's rate (expect improvement from fix 2; v110 = 9/200-ish
     from the anchor A/B window — measure both arms identically).
  3. Zero crew self-accusations (regression check on the v110 fix).
- **Mechanism confirmations (must fire):**
  4. Anchor fires: `domain.meeting_decision` path=accuse on the first meeting tick / anchor
     trace events present at ≈ the Thread-3 rate (~0.19/ep).
  5. Zero successful meeting-LLM calls with latency > 6.05s (timeout fix; baseline had
     successes out to 7.26s under abort-retry).
  6. Spend-read cadence reduced: meeting_spend event frequency per meeting well below v110's.
- **Expected improvements (directional, NOT gates):** crew accusation→ejection conversion up
  (anchor); no_vote / vote_timeout down (deadline fix).
- **Decision rule:** all 3 gates + mechanisms 4-6 pass → SUBMIT to Crewrift Prime (James's
  standing "submit at will" on a clean pre-registered verdict; retire v110's membership
  `lpm_cd2e6cbc…` FIRST, then submit, then targeted-poll the new pv to competing/active).
  Any gate fails → NO SUBMIT, diagnose.

## ✅ DONE (2026-07-22, W4): Bedrock spend measurement + per-call telemetry — SHIPPED & VERIFIED

James's ask: "measure our own bedrock usage… track per-call spend in the policy and log it."
- **Shipped `domain.llm_spend`** — one event per LLM call attempt (success AND failure), both
  seams (meeting + commander): trigger, meeting_index, role, tokens, `est_cost_usd`,
  cumulative `episode_est_cost_usd`, error_class, cached-sidecar cross-check. Core:
  `crewrift/crewborg/strategy/llm_spend.py` (shared SpendLedger); emitters in
  `attend_meeting.py` + `commander/worker.py`; `events.py` drains every step (llm_spend
  always emitted; commander_* still gated). Audit + spend profile + budget recs:
  `docs/designs/2026-07-22-bedrock-spend-telemetry-design.md`. 675 tests green.
- **Verified hosted** on probe `crewborg-spendtrace:v1` (`xreq_e026d5fe`, 100 eps): 1,024
  events exactly 1:1 with legacy signals; cost math matches the sidecar in production
  (median delta +$0.000000). One live-caught bug (meeting_index stuck 0 — mode recreated
  per meeting) fixed; confirmation probe `crewborg-spendtrace:v2` (`xreq_77c6b2e3`, 40 eps).
- **Headline findings:** 429-failed calls are FREE (rejected pre-inference — verified);
  whole-episode LLM bill ≈ $0.008/seat ($0.77/100-ep eval, ~$7/heavy night); all 4 triggers
  cost the same ~$0.0033/success and none converts dramatically worse → budget=5/interval
  120 correctly sized; **dollars are NOT the binding budget, the daily-token pool is** —
  quota-ask doc now carries the dollar counterfactual. `domain.llm_spend` telemetry should
  ride into the next `crewborg` version (it's in this branch's lineage for the merge).

## ✅ DONE (2026-07-22, W2): warm first-mover anchor — A/B SHIP RECOMMENDED (for W5's combination build)

**The anchor's rate-of-fire lever, validated.** `crewborg-warm:v1` (pv `2976ec7c`, v111 code +
`suspicion.warm_anchor_suspect` + attend_meeting warm route, branch `worktree-agent-aeed298a0eb592f2e`
@ `da6bb75`) vs W1's v111 arms: total first-mover fires **0.266/ep vs 0.220** (PRIMARY bar met), warm
route **0.065/ep at 84.6% accuracy**, crew win 30.4% vs 25.2% (directional), all hard guards clean,
warm-meeting vote precision 100% (chat decoupled from vote; pile clause escalates, lone ballots gate
to skip). KEY MEASUREMENT (reusable): the fitted posterior is **bimodal** — every 0.9-bar top suspect
is a witnessed catch, non-witnessed tops max p=0.74, so softer POSTERIOR bars unlock nothing; the
below-bar separation lives in the SOCIAL counters (rule: tail_max≥96t + times_accused≥1 + votes_cast≥1
+ no button/report/watched-task = 89.4% offline / 84.6% live precision; ML ceiling AUC 0.82 says more
is the suspicion-v5 refit). Design `docs/designs/2026-07-22-warm-anchor-design.md`; prereg + verdict
table `docs/designs/2026-07-22-warm-anchor-ab-prereg.md`; version_log `crewborg-warm:v1` row.
GOTCHA hit: run 1 invalidated by a platform-wide connect-timeout window (19:03–19:08Z, 61% of eps,
all slots) — always compare BOTH arms' ops profiles before reading an A/B.

## ⚖️ CLOSED (2026-07-22, Thread 4): the social-rework question — VERDICT: mechanism-positive, episode-neutral at current quota → deterministic-first until the quota is fixed

**The open bet since v101-v105 ("does the LLM social path, when it fires, beat the deterministic
path?") is SETTLED — observationally, without new episodes.** Design: within tonight's 5 LLM-on
arms (v110 197, v107 99, anchor 195, hsoff 197, survive 198 analyzable eps — all v110-lineage social code,
same pinned roster/slot 0), every alive crewborg meeting attempts an LLM call (first-call-always),
and whether *call #1* succeeds is decided by the shared-pool 429 state — near-random assignment.
Compared LLM-decided vs fallback-decided meetings on warehouse ground truth (2,561 alive meetings;
1,728 crew / 833 imposter), Mantel-Haenszel across arm×hour and arm×meeting-idx strata; scripts
`/tmp/t4_social/*.py`, per-meeting table `/tmp/t4_social/meetings.csv`.

**Crew side (first-call stratum, n=396 LLM vs 1,332 FB): the LLM path IS better when it fires.**
- Vote precision identical (hit-imposter | voted: 67.7% vs 67.9%) but volume 1.7× (voted-a-player
  33.6% vs 19.7%, p<0.001) → net correct-imposter votes/meeting **22.7% vs 13.4%**.
- Imposter ejected in the meeting **14.9% vs 10.1%** (MH arm×hour OR=1.49 p=0.018; arm×meeting-idx
  OR=1.47 p=0.027); accusation→ejection conversion 16.4% vs 10.9% (p≈0.007); crew mis-ejections NOT
  up (26.0% vs 23.6%, NS). Within-episode paired (375 eps with both): imposter-ejected diff +5.1pp
  (sign test p=0.010), conversion +7.1pp (p=0.001). Negative control clean: in meetings where we
  neither accused nor voted, LLM-meetings show NO ejection lift (0/52 vs 7.8%) — the lift rides on
  OUR actions, not pool-state luck. Residual selection risk stated: 429s cluster by time; hour+
  meeting-idx strata and the within-episode pairing all agree, but assignment is not literally random.
- Cost of the path: the LLM round-trip delays our first chat (median 77-79t vs 39-41t when call #1
  fails → deterministic fires) — the anchor lever (merged post-v110) already mitigates at meeting start.
**Imposter side: neutral-to-negative.** Deflection-win NS everywhere (MH OR=1.24 p=0.33); raw
self-ejected 20.1% vs 11.9% (p=0.005) but collapses under meeting-idx stratification (OR=1.34
p=0.23) — no evidence the LLM helps the imposter; weak evidence its extra chat/vote volume draws fire.
**Episode level: NOTHING propagates at current firing rates.** Crew win hi-vs-lo LLM exposure 26.5%
vs 25.4% (z=+0.30, pooled 639 crew-eps); imposter 60.7% vs 61.4% (z=−0.11); winners' mean exposure =
losers'. Implied total effect of the whole LLM path ≈ ±1-3pp crew win → 3,300–25,000 eps/arm to detect.
**Part B (detonly:v1 vs v110 A/B) SKIPPED — structurally uninformative:** at 200 eps/arm the MDE is
12.3pp crew win / ~5.1pp meeting-level ejection vs an expected ~2.4pp shift (only ~50% of meetings
change provenance); it would burn ~400 eps of the same throttled pool to learn nothing the
observational design (which controls field + pool-state better) hasn't already.
**VERDICT: keep `CREWBORG_LLM_MEETINGS=1` for crew (it's free upside when it fires, no downside
measured), but further LLM-social prompt investment at ~26-38% production firing is ~zero marginal
value — deterministic-first (anchor lever, vote coordination) until the quota moves. The durable fix
is the quota ask: `docs/bedrock-quota-ask.md`** (9,102 calls → 78% fail, 99.0% = daily-token 429;
removing 429s lifts meeting decision coverage ~26-50% → ~99%; ~27K tokens/seat-episode demand).

## 🎖️ DONE (2026-07-22, Thread 8): HS ecosystem follow-ups — isolated A/B (HS-NEUTRAL/mechanism-positive), liar-ledger consumer shipped, Alex note written

**1. HS isolated A/B (first ever — HS always shipped bundled).** Probe `crewborg-hsoff:v1`
(= v110's byte-identical image + recipe + `CREWBORG_HONOR_SOCIETY=0`; 114/114 image files
hash-verified vs main `9b9606c`), 2×100 paced arms (`xreq_dacceb4c`+`xreq_07fab795`) vs the
pooled 200 v110 HS-on eps (`xreq_774a384d`+`xreq_edd0f75e`), Thread-1 pinned roster/slot0/
natural roles. Pre-registered BEFORE launch (`docs/designs/2026-07-22-hs-isolated-ab-prereg.md`).
**VERDICT: HS-NEUTRAL at episode level, mechanism-positive** — crew win 28% vs 28% (z=+0.02;
only ~+15pp detectable at this n, as pre-registered); but the trust loop is REAL: OFF arm 0 HS
events in 200/200 artifacts (disable path verified), ON arm announced 138/199 + verified members
188/199 + veto fired 20 eps at **20/20 accuracy** (all spared seats truly crew), and **HS members
(sasmith/scott) vote against our crew 3× less when we announce** (0.31 vs 0.97 votes/ep, z=−7.1).
Keep HS ON; the win-rate payoff needs Direction-1 vote coordination to monetize the trust.
Anomaly flagged (unexplained, small-n): imposter-role HS-member votes against us UP with HS on
(1.68 vs 1.02/ep, z=+3.0; possibly kills-confounded 1.61 vs 1.42). Artifacts: `/tmp/ab_hsoff/`.
⚠️ Disk-dir gotcha: `/tmp/wh_anchor_base_v107_episodes` actually holds a v110 arm and
`/tmp/wh_anchor_base_v110_episodes` is half v107 (`xreq_136dd84f`) — always re-verify per
episode.json `policy_version`, not dir name. True 200-ep v110 baseline: `/tmp/hs_on_baseline_eps`.

**2. Liar-ledger consumer BUILT (the standing TODO).** `tools/harvest_liars.py` scans harvested
telemetry (loose jsonl + policy_artifact zips) for `domain.honor_liar`, dedupes per-tick repeats,
**validates each accusation against results.json ground truth**, and (with `--write`) renders the
vendored `crewrift/crewborg/data/honor_distrust.json`; `honor_society.py` gained the consumer seam
(`is_distrusted` → verified-liar keys pre-ledgered in `process_chats`, never trusted, traced
`honor_distrusted_announce`; `CREWBORG_HONOR_DISTRUST` override). **Key finding: the in-game liar
witness has FALSE POSITIVES — 6/199 baseline eps ledgered alex-smith's key while the accused seat
was actually CREW** (kill/vent misattribution); the ground-truth gate exists because of this.
Corpus scan (675 sources/234 eps): 0 confirmed lies, 6 refuted witness errors → list ships empty.

**3. Alex note written:** `crewrift_lab/docs/hs1-ecosystem-notes.md` (same-key-multi-seat vs
first-poster-wins, encoding canonicalization, publish-the-compact-form, palette pinning, verifier
cost at scale, registry/liar-ledger interop + the witness-false-positive warning). For James to send.

## 🔍 DONE (2026-07-21, Thread 5): residual alive-seat vote_timeout ROOT-CAUSED — client lag, not logic; FIXED on main (needs next version)

**Measured** (the three anchor A/B warehouses, /tmp/wh_anchor_*): crewborg alive-seat timeouts
9/579 alive-meeting-seats (1.6%/meeting, 3.5%/ep) cand, 6/563 (1.1%) v110, 1/279 (0.4%) v107.
**All 16 timeout meetings reconstructed tick-by-tick from slot-0 telemetry.** Hypotheses (a)
action-layer cursor failure, (b) mode-routing gap, (c) meeting never detected, (d) reconnect —
ALL REFUTED in their original form: AttendMeeting was entered on the meeting's first tick in
16/16, the auto-submit fired on time *by the belief clock* in 15/16 (48-55 ticks left), and the
cursor walk itself is correct (the one A-press case cast skip at believed-tick 2276, 4 ticks
before the believed deadline).

**Root cause: the belief clock lies under load.** The bridge stamps ticks from *queued* frames;
meeting ticks run over the ~42ms frame budget, frames queue, and the client falls behind the
server — cumulative lag measured **+54..+689 frames** at the failing deadlines (OK meetings:
+17..+95). So "48 ticks left" was often ZERO real ticks: the server's tally had already fired.
`bridge.tick_drift` is blind to this (it measures received-vs-processed, not arrival lag) —
use cumulative `loop_gap_ms` excess instead. The per-tick budget breaker is the **blocking
`/spend` sidecar HTTP GET issued EVERY meeting tick** (`_spend_allows_followup`): spend ticks
median 34-55ms, 56-74% over budget vs 5-9% for playing ticks. One 321064c8 case was hypothesis
(d)-adjacent: an 825-tick frame stall (mid-game disconnect + reconnect) swallowed the whole
deadline window.

**Fixed on main (rides the NEXT version, not uploaded):** `modes/attend_meeting.py` —
(1) `/spend` read now cached `SPEND_READ_CACHE_TICKS=24` (~1s) instead of per-tick;
(2) `AUTO_SUBMIT_REMAINING_TICKS` 48→96 to absorb residual lag. Regression test
`test_attend_meeting_spend_read_is_cached_across_ticks`; 661 passed. Residual risk: the
disconnect-stall case (1/16) is unfixable client-side; deeper fix (server-authoritative
vote-timer sprite already exists as `timer_present` — could read the actual remaining time)
deferred as not worth it at 1-2%/meeting.

## 🔧 DONE (2026-07-22, Thread 10): meeting-LLM call-failure mitigation — timeout 3→6s SHIP-WITH-NEXT-VERSION

Re-measured the 07-02 TODO on the v110 A/B arms (199 seats, 2084 calls): 74.5% call-fail, but
**1536/1553 errors = the shared daily-token-pool 429** — uniform across triggers, NOT
pacing-correlated (fail/success inter-call intervals identical, median 120 ticks both). So the
TODO's interval-raise/trigger-drop levers are REFUTED: retries are the coverage mechanism
(45/561 meetings got their first decision only at call 4-5). The real self-waste: the 3.0s
timeout client-aborted **40% of ultimately-successful calls** (success latency median 2.8s /
p90 4.0s) into SDK retries that double-spend ~2.5K input tokens each into the throttled pool.

**Shipped (committed this branch):** meeting timeout default **3.0→6.0s**
(`strategy/meeting/llm.py`, new env `CREWBORG_LLM_MEETING_TIMEOUT_SECONDS`; commander untouched;
deadline geometry follows automatically: latest-safe-start 132→204/1200) +
`CREWBORG_LLM_MIN_CALL_INTERVAL_TICKS` env knob (default 120 unchanged). 661 tests green.
**Probe verdict (crewborg-llmcadence:v1, xreq_f5e7a285, 100 eps): ALL PRE-REGISTERED CRITERIA
PASS** — abort-retry waste eliminated (0 successes >6.05s, max 4.94s vs baseline 7.26s; 0
timeout-bucket fails vs 17), coverage 52.5% ≈ contemporaneous same-night arms (52.6%/49.5%),
fails/meeting 2.40 = lowest of the night's 4 arms, vote_timeouts 0. → rides into the **next
crewborg version**. Residual: 429 pool contention is fleet-level — only cheaper tokens/call or
a bigger pool (quota bump on 583928386201) moves it. Design + criteria table:
`docs/designs/2026-07-21-meeting-llm-cadence-design.md`; version_log has the probe row.

## 🎯 DONE (2026-07-21, Thread 1): v110 A/B'd clean vs v107 → SUBMITTED → QUALIFIED + CHAMPION 👑

*(Superseded 2026-07-22: v111 is now champion — see W1 above; v110's membership retired.)*
**crewborg:v110 was `competing/active` and CHAMPION** (`lpm_cd2e6cbc…`; submission `sub_16bcf7fb…`,
qualified in ~3 min). v107's membership retired (`lpm_fd1323fc` → disqualified/inactive) — REQUIRED
first: the initial submit (`sub_326bf021`) was insta-disqualified "superseded" because the platform
keeps the incumbent (even benched) and retires the newcomer. Watch v110's league standings recover
(rank inherited ~14/18); HS1 is now live in league play for the first time.

**v110** (`028ba9f3-7dfc…`) = v109's code (HS1 compact fix + palette fix + HS default-on) re-uploaded
with the **v107-equivalent LLM meetings recipe + `CREWBORG_HS_SECRET`** — v109 as uploaded was
deterministic-only (no `--use-bedrock`/`CREWBORG_LLM_MEETINGS`), a confound vs the champion. A/B is
like-for-like: matched pinned rosters (current live champion labels: daf-actinf-crewborg-v3:v1,
softmaxwell-crewborg:v34, sasmith-crewborg-hs1:v15, notsus:v130, scott-crewborg-hs1:v13,
crewrift-prime-crewborg-aaln-hunter-relhalpha:v6, crewborg-aaln:v25), crewborg pinned slot 0,
natural roles, ~200 cand / 100 base eps, ≤400 concurrent (paced arms ≤100 eps each).

**PRE-REGISTERED verdict criteria (written before launch):**
1. PRIMARY: crew self-accusation chat = 0 in candidate (own-color accusations in chat telemetry);
   no false dead-mutes (meeting_dead_mute thousands of ticks before actual death) in candidate.
2. Imposter win rate and kills/seat NOT worse than v107 (bug fix — expect neutral-to-better).
3. Crew win rate not worse than v107.
4. Ops% ~0 both arms; vote timeouts ~0.
If ALL pass → submit v110 to Crewrift Prime (standing authorization). Any fail → report, no submit.

**RESULT (2026-07-21): VERDICT CLEAN — all 4 pre-registered criteria PASS.** Four matched arms,
all completed 100/100, 0 failed:
- Pinned-roster (crewborg slot 0): cand `xreq_774a384d` + `xreq_edd0f75e` (199 eps fetched),
  base `xreq_136dd84f` (100 eps). Confirms slot-0 behavior unchanged.
- Rotating-seat pair (all seats round-robin — slots ≥1 are where the palette bug lives):
  cand `xreq_276e3849`, base `xreq_f1f64260` (~100 eps each; the arm's own ~2-3 no-artifact
  eps + episodes with any seat connect/disconnect-timeout dropped as ops-dirty).
Measured (scan: `.tmp/ab_v110_v107/primary_check.py`; compare: crewrift-ab compare.py):
1. PRIMARY ✅ — crew self-accusation chat: **0 msgs/0 eps in v110** (285 eps incl. 74 non-slot-0);
   v107 reproduced the bug in the same window: 2 msgs/1 ep ("orange sus… vote orange", slot 4)
   + **6 false dead-mutes** (mute 1200-1800 ticks before death, e.g. mute@2675 death@4501; one
   while never dying). v110 false dead-mutes: **0** (rot + pinned, 88 dead-mute eps checked).
2. Imposter ✅ — pooled clean: win 60% (43/72) vs 61% (27/44), z=-0.18 noise; kills/ep 1.68 vs
   1.59. (Pinned arm looked -19pp at n=30 base / rotating arm +35pp p=0.04 — opposite-signed
   small-n noise; pooled = flat.)
3. Crew ✅ — pooled clean: win 27% (50/186) vs 25% (26/106), z=+0.44 (noise, right direction);
   no_vote_rate crew improved 4%→0% (p=0.01) in the pinned arm.
4. Ops ✅ — pinned arms 0% ops both; rotating arms ~20-28% ops-dirty BOTH arms (field-side
   connect timeouts, symmetric; dropped before comparing). vote_timeouts 2 vs 5.
Bonus: HS1 now live — v110 announced in 138/199 pinned + 44/86 rot eps, honor_known_member in
188/199 (v107: 0 everywhere). LLM fired both arms (cand 524 decisions/1506 fallbacks ≈ 26%,
base 188/817 ≈ 19% — same low-rate regime as the v107-vs-v100 A/B).
→ **SUBMITTED v110** to Crewrift Prime per James's standing "Submit at will" — see DONE header above.

## ❌ DONE (2026-07-22, Thread 13): the Thread-2 kill→WIN levers BUILT + A/B'd → REFUTED, do not ship

Both pinned levers implemented (`crewborg-survive:v1` probe, pv `82c4a42e`, v110 recipe;
code on this branch: post-kill flee in `modes/evade.py` + counter-accuse/first-mover in
`modes/attend_meeting.py`+`strategy/meeting/imposter.py`) and A/B'd 200 cand eps
(`xreq_9ec4f8bc`+`xreq_d998c7fb`, 0 ops) vs 300 v110-lineage eps. **All outcome criteria
FAILED with both mechanisms decisively firing** (full prereg table:
`docs/designs/2026-07-21-imposter-survival-ab-prereg.md`; version_log `crewborg-survive:v1`).
1. **The "4px lies-in-wait" premise below is a MEETING-FREEZE ARTIFACT.** Kill→meeting
   median latency is 77–91t for everyone; at +60t killers sit frozen in MeetingCall.
   Conditional on still-Playing, v110 already moved 100px (field 131). Retire the
   unconditional displacement metric — always phase-filter movement metrics.
2. **Post-kill flee is HARMFUL:** kills/seat 1.81→1.38, 3+-kill seats 21.5%→5.5% (p=0.01)
   — the kill room is the crew-dense room; leaving forfeits the snowball. The 2026-06-26
   crowd-seeking Evade design is re-confirmed. CLOSED lever.
3. **Meeting deflection fired (spoke-first 0→23.7%, z=8.7) but drew MORE votes**
   (1.14→1.28/meeting); ejection/win unmoved-to-worse. Fabricated counter-accusations
   from a seat under heat escalate rather than deflect in this field. If ever retried:
   real-evidence-only counter-accuse, no fabrication. CLOSED as designed.
The witnessed-kill→ejection gap itself (53% vs field ~30%) REMAINS unexplained-open, but
neither scene-fleeing nor meeting-talking is the lever; the next candidate direction is
pre-kill witness avoidance… which is the 3×-refuted witness-gate. Treat the whole
imposter-survival axis as cold until a new mechanism is found.

## 📊 DONE (2026-07-21, Thread 2): imposter-conversion picture RE-DERIVED on v110 data — conversion is NOT the lever; kill→WIN (meeting survival) is
**⚠️ 2026-07-22 UPDATE (Thread 13): the two recommended levers below were built and
REFUTED — see the Thread-13 section above. The 4px post-kill figure is a measurement
artifact. Numbers kept for the record.**

**Read-only analysis; supersedes the imposter numbers in the 2026-07-21 live-round audit below**
(those were v107 + palette-bug + definition-sensitive). Data: tonight's matched A/B warehouses
(`/tmp/wh_anchor_base_v110` 200 eps, `/tmp/wh_anchor_base_v107` 100 eps, `/tmp/wh_anchor_cand`
200 eps — anchor probe runs v110's imposter code, so "v110-lineage" pools it), rotating-seat
arms rebuilt (`/tmp/wh_rot_v110`, `/tmp/wh_rot_v107`, 100 eps each), fresh league rounds
(`/tmp/wh_v110_league`, 26 eps). Queries: `/tmp/t2_imposter/*.py`. Field = the 7 pinned opponents
in the same episodes. trace_warning eps (6-15%) retained — they carry full kill/state events
(trace fails partway; spot-checked).

**Three conversion definitions, pre-registered, all measured (imposter seats):**

| metric | v107 (n=30) | v110 (n=56) | anchor=v110 code (n=49) | field range |
|---|---|---|---|---|
| (a) isolation≥48t w/ crew → kill in window+60 | 23.5% | **12.2%** | 18.4% | 16.8–31.2% |
| (b) ready+victim-visible window → kill in +60 | 73.5% | **76.9%** | 68.2% | 58.7–70.9% |
| (c) kills/imposter-seat | 1.77 | 1.61 | 1.84 | 1.31–1.65 |
| imposter win% | 73.3 | 53.6 | 65.3 | 59.3–77.0 |
| ejected% of seats | 40.0 | **57.1** | 36.7 | 19.8–30.5 |
| votes received/seat | 3.17 | **3.80** | 3.71 | 1.70–3.18 |
| kill-ready ticks w/ victim visible | 58.3% | 25.9% | 23.9% | 10.8–42.4% |

1. **Definition sensitivity is decisive (July-02 lesson replicates).** Defs (a) and (b) give
   OPPOSITE verdicts on the same episodes: under (a) crewborg is bottom-tier; under (b) it's the
   FIELD-BEST converter (v110 76.9% vs field pooled 66.2%, p=0.017). Def (a) counts vote-frozen/
   cooldown-blocked isolation windows; def (b) at +0 ticks is 0% for everyone (the visibility
   interval ends AT the kill) and jumps to ~70% at +30. The audit's "19% conversion" was def (a)
   — retire it. **Strike-and-convert ability is fine; there is no conversion lever.**
2. **Palette-bug decomposition: weak, seat-consistent, does not explain the ejection gap.**
   Slot-0 pinned arms (palette correct in BOTH): all imposter diffs NS (win 53.6% vs 73.3%
   p=0.11, kills 1.61 vs 1.77, eject 57.1% vs 40.0% p=0.18 — n=56/30). Rotating slots≥1 (where
   the bug lived): v110 win 64.7% vs v107 35.7%, eject 41.2% vs 71.4% (both p≈0.15, directional,
   n=17/14) — consistent with the shielded-innocent effect at bugged seats, but the belief-level
   target-pool shrinkage is unmeasurable from replays (visibility events are role-truth, not
   crewborg's belief). Fresh league v110 (n=8 imp seats): kills/seat 1.75, win 62.5%, eject 12.5%
   — small-n, no red flag.
3. **Contact starvation no longer dominates as a crewborg-specific deficit.** v110 ready ticks/
   seat = 307 — 2nd-LOWEST in field (field 219–1414; the July-02 96%-starved figure described a
   pre-recon/search build). Ready→kill latency 1348t = mid-field (643–2019). The recon/search
   victim-finding work landed; **victim-finding/approach is not the open lever either.**
4. **THE deficit (new, significant): witnessed kills + zero meeting defense → ejection.**
   - Kills made while isolated with victim: v110-lineage 15% vs field 31% (p=1.7e-5); mean
     witnesses at kill tick 1.4–1.6 vs best-field 0.9; 1st kill witnessed 80% vs field 67%
     (p=0.007).
   - Ejected AFTER a witnessed kill: v110 62.2% vs field 31.6% (p=6e-5) — caught AND convicted.
   - Post-kill flee: median 4px moved in 60t after own kill (field 23–40px) — it lies in wait ON
     the scene (`modes/hunt.py` post-strike / lying-in-wait).
   - Meeting play: imposter speaks in 31.6% of meetings-alive, speaks FIRST 0.0% (field 40–98%
     spoke, 40–98% first) — `_decide_imposter` (modes/attend_meeting.py:310) has only
     proactive-real-evidence / bandwagon / parity-push / silent-skip paths; **no response-when-
     accused exists**, and the LLM round-trip forfeits first-mover anchoring (which Thread 1
     proved converts at 28.7% vs 12.5%).
   - NOT follow-stalking: follows-emitted 6.2/seat and times-trailed 4.8/seat are field-LOW —
     the audit's "follow-heavy stalking" reading is refuted.

**RECOMMENDATION — next imposter lever: kill→WIN conversion (meeting survival), two concrete
mechanisms, both sanctioned by best_practices (parity-push precedent +14.4pp win) and WEEKLY
Direction 5(b) "deflection-when-accused has never been built":**
1. **Accused-response deflection** in `modes/attend_meeting.py:_decide_imposter` +
   `strategy/meeting/imposter.py`: when self is taking heat (votes/chat targeting self), emit a
   counter-accusation/alibi instead of idling to a skip; pair with the Thread-1 anchor seam
   (first-decide-tick deterministic chat) so the imposter can speak first — 0% today.
2. **Post-kill flee** (`modes/hunt.py` after strike): leave the kill scene (field moves 23–40px
   in 60t; we move 4px). Cheap, independently A/B-able.
   NOT witness-gate tuning (refuted 3×), NOT victim-finding (already field-competitive), NOT
   kill volume (structurally capped). Cross-ref: pre-meeting suspicion warming (anchor follow-up)
   is the crew-side twin of the same "arrive at the meeting armed" principle.

## 🔧 SIDE-THREAD (2026-07-21, merged to main): Honor Society was DEAD in live play — FIXED + verified (crewborg:v109, NOT submitted)

Discovered the HS was a **no-op in every real game**: our code used a LEGACY 5-token `HS1` form,
but live members (sasmith-crewborg-hs1:v15) use the **compact** `HS1 <sig>` (sig over
`HS1|<ts5>|<color>`, ts5=(unix//5)*5, unpadded b64url; brute-force verify over ledger keys × a
{now5,-5,-10,+5} window; no first-poster-wins). `parse()` returned None on every real line. ALSO
found `PLAYER_COLOR_NAMES` stale since the game's 2026-06-24 palette change (`1cbd4de`) — slots ≥1
all wrong, corrupting v106's slot-seed self_color for non-slot-0 seats (latent bug beyond HS). Fixed
both; `CREWBORG_HONOR_SOCIETY` now **defaults ON**. Proved the compact spec by verifying 17/17 live
captured sigs vs sasmith's registered key. Uploaded **crewborg:v109** (traced) and verified END-TO-END
via `xreq_25bb7e0f` (v109 crew + sasmith crew): crewborg's trace shows `society: crew announce` +
`honor_claim`/`honor_known_member {label:alex-smith}` — we now send, verify, and register real HS1.
641 tests green; committed on the branch. **NOT submitted** (James's gate). Next if pursued: measure
whether HS actually helps (it's never been A/B'd in isolation), then the coordinated-vote-piling
direction (WEEKLY_CONTEXT Direction 1). Full detail: version_log v109.

## OBJECTIVE (superseded 2026-07-21 — v110 is champion now, see DONE above): v107 era

**v107 was `competing/active` and CHAMPION** in Crewrift Prime (qualified in ~5 min,
2026-07-15 17:10Z; membership `lpm_fd1323fc…`, Competition division). v106 is
`competing/benched` (no longer champion, benched by supersession). v107 = v106's fixes +
the self-hunt fix, A/B-verified (imposter restored to v100 level; see below). Standings
inherited from the damaged-v106 era: ~rank 14/16 — **watch whether rank/score climb over the
next ~50-100 rounds now the imposter actually kills opponents instead of itself.**

**2026-07-21 LIVE-ROUND AUDIT (10 rounds, 199 eps, warehouse /tmp/wh10, survey /tmp/survey10.html):**
v107 is rank **14/18** (52.4% WR; leader 60.8%). Role split in the sample: crew 27% (11/41, field
median ~32%), imposter 41% (7/17, field ~55-77%). Three mechanistic findings:
1. **SELF-ACCUSATION BUG (new, smoking gun):** crewborg *as crew* chats "orange sus: lurking on a
   vent, they were tailing me. vote orange" — its OWN color — 5 msgs / 2 eps
   (ereq_94c9f0fc: field then ejected it; ereq_e502d991). The deterministic accusation template can
   select self as suss target (self_color missing from the candidate filter — same class as the
   v106 self-hunt bug, but in the meeting/accusation path). It skip-votes while doing it, so the
   vote self-exclusion works; the CHAT target pool doesn't exclude self.
2. **Imposter too conspicuous + too timid** — ⚠️ SUPERSEDED by Thread 2 (2026-07-21, above):
   the "19% conversion" was definition-artifact (def (a); under kill-opportunity windows crewborg
   is field-BEST), and "follow-heavy stalking" is refuted (follows/seat field-LOW). What survives,
   re-measured on v110: ejected-after-witnessed-kill 62% vs field 32% (p=6e-5), isolated kills 15%
   vs 31%, speaks in meetings 32% / speaks first 0%. Original audit numbers (v107, palette-bugged):
   ejected 53% of seats, votes-received/seat 2.47, kills/seat 1.29.
3. **Crew draws suspicion:** votes-received/seat 1.37 as crew (2nd-worst), 15% of crew seats
   ejected — opponents (and framing imposters) cite "tailing me / lurking on a vent", i.e. its
   crew movement pattern trips the same detectors.
   Also: league telemetry shows LLM fired only ~38% (154 decision / 248 fallback, 236 Bedrock
   throttle lines over 58 eps) — production meetings mostly run the deterministic path.

**Next-lever candidates (from the 2026-07-15 session):** (1) residual ~7-9% alive-seat
vote_timeout — ~~cheap telemetry dig, never done~~ DONE Thread 5 (root-caused + fixed on main);
(2) ~~the social-rework crew-win question is STILL open~~ **CLOSED 2026-07-22 Thread 4** (see
verdict block at top: mechanism-positive crew-side, episode-neutral at current quota,
deterministic-first until the quota moves); (3) mine v107's live
rounds with coworld-hypothesis-miner / the top-3 advantage methodology
(docs/top3-advantage-reporter-guidance.md).

**What v106 is (the fix):** kills the v105 `no_vote`/vote_timeout regression. Root cause (replay-
confirmed): v105's `self_alive` went **falsely False** — the one-shot self_color latch stuck a
neighbour's colour pre-meeting; the census self-death check (types.py:776) flipped self_alive off when
that neighbour died; dead-mute then idled a LIVE meeting → game's "-10 for failing to vote" (19/200 v105,
0/200 v106). 3-layer fix (638 tests green): (1) seed self_color from runner `?slot=` (zero-CV — slot IS
colour, like suspectra); (2) self_color source hierarchy (marker/slot latches hard, corrects a
provisional sprite guess once — keeps v102 anti-drift); (3) dead-mute still SKIPs at the deadline
([[crewborg-idling-is-dangerous]]). version_log v106 has the detail.

**Validation state (honest):** v106 is SOUND but NOT proven better than v105.
- ✅ dead-mute vote_timeout fixed: 0/172 matched A/B (v105 8.6%).
- ✅ sound at ≤100-concurrent: 0% dead-game, LLM 73%, crew win 29% / imposter 56% (`.tmp/v106_field/eps100`).
- ⚠️ the matched v106-vs-v105 A/B win-rate is CONTAMINATED — fired 4×100=400 at once → opponent pods
  connect-timed-out → 76% dead games (ZERO at ≤100). LESSON: pace arms as separate ≤100-ep requests.
- ⚠️ residual ~7-9% alive-seat vote_timeout remains (separate, pre-existing; NOT the dead-mute path).

**🚨 A/B VERDICT (2026-07-15): v106 imposter SELF-HUNT BUG — the CHAMPION is hunting its own
sprite.** The paced v106-vs-v100 A/B (200 cand / 100 base eps; stopped early — verdict decisive;
round-3 xreq cancelled) found: imposter win 71%→35% (p=0.005), kills 1.58→0.58, zero-kill imposter
games 4%→44%. Root cause (telemetry-confirmed, 45/53 cand imposter eps, 0/50 base):
`visible_victims()` (strategy/opportunity.py:147) filters only `teammate_colors` and NEVER excluded
`self_color` — in v100 self was accidentally protected because reveal ingestion put OUR OWN color
into teammate_colors; v106's ingest-time self-exclusion (types.py:868-871, the correct v102-fix)
removed that shield, and select_victim's most-isolated heuristic now locks onto the self sprite
(always visible, dist ~6.3, 111,568 self-strikes vs 24 real). Crew metrics unchanged; LLM fired
27%/19% (<60% gate) so the social rework is STILL untested. Artifacts: `.tmp/ab_v106_v100/`
(diff.json, ab.html, finding.md, compare.md; arms in cand/ + base/).

**v107 SHIPPED + A/B VERIFIED (2026-07-15, commit `6cfdffb`, pv `5a4e0eae…`) — the self-hunt fix
works.** Fix: new `opportunity.is_live_opponent` (not self / not teammate / not dead) at every
roster-derived imposter pool; 7 regression tests; 645 green. **A/B verdict (196 v107 / 100 v100
matched eps):** self-strikes 0/36 imposter eps (v106: 45/53); kills 1.67 vs 1.28 (v106: 0.58);
zero-kill 3% vs 11% (v106: 44%); imposter win 64% vs 61% (v106: 35%); crew all noise. Pure-bug-fix
profile: no regression anywhere. Artifacts: `.tmp/ab_v107_v100/` (diff.json, ab.html, finding.md).
Caveat (same as v106 A/B): LLM fired ~19-27% both arms → deterministic path compared; fine, the fix
is deterministic-only. NOTE: mid-A/B the platform 500'd on GET/POST /v2/experience-requests
("Coworld Manifest tags Field required", ~15:55-16:45Z) then recovered; babysitter drained the
stuck batches.

**v107 SUBMITTED (James's go-ahead) + QUALIFIED + CHAMPION (2026-07-15 17:10Z, ~5 min
qualifier):** `sub_acd40308…`, membership `lpm_fd1323fc…` `competing/active` champ=True;
v106 → `competing/benched`. (Ops note for next submit: the skill's `monitor --watch` again
terminated on the OLD champion's 'competing' — use a targeted by-pv-id poller,
`.tmp/poll_v107_qualify.py` is the template.)

**Next action: when the 4 watchers drain (~10-15 min), (1) confirm vote_timeout→~0 on v106; (2) run
compare.py role-split. If clean, the v105 social rework (minus this bug) is worth a powered ~300/arm
A/B vs v100 to settle the crew-win signal (was 15%→22%, p=0.11, underpowered). Do NOT submit yet.**

<details><summary>The v105-vs-v100 social-rework A/B result (2026-07-09, the run that surfaced the bug)</summary>

400 eps, paced, LLM GATE PASSED (v105 71.6% / v100 81.9% seat-0 decision rate — first clean test of
the rework vs all the throttled historical data). crew win 15%→22% (p=0.11, underpowered ~160 crew /
~40 imposter per arm); imposter 57%→59% (p=0.86, flat); **the no_vote_rate regression** 0%→9% crew /
0%→14% imposter that v106 now fixes. Artifacts: `.tmp/ab_v105_v100/` (diff.json, ab.html, finding.md).</details>

<details><summary>Prior objective (done): run the paced A/B so the LLM fires</summary>

The chat-persuasion social rework is built + uploaded (v105) but had **never been cleanly
A/B-tested** — every attempt was starved by Bedrock throttling until we fixed the token cost.
Ran it paced at ≤400 concurrent; LLM fired reliably; see result above. First tried mining
historical episodes via the episode-search API (`POST /v2/episodes/search`) to avoid a fresh
run — but "LLM fired" and "roster matched" are anti-correlated in the archived data (throttled
matched-roster runs, random-field fired runs), so a fresh paced A/B was unavoidable.
</details>

- **Champion in the league: still v100** (last submitted). v101-v105 are UPLOADED (inert), NOT submitted.
- **crewborg on the live commissioner board sits ~#12/12** — but that's largely the imposter-favored
  meta (crew wins ~18% field-wide, imposter ~82%); crewborg is strong imposter (~87% win, 3rd/8),
  mid-field crew. There is NO clean mechanistic crew lever left (see "closed levers"). The social
  rework targets meeting *persuasion* (both roles) — the current open bet.

## ~~CRITICAL HANDOFF FACT~~ RESOLVED: v101→v106 is COMMITTED
`db3b1ae` (v101-v105 social rework) + `94888ef` (v106 self-ID/dead-mute fix) + `6735493` (docs/infra).
The list below is what those commits contain (kept for orientation):
- `events.py` — teammate-belief trace (`role_resolved` enriched + new `teammate_belief_changed`).
- `types.py` — teammate self-dedup fix + **self_color one-shot latch** (was re-derived every tick,
  drifted onto teammates → the v102 kill regression; now latched once).
- `strategy/meeting/context.py` — `recent_events` compressed + **`players` rendered as terse PROSE**
  not JSON (context 2490→~1340 tk/call; this is what got the LLM firing).
- `strategy/meeting/spend.py` (NEW) + `attend_meeting.py` — read sidecar `GET /spend`, gate
  FOLLOW-UP LLM calls on remaining per-episode budget (1st call always allowed); traces `meeting_spend`.
- `strategy/meeting/accusation.py` — deterministic accusations close with ". vote <color>".
- `memory/imposter.md` + `memory/crewmate.md` — persuasion doctrine from the chat_study.
- `crewrift_lab/chat_study/` (NEW, untracked) — the vote-persuasion study pipeline.
- **634 tests green.** **COMMIT THIS before more churn** (it's a lot of validated work at risk).

## ▶ NEXT ACTION: the v105-vs-v100 A/B (paced)
- Matched: crewborg pinned seat 0 + the **same 7 fixed champions both arms** (relhalpha:v1,
  notsus:v130, scott-hs1:v2, forgeling:v5, softmaxwell:v25, sasmith-hs1:v1, crewborg-aaln:v25),
  natural roles. ~300 eps/arm for power.
- **PACE IT: ≤400 episodes running concurrently** (fire ≤4×100 at once, let them drain, then more).
  Firing 6-8×100 at once self-throttles the shared Bedrock pool → LLM collapses to ~6%. (Rule now in
  best_practices.md.)
- **Fetch `--no-replay`** (telemetry.jsonl is all the measurement needs) and **delete each batch's
  episode dir after measuring** — fetching replays for big batches filled the disk (deadlocked a
  session). `--watch` is BROKEN on crewrift_prime 0.4.52 (reports 0 completed) — use one-shot
  `-n 100` fetch and poll.
- **GATE before trusting the compare: verify cand LLM-decision rate ≥60%** (count
  `domain.meeting_llm_decision` vs `_fallback` in crewborg's `artifacts/policy_artifact_*.zip`
  telemetry.jsonl). If low, the A/B only tested the deterministic path — the rework wasn't exercised.
- Then: `crewrift-ab/scripts/compare.py` role-split (target win_rate); build warehouses from a
  replay-fetched subset for ejection accuracy BY crewborg role — **imposter voted-out DOWN =
  deflection working; crew imposter-ejection UP = persuasion working**. Drop ops-fail episodes first.
- Ship v105 only if the LLM fired AND the social metrics move the right way (else the kill fix alone
  in v103+ is still a real, shippable improvement over v100).

## Chat-persuasion study findings (the social rework is built FROM these)
`crewrift_lab/chat_study/` (851 eps / 2450 meetings / 6757 NL chats; labels = REAL vote movement):
1. **Concrete evidence is the top persuasion lever, esp. imposter** — accusations WITH a cue land
   64% vs 43% without. crewborg's `fabricate_accusation` already makes cues; fire it, never bare-accuse.
2. Explicit "vote X"/"X sus" phrasing persuades; asking questions does NOT (defers).
3. Bandwagoning a live pile > opening a fresh accusation.
4. Self-referential defensiveness ("not me / I was doing tasks") DRAWS suspicion — don't self-defend unprompted.

## Bedrock LLM throttling — the hard-won operational truth
- The 429 "Too many tokens per day" is **shared-capacity ThrottlingException on the TOURNAMENT
  account `583928386201`** (`role/episode-runner-bedrock`), NOT our per-account quota (ours =
  714M/day, barely used) and NOT (for xreqs) the per-episode sidecar spend limit (xreqs have none set).
- It's **load contention** on the shared pool — worsens under concurrency. **Self-inflicted above
  ~400 concurrent episodes** (binary search: 100/200/400 hold LLM ≥60%, zero 429s; 800 → 52% + throttles).
- Token cost per call was the multiplier: prose-players compression cut context 2490→1340 tk, which
  is what moved LLM-use 2%→67% at equal load. `claude-haiku-4-5`, max_tokens 512.
- Latency median 2.6s / max 10s vs the old 3.0s timeout → DONE (Thread 10, 2026-07-22): meeting
  timeout default is now 6.0s (`CREWBORG_LLM_MEETING_TIMEOUT_SECONDS`), probe-validated — the 3.0s
  timeout was aborting 40% of successes into token-double-spending retries.
- I can't read `583928386201`'s quota directly (my SSO grants sandbox/prod/infra/staging only, not
  tournament). A quota increase there is the durable fix if throttling keeps blocking evals.

## CLOSED levers (don't re-chase — verified dead this session)
- **Wanderer / crew task-throughput bug** — GONE. crewborg crew 0% zero-task, 6.36 tasks ≈ notsus.
  The [[crewborg-crew-weakness]] 06-30 diagnosis is STALE (fixed by v77-80 FSM).
- **Teammate detection "broken"** — REFUTED by belief trace (0/24 failures; the "2 colors" was self
  inclusion, benign). Then the self-dedup FIX for that briefly caused the v102 kill regression — now
  fixed (latch). Detection is fine.
- **v102 kill regression (1.86→0.97)** — root-caused to the per-tick self-dedup deleting drifting-
  self-colored teammates; FIXED (v103+, confirmed 1.76→1.58 ~flat, no-kills 3%→3%).

## Platform / infra facts (load-bearing)
- xreq `top_n`/`random` seat-fill 500 is FIXED + deployed (metta #17288 + #17294; pool now ranks by
  the division's commissioner leaderboard). Both metta branches cleaned up.
- Event warehouse: `build_warehouse.py` now points at `replay.json` (platform serves replays
  UNCOMPRESSED — raw `CREWRIFT` magic, not zlib). Correct expander binary = `expand_replay-34a97a3`
  (NOT the `d9f6b30` in versions.env). Pass expander an ABSOLUTE path. Vote targets live in
  `vote_cast.value.target_slot`/`target_label` (`.target` is skip-only).
- fetch_artifacts/stream_eval/build_warehouse/xp_dashboard need `--elevated` for opponents' artifacts.
- Meeting LLM recipe: `--use-bedrock --bedrock-model us.anthropic.claude-haiku-4-5-20251001-v1:0
  --secret-env CREWBORG_LLM_MEETINGS=1 CREWBORG_CHAT_NLP=1 CREWBORG_METRICS=1 CREWBORG_TRACE_GROUPS=all
  CREWBORG_TRACE_SUSPICION_FEATURES=1`.
- Player SDK from Metta-AI/coworld-tools tarball (issue #13); coworld CLI pinned.
- /tmp fully cleaned of eval artifacts this session; everything re-fetches fresh.

## Reusable infra built this session
- `chat_study/` — merges any vote-target warehouses (`--warehouses`/`--glob-dir`) + LLM-labels chat;
  the persuasion/suspicion labels + readable-logit fit are the template for future social studies.
- Belief trace (`teammate_belief_changed`) — per-game teammate-belief queryable from policy artifacts.
