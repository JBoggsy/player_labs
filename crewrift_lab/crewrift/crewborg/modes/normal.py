"""Normal mode: the default crewmate stance — complete assigned tasks (design §7.1).

Targeting is driven off the **live task-signal set** (``visible_task_indices`` — the
arrows + bubbles, which together mark exactly the incomplete assigned tasks): pick
the nearest **reachable** signalled task, emit ``complete_task(T)`` until it's done,
then move to the next. When **no** task signal remains, every task is done, so head
back to the spawn / start room rather than standing still.

**Completion detection.** The authoritative signal is the **bubble disappearing**
(``T`` leaving the signal set while we are inside its rect). But a bubble can also
blink out for a tick from occlusion (an imposter overlapping us) or a screen-edge —
so we *gate* it on the progress bar: ``T`` is concluded done only if we recently saw
its progress reach ``COMPLETION_PROGRESS_PCT`` (≈ done). A bubble vanishing without
that progress is treated as a flicker — we keep holding the same task. Progress is
only a gate, never the trigger (so we never stop the hold early at, say, 98%); and
because targeting uses the live signals, a falsely-concluded task that is still
signalled is simply re-targeted (self-healing).

Stall guards (design §5, best_practices "idling is dangerous"):

- *Reachability* — prefer tasks the nav graph can actually route to, so we don't
  fixate on an unreachable station (the action layer holds still on no path).
- *Arrows-disabled sweep* — when ``showTaskArrows`` is off, off-screen tasks emit
  no signals, so the signal set can be empty at spawn even with tasks to do. Rather
  than head home immediately, sweep the baked stations to discover assigned ones.
- *Stall escape* — league forensics (H4, v82 warehouse) found crew seats standing
  frozen for thousands of ticks while holding a task target: wedged one pixel
  outside the station rect by the action deadband, or parked on an unroutable
  goal (the "hold still on no path" above, which nothing ever reacted to). So:
  standing in one spot with zero task progress for ``STALL_ESCAPE_TICKS`` blocks
  the held target for a retry window and forces a fresh pick — we never stand
  still holding a target that is going nowhere.

Witness posture: when no workable task remains (all done, or every remaining one
stall-blocked), a *live* crewmate shadows the nearest other live crewmate at a
small offset instead of idling solo — a witness deters kills and sees what
happens. Ghosts keep the old walk home (no witness value in a ghost).
"""

from __future__ import annotations

from crewrift.crewborg.map.types import Room, TaskStation
from crewrift.crewborg.strategy.commander.bias import commander_of, room_crew_count
from crewrift.crewborg.types import ActionState, Belief, Intent
from players.player_sdk import EmptyModeParams, Mode

# A bubble leaving the signal set counts as completion only if progress recently
# reached at least this — otherwise it's treated as a flicker/occlusion.
COMPLETION_PROGRESS_PCT = 90
SWEEP_ARRIVE_RADIUS = 24  # within this of a station center ⇒ count it as checked

# Stall escape: standing in one spot with no task-progress change for this many
# ticks means execution is wedged (deadband stall / unroutable goal) — never stand
# still longer than this holding a target.
STALL_ESCAPE_TICKS = 100
# A stall-blocked task becomes pickable again after this many ticks (the wedge may
# have been transient — a meeting teleport or a crowd shove clears it; the action
# layer's center-nudge usually fixes it outright on the retry).
BLOCKED_TASK_RETRY_TICKS = 900
# Witness posture: how often to re-pick which live crewmate to shadow, and how far
# from them to stand (just outside their sprite, well inside sight range).
SHADOW_REPICK_TICKS = 200
SHADOW_OFFSET_PX = 28


