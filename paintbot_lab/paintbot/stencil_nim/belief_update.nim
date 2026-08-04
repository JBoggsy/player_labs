## Fold one memoryless percept into stencil's long-lived belief.

import std/[math, options, sets, tables]
import belief_state, chat, config, fight, items, squads, types, worldmap

let
  DangerDecay = pow(0.5, 1.0 / DangerDecayHalfLifeTicks.float).float32
  SpreadCellsPerTick = DangerDiffusionFactor * MaxSpeedPxTick / NavCell.float
  StampCells = max(DangerStampRadiusPx div NavCell, 1)

proc stampDanger(belief: Belief, pos: Point, heat: float32, cells: int)

proc updateHearts(belief: Belief, percept: PaintState) =
  belief.hearts = percept.hearts
  belief.iCarryHeartOf = percept.iCarryHeartOf
  let map = belief.worldmap
  if not map.isNil:
    for color, heart in percept.hearts:
      if heart.planted and heart.pos.isSome:
        map.pedestals[color] = heart.pos.get
    let totalLives = belief.seatsPerTeam * LivesPerPlayer
    for color, heart in percept.hearts:
      if color in belief.heartsRetired or heart.planted or heart.carriedPos.isSome:
        continue
      if belief.teamScores.hasKey(color) and
          totalLives - belief.teamScores[color].deaths <= 0:
        belief.heartsRetired.incl(color)

  if percept.hearts.hasKey(belief.team):
    let own = percept.hearts[belief.team]
    belief.ownHeartStolen = not own.planted and belief.team notin belief.heartsRetired
    belief.ownHeartThiefPos = if belief.ownHeartStolen: own.carriedPos else: none(Point)
  else:
    belief.ownHeartStolen = false
    belief.ownHeartThiefPos = none(Point)

  if not map.isNil:
    if belief.stealTarget.isSome and belief.stealTarget.get in belief.heartsRetired:
      belief.stealTarget = none(Team)
    if belief.stealTarget.isNone:
      let home = map.homeCenter(belief.team)
      var bestDistance = Inf
      for color in belief.colors:
        if color == belief.team or color in belief.heartsRetired:
          continue
        let route = map.routeDistance(home, map.pedestal(color))
        if route < bestDistance:
          bestDistance = route
          belief.stealTarget = some(color)

proc updateTracks(
  tracks: var seq[PlayerTrack], sightings: openArray[Enemy], tick: int
) =
  var unclaimed = newSeq[bool](tracks.len)
  for value in unclaimed.mitems: value = true
  for sighting in sightings:
    var
      bestIndex = -1
      bestDistanceSquared = Inf
    for index in 0 ..< unclaimed.len:
      if not unclaimed[index]:
        continue
      let track = tracks[index]
      if sighting.identity.isSome and track.identity.isSome and
          (sighting.identity.get != track.identity.get or sighting.color != track.color):
        continue
      if track.color != sighting.color and track.identity.isSome:
        continue
      let elapsed = tick - track.lastTick
      let gate = elapsed.float * MaxSpeedPxTick + TrackMatchSlackPx.float
      let dx = sighting.pos.x - track.pos.x
      let dy = sighting.pos.y - track.pos.y
      if max(abs(dx), abs(dy)).float > gate:
        continue
      let distanceSquared = (dx * dx + dy * dy).float
      if distanceSquared < bestDistanceSquared:
        bestDistanceSquared = distanceSquared
        bestIndex = index
    if bestIndex < 0:
      tracks.add(PlayerTrack(
        pos: sighting.pos, lastTick: tick, facing: sighting.facing,
        color: sighting.color, framesSeen: 1, identity: sighting.identity,
        hpSegments: sighting.hpSegments, shielded: sighting.shielded))
      continue
    unclaimed[bestIndex] = false
    let oldPos = tracks[bestIndex].pos
    let elapsed = tick - tracks[bestIndex].lastTick
    tracks[bestIndex].color = sighting.color
    if sighting.identity.isSome: tracks[bestIndex].identity = sighting.identity
    if sighting.hpSegments.isSome: tracks[bestIndex].hpSegments = sighting.hpSegments
    tracks[bestIndex].shielded = sighting.shielded
    if elapsed > 0 and elapsed <= TrackVelMaxGapTicks:
      let vx = (sighting.pos.x - oldPos.x).float / elapsed.float
      let vy = (sighting.pos.y - oldPos.y).float / elapsed.float
      if tracks[bestIndex].vel.isSome:
        let oldVelocity = tracks[bestIndex].vel.get
        tracks[bestIndex].vel = some((
          oldVelocity.x + (vx - oldVelocity.x) * TrackVelEma,
          oldVelocity.y + (vy - oldVelocity.y) * TrackVelEma))
      else:
        tracks[bestIndex].vel = some((vx, vy))
    elif elapsed > TrackVelMaxGapTicks:
      tracks[bestIndex].vel = none(tuple[x, y: float])
    tracks[bestIndex].pos = sighting.pos
    tracks[bestIndex].facing = sighting.facing
    tracks[bestIndex].lastTick = tick
    inc tracks[bestIndex].framesSeen
  var retained: seq[PlayerTrack]
  for track in tracks:
    if tick - track.lastTick <= TrackTtlTicks:
      retained.add(track)
  tracks = retained

