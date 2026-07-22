# Bedrock daily-token quota ask — tournament account 583928386201

**One-pager for escalation.** The shared Bedrock daily-token pool on the tournament account
starves in-game meeting LLM calls fleet-wide. This documents the measured contention, what a
quota increase buys, and the concrete ask. Numbers measured 2026-07-21/22 from crewborg
policy-artifact telemetry (`domain.meeting_llm_*` events); analysis scripts `/tmp/t4_social/`.

## The problem, measured

- **Account / role:** tournament account `583928386201`, `role/episode-runner-bedrock`
  (the in-pod Bedrock sidecar every hosted episode uses). Model:
  `us.anthropic.claude-haiku-4-5-20251001-v1:0`.
- **Error:** `429 — "Too many tokens per day, please wait before trying again."`
- **Scale (one night, crewborg slot-0 seats only, 886 episodes across 5 eval arms):**
  **9,102 calls → 1,900 decisions, 7,109 failures; 99.0% of failures are the daily-token 429.**
  Overall call-fail rate 78%.
- **It is fleet-level contention, not self-inflicted pacing** (Thread 10, 2026-07-22):
  failure is uniform across call triggers and NOT correlated with inter-call interval
  (fail/success inter-call gaps identical, median 120 ticks). Client-side levers are
  exhausted — context compression (2,490→1,340 tk), spend guard, 120-tick min interval,
  dead-seat muting, and the 6s timeout fix (eliminated abort-retry double-spend) are all
  shipped. The residual 429s do not respond to anything in-policy.
- **Production impact:** meeting decision coverage (meetings that get ≥1 LLM decision) is
  **~26–38% in league play** (2026-07-21 league harvest: 11/29 meetings = 38%; the 07-21
  live-round audit: 154 dec / 402 calls ≈ 38%; v110 A/B arms: 19–26%). Even in the
  favorable overnight window it tops out at ~50%.

## What a quota increase buys (measured counterfactual)

- Of 1,268 alive-seat meetings that got **zero** LLM decisions, **1,246 (98.3%) failed on
  429s alone** — no other error class. Removing the 429s lifts meeting decision coverage
  from **~26–50% to ~99%**.
- Demand is small per episode: a successful call costs **~2,510 input + ~146 output tokens
  (~2.7K)**, ~10 calls per crewborg seat-episode ≈ **27K tokens/episode/seat**. A 100-episode
  eval ≈ 2.7M tokens; a full night of heavy eval work (~900 episodes) ≈ **24M tokens** —
  and the pool still starved it, so the pool is being exhausted by aggregate fleet demand,
  not by any single tenant's burst.
- Why it matters (2026-07-22 Thread 4 verdict, `WORKING_CONTEXT.md`): when the meeting LLM
  actually fires, crew-side meeting outcomes measurably improve (same vote precision,
  ~1.7× vote volume; imposter-ejected-in-meeting 14.9% vs 10.1%, p≈0.01 stratified). The
  quota is the binding constraint on realizing that in production, for every LLM-using
  policy in the league — not just crewborg.

## The ask

1. **Raise the daily token quota for `us.anthropic.claude-haiku-4-5` on account
   `583928386201`** (service quota: Bedrock on-demand tokens/day for the Haiku model family),
   sized to fleet demand — current demand signature: sustained multi-tenant 429s at a
   marginal per-episode cost of ~27K tokens/LLM-seat.
2. Alternatively (or additionally): **per-tenant daily budgets** inside the shared pool, so
   one tenant's eval burst can't starve league-play calls for everyone.
3. If neither is quick: publish the pool's actual daily limit + reset time so policies can
   schedule spend deliberately (today it is only observable by hitting the 429).

## Verification recipe

Count `domain.meeting_llm_decision` vs `domain.meeting_llm_fallback{reason=llm_call_failed}`
in any crewborg `policy_artifact_*.zip` telemetry.jsonl; the error text carries the 429.
After a quota change, rerun a 100-episode pinned-roster eval and compare decision coverage
against the numbers above.
