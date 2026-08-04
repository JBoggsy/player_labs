## Structured diagnostics and player-artifact delivery.
## Telemetry is isolated from gameplay: failures are reported and swallowed.

import std/[json, math, options, os, sequtils, sets, strutils, tables]
import curly, zippy/ziparchives
import belief_state, config, policy, types, worldmap

type
  OutputKind = enum
    JsonlFile, JsonlStdout, JsonlStderr, JsonlArtifact

  TraceOutput = ref object
    kind: OutputKind
    file: File
    ownsFile: bool
    member: string
    records: seq[string]

  TraceState* = ref object
    outputs: seq[TraceOutput]
    artifactUrl: string
    enabled: bool
    lastAlive: Option[bool]
    lastIntent: Option[string]
    lastCarry: Option[Team]
    carryInitialized: bool
    lastWorldSignature: Option[tuple[width, height, teams: int]]
    navigationFieldKeys: HashSet[int]

proc pointJson(point: Option[Point]): JsonNode =
  if point.isSome: %*[point.get.x, point.get.y] else: newJNull()

proc teamJson(team: Option[Team]): JsonNode =
  if team.isSome: %teamName(team.get) else: newJNull()

proc roleName(role: Role): string =
  if role == Attacker: "attacker" else: "defender"

proc countJson(counts: CountTable[string]): JsonNode =
  result = newJObject()
  for key, value in counts:
    result[key] = %value

proc rounded4(value: float): float =
  pyRound(value * 10_000.0).float / 10_000.0

proc pointJson(point: Point): JsonNode = %*[point.x, point.y]

proc boolRows(values: openArray[bool], width: int): JsonNode =
  result = newJArray()
  for y in 0 ..< values.len div width:
    var row = newString(width)
    for x in 0 ..< width:
      row[x] = if values[y * width + x]: '1' else: '0'
    result.add(%row)

proc hopRows(values: openArray[uint8], width: int): JsonNode =
  result = newJArray()
  for y in 0 ..< values.len div width:
    var row = newString(width)
    for x in 0 ..< width:
      row[x] = char(ord('0') + values[y * width + x].int)
    result.add(%row)

proc distanceRows(values: openArray[float], width: int): JsonNode =
  result = newJArray()
  for y in 0 ..< values.len div width:
    var row = newJArray()
    for x in 0 ..< width:
      let distance = values[y * width + x]
      row.add(if classify(distance) == fcInf: newJNull() else: %rounded4(distance))
    result.add(row)

proc navigationMap(map: WorldMap): JsonNode =
  var teams = newJArray()
  for index in 0 ..< map.teams:
    let color = Team(index)
    var entry = %*{
      "team": teamName(color),
      "home_center": pointJson(map.homeCenter(color)),
      "capture": pointJson(map.capturePoint(color)),
      "choke": pointJson(map.chokePoint(color)),
      "rally": pointJson(map.rallyPoint(color)),
      "spawn_aim_brads": map.spawnAim(color),
    }
    if map.endzones.hasKey(color):
      let zone = map.endzones[color]
      entry["endzone"] = %*{
        "shape": zone.shape,
        "box": [zone.x0, zone.y0, zone.x1, zone.y1],
      }
    if map.pedestals.hasKey(color):
      entry["pedestal"] = pointJson(map.pedestals[color])
    teams.add(entry)
  var fronts = newJArray()
  for front in map.postFronts:
    var candidates = newJArray()
    for candidate in front.candidates:
      candidates.add(%*{
        "position": pointJson(candidate.pos),
        "duck": pointJson(candidate.duck),
        "score": rounded4(candidate.score),
        "sightline": rounded4(candidate.sightline),
        "corridor": rounded4(candidate.corridor),
        "duck_contrast": rounded4(candidate.duckContrast),
      })
    var posts = newJArray()
    for post in front.posts:
      var rays = newJArray()
      for endpoint in post.rayEnds: rays.add(pointJson(endpoint))
      posts.add(%*{
        "position": pointJson(post.pos),
        "duck": pointJson(post.duck),
        "score": rounded4(post.score),
        "sightline": rounded4(post.sightline),
        "corridor": rounded4(post.corridor),
        "duck_contrast": rounded4(post.duckContrast),
        "ray_ends": rays,
      })
    fronts.add(%*{
      "team": teamName(front.team),
      "opponent": teamName(front.opponent),
      "candidates": candidates,
      "posts": posts,
    })
  %*{
    "schema_version": 2,
    "map": [map.width, map.height],
    "grid": [map.gridW, map.gridH],
    "cell_size": NavCell,
    "center": pointJson(map.center),
    "walkable_rows": boolRows(map.walkable, map.gridW),
    "cover_rows": boolRows(map.cover, map.gridW),
    "teams": teams,
    "post_fronts": fronts,
  }

