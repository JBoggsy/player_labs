# Crewmate play: the detective loop

How crewborg plays a crewmate end to end — the per-tick mode the selector picks, the
task-doing it does most of the time, the one-shot meeting it can call on a player tailing
it, and how it behaves at a meeting and as a ghost. This is the narrative that ties
`strategy/rule_based.py`, `modes/normal.py`, `modes/accuse.py`, `modes/report_body.py`,
and `modes/attend_meeting.py` together; the per-file docstrings have the local detail and
[`../design.md`](../design.md) §10 is the structural contract.

This doc is descriptive of the crewmate path only. It defers three things that live
elsewhere: the suspicion **model** (prior, log-LRs, thresholds) to
[`./suspicion.md`](./suspicion.md); the meeting **mechanics** (LLM path, fallback timing,
vote legality, chat parsing) to [`./meetings.md`](./meetings.md); and movement (routing,
button presses) to [`./navigation.md`](./navigation.md). The imposter's selector branch is
[`./imposter-play.md`](./imposter-play.md). For orientation start at
[`../README.md`](../README.md).

---

## The shape of it

A crewmate spends almost all its time in **Normal** mode doing tasks. The other crewmate
modes are interrupts the selector reaches for when belief crosses a line: a meeting opens,
a body comes into view, or a suspected imposter is actively shadowing it. The loop is
"do tasks, but watch — and when the evidence is there, drag a suspect into a public vote."

```
            ┌─────────────── every tick ───────────────┐
            │  RuleBasedStrategy._select(belief)        │
            └───────────────────────────────────────────┘
 Voting phase? ─────────────────────────────► attend_meeting
 Playing + ghost? ─────────────────────────► normal (finish own tasks)
 Playing + imposter? ──────────────────────► (imposter-play.md)
 Playing + live crewmate:
    body in view? ─────────────────────────► report_body
    button free & a suspect tailing us? ───► accuse  (call a meeting)
    else ──────────────────────────────────► normal  (do tasks)
 any other phase ──────────────────────────► idle
```

The selector (`strategy/rule_based.py:RuleBasedStrategy._select`) is a pure function of
belief plus two sticky fields it owns (`_accuse_target`, `_button_call_spent`). It only
**chooses** a mode and returns a `ModeDirective`; the chosen mode object produces the
`Intent`, and `action.py` turns that into wire input. No mode here moves the agent.

---

## The per-tick crewmate selector

`_select` dispatches on phase first, then aliveness, then role. The crewmate-specific
priority order lives in the `phase == "Playing"` branch for a live crewmate (alive, and
`self_role` not `"imposter"`).

| Priority | Condition | Mode | Reason string |
|---|---|---|---|
| 1 | `phase == "Voting"` (any role) | `attend_meeting` | `meeting open` |
| 2 | `phase == "Playing"`, ghost (`not self_alive`) | `normal` | `ghost: finish own tasks` |
| 3 | `phase == "Playing"`, imposter | (`_select_imposter`) | — |
| 4 | live crewmate, a body in view | `report_body` | `body in view` |
| 5 | live crewmate, button reachable + a sticky accuse target | `accuse` | `being tailed: call a meeting` |
| 6 | live crewmate, otherwise | `normal` | `playing: do tasks` |
| — | any non-play phase (VoteResult / GameOver / unknown) | `idle` | `idle in phase {phase}` |

Notes that are easy to miss:

- **Voting outranks everything, for every role.** A meeting is open, so the selector
  returns `attend_meeting` before it even looks at role, and clears `_accuse_target`
  (there is nothing to walk to once the meeting is up).
- **Report-body outranks accusing.** A visible body is checked
  (`any(bid in belief.bodies for bid in belief.visible_body_ids)`) before the tail check.
  Reporting opens a meeting *right here* and does **not** spend the one button call, so it
  is strictly better than walking to the button to call one. When the selector takes
  report-body or anything other than accuse, it clears `_accuse_target`.
- **Ghosts stay crewmates of a sort.** A dead crewmate can neither report nor be
  threatened, so it skips straight to Normal and finishes its own tasks (design §7.3).
