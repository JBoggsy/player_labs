## Flow-field lookup and cached weighted A* for moving objectives.

import std/[math, options]
import config, danger_field, planner, types, worldmap

type
  NavState* = object
    goal*: Option[Point]
    path*: seq[Point]
    hasPath*: bool
    cursor*: int
    lastXy*: Option[Point]
    stuckTicks*: int
    blockedPenalty*: Option[tuple[pos: Point, untilTick: int]]
    lastFollowReplanTick*: Option[int]
    followReplans*: int
    followStuckEvents*: int
    microCorridorRejects*: int
    planner*: PlannerState
    profile*: CostProfileKind
    profileSet*: bool
    lastPlanTick*: int
    planCount*: int
    planMsTotal*: float
    planExpansionsTotal*: int
    planUnroutableCount*: int
    planFallbackCount*: int
    planGoalSnappedCount*: int

proc distance(a, b: Point): float = hypot((a.x - b.x).float, (a.y - b.y).float)

proc pointSegmentDistance(point, start, finish: Point): float =
  let
    dx = (finish.x - start.x).float
    dy = (finish.y - start.y).float
  if dx == 0.0 and dy == 0.0:
    return distance(point, start)
  let projection = clamp(
    ((point.x - start.x).float * dx + (point.y - start.y).float * dy) /
      (dx * dx + dy * dy),
    0.0, 1.0)
  hypot(
    point.x.float - (start.x.float + projection * dx),
    point.y.float - (start.y.float + projection * dy))

proc withinCorridor*(state: NavState, point: Point): bool =
  if state.path.len == 0:
    return state.lastXy.isSome and
      distance(point, state.lastXy.get) <= FollowCorridorPx
  let
    cursor = clamp(state.cursor, 0, state.path.high)
    previous = max(0, cursor - 1)
    following = min(state.path.high, cursor + 1)
  min(
    pointSegmentDistance(point, state.path[previous], state.path[cursor]),
    pointSegmentDistance(point, state.path[cursor], state.path[following])) <=
      FollowCorridorPx

proc astarWaypoint*(
  state: var NavState, map: WorldMap, selfXy, goal: Point,
  danger = DangerField(), tick = 0, movingTarget = false,
  profile = ProfileDefault
): Point =
  if state.blockedPenalty.isSome and
      tick >= state.blockedPenalty.get.untilTick:
    state.blockedPenalty = none(tuple[pos: Point, untilTick: int])
  let goalCell = map.cellOf(goal)
  let previousCell = if state.goal.isSome: some(map.cellOf(state.goal.get)) else: none(Point)
  let goalMoved = previousCell.isNone or
    abs(goalCell.x - previousCell.get.x) > ReplanGoalCells or
    abs(goalCell.y - previousCell.get.y) > ReplanGoalCells
  let movingReplan = movingTarget and
    tick - state.lastPlanTick >= PlanMovingReplanTicks
  let profileChanged = not state.profileSet or state.profile != profile
  let forcedReplan = state.stuckTicks >= StuckTicks
  if forcedReplan:
    if state.lastFollowReplanTick.isSome and
        tick - state.lastFollowReplanTick.get <= FollowStuckWindowTicks:
      inc state.followStuckEvents
    state.lastFollowReplanTick = some(tick)
    state.blockedPenalty = some((selfXy, tick + FollowBlockTtlTicks))
    inc state.followReplans
  if goalMoved or profileChanged or not state.hasPath or
      forcedReplan or movingReplan:
    let avoid = if state.blockedPenalty.isSome:
      some(state.blockedPenalty.get.pos) else: none(Point)
    let planned = state.planner.planPath(
      map, danger, selfXy, goal, planCostProfile(profile), avoid)
    state.path = planned.path
    state.goal = some(goal)
    state.profile = profile
    state.profileSet = true
    # Python caches a successful list, but leaves an unroutable path as None so
    # it retries on the next observation. Preserve that distinction here.
    state.hasPath = state.path.len > 0
    state.cursor = 0
    state.stuckTicks = 0
    state.lastPlanTick = tick
    inc state.planCount
    state.planMsTotal += planned.elapsedMs
    state.planExpansionsTotal += planned.expansions
    if planned.fallbackStep > 0:
      inc state.planFallbackCount
    if planned.goalSnapped:
      inc state.planGoalSnappedCount
    if state.path.len == 0:
      inc state.planUnroutableCount
  if state.path.len == 0:
    return selfXy
  while state.cursor < state.path.high and
      distance(selfXy, state.path[state.cursor]) < NavCell.float:
    inc state.cursor
  state.path[state.cursor]

proc noteProgress*(state: var NavState, selfXy: Point) =
  if state.lastXy.isSome and distance(selfXy, state.lastXy.get) < 1.0:
    inc state.stuckTicks
  else:
    state.stuckTicks = 0
  state.lastXy = some(selfXy)

proc resetProgress*(state: var NavState, selfXy: Point) =
  state.stuckTicks = 0
  state.lastXy = some(selfXy)

proc octantToward*(selfXy, waypoint: Point): uint8 =
  let dx = waypoint.x - selfXy.x
  let dy = waypoint.y - selfXy.y
  if abs(dx) < 1 and abs(dy) < 1:
    return 0'u8
  let angle = arctan2(dy.float, dx.float)
  let cosine = cos(angle)
  let sine = sin(angle)
  if cosine > 0.383: result = result or ButtonRight
  elif cosine < -0.383: result = result or ButtonLeft
  if sine > 0.383: result = result or ButtonDown
  elif sine < -0.383: result = result or ButtonUp
