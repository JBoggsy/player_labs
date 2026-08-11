## Episode-scoped terrain, route fields, and derived tactical geometry.

import std/[algorithm, heapqueue, math, monotimes, options, tables, times]
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

  CachedRouteField* = tuple[
    goalCell: Point,
    distances: seq[float],
    hops: seq[uint8]]

  PostCandidate* = object
    pos*, duck*: Point
    score*, sightline*, corridor*, duckContrast*: float
    rayEnds*: seq[Point]

  PostFront* = object
    team*, opponent*: Team
    candidates*, posts*: seq[PostCandidate]

  WorldMap* = ref object
    width*, height*, teams*: int
    center*: Point
    wall*: seq[bool]
    clearance*: seq[uint8]
    gridW*, gridH*: int
    walkable*: seq[bool]
    cover*: seq[bool]
    postFronts*: seq[PostFront]
    endzones*: Table[Team, Endzone]
    pedestals*: Table[Team, Point]
    fields: Table[int, RouteFields]
    baseInitMs*, clearanceMs*, coverMs*, postMs*: float
    dijkstraMs*: seq[float]

proc fieldsFor(map: WorldMap, goal: Point): RouteFields
proc homeCenter*(map: WorldMap, color: Team): Point
proc pedestal*(map: WorldMap, color: Team): Point
proc capturePoint*(map: WorldMap, color: Team): Point
proc generatePosts(map: WorldMap, team: Team): seq[PostFront]

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

proc buildClearance(map: WorldMap, pixelWalkable: openArray[bool]): seq[uint8] =
  ## Exact L-infinity (Chebyshev) distance to the nearest wall pixel, with
  ## out-of-bounds counting as wall, clamped at 255. Two chamfer passes; for
  ## the L-inf metric the 8-neighbor unit-weight chamfer is exact, not an
  ## approximation. The engine's canOccupy footprint is a square of
  ## half-extent PlayerHalf (sim_state.nim), so `clearance[p] > PlayerHalf`
  ## reproduces it bit-for-bit.
  let
    width = map.width
    height = map.height
  result = newSeq[uint8](width * height)
  template neighbor(nx, ny: int): int =
    # Out-of-range reads count as wall (distance 0).
    if nx < 0 or nx >= width or ny < 0 or ny >= height: 0
    else: result[ny * width + nx].int
  for y in 0 ..< height:
    for x in 0 ..< width:
      if not pixelWalkable[y * width + x]:
        continue
      var best = min(255, min(
        min(neighbor(x - 1, y), neighbor(x, y - 1)),
        min(neighbor(x - 1, y - 1), neighbor(x + 1, y - 1))) + 1)
      result[y * width + x] = uint8(best)
  for y in countdown(height - 1, 0):
    for x in countdown(width - 1, 0):
      if not pixelWalkable[y * width + x]:
        continue
      let index = y * width + x
      var best = min(result[index].int, min(
        min(neighbor(x + 1, y), neighbor(x, y + 1)),
        min(neighbor(x + 1, y + 1), neighbor(x - 1, y + 1))) + 1)
      result[index] = uint8(best)

proc deriveWalkableGrid(map: WorldMap): seq[bool] =
  ## Cell-center footprint test read straight off the clearance field.
  ## Matches the previous summed-area erosion bit-for-bit: a cell is walkable
  ## when the footprint centered on its center pixel fits on walkable floor
  ## (cells whose footprint would leave the map fail via clearance, since
  ## out-of-bounds counts as wall).
  result = newSeq[bool](map.gridW * map.gridH)
  for gy in 0 ..< map.gridH:
    let cy = gy * NavCell + NavCell div 2
    for gx in 0 ..< map.gridW:
      let cx = gx * NavCell + NavCell div 2
      result[map.gridIndex(gx, gy)] =
        map.clearance[map.pixelIndex(cx, cy)].int > PlayerHalf

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
  markers: Table[Team, EndzoneMarker], team: Team
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
  let clearanceStarted = getMonoTime()
  result.clearance = result.buildClearance(pixelWalkable)
  result.walkable = result.deriveWalkableGrid()
  result.clearanceMs = elapsedMs(clearanceStarted)
  let coverStarted = getMonoTime()
  result.cover = result.coverCells()
  result.coverMs = elapsedMs(coverStarted)
  result.baseInitMs = elapsedMs(started)
  for index in 0 ..< result.teams:
    discard result.fieldsFor(result.homeCenter(Team(index)))
  let postStarted = getMonoTime()
  result.postFronts = result.generatePosts(team)
  result.postMs = elapsedMs(postStarted)

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

