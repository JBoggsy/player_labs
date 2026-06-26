# LLM gameplay commander

> **Status: designed, not yet built (2026-06-26).** This is the living design for an
> LLM that steers crewborg's *gameplay* by biasing the existing modes, without ever
> sitting on the play path. It is the planned realization of the "`AsyncStrategyRunner`
> LLM seam for future experiments" that [`design.md`](../../design.md) §10 anticipates.
> The summary lives in `design.md` §10.6; this is the full reference.

## 1. What it is, and what it is not

The **gameplay commander** is a background LLM that, while the agent plays, reads the
game state and writes a small set of **priorities** into belief. The deterministic
modes (§7) read those priorities and change *how* they execute — which room to task
in, which room to hunt, which player to follow, how much risk to take. That is the
whole job.

It is **not** a mode selector. `RuleBasedStrategy` (§10) still picks the mode every
tick, unchanged, and still owns every reactive transition (Voting → Attend Meeting,
body → Report, tail → Accuse, just-killed → Evade, kill-ready+victim → Hunt). The LLM
never chooses a mode and never blocks a tick. Mode selection is "the same no matter
what — you always want standard crew/imposter behaviour"; the LLM's value is purely in
biasing *within* the selected stance.

**Scope (v1).** Gameplay only. The meeting LLM (§10.3) is **untouched** — it keeps
running independently on the Attend Meeting fast path. Unifying the two brains (a
meeting that sets the next-phase gameplay plan) is a deliberate later phase, not v1.

**Why a separate LLM at all, when chat is meeting-only?** Crewrift chat is emitted
only during Voting (`types.py` — `chat` is meeting speech). So there is no in-game
chat to react to. The commander's value during the Playing phase is **strategic
positioning under partial information** the rule layer doesn't reason about: spreading
two imposters across rooms, sending a crewmate to task where it's safe (or where it
can watch a suspect), committing to hunt a specific isolated target, choosing when to
take a risky kill. The meeting LLM already handles the social/voting layer; the
commander handles where the body goes between meetings.

## 2. Architecture — two loops, one shared belief

Two producers write belief at two cadences; the inner loop only ever *reads* the
latest priorities.

```
  INNER LOOP  (~24 Hz, every tick, NEVER blocks)
  perceive → fold_belief(+ commander) → RuleBasedStrategy.decide → mode.decide → resolve_action
                     ▲                        (picks mode, unchanged)     │ reads belief.commander
                     │ apply_inferences → belief.commander                │ to bias HOW it executes
                     │  (latest priorities)                               ▼
  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┼─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
                     │ lock-protected latest-value buffers (no shared mutable belief)
  OUTER LOOP  (LLM cadence ~3–5 s, background daemon thread, runs constantly)
  snapshot game-state → build prompt (+ Crewrift play guide) → Bedrock Haiku → parse JSON
       → publish CommanderPriorities ───────────────────────────────────────────┘
```

**Wiring (decision A — background thread + sync Bedrock).** A `CommanderStrategy`
wraps the existing `RuleBasedStrategy` and is installed on the **existing**
`SynchronousStrategyRunner` (so mode selection stays per-tick and unchanged). Each
tick its `decide(snapshot)`:

1. delegates to `RuleBasedStrategy.decide()` for the mode directive (fast, instant
   reactive ladder intact);
2. publishes a fresh, serialized game-state snapshot to its internal **LLM worker
   thread** (non-blocking `OverwriteBuffer.publish`);
3. takes the worker's **latest** `CommanderPriorities` (non-blocking `take`) and
   returns `StrategyResult(directive=<rule-based mode>, inferences=<priorities dict>)`.

The runtime folds `inferences` into `belief.commander` via the `apply_inferences`
hook supplied in `build_runtime` (the same channel used for any belief inference),
emitting a `strategy_inferences` trace event for free. The worker thread runs the
synchronous `players.player_sdk` LLM path (the same `call_json` the meeting LLM uses)
in a loop, as fast as Bedrock returns; only ever one call is in flight, so an async
client buys nothing.

**Stickiness.** Priorities persist in belief until the next worker cycle overwrites
them. Between cycles (the 3–5 s an LLM call takes), the modes keep acting on the last
priorities. That is the point: the LLM steers, the rules execute continuously.

**Cross-thread safety.** The worker never touches the live mutable belief. The
inner-loop thread serializes a read-only game-state object and hands it over via the
SDK's lock-protected `OverwriteBuffer`; the worker hands `CommanderPriorities` back
the same way. The only belief mutation happens on the inner-loop thread, in
`apply_inferences`.

## 3. The priorities contract (`CommanderPriorities`)

A new optional field `belief.commander: CommanderPriorities | None` (frozen pydantic),
default `None`. It carries an `as_of_tick` for the staleness guard (§5). The LLM sets
only the fields it has an opinion about; everything else stays `None` → default
behaviour.

