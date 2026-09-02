import std/[os, strutils, json, algorithm]
import ../src/ctf/replays, ../src/ctf/sim, ../src/ctf/sim_state, ../src/ctf/sim_config, ../src/ctf/sim_types

let full = parseCtfReplayBytesFull(readFile(paramStr(1)))
var config = defaultGameConfig()
config.update(full.replay.configJson)
var world = initSimServer(config)
world.gameEventLoggingEnabled = false
var player = initReplayPlayer(full)
let recorded = full.replay.hashes[0].hash
echo "recorded tick=", full.replay.hashes[0].tick, " hash=", recorded
echo "tick0 hash=", world.gameHash(), " tickCount=", world.tickCount
player.stepReplay(world)
let got = world.gameHash()
echo "tick1 hash=", got, " tickCount=", world.tickCount, " match=", got == recorded
echo "phase=", world.phase, " winner=", world.winner, " gameOverTimer=", world.gameOverTimer,
  " gameStartTick=", world.gameStartTick, " startWaitTimer=", world.startWaitTimer,
  " timeLimitReached=", world.timeLimitReached, " barrageStartTick=", world.barrageStartTick,
  " zonePhases=", config.zonePhases.len, " zoneCenter=", world.zoneCenter,
  " zoneCenterConfigured=", config.zoneCenterConfigured,
  " isDraw=", world.isDraw, " numAgents=", config.numAgents, " nextJoinOrder=", world.nextJoinOrder,
  " players=", world.players.len, " map=", world.gameMap.width, "x", world.gameMap.height
for team in world.teams():
  echo "flag ", team, " x=", world.flags[team].x, " y=", world.flags[team].y, " carrier=", world.flags[team].carrier, " captured=", world.flags[team].captured
echo "spawns grenade=", world.grenadeSpawns.len, " med=", world.medKitSpawns.len, " shield=", world.shieldSpawns.len, " spray=", world.sprayPaintSpawns.len,
  " airborne=", world.airborneGrenades.len, " floorPaint=", config.floorPaint, " allowPolicyReflash=", config.allowPolicyReflash
var keys: seq[string]
for k, v in parseJson(full.replay.configJson): keys.add(k)
keys.sort()
echo "configKeys(", keys.len, ")=", keys.join(",")


proc report2(label: string) =
  let h = world.gameHash()
  echo (if h == recorded: "FOUND " else: "no    "), label, " hash=", h

report2("baseline")
world.config.numAgents = 1; report2("numAgents=1 (needsReregister unhashed)"); world.config.numAgents = 0
world.needsReregister = true; world.config.numAgents = 1; report2("numAgents=1 rr=true"); world.config.numAgents = 0; world.needsReregister = false
let savedPhases = world.config.zonePhases
world.config.zonePhases = @[]; report2("zonePhases empty"); world.config.zonePhases = savedPhases
world.config.floorPaint = true; report2("floorPaint=true"); world.config.floorPaint = false
world.config.allowPolicyReflash = true; report2("allowPolicyReflash=true"); world.config.allowPolicyReflash = false
let savedTeams = world.config.teams
for n in [2, 3, 4, 6, 8, 16]:
  world.config.teams = n
  report2("teams=" & $n)
world.config.teams = savedTeams
world.config.numAgents = 1
world.config.zonePhases = @[]
report2("numAgents=1 + zonePhases empty")
world.config.zonePhases = savedPhases; world.config.numAgents = 0
world.barrageStartTick = 0; world.barrageAccum = 0; report2("barrage armed 0/0"); world.barrageStartTick = -1
echo "done"
