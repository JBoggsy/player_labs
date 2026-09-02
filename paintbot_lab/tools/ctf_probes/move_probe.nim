import std/[os, strutils, math]
import ../src/ctf/replays, ../src/ctf/sim, ../src/ctf/sim_state, ../src/ctf/sim_config, ../src/ctf/sim_types

let full = parseCtfReplayBytesFull(readFile(paramStr(1)))
var config = defaultGameConfig()
config.update(full.replay.configJson)
var world = initSimServer(config)
world.gameEventLoggingEnabled = false
var player = initReplayPlayer(full)
player.looping = false
player.mismatchQuit = true
var dist = newSeq[float](MaxPlayers)
var movingTicks = newSeq[int](MaxPlayers)
var aliveTicks = newSeq[int](MaxPlayers)
var lastX = newSeq[int](MaxPlayers)
var lastY = newSeq[int](MaxPlayers)
var playingTicks = 0
var outsideTicks = newSeq[int](MaxPlayers)
var firstOutside = newSeq[int](MaxPlayers)
var deathTick = newSeq[int](MaxPlayers)
var deathOutside = newSeq[bool](MaxPlayers)
var wasAlive = newSeq[bool](MaxPlayers)
for i in 0 ..< MaxPlayers: (firstOutside[i] = -1; deathTick[i] = -1)
var firstPlaying = -1
while player.playing:
  player.stepReplay(world)
  if world.phase != Playing: continue
  if firstPlaying < 0: firstPlaying = world.tickCount
  inc playingTicks
  let zr = world.zoneRectAndDps(world.tickCount - world.gameStartTick).cur
  for i, p in world.players:
    if i >= MaxPlayers: break
    let px = p.x + CollisionW div 2
    let py = p.y + CollisionH div 2
    let inside = px >= zr.x and px <= zr.x + zr.w - 1 and py >= zr.y and py <= zr.y + zr.h - 1
    if p.alive and not inside:
      inc outsideTicks[i]
      if firstOutside[i] < 0: firstOutside[i] = world.tickCount
    if wasAlive[i] and not p.alive and deathTick[i] < 0:
      deathTick[i] = world.tickCount
      deathOutside[i] = not inside
    wasAlive[i] = p.alive
  for i, p in world.players:
    if i >= MaxPlayers: break
    if aliveTicks[i] > 0:
      let d = abs(p.x - lastX[i]) + abs(p.y - lastY[i])
      if p.alive and d > 0:
        dist[i] += float(d)
        inc movingTicks[i]
    if p.alive: inc aliveTicks[i]
    lastX[i] = p.x; lastY[i] = p.y
echo "hashOk=", not player.hashValidationFailed, " playingTicks=", playingTicks, " firstPlaying=", firstPlaying, " players=", world.players.len
for i in 0 ..< world.players.len:
  var name = ""
  for j in full.replay.joins:
    if int(j.player) == i: name = j.name
  echo "cog ", i, " team=", world.players[i].team, " name=", name, " aliveTicks=", aliveTicks[i],
    " movingTicks=", movingTicks[i], " movingPct=", (if aliveTicks[i] > 0: 100 * movingTicks[i] div aliveTicks[i] else: 0),
    " dist=", int(dist[i]), " kills=", world.players[i].kills, " deaths=", world.players[i].deaths, " outsideTicks=", outsideTicks[i], " firstOutside=", firstOutside[i], " deathTick=", deathTick[i], " deadOutsideZone=", deathOutside[i]