class NormalMode(Mode[Belief, ActionState, Intent]):
    name = "normal"
    params_type = EmptyModeParams

    def __init__(self, params=None) -> None:
        super().__init__(params)
        self._target: int | None = None
        self._max_progress: int = 0  # peak progress seen for the current target
        self._swept: set[int] = set()
        # Stall-escape state: the last observed (position, progress) signature and
        # when it last changed, plus targets blocked by a stall (index -> block tick).
        self._stall_signature: tuple[tuple[int, int], int | None] | None = None
        self._stall_since: int = 0
        self._blocked: dict[int, int] = {}
        # Witness-posture state: who we're shadowing and when we picked them; the
        # flip alternates the offset side when a shadow spot itself stalls.
        self._shadow_color: str | None = None
        self._shadow_picked_tick: int = 0
        self._shadow_flip: bool = False

    def decide(self, belief: Belief, action_state: ActionState) -> Intent:
        del action_state
        tasks = belief.map.tasks if belief.map is not None else ()

        self._update_stall(belief)
        self._update_target(belief, tasks)
        if self._target is not None:
            return Intent(kind="complete_task", task_index=self._target, reason="completing assigned task")

        hard_position = _hard_target_room_intent(belief)
        if hard_position is not None:
            return hard_position

        sweep = self._sweep_intent(belief, tasks)
        if sweep is not None:
            return sweep

        shadow = self._shadow_intent(belief)
        if shadow is not None:
            return shadow
        return _return_to_start(belief)

    def _update_stall(self, belief: Belief) -> None:
        """Escape a wedged execution: same spot + no task progress for too long.

        League forensics (H4): a held ``complete_task`` can stand forever — wedged
        one pixel outside the station rect by the action deadband, or parked on an
        unroutable goal. Working a task is *not* a stall (progress keeps changing),
        and any movement resets the clock (a meeting teleport counts as movement).
        """

        xy = _self_xy(belief)
        now = belief.last_tick
        if xy is None:
            self._stall_signature = None
            return
        signature = (xy, belief.active_task_progress_pct)
        if signature != self._stall_signature:
            self._stall_signature = signature
            self._stall_since = now
            return
        if now - self._stall_since < STALL_ESCAPE_TICKS:
            return
        # Wedged. Block the held target for a retry window and force a fresh pick;
        # a stalled shadow spot instead flips to the target's other side.
        if self._target is not None:
            self._blocked[self._target] = now
            self._target = None
        else:
            self._shadow_color = None
            self._shadow_flip = not self._shadow_flip
        self._stall_since = now

    def _update_target(self, belief: Belief, tasks: tuple[TaskStation, ...]) -> None:
        """Conclude/keep the current target, then pick a new one off the live signals."""

        signals = belief.visible_task_indices
        target = self._target
        if target is not None and target < len(tasks):
            on_station = _inside(tasks[target], belief.self_world_x, belief.self_world_y)
            if on_station and belief.active_task_progress_pct is not None:
                self._max_progress = max(self._max_progress, belief.active_task_progress_pct)
            if target not in signals:
                # Bubble gone: a real completion only if progress reached ~done.
                # Otherwise it's a flicker/occlusion — keep holding the same task.
                if self._max_progress >= COMPLETION_PROGRESS_PCT:
                    belief.completed_task_indices.add(target)
                    self._target = None
            # if still signalled, keep the current target (avoids thrashing).

        if self._target is None:
            self._target = self._pick_target(belief, tasks, signals)
            self._max_progress = 0

    def _pick_target(self, belief: Belief, tasks: tuple[TaskStation, ...], signals: set[int]) -> int | None:
        # The live signal set is the authoritative list of remaining tasks; a task
        # still signalled is still to do (even if we earlier mis-concluded it done).
        # Stall-blocked tasks are skipped until their retry window expires; with
        # every signalled task blocked we return None (the witness posture takes
        # over until a retry comes due).
        now = belief.last_tick
        self._blocked = {i: t for i, t in self._blocked.items() if now - t < BLOCKED_TASK_RETRY_TICKS}
        candidates = [index for index in signals if index < len(tasks) and index not in self._blocked]
        if not candidates:
            return None

        # Prefer tasks with a baked reachable anchor; fall back to all if none have
        # one (rare — the action layer then holds still rather than wall-drive).
        if belief.nav is not None:
            reachable = [i for i in candidates if belief.nav.task_anchor(i) is not None]
            if reachable:
                candidates = reachable

        cmd = commander_of(belief)
        if cmd is not None:
            if cmd.target_task in candidates:
                return cmd.target_task
            if cmd.target_room is not None:
                target_room_candidates = [i for i in candidates if _task_room(belief, tasks[i]) == cmd.target_room]
                if target_room_candidates:
                    candidates = target_room_candidates
                elif cmd.strength == "hard" and _room_exists(belief, cmd.target_room):
                    return None

        self_xy = _self_xy(belief)
        if self_xy is None:
            return min(candidates)
        if cmd is not None and cmd.posture != "neutral":
            return min(candidates, key=lambda i: _posture_key(belief, tasks[i], cmd.posture, self_xy, i))
        return min(candidates, key=lambda i: _dist2(self_xy, _nav_point(belief, tasks[i], i)))

    def _sweep_intent(self, belief: Belief, tasks: tuple[TaskStation, ...]) -> Intent | None:
        """Sweep baked stations to discover assigned tasks (arrows-disabled, §5)."""

        # Only sweep before any task signal has arrived, while the crew still has
        # tasks to do, and once we know where we are.
        if belief.assigned_task_indices or not tasks or belief.crew_tasks_remaining == 0:
            return None
        self_xy = _self_xy(belief)
        if self_xy is None:
            return None

        # Mark stations we have reached as checked.
        for index, task in enumerate(tasks):
            if _dist2(self_xy, _center(task)) <= SWEEP_ARRIVE_RADIUS**2:
                self._swept.add(index)

        remaining = [i for i in range(len(tasks)) if i not in self._swept]
        if not remaining:
            return None  # checked every station and found no assigned tasks
        nearest = min(remaining, key=lambda i: _dist2(self_xy, _nav_point(belief, tasks[i], i)))
        return Intent(kind="navigate_to", point=_nav_point(belief, tasks[nearest], nearest), reason="sweeping for tasks")

    def _shadow_intent(self, belief: Belief) -> Intent | None:
        """Witness posture: shadow the nearest live crewmate at a small offset.

        Fires only for a *live* crewmate with no workable task (all done, or every
        remaining one stall-blocked): standing near another player is witness
        cover — it deters kills and puts us where the game is happening — instead
        of idling solo. The shadow target is re-picked every SHADOW_REPICK_TICKS
        (or when it dies); ghosts skip this (no witness value) and walk home.
        """

        if not belief.self_alive:
            return None
        self_xy = _self_xy(belief)
        if self_xy is None:
            return None

        now = belief.last_tick
        if self._shadow_color is not None:
            record = belief.roster.get(self._shadow_color)
            if record is None or record.life_status == "dead" or now - self._shadow_picked_tick >= SHADOW_REPICK_TICKS:
                self._shadow_color = None
        if self._shadow_color is None:
            nearest = self._nearest_live_other(belief, self_xy)
            if nearest is None:
                return None
            self._shadow_color = nearest
            self._shadow_picked_tick = now

        record = belief.roster[self._shadow_color]
        side = -1 if self._shadow_flip else 1
        goal = (record.world_x + side * SHADOW_OFFSET_PX, record.world_y)
        if belief.nav is not None:
            cell = belief.nav.nearest_reachable_node(*goal)
            if cell is not None:
                goal = belief.nav.node_point[cell]
        return Intent(kind="navigate_to", point=goal, reason=f"witness posture: shadowing {self._shadow_color}")

    def _nearest_live_other(self, belief: Belief, self_xy: tuple[int, int]) -> str | None:
        """Color of the nearest known-live other player (last-known fix)."""

        best: str | None = None
        best_d = None
        for record in belief.roster.values():
            if record.color == belief.self_color or record.life_status == "dead":
                continue
            if record.last_seen_tick == 0:
                continue  # never actually sighted — no positional fix to walk to
            d = _dist2(self_xy, (record.world_x, record.world_y))
            if best_d is None or d < best_d:
                best, best_d = record.color, d
        return best


