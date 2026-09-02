import std/[os, strutils, options, times, sequtils]
import bitworld/spriteprotocol
import ../src/ctf/[replays, sim, sim_state, sim_config, sim_types]
import ../src/shell/[body, body_map, body_nav, body_planner, episode, reflexes, standing_order, types]

let seatCount = parseInt(paramStr(2))
let full = parseCtfReplayBytesFull(readFile(paramStr(1)))
var config = defaultGameConfig()
config.update(full.replay.configJson)
var world = initSimServer(config)
world.gameEventLoggingEnabled = false
var player = initReplayPlayer(full)
player.looping = false
# Walk the replay to the first Playing tick to get real spawn positions.
while player.playing and world.phase != Playing:
  player.stepReplay(world)
echo "phase=", world.phase, " tick=", world.tickCount, " players=", world.players.len
var spawns: seq[BodyPoint]
for i in 0 ..< min(seatCount, world.players.len):
  spawns.add((world.players[i].x, world.players[i].y))

proc shrinkTimer(elapsed: int): int =
  var remaining = max(0, elapsed)
  for phase in config.zonePhases:
    if remaining < phase.waitTicks: return phase.waitTicks - remaining
    remaining -= phase.waitTicks
    if remaining < phase.shrinkTicks: return 0
    remaining -= phase.shrinkTicks
  high(int) div 4

let map = newBodyMap(world.gameMap)
var controls = newSeq[SlotControl]()
var teams = newSeq[Team]()
for i in 0 ..< seatCount:
  controls.add(scPlay)
  teams.add(config.slots[i].team)
var ep = initFirstLightEpisode(true, true, controls, map, 1300, teams, "br", 6)

proc inRect(p: BodyPoint, r: MapRect): bool =
  p.x >= r.x and p.x < r.x + r.w and p.y >= r.y and p.y < r.y + r.h

proc frameFor(seat: int, pos: BodyPoint, cur, next: MapRect, ticks, dps: int): FirstLightSeatFrame =
  FirstLightSeatFrame(
    seat: uint8(seat), playerIndex: seat, present: true, playing: true,
    alive: true, aliveTeams: 8, motionScale: MotionScale, velocity: MaxSpeed,
    bodyInputs: BodyTickInputs(
      self: BodySelfState(pos: pos, hp: 4, hpFrac: 1.0, aimBrads: 32,
        alive: true, carrying: false)),
    defaultFallbacks: BrDefaultFallbacks(
      currentZone: cur, nextZone: next,
      ticksToNextShrink: ticks, zoneDps: dps,
      idleAimCenterBrads: 32, coverGoal: none(ValidatedGoal)))

var pos = spawns
var lastMask = newSeq[int](seatCount)

proc dumpSeat(i: int, t: int) =
  let sb = ep.seats[i].body
  let ns = ep.nav.seats[i]
  var goalTxt = "none"
  var comp = -2
  if sb.standingGoal.isSome:
    let g = sb.standingGoal.get.goalPoint
    goalTxt = $g
    comp = map.componentOf(g)
  echo "  t=", t, " seat=", i, " pos=", pos[i], " comp=", map.componentOf(pos[i]),
    " intent=", sb.standingIntent.kind, " reason=", sb.standingIntent.reason,
    " goal=", goalTxt, " goalComp=", comp,
    " stage=", ns.job.stage, " work=", ns.job.workUnits, " astar=", ns.job.astarExpansions,
    " pathLen=", ns.pathLen, " cursor=", ns.cursor, " revision=", ns.revision, " pathRev=", ns.pathRevision,
    " stuck=", ns.stuckTicks, " desired=", ns.desiredGoal, " blocked=", ns.blockedPenalty.isSome, " mask=", lastMask[i]
var firstMove = newSeq[int](seatCount)
var moveTicks = newSeq[int](seatCount)
var firstOutside = newSeq[int](seatCount)
var outsideStill = newSeq[int](seatCount)
var reflexInstalls = newSeq[int](seatCount)
var playInstalls = newSeq[int](seatCount)
for i in 0 ..< seatCount: (firstMove[i] = -1; firstOutside[i] = -1)
let started = cpuTime()
let ticksTotal = parseInt(paramStr(3))
let dumpSeatIndex = (if paramCount() >= 4: parseInt(paramStr(4)) else: 5)
var shown = 0
for t in 1 .. ticksTotal:
  let z = world.zoneRectAndDps(t)
  let ticks = shrinkTimer(t)
  var frames: seq[FirstLightSeatFrame]
  for i in 0 ..< seatCount: frames.add(frameFor(i, pos[i], z.cur, z.next, ticks, z.dps))
  let output = ep.step(frames, uint32(t))
  for inst in output.installs:
    let i = int(inst.seat)
    if i >= seatCount: continue
    if inst.provenance.startsWith("reflex"): inc reflexInstalls[i] else: inc playInstalls[i]
    if i == 5 and shown < 8:
      echo "install t=", t, " seat=5 rule=", inst.rule, " prov=", inst.provenance
      inc shown
  var moved = newSeq[bool](seatCount)
  for m in output.masks:
    let bits = m.input.encodeInputMask()
    let i = m.playerIndex
    if i < 0 or i >= seatCount: continue
    lastMask[i] = int(bits)
    if (bits and (ButtonUp or ButtonDown or ButtonLeft or ButtonRight)) != 0:
      moved[i] = true
      inc moveTicks[i]
      if firstMove[i] < 0: firstMove[i] = t
      var next = pos[i]
      if (bits and ButtonLeft) != 0: dec next.x, 4
      if (bits and ButtonRight) != 0: inc next.x, 4
      if (bits and ButtonUp) != 0: dec next.y, 4
      if (bits and ButtonDown) != 0: inc next.y, 4
      if map.canStand(next): pos[i] = next
      elif map.canStand((next.x, pos[i].y)): pos[i] = (next.x, pos[i].y)
      elif map.canStand((pos[i].x, next.y)): pos[i] = (pos[i].x, next.y)
  if t >= 1148 and t <= 1168 and dumpSeatIndex < seatCount:
    dumpSeat(dumpSeatIndex, t)
  for i in 0 ..< seatCount:
    if not inRect(pos[i], z.cur):
      if firstOutside[i] < 0: firstOutside[i] = t
      if not moved[i]: inc outsideStill[i]
echo "components=", map.componentCount, " grid=", map.gridWidth, "x", map.gridHeight
for i in 0 ..< seatCount: dumpSeat(i, ticksTotal)
echo "seats=", seatCount, " ticks=", ticksTotal, " cpu_ms=", int((cpuTime() - started) * 1000)
for i in 0 ..< seatCount:
  echo "seat ", i, " spawn=", spawns[i], " firstOutside=", firstOutside[i], " firstMove=", firstMove[i],
    " moveTicks=", moveTicks[i], " outsideStillTicks=", outsideStill[i],
    " reflexInstalls=", reflexInstalls[i], " playInstalls=", playInstalls[i],
    " moved=", abs(pos[i].x - spawns[i].x) + abs(pos[i].y - spawns[i].y)
ep.closeFirstLightEpisode()
