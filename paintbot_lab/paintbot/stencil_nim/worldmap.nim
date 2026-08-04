## Episode-scoped terrain, route fields, and derived tactical geometry.

import std/[heapqueue, math, monotimes, options, tables, times]
import config, types

const
  Neighbors*: array[8, Point] = [
    (-1, 0), (1, 0), (0, -1), (0, 1),
    (-1, -1), (-1, 1), (1, -1), (1, 1)]
  PlayerHalf* = 6
  Sqrt2 = sqrt(2.0)

type
  Endzone* = object
    color*: Team
    shape*: string
    x0*, y0*, x1*, y1*: int

  QueueNode = tuple[distance: float, x, y: int]

  RouteFields = object
    distances: seq[float]
    hops: seq[uint8]

  WorldMap* = ref object
    width*, height*, teams*: int
    center*: Point
    wall*: seq[bool]
    gridW*, gridH*: int
    walkable*: seq[bool]
    cover*: seq[bool]
    endzones*: Table[Team, Endzone]
    pedestals*: Table[Team, Point]
    fields: Table[int, RouteFields]
    baseInitMs*, erodeMs*, coverMs*: float
    dijkstraMs*: seq[float]

proc elapsedMs(started: MonoTime): float =
  (getMonoTime() - started).inNanoseconds.float / 1_000_000.0

proc center*(zone: Endzone): Point =
  ((zone.x0 + zone.x1) div 2, (zone.y0 + zone.y1) div 2)

proc contains*(zone: Endzone, point: Point): bool =
  if point.x < zone.x0 or point.x > zone.x1 or
      point.y < zone.y0 or point.y > zone.y1:
    return false
  if zone.shape == "disc":
    let
      middle = zone.center
      radius = min(zone.x1 - zone.x0, zone.y1 - zone.y0).float / 2.0
    return hypot((point.x - middle.x).float, (point.y - middle.y).float) <= radius
  true

template gridIndex(map: WorldMap, x, y: int): int = y * map.gridW + x
template pixelIndex(map: WorldMap, x, y: int): int = y * map.width + x

proc erode(map: WorldMap, pixelWalkable: openArray[bool]): seq[bool] =
  ## Summed-area footprint erosion: O(pixels + cells), one allocation per array.
  let satWidth = map.width + 1
  var sat = newSeq[int32]((map.height + 1) * satWidth)
  for y in 0 ..< map.height:
    var rowWalls = 0'i32
    let sourceRow = y * map.width
    let satRow = (y + 1) * satWidth
    let previousRow = y * satWidth
    for x in 0 ..< map.width:
      if not pixelWalkable[sourceRow + x]:
        inc rowWalls
      sat[satRow + x + 1] = sat[previousRow + x + 1] + rowWalls

  result = newSeq[bool](map.gridW * map.gridH)
  for gy in 0 ..< map.gridH:
    let
      cy = gy * NavCell + NavCell div 2
      y0 = cy - PlayerHalf
      y1 = cy + PlayerHalf
    if y0 < 0 or y1 >= map.height:
      continue
    for gx in 0 ..< map.gridW:
      let
        cx = gx * NavCell + NavCell div 2
        x0 = cx - PlayerHalf
        x1 = cx + PlayerHalf
      if x0 < 0 or x1 >= map.width:
        continue
      let walls = sat[(y1 + 1) * satWidth + x1 + 1] -
        sat[y0 * satWidth + x1 + 1] -
        sat[(y1 + 1) * satWidth + x0] +
        sat[y0 * satWidth + x0]
      result[map.gridIndex(gx, gy)] = walls == 0

proc coverCells(map: WorldMap): seq[bool] =
  result = newSeq[bool](map.walkable.len)
  for gy in 0 ..< map.gridH:
    for gx in 0 ..< map.gridW:
      let index = map.gridIndex(gx, gy)
      if not map.walkable[index]:
        continue
      for dy in -1 .. 1:
        for dx in -1 .. 1:
          if dx == 0 and dy == 0:
            continue
          let nx = gx + dx
          let ny = gy + dy
          if nx < 0 or nx >= map.gridW or ny < 0 or ny >= map.gridH or
              not map.walkable[map.gridIndex(nx, ny)]:
            result[index] = true