| Field | Role | Meaning |
|---|---|---|
| `target_room: str \| None` | crew | prefer doing tasks in this room |
| `target_task: int \| None` | crew | prefer this specific task index (if still signalled + reachable) |
| `posture: "stick" \| "isolate" \| "neutral"` | crew | among otherwise-equal tasks, prefer the room with the most / fewest crew |
| `hunt_room: str \| None` | imposter | go seek a kill in this room |
| `target_player: str \| None` | imposter | prefer hunting / following / closing on this color |
| `avoid_room: str \| None` | imposter | skip this room (e.g. a teammate imposter is working it) |
| `allow_witnessed_kill: bool` | imposter · **danger** | strike even when the kill would be witnessed (§4) |
| `skip_evade: bool` | imposter · **danger** | suppress the post-kill Evade window (§4) |
| `danger_reason: str \| None` | imposter · **danger** | required justification when either danger lever is set; traced |
| `reason: str \| None` | both | the LLM's short rationale for the whole directive; traced, never gates behaviour |

## 4. Danger mode — two opt-in, LLM-authorized risk levers

The commander's hard rule is **bias, don't force** (§5): it steers *which* room/target
among already-valid choices and never touches the reactive/safety gates. **Danger mode
is the deliberate, narrow exception** — the LLM may take more imposter risk when it has
a good reason. There are exactly two levers, both off by default:

| Lever | Gate today | Danger-mode effect | Still enforced |
|---|---|---|---|
| `allow_witnessed_kill` | Hunt strikes only when `in_range ∧ kill_ready ∧ unwitnessed` (`hunt.py:599`) | relax the **witness** test | in-range + kill-ready unchanged |
| `skip_evade` | After a kill, the selector forces **Evade** for `EVADE_TICKS`=72 (`rule_based.py:132`) | skip the Evade branch → straight back to Hunt/Search | nothing else in the ladder changes |

`skip_evade` is the **one** place the LLM reaches into `RuleBasedStrategy`'s reactive
ladder; it is a single guarded read of `belief.commander.skip_evade` in
`_select_imposter`, gated so an unset/stale/disabled commander always gets today's
conservative behaviour. There is precedent for relaxing the witness test:
Hunt already relaxes it automatically with *urgency* (§10) — danger mode lets the LLM
do it deliberately and immediately.

**Marking and audit.** The play-guide prompt labels these fields explicitly as
**⚠️ DANGER — only set with a strong, stated reason**, and the schema **requires
`danger_reason`** whenever either lever is set (a danger lever with no reason is
dropped). Every time a danger lever actually changes behaviour, crewborg traces the
event with its `danger_reason`, so post-hoc review can judge whether the risk paid off
(did the witnessed kill win the game, or get us ejected next meeting?).

## 5. Bias, don't force — the consumption rule, and per-mode injection

Every discretionary mode already picks from a candidate set by a score. A priority
enters in one of two ways, and **both fall back to the unbiased default when they would
select nothing valid**:

- **Filter-then-rank** — narrow candidates to the priority, but if that empties the
  set (no task in the room, target not visible, room unreachable) drop the filter and
  rank normally.
- **Score nudge** — add a preference term to the existing ranking (used where a hard
  filter is too blunt — Hunt victim choice).

A shared `strategy/commander.py` module owns `CommanderPriorities`, accessor helpers,
and a `filter_or_fallback(candidates, predicate)` utility, so the modes don't each
reimplement the bias-with-fallback logic. Reactive/safety gates (completion detection,
unwitnessed strike except under §4, evade except under §4, report-body) are never
touched.

| Mode | Today's discretionary step | Change |
|---|---|---|
| **NormalMode** `_pick_target` (`normal.py:85`) | `min(candidates, key=dist)` over signalled reachable tasks | filter candidates to `target_room` (fallback if empty); honour `target_task` if still signalled + reachable; `posture` breaks ties by the candidate room's live crew count (stick = most, isolate = fewest) |
| **SearchMode** `_pick_room` / `_nearby_task_rooms` (`search.py:266,477`) | `self._rng.choice(rooms)` over the nearest `NEARBY_ROOMS` task rooms | if `hunt_room` is a valid task room → pick it instead of random; drop `avoid_room`; `target_player` biases the follow choice in `_a_crewmate_left` |
| **ReconMode** `decide` (`recon.py:534`) | `most_recent_victim(belief)` | if `target_player` is alive & known, close on them instead |
| **HuntMode** `_resolve_victim` (`hunt.py:612`) | `select_victim` = most-isolated visible | **score nudge**: prefer `target_player` among visible victims; strike gates untouched (except §4) |

**Staleness & validity.** Before honouring any priority, the helper re-validates it
against live belief — the room still exists, the player is alive and recently seen —
and ignores `belief.commander` whose `as_of_tick` is older than a short TTL (a few
seconds). A dead or slow worker therefore degrades to default behaviour, never to a
stale fixation.

