## Replay one historical CTF recording and emit one player's Sprite-v1 input.
##
## Compile this file against the exact coworld-ctf source revision that produced
## the replay, then run it from that checkout's root so its recorded config and
## assets are interpreted by the matching simulator.
##
## Usage: extract_replay_wire <replay> <player-index> <output.jsonl>
import
  std/[base64, json, os, strutils],
  ctf/[global, replays, sim]

proc bytesToString(bytes: openArray[uint8]): string =
  result = newString(bytes.len)
  if bytes.len > 0:
    copyMem(result[0].addr, bytes[0].unsafeAddr, bytes.len)

proc main() =
  if paramCount() != 3:
    quit("usage: extract_replay_wire <replay> <player-index> <output.jsonl>")

  let
    replayPath = paramStr(1).absolutePath()
    playerIndex = parseInt(paramStr(2))
    outputPath = paramStr(3).absolutePath()
    data = loadReplay(replayPath)

  var
    config = defaultGameConfig()
    replay = initReplayPlayer(data)
    viewerState: PlayerViewerState
    nextState: PlayerViewerState
  config.update(data.configJson)
  var sim = initSimServer(config)
  sim.gameEventLoggingEnabled = false
  replay.looping = false
  replay.mismatchQuit = true

  createDir(outputPath.parentDir())
  let output = open(outputPath, fmWrite)
  defer: output.close()

  while replay.playing:
    replay.stepReplay(sim)
    let fullPacket = sim.buildSpriteProtocolPlayerUpdates(
      playerIndex,
      viewerState,
      nextState,
    )
    let packet =
      when compiles(fullPacket.stripSpritePixels()):
        fullPacket.stripSpritePixels()
      else:
        fullPacket
    viewerState = nextState
    output.writeLine($( %*{
      "direction": "in",
      "type": "binary",
      "tick": sim.tickCount,
      "player_index": playerIndex,
      "data": encode(bytesToString(packet)),
    }))

  if replay.hashValidationFailed:
    quit("replay hash validation failed at tick " & $replay.hashMismatchTick)

main()