proc newWorldMap*(
  pixelWalkable: openArray[bool], width, height, teams: int,
  markers: Table[Team, EndzoneMarker]
): WorldMap =
  let started = getMonoTime()
  result = WorldMap(
    width: width, height: height, teams: teams,
    center: (width div 2, height div 2),
    wall: newSeq[bool](pixelWalkable.len),
    gridW: max(1, width div NavCell), gridH: max(1, height div NavCell))
  for index, walkable in pixelWalkable:
    result.wall[index] = not walkable
  for color, marker in markers:
    result.endzones[color] = Endzone(
      color: color, shape: marker.shape,
      x0: marker.x0, y0: marker.y0, x1: marker.x1, y1: marker.y1)
  let erodeStarted = getMonoTime()
  result.walkable = result.erode(pixelWalkable)
  result.erodeMs = elapsedMs(erodeStarted)
  let coverStarted = getMonoTime()
  result.cover = result.coverCells()
  result.coverMs = elapsedMs(coverStarted)
  result.baseInitMs = elapsedMs(started)

proc cellOf*(map: WorldMap, point: Point): Point =
  (clamp(point.x div NavCell, 0, map.gridW - 1),
   clamp(point.y div NavCell, 0, map.gridH - 1))

proc cellCenter*(cell: Point): Point =
  (cell.x * NavCell + NavCell div 2, cell.y * NavCell + NavCell div 2)

proc nearestWalkable*(map: WorldMap, cell: Point): Point =
  if map.walkable[map.gridIndex(cell.x, cell.y)]:
    return cell
  for ring in 1 ..< max(map.gridW, map.gridH):
    for dy in -ring .. ring:
      for dx in -ring .. ring:
        let nx = cell.x + dx
        let ny = cell.y + dy
        if nx >= 0 and nx < map.gridW and ny >= 0 and ny < map.gridH and
            map.walkable[map.gridIndex(nx, ny)]:
          return (nx, ny)
  cell

proc rayClear*(map: WorldMap, a, b: Point, step = 2.0): bool =
  let
    dx = b.x - a.x
    dy = b.y - a.y
    length = hypot(dx.float, dy.float)
    samples = max(int(length / step), 1)
  for index in 0 .. samples:
    let ratio = index.float / samples.float
    let x = clamp(pyRound(a.x.float + dx.float * ratio), 0, map.width - 1)
    let y = clamp(pyRound(a.y.float + dy.float * ratio), 0, map.height - 1)
    if map.wall[map.pixelIndex(x, y)]:
      return false
  true

proc walkableSegment*(map: WorldMap, start, goal: Point): bool =
  let
    dx = goal.x - start.x
    dy = goal.y - start.y
    samples = max(1, ceil(hypot(dx.float, dy.float) / 2.0).int)
  for index in 0 .. samples:
    let ratio = index.float / samples.float
    let x = pyRound(start.x.float + dx.float * ratio)
    let y = pyRound(start.y.float + dy.float * ratio)
    let x0 = x - PlayerHalf
    let x1 = x + PlayerHalf
    let y0 = y - PlayerHalf
    let y1 = y + PlayerHalf
    if x0 < 0 or y0 < 0 or x1 >= map.width or y1 >= map.height:
      return false
    for py in y0 .. y1:
      for px in x0 .. x1:
        if map.wall[map.pixelIndex(px, py)]:
          return false
  true

proc reverseNeighborIndex(dx, dy: int): int =
  for index, delta in Neighbors:
    if delta.x == -dx and delta.y == -dy:
      return index

proc dijkstra(map: WorldMap, goalCell: Point): RouteFields =
  let goal = map.nearestWalkable(goalCell)
  result.distances = newSeq[float](map.walkable.len)
  result.hops = newSeq[uint8](map.walkable.len)
  for value in result.distances.mitems:
    value = Inf
  result.distances[map.gridIndex(goal.x, goal.y)] = 0.0
  var queue = initHeapQueue[QueueNode]()
  queue.push((0.0, goal.x, goal.y))
  while queue.len > 0:
    let current = queue.pop()
    if current.distance > result.distances[map.gridIndex(current.x, current.y)]:
      continue
    for neighborIndex, delta in Neighbors:
      let nx = current.x + delta.x
      let ny = current.y + delta.y
      if nx < 0 or nx >= map.gridW or ny < 0 or ny >= map.gridH:
        continue
      let nextIndex = map.gridIndex(nx, ny)
      if not map.walkable[nextIndex]:
        continue
      if delta.x != 0 and delta.y != 0 and
          (not map.walkable[map.gridIndex(nx, current.y)] or
           not map.walkable[map.gridIndex(current.x, ny)]):
        continue
      let nextDistance = current.distance +
        (if delta.x != 0 and delta.y != 0: Sqrt2 else: 1.0)
      if nextDistance < result.distances[nextIndex]:
        result.distances[nextIndex] = nextDistance
        result.hops[nextIndex] = uint8(1 + reverseNeighborIndex(delta.x, delta.y))
        queue.push((nextDistance, nx, ny))

proc goalKey(map: WorldMap, goal: Point): int =
  let cell = map.cellOf(goal)
  map.gridIndex(cell.x, cell.y)

