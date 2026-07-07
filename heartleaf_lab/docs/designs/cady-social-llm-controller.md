# Cady social LLM controller — design

**Status:** proposed (2026-07-07). Living doc; update as implementation reveals more.

**Goal:** Give Cady a slow-loop LLM controller that decides her *social plan*
(gather vs host vs attend, and whom to invite) a few seconds at a time, off the
frame path, while the existing rock-solid deterministic modes execute it every
frame. The LLM is an **enhancement over a deterministic floor**, never a
dependency.

## Why this shape

- **Nav/gather/actions are done** (v10/v11: 15/15 games, 100% present, harvest
  193–240, clean home loop). Only *scoring* is left, and scoring = hosting a
  party with guests (`food × guests`; only the host scores). That's a social
  problem: draw guests to our house / pick the right party to attend.
- The starter villager solves this with an **LLM-proposes / deterministic-
  disposes** hybrid (see [`villager-dinner-attendance.md`]). We mirror that
  structure and exploit its seams ([[heartleaf-villager-exploits]]): the chat→
  commitment lock and food-poor targeting.
- The SDK already ships the whole slow-loop seam — we write a strategy, not
  infrastructure.

## What already exists in the SDK (reuse, don't build)

- **`ThreadedStrategyRunner`** (`player_sdk/strategy.py`): runs a strategy's
  `decide(snapshot)` on a **background thread** with latest-value buffers.
  `observe()` never blocks the frame; `poll()` returns the most recent completed
  directive. This is the right seam for a **synchronous** LLM client
  (`llm.call_json` is sync) — it's the villager's curl-multi pattern in spirit,
  and crewborg's champion uses the sync/threaded family, not async.
  - **Why not `AsyncStrategyRunner`?** It calls `asyncio.get_running_loop()` at
    construction, but our runtime is built *before* `asyncio.run(run_sprite_bridge)`,
    and `llm.call_json` is synchronous anyway. `ThreadedStrategyRunner` fits both.
  - **Increment 1 uses `SynchronousStrategyRunner`** (cadence-limited, on the
    inner loop) because with the LLM OFF the deterministic decide is <1ms — no
    need for a thread. We switch to `ThreadedStrategyRunner` when the LLM turns
    on (increment 3), so the ~1-2s Haiku call runs off the frame path.
- **`llm.py`**: `select_client(use_bedrock, timeout)` → `AnthropicBedrock` (in
  pod, via the sidecar endpoint) or `Anthropic` (local key); `call_json`,
  `resolve_model`, `bedrock_enabled`, `extract_json_object`. Same path crewborg's
  champion uses. Model default **claude-haiku-4-5** (fast, cheap, proven in-pod).
- **Parameterized modes**: `ModeDirective.params` is a typed `ModeParams`
  (pydantic, frozen). Each mode declares `params_type` and reads `self.params`.
  `EmptyModeParams` is the default → a directive with no params is valid. So the
  LLM can say "gather in area X / invite player Y" OR just "gather / invite" and
  both work.
- **Anti-oscillation primitives**: `ModeDirective.ttl_ticks` (a directive stays
  valid for N ticks) + `source` + the runtime's `active_directive`. We use these
  so a brief LLM latency blip does NOT let the fallback yank the mode and then
  flip back when the LLM reply lands.

## Architecture

```
 fast loop (24 Hz)                         slow loop (background task, ~every few s)
 ─────────────────                         ────────────────────────────────────────
 perceive → belief → runtime.step          SocialStrategy.decide(snapshot)  [async]
   observe(snapshot) ─────────────────────▶   build compact social prompt
   poll() → directive (latest)                one Haiku call_json (hidden latency)
   run active mode → Intent                   parse → typed ModeDirective(+params)
   resolve_action → mask                    ◀─ published to latest-value buffer
```

### Two-tier strategy: `SocialStrategy` (async) over `ClockStrategy` (det. floor)

`SocialStrategy.decide` is the async strategy given to `AsyncStrategyRunner`:

1. Compute the **deterministic baseline** directive first (the existing
   `ClockStrategy` logic, extended with host/attend — see below). This is always
   available and correct.
2. If the LLM is enabled AND a fresh LLM decision exists, use it; else return the
   baseline. The LLM call itself is what makes `decide` async/slow, but because
   it runs in the background task the frame loop never waits.
3. Emit a `ModeDirective` with a **`ttl_ticks`** long enough to bridge normal LLM
   latency + jitter (e.g. ~5 s of ticks). While an LLM directive is live and
   un-expired, the runtime keeps running it; the fallback only supplies a new
   directive when nothing valid is active.

### Anti-oscillation (explicit requirement)

The failure mode to prevent: LLM is briefly slow → fallback changes the mode →
LLM reply lands → mode changes back → flip-flop.

Guards, in order:
1. **TTL on LLM directives.** An accepted LLM directive stays active for
   `LLM_DIRECTIVE_TTL` ticks. A latency blip shorter than the TTL never triggers
   a fallback swap — the current mode just keeps running.