**One genuinely new behaviour, deferred.** Crewmate **escorting** ("stick with player
X" as *active following* between rooms) does not exist today — crewmates only navigate
task → task; only the imposter's Search follows anyone. v1 models `posture="stick"` as
the cheap room-occupancy bias above (no new mode). A real `EscortMode` is a later
phase. This keeps v1 to "parameterize what already exists."

## 6. The worker, prompt, and configuration

**Module layout** mirrors the meeting LLM's portable three-piece split (§10.3), under
`strategy/commander/`:

- `context.py` — serialize `Belief` into explicit gameplay state for the LLM: phase,
  self role/position/room, kill-ready + cooldown estimate, roster with last-seen rooms,
  visible/known crew and bodies, current mode, task progress, teammate colors, and the
  list of legal rooms/players the priorities may name.
- `schema.py` — the `CommanderPriorities` contract; validates/sanitizes every field
  against the current legal state (unknown room/player → dropped; danger lever without
  `danger_reason` → dropped).
- `llm.py` — provider infra through `players.player_sdk` (Bedrock or direct Anthropic),
  default Haiku 4.5, `CREWBORG_LLM_MODEL` override. Client construction is a **no-raise
  boundary** that degrades to a disabled client (→ empty priorities), exactly like the
  meeting path.
- `prompts.py` — loads the **Crewrift play guide** + role doctrine from
  `strategy/commander/memory/{crewmate,imposter}.md`; `CREWBORG_LLM_PROMPT_DIR`
  override; missing files fall back to baked minimal doctrine rather than crashing.
- `worker.py` — the daemon thread: loop { take latest snapshot → build prompt → call →
  parse/validate → publish priorities }, with a bounded per-call timeout and one call
  in flight.

**Configuration.** Opt-in via `CREWBORG_LLM_COMMANDER=1` plus a backend (`USE_BEDROCK=1`
or `ANTHROPIC_API_KEY`) — the same gating shape as `CREWBORG_LLM_MEETINGS`. With no
flag or no backend, `CommanderStrategy` still installs but the worker is disabled,
`belief.commander` stays `None`, and behaviour is **exactly current crewborg** (zero
new branches on the disabled path). Model and prompt dir share the existing
`CREWBORG_LLM_MODEL` / `CREWBORG_LLM_PROMPT_DIR` knobs.

## 7. Tracing & evaluation

**Tracing** (§11 conventions): a `commander_decision` event per worker cycle (the
priorities set, the LLM `reason`, latency), `commander_applied` when a priority
actually changed a mode's choice, `commander_fallback` when a priority was dropped
(stale/invalid), and a `commander_danger` event carrying `danger_reason` whenever a
danger lever fires. These make it possible to read, per game, what the LLM asked for
and whether it mattered.

**Evaluation.** Role-decomposed experience requests vs the deterministic champion
(always 2 imposters per the lab convention), measuring:
- imposter: kill efficiency / second-kill conversion (the durable gap), in-view-at-
  ready %, ejection rate (does danger mode trade kills for ejections?);
- crewmate: task throughput, survival, whether posture/room bias helps or hurts;
- commander health: zero unexpected fallbacks, latency, danger-lever win/loss tally.

## 8. Phasing

Both roles are designed here; the build is phased.

1. **Scaffold** — `belief.commander`, `strategy/commander.py` helpers + `filter_or_fallback`,
   the `CommanderStrategy` wrapper + worker thread, env gating, no-op fallback verified
   (Gate-1 smoke unchanged behaviour with the flag off).
2. **Imposter levers first** — `hunt_room` / `target_player` / `avoid_room` in
   Search/Recon/Hunt, then danger mode. Highest expected lift: imposter kill efficiency
   is crewborg's durable weakness, and positioning is exactly what the rule layer
   under-reasons about.
3. **Crewmate levers** — `target_room` / `target_task` / `posture` in Normal.
4. **Later** — real `EscortMode`; unify with the meeting LLM (meeting sets the next
   Playing-phase plan).

## 9. Open questions / risks

- **Latency vs. game length.** A 3–5 s cycle means ~tens of updates per Playing phase.
  Enough for room-level steering; too coarse for tick-level tactics (which is why those
  stay in the rules). Confirm the worker keeps up and priorities don't lag a phase
  behind.
- **Stale priority harm.** The staleness TTL + live re-validation should prevent a dead
  worker from fixating the agent on an emptied room; verify in eval that fallback is
  clean.
- **Danger-mode discipline.** The LLM must be stingy with danger levers. If the trace
  shows danger kills lose more games than they win, tighten the prompt or gate the
  levers behind a higher bar.
- **Cost.** Continuous Haiku calls per game across a league add up; quantify against the
  measured lift before submitting.