proc updateHeard(belief: Belief, percept: PaintState, tick: int) =
  for sound in percept.heardImpacts:
    var matched = -1
    for index, event in belief.heardEvents:
      if event.kind == sound.kind and
          max(abs(sound.pos.x - event.pos.x), abs(sound.pos.y - event.pos.y)) <= HeardMatchPx:
        matched = index
        break
    if matched >= 0:
      belief.heardEvents[matched].lastTick = tick
    else:
      belief.heardEvents.add(HeardImpact(
        kind: sound.kind, pos: sound.pos, firstTick: tick, lastTick: tick))
  var retained: seq[HeardImpact]
  for event in belief.heardEvents:
    if tick - event.lastTick <= HeardTtlTicks:
      retained.add(event)
  belief.heardEvents = retained

proc updateUnderFire(belief: Belief, tick: int) =
  belief.underFire = false
  if belief.selfXy.isNone:
    return
  for event in belief.heardEvents:
    if tick - event.firstTick <= UnderFireFreshTicks and
        hypot((event.pos.x - belief.selfXy.get.x).float,
              (event.pos.y - belief.selfXy.get.y).float) <= UnderFireRangePx.float:
      belief.underFire = true
      return

proc updateChat(belief: Belief, percept: PaintState, tick: int) =
  if belief.worldmap.isNil:
    return
  for shout in percept.heardShouts:
    let key = shout.team & " " & shout.address
    if belief.chatProcessed.hasKey(key):
      let previous = belief.chatProcessed[key]
      if previous.text == shout.text and tick - previous.tick <= ChatBubbleDedupTicks:
        belief.chatProcessed[key] = (shout.text, tick)
        continue
    belief.chatProcessed[key] = (shout.text, tick)
    let shoutTeam = parseTeam(shout.team)
    if shoutTeam.isNone:
      continue
    if shoutTeam.get != belief.team:
      if ChatEnemyBubbleFix:
        let sighting = Enemy(pos: shout.pos, facing: FacingLeft,
          color: shoutTeam.get, identity: none(int), hpSegments: none(int))
        updateTracks(belief.enemyTracks, [sighting], tick)
        belief.chatHeardCounts.inc("enemy_bubble")
      continue
    if shout.text == belief.chatLastSentText:
      continue
    let decoded = belief.worldmap.decode(shout.text)
    if decoded.isNone:
      continue
    let message = decoded.get
    belief.chatHeardCounts.inc(message.kind)
    case message.kind
    of "order":
      if message.seat.isSome and message.seat.get == belief.leaderOf and
          message.seat.get != belief.seat:
        let goal = if message.goal.isSome: message.goal.get else: 'H'
        belief.order = some((goal, message.pos, tick))
        belief.orderSource = "heard"
        inc belief.ordersHeard
      if message.seat.isSome:
        belief.presence[message.seat.get] = tick
    of "ping":
      if message.seat.isSome:
        belief.presence[message.seat.get] = tick
        inc belief.pingsHeard
    of "focus_claim":
      if message.seat.isSome:
        belief.receiveFocusClaim(
          message.seat.get, message.targetIdentity, message.pos)
    of "enemy", "thief":
      let sighting = Enemy(pos: message.pos, facing: FacingLeft,
        color: Red, identity: none(int), hpSegments: none(int))
      updateTracks(belief.enemyTracks, [sighting], tick)
      if message.kind == "thief":
        belief.thiefFix = some((message.pos, tick))
    of "carrier":
      belief.carrierFix = some((message.pos,
        if message.heading.isSome: message.heading.get else: 0, tick))
    of "grenade":
      belief.grenadeWarnings.add((message.pos, tick))
    of "under_fire":
      belief.stampDanger(message.pos, HeardDangerHeat.float32,
        max(HeardDangerRadiusPx div NavCell, 1))
    else: discard
  if belief.carrierFix.isSome and
      tick - belief.carrierFix.get.heardTick > ChatFixTtlTicks:
    belief.carrierFix = none(CarrierFix)
  if belief.thiefFix.isSome and tick - belief.thiefFix.get.tick > ChatFixTtlTicks:
    belief.thiefFix = none(ThiefFix)
  var warnings: seq[GrenadeWarning]
  for warning in belief.grenadeWarnings:
    if tick - warning.tick <= GrenadeWarnTtlTicks:
      warnings.add(warning)
  belief.grenadeWarnings = warnings

