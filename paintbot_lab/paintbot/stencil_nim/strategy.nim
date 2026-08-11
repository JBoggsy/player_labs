## The single-objective movement priority ladder.

import std/[math, options, sets, tables]
import belief_state, config, items, squads, types, worldmap

type Objective* = object
  intent*: Intent
  flowGoal*: Option[Point]

type SprayThreat = tuple[track: PlayerTrack, pos: Point, raw, effective: float]

proc distance(a, b: Point): float = hypot((a.x - b.x).float, (a.y - b.y).float)

proc navigate(point: Point, reason: string, flow = none(Point)): Objective =
  Objective(intent: Intent(kind: NavigateTo, point: some(point), reason: reason),
    flowGoal: flow)

proc hold(reason: string): Objective =
  Objective(intent: Intent(kind: Hold, point: none(Point), reason: reason),
    flowGoal: none(Point))

proc coverageAt*(
  belief: Belief, point: Point, cache: var Table[int, float]
): float =
  let
    map = belief.worldmap
    cell = map.cellOf(point)
    key = cell.y * map.gridW + cell.x
  if cache.hasKey(key):
    return cache[key]
  let coneHalfBrads = GuaranteedVisionConeHalfDeg.float /
    360.0 * AimBradsTurn.float

  proc contribution(pos: Point, aim: Option[int], weight: float): float =
    if aim.isNone:
      return 0.0
    let
      dx = point.x - pos.x
      dy = point.y - pos.y
      range = hypot(dx.float, dy.float)
    if range > PostGunRangePx.float:
      return 0.0
    let
      wanted = arctan2(-dy.float, dx.float) /
        (2.0 * PI) * AimBradsTurn.float
      error = abs(floorMod(
        pyRound(wanted - aim.get.float + AimBradsTurn.float / 2.0),
        AimBradsTurn) - AimBradsTurn div 2).float
    if error > coneHalfBrads or not map.rayClear(pos, point):
      return 0.0
    weight

  var covered = 0.0
  for ally in belief.teammates:
    if ally.weapon == WeaponGun:
      covered = max(covered, contribution(ally.pos, ally.aimBrads, 1.0))
  for track in belief.teammateTracks:
    if track.weapon != WeaponGun or
        belief.tick - track.lastTick > SprayCoverTrackTtlTicks:
      continue
    let weight = if track.source == TrackVisual and track.lastTick == belief.tick:
      1.0 else: SprayCoverTrackDiscount
    covered = max(covered, contribution(
      belief.projectedTrackPos(track), track.aimBrads, weight))
  cache[key] = covered
  covered

proc updateSprayFleeLatch(belief: Belief): seq[SprayThreat] =
  belief.sprayThreatCount = 0
  belief.sprayNearestThreatDistancePx = none(float)
  belief.sprayFleeChoice = none(SprayFleeScore)
  if not SprayAvoid or belief.selfXy.isNone or
      (ShieldAwareness and belief.iHaveShield):
    belief.sprayFleeActive = false
    return

  for track in belief.enemyTracks:
    if track.weapon != WeaponSpray or
        belief.tick - track.lastTick > SprayThreatTtlTicks:
      continue
    let
      pos = belief.projectedTrackPos(track)
      rawDistance = distance(belief.selfXy.get, pos)
      sourcePad = if track.source == TrackTeamShout:
        SprayShoutThreatPadPx.float else: 0.0
    result.add((track, pos, rawDistance, rawDistance - sourcePad))
  belief.sprayThreatCount = result.len
  if result.len == 0:
    belief.sprayFleeActive = false
    return

  var nearestIndex = 0
  for index in 1 ..< result.len:
    if result[index].effective < result[nearestIndex].effective:
      nearestIndex = index
  belief.sprayNearestThreatDistancePx = some(result[nearestIndex].raw)
  if belief.sprayFleeActive:
    if result[nearestIndex].effective > SprayFleeReleasePx.float:
      belief.sprayFleeActive = false
  elif result[nearestIndex].effective <= SprayFleeTriggerPx.float:
    belief.sprayFleeActive = true