- **Per-game reset.** On `Lobby` / `RoleReveal` the selector calls `_reset_for_new_game`,
  which drops any committed accuse target and restores the single button-call budget.

### The accuse gate (priority 5)

Two things must both hold for the selector to enter Accuse:

1. **The button is reachable** — `_button_reachable(belief)`. Before any nav graph exists
   (`belief.nav is None`) this is optimistically `True` (the action layer steers straight
   at the button center and the graph builds within a tick or two). Once the graph exists,
   a missing `nav.button_anchor` means the button is unrouteable, so the gate is `False`
   and the crewmate keeps tasking rather than stalling at an unreachable goal.
2. **There is a sticky accuse target** — `_sticky_accuse_target(belief)` is not `None`.

When both hold the selector returns `accuse`. If our own position is already inside the
button rect that tick (`_inside_button_rect`), it sets `_button_call_spent = True` —
because the A-press at the button fires this tick and the emergency button is a one-shot
resource (`buttonCalls = 1`).

### Sticky accuse target and the commit-to-the-walk

`_sticky_accuse_target` is what makes Accuse *commit* to a target across the walk to the
button instead of flickering on and off with the tail:

- If `_button_call_spent` is already set, it returns `None` forever (this game) — we never
  call a second meeting; we fall back to tasks.
- If we already have a committed `_accuse_target` that is still alive **and** still
  `top_suspect` (the player the meeting would vote out), we **keep** it — even if the tail
  briefly lapses while we walk (suspicion persists, so a near-certain suspect stays
  convictable). But if it's been exculpated back below the vote bar — or overtaken /
  voted / killed — we drop it and re-acquire, so we never march the one-shot button run
  toward a meeting we can no longer win (or one that would eject a teammate).
- Otherwise we re-acquire from `strategy/suspicion.py:active_tail_suspect` — the player
  with an *ongoing* `tailing_self` interval who is also `top_suspect` (the player the
  meeting would vote out), so the call bar is the conviction bar. See
  [`./suspicion.md`](./suspicion.md) for what makes a tail
  "active" and how the posterior gets there; see [`./agent-tracking.md`](./agent-tracking.md)
  for how `tailing_self` intervals are detected.

The trigger is being *actively shadowed by a player we have grown suspicious of*. Crewborg's
answer is not to flee — it drops what it is doing and goes to call a public vote on them.

---

## Normal mode — the task play

`modes/normal.py:NormalMode` is the default crewmate stance: complete assigned tasks
(design §7.1). It holds three pieces of cross-tick state — `_target` (the task index it is
committed to), `_max_progress` (peak progress seen for that target), and `_swept`
(stations checked during a no-signal sweep).

### Targeting off the live signal set

The authoritative list of remaining work is **`belief.visible_task_indices`** — the live
task-signal set (the on-screen arrows + bubbles, which together mark exactly the incomplete
assigned tasks). `_pick_target` chooses from it:

1. Candidates are the signalled indices that exist in the map's task list.
2. Prefer tasks with a **baked reachable anchor** (`nav.task_anchor(i) is not None`) so we
   don't fixate on a station the nav graph can't route to; fall back to all candidates only
   if none are reachable.
3. Apply any commander bias (a named task/room or a stick/isolate posture) — gated and off
   by default; see [`./commander.md`](./commander.md). It never overrides the signal set's
   notion of what is still to do.
4. Pick the **nearest** remaining task by squared distance to its nav point (or the
   posture-scored one).

While a target is held, Normal emits `Intent(kind="complete_task", task_index=_target)`
every tick; `action.py:_resolve_complete_task` routes onto the station and holds A.

### Completion detection — gated on progress so a flicker can't false-complete

The authoritative completion signal is the **bubble disappearing** — the target leaving
`visible_task_indices` while we stand inside its rect. But a bubble can also blink out for a
tick from occlusion (an imposter overlapping us) or a screen edge, which would wrongly mark
the task done. So `_update_target` **gates** the disappearance on the progress bar:

- While we are inside the target's rect, `_max_progress` tracks the peak
  `belief.active_task_progress_pct` seen.
