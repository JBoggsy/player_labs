## expand_replay_json — emit a CTF replay's event timeline as JSONL for the warehouse.
##
## Runs its own re-sim loop (the same counter-diffing pattern as tools/expand_replay.nim,
## which the game ships) so every event can be enriched with LIVE sim state at the tick
## it happened — positions, aim, hp, carried items — which the human-timeline tool's
## position-less events cannot provide. Also emits a periodic `pos` snapshot row per
## player (every PosEvery ticks) plus per-flag `flag_pos` rows, so the warehouse can
## answer spatial questions (where kills happen, carrier paths, territory control).
##
## It is built by ctf_lab/tools/build_expand_replay.sh, which stages it INTO the fetched
## game repo's tools/ dir (so the `../src/ctf/...` relative imports resolve). Re-sim
## validates a per-tick hash, so it must be built at the SAME game ref that recorded the
## replay (a hash mismatch => bump CTF_REF).
##
## Usage:  expand_replay_json <replay.bitreplay>
##   stdout: one JSON row per event: {"ts": <tick>, "player": <slot>, "key": <event>, "value": {...}}
##   plus a trailing {"key":"_meta", "value":{tick_count, hash_failed, fail_tick}} line.
## Exit non-zero on a hash mismatch (after emitting the rows up to the failure).

import
  std/[json, os, strutils],
  ../src/ctf/replays,
  ../src/ctf/sim

const
  GameDir = currentSourcePath().parentDir().parentDir()

var posEvery = 30          ## ticks between periodic position snapshots
                           ## (CLI arg 2; the replay viewer bundles use 1)
var emitWalkability = false  ## viewer-only startup geometry (CLI arg 3)

type
  TrackState = object
    alive: seq[bool]
    kills: seq[int]
    deaths: seq[int]
    captures: seq[int]
    rewards: seq[int]
    shotsFired: seq[int]
    shotsHit: seq[int]

proc slotOf(sim: SimServer, i: int): int =
  ## A player's stable join slot (the identity the warehouse re-keys on).
  if i >= 0 and i < sim.players.len:
    return sim.players[i].joinOrder
  -1

proc labelOf(sim: SimServer, i: int): string =
  let p = sim.players[i]
  teamText(p.team) & " " & playerColorText(p.color) & "(" & p.address & ")"

proc emitRow(tick, slot: int, key: string, value: JsonNode) =
  echo $(%*{"ts": tick, "player": slot, "key": key, "value": value})

proc walkabilityValue(sim: SimServer): JsonNode =
  ## The exact startup walkability sprite, encoded as blocked x/length runs.
  ## The viewer consumes walls, so emitting blocked runs avoids expanding the
  ## full RGBA sprite or a width*height JSON boolean array.
  var rows = newJArray()
  for y in 0 ..< sim.gameMap.height:
    var
      runs: seq[int]
      x = 0
    while x < sim.gameMap.width:
      let index = y * sim.gameMap.width + x
      if index >= sim.walkMask.len or not sim.walkMask[index]:
        let start = x
        while x < sim.gameMap.width:
          let runIndex = y * sim.gameMap.width + x
          if runIndex < sim.walkMask.len and sim.walkMask[runIndex]:
            break
          inc x
        runs.add(start)
        runs.add(x - start)
      else:
        inc x
    rows.add(%runs)
  %*{
    "encoding": "wall-runs-v1",
    "w": sim.gameMap.width,
    "h": sim.gameMap.height,
    "rows": rows,
  }

proc richValue(event: SimEvent): JsonNode =
  result = %*{
    "action_id": event.actionId,
    "weapon": event.weapon,
    "heading_brads": event.headingBrads,
    "heading_degrees": event.headingBrads.float * 360.0 / AimBradsTurn.float,
    "x": event.x,
    "y": event.y,
    "distance": event.distance,
  }
  case event.kind
  of GrenadeThrow, GrenadeImpact, Pickup:
    result["item"] = %event.item
  of ShoutEvent:
    result["content"] = %event.content
  else:
    discard
  if event.kind in {ShotImpact, GrenadeImpact, SprayUse}:
    result["damages"] = newJArray()
    for damage in event.damages:
      result["damages"].add %*{
        "slot": damage.slot,
        "amount": damage.amount,
        "hp": damage.hp,
        "blocked": damage.blocked,
      }