def _return_to_start(belief: Belief) -> Intent:
    """All assigned tasks done — head back to the spawn / start room instead of
    standing still (which strands a finished crewmate and earns stuck penalties)."""

    if belief.map is None:
        return Intent(kind="idle", reason="no incomplete tasks remain")
    goal = (belief.map.home.x, belief.map.home.y)
    if belief.nav is not None:
        cell = belief.nav.nearest_reachable_node(*goal)
        if cell is not None:
            goal = belief.nav.node_point[cell]
    return Intent(kind="navigate_to", point=goal, reason="tasks done: returning to the start room")


def _hard_target_room_intent(belief: Belief) -> Intent | None:
    cmd = commander_of(belief)
    if cmd is None or cmd.strength != "hard" or cmd.target_room is None or belief.map is None:
        return None
    room = _room_exists(belief, cmd.target_room)
    if room is None:
        return None
    goal = (room.center.x, room.center.y)
    if belief.nav is not None:
        cell = belief.nav.nearest_reachable_node(*goal)
        if cell is not None:
            goal = belief.nav.node_point[cell]
    return Intent(kind="navigate_to", point=goal, reason=f"commander: positioning in {room.name}")


def _room_exists(belief: Belief, name: str) -> Room | None:
    if belief.map is None:
        return None
    return next((room for room in belief.map.rooms if room.name == name), None)


def _inside(task: TaskStation, x: int | None, y: int | None) -> bool:
    if x is None or y is None:
        return False
    return task.x <= x < task.x + task.w and task.y <= y < task.y + task.h


def _center(task: TaskStation) -> tuple[int, int]:
    return task.center.x, task.center.y


def _nav_point(belief: Belief, task: TaskStation, index: int) -> tuple[int, int]:
    """The station's baked reachable anchor, or its center before the graph exists."""

    if belief.nav is not None:
        anchor = belief.nav.task_anchor(index)
        if anchor is not None:
            return anchor
    return task.center.x, task.center.y


def _task_room(belief: Belief, task: TaskStation) -> str | None:
    if belief.map is None:
        return None
    x, y = task.center.x, task.center.y
    room = next((room for room in belief.map.rooms if room.x <= x < room.x + room.w and room.y <= y < room.y + room.h), None)
    return room.name if room is not None else None


def _posture_key(
    belief: Belief,
    task: TaskStation,
    posture: str,
    self_xy: tuple[int, int],
    index: int,
) -> tuple[int, int]:
    room = _task_room(belief, task)
    crew_count = room_crew_count(belief, room) if room is not None else 0
    posture_score = -crew_count if posture == "stick" else crew_count
    return posture_score, _dist2(self_xy, _nav_point(belief, task, index))


def _self_xy(belief: Belief) -> tuple[int, int] | None:
    if belief.self_world_x is None or belief.self_world_y is None:
        return None
    return belief.self_world_x, belief.self_world_y


def _dist2(a: tuple[int, int], b: tuple[int, int]) -> int:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