- When the target leaves the signal set, it is concluded **done only if**
  `_max_progress >= COMPLETION_PROGRESS_PCT` (90). It is then added to
  `belief.completed_task_indices` and the target is released.
- A bubble that vanishes without that progress is treated as a **flicker** — we keep
  holding the same task.

Progress is a **gate, never the trigger** — we never stop a hold early at, say, 98%; only
the bubble leaving ends it. And because targeting reads the live signals, a falsely
concluded task that is still signalled is simply re-targeted next tick (self-healing).

### When no task is signalled

If no target is held after `_update_target`, Normal falls through in order:

1. **Commander hard-room position** (`_hard_target_room_intent`) — only when a gated
   commander directive forces a room at `strength == "hard"`; navigate to that room's
   reachable center. Off by default ([`./commander.md`](./commander.md)).
2. **Arrows-disabled sweep** (`_sweep_intent`) — when `showTaskArrows` is off, off-screen
   tasks emit no signals, so the signal set can be empty at spawn even with tasks to do.
   Rather than head home, sweep the baked stations to discover assigned ones. It runs only
   before any task signal has arrived (`not belief.assigned_task_indices`), while the crew
   still has tasks (`crew_tasks_remaining != 0`), and once our position is known. Stations
   within `SWEEP_ARRIVE_RADIUS` (24 px) of us are marked `_swept`; we navigate to the
   nearest unswept one.
3. **Return to start** (`_return_to_start`) — every assigned task is done, so head back to
   the spawn / start room (`belief.map.home`, snapped to the nearest reachable node) rather
   than standing still (a stranded finished crewmate earns stuck penalties).

---

## Accuse mode — calling a meeting on a tail

`modes/accuse.py:AccuseMode` is selected when a live crewmate is being actively tailed by a
suspect the meeting would convict (the tailer is `top_suspect`) and the one button call is
still unspent and reachable. The
mode itself is **stateless** and does one thing: it emits

```
Intent(kind="call_meeting", target_color=active_tail_suspect(belief))
```

The `target_color` is best-effort only — a record of whom we mean to accuse. It is `None`
if the tail lapsed this very tick; the action layer still heads for the button regardless,
and the meeting re-derives the actual vote from suspicion when it opens.

The division of labor is deliberate:

- **The selector owns the budget and the commitment.** It decides when to spend the
  one-shot button (and refuses to re-enter Accuse once `_button_call_spent`), and it keeps
  `_sticky_accuse_target` locked on the committed player through the whole walk even if the
  tail briefly drops — so the agent commits to the walk instead of abandoning it the first
  frame the tailer steps out of view. The commitment is gated on **convictability**, not
  the tail: it holds while the suspect is still `top_suspect` (the meeting would eject it),
  and is released the moment it's exculpated below the vote bar / overtaken / voted /
  killed — so a tail lapse keeps the walk, but a suspect that stops being convictable sends
  us back to tasks rather than to a button press we can't win.
- **The action layer does the walking and pressing.**
  `action.py:_resolve_call_meeting` drives onto the button's reachable anchor
  (`nav.button_anchor`, or the button center before the graph exists) and, once standing in
  the button rect, fires a fresh edge-triggered A press (`tryCallButton`). It holds still
  until the map / nav graph is available. See [`./navigation.md`](./navigation.md).
- **Attend Meeting casts the actual vote**, re-derived from the same suspicion model once
  the meeting opens (below). Accuse never votes.

This replaces a keep-away/flee response entirely: a believed imposter shadowing us is
answered by dragging it into a public vote, not by running.

---

## Meeting conduct as a crewmate

`modes/attend_meeting.py:AttendMeetingMode` is active for the whole `Voting` phase, whether
the meeting was opened by us, by a body report, or by another player. It runs an
LLM-driven primary path and a deterministic fallback; the **meeting mechanics** — LLM
cadence, validation, chat parsing, vote legality, and the deadline-safety timing — are
[`./meetings.md`](./meetings.md). What matters for *crewmate strategy* is the deterministic
crewmate decision and the invariants that hold on every path.

### Accuse-then-vote a clear leading suspect, else stay silent

