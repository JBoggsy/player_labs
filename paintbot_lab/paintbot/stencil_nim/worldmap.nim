## Episode-scoped terrain, route fields, and derived tactical geometry.

import std/[algorithm, heapqueue, math, monotimes, options, sets, tables, times]
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

  Choke* = object
    pos*: Point              # widest pixel of the gate (watershed saddle)
    clearance*: int          # L-inf half-width at the gate
    roomA*, roomB*: int      # indices into WorldMap.rooms

  Room* = object
    peak*: Point             # clearance local maximum: the room's PoI point
    peakClearance*: int
    area*: int               # standable pixels
    component*: int
    chokes*: seq[int]        # indices into WorldMap.chokes

  TopologyJournal* = ref object
    ## Optional watershed process recorder for the offline visualizer
    ## (tools/topology_debug.nim). nil in production play: the flood itself
    ## is reconstructable from rawLabels + clearance (a pixel is labeled
    ## exactly when the flood reaches its own clearance level), so only the
    ## pre-merge labels and the decision events need recording.
    rawLabels*: seq[int32]
    seeds*: seq[Point]
    contacts*: seq[tuple[pos: Point, clearance: int, a, b: int]]
    merges*: seq[tuple[a, b: int, saddle: int, depth: int, ratio: float,
      merged: bool]]

  WorldMap* = ref object
    width*, height*, teams*: int
    center*: Point
    wall*: seq[bool]
    clearance*: seq[uint8]
    component*: seq[uint16]  # per pixel; 0 = not standable (4-connected CCL)
    componentCount*: int
    roomLabel*: seq[uint16]  # per pixel; 0 = not standable (post-merge rooms)
    rooms*: seq[Room]
    chokes*: seq[Choke]
    gridW*, gridH*: int
    walkable*: seq[bool]
    cover*: seq[bool]        # directional cover exists (coverDirs != 0)
    coverDirs*: seq[uint16]  # per cell: N-sector blocked-from bitmask
    postFronts*: seq[PostFront]
    endzones*: Table[Team, Endzone]
    pedestals*: Table[Team, Point]
    fields: Table[int, RouteFields]
    gates: Table[Team, Point]  # lazy defenseGate cache (chokes are static)
    baseInitMs*, clearanceMs*, componentMs*, topologyMs*, coverMs*,
      postMs*: float
    dijkstraMs*: seq[float]

proc fieldsFor(map: WorldMap, goal: Point): lent RouteFields
proc homeCenter*(map: WorldMap, color: Team): Point
proc pedestal*(map: WorldMap, color: Team): Point
proc capturePoint*(map: WorldMap, color: Team): Point
proc generatePosts(map: WorldMap, team: Team): seq[PostFront]
proc buildComponents(map: WorldMap)
proc buildTopology*(map: WorldMap, journal: TopologyJournal = nil)
proc buildCoverDirs(map: WorldMap)

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

