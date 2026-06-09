# Reading crewborg's trace logs

crewborg writes a per-tick **JSON-lines** trace to **stderr**, captured per episode as
`logs/policy_agent_{N}.log` for the slot it controlled — its subjective point of view:
what it **perceived**, **believed** (suspicion), the **mode** it chose, and the
**command** it sent, tick by tick. This doc is crewborg's log *format* and how to read
it.

This is **crewborg-specific** — other Crewrift policies log differently (the Nim
players emit plain-text stderr, not this schema). For the **game-level** side of
reading a finished episode — downloading artifacts, **finding which slot is
crewborg's**, the objective replay/`expand_replay` timeline, and the `.bitreplay`
format — see the lab's [`crewrift-replays.md`](../../../docs/crewrift-replays.md); its
§C "A policy's own logs" covers slot identification (by name **and** version) and
points here for the format. To interpret what the events *mean* in gameplay terms, see
[`crewrift-gameplay.md`](../../../docs/crewrift-gameplay.md).

(Format produced by `trace.py` sinks; events by `events.py` `CrewborgEventTracer`,
wired in `__init__.py`. Field meanings: `design.md §5.2, §10–11` and
[`docs/designs/suspicion.md`](designs/suspicion.md) / [`agent-tracking.md`](designs/agent-tracking.md).)

---

## Line format

One JSON object per line, two shapes (distinguished by `kind`):

```json
{"kind":"trace","tick":3420,"event":"snapshot_submitted","data":{"mode":"normal", ...}}
{"kind":"trace","tick":3442,"event":"domain.phase_change","data":{"from":"Playing","to":"Voting"}}
{"kind":"metric","metric_kind":"counter","name":"cyborg.strategy.observed","value":1.0,"tags":{...}}
```

`trace` lines have `tick`/`event`/`data`; `metric` lines have
`metric_kind`/`name`/`value`/`tags` and **no** `tick`/`event`. Bare event names
(`perception`, `belief_updated`, `strategy_evaluated`, `action_intent`,
`act_command`, `snapshot_submitted`) are SDK-framework events; game-level ones are
prefixed `domain.`.

The final line of a hosted log is plain text (`game over…`), not JSON — always
prefilter with **`grep '^{'`** (it also drops any Kubernetes collector-error lines so
`jq` never chokes).

## The two workhorse records

- **`domain.decision_snapshot`** — one per tick, the per-tick audit of what crewborg
  saw and chose. Key fields (`events.py`): `phase`, `role`
  (`crewmate` / `imposter` / `dead`; `null` at the terminal `GameOver` tick), `mode`
  (active mode), `intent` `{kind,point,target_color,task_index,reason}`, `command`
  `{held_mask,buttons,chat}`, `self {x,y}`, `visible_players[]`
  `{color,xy,life_status,suspicion,believed_imposter,confirmed_imposter}` — where
  `suspicion` is P(imposter) ∈ [0,1] when crewborg is a **crewmate** and `null` when
  it is the **imposter** (it only scores suspicion as a crewmate), `visible_bodies[]`,
  `threats[]` (every *believed* imposter even if not visible, with `p`, `visible`,
  `last_seen_tick`, `dist`, and the `flee_*` gate booleans), `task`, `flee`,
  `nav {route_goal,next_waypoint}`.
- **`domain.suspicion_snapshot`** — one per meeting (crewmate only); explains the vote.
  `ranking[]` of `{color, p, events[]}` sorted by descending `p` (posterior
  P(imposter) ∈ [0,1]), plus `vote_bar`, `would_vote`, `confirmed[]`, `believed[]`.

## Other domain events

`phase_change`, `player_event` (a durative observation interval opened on someone:
room/task/vent/near_body/proximity), `player_died`, `vote_cast`,
`chat_received`/`chat_sent`, `occupancy_reacquired` (a lost player re-seen:
predicted-vs-actual cell), `meeting_*` (serialized meeting context + the
LLM/deterministic vote path). Imposter-only: `kill_ready_changed`, `kill_attempted`,
`kill_landed`, `occupancy_seek_target`.

