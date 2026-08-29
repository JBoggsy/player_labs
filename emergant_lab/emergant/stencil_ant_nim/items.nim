## Discovered item spawns and objective-relative pickup convenience.

import std/[algorithm, math, options, tables]
import belief_state, config, types, worldmap

const SpawnMatchPx = 24.0

proc floorModFloat(value, modulus: float): float =
  value - floor(value / modulus) * modulus

proc itemKind(name: string): ItemKind =
  case name
  of "grenade": Grenade
  of "medkit": Medkit
  of "shield": Shield
  of "arc": Arc
  else: raise newException(ValueError, "unknown item kind: " & name)

proc respawnTicks(kind: ItemKind): int =
  case kind
  of Grenade: GrenadeRespawnTicks
  of Medkit: MedkitRespawnTicks
  of Shield: ShieldRespawnTicks
  of Arc: ArcRespawnTicks

proc inView(belief: Belief, pos: Point): bool =
  let dx = pos.x - belief.selfXy.get.x
  let dy = pos.y - belief.selfXy.get.y
  if hypot(dx.float, dy.float) <= VisionBubble.float:
    return true
  let wanted = arctan2(-dy.float, dx.float) / (2.0 * PI) * AimBradsTurn.float
  let error = abs(floorModFloat(
    wanted - belief.aimBrads.float + AimBradsTurn.float / 2.0,
    AimBradsTurn.float) - AimBradsTurn.float / 2.0)
  if error > GuaranteedVisionConeHalfDeg.float / 360.0 * AimBradsTurn.float:
    return false
  belief.worldmap.rayClear(belief.selfXy.get, pos)

proc updateItems*(belief: Belief, percept: EmergAntState) =
  let tick = belief.tick
  var confirmed = newSeq[bool](belief.itemSpawns.len)
  for visible in percept.visibleItems:
    let kind = itemKind(visible.kind)
    var matched = -1
    for index, spawn in belief.itemSpawns:
      if spawn.kind == kind and
          hypot((visible.pos.x - spawn.pos.x).float,
                (visible.pos.y - spawn.pos.y).float) <= SpawnMatchPx:
        matched = index
        break
    if matched >= 0:
      belief.itemSpawns[matched].present = true
      belief.itemSpawns[matched].lastSeen = tick
      confirmed[matched] = true
    else:
      belief.itemSpawns.add(ItemSpawn(
        kind: kind, pos: visible.pos, present: true, lastSeen: tick))
      confirmed.add(true)
  if belief.alive and belief.selfXy.isSome and not belief.worldmap.isNil:
    for index in 0 ..< belief.itemSpawns.len:
      if not confirmed[index] and belief.inView(belief.itemSpawns[index].pos):
        belief.itemSpawns[index].present = false
        belief.itemSpawns[index].absentUntil = tick +
          respawnTicks(belief.itemSpawns[index].kind)
  for spawn in belief.itemSpawns.mitems:
    if not spawn.present and tick >= spawn.absentUntil:
      spawn.present = true

proc alreadyHave(belief: Belief, kind: ItemKind): bool =
  (kind == Grenade and belief.iHaveGrenade) or
    (kind == Shield and ShieldAwareness and belief.iHaveShield) or
    (kind == Arc and belief.iHaveArc)

proc threshold(kind: ItemKind): float =
  case kind
  of Arc: ItemArcDetourPx.float
  of Medkit: MedkitConvenientDetourPx.float
  else: ItemConvenientDetourPx.float

proc closerVisibleTeammate(
  belief: Belief, spawn: ItemSpawn, selfRoute: float
): bool =
  for teammate in belief.teammates:
    let route = belief.worldmap.routeDistance(teammate.pos, spawn.pos)
    if route + ItemYieldMarginPx.float < selfRoute:
      return true
    if abs(route - selfRoute) <= ItemYieldMarginPx.float and
        teammate.pos < belief.selfXy.get:
      return true

