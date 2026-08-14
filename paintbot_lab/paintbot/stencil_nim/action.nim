## Intent-to-controller resolution: movement, aim, fire, micro, and grenades.

import std/[algorithm, math, options, tables]
import belief_state, config, fight, nav, squads, types, worldmap

const MovementMask = ButtonUp or ButtonDown or ButtonLeft or ButtonRight

type
  MicroOverride = object
    mask: uint8
    aim: Option[int]
    destination: Option[Point]
  GrenadePlan = object
    target: Point
    reason: string
    enemyCount: int
    liveTarget: bool
    rank: int
    distancePx: float

proc distance(a, b: Point): float = hypot((a.x - b.x).float, (a.y - b.y).float)

proc bradsOf(dx, dy: float): int =
  floorMod(pyRound(arctan2(-dy, dx) / (2.0 * PI) * AimBradsTurn.float),
    AimBradsTurn)

proc bradError(target, current: int): int =
  result = floorMod(target - current, AimBradsTurn)
  if result > AimBradsTurn div 2: result -= AimBradsTurn

proc nearestEnemy(belief: Belief): Option[Enemy] =
  if belief.enemies.len == 0 or belief.selfXy.isNone: return none(Enemy)
  result = some(belief.enemies[0])
  var best = distance(belief.enemies[0].pos, belief.selfXy.get)
  for index in 1 ..< belief.enemies.len:
    let d = distance(belief.enemies[index].pos, belief.selfXy.get)
    if d < best:
      best = d
      result = some(belief.enemies[index])

proc clampToMap(belief: Belief, point: Point): Point =
  if belief.worldmap.isNil: point
  else: (clamp(point.x, 0, belief.worldmap.width - 1),
         clamp(point.y, 0, belief.worldmap.height - 1))

proc trackForEnemy(belief: Belief, enemy: Enemy): Option[PlayerTrack] =
  for track in belief.enemyTracks:
    if track.lastTick == belief.tick and track.pos == enemy.pos:
      return some(track)

proc sprayContains(belief: Belief, target: Point): bool =
  let angle = belief.aimBrads.float / AimBradsTurn.float * 2.0 * PI
  let ux = cos(angle)
  let uy = -sin(angle)
  let vx = (target.x - belief.selfXy.get.x).float
  let vy = (target.y - belief.selfXy.get.y).float
  let forward = vx * ux + vy * uy
  let perpendicular = abs(vx * uy - vy * ux)
  forward > 0 and forward <= ArcFireRangePx.float and
    perpendicular <= forward * ArcMaxWidthPx.float / (2.0 * ArcFireRangePx.float)

proc threatAxis(belief: Belief): int =
  if belief.worldmap.isNil: return belief.aimBrads
  let target = if belief.squadOrderPostActive and
      belief.squadOrderPostSightlineAim.isSome:
    belief.squadOrderPostSightlineAim.get
  elif belief.role == Defender and not belief.ownHeartStolen and
      belief.defensivePostOpponent.isSome:
    belief.worldmap.pedestal(belief.defensivePostOpponent.get)
  elif belief.stealTarget.isSome:
    belief.worldmap.pedestal(belief.stealTarget.get)
  else:
    belief.worldmap.center
  let delta: Point = (target.x - belief.selfXy.get.x, target.y - belief.selfXy.get.y)
  if abs(delta.x) < 1 and abs(delta.y) < 1:
    belief.worldmap.spawnAim(belief.team)
  else: bradsOf(delta.x.float, delta.y.float)

proc sweepTarget(belief: Belief): int =
  var axis = belief.threatAxis
  if Squads and not belief.squadOrderPostActive and
      belief.defensivePost.isNone:
    axis = floorMod(axis + belief.sectorOffsetBrads, AimBradsTurn)
  belief.sweepOffset += belief.sweepDir * AimSweepStepBrads
  if belief.sweepOffset >= SweepHalfArc:
    belief.sweepOffset = SweepHalfArc; belief.sweepDir = -1
  elif belief.sweepOffset <= -SweepHalfArc:
    belief.sweepOffset = -SweepHalfArc; belief.sweepDir = 1
  floorMod(axis + belief.sweepOffset, AimBradsTurn)

