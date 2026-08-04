## Roster-aware squad formation and multi-team convert trigger.

import std/[math, options, sets, tables]
import belief_state, config, types, worldmap

type Squad* = tuple[name: char, seats: seq[int]]

proc squadTable(seats: int): seq[Squad] =
  if seats <= 4:
    @[('A', @[0, 1]), ('B', @[2, 3])]
  else:
    @[('A', @[0, 1, 2]), ('C', @[3, 4]), ('B', @[5, 6, 7])]

proc squadOf*(belief: Belief, selectedSeat = -1): Squad =
  let seat = if selectedSeat < 0: belief.seat else: selectedSeat
  let squads = squadTable(belief.seatsPerTeam)
  for squad in squads:
    if seat in squad.seats:
      return squad
  squads[^1]

proc rankOf*(belief: Belief, selectedSeat = -1): int =
  let seat = if selectedSeat < 0: belief.seat else: selectedSeat
  let squad = belief.squadOf(seat)
  let rank = squad.seats.find(seat)
  if rank >= 0: rank else: 0

proc squadSize*(belief: Belief): int = belief.squadOf.seats.len
proc leaderOf*(belief: Belief, selectedSeat = -1): int = belief.squadOf(selectedSeat).seats[0]

proc sectorOffsetBrads*(belief: Belief): int =
  let rank = belief.rankOf
  if rank == 0: return 0
  let sign = if rank mod 2 == 1: 1 else: -1
  sign * SquadSectorBrads * ((rank + 1) div 2)

proc teammatePositions(belief: Belief, squadOnly = false): seq[Point] =
  var mySquad = belief.squadOf.seats.toHashSet
  mySquad.excl(belief.seat)
  for teammate in belief.teammates:
    if squadOnly and (teammate.identity.isNone or teammate.identity.get notin mySquad):
      continue
    result.add(teammate.pos)
  for track in belief.teammateTracks:
    if belief.tick - track.lastTick > TrackTtlTicks div 2 or track.pos in result:
      continue
    if squadOnly and (track.identity.isNone or track.identity.get notin mySquad):
      continue
    result.add(track.pos)

proc buddiesNear*(belief: Belief, radiusPx: float): int =
  let selfXy = belief.selfXy.get
  for pos in belief.teammatePositions:
    if hypot((pos.x - selfXy.x).float, (pos.y - selfXy.y).float) <= radiusPx:
      inc result

proc nearestTo(points: openArray[Point], origin: Point): Point =
  result = points[0]
  var best = (result.x - origin.x) * (result.x - origin.x) +
    (result.y - origin.y) * (result.y - origin.y)
  for index in 1 ..< points.len:
    let distance = (points[index].x - origin.x) * (points[index].x - origin.x) +
      (points[index].y - origin.y) * (points[index].y - origin.y)
    if distance < best:
      best = distance
      result = points[index]

proc separationBias*(belief: Belief): Option[tuple[x, y: float]] =
  if belief.selfXy.isNone:
    return none(tuple[x, y: float])
  let mates = belief.teammatePositions
  if mates.len == 0:
    return none(tuple[x, y: float])
  let selfXy = belief.selfXy.get
  let nearest = nearestTo(mates, selfXy)
  let distance = hypot((nearest.x - selfXy.x).float, (nearest.y - selfXy.y).float)
  if distance > 0.5 and distance < SquadSeparationPx.float:
    return some(((selfXy.x - nearest.x).float / distance,
                 (selfXy.y - nearest.y).float / distance))
  none(tuple[x, y: float])

proc formationBias*(belief: Belief): Option[tuple[x, y: float]] =
  if belief.selfXy.isNone:
    return none(tuple[x, y: float])
  let mates = belief.teammatePositions
  if mates.len == 0:
    return none(tuple[x, y: float])
  let separation = belief.separationBias
  if separation.isSome:
    return separation
  let selfXy = belief.selfXy.get
  let nearest = nearestTo(mates, selfXy)
  let distance = hypot((nearest.x - selfXy.x).float, (nearest.y - selfXy.y).float)
  if belief.buddiesNear(SquadCohesionPx.float) < SquadMinBuddies and
      distance > SquadCohesionPx.float:
    let squadmates = belief.teammatePositions(true)
    let target = if squadmates.len > 0: nearestTo(squadmates, selfXy) else: nearest
    let targetDistance = hypot((target.x - selfXy.x).float, (target.y - selfXy.y).float)
    if targetDistance >= 0.5:
      return some(((target.x - selfXy.x).float / targetDistance,
                   (target.y - selfXy.y).float / targetDistance))
  none(tuple[x, y: float])

proc spreadPoint*(belief: Belief, pos: Point): Point =
  let rank = belief.rankOf
  let offset = if rank == 0: 0 else:
    (if rank mod 2 == 1: 1 else: -1) * SquadSpreadPx * ((rank + 1) div 2)
  let maxY = if belief.worldmap.isNil: pos.y else: belief.worldmap.height - 21
  let point = (pos.x, clamp(pos.y + offset, 20, maxY))
  if offset == 0 or belief.worldmap.isNil:
    return point
  let cover = belief.worldmap.nearestCover(point)
  if cover.isSome: cover.get else: point