proc initDanger(belief: Belief) =
  let map = belief.worldmap
  belief.danger = newSeq[float32](map.gridW * map.gridH)
  let home = map.homeCenter(belief.team)
  for gy in 0 ..< map.gridH:
    for gx in 0 ..< map.gridW:
      let index = gy * map.gridW + gx
      if not map.walkable[index]:
        continue
      let px = gx * NavCell + NavCell div 2
      let py = gy * NavCell + NavCell div 2
      let homeDistance = (px - home.x) * (px - home.x) + (py - home.y) * (py - home.y)
      let centerDistance = (px - map.center.x) * (px - map.center.x) +
        (py - map.center.y) * (py - map.center.y)
      if homeDistance >= centerDistance:
        belief.danger[index] = 1.0

proc dilateDanger(belief: Belief) =
  let map = belief.worldmap
  var dilated = newSeq[float32](belief.danger.len)
  for gy in 0 ..< map.gridH:
    for gx in 0 ..< map.gridW:
      let index = gy * map.gridW + gx
      if not map.walkable[index]:
        continue
      var peak = 0'f32
      for dy in -1 .. 1:
        for dx in -1 .. 1:
          let nx = gx + dx
          let ny = gy + dy
          if nx >= 0 and nx < map.gridW and ny >= 0 and ny < map.gridH:
            peak = max(peak, belief.danger[ny * map.gridW + nx])
      dilated[index] = peak
  belief.danger = dilated

proc stampDanger(
  belief: Belief, pos: Point, heat: float32, cells: int
) =
  if belief.worldmap.isNil or belief.danger.len == 0:
    return
  let map = belief.worldmap
  let center = map.cellOf(pos)
  for gy in max(center.y - cells, 0) .. min(center.y + cells, map.gridH - 1):
    for gx in max(center.x - cells, 0) .. min(center.x + cells, map.gridW - 1):
      let index = gy * map.gridW + gx
      belief.danger[index] = max(belief.danger[index], heat)

