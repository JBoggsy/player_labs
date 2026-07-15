# Player engineering — architecture and robustness doctrine

Game-agnostic doctrine for **designing** a Coworld player: which architecture to pick,
how to structure the package so the improvement loop stays cheap, and the techniques
that make a player robust enough to never lose on *time* instead of *strategy*.
Adapted from `Metta-AI/optimizer-skills` (`seed-a-new-policy`,
`scripted-policy-techniques`, `map-navigation`), filtered through this lab's operating
model. The image/runner contract is [`../player-build.md`](../player-build.md); this
doc is what goes *inside* the image.

**When to read this:** standing up a player for a new game lab; rewriting a player
that's fragile under load; or diagnosing losses that look like timeouts/disconnects
rather than bad play.

## 1. Read the mechanics before picking an architecture

Architecture follows mechanics. Answer these from the game's source (extract exact
rules and constants — see best practices "ground truth beats inference") before
writing player code:

- **Observability** — full state per observation, or hidden/partial (fog of war,
  hidden roles)?
- **Determinism & branching** — deterministic transitions with a small action set, or
  stochastic / large / continuous?
- **Latency budget** — how long is a tick/turn? Can an LLM round-trip fit inside it,
  or must actions be near-instant?
- **Players & asymmetry** — how many players; does score depend on a randomized
  role/seat? (This also sets eval variance — see best practices.)
- **Score shape** — tight range, or wide with big penalties/bonuses?
- **Protocol** — JSON/websocket, a token protocol via the SDK bridge, or binary
  (e.g. Crewrift Sprite-v1, which needs a custom bridge)?

Record the answers in the game lab's docs — they're durable game facts.

## 2. Pick the architecture

| Observable? | Deterministic? | Latency tolerates model call? | Architecture |
|---|---|---|---|
| Full | Yes | (n/a) | **Scripted** |
| Partial / social | Either | Per-tick: no; strategically: yes | **Hybrid two-loop** |
| Either | No / open-ended judgement | Yes | **LLM** (with scripted fallback) |

- **Scripted** — the brain is a pure function `observation -> action`; no model, no
  network. Instant, free, reproducible, no provider crash surface. Start here unless
  the mechanics rule it out.
- **LLM** — for decisions needing open-ended reasoning or natural language, when the
  latency budget allows. Hard rule: **an LLM player that can crash or time out scores
  the floor penalty regardless of strategy** — the LLM path must always have a
  deterministic, legal fallback (§4).
- **Hybrid two-loop** — for partially-observed / social / adversarial games needing
  fast reflexes every tick plus occasional slow strategic reasoning: a fast
  deterministic inner loop acts every tick; a slower strategy loop (often an LLM)
  updates a *directive* the inner loop follows. The inner loop never blocks on the
  strategy; directives carry a TTL and expire to a default. (Crewborg is this shape.)

When unsure, **seed scripted** — a working simple player beats a clever broken one,
and it matches this lab's "ship the minimal capable player first; let the eval locate
the gap" practice. Let evals justify adding cognition.

## 3. Structure for the improvement loop

The loop changes **one** component per iteration and must attribute the eval delta to
it. Structure the package so that's cheap:

1. **Separate the brain from the transport.** Decision logic in a pure, import-clean
   module (no I/O, no websockets); protocol/network glue in a thin transport module.
   Strategy edits and any unit tests never touch the network.
2. **Type the observation.** Parse the raw payload into a validated model once, at
   the transport edge. Downstream code reads typed fields — bugs surface at parse
   time, not deep in strategy.
3. **Make every decision attributable.** Trace, per tick: what was observed, which
   rule/branch chose the action, and *why* (mode / options / choice) — plus
   `llm_used` / `llm_failed` / `fallback_used`. You can't debug an outcome, only a
   trace; you can't improve a black box.
