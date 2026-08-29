## Reusable pixel-lattice weighted A* planner.

import std/[algorithm, heapqueue, math, monotimes, options, times]
import config, danger_field, types, worldmap

const
  Sqrt2 = sqrt(2.0)
  EndpointSnapPx = 4 * NavCell

type
  PlanCostProfile* = object
    dangerWeight*: float

  PlanResult* = object
    path*: seq[Point]
    expansions*: int
    elapsedMs*: float
    fallbackStep*: int
    startSnapped*, goalSnapped*: bool

  QueueNode = tuple[priority, cost: float, index: int]

  PlannerState* = object
    latticeW, latticeH, mapWidth, mapHeight, step: int
    generation: uint32
    seenGeneration, closedGeneration: seq[uint32]
    gScore: seq[float]
    cameFrom: seq[int32]
    queue: HeapQueue[QueueNode]

proc planCostProfile*(kind: CostProfileKind): PlanCostProfile =
  case kind
  of ProfileDefault:
    PlanCostProfile(dangerWeight: 1.0)
  of ProfileCarrier:
    PlanCostProfile(dangerWeight: ProfileCarrierDanger)
  of ProfileHunter:
    PlanCostProfile(dangerWeight: ProfileHunterDanger)

proc elapsedMs(started: MonoTime): float =
  (getMonoTime() - started).inNanoseconds.float / 1_000_000.0

proc distanceSquared(a, b: Point): int64 =
  let
    dx = (a.x - b.x).int64
    dy = (a.y - b.y).int64
  dx * dx + dy * dy

proc resolveEndpoint(map: WorldMap, endpoint: Point): Option[Point] =
  if map.canStand(endpoint):
    return some(endpoint)
  var
    best = none(Point)
    bestDistance = high(int64)
    bestIndex = high(int)
  let radiusSquared = EndpointSnapPx.int64 * EndpointSnapPx.int64
  for ring in 1 .. EndpointSnapPx:
    for y in max(0, endpoint.y - ring) .. min(map.height - 1, endpoint.y + ring):
      for x in max(0, endpoint.x - ring) .. min(map.width - 1, endpoint.x + ring):
        if max(abs(x - endpoint.x), abs(y - endpoint.y)) != ring:
          continue
        let
          candidate: Point = (x, y)
          candidateDistance = distanceSquared(candidate, endpoint)
          candidateIndex = y * map.width + x
        if candidateDistance > radiusSquared or
            candidateDistance > bestDistance or not map.canStand(candidate):
          continue
        if candidateDistance < bestDistance or candidateIndex < bestIndex:
          best = some(candidate)
          bestDistance = candidateDistance
          bestIndex = candidateIndex
  best

proc latticePoint(state: PlannerState, index: int): Point =
  ((index mod state.latticeW) * state.step,
   (index div state.latticeW) * state.step)

proc ensureWorkspace(state: var PlannerState, map: WorldMap, step: int) =
  ## This is the only allocation point for grid-sized planner storage. Merely
  ## constructing NavState or Belief does not pay for agents that never use A*.
  let
    latticeW = (map.width - 1) div step + 1
    latticeH = (map.height - 1) div step + 1
    size = latticeW * latticeH
  if state.mapWidth == map.width and state.mapHeight == map.height and
      state.step == step and state.seenGeneration.len == size:
    return
  state.mapWidth = map.width
  state.mapHeight = map.height
  state.step = step
  state.latticeW = latticeW
  state.latticeH = latticeH
  state.generation = 0
  state.seenGeneration = newSeq[uint32](size)
  state.closedGeneration = newSeq[uint32](size)
  state.gScore = newSeq[float](size)
  state.cameFrom = newSeq[int32](size)
  state.queue = initHeapQueue[QueueNode]()

proc beginSearch(state: var PlannerState) =
  if state.generation == high(uint32):
    for value in state.seenGeneration.mitems:
      value = 0
    for value in state.closedGeneration.mitems:
      value = 0
    state.generation = 1
  else:
    inc state.generation
  state.queue.clear()

proc nearestConnector(
  state: PlannerState, map: WorldMap, endpoint: Point
): Option[int] =
  if not map.canStand(endpoint):
    return none(int)
  let
    baseX = clamp(pyRound(endpoint.x.float / state.step.float), 0, state.latticeW - 1)
    baseY = clamp(pyRound(endpoint.y.float / state.step.float), 0, state.latticeH - 1)
    maxRing = max(state.latticeW, state.latticeH)
  var
    bestIndex = -1
    bestDistance = high(int64)
  for ring in 0 ..< maxRing:
    for y in max(0, baseY - ring) .. min(state.latticeH - 1, baseY + ring):
      for x in max(0, baseX - ring) .. min(state.latticeW - 1, baseX + ring):
        if max(abs(x - baseX), abs(y - baseY)) != ring:
          continue
        let
          index = y * state.latticeW + x
          candidate = state.latticePoint(index)
          candidateDistance = distanceSquared(candidate, endpoint)
        if candidateDistance > bestDistance or not map.canStand(candidate) or
            not map.segmentClear(endpoint, candidate):
          continue
        if candidateDistance < bestDistance or index < bestIndex:
          bestDistance = candidateDistance
          bestIndex = index
    if bestIndex >= 0:
      let nextRingLowerBound = max(0.0,
        (ring + 1).float * state.step.float - state.step.float / 2.0)
      if bestDistance.float <= nextRingLowerBound * nextRingLowerBound:
        break
  if bestIndex >= 0:
    some(bestIndex)
  else:
    none(int)

