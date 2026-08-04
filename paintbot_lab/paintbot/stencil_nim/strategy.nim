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
    return (belief.order.get.pos, "order")
  if belief.role == Defender and belief.holdPoint.isSome:
    return (belief.holdPoint.get, "role")
  let steal = belief.stealGoal
  if steal.isSome: (steal.get, "role") else: (belief.worldmap.center, "role")

proc decideObjective*(belief: Belief): Objective =
  let map = belief.worldmap
  if map.isNil:
    return hold("no_worldmap")

  if SquadCommand:
    belief.updatePresence()
    belief.leadSquad()

  if belief.iCarryHeartOf.isSome:
    let home = map.capturePoint(belief.team)
    return navigate(home, "carry_home", some(home))

  if SquadCommand and belief.rejoinUntil >= 0 and belief.selfXy.isSome:
    if belief.tick >= belief.rejoinUntil or belief.inSquadContact:
      belief.rejoinUntil = -1
      belief.rejoinPoint = none(Point)
    elif belief.rejoinPoint.isSome:
      inc belief.rejoinTicks
      if distance(belief.selfXy.get, belief.rejoinPoint.get) > 40.0:
        return navigate(belief.rejoinPoint.get, "rejoin")
      return hold("rejoin_hold")

  if belief.ownHeartStolen:
    if belief.ownHeartThiefPos.isSome:
      return navigate(belief.ownHeartThiefPos.get, "intercept_thief")
    if belief.thiefFix.isSome:
      return navigate(belief.thiefFix.get.pos, "intercept_thief_heard")

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

  if belief.selfXy.isSome and Items:
    let kit = belief.medkitTarget(MedkitConvenientDetourPx.float)
    if kit.isSome:
      return navigate(belief.itemSpawns[kit.get].pos, "fetch_medkit")
    let anchor = belief.itemAnchor
    let choice = belief.evaluateFetch(anchor.pos, anchor.kind)
    if choice.isSome and choice.get.accepted:
      return navigate(belief.itemSpawns[choice.get.spawnIndex].pos, "fetch_item")

  if SquadCommand and belief.order.isSome and belief.selfXy.isSome:
    var order = belief.order.get
    if belief.tick - order.setTick > OrderTtlTicks:
      if belief.wipeInReach:
        belief.order = some(('T', belief.convertHuntPoint, belief.tick))
        belief.orderSource = "convert"
      else:
        belief.order = some(('H', belief.decayHoldPoint, belief.tick))
        belief.orderSource = "decay"
      order = belief.order.get
    var orderPos = order.pos
    if order.goal in {'H', 'S', 'P'}:
      orderPos = belief.spreadPoint(orderPos)
    case order.goal
    of 'H', 'S':
      if distance(belief.selfXy.get, orderPos) <= HoldArrivePx.float * 2.0:
        return hold("order_hold")
      return navigate(orderPos, "order_to_hold")
    of 'P':
      if distance(belief.selfXy.get, orderPos) <= HoldArrivePx.float * 2.0:
        return hold("order_push_arrived")
      return navigate(orderPos, "order_push")
    of 'T': return navigate(orderPos, "order_hunt")
    of 'F':
      let steal = belief.stealGoal
      if steal.isSome: return navigate(steal.get, "steal", steal)
    else: discard

  if belief.wipeInReach and belief.selfXy.isSome:
    if not belief.converting:
      belief.converting = true
      inc belief.convertEvents
    return navigate(belief.convertHuntPoint, "convert_hunt")
  belief.converting = false

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
