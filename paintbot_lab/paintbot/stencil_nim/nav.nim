## Flow-field lookup and cached A* for moving objectives.

import std/[algorithm, heapqueue, math, options]
import config, types, worldmap

const Sqrt2 = sqrt(2.0)

type
  AstarNode = tuple[priority, cost: float, x, y: int]

  NavState* = object
    goal*: Option[Point]
    path*: seq[Point]
    hasPath*: bool
    cursor*: int
    lastXy*: Option[Point]
    stuckTicks*: int

proc distance(a, b: Point): float = hypot((a.x - b.x).float, (a.y - b.y).float)
proc gridIndex(map: WorldMap, point: Point): int = point.y * map.gridW + point.x

proc astar(map: WorldMap, start, goal: Point): seq[Point] =
  let source = map.nearestWalkable(map.cellOf(start))
  let target = map.nearestWalkable(map.cellOf(goal))
  if source == target:
    return @[cellCenter(target)]
  proc heuristic(point: Point): float =
    hypot((point.x - target.x).float, (point.y - target.y).float)

  var
    queue = initHeapQueue[AstarNode]()
    came = newSeq[int](map.walkable.len)
    best = newSeq[float](map.walkable.len)
  for value in came.mitems: value = -1
  for value in best.mitems: value = Inf
  best[map.gridIndex(source)] = 0.0
  queue.push((heuristic(source), 0.0, source.x, source.y))
  while queue.len > 0:
    let current = queue.pop()
    let currentPoint: Point = (current.x, current.y)
    if currentPoint == target:
      var cursor = map.gridIndex(target)
      while cursor >= 0:
        result.add(cellCenter((cursor mod map.gridW, cursor div map.gridW)))
        cursor = came[cursor]
      result.reverse()
      return
    if current.cost > best[map.gridIndex(currentPoint)]:
      continue
    for delta in Neighbors:
      let next: Point = (current.x + delta.x, current.y + delta.y)
      if next.x < 0 or next.x >= map.gridW or next.y < 0 or next.y >= map.gridH or
          not map.walkable[map.gridIndex(next)]:
        continue
      if delta.x != 0 and delta.y != 0 and
          (not map.walkable[map.gridIndex((next.x, current.y))] or
           not map.walkable[map.gridIndex((current.x, next.y))]):
        continue
      let nextCost = current.cost +
        (if delta.x != 0 and delta.y != 0: Sqrt2 else: 1.0)
      if nextCost < best[map.gridIndex(next)]:
        best[map.gridIndex(next)] = nextCost
        came[map.gridIndex(next)] = map.gridIndex(currentPoint)
        queue.push((nextCost + heuristic(next), nextCost, next.x, next.y))

proc astarWaypoint*(
  state: var NavState, map: WorldMap, selfXy, goal: Point
): Point =
  let goalCell = map.cellOf(goal)
  let previousCell = if state.goal.isSome: some(map.cellOf(state.goal.get)) else: none(Point)
  let goalMoved = previousCell.isNone or
    abs(goalCell.x - previousCell.get.x) > ReplanGoalCells or
    abs(goalCell.y - previousCell.get.y) > ReplanGoalCells
  if goalMoved or not state.hasPath or state.stuckTicks >= StuckTicks:
    state.path = map.astar(selfXy, goal)
    state.goal = some(goal)
    # Python caches a successful list, but leaves an unroutable path as None so
    # it retries on the next observation. Preserve that distinction here.
    state.hasPath = state.path.len > 0
    state.cursor = 0
    state.stuckTicks = 0
  if state.path.len == 0:
    return goal
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

proc octantToward*(selfXy, waypoint: Point, jitter: bool): uint8 =
  let dx = waypoint.x - selfXy.x
  let dy = waypoint.y - selfXy.y
  if abs(dx) < 1 and abs(dy) < 1:
    return 0'u8
  var angle = arctan2(dy.float, dx.float)
  if jitter:
    angle += PI / 2.0
  let cosine = cos(angle)
  let sine = sin(angle)
  if cosine > 0.383: result = result or ButtonRight
  elif cosine < -0.383: result = result or ButtonLeft
  if sine > 0.383: result = result or ButtonDown
  elif sine < -0.383: result = result or ButtonUp