proc sprayFleeObjective(
  belief: Belief, threats: openArray[SprayThreat]
): Option[Objective] =
  if not belief.sprayFleeActive:
    return none(Objective)

  let
    selfXy = belief.selfXy.get
    map = belief.worldmap
  var
    best = none(SprayFleeScore)
    coverageCache: Table[int, float]
  for directionIndex in 0 ..< 16:
    let angle = directionIndex.float / 16.0 * 2.0 * PI
    for ring in 1 .. 2:
      let candidate: Point = (
        pyRound(selfXy.x.float + cos(angle) * (SprayFleeStepPx * ring).float),
        pyRound(selfXy.y.float + sin(angle) * (SprayFleeStepPx * ring).float))
      if not map.segmentClear(selfXy, candidate):
        continue
      var nearestThreat = Inf
      for threat in threats:
        nearestThreat = min(nearestThreat, distance(candidate, threat.pos))
      let threatGain = clamp(
        nearestThreat / SprayFleeReleasePx.float, 0.0, 1.0)
      var
        coverageSum = 0.0
        coverageWeight = 0.0
        maxNearbyAllies = 0
      for sampleIndex in 1 .. SprayCoverSamples:
        let
          ratio = sampleIndex.float / SprayCoverSamples.float
          sample: Point = (
            pyRound(selfXy.x.float + (candidate.x - selfXy.x).float * ratio),
            pyRound(selfXy.y.float + (candidate.y - selfXy.y).float * ratio))
          weight = 1.0 + (SprayCoverFarBias - 1.0) *
            (sampleIndex - 1).float / (SprayCoverSamples - 1).float
        coverageSum += belief.coverageAt(sample, coverageCache) * weight
        coverageWeight += weight
        var nearbyAllies = 0
        for ally in belief.teammates:
          if distance(sample, ally.pos) <= SprayClumpRadiusPx.float:
            inc nearbyAllies
        maxNearbyAllies = max(maxNearbyAllies, nearbyAllies)
      let
        coverPath = coverageSum / coverageWeight
        clumpRisk = clamp(
          maxNearbyAllies.float / SprayClumpNormAllies.float, 0.0, 1.0)
        centerTerm =
          if belief.barrage.isSome and belief.barrage.get.depth > 0:
            clamp(1.0 - distance(candidate, map.center) /
              BarrageCenterRadiusPx.float, 0.0, 1.0)
          else:
            0.0
        score = SprayThreatWeight * threatGain + SprayCoverWeight * coverPath -
          SprayClumpWeight * clumpRisk + SprayCenterWeight * centerTerm
        candidateScore = SprayFleeScore(
          point: candidate, score: score, threatGain: threatGain,
          coverPath: coverPath, clumpRisk: clumpRisk, centerTerm: centerTerm)
      if best.isNone or score > best.get.score:
        best = some(candidateScore)
  if best.isSome:
    belief.sprayFleeChoice = best
    inc belief.sprayFleeTicks
    return some(navigate(best.get.point, "clear_spray"))

  var nearestIndex = 0
  for index in 1 ..< threats.len:
    if threats[index].effective < threats[nearestIndex].effective:
      nearestIndex = index
  let
    nearest = threats[nearestIndex].pos
    dx = selfXy.x - nearest.x
    dy = selfXy.y - nearest.y
    norm = max(distance(selfXy, nearest), 1.0)
    fallback: Point = (
      pyRound(selfXy.x.float + dx.float / norm * SprayFleeStepPx.float),
      pyRound(selfXy.y.float + dy.float / norm * SprayFleeStepPx.float))
  if map.segmentClear(selfXy, fallback):
    inc belief.sprayFleeTicks
    return some(navigate(fallback, "clear_spray"))
  inc belief.sprayFleeTicks
  some(hold("clear_spray"))