**Identity:** players are **colors**, not slots, almost everywhere; the slot↔color map
appears only inside `meeting_context_serialized` (`voting.candidates[].slot`).
crewborg's own color is in `meeting_context.self.color`; its own slot is the filename.

## Trace levels

Fixed at episode time by `CREWBORG_TRACE` (read once in `events.py`):

- **`viewer`** adds the heavy `viewer_frame` per tick (the browser-replay model).
- **`debug`** adds `decision_snapshot`, `suspicion_tick` (full P vector every tick),
  `kill_state`, `occupancy_snapshot`.

To get the heavy per-tick belief dumps you must **re-run locally** — and you can
**target** specific families without full debug volume:
`CREWBORG_TRACE_GROUPS=decision|voting|action|…`,
`CREWBORG_TRACE_INCLUDE`/`CREWBORG_TRACE_EXCLUDE` (glob patterns; `meeting_*` /
`vote_cast` match `domain.*` too), `CREWBORG_TRACE_DECISION_FIELDS=mode,intent,command`,
and `CREWBORG_METRICS=1` for counters (see `design.md §11`).

> **Default-level caveat.** crewborg's trace default recently changed: `decision_snapshot`
> and per-tick metrics are now **off** by default (debug/`GROUPS=decision`-only), and
> the lean default keeps durable domain events, action attempts, meeting chat/vote
> decisions, per-player deltas, occupancy seeks, and the per-meeting `suspicion_snapshot`.
> Logs captured **before** that change shipped to the league (incl. older v15 episodes)
> still carry `decision_snapshot` per tick — so always confirm what's present with the
> **event histogram** recipe below rather than assuming.

## Reading recipes

Prefilter with **`grep '^{'`** (keeps only JSON lines). `f=logs/policy_agent_7.log`.

```bash
# event-type histogram — run this FIRST: it tells you which events exist,
# so an empty result below means "none happened," not "wrong query/file".
grep '^{' "$f" | jq -r 'select(.kind=="trace")|.event' | sort | uniq -c | sort -rn

# the suspicion timeline (per meeting): top suspects + whether it would vote
grep '^{' "$f" | jq -c 'select(.event=="domain.suspicion_snapshot")
  | {tick, would_vote:.data.would_vote, top:[.data.ranking[]|{c:.color,p:.p}][:3]}'

# what crewborg saw + decided at a given tick
grep '^{' "$f" | jq -c 'select(.tick==3430 and .event=="domain.decision_snapshot")|.data'

# kills / votes / deaths / meeting events — note: exclude meeting_context_serialized,
# whose payload is huge (the full LLM dossier); ask for it explicitly when you want it
grep '^{' "$f" | jq -c 'select((.event//"")|test("vote_cast|kill_|player_died|meeting_"))
  | select(.event!="domain.meeting_context_serialized") | {tick,event,data}'

# phase timeline
grep '^{' "$f" | jq -c 'select(.event=="domain.phase_change")|{tick,from:.data.from,to:.data.to}'
```

Empty output from a `select` is normal (that event didn't occur — confirm against the
histogram); it is **not** an error. Metric lines have no `.event`, so always
`select(.kind=="trace")` or guard `(.event//"")` before `test()`.

## Gotchas

- **Role-gated content:** a crewmate game has no `kill_*`; an imposter game has no
  `suspicion_snapshot` and `null` `visible_players[].suspicion`. `role` may be `dead`
  for the stretch after crewborg dies.
- **Framework `action_intent`/`act_command` payloads are `repr()` strings** — use
  `decision_snapshot.data.intent`/`.command` for the structured form.
- **Hosted logs are capped (~10k lines)** and may be missing the **start** of the game
  — don't assume tick 0 is present.
- **A single league episode can carry more than one crewborg version**, all logging
  this same JSON shape — so identify crewborg's slot by name **and** version from the
  episode metadata (see [`crewrift-replays.md`](../../../docs/crewrift-replays.md) §C),
  not by eyeballing which logs are JSON.
</content>