proc canStand*(map: WorldMap, point: Point): bool =
  ## Engine-exact point walkability: the square footprint of half-extent
  ## PlayerHalf fits entirely on walkable floor at `point`.
  point.x >= 0 and point.x < map.width and
    point.y >= 0 and point.y < map.height and
    map.clearance[map.pixelIndex(point.x, point.y)].int > PlayerHalf

proc segmentClear*(map: WorldMap, start, goal: Point): bool =
  ## True when the footprint stays on walkable floor at every pixel the
  ## start->goal segment passes through. Integer supercover DDA (the same
  ## traversal the old grid-level walkableNavSegment used, at pixel
  ## resolution): at an exact diagonal crossing both adjacent pixels are
  ## checked, so a blocked corner cannot be cut. One clearance read per
  ## visited pixel via canStand.
  if not map.canStand(start):
    return false
  let
    dx = goal.x - start.x
    dy = goal.y - start.y
    nx = abs(dx)
    ny = abs(dy)
    stepX = cmp(dx, 0)
    stepY = cmp(dy, 0)
  var
    x = start.x
    y = start.y
    ix = 0
    iy = 0
  while ix < nx or iy < ny:
    let decision = (1 + 2 * ix) * ny - (1 + 2 * iy) * nx
    if decision == 0:
      if not map.canStand((x + stepX, y)) or not map.canStand((x, y + stepY)):
        return false
      x += stepX
      y += stepY
      inc ix
      inc iy
    elif decision < 0:
      x += stepX
      inc ix
    else:
      y += stepY
      inc iy
    if not map.canStand((x, y)):
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

proc cachedRouteFields*(map: WorldMap): seq[CachedRouteField] =
  ## Read-only snapshots of the lazy Dijkstra cache for diagnostics.
  var keys: seq[int]
  for key in map.fields.keys:
    keys.add(key)
  keys.sort()
  for key in keys:
    let fields = map.fields[key]
    result.add((
      goalCell: (key mod map.gridW, key div map.gridW),
      distances: fields.distances,
      hops: fields.hops))

proc distanceAt(map: WorldMap, point, goal: Point): float =
  let
    fields = map.fieldsFor(goal)
    cell = map.nearestWalkable(map.cellOf(point))
  fields.distances[map.gridIndex(cell.x, cell.y)] * NavCell.float

proc forwardRayEnds(map: WorldMap, point, goal: Point): tuple[score: float, ends: seq[Point]] =
  let waypoint = map.flowWaypoint(goal, point)
  var
    dx = waypoint.x - point.x
    dy = waypoint.y - point.y
  if dx == 0 and dy == 0:
    dx = goal.x - point.x
    dy = goal.y - point.y
  let
    centerAngle = arctan2(dy.float, dx.float)
    rayCount = max(3, PostRayCount or 1)
    halfArc = PostRayHalfArcDeg * PI / 180.0
  for rayIndex in 0 ..< rayCount:
    let
      fraction = rayIndex.float / (rayCount - 1).float
      angle = centerAngle - halfArc + 2.0 * halfArc * fraction
      rayDx = cos(angle)
      rayDy = sin(angle)
    var last = point
    var distance = NavCell
    while distance <= PostGunRangePx:
      let sample: Point = (
        pyRound(point.x.float + rayDx * distance.float),
        pyRound(point.y.float + rayDy * distance.float))
      if sample.x < 0 or sample.x >= map.width or
          sample.y < 0 or sample.y >= map.height or
          map.wall[map.pixelIndex(sample.x, sample.y)]:
        break
      last = sample
      distance += NavCell
    result.ends.add(last)
    result.score += min(hypot((last.x - point.x).float,
      (last.y - point.y).float) / PostGunRangePx.float, 1.0)
  result.score /= rayCount.float

