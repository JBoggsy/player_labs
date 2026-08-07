## Structured diagnostics and player-artifact delivery.
## Telemetry is isolated from gameplay: failures are reported and swallowed.

import std/[algorithm, json, math, options, os, sequtils, sets, strutils, tables]
import curly, zippy/ziparchives
import belief_state, config, policy, squads, types, worldmap

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
    lastConsensusSignature: string
    lastOrderSignature: string
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

proc facingName(facing: Facing): string =
  if facing == FacingRight: "right" else: "left"

proc trackJson(track: PlayerTrack, tick: int): JsonNode =
  %*{
    "pos": pointJson(track.pos),
    "age": tick - track.lastTick,
    "facing": facingName(track.facing),
    "heading_brads": (if track.aimBrads.isSome:
      %track.aimBrads.get else: newJNull()),
    "vel": (if track.vel.isSome:
      %*[rounded4(track.vel.get.x), rounded4(track.vel.get.y)] else: newJNull()),
    "frames_seen": track.framesSeen,
    "identity": (if track.identity.isSome: %track.identity.get else: newJNull()),
    "hp_segments": (if track.hpSegments.isSome:
      %track.hpSegments.get else: newJNull()),
    "shielded": track.shielded,
  }

proc itemKindName(kind: ItemKind): string =
  case kind
  of Arc: "arc"
  of Grenade: "grenade"
  of Medkit: "medkit"
  of Shield: "shield"

proc scalarGrid(values: openArray[float32], map: WorldMap): JsonNode =
  ## Block-max downsample and quantize a nav-grid scalar to compact 0..255 rows.
  let
    scale = DangerTraceDownsample
    outW = (map.gridW + scale - 1) div scale
    outH = (map.gridH + scale - 1) div scale
  var rows = newJArray()
  for outY in 0 ..< outH:
    var row = newJArray()
    for outX in 0 ..< outW:
      var peak = 0'f32
      for y in outY * scale .. min((outY + 1) * scale, map.gridH) - 1:
        for x in outX * scale .. min((outX + 1) * scale, map.gridW) - 1:
          peak = max(peak, values[y * map.gridW + x])
      row.add(%clamp(pyRound(peak.float * 255.0), 0, 255))
    rows.add(row)
  %*{"cell_px": scale * NavCell, "rows": rows}

proc coveredGrid(belief: Belief): JsonNode =
  ## Conservative instantaneous ally vision. Other players expose a fuzzed
  ## 16-step heading, not their exact aim, so coverage uses that observable
  ## heading, the narrowest deployed cone, and exact pixel-wall LoS.
  let map = belief.worldmap
  if map.isNil:
    return newJNull()
  var allies: seq[Enemy]
  for teammate in belief.teammates:
    if teammate.aimBrads.isSome:
      allies.add(teammate)
  let
    scale = DangerTraceDownsample
    cellPx = scale * NavCell
    outW = (map.gridW + scale - 1) div scale
    outH = (map.gridH + scale - 1) div scale
    coneHalfBrads = GuaranteedVisionConeHalfDeg.float /
      360.0 * AimBradsTurn.float
    visionRange = PostGunRangePx.float * 1.5
  var rows = newJArray()
  for outY in 0 ..< outH:
    var row = newJArray()
    for outX in 0 ..< outW:
      let point: Point = (
        min(outX * cellPx + cellPx div 2, map.width - 1),
        min(outY * cellPx + cellPx div 2, map.height - 1))
      var isCovered = false
      if map.wall[point.y * map.width + point.x]:
        row.add(%0)
        continue
      for ally in allies:
        let
          dx = point.x - ally.pos.x
          dy = point.y - ally.pos.y
          distance = hypot(dx.float, dy.float)
        if distance > VisionBubble.float:
          if distance > visionRange:
            continue
          let
            wanted = arctan2(-dy.float, dx.float) /
              (2.0 * PI) * AimBradsTurn.float
            error = abs(floorMod(
              pyRound(wanted - ally.aimBrads.get.float + AimBradsTurn.float / 2.0),
              AimBradsTurn) - AimBradsTurn div 2).float
          if error > coneHalfBrads:
            continue
        if map.rayClear(ally.pos, point):
          isCovered = true
          break
      row.add(%(if isCovered: 255 else: 0))
    rows.add(row)
  %*{
    "cell_px": cellPx,
    "rows": rows,
    "source": "visible_allies",
    "heading_precision_brads": AimBradsTurn div ObservedHeadingSteps,
  }

proc directiveJson(directive: SquadDirective): JsonNode =
  %*{
    "kind": $directive.kind,
    "point": pointJson(directive.pos),
    "opponent": teamName(directive.opponent),
  }