proc navigationFlow(field: CachedRouteField, map: WorldMap): JsonNode =
  %*{
    "schema_version": 1,
    "goal_cell": pointJson(field.goalCell),
    "goal": pointJson(cellCenter(field.goalCell)),
    "distance_cells": distanceRows(field.distances, map.gridW),
    "hop_rows": hopRows(field.hops, map.gridW),
  }

proc navMetrics(map: WorldMap): JsonNode =
  var total = 0.0
  var maximum = 0.0
  for elapsed in map.dijkstraMs:
    total += elapsed
    maximum = max(maximum, elapsed)
  var walkable = 0
  for value in map.walkable:
    if value: inc walkable
  %*{
    "base_ms": map.baseInitMs,
    "erode_ms": map.erodeMs,
    "cover_ms": map.coverMs,
    "post_ms": map.postMs,
    "dijkstra_count": map.dijkstraMs.len,
    "dijkstra_total_ms": total,
    "dijkstra_max_ms": maximum,
    "total_ms": map.baseInitMs + total + map.postMs,
    "decode_ms": 0.0,
    "map_pixels": map.width * map.height,
    "grid_cells": map.gridW * map.gridH,
    "walkable_cells": walkable,
  }

proc snapshot(policy: StencilPolicy, command: Command): JsonNode =
  let belief = policy.belief
  var retired = newJArray()
  for color in Team:
    if color in belief.heartsRetired: retired.add(%teamName(color))
  var scores = newJObject()
  for color, score in belief.teamScores:
    scores[teamName(color)] = %*[score.kills, score.deaths]
  var world = newJNull()
  if not belief.worldmap.isNil:
    let map = belief.worldmap
    world = %*{
      "w": map.width,
      "h": map.height,
      "teams": map.teams,
      "seats_per_team": belief.seatsPerTeam,
      "grid": [map.gridW, map.gridH],
      "nav_init": navMetrics(map),
    }
  result = %*{
    "tick": policy.tick,
    "team": teamName(belief.team),
    "seat": belief.seat,
    "slot": belief.slot,
    "role": roleName(belief.role),
    "defensive_post": pointJson(belief.defensivePost),
    "defensive_post_duck": pointJson(belief.defensivePostDuck),
    "defensive_post_sightline_aim": pointJson(belief.defensivePostSightlineAim),
    "defensive_post_opponent": teamJson(belief.defensivePostOpponent),
    "defensive_post_score": rounded4(belief.defensivePostScore),
    "defensive_post_heart_distance": belief.defensivePostHeartDistance,
    "defensive_post_forward": belief.defensivePostForward,
    "alive": belief.alive,
    "self_xy": pointJson(belief.selfXy),
    "aim_brads": belief.aimBrads,
    "aim_target_brads": belief.aimTargetBrads,
    "aim_error_brads": belief.aimErrorBrads,
    "aim_grid_error_brads": belief.aimBrads mod AimStepBrads,
    "aim_slot_error_brads": belief.aimSlotErrorBrads,
    "aim_lateral_error_px": rounded4(belief.aimLateralErrorPx),
    "target_range_px": rounded4(belief.targetRangePx),
    "fire_ready": belief.fireReady,
    "fire_gate_reason": belief.fireGateReason,
    "target_ray_clear": belief.targetRayClear,
    "target_teammate_blocked": belief.targetTeammateBlocked,
    "intent": policy.lastIntent.reason,
    "intent_point": pointJson(policy.lastIntent.point),
    "flow_goal": pointJson(policy.lastFlowGoal),
    "micro": belief.micro,
    "carrying": teamJson(belief.iCarryHeartOf),
    "steal_target": teamJson(belief.stealTarget),
    "own_heart_stolen": belief.ownHeartStolen,
    "hearts_retired": retired,
    "enemies_visible": belief.enemies.len,
    "teammates_visible": belief.teammates.len,
    "enemy_tracks": belief.enemyTracks.len,
    "hp_pips": (if belief.hpPips.isSome: %belief.hpPips.get else: newJNull()),
    "have": {
      "grenade": belief.iHaveGrenade,
      "shield": belief.iHaveShield,
      "arc": belief.iHaveArc,
    },
    "team_scores": scores,
    "firefight_active": belief.firefightActive,
    "converting": belief.converting,
    "under_fire": belief.underFire,
    "worldmap": world,
    "mask": int(command.heldMask),
    "chat": (if command.chat.len > 0: %command.chat else: newJNull()),
  }
  if belief.danger.len > 0:
    var total = 0.0
    var maximum = 0.0
    var count = 0
    let map = belief.worldmap
    for y in countup(0, map.gridH - 1, DangerTraceDownsample):
      for x in countup(0, map.gridW - 1, DangerTraceDownsample):
        let value = belief.danger[y * map.gridW + x].float
        total += value
        maximum = max(maximum, value)
        inc count
    result["danger_mean"] = %rounded4(total / count.float)
    result["danger_max"] = %rounded4(maximum)

