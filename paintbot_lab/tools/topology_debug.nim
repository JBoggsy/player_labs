## Offline Layer 2 topology process debugger.
##
## Re-runs the EXACT stencil topology code (worldmap.nim: 4-connected CCL,
## priority-flood watershed + persistence merge, directional cover, defense
## gates) on a clearance field the agent logged, with the TopologyJournal
## recording the process events the production path never retains: pre-merge
## watershed labels, seeds, saddle contacts, and every merge decision.
##
## Driven by tools/render_topology.py, which decodes the agent's
## `clearance_packed` trace payload into a raw byte file, invokes this tool,
## cross-checks the recomputed finals against the agent-traced finals (drift
## guard), and renders the interactive HTML viewer. The flood animation needs
## no per-pixel event log: a pixel is labeled exactly when the flood reaches
## its own clearance level, so (rawLabels, clearance) replay it faithfully.
##
## Build (host-native, no external deps — worldmap/config/types only):
##   nim c -d:release --path:../paintbot/stencil_nim -o:bin/topology_debug \
##     topology_debug.nim
## Usage:
##   topology_debug <meta.json> <clearance.bin> <output.json>
##
## meta.json: {"width": W, "height": H, "teams": N, "team": 0,
##             "endzones": [{"team": 0, "shape": "box",
##                           "x0":..,"y0":..,"x1":..,"y1":..}, ...]}
## clearance.bin: W*H row-major uint8 clearance values (delta-decoded).

import std/[json, math, options, os, random, strformat, tables]
import config, roles, types, worldmap

proc rleJson(values: seq[int]): JsonNode =
  ## [[value, runLength], ...] over a row-major array; label arrays are
  ## run-heavy so this stays small without a compression dependency.
  result = newJArray()
  if values.len == 0:
    return
  var current = values[0]
  var run = 1
  for index in 1 ..< values.len:
    if values[index] == current:
      inc run
    else:
      result.add(%[current, run])
      current = values[index]
      run = 1
  result.add(%[current, run])

proc pointJson(point: Point): JsonNode = %[point.x, point.y]