4. **One knob per concept.** Tunable parameters (weights, thresholds, timings) as
   named config separate from logic, so an iteration changes one and the diff is one
   line. (This is the root loop's "keep tunable knobs in a config layer" rule.)

## 4. Robustness — never lose on time

A player that crashes, stalls, or times out scores the floor penalty no matter how
good its strategy is. The tell that you need this section: losses where the *time*
ran out or the connection died, while a simpler opponent never times out.

**The inversion that matters:** the scripted path is the **primary** decision maker
and must be able to play **every phase of the game on its own**. The LLM is an
enhancement consulted only when it's healthy, the decision is genuinely
ambiguous/semantic, and there's time budget. A player that can't finish the game
without the LLM is not done.

```text
decide(state):
    intent = scripted_decision(state)          # always produces a legal action
    if llm_healthy and time_ok and is_ambiguous(state):
        try:
            intent = llm_refine(state, intent, deadline=short)  # may improve it
        except (timeout, provider_error):
            circuit.trip()                     # fall through with scripted intent
    return intent
```

The techniques, each of which has independently caused real losses when missing:

1. **Never crash — always return a legal action.** Every path, including all error
   branches, returns a valid action for the current phase. Instrumentation (trace
   writes, artifact uploads, feature parsing) must never raise into the game loop —
   record the error and continue.
2. **Fail fast, not slow.** Give LLM calls a **short** deadline (single-digit
   seconds), never the game timeout; no retry/backoff chains on the hot path. Add a
   **circuit breaker**: after K consecutive failures (K can be 1), stop calling the
   LLM for the rest of the episode — provider problems persist within an episode, and
   re-probing burns the clock. Treat a timed-out call as abandoned; never let
   abandoned calls pile up in an executor.
3. **Drain to the latest state before deciding.** On a broadcast-heavy transport,
   a naive `for msg in stream:` loop falls behind under an opponent's message storm
   and spends the game acting on stale states. Flush the buffer to the newest state
   each decision; inbound messages are state *replacements*, not a work queue.
4. **Quota-gate every action.** Track what's already been done per phase/step and
   never re-submit completed work — even a late-arriving stale state then can't make
   the player loop on rejected actions.
5. **Send-and-confirm.** After sending an action, wait for the server's state to
   reflect it before deciding the next one — fire-and-forget under load produces
   duplicates and quota violations.
6. **Resume mid-game from live state.** Derive phase/step from the **observed
   state**, not an internal counter that assumes no dropped messages. A reconnecting
   or mid-episode-starting player must pick up correctly from the latest state.
   (Related trap from our own labs: guards keyed on "did my action appear in my own
   view" wedge across phase boundaries — clear them on phase advance.)
7. **Instrument the fallback path.** Trace `fallback_used`, `circuit_open`,
   `llm_failed` per decision, so "we lost on time" vs "the LLM path never fired" is
   readable from the batch instead of reconstructed. (Best-practices corollary:
   verify success, not capability — find the log line proving the LLM call happened.)

**Verify the robustness claims** (this is critical-path testing, not ritual — each is
the fastest answer to "will it survive X"): runs to completion with the LLM forced
off; survives a simulated broadcast storm; circuit trips on an injected slow/failing
LLM and play continues; the decision function produces the right action from a
mid-game state.

## 5. Map navigation (only for games with movement)

"Go to point P" is the most common primitive and a frequent *silent* failure: wedging
on walls, momentum overshoot, targeting a point inside an obstacle, committing to a
stale route. The layering rule: the decision layer emits a symbolic intent
(`navigate_to(P)`) and never touches buttons or routes; the action layer owns *how*,
statefully across ticks.

- **Bake a nav graph once per episode** over the walkability grid: plan on coarse
  cells for speed, validate nodes/edges against the true pixel mask, and compute
  reachability by flood-fill from spawn — an unreachable destination should fail loud
  at bake time, not as a mid-game stall. Plan on an **eroded** (clearance-margin)
  mask so routes run down corridor centers; momentum drift wedges wall-grazing paths.
- **Destination anchors:** a region's geometric center can sit inside a wall or out
  of interaction range — precompute a reachable anchor point per static destination
  that satisfies the interaction condition.
- **Special edges** (teleports/portals/vents) are directed graph edges between
  anchors, gated by role/intent if only some agents may use them.
- **Momentum control:** bang-bang per axis with a **predictive stop** (estimate
  stopping distance from velocity + friction); read speed/accel/friction constants
  from the game source, never guess.
- **Re-root the route** at the live position on a fixed interval and on goal change —
  A* on a baked graph is sub-millisecond, so replanning is nearly free and eliminates
  approach-wedging. String-pull/LoS-smooth the polyline.
- **Stuck watchdog:** detect no-progress over K ticks and route-exhausted-without-
  arrival; replan, nudge, or pick another goal — never spin forever.
- **Instrument it:** route events (`route_planned`, `replan`, `arrived`, `stuck`,
  `unreachable_destination`) and per-tick position/goal in the trace, so pathing
  failures show up in batch analysis instead of staying invisible.

## Fit with this lab's loop

One deliberate divergence from the source material: optimizer-skills gates uploads
behind local smoke tests and an eval ladder. **Here, uploading stays ungated** — the
hosted eval is the test (see [`../AGENTS.md`](../AGENTS.md)). The robustness
verification in §4 is not a pre-upload gate; it's the targeted debugging you do when
evals show time/connection losses, or the design work you do once when standing up
the player. Speed doctrine unchanged.