proc counters(policy: StencilPolicy): JsonNode =
  let b = policy.belief
  %*{
    "friendly_fire_suppressed": b.friendlyFireSuppressed,
    "aim_resyncs": b.aimResyncs,
    "firing_turns": b.firingTurns,
    "firefight_ticks_total": b.firefightTicksTotal,
    "firefight_engagements": b.firefightEngagements,
    "firefight_target_switches": b.firefightTargetSwitches,
    "focus_claims_sent": b.focusClaimsSent,
    "focus_claims_heard": b.focusClaimsHeard,
    "focus_claims_suppressed": b.focusClaimsSuppressed,
    "shots_by_range": countJson(b.firefightShotRangeCounts),
    "targets_by_range": countJson(b.firefightTargetRangeCounts),
    "grenade_starts": countJson(b.grenadeTargetStarts),
    "grenade_releases": countJson(b.grenadeTargetReleases),
    "grenade_safety_vetoes": b.grenadeSafetyVetoes,
    "chat_sent": countJson(b.chatSentCounts),
    "chat_heard": countJson(b.chatHeardCounts),
    "item_fetch_ticks": b.itemFetchTicks,
    "item_yield_ticks": b.itemYieldTicks,
    "convert_events": b.convertEvents,
    "defensive_post_travel_ticks": b.defensivePostTravelTicks,
    "defensive_post_hold_ticks": b.defensivePostHoldTicks,
    "defensive_post_fallbacks": b.defensivePostFallbacks,
    "spray_pursuit_ticks": b.sprayPursuitTicks,
  }

proc write(output: TraceOutput, record: JsonNode) =
  let line = $record
  case output.kind
  of JsonlArtifact: output.records.add(line)
  of JsonlStdout: stdout.writeLine(line); stdout.flushFile()
  of JsonlStderr: stderr.writeLine(line); stderr.flushFile()
  of JsonlFile: output.file.writeLine(line); output.file.flushFile()

proc emit(trace: TraceState, tick: int, name: string, data: JsonNode) =
  let record = %*{
    "kind": "trace", "tick": tick, "event": name, "name": name, "data": data,
  }
  for output in trace.outputs:
    output.write(record)

proc addJsonlOutput(trace: TraceState, destination: string) =
  if destination == "stdout":
    trace.outputs.add(TraceOutput(kind: JsonlStdout))
  elif destination == "stderr":
    trace.outputs.add(TraceOutput(kind: JsonlStderr))
  elif destination == "artifact" or destination.startsWith("artifact:"):
    if trace.artifactUrl.len == 0:
      raise newException(ValueError,
        "artifact trace output requires COWORLD_PLAYER_ARTIFACT_UPLOAD_URL")
    let member = if destination == "artifact": "telemetry.jsonl"
      else: destination["artifact:".len .. ^1]
    if member.len == 0 or member.startsWith("/") or ".." in member.split('/'):
      raise newException(ValueError, "invalid artifact member path")
    trace.outputs.add(TraceOutput(kind: JsonlArtifact, member: member))
  elif destination.startsWith("file://") or destination.startsWith("file:"):
    let prefix = if destination.startsWith("file://"): "file://" else: "file:"
    let path = destination[prefix.len .. ^1]
    if path.len == 0: raise newException(ValueError, "file trace output requires a path")
    if path.parentDir.len > 0: createDir(path.parentDir)
    trace.outputs.add(TraceOutput(
      kind: JsonlFile, file: open(path, fmWrite), ownsFile: true))
  else:
    raise newException(ValueError, "unsupported trace output destination")

proc configure(trace: TraceState, raw: string) =
  if raw.strip.toLowerAscii in ["", "none", "off", "0", "false"]: return
  for chunk in raw.replace(';', ',').split(','):
    let spec = chunk.strip
    if spec.len == 0: continue
    let at = spec.find('@')
    if at < 0: raise newException(ValueError, "trace output must use format@destination")
    let format = spec[0 ..< at].toLowerAscii
    if format notin ["jsonl", "ndjson"]:
      raise newException(ValueError, "native stencil trace output supports jsonl")
    trace.addJsonlOutput(spec[at + 1 .. ^1])