proc consensusJson(belief: Belief): JsonNode =
  var
    proposals = newJArray()
    votes = newJArray()
    proposalSeats: seq[int]
    voteSeats: seq[int]
  for seat in belief.consensusProposals.keys: proposalSeats.add(seat)
  for seat in belief.consensusVotes.keys: voteSeats.add(seat)
  proposalSeats.sort()
  voteSeats.sort()
  for seat in proposalSeats:
    proposals.add(%*{
      "seat": seat,
      "directive": directiveJson(belief.consensusProposals[seat]),
    })
  for seat in voteSeats:
    votes.add(%*{
      "seat": seat,
      "directive": directiveJson(belief.consensusVotes[seat]),
    })
  %*{
    "epoch": belief.consensusEpoch,
    "state": belief.consensusState,
    "started_tick": (if belief.consensusStartedTick >= 0:
      %belief.consensusStartedTick else: newJNull()),
    "squad": $belief.squadOf.name,
    "members": belief.squadOf.seats,
    "rank": belief.rankOf,
    "quorum": belief.consensusQuorum,
    "proposal": (if belief.consensusProposal.isSome:
      directiveJson(belief.consensusProposal.get) else: newJNull()),
    "vote": (if belief.consensusVote.isSome:
      directiveJson(belief.consensusVote.get) else: newJNull()),
    "proposals": proposals,
    "votes": votes,
  }

