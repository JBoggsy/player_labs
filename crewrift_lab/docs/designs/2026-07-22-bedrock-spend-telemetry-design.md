# Bedrock spend telemetry — per-call attribution + budget optimization (W4)

**Status:** living document. Audit complete; implementation in this change; spend profile +
budget recommendations appended as they are measured.

James's directive: "measure our own bedrock usage and see where we can budget more
effectively… the player protocol provides some method of seeing how much you've spent after
each call; we should be tracking that in the policy and logging it, so we can see when and
where we're spending the most."

## 1. Audit — what spend tracing exists today (2026-07-22)

### Platform surface (metta, read-only reference: `app_backend/job_runner/bedrock_sidecar.py`)

The per-pod Bedrock sidecar exposes THREE spend/usage signals to the policy:

1. **`GET /spend`** → `{spend_usd, spend_limit_usd, remaining_usd}` — the pod's *running
   list-price estimate* of every metered call. `*_limit`/`remaining` are null unless the
   league configures a per-episode per-player-pod limit (xreqs have none — confirmed in our
   telemetry: `meeting_spend` always logs `limit_usd: null` on eval batches).
2. **Response headers on EVERY proxied call** — `X-Coworld-Spend-Usd` (running spend) and
   `X-Coworld-Spend-Limit-Usd` (when configured). This is "the method of seeing how much
   you've spent after each call" from the player protocol. Caveat: the Anthropic SDK's
   `client.messages.create(...)` returns a parsed model, not raw headers, so reading these
   requires `with_raw_response` — see §2 design choice.
3. **The Messages response `usage` object** — `input_tokens`, `output_tokens`,
   `cache_read_input_tokens`, `cache_creation_input_tokens`. The sidecar meters spend from
   exactly these counts × a pricing snapshot (`bedrock_pricing.py`: haiku family =
   $1.00/M input, $5.00/M output, $0.10/M cache-read, $1.25/M cache-write), so a
   client-side `tokens × haiku rates` estimate reproduces the sidecar's number.

Sidecar spend semantics that matter for attribution:

- **Failed calls that are rejected before inference accrue $0.** Spend accrues only in
  `_record_usage`, which fires only when a usage object is parsed from a *delivered
  response body/stream*. A 429 (shared daily-token pool throttle or sidecar spend-cap) has
  no usage object → $0. **Verified empirically** on 387 crewborg slot-0 seats
  (v110/anchor-era artifacts): seats with ≥1 429 and ZERO successful decisions read
  `spend_usd ∈ {0, ~0.0034}` — the nonzero ones are exactly one successful *commander*
  call's worth (see below), and seats-with-decisions show
  `median(sidecar_spend − token_estimate) = 0.000000`. Failed-call token waste on our side
  is therefore **timeout-abort retries only** (fixed by the 3→6s timeout in v111), not 429s.
- Streaming ops meter from stream metadata; the spend headers on a streaming call lag one
  call behind (headers are sent before the body meters). We use non-streaming
  `messages.create` only, so headers are current as of the *previous* call and `usage` is
  authoritative for the call itself.

### crewborg's existing tracing (before this change)

| Signal | Where | What it captures | Gap |
| --- | --- | --- | --- |
| `domain.meeting_spend` | `modes/attend_meeting.py` `_spend_allows_followup` | sidecar `/spend` snapshot (spend/remaining/limit), read at most every `SPEND_READ_CACHE_TICKS=24` ticks, ONLY while evaluating a follow-up-call gate | fires only mid-meeting on the gate path; no end-of-call correlation; never fires for meeting_start-only meetings or the commander |
| `domain.meeting_llm_call` | same file, `_submit_llm_request` | trigger, request_id, calls_used, budget | no cost |
| `domain.meeting_llm_decision` | same file, `_trace_decision` | trigger, model, latency, **full `usage` dict**, decision | usage present but **no USD**, and only on success |
| `domain.meeting_llm_fallback{reason=llm_call_failed}` | `_collect_llm_outcome` | trigger + error repr | no token/cost info (correct for 429s — they cost $0 — but timeout-aborts DID cost the full input; not attributed) |
| `domain.commander_call` | `strategy/commander/worker.py` → drained by `events.py` | outcome, latency, model, `usage` on success | in `NOISY_DOMAIN_EVENTS` — **filtered out of hosted artifacts** unless `CREWBORG_TRACE_GROUPS` includes `commander`/`all`; no USD |
| `meeting_llm.latency_ms` histogram | `_collect_llm_outcome` | latency by model/trigger | metrics only |

