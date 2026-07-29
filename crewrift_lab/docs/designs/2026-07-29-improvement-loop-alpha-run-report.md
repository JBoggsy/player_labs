# Improvement-loop alpha — final run report (2026-07-29)

First autonomous multi-loop run of the 9-step tournament-scale improvement pipeline
(spec: [`2026-07-28-improvement-loop-alpha.md`](2026-07-28-improvement-loop-alpha.md)).
Dispatched 2026-07-28, finished 2026-07-29. **Outcome: two ships (v117, v118), two
levers honestly closed, zero unverified claims. Champion progression v116 → v117 → v118
in ~30 hours.**

## Per-loop results

| loop | hypothesis | verdict | evidence | prereg |
|---|---|---|---|---|
| 1 | Pre-vote chat push during the retime hold converts wasted expire ballots into joined piles | **REFUTED — NO-SHIP** | Mechanism fired 136×/84 eps but late-join share 21.0% vs 21.2%; a second explicit vote call recruits nobody. Closes the whole "more chat calls" channel on the conversion axis (2× with the earlier combo failure). | [`2026-07-28-prevote-push-prereg.md`](2026-07-28-prevote-push-prereg.md) |
| 2 | Suspicion-v5 refit (runtime-v116-L2 weights, CV AUC 0.773 vs vendored 0.698) recovers ranking skill that converts to correct votes | **SHIPPED → v117** (`54bb6cc5…`) | Probe: hits/cep 1.420 vs 1.030 (p=0.0004). Confirmatory: 1.335 vs 1.030 (p=0.0038), precision 82.1%, both WRs directionally up. | [`2026-07-28-suspicion-v5-refit-prereg.md`](2026-07-28-suspicion-v5-refit-prereg.md) |
| 3 | Server chat-cooldown swallow (~30% of accusations silently dropped) — fix: CHAT_COOLDOWN 60→104 + HS1 defers to accusation | **honest NO-SHIP** (GUARD-7 mis-ej point-bar trip at n=155, p=0.098) | Both primaries + 5/6 guards passed; acceptance 100% vs 81.5%. Guard read was noise-dominated at that n — but the registered rule is the rule. | [`2026-07-29-chat-swallow-fix-prereg.md`](2026-07-29-chat-swallow-fix-prereg.md) |
| 4 | L3's guard trip was sampling noise (powered pooled re-test, ~80% power on the one question) | **ALL PASS** — mis-ej 0.160 vs 0.142 (bar 0.213, p=0.58); L3 noise confirmed → v118 built | Pooled 399 cand / 500 base eps. Confirmatory arms 1–2: gate-2b p=0.081 miss at n=200 with every point estimate replicating → pre-registered extension. | [`2026-07-29-chatfix-powered-prereg.md`](2026-07-29-chatfix-powered-prereg.md) |
| 5 | (= the pre-registered confirmatory extension + run wrap-up) | **ALL GATES PASS → SHIPPED v118** (`912f94cb…`) | Pooled 4-arm 400 eps vs 500-ep base: votes-on-imp-target 1.10 vs 0.96 (MW p=0.0274), acceptance 886/886=100% vs 82.2%, crew WR 35.0% vs 30.1%, mis-ej 0.148, hits/cep 1.434 vs 1.326. | same doc, extension section |

## Ships

- **v117** (`54bb6cc5…`, sub `319c6219…`): v116 + suspicion-v5 refit weights, no code
  change. v116's `lpm_288949ba…` retired first.
- **v118** (`912f94cb…`, sub `a6f38a7f…`): v117 + the chat-swallow fix (main `1a71c6b`).
  v117's `lpm_fca1ad4b…` retired first. Four independent datasets replicate every point
  estimate (votes-on-imp-target 1.10–1.16 vs 0.94–0.96; acceptance 100% vs ~82%; crew WR
  up 3–7pp; mis-ej clean).

Scale: 26 experience requests, ~2,600 episodes, all Thread-1 pinned roster / slot 0 /
natural roles / ≤400 concurrent. Zero ops-dirty arms.

## Process assessment (vs the alpha success criteria)

- **(a) Every experiment pre-registered before firing: PASS.** Verified by git
  timestamps at the submit gates (e.g. extension prereg committed 18:00:31Z, arm 3
  created 18:00:33Z). Five preregs, five verdicts strictly against registered gates.
- **(b) No submit without a clean verdict + orchestrator approval: PASS.** Two submits,
  both after full gate tables and the orchestrator's prereg-discipline audit.
- **(c) Belief-divergence channel feeding hypotheses: PASS, with nuance.** The step-3+5
  tooling's biggest contribution was *negative* triage in L1 (both smoke signals
  verified real but mined invariant — two dead-end hypotheses avoided) and
  *instrumental* in L3: the chat-swallow root cause came from joining belief-side
  `chat_sent` telemetry against ground-truth visibility — exactly the belief-vs-truth
  join the pipeline was built for.
- **(d) Honest verdicts: PASS.** L1 refuted and closed; L3 NO-SHIPPED on a guard that
  later proved to be noise — and the recovery was a *pre-registered powered re-test*,
  not a rerun-until-pass.

## Operational findings

- **Interruptions are survivable iff state lives in git.** The runner died ~6× on
  transient API errors and was user-stopped once; /tmp was wiped between arm completion
  and the final verdict. Everything recovered because preregs/verdicts/version-log
  commits landed *before* each next action — the pooled verdict was reproduced from
  re-fetched platform data with the instrument recovered verbatim from the runner
  transcript. Cost of the /tmp loss: ~40 min of re-downloading 900 episodes.
- **Analysis instruments must be committed, not left in /tmp.** The one asset that
  nearly died with the tmpdir was `verdict.py`. Now at
  `crewrift_lab/tools/experiments/2026-07-29-chatfix-verdict.py`; beta makes this a rule.
- **The powered-re-test pattern works.** A guard tripping its *point bar* at low n with
  a non-significant p is a "register a powered re-test" signal, not a "close the lever"
  signal. L3→L4 turned an honest NO-SHIP into a clean ship without ever bending a rule.
- **Instrument correction found en route:** raw replay bytes contain server-DROPPED
  chats (`writeChat` precedes the `addVotingChat` filter) — acceptance must be simulated
  via the server cooldown rule, never read from replay bytes.
- **Platform quirks:** `coworld upload` "unauthorized" can mean the local Docker daemon
  is down (OrbStack died overnight); league episodes carry no policy artifacts (belief
  pipeline needs xreq episodes); short xreq ids 422 on sub-routes (resolve full UUIDs
  via `/observatory/v2/experience-requests`).

## League state at close

v118 `912f94cb…` qualified 2026-07-29 16:39 — `lpm_53214866…` **competing/active +
champion**; v117 retired with audit reason. LEAGUE WATCH: crew WR and mis-ej on fresh
league data; the acceptance win should surface as more votes landing on our targets.
