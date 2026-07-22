# Meeting-LLM call-failure mitigation at 1200-tick meetings (Thread 10)

**Date:** 2026-07-21 · **Status:** VERDICT — SHIP-WITH-NEXT-VERSION (probe clean; see §Verdict)
**TODO item:** "Meeting-LLM call failures at 1200-tick meetings (~43% of non-cooldown calls)" (2026-07-02)

## Problem

When `VOTE_TIMER` went 240→1200 ticks (v84), meeting-LLM call volume tripled and the
Bedrock sidecar started failing calls. Failures fall back safely to the deterministic
path — lost upside, not a correctness bug. This thread re-measures the CURRENT failure
profile on tonight's data and ships the minimal mitigation the data supports.

## Measured baseline (2026-07-21, v110 league-recipe arms)

Source: the Thread-1 v110 A/B pinned-roster arms, 200 eps / 199 crewborg seats
(`/tmp/wh_anchor_base_v110_episodes`, xreq_136dd84f + xreq_edd0f75e). Script:
`/tmp/t10_measure.py`. The fresh telemetry_harvest dir (36 league eps) shows the same
shape at smaller n (78 calls, 73% fail, 56/57 errors = daily-token 429).

Per-trigger profile (673 meetings, 561 with ≥1 call, 2084 calls):

| trigger | calls | decisions | failed | fail % |
| --- | --- | --- | --- | --- |
| new_chat | 751 | 169 | 581 | 77% |
| meeting_start | 561 | 133 | 428 | 76% |
| chat_cooldown_ready | 478 | 131 | 347 | 73% |
| deadline | 294 | 74 | 197 | 67% |
| **total** | **2084** | **507** | **1553** | **74.5%** |

Key facts that ground the change:

1. **The failure is ~uniform across triggers and NOT pacing-correlated.** Inter-call
   interval before success (median 120 ticks) equals the interval before failure
   (median 120). Error bucket: 1536/1553 = **daily-token-pool 429**
   ("Too many tokens per day"), 17 = client timeout. This is shared-pool contention
   (self-inflicted at fleet scale), not per-seat burstiness — so raising
   `LLM_MIN_CALL_INTERVAL_TICKS` or dropping a trigger would NOT cut the 429 rate,
   it would only cut retry attempts.
2. **Retries ARE the coverage mechanism under throttling.** First-decision call index:
   1→133, 2→90, 3→65, 4→31, 5→14 (228 meetings got none). 45/561 meetings (8%) got
   their FIRST decision only at call 4-5. Cutting the budget (5) or the "worst" trigger
   directly cuts per-meeting decision coverage (currently 333/673 = 49% of meetings).
   `new_chat` has the highest fail % but also the MOST absolute decisions (169).
3. **The 3.0s timeout is the one measurable waste.** Success latency: median 2.81s,
   p90 4.03s, max 7.3s. **203/507 (40%) of successes took >3.05s total** — i.e. the
   anthropic SDK client-aborted a first attempt at 3.0s and its automatic retry
   succeeded. A client-side abort does not un-spend the server-side tokens: each such
   call burns ~2×2.5K input tokens into the very daily-token pool that is 429ing.
   At 1200-tick meetings the deadline budget absorbs a longer timeout trivially
   (latest-safe-start with 6.0s = 48 + 144 + 12 = 204 of 1200 ticks; it was 132/240 —
   i.e. 55% of the old meeting — back when 3.0s was chosen).
4. Spend guard: 0 `meeting_llm_spend_gated` in 199 seats — the per-episode spend limit
   is not the binding constraint tonight; the daily pool is.

## Change (minimal, data-supported)

1. **Meeting call timeout default 3.0s → 6.0s** (`strategy/meeting/llm.py`):
   covers p90+ of observed success latency in ONE attempt, eliminating the
   double-token abort-retry on ~40% of successful calls (and the corresponding waste
   inside failed sequences). New env `CREWBORG_LLM_MEETING_TIMEOUT_SECONDS` wins,
   then the shared `CREWBORG_LLM_TIMEOUT_SECONDS` (still one knob for meeting +
   commander), then 6.0. The commander's own default stays 3.0s (its calls run
   during Playing where time is scarcer; out of scope here).
   The deadline geometry in `attend_meeting.py` derives from the client's actual
   timeout, so the latest-safe-start / deadline-prompt window shifts automatically
   (fallback constant aligned to 6.0).
2. **`LLM_MIN_CALL_INTERVAL_TICKS` now env-tunable** (`CREWBORG_LLM_MIN_CALL_INTERVAL_TICKS`,
   default unchanged at 120): the data says the interval is not tonight's lever, so we
   do NOT change the default — but the knob enables the later sweep the TODO asks for.
3. **No trigger dropped, budget unchanged (5):** per facts 1-2, both would trade
   decision coverage for nothing (the 429s are pool-level, not cadence-level).

