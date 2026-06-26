# LLM gameplay commander

> **Status: BUILT & gated-off (2026-06-26).** Both roles are wired (imposter + crewmate levers),
> with a danger mode, a soft/hard **strength** dial, full observability, a forced-priority debug
> knob, and the Bedrock-in-pod gating fix. Disabled by default → behaviour is byte-identical to
> deterministic crewborg. 460 crewborg tests green. **Not submitted to any league.** Control
> capacity is *demonstrated* (§13) but **not yet tuned for performance** — early use will often
> degrade play; that is expected. Summary in [`design.md`](../../design.md) §10.6; this is the full reference.

---

## 1. What it is

The **gameplay commander** is a background LLM that, while crewborg plays, reads the game state and
writes a small set of **priorities** into `belief.commander`. The deterministic modes read those
priorities and change *how* they execute — which room to do tasks in, which room to hunt, which
player to chase, how much risk to take, and how *hard* to commit. It runs entirely off the per-tick
play path: it never blocks the game loop, and when it's disabled or silent the agent plays exactly
as deterministic crewborg does.

It is the realization of the `AsyncStrategyRunner` "future LLM seam" that `design.md` §10 anticipated,
scoped to the **Playing** phase.

## 2. What it DOES (capabilities)

- **Steers positioning/targeting for both roles** by setting priorities the modes consume:
  - *Crewmate:* `target_room` (where to task), `target_task` (a specific task), `posture`
    (stick-with-crew / isolate).
  - *Imposter:* `hunt_room` (where to seek a kill), `target_player` (who to chase), `avoid_room`
    (where not to go, e.g. a teammate's room).
- **Takes opt-in extra risk (danger mode, imposter):** `allow_witnessed_kill`, `skip_evade` (§7).
- **Dials steering strength** per directive: `strength: soft` (gentle bias with fallback, default)
  vs `hard` (override default behaviour, including a crewmate *loiter-in-room* and a distance-blind
  hunt-room) (§6).
- **Runs continuously and asynchronously** on a background daemon thread, refreshing priorities as
  fast as the LLM returns (~2 s/call observed); the inner loop reads the latest **sticky** value.
- **Emits rich traces** (`domain.commander_*`) so what the LLM proposed, its latency, and whether it
  changed behaviour are all observable in-pod (§10).
- **Degrades safely** at every boundary: disabled feature, no backend, dead/slow worker, malformed
  JSON, stale or illegal priority → deterministic default.

## 3. What it DOESN'T do (explicit non-goals / boundaries)

- **It does NOT select modes.** `RuleBasedStrategy` still picks the mode every tick, unchanged, and
  owns *every* reactive transition (Voting→Attend Meeting, body→Report, tail→Accuse, just-killed→Evade,
  kill-ready+victim→Hunt). The commander cannot enter, skip, or reorder modes (the **one** exception
  is the `skip_evade` danger lever, §7).
- **It does NOT issue actions, movement, button presses, or paths.** It only sets belief priorities;
  the modes + action layer still produce every intent and wire command.
- **It does NOT block or pace the game loop.** A 2–5 s LLM call runs on its own thread; the inner
  loop never waits on it. If the LLM is slow/dead, the agent keeps playing on the last (or no) priorities.
- **It does NOT override safety/correctness gates** (except the two opt-in danger levers): kill range,
  kill-cooldown readiness, the unwitnessed-strike test (unless `allow_witnessed_kill`), the post-kill
  Evade (unless `skip_evade`), task-completion detection, self-vote/teammate guards, victim commitment —
  all intact.
- **It does NOT touch the meeting/chat LLM logic.** Meetings remain a separate brain on the Attend
  Meeting fast path (the only shared code is the Bedrock-enable detection, §8). The commander never
  chats or votes; its prompt explicitly tells it so.
- **It does NOT force by default.** `strength: soft` (the default) always falls back to deterministic
  behaviour when a priority would select nothing valid. You must opt into `hard` to override.
- **It does NOT actively escort/follow as a crewmate.** Crewmates still navigate task→task; `posture`
  and `target_room` only bias *task selection* (soft) or *loiter in a room* (hard). A real
  `EscortMode` (a crewmate following a buddy between rooms) is **not built** (§16).
- **It does NOT react to in-game chat.** Crewrift chat is meeting-only; there is no Playing-phase chat.
  The commander reasons from observed game state, not conversation.
- **It does NOT (yet) improve performance.** As of this writing it is unvalidated and likely net-negative
  until the prompt/levers are tuned. It is a *control capability*, not a win.

## 4. Architecture — two loops, one shared belief

Two producers write belief at two cadences; the inner loop only ever *reads* the latest priorities.

```
  INNER LOOP  (~24 Hz, every tick, NEVER blocks)
  perceive → fold_belief → RuleBasedStrategy.select → mode.decide → resolve_action
                  ▲                  (picks mode, unchanged)   │ reads belief.commander
                  │ apply_commander_inferences                 │ to bias HOW it executes
                  │  → belief.commander (latest priorities)    ▼
  ─ ─ ─ ─ ─ ─ ─ ─ ┼ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
                  │ lock-protected latest-value buffers (no shared mutable belief)
  OUTER LOOP  (LLM cadence ~2–5 s, background daemon thread, runs constantly)
  snapshot game-state → build prompt (+ Crewrift role doctrine) → Bedrock Haiku → parse/sanitize JSON
       → publish CommanderPriorities ─────────────────────────────────────────────┘
```

**`CommanderStrategy`** wraps the existing `RuleBasedStrategy` and is installed on the **existing**
`SynchronousStrategyRunner` (so mode selection stays per-tick and unchanged). It is gated by an eager,
cheap read of `CREWBORG_LLM_COMMANDER` (the feature flag): **off → it returns only the rule directive
and never starts the worker or serializes context** (the byte-identical disabled path). On, each tick
`decide(snapshot)`:

1. delegates to `RuleBasedStrategy.select(belief)` for the mode directive (fast; reactive ladder intact);
2. publishes a fresh, serialized game-state snapshot to the **worker thread** (non-blocking `OverwriteBuffer.publish`);
3. takes the worker's **latest** `CommanderPriorities` (non-blocking `take`), sanitizes it against the
   current legal rooms/players, and returns `StrategyResult(directive=<mode>, inferences={"commander": …})`.

The runtime folds `inferences` into `belief.commander` via the `apply_commander_inferences` hook passed
to `build_runtime`. The worker runs the **synchronous** `players.player_sdk` LLM path (`call_json`, the
same one the meeting LLM uses) in a loop; only one call is ever in flight, so an async client buys nothing.

**Lazy client construction.** The worker builds its LLM client **inside its own thread from live
`os.environ`** (with a bounded retry on "no backend"), mirroring the meeting client — *not* eagerly at
`build_runtime`. (An earlier eager version read the env at process start, before the pod's Bedrock env
was available, and silently disabled. See §8.)

**Stickiness.** Priorities persist in belief until the next worker cycle overwrites them; between cycles
the modes act on the last value. **Cross-thread safety:** the worker never touches live belief — the
inner loop serializes a read-only state dict in, the worker hands a priorities dict back, both via the
SDK's lock-protected `OverwriteBuffer`. The only belief mutation is on the inner-loop thread.

## 5. The priorities contract (`CommanderPriorities`)

`belief.commander: CommanderPriorities | None` (frozen pydantic), default `None`. Carries `as_of_tick`
for the staleness guard. The LLM sets only the fields it has an opinion about.

| Field | Role | Meaning |
|---|---|---|
| `target_room: str \| None` | crew | prefer doing tasks in this room |
| `target_task: int \| None` | crew | prefer this specific task index (if still signalled + reachable) |
| `posture: "stick"\|"isolate"\|"neutral"` | crew | break task ties toward most- / fewest-crew rooms |
| `hunt_room: str \| None` | imposter | seek a kill in this room |
| `target_player: str \| None` | imposter | prefer hunting / following / closing on this color |
| `avoid_room: str \| None` | imposter | skip this room |
| `strength: "soft"\|"hard"` | both | how hard to honour the positioning levers (§6); default `soft` |
| `allow_witnessed_kill: bool` | imposter · **danger** | strike even when witnessed (§7) |
| `skip_evade: bool` | imposter · **danger** | suppress post-kill Evade (§7) |
| `danger_reason: str \| None` | imposter · **danger** | required when a danger lever is set; traced |
| `reason: str \| None` | both | LLM rationale; traced, never gates behaviour |

`schema.py:sanitize_priorities` validates every field against the **current legal state**: unknown
rooms/players → `None`; non-int `target_task` → `None`; invalid posture/strength → default; a danger
lever without a non-empty `danger_reason` → dropped.

## 6. Consumption: "bias, don't force" + the strength dial

Every discretionary mode already picks from a candidate set by a score. The helpers in
`strategy/commander/bias.py` (`commander_of` — returns the priorities only if non-stale; `filter_or_fallback`;
`room_crew_count`) centralize the rule. Two strengths:

- **`soft` (default)** — *filter-then-rank* or *score-nudge*, and **always fall back** to the
  deterministic choice when the priority would select nothing valid. Cannot make play worse than the
  rules when the priority is impossible (no task in the room, target not visible, room unreachable).
- **`hard`** — override the default even when suboptimal (still never violating safety gates).

| Mode | Discretionary step | `soft` | `hard` |
|---|---|---|---|
| **NormalMode** (`_pick_target` / `decide`) | nearest signalled+reachable task | filter tasks to `target_room` (fallback to all if none); honour `target_task` if signalled+reachable; `posture` breaks ties by room crew count (stick=most, isolate=fewest) | if `target_room` has **no** task for me → **navigate to / loiter in that room** instead of tasking elsewhere |
| **SearchMode** (`_pick_room`, `_nearby_task_rooms`, follow) | random among nearest `NEARBY_ROOMS` task rooms | pick `hunt_room` if it's among those nearest rooms; drop `avoid_room`; prefer `target_player` among leavers to follow | inject `hunt_room` as a candidate **even if far** (target it regardless of distance); extend the `target_player` follow-lost window (120→240 ticks) |
| **ReconMode** (`decide`) | `most_recent_victim` | close on `target_player` if alive & known, else `most_recent_victim` | (same) |
| **HuntMode** (`_resolve_victim`) | `select_victim` = most-isolated visible | **score-nudge**: prefer `target_player` among visible, reachability-checked, else `select_victim` | (same; strike gate only relaxed via §7) |

**Staleness & validity.** `commander_of` ignores `belief.commander` older than `COMMANDER_TTL_TICKS`
(240 ≈ 10 s); fields are re-validated against live belief (room exists, player alive & recently seen).
A dead/slow worker degrades to default, never to a stale fixation.

## 7. Danger mode — two opt-in, LLM-authorized risk levers (imposter)

The deliberate, narrow exception to "never touch the safety gates." Both off by default; both require
`danger_reason`.

| Lever | Default gate | Danger effect | Still enforced |
|---|---|---|---|
| `allow_witnessed_kill` | Hunt strikes only when `in_range ∧ kill_ready ∧ unwitnessed` | relax **only** the witness test | in-range + kill-ready unchanged |
| `skip_evade` | After a kill the selector forces **Evade** for `EVADE_TICKS`=72 | skip the Evade branch → straight back to Hunt/Search | nothing else changes |

`skip_evade` is the **one** place the commander reaches into `RuleBasedStrategy`'s reactive ladder
(a single guarded read in `_select_imposter`). When either lever actually changes behaviour, crewborg
emits a `domain.commander_danger` trace with the `danger_reason` (HuntMode via `self.emit`; `skip_evade`
via a transient `belief.commander_danger_events` marker drained by the event tracer) so the risk can be
reviewed after the fact.

## 8. Bedrock in-pod gating (the endpoint, not `USE_BEDROCK`)

The SDK's `bedrock_enabled(env)` checks `USE_BEDROCK`/`CLAUDE_CODE_USE_BEDROCK`. **In sidecar mode the
Coworld runner strips `USE_BEDROCK` from the player container** (it treats it like a credential) and
injects the loopback Bedrock proxy endpoint `AWS_ENDPOINT_URL_BEDROCK_RUNTIME` (+ dummy creds) instead.
So gating on `USE_BEDROCK` reports "no LLM backend configured" in-pod even though Bedrock *is* available.

**Fix (both `strategy/commander/llm.py` and `strategy/meeting/llm.py`):** treat the presence of
`AWS_ENDPOINT_URL_BEDROCK_RUNTIME` as a Bedrock signal — `use_bedrock = bedrock_enabled(env) or
_sidecar_bedrock(env)` — so `select_client(use_bedrock=True)` reaches the SDK's sidecar routing. Verified
in-pod: commander `commander_call outcome:ok` and meeting `meeting_llm_decision` (no more `_fallback`).
The platform/SDK should still ideally pass `USE_BEDROCK=true` for the documented `--use-bedrock` contract —
see `docs/issues/2026-06-26-bedrock-disabled-crewrift-prime-xp.md`.

## 9. Forced-priority override (`CREWBORG_COMMANDER_FORCE`)

A debug/QA knob: when the feature is on and `CREWBORG_COMMANDER_FORCE` holds a JSON object,
`CommanderStrategy` parses it once and stamps it (sanitized, fresh `as_of_tick`) into `belief.commander`
**every tick**, bypassing the worker and the LLM entirely (works with no Bedrock backend). This makes
control deterministic for demos/tests (e.g. `'{"hunt_room":"Observatory","strength":"hard"}'`). Unset →
normal worker path. Parse failure → ignored (logged), behaves as unset.

## 10. Observability

`domain.commander_*` trace events, gated behind `CREWBORG_TRACE=debug` **or** `CREWBORG_TRACE_GROUPS=commander`
(off by default). The worker (background thread) records into a small lock-protected ring buffer
(`CommanderTrace`, bounded, drop-oldest with a `commander_trace_dropped` counter); `CrewborgEventTracer`
drains it on the inner-loop thread and emits:

- `commander_started` — worker connect: `{enabled, backend, model, disabled_reason, attempt, env_seen}`,
  where `env_seen` reports which of `USE_BEDROCK`/`CLAUDE_CODE_USE_BEDROCK`/`ANTHROPIC_API_KEY`/
  `AWS_ENDPOINT_URL_BEDROCK_RUNTIME` are present (the in-pod-enablement diagnostic).
- `commander_call_start` / `commander_call` — per call: `{outcome: ok|error, latency_ms, model,
  priorities, usage}` (+ `raw_request`/`raw_response` when `CREWBORG_LLM_TRACE_RAW`).
- `commander_applied` — when the sanitized priorities applied to belief change (delta).
- `commander_danger` — when a danger lever actually fires (with `danger_reason`).
- `commander_stopped` — worker close.

## 11. Configuration (env)

| Var | Effect |
|---|---|
| `CREWBORG_LLM_COMMANDER=1` | enable the gameplay commander (feature flag) |
| `USE_BEDROCK=1` / `ANTHROPIC_API_KEY` / (in-pod) `AWS_ENDPOINT_URL_BEDROCK_RUNTIME` | a backend (else the worker disables; §8) |
| `CREWBORG_LLM_MODEL` | override model (default Haiku 4.5) |
| `CREWBORG_LLM_PROMPT_DIR` | override the role-doctrine prompt dir |
| `CREWBORG_LLM_TIMEOUT_SECONDS` | per-call timeout (default 3.0) |
| `CREWBORG_LLM_TRACE_RAW=1` | include raw request/response in `commander_call` traces |
| `CREWBORG_TRACE_GROUPS=commander` / `CREWBORG_TRACE=debug` | surface `domain.commander_*` traces |
| `CREWBORG_COMMANDER_FORCE='{…}'` | force a fixed priority, bypassing the LLM (§9) |

## 12. Disabled / fallback guarantee

With `CREWBORG_LLM_COMMANDER` unset (or no backend, or a stale/None commander), behaviour is
**byte-identical** to deterministic crewborg: `CommanderStrategy` returns just the rule directive, no
worker runs, no context is serialized, `belief.commander` stays `None`, and every mode/branch takes its
current path. This is asserted by an equivalence test across crewmate (normal/voting/report-body) and
imposter (search/hunt/evade/recon) selections.

## 13. Measured control capacity (not performance)

Forced-priority Prime runs (`CREWBORG_COMMANDER_FORCE`, `target_room=Reactor` / `hunt_room=Observatory`),
nav-destination room tally during Playing:

| Lever | `soft` | `hard` |
|---|---|---|
| Imposter `hunt_room` adherence | 29% (#1 of ~13 rooms; chance ≈8%) | **100%** |
| Crew `target_room` adherence | 13% (#2; ≈1.6× chance) | **67%** (rest = transit/finishing a prior task) |

So control is real and dial-able for **both** roles. `soft` is a gentle nudge (crew especially, since it
only steers among a crewmate's *own* tasks); `hard` is near-total positional control. This says nothing
yet about whether steering *helps* — that's tuning.

## 14. Module layout (`strategy/commander/`)

- `types.py` (in the package root) — `CommanderPriorities` + `belief.commander` / `belief.commander_danger_events`.
- `bias.py` — `commander_of` (staleness guard), `filter_or_fallback`, `room_crew_count`.
- `context.py` — serialize belief → gameplay-state dict (+ legal rooms/players).
- `schema.py` — `sanitize_priorities` against legal state.
- `llm.py` — config, client protocol, `DisabledCommanderClient`, `AnthropicCommanderClient`,
  `build_commander_client_from_env`, `commander_feature_enabled`, `_sidecar_bedrock` (§8).
- `prompts.py` + `memory/{crewmate,imposter}.md` — role doctrine (imposter doctrine marks the ⚠️ danger
  fields); the prompt states the LLM is the commander, **not** the meeting chatter.
- `worker.py` — `CommanderWorker` daemon (lazy client, retry, the call loop) + `CommanderTrace` buffer.
- `strategy.py` — `CommanderStrategy` + `apply_commander_inferences` + the forced-override hook.
- Consumed in `modes/{normal,search,recon,hunt}.py` and `strategy/rule_based.py` (`skip_evade`), wired in
  `crewborg/__init__.py:build_runtime`.

## 15. Testing

460 crewborg tests pass. Coverage includes: the priorities type + sanitization; the bias helpers +
staleness; the worker (lazy build, retry, disabled fallback, trace records); the strategy wrapper +
forced override + disabled-path equivalence; the Bedrock endpoint-gating; per-lever mode tests (each
lever's biased choice **and** its invalid/stale/absent fallback) for both roles and both strengths; the
danger levers on/off/stale; and the `commander_*` trace emission/gating.

## 16. Not built / future

- **`EscortMode`** — a crewmate actively following a buddy between rooms (true "stick with X"). Today
  `posture`/`target_room` only bias task selection (soft) or loiter (hard).
- **Unify with the meeting LLM** — a meeting that sets the next Playing-phase plan; today they're separate.
- **Prompt/lever tuning + A/B** — confirm (and make) steering actually improve imposter kill efficiency
  / crew survival; iterate the role doctrine (incl. *when* to set `strength:hard` and the danger levers).
- **Platform `USE_BEDROCK` fix** (§8) — so the documented upload contract holds without the endpoint workaround.

## Open questions / risks

- **Latency vs. game length** — ~tens of updates per Playing phase; fine for room-level steering, too
  coarse for tick-level tactics (which stay in the rules).
- **`hard` overuse** — 100% adherence is usually bad play; the LLM/operator must spend `hard` and the
  danger levers sparingly. The traces (`commander_danger`, `commander_applied`) are how we'll audit that.
- **Cost** — continuous Haiku calls per game across a league add up; quantify against measured lift before submitting.
