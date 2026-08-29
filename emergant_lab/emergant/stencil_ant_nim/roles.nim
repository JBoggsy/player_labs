## Seat roles and geometry-derived defender hold points.

import std/[math, options, tables]
import config, types, worldmap

proc defenderCount*(seats: int): int =
  max(1, pyRound(ConfiguredDefenderCount.float * seats.float / 8.0))

proc roleForSeat*(seat, seats: int): Role =
  if seat < defenderCount(seats): Defender else: Forager

proc holdPointForSeat*(map: WorldMap, team: Team, seat, seats: int): Point =
  let
    count = max(1, defenderCount(seats))
    base = map.defenseGate(team)
    home = map.homeCenter(team)
    axisX = map.center.x - home.x
    axisY = map.center.y - home.y
    norm = max(hypot(axisX.float, axisY.float), 1.0)
    perpendicularX = -axisY.float / norm
    perpendicularY = axisX.float / norm
    band = min(map.width, map.height) div 4
    offset = if count == 1: 0.0
      else: -band.float + 2.0 * band.float * seat.float / (count - 1).float
    point = (
      clamp(int(base.x.float + perpendicularX * offset), 12, map.width - 13),
      clamp(int(base.y.float + perpendicularY * offset), 12, map.height - 13))
    cover = map.nearestCover(point, 10)
  if cover.isSome: cover.get else: point

proc defensivePostForSeat*(
  map: WorldMap, team: Team, seat, seats: int,
  threats: openArray[Point] = []
): Option[tuple[post: PostCandidate, opponent: Team]] =
  ## Give defenders distinct atlas posts, preserving the home-outward 64px
  ## band ordering while evaluating reach, travel, facing, and lazy ducking at
  ## query time.
  if seat >= defenderCount(seats):
    return none(tuple[post: PostCandidate, opponent: Team])
  let opponent = map.mostDirectOpponent(team)
  if opponent.isNone:
    return none(tuple[post: PostCandidate, opponent: Team])
  let
    home = map.homeCenter(team)
    enemyHome = map.homeCenter(opponent.get)
    bearing = some(arctan2(
      (enemyHome.y - home.y).float, (enemyHome.x - home.x).float))
    bandPx = NavCell * 8
    maxRadius = ceil(hypot(map.width.float, map.height.float)).int + bandPx
  var selected: seq[PostCandidate]
  var radius = bandPx
  while radius <= maxRadius:
    var band: seq[int]
    let innerSquared = (radius - bandPx).int64 * (radius - bandPx).int64
    for atlasIndex in map.atlasNear(home, radius):
      let post = map.postAtlas[atlasIndex]
      let
        dx = (post.pos.x - home.x).int64
        dy = (post.pos.y - home.y).int64
      if radius == bandPx or dx * dx + dy * dy > innerSquared:
        band.add(atlasIndex)
    for candidate in map.rankedAtlasPosts(
        band, home, threats, bearing, radius):
      var separated = true
      for previous in selected:
        if hypot((candidate.pos.x - previous.pos.x).float,
            (candidate.pos.y - previous.pos.y).float) < PostSeparationPx.float:
          separated = false
          break
      if separated:
        selected.add(candidate)
        if selected.len > seat:
          return some((selected[seat], opponent.get))
    radius += bandPx
  none(tuple[post: PostCandidate, opponent: Team])

proc earlyDefensePostForSeat*(
  map: WorldMap, team: Team, seat, seats: int
): Point =
  ## Cover the seat's home-room entrance gate from inside the exact endzone.
  ## Degenerate topology or a gate with no qualifying atlas post retains the
  ## previous spawn-cover behavior.
  let fallback = map.spawnCoverPoint(team, seat, seats)
  if not map.endzones.hasKey(team):
    return fallback
  let capture = map.capturePoint(team)
  if not map.canStand(capture) or map.roomLabel.len == 0:
    return fallback
  let roomLabel = map.roomLabel[capture.y * map.width + capture.x].int
  if roomLabel <= 0 or map.rooms[roomLabel - 1].chokes.len == 0:
    return fallback
  let
    chokeIndex = map.rooms[roomLabel - 1].chokes[
      floorMod(seat, map.rooms[roomLabel - 1].chokes.len)]
    gate = map.chokes[chokeIndex].pos
    home = map.homeCenter(team)
    bearing = some(arctan2(
      (gate.y - home.y).float, (gate.x - home.x).float))
    zone = map.endzones[team]
  var candidates: seq[int]
  for atlasIndex in map.atlasNear(gate, SquadPostSearchPx):
    if zone.contains(map.postAtlas[atlasIndex].pos):
      candidates.add(atlasIndex)
  let selected = map.selectRankedPost(
    candidates, gate, 0, [], bearing, SquadPostSearchPx)
  if selected.isSome: selected.get.pos else: fallback