proc updateDanger(belief: Belief) =
  let map = belief.worldmap
  if map.isNil:
    return
  if belief.danger.len != map.gridW * map.gridH:
    belief.initDanger()
  for value in belief.danger.mitems:
    value *= DangerDecay
  belief.dangerSpreadCarry += SpreadCellsPerTick
  while belief.dangerSpreadCarry >= 1.0:
    belief.dilateDanger()
    belief.dangerSpreadCarry -= 1.0
  for enemy in belief.enemies:
    belief.stampDanger(enemy.pos, 1.0, StampCells)
  let heardCells = max(HeardDangerRadiusPx div NavCell, 1)
  for event in belief.heardEvents:
    if event.firstTick == belief.tick:
      belief.stampDanger(event.pos, HeardDangerHeat.float32, heardCells)
  for index, walkable in map.walkable:
    if not walkable:
      belief.danger[index] = 0.0

proc updateBeliefCore*(
  belief: Belief, percept: PaintState, actionState: ActionState, tick: int
) =
  belief.tick = tick
  let wasAlive = belief.alive
  belief.alive = percept.selfXy.isSome
  if percept.selfXy.isSome:
    belief.selfXy = percept.selfXy
  if not wasAlive and belief.alive:
    belief.respawnedTick = tick

  if not belief.colorLocked and percept.selfColor.isSome and
      percept.selfColor.get != belief.team:
    belief.team = percept.selfColor.get
    belief.colorLocked = true
    belief.stealTarget = none(Team)
  elif percept.selfColor.isSome:
    belief.colorLocked = true

  if SquadCommand:
    if wasAlive and not belief.alive:
      belief.rejoinPoint = belief.rejoinTarget()
      belief.rejoinUntil = -1
    elif not wasAlive and belief.alive and belief.rejoinPoint.isSome:
      belief.rejoinUntil = tick + RejoinTimeoutTicks

  if not wasAlive and belief.alive:
    if not belief.worldmap.isNil:
      belief.aimBrads = belief.worldmap.spawnAim(belief.team)
    belief.sweepOffset = 0
    belief.sweepDir = 1
  belief.aimBrads = floorMod(
    belief.aimBrads + actionState.lastRot * AimTurnRate, AimBradsTurn)
  if percept.observedAim.isSome:
    let observed = percept.observedAim.get
    # The wire marker is authoritative for this rendered tick. GV36 makes it
    # especially important not to tolerate a one-slot discrepancy: carrying a
    # stale estimate causes the controller to oscillate around an unreachable
    # fine-grained angle.
    if observed != belief.aimBrads:
      inc belief.aimResyncs
    belief.aimBrads = observed
    belief.prevObservedAim = percept.observedAim

  belief.fireReady = percept.fireReady
  belief.enemies = percept.enemies
  belief.teammates = percept.teammates
  # Campaign map size is independent of variant/muster, and the wire does not
  # state seat count. Grow the lower-bound estimate from identities actually
  # observed; unlike map width, this can never mistake giant 4ffa for 4ffa8.
  for player in percept.enemies & percept.teammates:
    if player.identity.isSome:
      let observedSeats = player.identity.get + 1
      if belief.colors.len == 2 and observedSeats > 1:
        belief.seatsPerTeam = 8
      elif belief.colors.len == 4 and observedSeats > 4:
        belief.seatsPerTeam = 8
  belief.updateHearts(percept)
  for color, score in percept.teamScores:
    belief.teamScores[color] = score
  belief.hpPips = percept.hpPips
  belief.iHaveGrenade = percept.iHaveGrenade
  belief.iHaveShield = percept.iHaveShield
  belief.iHaveArc = percept.iHaveArc
  belief.updateItems(percept)
  updateTracks(belief.enemyTracks, percept.enemies, tick)
  updateTracks(belief.teammateTracks, percept.teammates, tick)
  if Hearing:
    belief.updateHeard(percept, tick)
  belief.updateUnderFire(tick)
  if Chat:
    belief.updateChat(percept, tick)
  belief.updateDanger()
  belief.updateFirefight()
