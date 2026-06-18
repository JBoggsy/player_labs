# Crewborg

An agent that plays **Crewrift**, a Coworld social-deduction game (Among Us–style).
Crewborg plugs Crewrift-specific perception, belief, modes, and strategy into the
Player SDK's two-loop runtime and runs as a WebSocket client that speaks Crewrift's
binary protocol to the Coworld runner.

The shared **Player SDK** is the `players.player_sdk` package, imported from the
**public `Metta-AI/players` repo**, which tracks `main` (installed via `pyproject.toml`;
no local checkout — see the [lab README](../../README.md)); it is not vendored in this tree.

- **Design spec:** [`design.md`](./design.md) — the settled architecture.
- **Orientation:** [`AGENTS.md`](./AGENTS.md) — codebases, protocol, source pointers.
- **Design docs:** [`docs/designs/`](./docs/designs/) — living deep-dives, e.g.
  [`suspicion.md`](./docs/designs/suspicion.md) (the Bayesian model + likelihood-ratio
  table + how we learn/improve the weights) and
  [`agent-tracking.md`](./docs/designs/agent-tracking.md) (probabilistic location
  tracking for imposter search).

Develop / run / test / benchmark / fetch-episode workflows live at the lab level —
see the [lab README](../../README.md).

## What it does

Crewborg plays **both roles** end-to-end. As a crewmate it does tasks, attends
meetings, reports bodies, and **votes out the most-likely imposter** — a **Bayesian
suspicion model** (`strategy/suspicion.py`) maintains a posterior `P(imposter)` per
player (a combinatorial prior updated by likelihood ratios for witnessed kills/vents,
being tailed, and graded event-log cues). When it detects it's being **actively
tailed** by a player it's grown suspicious of, it switches to **Accuse** mode — drop
tasks, go slam the one-shot emergency button to call a meeting. At meetings, when
there's a **clear leading suspect**, it **accuses then votes** them — chatting
`"<color> sus: <reasons>"` from the ranked event-log evidence — staying silent and
skipping a flat field. Reporting a visible body takes priority over accusing. As an
imposter the
role-aware selector runs a priority order during `Playing`: **Evade** immediately
after its own kill (vent if possible, else move away from the body), **Report Body**
for non-fresh visible bodies, **Hunt** (kill ready *and* a victim visible → commit
to the most-isolated visible crewmate, close via a trajectory-led intercept, and
strike when in range and unwitnessed),
**Search** (within the kill lead window, walk ranked occupancy hot spots until a
victim is visible, then follow that target), and **Pretend** (the default — pick a
real task station in the highest-scoring occupancy room, penalizing rooms another
imposter is likely occupying, then fake the task for one task duration). At meetings
it **deflects onto crewmates** (never a teammate): it proactively accuses + votes a
non-teammate who genuinely looks sus (real cues, same chat format as a crewmate — the
formatting is identical by design so it isn't a tell), and otherwise waits to
**bandwagon** onto whoever others suss/vote, citing *fabricated safe cues* in that
same format. Meetings reuse **Attend Meeting**. With `CREWBORG_LLM_MEETINGS=1` and `ANTHROPIC_API_KEY`,
Attend Meeting uses a fast Haiku-class LLM call on the meeting fast path to chat,
respond to other players, keep a tentative vote, and submit early when requested;
otherwise it preserves the deterministic accuse-and-vote / silent-skip fallback.
Hunt is gated on a visible kill opportunity whose isolation bar relaxes with
urgency, not merely on the cooldown ending. The action layer covers `kill` (edge-A
in KillRange) and `vent` (level-B in VentRange).

## Layout

```
crewborg/                (package crewrift.crewborg)
  __init__.py        build_runtime(): assemble the AgentRuntime + bake the map
  agent_tracking.py  reachability-disc location beliefs + coarse occupancy grid search
  types.py           the six SDK types + perceive/update_belief + phase machine
  action.py          action layer: stateful resolve_action + movement/edge FSMs
  nav.py             baked nav graph: pixel-validated A* + reachability + anchors + vent-teleport routing
  navbake.py         load/validate the offline-baked nav graph + occupancy substrate (else fall back to live build)
  trace.py           trace selection: event families + env filtering (outputs = SDK TraceOutputs)
  events.py          CrewborgEventTracer: on_step_complete hook → domain.* events
  modes/             idle/normal/attend_meeting/report_body/accuse + evade/pretend/search/hunt (+ imposter_common helpers)
  strategy/          rule_based.py: mode selector + suspicion.py: Bayesian P(imposter) → believed_imposters + event_log.py: per-player observation log + occupancy.py: perception-tape predicates + opportunity.py: victim/witness logic + trajectory.py: intercept prediction
  strategy/meeting/  accusation (chat templates + fabrication) + imposter (deflect/bandwagon) + chat_read/chat_nlp (spaCy chat parsing, CREWBORG_CHAT_NLP) + context/schema/llm (LLM path)
  perception/        Sprite-v1 decoder (decoder/tables) + resolution (resolve/entities)
  map/               vendored croatoan.resources + ported parser/bake (§6)
  coworld/           policy_player.py (the websocket bridge) + scene.py
  viewer/            browser trace replay UI for agent-perspective forensics
  tests/
```
