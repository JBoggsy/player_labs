## Offline byte-stream driver for Python-to-Nim differential tests.
##
## Input is the JSONL emitted by STENCIL_WIRE_RECORD.  Each inbound binary
## websocket message is applied to the native retained scene and produces one
## compact semantic decision record on stdout.

import std/[base64, json, options, os, strutils]
import policy, protocols, types, worldmap

proc pointJson(point: Point): JsonNode =
  %*[point.x, point.y]

proc pointJson(point: Option[Point]): JsonNode =
  if point.isSome: pointJson(point.get) else: newJNull()

proc heardJson(stencil: StencilPolicy): JsonNode =
  result = newJArray()
  for event in stencil.belief.heardEvents:
    result.add(%*{
      "kind": event.kind,
      "pos": pointJson(event.pos),
      "first": event.firstTick,
      "last": event.lastTick,
      "clear": stencil.belief.worldmap.rayClear(stencil.belief.selfXy.get, event.pos),
    })

proc replay(path: string, slot: int) =
  let
    client = initProtocolClient()
    stencil = newStencilPolicy(slot)
    diagnostic = getEnv("STENCIL_REPLAY_DIAG") == "1"
    quiet = getEnv("STENCIL_REPLAY_QUIET") == "1"
  if getEnv("STENCIL_REPLAY_BINARY") == "1":
    let input = open(path, fmRead)
    defer: input.close()
    var sizeBytes: array[4, uint8]
    while input.readBuffer(addr sizeBytes[0], 4) == 4:
      let size = int(sizeBytes[0]) or int(sizeBytes[1]) shl 8 or
        int(sizeBytes[2]) shl 16 or int(sizeBytes[3]) shl 24
      var packet = newString(size)
      if size > 0 and input.readBuffer(addr packet[0], size) != size:
        raise newException(IOError, "truncated binary replay packet")
      if not client.applyFrame(packet):
        raise newException(ValueError, "malformed binary replay packet")
      discard stencil.decide(client)
    return
  var tick = 0
  for line in lines(path):
    let event = parseJson(line)
    if event["direction"].getStr != "in" or event["type"].getStr != "binary":
      continue
    let packet = decode(event["data"].getStr)
    if not client.applyFrame(packet):
      raise newException(ValueError, "malformed captured Sprite-v1 packet")
    let command = stencil.decide(client)
    inc tick
    let belief = stencil.belief
    if quiet:
      continue
    if not diagnostic:
      echo $(%*{
        "tick": tick,
        "mask": command.heldMask.int,
        "chat": command.chat,
      })
      continue
    echo $(%*{
      "tick": tick,
      "mask": command.heldMask.int,
      "chat": command.chat,
      "team": belief.team.teamName,
      "seat": belief.seat,
      "role": $belief.role,
      "alive": belief.alive,
      "self": pointJson(belief.selfXy),
      "aim": belief.aimBrads,
      "intent_reason": stencil.lastIntent.reason,
      "intent_point": pointJson(stencil.lastIntent.point),
      "flow_goal": pointJson(stencil.lastFlowGoal),
      "hold_point": pointJson(belief.holdPoint),
      "defensive_post": pointJson(belief.defensivePost),
      "defensive_post_duck": pointJson(belief.defensivePostDuck),
      "nav_goal": pointJson(belief.nav.goal),
      "nav_cursor": belief.nav.cursor,
      "nav_stuck": belief.nav.stuckTicks,
      "sweep_offset": belief.sweepOffset,
      "sweep_dir": belief.sweepDir,
      "micro": belief.micro,
      "enemies": belief.enemies.len,
      "teammates": belief.teammates.len,
      "under_fire": belief.underFire,
      "firefight": belief.firefightActive,
      "a_held": stencil.actionState.aHeld,
      "fire_hold": stencil.actionState.fireHoldTicks,
      "heard": heardJson(stencil),
    })

when isMainModule:
  if paramCount() notin 1 .. 2:
    quit("usage: replay WIRE.jsonl [SLOT]", 2)
  let slot = if paramCount() == 2: parseInt(paramStr(2)) else: 0
  replay(paramStr(1), slot)