proc emitRichEvents(events: openArray[SimEvent]) =
  for event in events:
    let key =
      case event.kind
      of GunTrigger: "gun_trigger"
      of Shot: "gun_fire"
      of ShotImpact: "shot_impact"
      of GrenadeThrow: "grenade_throw"
      of GrenadeImpact: "grenade_impact"
      of SprayUse: "spray_use"
      of Pickup: "item_pickup"
      of ShoutEvent: "shout"
      else: continue
    emitRow(event.tick, event.source, key, event.richValue())

proc posValue(p: Player): JsonNode =
  ## Live state snapshot for one player (map pixels; aim in brads 0..255 CCW-from-east).
  %*{
    "x": p.x, "y": p.y, "aim": p.aimBrads, "alive": p.alive, "hp": p.hp,
    "carry": p.carryingFlag, "shield": p.hasShield, "grenade": p.hasGrenade,
    "arc": p.hasPlasmaArc,
  }

proc killerThisTick(sim: SimServer, track: TrackState): int =
  ## The single player whose kill count just rose this tick, or -1 when none or
  ## SEVERAL did (the sim cannot attribute simultaneous kills — never guess).
  result = -1
  var killerCount = 0
  for i, player in sim.players:
    if i < track.kills.len and player.kills > track.kills[i]:
      inc killerCount
      result = i
  if killerCount > 1:
    result = -1

