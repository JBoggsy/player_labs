## The single-objective movement priority ladder.

import std/[math, options, sets, tables]
import belief_state, config, items, squads, types, worldmap

type Objective* = object
  intent*: Intent
  flowGoal*: Option[Point]

proc distance(a, b: Point): float = hypot((a.x - b.x).float, (a.y - b.y).float)

proc navigate(point: Point, reason: string, flow = none(Point)): Objective =
  Objective(intent: Intent(kind: NavigateTo, point: some(point), reason: reason),
    flowGoal: flow)

proc hold(reason: string): Objective =
  Objective(intent: Intent(kind: Hold, point: none(Point), reason: reason),
    flowGoal: none(Point))

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