proc evaluateFetch*(
  belief: Belief, anchor: Point, anchorKind: string
): Option[ItemOption] =
  belief.itemOptions.setLen(0)
  belief.itemChoice = none(ItemOption)
  if belief.selfXy.isNone or belief.worldmap.isNil or belief.itemSpawns.len == 0:
    return none(ItemOption)
  let directRoute = belief.worldmap.routeDistance(belief.selfXy.get, anchor)
  for spawnIndex, spawn in belief.itemSpawns:
    if not spawn.present or belief.alreadyHave(spawn.kind):
      continue
    if spawn.kind == Medkit and (belief.hpPips.isNone or belief.hpPips.get >= 3):
      continue
    let routeToItem = belief.worldmap.routeDistance(belief.selfXy.get, spawn.pos)
    let routeViaItem = routeToItem + belief.worldmap.routeDistance(spawn.pos, anchor)
    let detour = max(0.0, routeViaItem - directRoute)
    let limit = threshold(spawn.kind)
    var
      accepted = false
      reason: string
    if spawn.kind == Arc and routeToItem > ItemPickupRange.float:
      reason = "tactics_not_ready"
    elif belief.closerVisibleTeammate(spawn, routeToItem):
      reason = "closer_teammate"
    elif detour <= limit:
      accepted = true
      reason = "convenient"
    else:
      reason = "too_far"
    belief.itemOptions.add(ItemOption(
      spawnIndex: spawnIndex, anchor: anchor, anchorKind: anchorKind,
      routeToItemPx: routeToItem, routeViaItemPx: routeViaItem,
      directRoutePx: directRoute, detourPx: detour, thresholdPx: limit,
      accepted: accepted, reason: reason))
    belief.itemOptionTicks.inc($spawn.kind)
    belief.itemReasonTicks.inc(reason)
  if belief.itemOptions.len == 0:
    return none(ItemOption)
  inc belief.itemOpportunityTicks
  var accepted: seq[ItemOption]
  for option in belief.itemOptions:
    if option.accepted: accepted.add(option)
  if accepted.len > 0:
    accepted.sort(proc(a, b: ItemOption): int =
      result = cmp(a.detourPx, b.detourPx)
      if result == 0: result = cmp(a.routeToItemPx, b.routeToItemPx)
      if result == 0:
        result = cmp(belief.itemSpawns[a.spawnIndex].kind,
          belief.itemSpawns[b.spawnIndex].kind))
    belief.itemChoice = some(accepted[0])
    inc belief.itemFetchTicks
  else:
    belief.itemOptions.sort(proc(a, b: ItemOption): int =
      result = cmp(a.detourPx, b.detourPx)
      if result == 0: result = cmp(a.routeToItemPx, b.routeToItemPx)
      if result == 0:
        result = cmp(belief.itemSpawns[a.spawnIndex].kind,
          belief.itemSpawns[b.spawnIndex].kind))
    belief.itemChoice = some(belief.itemOptions[0])
    if belief.itemChoice.get.reason == "closer_teammate":
      inc belief.itemYieldTicks
  belief.itemChoice

proc medkitTarget*(belief: Belief, maxDistancePx: float): Option[int] =
  if belief.hpPips.isNone or belief.hpPips.get >= 3 or belief.selfXy.isNone or
      belief.itemSpawns.len == 0:
    return none(int)
  var bestDistance = maxDistancePx
  for index, spawn in belief.itemSpawns:
    if spawn.kind != Medkit or not spawn.present:
      continue
    let distance = hypot((spawn.pos.x - belief.selfXy.get.x).float,
                         (spawn.pos.y - belief.selfXy.get.y).float)
    if distance <= bestDistance:
      result = some(index)
      bestDistance = distance

proc arrived*(selfXy: Point, spawn: ItemSpawn): bool =
  hypot((selfXy.x - spawn.pos.x).float, (selfXy.y - spawn.pos.y).float) <=
    ItemPickupRange.float