`_decide_crewmate` couples chat and vote — we accuse exactly whom we vote (the anti-tell) —
and exercises **vote restraint**:

- It asks `strategy/suspicion.py:top_suspect(belief)` for the **clear leading suspect**.
  That returns a color only when the evidence stands out (near-certainty, or a clear lead
  over a non-flat field); on a flat field it returns `None`. The thresholds and the
  fitted-vs-hand vote rules live in [`./suspicion.md`](./suspicion.md).
- **If there is a clear leader**, we set it as the tentative vote and build an accusation
  with `strategy/meeting/accusation.py:build_accusation` — `"<color> sus: <reason>, <reason>"`,
  the suspect's event-log cues rendered as short phrases and **ranked strongest-first** by
  how much each cue moved the posterior (witnessed kill/vent, then tailing-us, follow-to-
  death, body proximity, vent dwell). We send that as chat (path `accuse`) and vote that
  color. If the suspect has no citable evidence to phrase, we skip the chat but still vote
  them (path `vote_no_chat`).
- **If there is no clear leader**, we stay silent and skip (path `silent_skip`). This is
  the vote-restraint that avoids ejecting crewmates: an innocent ejection is a parity gift
  to the imposters, so a flat or low field names no one.

### Always cast something before the timer

Whatever the path, a vote is **always cast before the meeting clock expires** — the
deadline-safety invariant. The deterministic crewmate ends in `_submit_vote_intent`, and
the auto-submit window forces a vote out even if nothing decisive emerged. A hard guard
also forbids ever voting our own color (coerced to skip). The exact timing windows are in
[`./meetings.md`](./meetings.md).

---

## Ghost crewmate

A crewmate that has been killed (`not self_alive`) still has a job: finish its own
tasks (design §7.3). The selector routes a ghost straight to Normal (`ghost: finish own
tasks`) in the `Playing` phase — it never reaches report-body or accuse (a ghost can't
report a body or be threatened, and holds no suspicion). It otherwise runs the same Normal
task loop: nearest signalled task, progress-gated completion, return-to-start when done.

---

## Files and entry points

| File | Role in the crewmate loop |
|---|---|
| `strategy/rule_based.py:RuleBasedStrategy._select` | per-tick crewmate mode selector + sticky accuse / button budget |
| `strategy/rule_based.py:_button_reachable` | whether the emergency button can be routed to |
| `strategy/suspicion.py:active_tail_suspect` | the Accuse trigger (a tailing suspect who is also `top_suspect` — the call bar = the conviction bar) |
| `strategy/suspicion.py:top_suspect` | the meeting vote target (clear leading suspect, or `None`) |
| `modes/normal.py:NormalMode` | task targeting, progress-gated completion, sweep, return-to-start |
| `modes/report_body.py:ReportBodyMode` | report the nearest visible body (outranks accusing) |
| `modes/accuse.py:AccuseMode` | emit `call_meeting` on the committed tail |
| `modes/attend_meeting.py:AttendMeetingMode._decide_crewmate` | accuse-then-vote a clear suspect, else silent skip |
| `strategy/meeting/accusation.py:build_accusation` | ranked event-log cues for the accusation line |
| `action.py:_resolve_call_meeting` / `_resolve_complete_task` | execute the button-walk and the task-hold |

### Key constants

| Constant | Value | Where | Meaning |
|---|---|---|---|
| _(accuse bar)_ | = conviction bar | `strategy/suspicion.py` | no standalone threshold; an active tail triggers Accuse only when the tailer is `top_suspect` (the player the meeting would vote out) |
| `ACCUSE_TAIL_RECENCY_TICKS` | `6` | `strategy/suspicion.py` | a tail counts as "active" if extended within this many ticks |
| `COMPLETION_PROGRESS_PCT` | `90` | `modes/normal.py` | progress a vanished bubble needs to count as a real completion |
| `SWEEP_ARRIVE_RADIUS` | `24` | `modes/normal.py` | distance (px) within which a swept station counts as checked |
| `buttonCalls` | `1` | sim | the emergency button is a one-shot per game |