proc newWorldMap*(
  pixelWalkable: openArray[bool], width, height, teams: int,
  markers: Table[Team, EndzoneMarker], team: Team,
  journal: TopologyJournal = nil
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
  let componentStarted = getMonoTime()
  result.buildComponents()
  result.componentMs = elapsedMs(componentStarted)
  let topologyStarted = getMonoTime()
  result.buildTopology(journal)
  result.topologyMs = elapsedMs(topologyStarted)
  let coverStarted = getMonoTime()
  result.buildCoverDirs()
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

proc isWall*(map: WorldMap, point: Point): bool =
  ## Out-of-bounds is blocking, matching the clearance field's map-edge rule.
  point.x < 0 or point.x >= map.width or point.y < 0 or point.y >= map.height or
    map.wall[map.pixelIndex(point.x, point.y)]

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

proc nudgeClear*(map: WorldMap, start, goal: Point): bool =
  ## Walkability for short micro nudges (sidesteps, stances, bias waypoints,
  ## separation steps): canStand sampled every 2px — bit-identical acceptance
  ## to the pre-clearance walkableSegment (2px samples x full footprint scan)
  ## at ~1/169th the reads. Deliberately NOT the exact supercover test:
  ## micro nudges ride the engine's forgiving wall-slide, and validating them
  ## at engine fidelity rejects peeks the engine executes fine — the hosted
  ## v60-vs-v59 A/B measured +3.7pp duck time and a win deficit from exactly
  ## that. Use segmentClear for real route segments.
  let
    dx = goal.x - start.x
    dy = goal.y - start.y
    samples = max(1, ceil(hypot(dx.float, dy.float) / 2.0).int)
  for index in 0 .. samples:
    let ratio = index.float / samples.float
    let point: Point = (
      pyRound(start.x.float + dx.float * ratio),
      pyRound(start.y.float + dy.float * ratio))
    if not map.canStand(point):
      return false
  true

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

const Orth = [(-1, 0), (1, 0), (0, -1), (0, 1)]

template standableAt(map: WorldMap, index: int): bool =
  map.clearance[index].int > PlayerHalf

proc buildComponents(map: WorldMap) =
  ## 4-connected components of the standable-pixel set (canStand), one label
  ## per pixel, 0 = not standable. 4-connectivity is engine-exact: the engine
  ## integrates movement per axis (Y then X) and wall-slide composes axis
  ## steps, so a diagonal move needs a standable orthogonal intermediate —
  ## 8-connectivity would over-claim reachability at diagonal pinches.
  map.component = newSeq[uint16](map.width * map.height)
  map.componentCount = 0
  var queue: seq[int]
  for start in 0 ..< map.component.len:
    if map.component[start] != 0 or not map.standableAt(start):
      continue
    # Label cap: unreachable on generator-validated maps (components are few
    # and fat); if ever exceeded, remaining components share the last label.
    if map.componentCount < high(uint16).int:
      inc map.componentCount
    let label = uint16(map.componentCount)
    map.component[start] = label
    queue.setLen(0)
    queue.add(start)
    var head = 0
    while head < queue.len:
      let index = queue[head]
      inc head
      let x = index mod map.width
      let y = index div map.width
      for delta in Orth:
        let nx = x + delta[0]
        let ny = y + delta[1]
        if nx < 0 or nx >= map.width or ny < 0 or ny >= map.height:
          continue
        let neighbor = ny * map.width + nx
        if map.component[neighbor] == 0 and map.standableAt(neighbor):
          map.component[neighbor] = label
          queue.add(neighbor)

proc componentOf*(map: WorldMap, p: Point): int =
  ## 0 when `p` is not standable; otherwise the 4-connected component label.
  if map.canStand(p): map.component[map.pixelIndex(p.x, p.y)].int else: 0

proc sameComponent*(map: WorldMap, a, b: Point): bool =
  ## The O(1) reachability query behind the Layer 4 goal contract.
  let ca = map.componentOf(a)
  ca != 0 and ca == map.componentOf(b)

proc nearestReachable*(
  map: WorldMap, point, fromPoint: Point, maxRadiusPx = 32 * NavCell
): Option[Point] =
  ## Resolve a prospective goal before it becomes an Intent. Search order does
  ## not decide the winner: squared distance and then row-major pixel index do,
  ## so the bounded ring scan is deterministic and directionally unbiased.
  let component = map.componentOf(fromPoint)
  if component == 0 or maxRadiusPx < 0:
    return none(Point)
  var
    best = none(Point)
    bestDistance = high(int64)
    bestIndex = high(int)
  let radiusSquared = maxRadiusPx.int64 * maxRadiusPx.int64
  for ring in 0 .. maxRadiusPx:
    if best.isSome and ring.int64 * ring.int64 > bestDistance:
      break
    for y in max(0, point.y - ring) .. min(map.height - 1, point.y + ring):
      for x in max(0, point.x - ring) .. min(map.width - 1, point.x + ring):
        if max(abs(x - point.x), abs(y - point.y)) != ring:
          continue
        let
          candidate: Point = (x, y)
          dx = (x - point.x).int64
          dy = (y - point.y).int64
          candidateDistance = dx * dx + dy * dy
          candidateIndex = y * map.width + x
        if candidateDistance > radiusSquared or
            candidateDistance > bestDistance or not map.canStand(candidate) or
            map.component[candidateIndex].int != component:
          continue
        if candidateDistance < bestDistance or candidateIndex < bestIndex:
          best = some(candidate)
          bestDistance = candidateDistance
          bestIndex = candidateIndex
  best

proc buildTopology*(map: WorldMap, journal: TopologyJournal = nil) =
  ## Rooms and chokepoints via priority-flood watershed on the clearance
  ## field: regions grow from clearance-maxima plateaus in decreasing
  ## clearance order (256-bucket queue — exact O(pixels)); the first contact
  ## between two regions is their gate (the widest point of the narrowest
  ## crossing) and its clearance is the gate's L-inf half-width; shallow
  ## saddles are merged away by persistence (depth + relative-ratio tests).
  ## Every standable pixel is labeled exactly when the flood reaches its own
  ## clearance level — the property the offline visualizer relies on.
  let
    width = map.width
    pixels = width * map.height
  var
    raw = newSeq[int32](pixels)
    seeds: seq[Point]
    peaks: seq[int]
    areas: seq[int]
  # --- seeds: local-maxima plateaus (4-connected, constant clearance) ---
  var visited = newSeq[bool](pixels)
  var plateau: seq[int]
  for start in 0 ..< pixels:
    if visited[start] or not map.standableAt(start):
      continue
    let level = map.clearance[start].int
    plateau.setLen(0)
    plateau.add(start)
    visited[start] = true
    var head = 0
    var isMax = true
    while head < plateau.len:
      let index = plateau[head]
      inc head
      let x = index mod width
      let y = index div width
      for delta in Orth:
        let nx = x + delta[0]
        let ny = y + delta[1]
        if nx < 0 or nx >= width or ny < 0 or ny >= map.height:
          continue
        let neighbor = ny * width + nx
        if not map.standableAt(neighbor):
          continue
        let c = map.clearance[neighbor].int
        if c > level:
          isMax = false
        elif c == level and not visited[neighbor]:
          visited[neighbor] = true
          plateau.add(neighbor)
    if isMax:
      seeds.add((plateau[0] mod width, plateau[0] div width))
      peaks.add(level)
      areas.add(plateau.len)
      let label = int32(seeds.len)
      for index in plateau:
        raw[index] = label
  # --- flood: descending clearance, FIFO within a level ---
  var buckets: array[256, seq[int32]]
  var queued = newSeq[bool](pixels)
  var contacts: seq[tuple[pos: Point, clearance: int, a, b: int]]
  var pairContacts = initTable[(int, int), seq[Point]]()
  template pushNeighbors(index: int) =
    let x = index mod width
    let y = index div width
    for delta in Orth:
      let nx = x + delta[0]
      let ny = y + delta[1]
      if nx >= 0 and nx < width and ny >= 0 and ny < map.height:
        let neighbor = ny * width + nx
        if raw[neighbor] == 0 and not queued[neighbor] and
            map.standableAt(neighbor):
          queued[neighbor] = true
          buckets[map.clearance[neighbor].int].add(int32(neighbor))
  for index in 0 ..< pixels:
    if raw[index] != 0:
      pushNeighbors(index)
  for level in countdown(255, PlayerHalf + 1):
    var head = 0
    while head < buckets[level].len:
      let index = buckets[level][head].int
      inc head
      if raw[index] != 0:
        continue
      let x = index mod width
      let y = index div width
      var labels: array[4, int32]
      var labelCount = 0
      for delta in Orth:
        let nx = x + delta[0]
        let ny = y + delta[1]
        if nx < 0 or nx >= width or ny < 0 or ny >= map.height:
          continue
        let value = raw[ny * width + nx]
        if value == 0:
          continue
        var known = false
        for existing in 0 ..< labelCount:
          if labels[existing] == value:
            known = true
            break
        if not known:
          labels[labelCount] = value
          inc labelCount
      if labelCount == 0:
        continue
      var assigned = labels[0]
      for existing in 1 ..< labelCount:
        assigned = min(assigned, labels[existing])
      raw[index] = assigned
      inc areas[assigned - 1]
      if labelCount >= 2:
        for first in 0 ..< labelCount:
          for second in first + 1 ..< labelCount:
            let pair = (min(labels[first], labels[second]).int,
              max(labels[first], labels[second]).int)
            var nearExisting = false
            if pairContacts.hasKey(pair):
              for previous in pairContacts[pair]:
                if max(abs(previous.x - x), abs(previous.y - y)) <
                    GateSeparationPx:
                  nearExisting = true
                  break
            if not nearExisting:
              pairContacts.mgetOrPut(pair, @[]).add((x, y))
              contacts.add(((x, y), level, pair[0], pair[1]))
      pushNeighbors(index)
    buckets[level].setLen(0)
  # --- persistence merge (contacts arrive in descending saddle order) ---
  var parent = newSeq[int](seeds.len)
  for index in 0 ..< parent.len:
    parent[index] = index
  proc findRoot(parent: var seq[int], node: int): int =
    result = node
    while parent[result] != result:
      parent[result] = parent[parent[result]]
      result = parent[result]
  if journal != nil:
    journal.rawLabels = raw
    journal.seeds = seeds
    journal.contacts = contacts
  for contact in contacts:
    let ra = findRoot(parent, contact.a - 1)
    let rb = findRoot(parent, contact.b - 1)
    if ra == rb:
      continue
    let minPeak = min(peaks[ra], peaks[rb])
    let depth = minPeak - contact.clearance
    let ratio = contact.clearance.float / max(minPeak, 1).float
    let merged = depth < TopologyMergeDepthPx or ratio >= TopologyMergeRatio
    if journal != nil:
      journal.merges.add((contact.a, contact.b, contact.clearance, depth,
        ratio, merged))
    if merged:
      var winner = ra
      var loser = rb
      if peaks[rb] > peaks[ra] or (peaks[rb] == peaks[ra] and rb < ra):
        winner = rb
        loser = ra
      parent[loser] = winner
      areas[winner] += areas[loser]
  # --- compact surviving rooms and gates ---
  map.rooms.setLen(0)
  map.chokes.setLen(0)
  var final = newSeq[int](seeds.len)
  for index in 0 ..< final.len:
    final[index] = -1
  for label in 0 ..< seeds.len:
    let root = findRoot(parent, label)
    if final[root] < 0:
      final[root] = map.rooms.len
      map.rooms.add(Room(
        peak: seeds[root], peakClearance: peaks[root], area: areas[root],
        component: map.component[seeds[root].y * width + seeds[root].x].int))
    final[label] = final[root]
  for contact in contacts:
    let ra = final[findRoot(parent, contact.a - 1)]
    let rb = final[findRoot(parent, contact.b - 1)]
    if ra == rb:
      continue
    let pair = (min(ra, rb), max(ra, rb))
    var nearExisting = false
    for choke in map.chokes:
      if (min(choke.roomA, choke.roomB), max(choke.roomA, choke.roomB)) ==
          pair and
          max(abs(choke.pos.x - contact.pos.x),
            abs(choke.pos.y - contact.pos.y)) < GateSeparationPx:
        nearExisting = true
        break
    if not nearExisting:
      for room in [pair[0], pair[1]]:
        map.rooms[room].chokes.add(map.chokes.len)
      map.chokes.add(Choke(
        pos: contact.pos, clearance: contact.clearance,
        roomA: pair[0], roomB: pair[1]))
  map.roomLabel = newSeq[uint16](pixels)
  for index in 0 ..< pixels:
    if raw[index] != 0:
      map.roomLabel[index] = uint16(final[raw[index] - 1] + 1)

proc buildCoverDirs(map: WorldMap) =
  ## N-sector directional cover per walkable nav cell: bit k set iff a ray
  ## from the cell center at angle k*2pi/N hits a real, in-bounds wall pixel
  ## within CoverRayPx. Rays test the wall mask (shots are points, not
  ## footprints), and a ray that leaves the map does NOT count as blocked —
  ## no shooter can stand outside the map, so edge adjacency is not cover.
  let rayCount = clamp(CoverRays, 1, 16)
  map.coverDirs = newSeq[uint16](map.walkable.len)
  map.cover = newSeq[bool](map.walkable.len)
  for gy in 0 ..< map.gridH:
    for gx in 0 ..< map.gridW:
      let index = map.gridIndex(gx, gy)
      if not map.walkable[index]:
        continue
      let center = cellCenter((gx, gy))
      var mask: uint16 = 0
      for ray in 0 ..< rayCount:
        let angle = ray.float * 2.0 * PI / rayCount.float
        let dirX = cos(angle)
        let dirY = sin(angle)
        var distance = 2.0
        while distance <= CoverRayPx.float:
          let sx = pyRound(center.x.float + dirX * distance)
          let sy = pyRound(center.y.float + dirY * distance)
          if sx < 0 or sx >= map.width or sy < 0 or sy >= map.height:
            break
          if map.wall[map.pixelIndex(sx, sy)]:
            mask = mask or uint16(1 shl ray)
            break
          distance += 2.0
      map.coverDirs[index] = mask
      map.cover[index] = mask != 0

proc facingScore*(map: WorldMap, point: Point,
    threats: openArray[Point]): float =
  ## Situational cover facing: the fraction of believed threat positions the
  ## cell is covered FROM (bearing point->threat quantized to the cover-ray
  ## sectors, tested against the precomputed blocked-from bitmask). No
  ## threats -> neutral 0.5, so intel-free selection is unchanged.
  if threats.len == 0:
    return 0.5
  let rays = clamp(CoverRays, 1, 16)
  let cell = map.cellOf(point)
  let mask = map.coverDirs[map.gridIndex(cell.x, cell.y)]
  var covered = 0
  for threat in threats:
    let bearing = arctan2((threat.y - point.y).float, (threat.x - point.x).float)
    let sector = floorMod(pyRound(bearing / (2.0 * PI) * rays.float), rays)
    if (mask and uint16(1 shl sector)) != 0:
      inc covered
  covered.float / threats.len.float

proc selectRankedPost*(map: WorldMap, candidates: seq[PostCandidate],
    anchor: Point, rank: int,
    threats: openArray[Point]): Option[PostCandidate] =
  ## The squad post-selection core, extracted from squads.orderPost so the
  ## offline harness can run the exact production logic. Ranks candidates
  ## near `anchor` by score, travel, and situational facing against believed
  ## threats, then picks the rank-th survivor of the separation filter.
  var ranked: seq[tuple[post: PostCandidate, utility: float]]
  for candidate in candidates:
    let distance = hypot((candidate.pos.x - anchor.x).float,
      (candidate.pos.y - anchor.y).float)
    if distance <= SquadPostSearchPx.float:
      ranked.add((candidate,
        candidate.score - 0.25 * distance / max(SquadPostSearchPx.float, 1.0) +
        PostFacingWeight * (map.facingScore(candidate.pos, threats) - 0.5)))
  ranked.sort(proc(a, b: tuple[post: PostCandidate, utility: float]): int =
    cmp(b.utility, a.utility))
  var selected: seq[PostCandidate]
  for candidate in ranked:
    var separated = true
    for previous in selected:
      if hypot((candidate.post.pos.x - previous.pos.x).float,
          (candidate.post.pos.y - previous.pos.y).float) <
          SquadPostSeparationPx.float:
        separated = false
        break
    if separated:
      selected.add(candidate.post)
  if selected.len == 0:
    return none(PostCandidate)
  some(selected[min(rank, selected.high)])

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

proc fieldsFor(map: WorldMap, goal: Point): lent RouteFields =
  ## Returns a BORROW of the cached field. RouteFields carries two
  ## grid-sized seqs (~1.4 MB on giants); the previous by-value return
  ## memcpy'd them on every routeDistance/flowWaypoint/distanceAt call —
  ## measured as seconds per tick once the v64 wide pool multiplied the
  ## per-candidate routeDistance calls in squads.advancePoint.
  let key = map.goalKey(goal)
  if not map.fields.hasKey(key):
    let started = getMonoTime()
    map.fields[key] = map.dijkstra((key mod map.gridW, key div map.gridW))
    map.dijkstraMs.add(elapsedMs(started))
  map.fields[key]

proc flowWaypoint*(map: WorldMap, goal, selfXy: Point): Point =
  ## Oracle-derived geometry helper only. Movement must route through the
  ## weighted planner; forwardRayEnds uses this to orient static sightline rays.
  let current = map.nearestWalkable(map.cellOf(selfXy))
  let code = map.fieldsFor(goal).hops[map.gridIndex(current.x, current.y)].int
  if code == 0:
    return selfXy
  let delta = Neighbors[code - 1]
  cellCenter((current.x + delta.x, current.y + delta.y))

proc routeDistance*(map: WorldMap, start, goal: Point): float =
  let cell = map.nearestWalkable(map.cellOf(start))
  map.fieldsFor(goal).distances[map.gridIndex(cell.x, cell.y)] * NavCell.float

proc cachedFields(map: WorldMap, key: int): lent RouteFields =
  ## Caller must prove membership first; unlike fieldsFor this accessor cannot
  ## mint, and the lent result cannot copy either grid-sized sequence.
  map.fields[key]

proc peekRouteDistance*(map: WorldMap, point, goal: Point): Option[float] =
  ## Reads an existing goal field without invoking fieldsFor. A miss must stay
  ## a miss: arbitrary planner goals may never mint a full-grid Dijkstra field.
  let key = map.goalKey(goal)
  if not map.fields.hasKey(key):
    return none(float)
  let cell = map.nearestWalkable(map.cellOf(point))
  let distance = map.cachedFields(key).distances[map.gridIndex(cell.x, cell.y)]
  if classify(distance) == fcInf:
    return none(float)
  some(distance * NavCell.float)

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
  let cell = map.nearestWalkable(map.cellOf(point))
  map.fieldsFor(goal).distances[map.gridIndex(cell.x, cell.y)] * NavCell.float

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
      if not map.nudgeClear(candidate.pos, hide):
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
  # v63 candidate sourcing: cover-bearing cells in the vicinity of on-route
  # gates (chokes), instead of a full-grid cover scan — posts live at the
  # constrictions the route actually crosses. Facing is deliberately NOT
  # filtered here: threat direction is situational and scored at selection
  # time against believed enemy tracks (facingScore). The legacy full-grid
  # scan survives only as the per-bucket fallback for route stretches that
  # cross gateless open space.
  # The two route fields are hoisted ONCE per front and read by cell index:
  # per-cell distanceAt calls (table lookup + snap each) were the measured
  # dominant cost of the candidate stage on gate-dense giants.
  let homeFields = map.fieldsFor(home)
  let enemyFields = map.fieldsFor(enemyHome)
  template admitCell(gx, gy: int, cellIndex, onlyBucket: int) =
    # Callers guarantee map.walkable[cellIndex], so the field reads need no
    # nearestWalkable snap.
    let fromHome = homeFields.distances[cellIndex] * NavCell.float
    let toEnemy = enemyFields.distances[cellIndex] * NavCell.float
    let via = fromHome + toEnemy
    let detour = max(0.0, via - direct)
    if classify(via) != fcInf and detour <= PostCorridorPx.float * 3.0:
      let corridor = exp(-detour / max(PostCorridorPx.float, 1.0))
      let bucket = clamp(int(fromHome / direct * PostProgressBuckets.float),
        0, PostProgressBuckets - 1)
      if onlyBucket < 0 or bucket == onlyBucket:
        buckets[bucket].add(PostCandidate(
          pos: cellCenter((gx, gy)), duck: cellCenter((gx, gy)),
          score: corridor, corridor: corridor))
  var seenCells = initHashSet[int]()
  let vicinity = max(1, PostGateVicinityPx div NavCell)
  for choke in map.chokes:
    let gateFromHome = map.distanceAt(choke.pos, home)
    let gateToEnemy = map.distanceAt(choke.pos, enemyHome)
    if classify(gateFromHome) == fcInf or classify(gateToEnemy) == fcInf:
      continue
    if gateFromHome + gateToEnemy - direct > PostCorridorPx.float * 3.0:
      continue
    let gateCell = map.cellOf(choke.pos)
    for dy in -vicinity .. vicinity:
      for dx in -vicinity .. vicinity:
        let gx = gateCell.x + dx
        let gy = gateCell.y + dy
        if gx < 0 or gx >= map.gridW or gy < 0 or gy >= map.gridH:
          continue
        let index = map.gridIndex(gx, gy)
        if index in seenCells:
          continue
        seenCells.incl(index)
        if not map.walkable[index] or map.coverDirs[index] == 0:
          continue
        admitCell(gx, gy, index, -1)
  if PostBucketFallback:
    var wasEmpty = newSeq[bool](PostProgressBuckets)
    var anyEmpty = false
    for index, bucket in buckets:
      if bucket.len == 0:
        wasEmpty[index] = true
        anyEmpty = true
    if anyEmpty:
      # One bounded legacy pass, filling only the empty progress bands.
      for gy in 0 ..< map.gridH:
        for gx in 0 ..< map.gridW:
          let index = map.gridIndex(gx, gy)
          if not map.cover[index] or (gx + gy) mod stride != 0 or
              index in seenCells:
            continue
          let probeFromHome = homeFields.distances[index] * NavCell.float
          if classify(probeFromHome) == fcInf:
            continue
          let probeBucket = clamp(
            int(probeFromHome / direct * PostProgressBuckets.float),
            0, PostProgressBuckets - 1)
          if wasEmpty[probeBucket]:
            admitCell(gx, gy, index, probeBucket)
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

proc defenseGate*(map: WorldMap, color: Team): Point =
  ## Derived defender hold base, replacing the authored chokePoint anchor:
  ## the first significant gate on the route from our home toward the most
  ## direct opponent — the on-route choke (home->gate->enemy detour within
  ## GateDetourPx) nearest home. Falls back to the home room's open-area
  ## peak when the route crosses no gate (single-room maps), then to the
  ## capture point. Uses only the home-goal Dijkstra fields minted at init.
  ## Cached per team: the inputs (chokes, homes, fields) are episode-static
  ## and holdPointForSeat sits on a per-tick defender path.
  if map.gates.hasKey(color):
    return map.gates[color]
  defer: map.gates[color] = result
  let home = map.homeCenter(color)
  var
    enemyHome = home
    direct = Inf
  for index in 0 ..< map.teams:
    let opponent = Team(index)
    if opponent == color:
      continue
    let route = map.routeDistance(home, map.homeCenter(opponent))
    if route < direct:
      direct = route
      enemyHome = map.homeCenter(opponent)
  if classify(direct) != fcInf:
    var
      found = false
      best: Point
      bestFromHome = Inf
    for choke in map.chokes:
      let fromHome = map.distanceAt(choke.pos, home)
      let toEnemy = map.distanceAt(choke.pos, enemyHome)
      if classify(fromHome) == fcInf or classify(toEnemy) == fcInf:
        continue
      if fromHome + toEnemy > direct + GateDetourPx.float or fromHome <= 0.0:
        continue
      if fromHome < bestFromHome:
        found = true
        bestFromHome = fromHome
        best = choke.pos
    if found:
      return best
  let anchor = map.capturePoint(color)
  if map.canStand(anchor) and map.roomLabel.len > 0:
    let label = map.roomLabel[map.pixelIndex(anchor.x, anchor.y)].int
    if label > 0:
      return map.rooms[label - 1].peak
  anchor

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