proc orderJson(belief: Belief): JsonNode =
  if belief.order.isNone:
    return newJNull()
  let order = belief.order.get
  %*{
    "directive": directiveJson(order.directive),
    "epoch": order.epoch,
    "set_tick": order.setTick,
    "source": belief.orderSource,
    "arrived": belief.orderArrived,
  }

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
  let targetScore = belief.firefightTargetScore
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
  var enemyTracks = newJArray()
  for track in belief.enemyTracks:
    enemyTracks.add(trackJson(track, belief.tick))
  var teammateTracks = newJArray()
  for track in belief.teammateTracks:
    teammateTracks.add(trackJson(track, belief.tick))
  var itemSpawns = newJArray()
  for spawn in belief.itemSpawns:
    itemSpawns.add(%*{
      "kind": itemKindName(spawn.kind),
      "pos": pointJson(spawn.pos),
      "present": spawn.present,
      "absent_until": spawn.absentUntil,
      "last_seen": spawn.lastSeen,
    })
  var heardEvents = newJArray()
  for event in belief.heardEvents:
    heardEvents.add(%*{
      "kind": event.kind,
      "pos": pointJson(event.pos),
      "age": belief.tick - event.lastTick,
    })
  var visibleEnemies = newJArray()
  var visibleEnemyDetails = newJArray()
  for enemy in belief.enemies:
    visibleEnemies.add(pointJson(enemy.pos))
    visibleEnemyDetails.add(%*{
      "pos": pointJson(enemy.pos),
      "heading_brads": (if enemy.aimBrads.isSome:
        %enemy.aimBrads.get else: newJNull()),
      "identity": (if enemy.identity.isSome: %enemy.identity.get else: newJNull()),
      "hp_segments": (if enemy.hpSegments.isSome:
        %enemy.hpSegments.get else: newJNull()),
      "shielded": enemy.shielded,
    })
  var visibleTeammates = newJArray()
  for teammate in belief.teammates:
    visibleTeammates.add(%*{
      "pos": pointJson(teammate.pos),
      "heading_brads": (if teammate.aimBrads.isSome:
        %teammate.aimBrads.get else: newJNull()),
      "identity": (if teammate.identity.isSome:
        %teammate.identity.get else: newJNull()),
    })
  var presenceAge = newJObject()
  for seat, seenTick in belief.presence:
    presenceAge[$seat] = %(belief.tick - seenTick)
  var navPath = newJArray()
  if belief.nav.hasPath:
    for index in belief.nav.cursor .. belief.nav.path.high:
      navPath.add(pointJson(belief.nav.path[index]))
  var viewerOrder = newJNull()
  var orderAge = newJNull()
  if belief.order.isSome:
    let order = belief.order.get
    viewerOrder = %*[$order.directive.kind, pointJson(order.directive.pos), order.setTick]
    orderAge = %(belief.tick - order.setTick)
  let enemyLives = belief.enemyLivesLeft
  var ownLives = newJNull()
  if belief.teamScores.hasKey(belief.team):
    ownLives = %(max(0, belief.seatsPerTeam * LivesPerPlayer -
      belief.teamScores[belief.team].deaths))
  result = %*{
    "tick": policy.tick,
    "team": teamName(belief.team),
    "seat": belief.seat,
    "slot": belief.slot,
    "role": roleName(belief.role),
    "squad": $belief.squadOf.name,
    "squad_members": belief.squadOf.seats,
    "squad_rank": belief.rankOf,
    "squad_quorum": belief.consensusQuorum,
    "squad_consensus": consensusJson(belief),
    "squad_order": orderJson(belief),
    "squad_order_post": pointJson(belief.squadOrderPost),
    "squad_order_post_duck": pointJson(belief.squadOrderPostDuck),
    "squad_order_post_sightline_aim": pointJson(
      belief.squadOrderPostSightlineAim),
    "squad_order_post_opponent": teamJson(belief.squadOrderPostOpponent),
    "squad_order_post_score": rounded4(belief.squadOrderPostScore),
    "squad_order_post_active": belief.squadOrderPostActive,
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
    "enemy_tracks": enemyTracks,
    "teammate_tracks": teammateTracks,
    "visible_enemies": visibleEnemies,
    "visible_enemy_details": visibleEnemyDetails,
    "visible_teammates": visibleTeammates,
    "item_spawns": itemSpawns,
    "heard_events_live": heardEvents,
    "presence_age": presenceAge,
    "nav_path": navPath,
    "objective": policy.lastIntent.reason,
    "order": viewerOrder,
    "order_source": belief.orderSource,
    "order_age": orderAge,
    "orders_sent": belief.commitsSent,
    "orders_heard": belief.commitsHeard,
    "pings_sent": belief.pingsSent,
    "pings_heard": belief.pingsHeard,
    "backoff_events": belief.backoffEvents,
    "enemy_lives_left": (if enemyLives.isSome:
      %enemyLives.get else: newJNull()),
    "own_lives_left": ownLives,
    "hp_pips": (if belief.hpPips.isSome: %belief.hpPips.get else: newJNull()),
    "have": {
      "grenade": belief.iHaveGrenade,
      "shield": belief.iHaveShield,
      "arc": belief.iHaveArc,
    },
    "team_scores": scores,
    "firefight_active": belief.firefightActive,
    "target_enemy": (if targetScore.isSome:
      pointJson(targetScore.get.candidate.enemy.pos) else: newJNull()),
    "target_enemy_team": (if targetScore.isSome:
      %teamName(targetScore.get.candidate.enemy.color) else: newJNull()),
    "target_score": (if targetScore.isSome:
      %rounded4(targetScore.get.score) else: newJNull()),
    "target_generic_score": (if targetScore.isSome:
      %rounded4(targetScore.get.genericScore) else: newJNull()),
    "target_defensive_threat": (if targetScore.isSome:
      %rounded4(targetScore.get.defensiveThreat) else: newJNull()),
    "target_heart_distance_px": (if targetScore.isSome and
        classify(targetScore.get.heartDistancePx) != fcInf:
      %rounded4(targetScore.get.heartDistancePx) else: newJNull()),
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
    result["danger"] = scalarGrid(belief.danger, map)
  result["covered"] = coveredGrid(belief)

proc counters(policy: StencilPolicy): JsonNode =
  let b = policy.belief
  %*{
    "friendly_fire_suppressed": b.friendlyFireSuppressed,
    "aim_resyncs": b.aimResyncs,
    "firing_turns": b.firingTurns,
    "firefight_ticks_total": b.firefightTicksTotal,
    "firefight_engagements": b.firefightEngagements,
    "firefight_target_switches": b.firefightTargetSwitches,
    "defensive_target_multi_ticks": b.defensiveTargetMultiTicks,
    "defensive_target_choice_changes": b.defensiveTargetChoiceChanges,
    "defensive_carrier_override_ticks": b.defensiveCarrierOverrideTicks,
    "defensive_carrier_immediate_switches": b.defensiveCarrierImmediateSwitches,
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
    "squad_proposals_sent": b.proposalsSent,
    "squad_proposals_heard": b.proposalsHeard,
    "squad_votes_sent": b.votesSent,
    "squad_votes_heard": b.votesHeard,
    "squad_commits_sent": b.commitsSent,
    "squad_commits_heard": b.commitsHeard,
    "squad_consensus_commits": b.consensusCommits,
    "squad_consensus_timeouts": b.consensusTimeouts,
    "squad_consensus_resyncs": b.consensusResyncs,
    "squad_order_follow_ticks": b.orderFollowTicks,
    "squad_order_move_ticks": b.orderMoveTicks,
    "squad_order_hold_ticks": b.orderHoldTicks,
    "squad_order_watch_ticks": b.orderWatchTicks,
    "squad_order_arrivals": b.orderArrivals,
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
      if policy.lastIntent.reason.startsWith("squad_"):
        trace.emit(policy.tick, "squad_follow", %*{
          "reason": policy.lastIntent.reason,
          "point": pointJson(policy.lastIntent.point),
          "order": orderJson(belief),
          "post": pointJson(belief.squadOrderPost),
          "post_duck": pointJson(belief.squadOrderPostDuck),
        })
    let consensus = consensusJson(belief)
    let consensusSignature = $consensus
    if consensusSignature != trace.lastConsensusSignature:
      trace.lastConsensusSignature = consensusSignature
      trace.emit(policy.tick, "squad_consensus", consensus)
    let order = orderJson(belief)
    let orderSignature = $order
    if orderSignature != trace.lastOrderSignature:
      trace.lastOrderSignature = orderSignature
      trace.emit(policy.tick, "squad_order", %*{
        "order": order,
        "post": pointJson(belief.squadOrderPost),
        "post_duck": pointJson(belief.squadOrderPostDuck),
        "post_sightline_aim": pointJson(belief.squadOrderPostSightlineAim),
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