proc leadAimPos(belief: Belief, enemy: Enemy): tuple[pos: Point, lead: int] =
  if not LeadAim or belief.selfXy.isNone: return (enemy.pos, 0)
  let track = belief.trackForEnemy(enemy)
  if track.isNone or track.get.vel.isNone or track.get.framesSeen < LeadMinFrames:
    return (enemy.pos, 0)
  let pos = belief.clampToMap((
    pyRound(enemy.pos.x.float + track.get.vel.get.x * LeadTicks),
    pyRound(enemy.pos.y.float + track.get.vel.get.y * LeadTicks)))
  if pos == enemy.pos: return (enemy.pos, 0)
  let selfXy = belief.selfXy.get
  let raw = bradsOf((enemy.pos.x - selfXy.x).float, (enemy.pos.y - selfXy.y).float)
  let led = bradsOf((pos.x - selfXy.x).float, (pos.y - selfXy.y).float)
  (pos, bradError(led, raw))

proc fireGate(belief: Belief, target: Point): bool =
  let range = distance(belief.selfXy.get, target)
  if range < 1.0: return true
  let wanted = bradsOf((target.x - belief.selfXy.get.x).float,
    (target.y - belief.selfXy.get.y).float)
  let errorRadians = abs(bradError(wanted, belief.aimBrads)).float /
    AimBradsTurn.float * 2.0 * PI
  let slack = FireSlackPx.float * (if range <= CloseRangePx.float: 2.0 else: 1.0)
  range * sin(errorRadians) <= slack

proc teammateBlocksShot(belief: Belief, target: Point): bool =
  let selfXy = belief.selfXy.get
  let range = distance(selfXy, target)
  if range < 1.0: return false
  let ux = (target.x - selfXy.x).float / range
  let uy = (target.y - selfXy.y).float / range
  for teammate in belief.teammates:
    let mx = (teammate.pos.x - selfXy.x).float
    let my = (teammate.pos.y - selfXy.y).float
    let along = mx * ux + my * uy
    if along <= 0 or along >= range: continue
    if abs(mx * -uy + my * ux) <= FriendlyFireCorridorPx.float: return true

proc targetCandidates(belief: Belief): seq[TargetCandidate] =
  let selfXy = belief.selfXy.get
  for enemy in belief.enemies:
    let aim = belief.leadAimPos(enemy)
    let wanted = bradsOf((aim.pos.x - selfXy.x).float, (aim.pos.y - selfXy.y).float)
    let clear = belief.lineClear(selfXy, aim.pos)
    let blocked = belief.teammateBlocksShot(aim.pos)
    result.add(TargetCandidate(enemy: enemy, target: belief.targetRefFor(enemy),
      aimPos: aim.pos, leadBrads: aim.lead, distancePx: distance(enemy.pos, selfXy),
      aimCost: abs(bradError(wanted, belief.aimBrads)).float /
        (AimBradsTurn div 2).float,
      lineClear: clear, teammateBlocked: blocked, shootable: clear and not blocked))

proc freshTrack(belief: Belief, maxAge: int, maxRange = Inf): Option[PlayerTrack] =
  var bestDistance = maxRange
  for track in belief.enemyTracks:
    if belief.tick - track.lastTick > maxAge: continue
    let d = distance(track.pos, belief.selfXy.get)
    if d < bestDistance:
      bestDistance = d; result = some(track)