proc stealGoal(belief: Belief): Option[Point] =
  if belief.worldmap.isNil or belief.stealTarget.isNone:
    return none(Point)
  let target = belief.stealTarget.get
  if belief.hearts.hasKey(target):
    let heart = belief.hearts[target]
    if heart.planted and heart.pos.isSome:
      return heart.pos
  some(belief.worldmap.pedestal(target))

proc itemAnchor(belief: Belief): tuple[pos: Point, kind: string] =
  if belief.order.isSome and belief.tick - belief.order.get.setTick <= OrderTtlTicks:
    return (belief.order.get.directive.pos, "order")
  if belief.role == Defender and belief.holdPoint.isSome:
    return (belief.holdPoint.get, "role")
  let steal = belief.stealGoal
  if steal.isSome: (steal.get, "role") else: (belief.worldmap.center, "role")

proc decideObjective*(belief: Belief): Objective =
  let map = belief.worldmap
  if map.isNil:
    return hold("no_worldmap")
  let sprayThreats = belief.updateSprayFleeLatch

  belief.squadOrderPostActive = false
  belief.squadOrderPost = none(Point)
  belief.squadOrderPostDuck = none(Point)
  belief.squadOrderPostSightlineAim = none(Point)
  belief.squadOrderPostOpponent = none(Team)
  belief.squadOrderPostScore = 0.0

  if EarlyDefense and not belief.earlyDefenseComplete and
      belief.everyEnemyTrailsLives:
    belief.earlyDefenseComplete = true

  if SquadCommand and (not EarlyDefense or belief.earlyDefenseComplete):
    belief.updateConsensus()

  if belief.iCarryHeartOf.isSome:
    let home = map.capturePoint(belief.team)
    return navigate(home, "carry_home", some(home))

  if belief.ownHeartStolen:
    if belief.ownHeartThiefPos.isSome:
      return navigate(belief.ownHeartThiefPos.get, "intercept_thief")
    if belief.thiefFix.isSome:
      return navigate(belief.thiefFix.get.pos, "intercept_thief_heard")

  if belief.selfXy.isSome:
    for warning in belief.grenadeWarnings:
      let distanceFromGrenade = distance(belief.selfXy.get, warning.pos)
      if distanceFromGrenade < GrenadeWarnClearPx.float:
        let dx = belief.selfXy.get.x - warning.pos.x
        let dy = belief.selfXy.get.y - warning.pos.y
        let norm = max(distanceFromGrenade, 1.0)
        return navigate((
          int(belief.selfXy.get.x.float + dx.float / norm * GrenadeWarnClearPx.float),
          int(belief.selfXy.get.y.float + dy.float / norm * GrenadeWarnClearPx.float)),
          "clear_grenade")

  let sprayFlee = belief.sprayFleeObjective(sprayThreats)
  if sprayFlee.isSome:
    return sprayFlee.get

  if BarrageCentering and belief.barrage.isSome and
      belief.barrage.get.depth > 0 and belief.selfXy.isSome:
    inc belief.barrageCenterTicks
    if distance(belief.selfXy.get, map.center) <= BarrageCenterRadiusPx.float:
      return hold("barrage_center")
    return navigate(map.center, "barrage_center", some(map.center))

  if EarlyDefense and not belief.earlyDefenseComplete and belief.selfXy.isSome:
    if belief.earlyDefensePoint.isNone:
      belief.earlyDefensePoint = some(map.spawnCoverPoint(
        belief.team, belief.seat, belief.seatsPerTeam))
    let point = belief.earlyDefensePoint.get
    if distance(belief.selfXy.get, point) <= HoldArrivePx.float:
      return hold("early_defense")
    return navigate(point, "early_defense", some(point))

  if SquadCommand and belief.rejoinUntil >= 0 and belief.selfXy.isSome:
    if belief.tick >= belief.rejoinUntil or belief.inSquadContact:
      belief.rejoinUntil = -1
      belief.rejoinPoint = none(Point)
    elif belief.rejoinPoint.isSome:
      inc belief.rejoinTicks
      if distance(belief.selfXy.get, belief.rejoinPoint.get) > 40.0:
        return navigate(belief.rejoinPoint.get, "rejoin")
      return hold("rejoin_hold")

  if belief.role == Attacker and belief.iCarryHeartOf.isNone:
    for color in belief.colors:
      if color == belief.team or color in belief.heartsRetired or
          not belief.hearts.hasKey(color):
        continue
      let heart = belief.hearts[color]
      if not heart.planted and heart.carriedPos.isSome:
        return navigate(heart.carriedPos.get, "escort_carrier")
    if belief.carrierFix.isSome:
      let fix = belief.carrierFix.get
      let elapsed = min(belief.tick - fix.heardTick, 48)
      let angle = fix.heading.float * PI / 4.0
      return navigate((
        int(fix.pos.x.float + cos(angle) * 1.9 * elapsed.float),
        int(fix.pos.y.float - sin(angle) * 1.9 * elapsed.float)),
        "escort_carrier_heard")

  if belief.selfXy.isSome and Items:
    let kit = belief.medkitTarget(MedkitConvenientDetourPx.float)
    if kit.isSome:
      return navigate(belief.itemSpawns[kit.get].pos, "fetch_medkit")
    let anchor = belief.itemAnchor
    let choice = belief.evaluateFetch(anchor.pos, anchor.kind)
    if choice.isSome and choice.get.accepted:
      return navigate(belief.itemSpawns[choice.get.spawnIndex].pos, "fetch_item")

  if belief.wipeInReach and belief.selfXy.isSome:
    if not belief.converting:
      belief.converting = true
      inc belief.convertEvents
    return navigate(belief.convertHuntPoint, "convert_hunt")
  belief.converting = false

  if SquadCommand and belief.order.isSome and belief.selfXy.isSome and
      belief.tick - belief.order.get.setTick <= OrderTtlTicks:
    let directive = belief.order.get.directive
    var orderPos = belief.spreadPoint(directive.pos)
    let post = belief.orderPost(directive)
    if post.isSome:
      let selected = post.get
      orderPos = selected.pos
      belief.squadOrderPostActive = true
      belief.squadOrderPost = some(selected.pos)
      belief.squadOrderPostDuck = some(selected.duck)
      belief.squadOrderPostOpponent = some(directive.opponent)
      belief.squadOrderPostScore = selected.score
      if selected.rayEnds.len > 0:
        belief.squadOrderPostSightlineAim = some(
          selected.rayEnds[selected.rayEnds.len div 2])
    let arrived = distance(belief.selfXy.get, orderPos) <= HoldArrivePx.float * 2.0
    if arrived and not belief.orderArrived:
      belief.orderArrived = true
      inc belief.orderArrivals
    inc belief.orderFollowTicks
    case directive.kind
    of 'M':
      inc belief.orderMoveTicks
      if arrived:
        return hold("squad_move_arrived")
      return navigate(orderPos, "squad_move")
    of 'W':
      inc belief.orderWatchTicks
      if arrived:
        return hold("squad_watch")
      return navigate(orderPos, "squad_to_watch")
    of 'H':
      inc belief.orderHoldTicks
      if arrived:
        return hold("squad_hold")
      return navigate(orderPos, "squad_to_hold")
    else:
      discard

  if belief.role == Defender and belief.holdPoint.isSome:
    let usingPost = belief.defensivePost.isSome
    if belief.selfXy.isSome and
        distance(belief.selfXy.get, belief.holdPoint.get) <= HoldArrivePx.float:
      if usingPost:
        inc belief.defensivePostHoldTicks
        return hold("hold_post")
      return hold("hold_line")
    if usingPost:
      inc belief.defensivePostTravelTicks
      return navigate(belief.holdPoint.get, "to_post", belief.holdPoint)
    return navigate(belief.holdPoint.get, "to_hold", belief.holdPoint)

  let steal = belief.stealGoal
  if steal.isNone:
    return navigate(belief.convertHuntPoint, "hunt_fallback")
  # _should_wait is intentionally false in the Python policy.
  navigate(steal.get, "steal", steal)