Commander budget note: the commander (`CREWBORG_LLM_COMMANDER`) calls the same sidecar →
same pod spend pool → same daily-token pool. It is OFF in the v110/v111 recipe
(`CREWBORG_LLM_MEETINGS=1` only), but when enabled it shares the meeting budget with **no
spend guard of its own** — only the mode-level snapshot cadence limits it.

**The missing piece (James's ask): per-CALL spend attribution** — one event per LLM call,
success or failure, carrying trigger/context, tokens, estimated USD, and cumulative
episode spend, cheap enough to always leave on.

## 2. Design — `domain.llm_spend`

One event per completed LLM call attempt (success AND failure), emitted from the meeting
mode's outcome pickup (`_collect_llm_outcome`) and from the commander worker's existing
trace handoff. Named `llm_spend` (a `domain.` event → survives the lean artifact filter,
unlike `commander_call`).

Payload:

```jsonc
{
  "surface": "meeting" | "commander",   // which LLM seam spent it
  "trigger": "meeting_start" | ...,      // commander: "commander"
  "ok": true | false,
  "error_class": null | "throttle_429" | "timeout" | "other",
  "model": "us.anthropic....",
  "latency_ms": 2558.7,
  "input_tokens": 2560, "output_tokens": 135,          // null when unavailable (failures)
  "cache_read_input_tokens": 0, "cache_write_input_tokens": 0,
  "est_cost_usd": 0.003235,     // tokens × pricing table (0.0 for token-free failures)
  "episode_est_cost_usd": 0.009812,  // cumulative client-side estimate, this process
  "sidecar_spend_usd": 0.009812      // last known sidecar /spend or header value; null if never read
}
```

Design choices:

- **Cost source: response `usage` × a vendored haiku/sonnet pricing table** (mirrors
  metta's `FAMILY_PRICING_PER_1M`). Verified to match the sidecar's own metering to ~$0
  median on 335 seats. We do NOT add a per-call `/spend` HTTP read — the 20-40ms blocking
  loopback GET per meeting tick was the 2026-07-21 vote_timeout root cause; per-call reads
  from the worker thread would be safe latency-wise but add nothing the token math doesn't.
- **`sidecar_spend_usd` is opportunistic**: the meeting path reports the cached value the
  existing `_spend_allows_followup` read already maintains (no new HTTP). It is a
  cross-check, not the primary number.
- **Failures**: 429s report `est_cost_usd: 0.0` (measured — pre-inference rejection);
  timeouts report the *wasted input estimate* using the request's serialized context size
  (chars/4) since no usage object comes back; `error_class` distinguishes them.
- **Cumulative episode spend** is a plain accumulator shared per process
  (`strategy/llm_spend.py`), covering meeting + commander so the episode total is one
  number.
- The shared helper lives in `strategy/llm_spend.py`; both seams call
  `record()`/`build_event()` so the payload stays schema-identical.

## 3. Spend profile — existing corpus (2026-07-21/22, 400 crewborg slot-0 seats)

Sources: `/tmp/wh_anchor_base_v110_episodes`, `/tmp/wh_v110_league_episodes`,
`/tmp/wh_anchor_cand_episodes`. Caveat (per the lessons buffer): the anchor-base dir
actually holds v107 eps (dir names swapped vs contents) — immaterial here, since
v107/v110/anchor all run the identical meeting-LLM recipe, model, and cadence, and the
profile is about call economics, not policy behavior. Script:
`crewrift_lab/tools/spend_profile.py`. Costs = tokens × haiku rates ($1/M in, $5/M out),
verified to match the sidecar's own metering (§1).

### Per trigger

| trigger | calls | decisions | 429 fails | timeout fails | success % | mean in/out tokens | $/successful call |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| new_chat | 1,435 | 319 | 1,099 | 15 | 22.2% | 2,556 / 139 | $0.00326 |
| meeting_start | 1,149 | 287 | 858 | 4 | 25.0% | 2,312 / 138 | $0.00300 |
| chat_cooldown_ready | 947 | 235 | 699 | 13 | 24.8% | 2,562 / 146 | $0.00330 |
| deadline | 617 | 122 | 448 | 0 | 19.8% | 2,601 / 131 | $0.00326 |

Decision-action mix: `meeting_start` → 78% send_chat, 20% set_tentative_vote (opens the
conversation); `deadline` → 78% submit_vote (closes it); the two middle triggers are
~60/40 chat/vote-ish. **No trigger is a cost outlier** (all ~$0.0033/success) and no
trigger converts dramatically worse — deadline's 19.8% success is pool luck, not different
economics. All four earn their place.

### Per meeting order (0-indexed)

| meeting | calls | decisions | 429 fails |
| --- | ---: | ---: | ---: |
| 0 | 1,723 | 311 | 1,382 |
| 1 | 1,140 | 227 | 897 |
| 2 | 769 | 213 | 536 |
| 3 | 390 | 141 | 237 |
| 4+ | 126 | 71 | 52 |

Meeting 0 takes 41% of call volume at an 18% success rate; later meetings succeed better
(m3: 36%, m4+: 56%) — consistent with fewer surviving seats hammering the pool late-game,
not with any per-meeting policy difference.

### Per role

crewmate: 2,803 calls / 655 decisions (23.4%); imposter: 1,345 / 308 (22.9%) — symmetric.

### The headline numbers

- **Mean cost per seat-episode: $0.0077** (median $0.0064, max $0.041). 400 seats ≈ $3.07.
  A 100-episode eval costs crewborg **~77¢**; a full heavy night (~900 eps) ≈ **$7**.
- **Money waste is ~zero; the waste is opportunity.** 3,104 of 4,148 call attempts (75%)
  died on the daily-token-pool 429 — and those cost $0 (measured). The only real
  token-money waste was timeout abort-retries (~45 calls × ~2.5K input ≈ $0.11 across the
  whole corpus), and v111's 6s timeout already eliminated it (llmcadence probe: 0
  timeout-bucket fails).
- **USD budget is not a binding constraint anywhere.** No xreq/league episode we measured
  had a sidecar spend limit configured (`limit_usd: null` in every `meeting_spend` read);
  the binding constraint is the shared **daily-token pool** (docs/bedrock-quota-ask.md).

## 4. Budget recommendations (quantified)

1. **Do not cut the call budget or interval to save money — there is no money to save.**
   A full episode's LLM bill is ~0.8¢; failed calls are free. The current budget=5 ×
   4-trigger cadence is correctly sized against the *spend* dimension.
2. **The 429 pool is the only real budget; spend it earlier.** Meeting 0 fires 41% of all
   calls into the worst success window. But per-meeting success ordering tracks fleet
   contention, not our cadence (Thread-10: failure uncorrelated with inter-call gap), so
   in-policy reshuffling buys little — the fix stays the quota ask.
3. **Keep the deadline trigger.** It converts 78% of its successes into submit_vote (the
   highest-value action, 76% vote precision per v89) at the same $0.0033 as any other
   trigger. Gating it harder would trade real votes for nothing.
4. **Retries are cheap; the spend guard's job is the LEAGUE limit.** When a league does
   configure `episode_player_pod_llm_spend_limit_usd`, the existing
   `_spend_allows_followup` reserve gate is the correct mechanism; with the measured
   $0.003/call and DEFAULT_LLM_CALL_COST_USD=0.004, the estimate is conservative by ~25%
   — right where it should be.
5. **Commander (if ever re-enabled) must count against the same mental budget** — it now
   records into the same episode ledger, so `episode_est_cost_usd` covers both seams.

## 5. Probe verification — appended after the hosted run

(pending)