proc duckFor(map: WorldMap, candidate: PostCandidate): tuple[pos: Point, contrast: float] =
  let cell = map.cellOf(candidate.pos)
  var threatEnds: seq[Point]
  if candidate.rayEnds.len > 0:
    for index in [0, candidate.rayEnds.len div 2, candidate.rayEnds.high]:
      if candidate.rayEnds[index] notin threatEnds:
        threatEnds.add(candidate.rayEnds[index])
  result.pos = candidate.pos
  var bestUtility = 0.0
  for dy in -PostDuckSearchCells .. PostDuckSearchCells:
    for dx in -PostDuckSearchCells .. PostDuckSearchCells:
      if dx == 0 and dy == 0:
        continue
      if dx != 0 and dy != 0 and abs(dx) != abs(dy):
        continue
      let hideCell: Point = (cell.x + dx, cell.y + dy)
      if hideCell.x < 0 or hideCell.x >= map.gridW or
          hideCell.y < 0 or hideCell.y >= map.gridH or
          not map.walkable[map.gridIndex(hideCell.x, hideCell.y)]:
        continue
      let hide = cellCenter(hideCell)
      if not map.segmentClear(candidate.pos, hide):
        continue
      var blocked = 0
      for endpoint in threatEnds:
        if endpoint != candidate.pos and
            not map.rayClear(hide, endpoint, NavCell.float):
          inc blocked
      let
        contrast = blocked.float / max(threatEnds.len, 1).float
        travel = hypot(dx.float, dy.float) /
          max(PostDuckSearchCells.float * sqrt(2.0), 1.0)
        utility = contrast - 0.15 * travel
      if utility > bestUtility:
        bestUtility = utility
        result = (hide, contrast)

proc generateFront(map: WorldMap, team, opponent: Team): PostFront =
  result.team = team
  result.opponent = opponent
  let
    home = map.homeCenter(team)
    enemyHome = map.homeCenter(opponent)
    direct = map.distanceAt(enemyHome, home)
    stride = max(PostCandidateStrideCells, 1)
  var buckets = newSeq[seq[PostCandidate]](PostProgressBuckets)
  if classify(direct) == fcInf:
    return
  for gy in 0 ..< map.gridH:
    for gx in 0 ..< map.gridW:
      let index = map.gridIndex(gx, gy)
      if not map.cover[index] or (gx + gy) mod stride != 0:
        continue
      let
        point = cellCenter((gx, gy))
        fromHome = map.distanceAt(point, home)
        toEnemy = map.distanceAt(point, enemyHome)
        via = fromHome + toEnemy
        detour = max(0.0, via - direct)
      if classify(via) == fcInf or detour > PostCorridorPx.float * 3.0:
        continue
      let corridor = exp(-detour / max(PostCorridorPx.float, 1.0))
      let bucket = clamp(int(fromHome / direct * PostProgressBuckets.float),
        0, PostProgressBuckets - 1)
      buckets[bucket].add(PostCandidate(
        pos: point, duck: point,
        score: corridor, corridor: corridor))
  for bucket in buckets.mitems:
    bucket.sort(proc(a, b: PostCandidate): int = cmp(b.corridor, a.corridor))
    var retained: seq[PostCandidate]
    for candidate in bucket:
      var separated = true
      for previous in retained:
        if hypot((candidate.pos.x - previous.pos.x).float,
            (candidate.pos.y - previous.pos.y).float) <
            PostRayCandidateSeparationPx.float:
          separated = false
          break
      if separated:
        retained.add(candidate)
        result.candidates.add(candidate)
        if retained.len >= PostRayCandidatesPerBucket:
          break
  for candidate in result.candidates.mitems:
    let rays = map.forwardRayEnds(candidate.pos, enemyHome)
    candidate.rayEnds = rays.ends
    candidate.sightline = rays.score
    candidate.score = 0.8 * candidate.sightline + 0.2 * candidate.corridor
  result.candidates.sort(proc(a, b: PostCandidate): int = cmp(b.score, a.score))
  if result.candidates.len > PostShortlistCount:
    result.candidates.setLen(PostShortlistCount)
  for candidate in result.candidates.mitems:
    let duck = map.duckFor(candidate)
    candidate.duck = duck.pos
    candidate.duckContrast = duck.contrast
    candidate.score = 0.65 * candidate.sightline +
      0.20 * candidate.corridor + 0.15 * candidate.duckContrast
  result.candidates.sort(proc(a, b: PostCandidate): int = cmp(b.score, a.score))
  for candidate in result.candidates:
    if candidate.duck == candidate.pos:
      continue
    var separated = true
    for selected in result.posts:
      if hypot((candidate.pos.x - selected.pos.x).float,
          (candidate.pos.y - selected.pos.y).float) < PostSeparationPx.float:
        separated = false
        break
    if separated:
      result.posts.add(candidate)
      if result.posts.len >= PostCount:
        break

