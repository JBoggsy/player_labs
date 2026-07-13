## expand_replay_json — emit a CTF replay's event timeline as JSONL for the warehouse.
##
## The game ships tools/expand_replay.nim, whose `main` prints a HUMAN timeline. This
## thin sibling reuses its public API (`expandReplayTimeline` + `jsonRow`) to emit one
## JSON object per event instead, so the event warehouse can ingest ground-truth game
## events (Kill / FlagSteal / FlagReturnHome / Capture / Respawn / ScoreChanged /
## PhaseChanged / GameOver) with tick + slot.
##
## It is built by ctf_lab/tools/build_expand_replay.sh, which stages it INTO the fetched
## game repo's tools/ dir (so the `../src/ctf/...` relative imports resolve) alongside the
## version-matched expand_replay it imports. Re-sim validates a per-tick hash, so it must
## be built at the SAME game ref that recorded the replay (a hash mismatch => bump CTF_REF).
##
## Usage:  expand_replay_json <replay.bitreplay>
##   stdout: one JSON row per event: {"ts": <tick>, "player": <slot>, "key": <event>, "value": {...}}
##   plus a trailing {"key":"_meta", "value":{tick_count, hash_failed, fail_tick}} line.
## Exit non-zero on a hash mismatch (after emitting the rows up to the failure).

import
  std/[json, os],
  ./expand_replay,
  ../src/ctf/replays

proc emitReplayJson(path: string) =
  if not fileExists(path):
    stderr.writeLine("expand_replay_json: replay file does not exist: " & path)
    quit(1)

  let data = loadReplay(path)
  let timeline = expandReplayTimeline(data)

  for event in timeline.events:
    echo $jsonRow(event)

  # Trailing meta row: lets the warehouse ingest detect a truncated / hash-failed
  # expansion instead of silently trusting a partial timeline.
  echo $(%*{
    "key": "_meta",
    "value": {
      "tick_count": timeline.tickCount,
      "hash_failed": timeline.hashFailed,
      "fail_tick": timeline.failTick,
    },
  })

  if timeline.hashFailed:
    stderr.writeLine("expand_replay_json: hash failed at tick " & $timeline.failTick &
      " (build ref does not match the replay's game version)")
    quit(2)

when isMainModule:
  if paramCount() < 1:
    stderr.writeLine("Usage: expand_replay_json <replay.bitreplay>")
    quit(1)
  emitReplayJson(paramStr(1))
