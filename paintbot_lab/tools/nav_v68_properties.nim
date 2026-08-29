## Focused deterministic properties for the v68 bounded follower and watchdog.
##
## Run from the repository root:
##   nim c -r -d:release --path:paintbot_lab/paintbot/stencil_nim \
##     paintbot_lab/tools/nav_v68_properties.nim

import std/[options, tables]
import config, danger_field, nav, planner, strategy, types, worldmap

proc fixture(): WorldMap =
  const
    Width = 96
    Height = 64
  var walkable = newSeq[bool](Width * Height)
  for y in 1 ..< Height - 1:
    for x in 1 ..< Width - 1:
      walkable[y * Width + x] = true
  var markers = initTable[Team, EndzoneMarker]()
  markers[Red] = EndzoneMarker(
    shape: "box", x0: 4, y0: 8, x1: 28, y1: 56)
  markers[Blue] = EndzoneMarker(
    shape: "box", x0: 68, y0: 8, x1: 92, y1: 56)
  newWorldMap(walkable, Width, Height, 2, markers, Red)

proc corridorProperties() =
  var state = NavState(path: @[(8, 32), (32, 32), (56, 32)], cursor: 1)
  doAssert state.withinCorridor((32, 32))
  doAssert state.withinCorridor((32, 32 + FollowCorridorPx.int))
  # Today's normalized hold-separation step is approximately 16px perpendicular
  # to the route. The reviewed 20px default must preserve it.
  doAssert FollowCorridorPx == 20.0
  doAssert state.withinCorridor((32, 48))
  doAssert not state.withinCorridor((32, 53))

  state.cursor = 0
  doAssert state.withinCorridor((8, 48))
  state.cursor = state.path.high
  doAssert state.withinCorridor((56, 48))
  state.path = @[(32, 32)]
  state.cursor = 0
  doAssert state.withinCorridor((44, 44))
  doAssert not state.withinCorridor((47, 47))

  state.path.setLen(0)
  state.lastXy = some((32, 32))
  doAssert state.withinCorridor((48, 32))
  doAssert not state.withinCorridor((53, 32))
  state.lastXy = none(Point)
  doAssert not state.withinCorridor((32, 32))

proc watchdogProperties() =
  let map = fixture()
  var first, second: NavState
  for state in [addr first, addr second]:
    state[].stuckTicks = StuckTicks
    discard state[].astarWaypoint(
      map, (16, 32), (80, 32), DangerField(), tick = 10)
    doAssert state[].followReplans == 1
    doAssert state[].followStuckEvents == 0
    doAssert state[].blockedPenalty.isSome
    doAssert state[].blockedPenalty.get.untilTick == 10 + FollowBlockTtlTicks

    state[].stuckTicks = StuckTicks
    discard state[].astarWaypoint(
      map, (16, 32), (80, 32), DangerField(),
      tick = 10 + FollowStuckWindowTicks)
    doAssert state[].followReplans == 2
    doAssert state[].followStuckEvents == 1

  doAssert first.path == second.path
  doAssert first.followReplans == second.followReplans
  doAssert first.followStuckEvents == second.followStuckEvents
  doAssert first.blockedPenalty == second.blockedPenalty

  let expiry = first.blockedPenalty.get.untilTick
  discard first.astarWaypoint(
    map, (16, 32), (80, 32), DangerField(), tick = expiry)
  doAssert first.blockedPenalty.isNone

proc blockedPenaltyProperties() =
  let map = fixture()
  var baselinePlanner, avoidedPlanner: PlannerState
  let
    baseline = baselinePlanner.planPath(
      map, DangerField(), (16, 32), (80, 32))
    avoided = avoidedPlanner.planPath(
      map, DangerField(), (16, 32), (80, 32), avoid = some((48, 32)))
  doAssert baseline.path.len > 0 and avoided.path.len > 0
  doAssert baseline.path != avoided.path

proc arriveRadiusProperties() =
  doAssert makeIntent(NavigateTo, some((0, 0)), "barrage_center").arriveRadius ==
    BarrageCenterRadiusPx.float
  for reason in ["early_defense", "to_post", "to_hold"]:
    doAssert makeIntent(NavigateTo, some((0, 0)), reason).arriveRadius ==
      HoldArrivePx.float
  doAssert makeIntent(NavigateTo, some((0, 0)), "rejoin").arriveRadius == 40.0
  for reason in ["squad_move", "squad_to_watch", "squad_to_hold"]:
    doAssert makeIntent(NavigateTo, some((0, 0)), reason).arriveRadius ==
      (2 * HoldArrivePx).float
  for reason in ["carry_home", "steal", "clear_grenade", "clear_spray",
      "fetch_medkit", "intercept_thief", "convert_hunt", "escort_carrier",
      "arc_pursuit", "hunt_fallback"]:
    doAssert makeIntent(NavigateTo, some((0, 0)), reason).arriveRadius == 0.0

proc stationaryProgressProperties() =
  var state = NavState(lastXy: some((32, 32)), stuckTicks: StuckTicks)
  # Targetless Hold at a post and barrage-ring Hold both settle the baseline.
  state.resetProgress((32, 32))
  doAssert state.stuckTicks == 0 and state.lastXy == some((32, 32))
  # Fire windup uses the same reset even though the intent retains a target.
  state.stuckTicks = StuckTicks
  state.resetProgress((32, 32))
  doAssert state.stuckTicks == 0
  # Accepted moving and zero-mask ducks reset after their override fires.
  state.noteProgress((32, 32))
  state.resetProgress((32, 32))
  doAssert state.stuckTicks == 0
  # A rejected override does not reset; ordinary follower accountability stays.
  state.noteProgress((32, 32))
  doAssert state.stuckTicks == 1

corridorProperties()
watchdogProperties()
blockedPenaltyProperties()
arriveRadiusProperties()
stationaryProgressProperties()
echo "nav_v68_properties: corridor, watchdog, penalty, arrival, and stationarity passed"