proc generatePosts(map: WorldMap, team: Team): seq[PostFront] =
  for opponentIndex in 0 ..< map.teams:
    if Team(opponentIndex) != team:
      result.add(map.generateFront(team, Team(opponentIndex)))

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

proc spawnCoverPoint*(map: WorldMap, color: Team, seat, seats: int): Point =
  ## Assign distinct wall-adjacent cells inside the exact spawn endzone,
  ## ordered outward from the heart. Fall back to the capture point only when
  ## generated terrain offers no covered cell in the box.
  if not map.endzones.hasKey(color):
    return map.capturePoint(color)
  let
    zone = map.endzones[color]
    heart = map.pedestal(color)
  var candidates: seq[tuple[pos: Point, distance: int]]
  for gy in 0 ..< map.gridH:
    for gx in 0 ..< map.gridW:
      let index = gy * map.gridW + gx
      if not map.cover[index]:
        continue
      let point = cellCenter((gx, gy))
      if zone.contains(point):
        let dx = point.x - heart.x
        let dy = point.y - heart.y
        candidates.add((point, dx * dx + dy * dy))
  candidates.sort(proc(a, b: tuple[pos: Point, distance: int]): int =
    cmp(a.distance, b.distance))
  var selected: seq[Point]
  for candidate in candidates:
    var separated = true
    for previous in selected:
      if hypot((candidate.pos.x - previous.x).float,
          (candidate.pos.y - previous.y).float) < 32.0:
        separated = false
        break
    if separated:
      selected.add(candidate.pos)
      if selected.len >= max(seats, 1):
        break
  if selected.len == 0:
    return map.capturePoint(color)
  selected[floorMod(seat, selected.len)]

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

proc insideEndzone*(map: WorldMap, color: Team, point: Point): bool =
  map.endzones.hasKey(color) and map.endzones[color].contains(point)

proc spawnAim*(map: WorldMap, color: Team): int =
  let home = map.homeCenter(color)
  if home == map.center:
    return 0
  let angle = arctan2(-(map.center.y - home.y).float, (map.center.x - home.x).float)
  floorMod(pyRound(angle / (2.0 * PI) * AimBradsTurn.float), AimBradsTurn)

proc grenadeMaxRange*(map: WorldMap): int = map.width div 5

proc signature*(map: WorldMap): tuple[width, height, teams: int] =
  (map.width, map.height, map.teams)
