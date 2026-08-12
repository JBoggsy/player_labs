## Seat roles and geometry-derived defender hold points.

import std/[algorithm, math, options]
import config, types, worldmap

proc defenderCount*(seats: int): int =
  max(1, pyRound(ConfiguredDefenderCount.float * seats.float / 8.0))

proc roleForSeat*(seat, seats: int): Role =
  if seat < defenderCount(seats): Defender else: Attacker

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
  ## Give defenders distinct generated posts, ordered from home center
  ## outward in 64px distance bands; within a band, score plus the
  ## situational facing term against believed threats breaks ties (exact
  ## distances almost never tie, so banding is what lets intel matter).
  if seat >= defenderCount(seats):
    return none(tuple[post: PostCandidate, opponent: Team])
  let home = map.homeCenter(team)
  # v64 wide pool: defenders select from the full per-front candidate pool
  # (every candidate is ray-scored and duck-paired now), not the static
  # top-N posts — the choice, not the menu, carries the context.
  var posts: seq[tuple[post: PostCandidate, opponent: Team]]
  for front in map.postFronts:
    for post in front.candidates:
      var duplicate = false
      for existing in posts:
        if existing.post.pos == post.pos:
          duplicate = true
          break
      if not duplicate:
        posts.add((post, front.opponent))
  let bandPx = NavCell.float * 8.0
  var threatList = newSeq[Point](threats.len)
  for index, threat in threats:
    threatList[index] = threat
  posts.sort(proc(
    a, b: tuple[post: PostCandidate, opponent: Team]
  ): int =
    let
      aBand = int(hypot((a.post.pos.x - home.x).float,
        (a.post.pos.y - home.y).float) / bandPx)
      bBand = int(hypot((b.post.pos.x - home.x).float,
        (b.post.pos.y - home.y).float) / bandPx)
    result = cmp(aBand, bBand)
    if result == 0:
      let aUtility = a.post.score +
        PostFacingWeight * (map.facingScore(a.post.pos, threatList) - 0.5)
      let bUtility = b.post.score +
        PostFacingWeight * (map.facingScore(b.post.pos, threatList) - 0.5)
      result = cmp(bUtility, aUtility))
  # Seat-th DISTINCT position: with a dense pool, adjacent cells would
  # otherwise stack defenders shoulder to shoulder.
  var selected: seq[tuple[post: PostCandidate, opponent: Team]]
  for candidate in posts:
    var separated = true
    for previous in selected:
      if hypot((candidate.post.pos.x - previous.post.pos.x).float,
          (candidate.post.pos.y - previous.post.pos.y).float) <
          PostSeparationPx.float:
        separated = false
        break
    if separated:
      selected.add(candidate)
      if selected.len > seat:
        break
  if seat < selected.len:
    some(selected[seat])
  else:
    none(tuple[post: PostCandidate, opponent: Team])