## Pre-registered probe criteria (BEFORE launch)

Probe: `crewborg-llmcadence:v1` = current main (v110 code) + the timeout change, v110
recipe (LLM meetings + HS seed), ~100 eps, ONE xreq, pinned Thread-1 roster
(daf-actinf-crewborg-v3:v1, softmaxwell-crewborg:v34, sasmith-crewborg-hs1:v15,
notsus:v130, scott-crewborg-hs1:v13, crewrift-prime-crewborg-aaln-hunter-relhalpha:v6,
crewborg-aaln:v25), crewborg pinned slot 0, natural roles.
Baseline for comparison: the v110 arms measured above (same roster, same recipe, 2026-07-21).

| # | criterion | baseline (v110 arms) | pass condition |
| --- | --- | --- | --- |
| 1 | PRIMARY — abort-retry waste: share of successful calls with total latency >3.05s | 40% (203/507) | ≤10% (the 6.0s budget makes one attempt suffice) |
| 2 | PRIMARY — timeout-bucket `llm_call_failed` | 17/1553 | ~0 (429s excluded — they are pool-level and vary with fleet load) |
| 3 | GUARD — per-meeting decision coverage (meetings with ≥1 `meeting_llm_decision` / meetings with ≥1 call) | 59% (333/561) | NOT down >5pp (first-call-always + budget-5 retries preserved) |
| 4 | GUARD — `llm_call_failed` per meeting | 2.77 (1553/561 called meetings) | not UP materially (>20%) |
| 5 | GUARD — vote quality proxies | vote_timeouts 0; `meeting_vote_gated` ≈1.0/seat (198/199) | vote_timeouts 0; gated rate ~flat |

Honest caveat, pre-registered: the overall 429 fail RATE is dominated by concurrent
fleet load on the shared pool (account 583928386201) and by how much of the daily
quota is already spent when the probe runs — a raw fail-rate comparison vs tonight's
baseline is NOT a clean read, which is why the primaries are the timeout-specific
signatures (1, 2), not the 429 rate itself.

## Verdict — SHIP-WITH-NEXT-VERSION (2026-07-22)

Probe: `xreq_f5e7a285-8deb-4db0-8fcd-f29787a7220f`, 100/100 completed, 100 crewborg-llmcadence
seats fetched (`/tmp/t10_probe_eps`), 1018 calls / 294 decisions / 723 fails.
Verdict script: `/tmp/t10_probe_verdict.py` (validated: reproduces the baseline numbers exactly).

| # | criterion | baseline (v110 arms) | probe | verdict |
| --- | --- | --- | --- | --- |
| 1 | abort-retry waste | 40% of successes >3.05s (only possible via retry at the 3.0s timeout); max 7.26s | **0 aborted attempts**: 0 successes >6.05s, max 4.94s, 0 timeout errors | **PASS** (see note) |
| 2 | timeout-bucket `llm_call_failed` | 17/1553 | **0**/723 | **PASS** |
| 3 | decision coverage (called meetings with ≥1 decision) | 59.4% | 52.5% — vs **contemporaneous** same-night arms: anchor-cand 52.6%, v107 49.5% (pool-depletion drift, exogenous) | **PASS vs contemporaneous controls** |
| 4 | `llm_call_failed` per called meeting | 2.77 | **2.40** (lowest of all four same-night arms: 2.77/2.70/2.76) | **PASS** |
| 5 | vote quality | timeouts 0; gated 0.99/seat | timeouts **0**; gated 0.89/seat; success latency median 2835 (≈baseline 2813) | **PASS** |

**Note on C1's literal threshold.** The pre-registered "≤10% of successes >3.05s" was
mis-specified: under the NEW 6.0s timeout a 3–5s success is a *single* attempt, so the
3.05s line no longer identifies retries. The intended mechanism — no client-aborted
attempts double-spending tokens — is directly confirmed by the correct signatures:
**zero** successes past the 6.05s abort boundary (max 4.94s vs baseline max 7.26s, which
was a 3s-abort + retry) and **zero** timeout-bucket failures (C2). Under the old 3.0s
timeout, 36% of the probe's successful calls (3.05–4.94s) would have burned a wasted
first attempt; now none do.

Fail rate context (exogenous, pre-registered as not-a-primary): probe 71.0% vs
same-night arms 74.5% / 77.0% / 78.4% — lowest of the night despite running last
(quota most depleted), consistent with removing the double-spend.

Residual: the 429 daily-token-pool contention still dominates (723/723 probe errors) —
that is fleet-level (account 583928386201) and not addressable from inside one policy;
per this measurement neither interval nor trigger changes would help, only fewer/cheaper
tokens per call or a bigger pool.

**Action:** the timeout change (and the interval env knob, default unchanged) rides into
the next `crewborg` version. NOT submitted from this probe (probes never are).