2. **Fallback is sticky, not eager.** The deterministic baseline only *replaces*
   an active directive when that directive has expired or the phase genuinely
   changed (e.g. crossed the dinner deadline) — not merely because a new tick
   arrived without a fresh LLM reply.
3. **Mode-level hysteresis.** Switching INTO host/attend commits for a minimum
   dwell (and, like the villager, honors a party commitment until proven empty),
   so we don't thrash between "attend house A" and "attend house B" on
   successive LLM calls. Commitment lives in belief, updated slowly.

Net: the fast loop always runs *some* coherent mode; the slow loop refines the
choice without ever causing a visible flip.

### Modes (v1 scope: host/attend/invite; gather/nav stay deterministic)

| Mode | Params (`ModeParams`) | Behavior |
|---|---|---|
| `gather` (exists) | `GatherParams(area: optional)` | Circuit gather; if `area` given, bias to that region's gardens, else full circuit. **No-param = today's behavior.** |
| `host` (exists, extend) | `HostParams()` | Go home, be a visible presence at own door pre-dinner, be inside at dinner. |
| `invite` (new) | `InviteParams(target: optional player)` | Position near `target` (or nearest good candidate) and release a prepared invite line when in hearing range. No-param = invite the best visible candidate. |
| `attend` (new) | `AttendParams(house: optional)` | Go to `house` (or best-visible crowd) and enter for dinner. No-param = crowd-follow like the villager. |

Params are **optional by construction** (`EmptyModeParams` default + optional
fields), satisfying "LLM can specify a target OR not and both work."

### Chat: LLM prepares, fast loop releases (proximity-gated)

The LLM authoring full chat is **out of v1 scope** (per the scope decision:
"host/attend + who to invite"). v1 uses **templated** invite lines
(`"Party at my house at 6 — tons of food!"`, ≤48 chars, the broadcast-width
rule). The LLM picks the *target/plan*; a cheap per-frame proximity check in the
`invite` mode releases the templated line when the target is within hearing range
(the villager's `maybeSendDecisionChat` trick, and the bubble-width reach from
[[heartleaf-chat-broadcast-whisper]]). LLM-authored persuasion is a fast-follow.

### The exploits this enables ([[heartleaf-villager-exploits]])

- **Trip the commitment lock**: invite early, clearly, naming our house — an
  attendance phrase from a villager's LLM force-locks it to us.
- **Target food-poor villagers**: they're the ones who attend. Food isn't
  observable, so infer it from behavior (still roaming near dinner = likely
  guest) — the LLM prompt gets each visible player's recent movement/where-headed
  summary so it can pick likely acceptors.
- **Crowd begets crowd**: get 1–2 committed guests visible at our door early;
  the villager crowd-follow (`crowd×10000 − dist`) snowballs the rest.

## LLM I/O contract

- **Input** (compact text snapshot, rebuilt each call): clock/phase, my food
  total, my committed plan, visible players (name, rough position, which
  house they're near / heading to, recent chat heard from them), my house.
- **Output** (strict JSON → typed decision): `{plan: gather|host|invite|attend,
  target: <player name?>, house: <index?>, area: <region?>, reason: <str>}` →
  mapped to a `ModeDirective(mode, params, ttl_ticks, source="llm")`.
- Uses SDK `call_json` + `extract_json_object`; invalid/empty → fallback baseline.

## Gating & safety (crewborg's hard-won rules)

- **LLM off by default**; enabled by env (`--use-bedrock` + a `CADY_LLM_SOCIAL=1`
  secret-env), exactly like crewborg. Deterministic path is what ships/evals
  until the LLM is *verified firing* in-pod (check the trace for
  `strategy_evaluated {runner:"async"}` + our own decision events, not fallback).
- **Never depend on the LLM.** Bedrock is frequently absent in league pods; the
  deterministic floor must play a competent host/attend game on its own. (The
  villager's whole strategy is deterministic and beatable — so ours can be too.)
- **Bounded call rate**: `cadence_ticks` + a per-call budget so we don't hammer
  the sidecar (crewborg hit 429s). One decision every few seconds is plenty for a
  social plan.

## First increment (what to build now)

1. `SocialStrategy` (async) + wire `AsyncStrategyRunner` in `runtime.py`, LLM
   **off** — verify the deterministic host/attend floor works end-to-end and
   doesn't oscillate (local + hosted eval; expect first non-zero hosting attempts).
2. Add `invite`/`attend` modes + `GatherParams`/`InviteParams`/`AttendParams`.
3. Turn the LLM on (Haiku, env-gated), verify it fires in-pod, then A/B vs the
   deterministic-only build.

Deterministic floor first, LLM layered second — so we always have a shippable,
non-regressing build and can attribute any gain to the LLM.

## Open questions

- Exact `LLM_DIRECTIVE_TTL` / cadence (start ~5 s TTL, ~2–3 s cadence; tune from
  measured Haiku latency in-pod).
- How reliably we can infer another player's food from behavior alone (drives
  target quality) — measure from expanded replays.
- Whether the deterministic floor alone already scores respectably (it might —
  the villager's does), which would set the LLM's bar.
