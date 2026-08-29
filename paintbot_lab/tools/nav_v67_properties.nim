## Focused deterministic properties for the v67 orientation-free post atlas.
##
## Run from the repository root:
##   nim c -r -d:release --path:paintbot_lab/paintbot/stencil_nim \
##     paintbot_lab/tools/nav_v67_properties.nim

import std/[math, options, tables]
import config, roles, types, worldmap

proc fixture(): WorldMap =
  const
    Width = 256
    Height = 192
  var walkable = newSeq[bool](Width * Height)
  for y in 1 ..< Height - 1:
    for x in 1 ..< Width - 1:
      walkable[y * Width + x] = true
  # Two broad rooms with one entrance gate. The irregular wall shelves create
  # ample cover-bearing cells and non-trivial duck alternatives.
  for y in 1 ..< Height - 1:
    if y < 76 or y > 116:
      walkable[y * Width + 128] = false
  for x in 28 .. 92:
    walkable[48 * Width + x] = false
  for x in 164 .. 228:
    walkable[144 * Width + x] = false
  var markers = initTable[Team, EndzoneMarker]()
  markers[Team(0)] = EndzoneMarker(
    shape: "box", x0: 16, y0: 24, x1: 112, y1: 168)
  markers[Team(1)] = EndzoneMarker(
    shape: "box", x0: 144, y0: 24, x1: 240, y1: 168)
  newWorldMap(walkable, Width, Height, 2, markers, Team(0))

proc allAtlasIndices(map: WorldMap): seq[int] =
  for index in 0 ..< map.postAtlas.len:
    result.add(index)

proc sameCandidate(a, b: Option[PostCandidate]): bool =
  if a.isSome != b.isSome:
    return false
  if a.isNone:
    return true
  let (left, right) = (a.get, b.get)
  left.pos == right.pos and left.duck == right.duck and
    left.score == right.score and left.sightline == right.sightline and
    left.duckContrast == right.duckContrast and left.rayEnds == right.rayEnds

proc referenceReach(map: WorldMap, point: Point, sector: int): int =
  let
    angle = sector.float * 2.0 * PI / AtlasSectorCount.float
    dx = cos(angle)
    dy = sin(angle)
  for distance in 1 .. PostReachCapPx:
    let sample: Point = (
      point.x + pyRound(dx * distance.float),
      point.y + pyRound(dy * distance.float))
    if map.isWall(sample):
      break
    result = distance

proc atlasGeometryProperties() =
  let map = fixture()
  var coverCount = 0
  for gy in 0 ..< map.gridH:
    for gx in 0 ..< map.gridW:
      if map.coverDirs[gy * map.gridW + gx] != 0:
        inc coverCount
  doAssert map.postAtlas.len == coverCount
  for post in map.postAtlas:
    let cell = map.cellOf(post.pos)
    doAssert map.coverDirs[cell.y * map.gridW + cell.x] != 0
    for sector in 0 ..< AtlasSectorCount:
      doAssert post.reach[sector].int <= PostReachCapPx
      doAssert post.reach[sector].int == map.referenceReach(post.pos, sector)
      let
        angle = sector.float * 2.0 * PI / AtlasSectorCount.float
        immediate: Point = (
          post.pos.x + pyRound(cos(angle)),
          post.pos.y + pyRound(sin(angle)))
      if map.isWall(immediate):
        doAssert post.reach[sector] == 0

proc deterministicLazyQueries() =
  let
    first = fixture()
    second = fixture()
  doAssert first.postAtlas.len == second.postAtlas.len
  for index in 0 ..< first.postAtlas.len:
    doAssert first.postAtlas[index].pos == second.postAtlas[index].pos
    doAssert first.postAtlas[index].reach == second.postAtlas[index].reach
  let
    candidates = first.allAtlasIndices
    anchorA: Point = (72, 88)
    anchorB: Point = (184, 104)
    bearingA = some(0.0)
    bearingB = some(PI)
    firstA = first.selectRankedPost(
      candidates, anchorA, 0, [], bearingA, 400)
    firstB = first.selectRankedPost(
      candidates, anchorB, 0, [], bearingB, 400)
    secondB = second.selectRankedPost(
      candidates, anchorB, 0, [], bearingB, 400)
    secondA = second.selectRankedPost(
      candidates, anchorA, 0, [], bearingA, 400)
  doAssert sameCandidate(firstA, secondA)
  doAssert sameCandidate(firstB, secondB)

proc topEightDuckRescueBound() =
  let map = fixture()
  let candidates = map.allAtlasIndices
  doAssert candidates.len > 8
  doAssert map.cachedDuckCount == 0
  discard map.selectRankedPost(
    candidates, map.center, 0, [], none(float), max(map.width, map.height))
  # Phase two may compute duck geometry for every finalist, but never for a
  # phase-one candidate outside the top eight.
  doAssert map.cachedDuckCount == 8

proc roleProperties() =
  let map = fixture()
  let zone = map.endzones[Team(0)]
  for seat in 0 ..< 4:
    doAssert zone.contains(map.earlyDefensePostForSeat(Team(0), seat, 4))
  let
    first = map.defensivePostForSeat(Team(0), 0, 4)
    second = map.defensivePostForSeat(Team(0), 1, 4)
  doAssert first.isSome and second.isSome
  doAssert hypot(
    (first.get.post.pos.x - second.get.post.pos.x).float,
    (first.get.post.pos.y - second.get.post.pos.y).float) >=
    PostSeparationPx.float

atlasGeometryProperties()
deterministicLazyQueries()
topEightDuckRescueBound()
roleProperties()
echo "nav_v67_properties: atlas, determinism, duck bound, and roles passed"