proc emitReplayJson(path: string) =
  if not fileExists(path):
    stderr.writeLine("expand_replay_json: replay file does not exist: " & path)
    quit(1)

  let data = loadReplay(path)
  var config = defaultGameConfig()
  config.update(data.configJson)

  let previousDir = getCurrentDir()
  setCurrentDir(GameDir)

  var
    sim = initSimServer(config)
    replay = initReplayPlayer(data)
    track: TrackState
    phase = sim.phase
    prevCarriers: array[Team, int]
    tickCount = 0
    hashFailed = false
    failTick = -1
  for team in Team:
    prevCarriers[team] = sim.flags[team].carrier

  sim.gameEventLoggingEnabled = false
  sim.collectEvents = true
  replay.looping = false
  replay.mismatchQuit = true

  if emitWalkability:
    emitRow(0, -1, "walkability_map", walkabilityValue(sim))

  while replay.playing:
    let tick = sim.tickCount + 1
    tickCount = tick
    try:
      replay.stepReplay(sim)
    except ReplayError:
      hashFailed = true
      failTick = tick
      break

    emitRichEvents(sim.events)
    sim.events.setLen(0)

    # Phase transitions + game over.
    if phase != sim.phase:
      emitRow(tick, -1, "phase", %*{"phase": $sim.phase})
      if sim.phase == GameOver:
        var v = %*{"draw": sim.isDraw}
        if not sim.isDraw:
          v["winner"] = %teamText(sim.winner)
        emitRow(tick, -1, "game_over", v)
      phase = sim.phase

    # Newly joined players.
    while track.alive.len < sim.players.len:
      let i = track.alive.len
      track.alive.add(sim.players[i].alive)
      track.kills.add(sim.players[i].kills)
      track.deaths.add(sim.players[i].deaths)
      track.captures.add(sim.players[i].captures)
      track.rewards.add(sim.players[i].reward)
      track.shotsFired.add(sim.players[i].shotsFired)
      track.shotsHit.add(sim.players[i].shotsHit)
      emitRow(tick, sim.slotOf(i), "player_joined", %*{"label": sim.labelOf(i)})

    # Shots + hits, with the shooter's live position/aim.
    for i, p in sim.players:
      if p.shotsFired > track.shotsFired[i]:
        emitRow(tick, sim.slotOf(i), "shot", %*{"x": p.x, "y": p.y, "aim": p.aimBrads})
      if p.shotsHit > track.shotsHit[i]:
        emitRow(tick, sim.slotOf(i), "hit", %*{"x": p.x, "y": p.y, "aim": p.aimBrads})
      track.shotsFired[i] = p.shotsFired
      track.shotsHit[i] = p.shotsHit

    # Kills / respawns, with both parties' positions.
    let killer = sim.killerThisTick(track)
    for i, p in sim.players:
      if p.deaths > track.deaths[i]:
        var v = %*{
          "victim_slot": sim.slotOf(i), "victim_label": sim.labelOf(i),
          "victim_x": p.x, "victim_y": p.y,
        }
        if killer >= 0:
          v["killer_x"] = %sim.players[killer].x
          v["killer_y"] = %sim.players[killer].y
        emitRow(tick, if killer >= 0: sim.slotOf(killer) else: -1, "kill", v)
      elif p.alive and not track.alive[i]:
        emitRow(tick, sim.slotOf(i), "respawn", %*{"x": p.x, "y": p.y})
      track.alive[i] = p.alive
      track.kills[i] = p.kills
      track.deaths[i] = p.deaths

    # Flag steals / returns (diff each flag's carrier), with the thief's position.
    for team in Team:
      let carrier = sim.flags[team].carrier
      if carrier != prevCarriers[team]:
        if prevCarriers[team] >= 0:
          emitRow(tick, -1, "flag_return_home", %*{"flag": teamText(team)})
        if carrier >= 0:
          let p = sim.players[carrier]
          emitRow(tick, sim.slotOf(carrier), "flag_steal",
                  %*{"flag": teamText(team), "x": p.x, "y": p.y})
        prevCarriers[team] = carrier

    # Captures, with the capturer's position.
    for i, p in sim.players:
      if p.captures > track.captures[i]:
        var captured = ""
        for team in sim.teams():
          if sim.flags[team].carrier == i:
            captured = teamText(team)
        doAssert captured.len > 0, "capture event with no carried flag"
        emitRow(tick, sim.slotOf(i), "capture",
                %*{"flag": captured, "x": p.x, "y": p.y})
      track.captures[i] = p.captures

    # Score changes.
    for i, p in sim.players:
      if p.reward != track.rewards[i]:
        emitRow(tick, sim.slotOf(i), "score", %*{"amount": p.reward - track.rewards[i]})
        track.rewards[i] = p.reward

    # Periodic spatial snapshots: every player + both flags.
    if tick mod posEvery == 0:
      for i, p in sim.players:
        emitRow(tick, sim.slotOf(i), "pos", posValue(p))
      for team in Team:
        let f = sim.flags[team]
        emitRow(tick, -1, "flag_pos", %*{
          "flag": teamText(team), "x": f.x, "y": f.y,
          "carrier_slot": if f.carrier >= 0: sim.slotOf(f.carrier) else: -1,
        })

  setCurrentDir(previousDir)

  # Trailing meta row: lets the warehouse ingest detect a truncated / hash-failed
  # expansion instead of silently trusting a partial timeline.
  echo $(%*{
    "key": "_meta",
    "value": {
      "tick_count": tickCount,
      "hash_failed": hashFailed,
      "fail_tick": failTick,
    },
  })

  if hashFailed:
    stderr.writeLine("expand_replay_json: hash failed at tick " & $failTick &
      " (build ref does not match the replay's game version)")
    quit(2)

when isMainModule:
  if paramCount() < 1:
    stderr.writeLine(
      "Usage: expand_replay_json <replay.bitreplay> [pos_every] [walkability]")
    quit(1)
  if paramCount() >= 2:
    posEvery = max(1, parseInt(paramStr(2)))
  if paramCount() >= 3:
    emitWalkability = paramStr(3) == "walkability"
  emitReplayJson(paramStr(1))