proc heuristic(map: WorldMap, point, target, goal: Point): float =
  result = hypot((point.x - target.x).float, (point.y - target.y).float)
  if PlanOracle:
    let cached = map.peekRouteDistance(point, goal)
    if cached.isSome:
      result = max(result, cached.get * 0.999)
  result *= PlanWeight

proc reconstruct(
  state: PlannerState, sourceIndex, targetIndex: int, start, goal: Point
): seq[Point] =
  var cursor = targetIndex
  while true:
    result.add(state.latticePoint(cursor))
    if cursor == sourceIndex:
      break
    cursor = state.cameFrom[cursor].int
  result.reverse()
  if result.len > 0 and result[0] == start:
    result.delete(0)
  if result.len == 0 or result[^1] != goal:
    result.add(goal)

proc searchAtStep(
  state: var PlannerState, map: WorldMap, danger: DangerField,
  start, goal: Point, step: int, profile: PlanCostProfile,
  avoid: Option[Point], expansions: var int
): seq[Point] =
  state.ensureWorkspace(map, step)
  let
    source = state.nearestConnector(map, start)
    target = state.nearestConnector(map, goal)
    avoidCell = if avoid.isSome: some(map.cellOf(avoid.get)) else: none(Point)
  if source.isNone or target.isNone:
    return
  let
    sourceIndex = source.get
    targetIndex = target.get
    targetPoint = state.latticePoint(targetIndex)
  state.beginSearch()
  state.seenGeneration[sourceIndex] = state.generation
  state.gScore[sourceIndex] = 0.0
  state.cameFrom[sourceIndex] = -1
  state.queue.push((map.heuristic(state.latticePoint(sourceIndex), targetPoint, goal),
    0.0, sourceIndex))

  while state.queue.len > 0:
    let current = state.queue.pop()
    if state.closedGeneration[current.index] == state.generation or
        current.cost > state.gScore[current.index]:
      continue
    state.closedGeneration[current.index] = state.generation
    inc expansions
    if current.index == targetIndex:
      result = state.reconstruct(sourceIndex, targetIndex, start, goal)
      return
    let currentPoint = state.latticePoint(current.index)
    for delta in Neighbors:
      let
        nextX = currentPoint.x + delta.x * state.step
        nextY = currentPoint.y + delta.y * state.step
      if nextX < 0 or nextX >= map.width or nextY < 0 or nextY >= map.height:
        continue
      let
        nextPoint: Point = (nextX, nextY)
        nextIndex = (nextY div state.step) * state.latticeW + nextX div state.step
      if state.closedGeneration[nextIndex] == state.generation or
          not map.canStand(nextPoint) or not map.segmentClear(currentPoint, nextPoint):
        continue
      let
        baseCost = state.step.float *
          (if delta.x != 0 and delta.y != 0: Sqrt2 else: 1.0)
        midpoint: Point = ((currentPoint.x + nextPoint.x) div 2,
          (currentPoint.y + nextPoint.y) div 2)
      var edgeCost = baseCost *
        (1.0 + profile.dangerWeight * danger.sample(map, midpoint))
      if avoidCell.isSome and map.cellOf(midpoint) == avoidCell.get:
        edgeCost *= FollowBlockFactor
      let nextCost = current.cost + edgeCost
      if state.seenGeneration[nextIndex] != state.generation or
          nextCost < state.gScore[nextIndex]:
        state.seenGeneration[nextIndex] = state.generation
        state.gScore[nextIndex] = nextCost
        state.cameFrom[nextIndex] = current.index.int32
        state.queue.push((nextCost + map.heuristic(nextPoint, targetPoint, goal),
          nextCost, nextIndex))

proc planPath*(
  state: var PlannerState, map: WorldMap, danger: DangerField,
  start, goal: Point, profile = PlanCostProfile(dangerWeight: 1.0),
  avoid = none(Point)
): PlanResult =
  let started = getMonoTime()
  defer: result.elapsedMs = elapsedMs(started)
  let
    resolvedStart = map.resolveEndpoint(start)
    resolvedGoal = map.resolveEndpoint(goal)
  if resolvedStart.isNone or resolvedGoal.isNone:
    return
  let
    planStart = resolvedStart.get
    planGoal = resolvedGoal.get
  result.startSnapped = planStart != start
  result.goalSnapped = planGoal != goal
  if planStart == planGoal:
    result.path = @[planGoal]
    return
  if not map.sameComponent(planStart, planGoal):
    return

  result.path = state.searchAtStep(
    map, danger, planStart, planGoal, PlanStepPx, profile, avoid, result.expansions)
  if result.path.len == 0 and PlanStepPx > 1:
    # Coarse lattice nodes need not intersect a narrow standable ridge. Halving
    # preserves the common fast path; step 1 is complete for the component's
    # 4-connected pixel paths because every orthogonal pixel edge is admitted.
    let halfStep = max(1, PlanStepPx div 2)
    result.fallbackStep = halfStep
    result.path = state.searchAtStep(
      map, danger, planStart, planGoal, halfStep, profile, avoid, result.expansions)
    if result.path.len == 0 and halfStep > 1:
      result.fallbackStep = 1
      result.path = state.searchAtStep(
        map, danger, planStart, planGoal, 1, profile, avoid, result.expansions)
  if result.startSnapped and result.path.len > 0 and result.path[0] != planStart:
    result.path.insert(planStart, 0)