proc main() =
  if paramCount() != 3:
    stderr.writeLine("usage: topology_debug <meta.json> <clearance.bin> <output.json>")
    quit(2)
  let
    meta = parseFile(paramStr(1))
    width = meta["width"].getInt
    height = meta["height"].getInt
    teams = meta["teams"].getInt
    selfTeam = Team(meta["team"].getInt)
  let clearanceBytes = readFile(paramStr(2))
  if clearanceBytes.len != width * height:
    stderr.writeLine(&"clearance.bin has {clearanceBytes.len} bytes, " &
      &"expected {width * height}")
    quit(2)
  var markers = initTable[Team, EndzoneMarker]()
  for zone in meta["endzones"]:
    markers[Team(zone["team"].getInt)] = EndzoneMarker(
      shape: zone["shape"].getStr,
      x0: zone["x0"].getInt, y0: zone["y0"].getInt,
      x1: zone["x1"].getInt, y1: zone["y1"].getInt)

  # Walkability is fully determined by clearance: a pixel is a wall iff its
  # clearance is 0 (a walkable pixel is at distance >= 1 from the nearest
  # wall). Rebuilding from it and re-deriving clearance is drift guard #1.
  var pixelWalkable = newSeq[bool](width * height)
  for index in 0 ..< pixelWalkable.len:
    pixelWalkable[index] = clearanceBytes[index].uint8 > 0
  let journal = TopologyJournal()
  let map = newWorldMap(pixelWalkable, width, height, teams, markers,
    selfTeam, journal)
  for index in 0 ..< map.clearance.len:
    if map.clearance[index] != clearanceBytes[index].uint8:
      stderr.writeLine(&"clearance drift at pixel {index}: recomputed " &
        &"{map.clearance[index]} != logged {clearanceBytes[index].uint8}")
      quit(3)

  # Anchor (defense gate) scoring table per team. This mirrors defenseGate's
  # selection so the viewer can show WHY each gate won; the assert below
  # keeps the mirror honest against the production proc.
  var anchors = newJArray()
  for teamIndex in 0 ..< teams:
    let color = Team(teamIndex)
    let home = map.homeCenter(color)
    var
      enemyHome = home
      direct = Inf
    for opponentIndex in 0 ..< teams:
      let opponent = Team(opponentIndex)
      if opponent == color:
        continue
      let route = map.routeDistance(home, map.homeCenter(opponent))
      if route < direct:
        direct = route
        enemyHome = map.homeCenter(opponent)
    var rows = newJArray()
    var
      found = false
      best: Point
      bestFromHome = Inf
    if classify(direct) != fcInf:
      for choke in map.chokes:
        let fromHome = map.routeDistance(choke.pos, home)
        let toEnemy = map.routeDistance(choke.pos, enemyHome)
        let unreachable = classify(fromHome) == fcInf or
          classify(toEnemy) == fcInf
        let detour = if unreachable: Inf else: fromHome + toEnemy - direct
        let qualified = not unreachable and
          detour <= GateDetourPx.float and fromHome > 0.0
        rows.add(%*{
          "pos": pointJson(choke.pos),
          "from_home": if unreachable: newJNull() else: %fromHome,
          "to_enemy": if unreachable: newJNull() else: %toEnemy,
          "detour": if classify(detour) == fcInf: newJNull() else: %detour,
          "qualified": qualified,
        })
        if qualified and fromHome < bestFromHome:
          found = true
          bestFromHome = fromHome
          best = choke.pos
    let gate = map.defenseGate(color)
    if found and gate != best:
      stderr.writeLine(&"defenseGate mirror drift for team {teamIndex}: " &
        &"proc {gate} != mirror {best}")
      quit(3)
    anchors.add(%*{
      "team": teamIndex,
      "home": pointJson(home),
      "enemy_home": pointJson(enemyHome),
      "direct": if classify(direct) == fcInf: newJNull() else: %direct,
      "chokes": rows,
      "gate": pointJson(gate),
      "fallback_used": not found,
    })

  var rooms = newJArray()
  for room in map.rooms:
    rooms.add(%*{
      "peak": pointJson(room.peak),
      "clearance": room.peakClearance,
      "area": room.area,
      "component": room.component,
      "chokes": room.chokes,
    })
  var chokes = newJArray()
  for choke in map.chokes:
    chokes.add(%*{
      "pos": pointJson(choke.pos),
      "clearance": choke.clearance,
      "rooms": [choke.roomA, choke.roomB],
    })
  var seeds = newJArray()
  for index, seed in journal.seeds:
    seeds.add(%*{
      "label": index + 1,
      "pos": pointJson(seed),
      "clearance": map.clearance[seed.y * width + seed.x].int,
    })
  var contacts = newJArray()
  for contact in journal.contacts:
    contacts.add(%*{
      "pos": pointJson(contact.pos),
      "clearance": contact.clearance,
      "pair": [contact.a, contact.b],
    })
  var merges = newJArray()
  for merge in journal.merges:
    merges.add(%*{
      "pair": [merge.a, merge.b],
      "saddle": merge.saddle,
      "depth": merge.depth,
      "ratio": merge.ratio,
      "merged": merge.merged,
    })
  # Post fronts (static, belief-free) + defender assignments, so the viewer
  # can show candidate generation and seat selection from the exact
  # production code.
  proc candidateJson(candidate: PostCandidate): JsonNode =
    var rays = newJArray()
    for endpoint in candidate.rayEnds:
      rays.add(pointJson(endpoint))
    %*{
      "pos": pointJson(candidate.pos),
      "duck": pointJson(candidate.duck),
      "score": candidate.score,
      "sightline": candidate.sightline,
      "corridor": candidate.corridor,
      "duck_contrast": candidate.duckContrast,
      "ray_ends": rays,
    }
  var fronts = newJArray()
  for front in map.postFronts:
    var candidates = newJArray()
    for candidate in front.candidates:
      candidates.add(candidateJson(candidate))
    var posts = newJArray()
    for post in front.posts:
      posts.add(candidateJson(post))
    fronts.add(%*{
      "team": ord(front.team),
      "opponent": ord(front.opponent),
      "candidates": candidates,
      "posts": posts,
    })
  var defenders = newJArray()
  for teamIndex in 0 ..< teams:
    var seatsJson = newJArray()
    let seatCount = if teams == 4: 4 else: 8
    for seat in 0 ..< defenderCount(seatCount):
      let assignment = defensivePostForSeat(
        map, Team(teamIndex), seat, seatCount)
      if assignment.isSome:
        seatsJson.add(%*{
          "seat": seat,
          "post": pointJson(assignment.get.post.pos),
          "opponent": ord(assignment.get.opponent),
        })
    defenders.add(%*{"team": teamIndex, "assignments": seatsJson})

  # Selection samples: run the REAL production selection core on randomized
  # (front, anchor, rank, threats) cases so the viewer's interactive JS
  # mirror can be verified fail-closed at load time.
  var walkableCenters: seq[Point]
  for gy in 0 ..< map.gridH:
    for gx in 0 ..< map.gridW:
      if map.walkable[gy * map.gridW + gx]:
        walkableCenters.add(cellCenter((gx, gy)))
  var sampleRng = initRand(20260812)
  var samples = newJArray()
  if map.postFronts.len > 0 and walkableCenters.len > 0:
    for _ in 0 ..< 200:
      let frontIndex = sampleRng.rand(map.postFronts.high)
      let anchor = walkableCenters[sampleRng.rand(walkableCenters.high)]
      let rank = sampleRng.rand(2)
      var threats: seq[Point]
      for _ in 0 ..< sampleRng.rand(3):
        threats.add(walkableCenters[sampleRng.rand(walkableCenters.high)])
      let chosen = map.selectRankedPost(
        map.postFronts[frontIndex].candidates, anchor, rank, threats)
      var threatsJson = newJArray()
      for threat in threats:
        threatsJson.add(pointJson(threat))
      samples.add(%*{
        "front": frontIndex,
        "anchor": pointJson(anchor),
        "rank": rank,
        "threats": threatsJson,
        "chosen": if chosen.isSome: pointJson(chosen.get.pos) else: newJNull(),
      })

  var rawLabels = newSeq[int](width * height)
  for index in 0 ..< rawLabels.len:
    rawLabels[index] = journal.rawLabels[index].int
  var finalLabels = newSeq[int](width * height)
  for index in 0 ..< finalLabels.len:
    finalLabels[index] = map.roomLabel[index].int
  var componentLabels = newSeq[int](width * height)
  for index in 0 ..< componentLabels.len:
    componentLabels[index] = map.component[index].int
  var coverCells = newJArray()
  for value in map.coverDirs:
    coverCells.add(%value.int)

  let output = %*{
    "schema_version": 1,
    "width": width,
    "height": height,
    "grid": [map.gridW, map.gridH],
    "cell_size": NavCell,
    "cover_rays": clamp(CoverRays, 1, 16),
    "cover_ray_px": CoverRayPx,
    "merge_depth_px": TopologyMergeDepthPx,
    "merge_ratio": TopologyMergeRatio,
    "gate_detour_px": GateDetourPx,
    "gate_separation_px": GateSeparationPx,
    "components_n": map.componentCount,
    "component_ms": map.componentMs,
    "topology_ms": map.topologyMs,
    "cover_ms": map.coverMs,
    "rooms": rooms,
    "chokes": chokes,
    "seeds": seeds,
    "contacts": contacts,
    "merges": merges,
    "raw_labels_rle": rleJson(rawLabels),
    "final_labels_rle": rleJson(finalLabels),
    "component_labels_rle": rleJson(componentLabels),
    "cover_dirs": coverCells,
    "anchors": anchors,
    "post_fronts": fronts,
    "defender_assignments": defenders,
    "selection_params": %*{
      "search_px": SquadPostSearchPx,
      "separation_px": SquadPostSeparationPx,
      "facing_weight": PostFacingWeight,
    },
    "selection_samples": samples,
  }
  writeFile(paramStr(3), $output)
  echo &"topology_debug: {map.rooms.len} rooms, {map.chokes.len} chokes, " &
    &"{map.componentCount} components -> {paramStr(3)}"

main()