proc newTraceState*(): TraceState =
  result = TraceState(artifactUrl: getEnv("COWORLD_PLAYER_ARTIFACT_UPLOAD_URL"))
  let configured = getEnv("STENCIL_TRACE_OUTPUTS", "jsonl@artifact")
  try:
    result.configure(configured)
  except CatchableError as error:
    stderr.writeLine("WARNING: trace outputs unavailable (" & error.msg &
      "); falling back to jsonl@stderr")
    result.outputs.setLen(0)
    result.addJsonlOutput("stderr")
  result.enabled = result.outputs.len > 0

proc record*(trace: TraceState, policy: StencilPolicy, command: Command) =
  if not trace.enabled: return
  try:
    let belief = policy.belief
    var signature = none(tuple[width, height, teams: int])
    if not belief.worldmap.isNil: signature = some(belief.worldmap.signature)
    if signature != trace.lastWorldSignature:
      trace.lastWorldSignature = signature
      trace.navigationFieldKeys.clear()
      trace.emit(policy.tick, "worldmap", snapshot(policy, command))
      if TraceNavigation and not belief.worldmap.isNil:
        trace.emit(policy.tick, "navigation_map", navigationMap(belief.worldmap))
    if TraceNavigation and not belief.worldmap.isNil:
      let map = belief.worldmap
      for field in map.cachedRouteFields:
        let key = field.goalCell.y * map.gridW + field.goalCell.x
        if key notin trace.navigationFieldKeys:
          trace.navigationFieldKeys.incl(key)
          trace.emit(policy.tick, "navigation_flow", navigationFlow(field, map))
    if trace.lastAlive.isNone or trace.lastAlive.get != belief.alive:
      trace.lastAlive = some(belief.alive)
      trace.emit(policy.tick, if belief.alive: "alive" else: "dead", newJObject())
    if trace.lastIntent.isNone or trace.lastIntent.get != policy.lastIntent.reason:
      trace.lastIntent = some(policy.lastIntent.reason)
      trace.emit(policy.tick, "objective", %*{
        "reason": policy.lastIntent.reason,
        "point": pointJson(policy.lastIntent.point),
      })
    if trace.carryInitialized and trace.lastCarry != belief.iCarryHeartOf:
      trace.emit(policy.tick, "carry", %*{"color": teamJson(belief.iCarryHeartOf)})
    trace.carryInitialized = true
    trace.lastCarry = belief.iCarryHeartOf
    if DiagEveryTicks > 0 and policy.tick mod DiagEveryTicks == 0:
      var data = snapshot(policy, command)
      for key, value in counters(policy): data[key] = value
      trace.emit(policy.tick, "snapshot", data)
  except CatchableError as error:
    stderr.writeLine("stencil trace error: " & error.msg)
    trace.enabled = false

proc close*(trace: TraceState) =
  if trace.isNil: return
  for output in trace.outputs:
    if output.ownsFile: output.file.close()
  let artifacts = trace.outputs.filterIt(it.kind == JsonlArtifact)
  if artifacts.len == 0: return
  try:
    var entries = initOrderedTable[string, string]()
    var files = newJArray()
    for output in artifacts:
      entries[output.member] = output.records.join("\n") &
        (if output.records.len > 0: "\n" else: "")
      files.add(%output.member)
    entries["manifest.json"] = pretty(%*{
      "schema_version": 1,
      "producer": "players.player_sdk.TraceOutputs",
      "files": files,
    })
    let payload = createZipArchive(entries)
    if trace.artifactUrl.startsWith("file://"):
      let path = trace.artifactUrl["file://".len .. ^1]
      if path.parentDir.len > 0: createDir(path.parentDir)
      writeFile(path, payload)
    elif trace.artifactUrl.startsWith("http://") or
        trace.artifactUrl.startsWith("https://"):
      let curl = newCurlPool(1)
      defer: curl.close()
      let response = curl.put(trace.artifactUrl,
        @[("Content-Type", "application/zip")], payload, 30.0'f32)
      if response.code < 200 or response.code >= 300:
        raise newException(IOError, "artifact PUT failed: HTTP " & $response.code)
    else:
      raise newException(ValueError, "unsupported artifact upload URL")
  except CatchableError as error:
    stderr.writeLine("WARNING: failed to close trace output: " & error.msg)
