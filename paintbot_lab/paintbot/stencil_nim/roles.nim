## Seat roles and geometry-derived defender hold points.

import std/[math, options]
import config, types, worldmap

proc defenderCount*(seats: int): int =
  max(1, pyRound(ConfiguredDefenderCount.float * seats.float / 8.0))

proc roleForSeat*(seat, seats: int): Role =
  if seat < defenderCount(seats): Defender else: Attacker

proc holdPointForSeat*(map: WorldMap, team: Team, seat, seats: int): Point =
  let
    count = max(1, defenderCount(seats))
    base = map.chokePoint(team)
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