proc fieldsFor(map: WorldMap, goal: Point): RouteFields =
  let key = map.goalKey(goal)
  if not map.fields.hasKey(key):
    let started = getMonoTime()
    map.fields[key] = map.dijkstra((key mod map.gridW, key div map.gridW))
    map.dijkstraMs.add(elapsedMs(started))
  map.fields[key]

proc flowWaypoint*(map: WorldMap, goal, selfXy: Point): Point =
  let fields = map.fieldsFor(goal)
  let current = map.nearestWalkable(map.cellOf(selfXy))
  let code = fields.hops[map.gridIndex(current.x, current.y)].int
  if code == 0:
    return selfXy
  let delta = Neighbors[code - 1]
  cellCenter((current.x + delta.x, current.y + delta.y))

proc routeDistance*(map: WorldMap, start, goal: Point): float =
  let fields = map.fieldsFor(goal)
  let cell = map.nearestWalkable(map.cellOf(start))
  fields.distances[map.gridIndex(cell.x, cell.y)] * NavCell.float

proc nearestCover*(map: WorldMap, point: Point, maxCells = 6): Option[Point] =
  let cell = map.cellOf(point)
  if map.cover[map.gridIndex(cell.x, cell.y)]:
    return some(cellCenter(cell))
  for ring in 1 .. maxCells:
    var
      found = false
      best: Point
      bestDistance = high(int)
    for dy in -ring .. ring:
      for dx in -ring .. ring:
        let nx = cell.x + dx
        let ny = cell.y + dy
        if nx >= 0 and nx < map.gridW and ny >= 0 and ny < map.gridH and
            map.cover[map.gridIndex(nx, ny)]:
          let d = dx * dx + dy * dy
          if d < bestDistance:
            bestDistance = d
            best = cellCenter((nx, ny))
            found = true
    if found:
      return some(best)

proc homeCenter*(map: WorldMap, color: Team): Point =
  if map.endzones.hasKey(color): map.endzones[color].center else: map.center

proc pedestal*(map: WorldMap, color: Team): Point =
  if map.pedestals.hasKey(color): map.pedestals[color] else: map.homeCenter(color)

proc capturePoint*(map: WorldMap, color: Team): Point =
  if not map.endzones.hasKey(color):
    return map.center
  let cell = map.nearestWalkable(map.cellOf(map.endzones[color].center))
  cellCenter(cell)

proc axisPoint(map: WorldMap, color: Team, fraction: float): Point =
  let home = map.homeCenter(color)
  (int(home.x.float + (map.center.x - home.x).float * fraction),
   int(home.y.float + (map.center.y - home.y).float * fraction))

proc chokePoint*(map: WorldMap, color: Team): Point =
  let base = map.axisPoint(color, ChokeFraction)
  let cover = map.nearestCover(base, 10)
  if cover.isSome: cover.get else: base

proc rallyPoint*(map: WorldMap, color: Team): Point =
  map.axisPoint(color, RallyFraction)

proc pastRally*(map: WorldMap, color: Team, point: Point): bool =
  let home = map.homeCenter(color)
  let ax = map.center.x - home.x
  let ay = map.center.y - home.y
  let normSquared = ax * ax + ay * ay
  if normSquared == 0:
    return false
  let projection = ((point.x - home.x) * ax + (point.y - home.y) * ay).float /
    normSquared.float
  projection > RallyFraction

proc homeStep*(map: WorldMap, color: Team, pos: Point, step: int): Point =
  let home = map.homeCenter(color)
  let dx = home.x - pos.x
  let dy = home.y - pos.y
  let distance = hypot(dx.float, dy.float)
  if distance < 1.0:
    return pos
  (clamp(int(pos.x.float + dx.float / distance * step.float), 12, map.width - 13),
   clamp(int(pos.y.float + dy.float / distance * step.float), 12, map.height - 13))

proc insideBase*(map: WorldMap, color: Team, point: Point, margin = 80): bool =
  if not map.endzones.hasKey(color):
    return false
  let zone = map.endzones[color]
  point.x >= zone.x0 - margin and point.x <= zone.x1 + margin and
    point.y >= zone.y0 - margin and point.y <= zone.y1 + margin

proc spawnAim*(map: WorldMap, color: Team): int =
  let home = map.homeCenter(color)
  if home == map.center:
    return 0
  let angle = arctan2(-(map.center.y - home.y).float, (map.center.x - home.x).float)
  floorMod(pyRound(angle / (2.0 * PI) * AimBradsTurn.float), AimBradsTurn)

proc grenadeMaxRange*(map: WorldMap): int = map.width div 5

proc signature*(map: WorldMap): tuple[width, height, teams: int] =
  (map.width, map.height, map.teams)