proc freshHeardImpact(belief: Belief): Option[Point] =
  var bestDistance = HeardDuckRangePx.float
  let angle = belief.aimBrads.float / AimBradsTurn.float * 2.0 * PI
  let ux = cos(angle); let uy = -sin(angle)
  for event in belief.heardEvents:
    if belief.tick - event.firstTick > HeardDuckFreshTicks: continue
    let dx = (event.pos.x - belief.selfXy.get.x).float
    let dy = (event.pos.y - belief.selfXy.get.y).float
    let d = hypot(dx, dy)
    if d >= bestDistance: continue
    if dx * ux + dy * uy > 0 and abs(dx * -uy + dy * ux) <= 24.0: continue
    result = some(event.pos); bestDistance = d

proc predictedPos(belief: Belief, track: PlayerTrack, tick: int): Point =
  if track.vel.isNone: return track.pos
  let elapsed = tick - track.lastTick
  belief.clampToMap((
    pyRound(track.pos.x.float + track.vel.get.x * elapsed.float),
    pyRound(track.pos.y.float + track.vel.get.y * elapsed.float)))

proc findSidestepCell(
  belief: Belief, selfXy, reference: Point, wantLos: bool
): Option[Point] =
  let map = belief.worldmap
  let source = map.cellOf(selfXy)
  var bestDistance = high(int)
  for dy in -PeekDuckSearchCells .. PeekDuckSearchCells:
    for dx in -PeekDuckSearchCells .. PeekDuckSearchCells:
      let cell: Point = (source.x + dx, source.y + dy)
      if cell.x < 0 or cell.x >= map.gridW or cell.y < 0 or cell.y >= map.gridH or
          not map.walkable[cell.y * map.gridW + cell.x]: continue
      let point = cellCenter(cell)
      if not map.nudgeClear(selfXy, point) or map.rayClear(point, reference) != wantLos:
        continue
      let d = (point.x - selfXy.x) * (point.x - selfXy.x) +
        (point.y - selfXy.y) * (point.y - selfXy.y)
      if d < bestDistance: bestDistance = d; result = some(point)

proc hasViableEngagement(belief: Belief): bool =
  if belief.iHaveArc: return belief.sprayTarget.isSome
  else:
    for candidate in belief.targetCandidates:
      if candidate.shootable: return true

