import std/[os, strutils, options, times]
import ../src/ctf/[replays, sim, sim_state, sim_config, sim_types]
import ../src/shell/[body, body_map, body_nav, body_planner, episode, types]

let full = parseCtfReplayBytesFull(readFile(paramStr(1)))
var config = defaultGameConfig()
config.update(full.replay.configJson)
var world = initSimServer(config)
world.gameEventLoggingEnabled = false
let map = newBodyMap(world.gameMap)
echo "grid=", map.gridWidth, "x", map.gridHeight, " components=", map.componentCount
var nav = newBodyNavSystem(map, 1, 1300)

proc planCost(start, goal: BodyPoint) =
  let validated = map.validateGoal(goal, start)
  if validated.isNone:
    echo "plan ", start, " -> ", goal, ": goal did not validate"
    return
  let g = validated.get
  nav.replacePlan(0, 1, start, g)
  let t0 = cpuTime()
  var ticks = 0
  while nav.seats[0].job.planPending and ticks < 20000:
    discard nav.runPlanningTick(ticks)
    inc ticks
  let job = nav.seats[0].job
  echo "plan ", start, " -> ", g.goalPoint, " dist=", abs(goal.x - start.x) + abs(goal.y - start.y),
    ": stage=", job.stage, " ticks=", ticks, " work=", job.workUnits, " astar=", job.astarExpansions,
    " pathLen=", nav.seats[0].planner.resultLen, " ms=", int((cpuTime() - t0) * 1000)

planCost((1589, 320), (1489, 320))
planCost((1589, 320), (1389, 320))
planCost((1589, 320), (1189, 420))
planCost((1589, 320), (881, 500))
planCost((2034, 981), (881, 500))
planCost((335, 753), (881, 500))
planCost((829, 1001), (829, 953))
