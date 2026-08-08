## Extract one player's held Sprite-v1 input-mask change points.
## The CTF replay input-record schema is stable across the studied eras, so
## unlike rendered observations this does not need the exact game simulator.
## Usage: extract_replay_actions <replay> <game-version> <player-index> <output.jsonl>
import std/[json, os, strutils]
import bitworld/replays

const
  ReplayFps = 24
  CtfReplaySpecTemplate = ReplaySpec(
    magic: "COWLDCTF",
    formatVersion: 1'u16,
    gameName: "ctf",
    joinKind: rjkNameSlotToken,
    allowChat: true,
    allowCompressed: true,
    hashOrder: rhoStop,
  )

proc main() =
  if paramCount() != 4:
    quit("usage: extract_replay_actions <replay> <game-version> <player-index> <output.jsonl>")
  let
    replayPath = paramStr(1).absolutePath()
    gameVersion = paramStr(2)
    playerIndex = parseInt(paramStr(3))
    outputPath = paramStr(4).absolutePath()
  var spec = CtfReplaySpecTemplate
  spec.gameVersion = gameVersion
  let data = loadReplay(replayPath, spec)

  createDir(outputPath.parentDir())
  let output = open(outputPath, fmWrite)
  defer: output.close()
  var tick = 0
  for input in data.inputs:
    if int(input.player) == playerIndex:
      while tickTime(tick, ReplayFps) < input.time:
        inc tick
      output.writeLine($( %*{
        "tick": tick,
        "mask": int(input.keys),
      }))

main()