proc coverFromThreat(
  belief: Belief, threat: Point, fromHeard: bool, micro: string
): Option[MicroOverride] =
  let aim = bradsOf((threat.x - belief.selfXy.get.x).float,
    (threat.y - belief.selfXy.get.y).float)
  if not belief.worldmap.rayClear(belief.selfXy.get, threat):
    belief.micro = micro; belief.heardDuck = fromHeard
    return some(MicroOverride(mask: 0'u8, aim: some(aim)))
  let cover = belief.findSidestepCell(belief.selfXy.get, threat, false)
  if cover.isNone: return none(MicroOverride)
  belief.micro = micro; belief.heardDuck = fromHeard
  some(MicroOverride(
    mask: octantToward(belief.selfXy.get, cover.get),
    aim: some(aim), destination: cover))

proc peekDuckAllowed*(intent: Intent, carrying: bool, selfXy: Point): bool =
  if carrying or MicroPeekDuck notin intent.micro: return false
  if MicroStealRushExempt in intent.micro and intent.point.isSome and
      distance(intent.point.get, selfXy) <= PeekDuckRushExemptPx.float:
    return false
  true

proc peekDuckOverride(belief: Belief, intent: Intent): Option[MicroOverride] =
  if belief.worldmap.isNil or not intent.peekDuckAllowed(
      belief.iCarryHeartOf.isSome, belief.selfXy.get):
    return none(MicroOverride)
  if belief.squadOrderPostActive and intent.kind == Hold:
    let threat = belief.freshTrack(DuckThreatFreshTicks, DuckRangePx.float)
    if threat.isSome or belief.enemies.len > 0:
      let aimPoint = if threat.isSome:
        belief.predictedPos(threat.get, belief.tick)
      elif belief.squadOrderPostSightlineAim.isSome:
        belief.squadOrderPostSightlineAim.get
      else:
        belief.enemies[0].pos
      let aim = bradsOf((aimPoint.x - belief.selfXy.get.x).float,
        (aimPoint.y - belief.selfXy.get.y).float)
      let stance = if belief.fireReady:
        belief.squadOrderPost
      else:
        belief.squadOrderPostDuck
      if stance.isSome and distance(stance.get, belief.selfXy.get) >= 5.0 and
          belief.worldmap.nudgeClear(belief.selfXy.get, stance.get):
        belief.micro = if belief.fireReady: "squad_post_peek" else: "squad_post_duck"
        return some(MicroOverride(
          mask: octantToward(belief.selfXy.get, stance.get),
          aim: some(aim), destination: stance))
  if not belief.fireReady:
    let threat = belief.freshTrack(DuckThreatFreshTicks, DuckRangePx.float)
    var fromHeard = false
    var target: Option[Point]
    if threat.isSome: target = some(belief.predictedPos(threat.get, belief.tick))
    elif Hearing:
      target = belief.freshHeardImpact; fromHeard = target.isSome
    if target.isNone: return none(MicroOverride)
    return belief.coverFromThreat(target.get, fromHeard, "duck")
  let heard = if Hearing: belief.freshHeardImpact else: none(Point)
  let allowCover = intent.kind == Hold or belief.underFire or heard.isSome
  if belief.enemies.len > 0:
    if belief.hasViableEngagement: return none(MicroOverride)
    let track = belief.freshTrack(DuckThreatFreshTicks, DuckRangePx.float)
    let target = if track.isSome: belief.predictedPos(track.get, belief.tick)
      else: belief.nearestEnemy.get.pos
    if not belief.worldmap.rayClear(belief.selfXy.get, target):
      let peek = belief.findSidestepCell(belief.selfXy.get, target, true)
      if peek.isSome:
        belief.micro = "peek"
        return some(MicroOverride(
          mask: octantToward(belief.selfXy.get, peek.get),
          aim: some(bradsOf((target.x - belief.selfXy.get.x).float,
                           (target.y - belief.selfXy.get.y).float)),
          destination: peek))
    if allowCover: return belief.coverFromThreat(target, false, "cover")
    return none(MicroOverride)
  let track = belief.freshTrack(PeekTargetFreshTicks)
  if track.isNone:
    if heard.isSome: return belief.coverFromThreat(heard.get, true, "cover")
    return none(MicroOverride)
  let target = belief.predictedPos(track.get, belief.tick)
  if belief.worldmap.rayClear(belief.selfXy.get, target):
    if allowCover: return belief.coverFromThreat(target, false, "cover")
    return none(MicroOverride)
  let aim = bradsOf((target.x - belief.selfXy.get.x).float,
    (target.y - belief.selfXy.get.y).float)
  let peek = belief.findSidestepCell(belief.selfXy.get, target, true)
  if peek.isNone: return none(MicroOverride)
  belief.micro = "peek"
  if distance(peek.get, belief.selfXy.get) < 5.0:
    return some(MicroOverride(mask: 0'u8, aim: some(aim)))
  some(MicroOverride(
    mask: octantToward(belief.selfXy.get, peek.get),
    aim: some(aim), destination: peek))

proc rotationButton(target, current: int, state: var ActionState): uint8 =
  let error = bradError(target, current)
  if abs(error) <= AimTurnDeadbandBrads:
    state.lastRot = 0
    return 0
  if error > 0: state.lastRot = 1; ButtonB
  else: state.lastRot = -1; ButtonSelect

proc blastSafe(belief: Belief, target: Point): bool =
  for track in belief.teammateTracks:
    if belief.tick - track.lastTick > GrenadeTeammateFreshTicks: continue
    let predicted = belief.predictedPos(track, belief.tick + GrenadeFlightTicks)
    if distance(predicted, target) <= GrenadeBlastRadius.float + 20.0: return false
  true

proc postInputAim(mask: uint8, belief: Belief): int =
  if (mask and ButtonB) != 0: floorMod(belief.aimBrads + AimTurnRate, AimBradsTurn)
  elif (mask and ButtonSelect) != 0: floorMod(belief.aimBrads - AimTurnRate, AimBradsTurn)
  else: belief.aimBrads

proc grenadePlan(belief: Belief, mask: uint8): Option[GrenadePlan] =
  let selfXy = belief.selfXy.get
  let lives = belief.enemyLivesLeft
  var plans: seq[GrenadePlan]
  proc addPlan(target: Point, reason: string, enemyCount: int, live: bool, rank: int) =
    let d = distance(target, selfXy)
    if d < GrenadeMinThrowPx.float or d > belief.worldmap.grenadeMaxRange.float: return
    if not belief.blastSafe(target): inc belief.grenadeSafetyVetoes; return
    plans.add(GrenadePlan(target: target, reason: reason, enemyCount: enemyCount,
      liveTarget: live, rank: rank, distancePx: d))
  for enemy in belief.enemies:
    var count = 0
    for other in belief.enemies:
      if distance(other.pos, enemy.pos) <= GrenadeBlastRadius.float: inc count
    let blocked = not belief.worldmap.rayClear(selfXy, enemy.pos)
    let thief = belief.ownHeartStolen and belief.ownHeartThiefPos.isSome and
      distance(belief.ownHeartThiefPos.get, enemy.pos) <= GrenadeBlastRadius.float
    if blocked: addPlan(enemy.pos, "wall_blocked", count, true, 0)
    elif count >= 2: addPlan(enemy.pos, "group", count, true, 1)
    elif thief: addPlan(enemy.pos, "heart_thief", count, true, 2)
    elif lives.isSome and lives.get == 1: addPlan(enemy.pos, "final_life", count, true, 3)
    elif not belief.fireReady and (not ShieldAwareness or not enemy.shielded) and
        enemy.hpSegments.isSome and
        enemy.hpSegments.get <= GrenadeSingleHpMax:
      addPlan(enemy.pos, "cooldown_finish", count, true, 4)
  var predicted: seq[Point]
  for track in belief.enemyTracks:
    if belief.tick - track.lastTick >= 0 and
        belief.tick - track.lastTick <= GrenadeTargetFreshTicks:
      predicted.add(belief.predictedPos(track, belief.tick + GrenadeFlightTicks))
  for track in belief.enemyTracks:
    let age = belief.tick - track.lastTick
    if age < 0 or age > GrenadeTargetFreshTicks or
        (age == 0 and belief.enemies.len > 0): continue
    let pos = belief.predictedPos(track, belief.tick + GrenadeFlightTicks)
    if belief.worldmap.rayClear(selfXy, pos): continue
    var count = 0
    for other in predicted:
      if distance(other, pos) <= GrenadeBlastRadius.float: inc count
    addPlan(pos, "wall_blocked", count, false, 0)
  if plans.len == 0: return none(GrenadePlan)
  let aim = postInputAim(mask, belief)
  plans.sort(proc(a, b: GrenadePlan): int =
    result = cmp(a.rank, b.rank)
    if result == 0: result = cmp(b.enemyCount, a.enemyCount)
    if result == 0:
      result = cmp(abs(bradError(bradsOf((a.target.x-selfXy.x).float,
        (a.target.y-selfXy.y).float), aim)), abs(bradError(bradsOf(
        (b.target.x-selfXy.x).float, (b.target.y-selfXy.y).float), aim)))
    if result == 0: result = cmp(a.distancePx, b.distancePx))
  some(plans[0])

proc refreshLiveThrowTarget(belief: Belief): Option[tuple[pos: Point, count: int]] =
  var candidates: seq[Enemy]
  for enemy in belief.enemies:
    if distance(enemy.pos, belief.throwTarget.get) <= GrenadeBlastRadius.float + 20.0 and
        belief.blastSafe(enemy.pos): candidates.add(enemy)
  if candidates.len == 0: return none(tuple[pos: Point, count: int])
  var target = candidates[0]
  var best = distance(target.pos, belief.throwTarget.get)
  for index in 1 ..< candidates.len:
    let d = distance(candidates[index].pos, belief.throwTarget.get)
    if d < best: best = d; target = candidates[index]
  var count = 0
  for enemy in belief.enemies:
    if distance(enemy.pos, target.pos) <= GrenadeBlastRadius.float: inc count
  some((target.pos, count))

proc grenadeOverlay(mask: uint8, belief: Belief, state: var ActionState): uint8 =
  let selfXy = belief.selfXy.get
  let carrying = belief.iCarryHeartOf.isSome
  let charging = belief.throwChargeTicks > 0
  if charging and carrying: return mask or ButtonC
  let plan = belief.grenadePlan(mask)
  if not charging:
    if plan.isNone: return mask
    let value = plan.get
    belief.throwTarget = some(value.target); belief.throwReason = value.reason
    belief.throwEnemyCount = value.enemyCount; belief.throwLiveTarget = value.liveTarget
    belief.grenadeTargetStarts.inc(value.reason)
    belief.grenadeTargetedEnemies += value.enemyCount
    if value.liveTarget: inc belief.visibleGrenadeStarts
    belief.throwChargeTicks = 1
    return mask or ButtonC
  if belief.throwLiveTarget:
    let refreshed = belief.refreshLiveThrowTarget
    if refreshed.isSome:
      belief.throwTarget = some(refreshed.get.pos); belief.throwEnemyCount = refreshed.get.count
  elif plan.isSome and plan.get.liveTarget:
    belief.throwTarget = some(plan.get.target); belief.throwReason = plan.get.reason
    belief.throwEnemyCount = plan.get.enemyCount; belief.throwLiveTarget = true
  let target = if belief.throwTarget.isSome: belief.throwTarget.get else: selfXy
  inc belief.throwChargeTicks
  let span = max(1, belief.worldmap.grenadeMaxRange - GrenadeMinRange)
  let needed = min(GrenadeChargeTicks, max(1, ceil(
    (distance(target, selfXy) - GrenadeMinRange.float) / span.float *
      GrenadeChargeTicks.float).int))
  let wanted = bradsOf((target.x-selfXy.x).float, (target.y-selfXy.y).float)
  let overdue = belief.throwChargeTicks >= GrenadeChargeTicks + GrenadeForceReleaseTicks
  result = mask
  if belief.enemies.len == 0 and not belief.throwLiveTarget:
    result = result and not (ButtonB or ButtonSelect)
    result = result or rotationButton(wanted, belief.aimBrads, state)
  let releaseError = bradError(wanted, postInputAim(result, belief))
  let ready = belief.throwChargeTicks >= needed and
    abs(releaseError) <= GrenadeAimErrBrads and
    (belief.enemies.len == 0 or belief.throwLiveTarget) and belief.blastSafe(target)
  if ready or overdue:
    let reason = if belief.throwReason.len > 0: belief.throwReason else: "unknown"
    belief.grenadeTargetReleases.inc(reason)
    if overdue: inc belief.grenadeForceReleases
    if ready and belief.throwLiveTarget: inc belief.visibleGrenadeReleases
    belief.throwChargeTicks = 0; belief.throwTarget = none(Point)
    belief.throwReason = ""; belief.throwEnemyCount = 0; belief.throwLiveTarget = false
    return result
  result = result or ButtonC

proc resolveAction*(intent: Intent, belief: Belief, state: var ActionState): Command =
  var mask = 0'u8
  state.lastRot = 0; belief.micro = ""; belief.heardDuck = false
  belief.aimTargetBrads = belief.aimBrads; belief.aimErrorBrads = 0
  belief.aimLateralErrorPx = 0.0
  belief.targetRangePx = 0.0; belief.targetRayClear = false
  belief.targetTeammateBlocked = false; belief.fireGateReason = "no_target"
  belief.sprayFireFreezeSuppressed = false
  if belief.selfXy.isNone or belief.worldmap.isNil:
    state.aHeld = false; belief.leadBrads = 0; belief.throwChargeTicks = 0
    belief.throwTarget = none(Point); belief.throwReason = ""
    belief.throwEnemyCount = 0; belief.throwLiveTarget = false
    return Command(heldMask: 0)
  let selfXy = belief.selfXy.get
  let carrying = belief.iCarryHeartOf.isSome
  let sprayFreezeUnsafe = intent.suppressFireFreeze and
    belief.sprayNearestThreatDistancePx.isSome and
    belief.sprayNearestThreatDistancePx.get <= SprayLethalReachPx.float +
      FireWindupTicks.float * MaxSpeedPxTick + SprayFireFreezeMarginPx.float
  belief.sprayFireFreezeSuppressed = sprayFreezeUnsafe
  let rawOverride = if PeekDuck:
    belief.peekDuckOverride(intent) else: none(MicroOverride)
  let freeze = state.fireHoldTicks > 0 and not carrying and not sprayFreezeUnsafe
  if state.fireHoldTicks > 0: dec state.fireHoldTicks
  let arrived = intent.point.isSome and intent.arriveRadius > 0.0 and
    distance(selfXy, intent.point.get) <= intent.arriveRadius
  if belief.alive:
    if intent.point.isSome and not freeze and not arrived:
      noteProgress(belief.nav, selfXy)
    else:
      resetProgress(belief.nav, selfXy)
  var override = rawOverride
  if not freeze and override.isSome and override.get.destination.isSome and
      intent.kind != Hold and
      not belief.nav.withinCorridor(override.get.destination.get):
    inc belief.nav.microCorridorRejects
    belief.micro = ""
    override = none(MicroOverride)
  if freeze: discard
  elif override.isSome:
    mask = mask or override.get.mask
    if belief.alive:
      resetProgress(belief.nav, selfXy)
  elif intent.kind == NavigateTo and intent.point.isSome and not arrived:
    var waypoint = astarWaypoint(
      belief.nav, belief.worldmap, selfXy, intent.point.get,
      belief.planDanger, belief.tick, intent.movingGoal, intent.profile)
    if Squads and MicroFormationBias in intent.micro and not carrying:
      let bias = belief.formationBias
      if bias.isSome:
        let biased: Point = (int(waypoint.x.float + bias.get.x * NavCell.float * 3.0),
          int(waypoint.y.float + bias.get.y * NavCell.float * 3.0))
        if belief.worldmap.nudgeClear(selfXy, biased):
          if belief.nav.withinCorridor(biased):
            inc belief.squadCohesionTicks
            waypoint = biased
          else:
            inc belief.nav.microCorridorRejects
    mask = mask or octantToward(selfXy, waypoint)
  elif intent.kind == Hold and not carrying and MicroSeparation in intent.micro:
    let separation = belief.separationBias
    if separation.isSome:
      let step: Point = (int(selfXy.x.float + separation.get.x * NavCell.float * 2.0),
        int(selfXy.y.float + separation.get.y * NavCell.float * 2.0))
      if belief.worldmap.nudgeClear(selfXy, step):
        if belief.nav.withinCorridor(step):
          inc belief.squadCohesionTicks
          mask = mask or octantToward(selfXy, step)
        else:
          inc belief.nav.microCorridorRejects
  let selected = if Firefight and belief.firefightActive and not belief.iHaveArc:
    belief.selectTarget(belief.targetCandidates) else: none(TargetScore)
  let enemy = if belief.iHaveArc: belief.sprayTarget
    elif selected.isSome: some(selected.get.candidate.enemy)
    else: belief.nearestEnemy
  if enemy.isSome:
    let aim: tuple[pos: Point, lead: int] =
      if belief.iHaveArc: (belief.sprayAimPos(enemy.get), 0)
      elif selected.isSome: (selected.get.candidate.aimPos, selected.get.candidate.leadBrads)
      else: belief.leadAimPos(enemy.get)
    belief.leadBrads = aim.lead
    belief.aimTargetBrads = bradsOf((aim.pos.x-selfXy.x).float,
      (aim.pos.y-selfXy.y).float)
    let error = bradError(belief.aimTargetBrads, belief.aimBrads)
    belief.aimErrorBrads = error
    belief.targetRangePx = distance(aim.pos, selfXy)
    belief.aimLateralErrorPx = belief.targetRangePx * sin(
      abs(belief.aimErrorBrads).float / AimBradsTurn.float * 2.0 * PI)
    var canFire: bool
    if belief.iHaveArc:
      let contains = belief.sprayContains(aim.pos)
      belief.targetRayClear = contains
      belief.targetTeammateBlocked = belief.teammateBlocksShot(enemy.get.pos)
      canFire = belief.fireReady and contains and not belief.targetTeammateBlocked
      belief.fireGateReason = if not belief.fireReady: "cooldown"
        elif not contains: "arc_alignment"
        elif belief.targetTeammateBlocked: "teammate"
        else: "ready"
    else:
      let aimAligned = belief.fireGate(aim.pos)
      belief.targetRayClear = belief.worldmap.rayClear(selfXy, aim.pos)
      belief.targetTeammateBlocked = belief.teammateBlocksShot(aim.pos)
      if belief.fireReady and aimAligned and belief.targetRayClear and
          belief.targetTeammateBlocked and not state.aHeld:
        inc belief.friendlyFireSuppressed
      canFire = belief.fireReady and aimAligned and belief.targetRayClear and
        not belief.targetTeammateBlocked
      belief.fireGateReason = if not belief.fireReady: "cooldown"
        elif not aimAligned: "aim_alignment"
        elif not belief.targetRayClear: "wall"
        elif belief.targetTeammateBlocked: "teammate"
        else: "ready"
    if canFire and not state.aHeld:
      if not carrying and not sprayFreezeUnsafe:
        mask = mask and not MovementMask; state.fireHoldTicks = FireWindupTicks
      mask = mask or ButtonA; state.aHeld = true
      belief.fireGateReason = "fire"
      if not belief.iHaveArc:
        belief.firefightShotRangeCounts.inc(rangeBucket(distance(enemy.get.pos, selfXy)))
    else:
      if canFire and state.aHeld: belief.fireGateReason = "release"
      state.aHeld = false
      mask = mask or rotationButton(belief.aimTargetBrads, belief.aimBrads, state)
  else:
    state.aHeld = false; belief.leadBrads = 0
    let target = if override.isSome and override.get.aim.isSome:
      override.get.aim.get else: belief.sweepTarget
    belief.aimTargetBrads = target
    belief.aimErrorBrads = bradError(target, belief.aimBrads)
    mask = mask or rotationButton(belief.aimTargetBrads, belief.aimBrads, state)
  if intent.clampToEndzone and
      belief.worldmap.insideEndzone(belief.team, selfXy):
    var next = selfXy
    if (mask and ButtonLeft) != 0: next.x -= 4
    if (mask and ButtonRight) != 0: next.x += 4
    if (mask and ButtonUp) != 0: next.y -= 4
    if (mask and ButtonDown) != 0: next.y += 4
    if not belief.worldmap.insideEndzone(belief.team, next):
      mask = mask and not MovementMask
  if GrenadeThrow and belief.iHaveGrenade and
      (not carrying or belief.throwChargeTicks > 0):
    mask = grenadeOverlay(mask, belief, state)
  else:
    belief.throwChargeTicks = 0; belief.throwTarget = none(Point)
    belief.throwReason = ""; belief.throwEnemyCount = 0; belief.throwLiveTarget = false
  Command(heldMask: mask)