proc updatePresence*(belief: Belief) =
  var mySquad = belief.squadOf.seats.toHashSet
  mySquad.excl(belief.seat)
  for teammate in belief.teammates:
    if teammate.identity.isSome and teammate.identity.get in mySquad:
      belief.presence[teammate.identity.get] = belief.tick

proc enemyLivesLeft*(belief: Belief): Option[int] =
  if belief.worldmap.isNil or belief.teamScores.len == 0:
    return none(int)
  let total = belief.seatsPerTeam * LivesPerPlayer
  var best = high(int)
  for color in belief.colors:
    if color == belief.team or not belief.teamScores.hasKey(color):
      continue
    let remaining = max(0, total - belief.teamScores[color].deaths)
    if remaining > 0:
      best = min(best, remaining)
  if best < high(int): some(best) else: none(int)

proc weakestEnemyColor*(belief: Belief): Option[Team] =
  if belief.worldmap.isNil or belief.teamScores.len == 0:
    return none(Team)
  let total = belief.seatsPerTeam * LivesPerPlayer
  var bestLives = high(int)
  for color in belief.colors:
    if color == belief.team or not belief.teamScores.hasKey(color):
      continue
    let remaining = max(0, total - belief.teamScores[color].deaths)
    if remaining > 0 and remaining < bestLives:
      bestLives = remaining
      result = some(color)

proc wipeInReach*(belief: Belief): bool =
  let lives = belief.enemyLivesLeft
  lives.isSome and lives.get <= ConvertEnemyLives

proc convertHuntPoint*(belief: Belief): Point =
  if belief.enemies.len > 0:
    return belief.enemies[0].pos
  var newestTick = low(int)
  for track in belief.enemyTracks:
    if belief.tick - track.lastTick <= TrackTtlTicks and track.lastTick > newestTick:
      newestTick = track.lastTick
      result = track.pos
  if newestTick > low(int):
    return
  if not belief.worldmap.isNil:
    let target = belief.weakestEnemyColor
    if target.isSome:
      return belief.worldmap.pedestal(target.get)
    return belief.worldmap.center
  result = if belief.selfXy.isSome: belief.selfXy.get else: (0, 0)

proc squadmatesAlive*(belief: Belief): int =
  var mySquad = belief.squadOf.seats.toHashSet
  mySquad.excl(belief.seat)
  for seat in mySquad:
    if belief.tick - belief.presence.getOrDefault(seat, -10_000) <= PresenceStaleTicks:
      inc result

proc leadSquad*(belief: Belief) =
  if belief.leaderOf != belief.seat or belief.selfXy.isNone or belief.worldmap.isNil:
    return
  let map = belief.worldmap
  var goal: char
  var pos: Point
  if belief.ownHeartStolen and
      (belief.ownHeartThiefPos.isSome or belief.thiefFix.isSome):
    goal = 'T'
    pos = if belief.ownHeartThiefPos.isSome:
      belief.ownHeartThiefPos.get else: belief.thiefFix.get.pos
  elif belief.carrierFix.isSome:
    goal = 'F'
    pos = belief.carrierFix.get.pos
  elif belief.wipeInReach:
    goal = 'T'
    pos = belief.convertHuntPoint
    if belief.order.isNone or belief.order.get.goal != 'T': inc belief.convertEvents
  elif map.pastRally(belief.team, belief.selfXy.get) and
      belief.squadmatesAlive < belief.squadSize - 1:
    goal = 'H'
    pos = map.homeStep(belief.team, belief.selfXy.get, BackoffStepPx)
    if belief.order.isNone or belief.order.get.goal != 'H': inc belief.backoffEvents
  else:
    let choke = map.chokePoint(belief.team)
    if belief.squadOf.name in {'A', 'B'}:
      goal = 'H'
      pos = belief.spreadPoint(choke)
    else:
      goal = 'P'
      pos = map.center
  if belief.order.isNone or belief.order.get.goal != goal or belief.order.get.pos != pos:
    belief.order = some((goal, pos, belief.tick))
    belief.orderSource = "leader"

proc decayHoldPoint*(belief: Belief): Point =
  if not belief.worldmap.isNil and belief.worldmap.pastRally(belief.team, belief.selfXy.get):
    belief.worldmap.homeStep(belief.team, belief.selfXy.get, BackoffStepPx)
  else:
    belief.selfXy.get

proc rejoinTarget*(belief: Belief): Option[Point] =
  var mySquad = belief.squadOf.seats.toHashSet
  mySquad.excl(belief.seat)
  var bestTick = -1
  for track in belief.teammateTracks:
    if track.identity.isSome and track.identity.get in mySquad and track.lastTick > bestTick:
      bestTick = track.lastTick
      result = some(track.pos)
  if result.isSome:
    return
  if belief.selfXy.isSome and not belief.worldmap.isNil:
    return some(belief.worldmap.homeStep(
      belief.team, belief.selfXy.get, BackoffStepPx * 2))

proc inSquadContact*(belief: Belief): bool =
  var mySquad = belief.squadOf.seats.toHashSet
  mySquad.excl(belief.seat)
  for teammate in belief.teammates:
    if teammate.identity.isSome and teammate.identity.get in mySquad and
        hypot((teammate.pos.x - belief.selfXy.get.x).float,
              (teammate.pos.y - belief.selfXy.get.y).float) <= RejoinContactPx.float:
      return true
