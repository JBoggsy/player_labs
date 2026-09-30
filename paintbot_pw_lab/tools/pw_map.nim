## pw_map: Paintbot PW background-map exporter (lab tool T8).
##
##   pw_map OUT_PREFIX [--map NAME] [--rules N] [--step UNITS] [--ppm]
##
## Samples the engine's own terrain predicates on a grid from newWorld and writes:
##   OUT_PREFIX.json  bounds, grid shape, hearts, pickups, trenches, cover, homes
##   OUT_PREFIX.bin   heights as int16 little-endian (nz*nx, row-major, z rows), then
##                    flags as uint8 (nz*nx): 1 water (inWater), 2 blocked at radius 0
##                    (bounds, off-island, cover), 4 trench, 8 off-island, 16 blocked at
##                    cog radius (a cog centre cannot stand there)
##   OUT_PREFIX.ppm   optional quick-look image (--ppm)
## Cell (i, j) samples the point (minX + i*step + step/2, minZ + j*step + step/2); world z
## grows downward in the viewer, so plot with extent [minX, maxX, maxZ, minZ].
## --map "" (default) is the procedural Heartwick island. --rules defaults to LiveRules.
## Contract and the Python loader (pw_mapdata.py): docs/tools/pw_map.md.
import std/[os, json, monotimes, times, strutils]
import sim, lab_pw_terrain_cache

proc inWater(p: Point): bool =
  ## Standing in the river's water: the predicate mechanics.nim uses to quarter a wading
  ## seat's speed (rules >= 30). Was neural_contract.inWater until 0.3.89 removed it (#185).
  visionRulesVersion >= 30 and riverBlend(p.x.int, p.z.int) > 0 and
    terrainHeight(p.x.int, p.z.int) < RiverWaterHeight

const SchemaVersion = 1
const PwRelease {.strdefine.} = "unknown"

proc main() =
  var prefix = ""
  var mapName = ""
  var rules = LiveRules
  var step = 25
  var ppm = false
  let args = commandLineParams()
  var i = 0
  while i < args.len:
    case args[i]
    of "--map": mapName = args[i+1]; inc i
    of "--rules": rules = parseInt(args[i+1]); inc i
    of "--step": step = parseInt(args[i+1]); inc i
    of "--ppm": ppm = true
    else:
      if args[i].startsWith("--") or prefix.len > 0: quit("usage: pw_map OUT_PREFIX [--map NAME] [--rules N] [--step UNITS] [--ppm]", 2)
      prefix = args[i]
    inc i
  if prefix.len == 0 or step < 1:
    quit("usage: pw_map OUT_PREFIX [--map NAME] [--rules N] [--step UNITS] [--ppm]", 2)
  let t0 = getMonoTime()
  configureRules(rules)
  visionRulesVersion = rules
  configureMap(mapName)
  let terrain = useTerrainCache()   # see pw_terrain_cache.nim
  var w = newWorld(1, 0)
  let x0 = minX(); let z0 = minZ(); let x1 = maxX(); let z1 = maxZ()
  let nx = (x1-x0) div step; let nz = (z1-z0) div step
  var heights = newSeq[int16](nx*nz)
  var flags = newSeq[uint8](nx*nz)
  var hmin = high(int); var hmax = low(int)
  for j in 0..<nz:
    for i in 0..<nx:
      let x = x0+i*step+step div 2; let z = z0+j*step+step div 2
      let p = point(x, z)
      let h = terrainHeight(x, z)
      heights[j*nx+i] = int16(clamp(h, int(low(int16)), int(high(int16))))
      hmin = min(hmin, h); hmax = max(hmax, h)
      var f = 0'u8
      if inWater(p): f = f or 1
      if w.blocked(p, 0): f = f or 2
      if w.trenchAt(p) >= 0: f = f or 4
      if islandTerrain and islandMargin(x, z) < 40: f = f or 8
      if w.blocked(p, Radius): f = f or 16
      flags[j*nx+i] = f
  var bin = newString(nx*nz*3)
  for k in 0..<nx*nz:
    let v = cast[uint16](heights[k])
    bin[2*k] = char(v and 0xff)
    bin[2*k+1] = char(v shr 8)
    bin[2*nx*nz+k] = char(flags[k])
  writeFile(prefix & ".bin", bin)
  if ppm:
    var img = newString(nx*nz*3)
    for k in 0..<nx*nz:
      let shade = 60 + 180*(heights[k].int-hmin) div max(1, hmax-hmin)
      var c = [shade, shade, shade-20]
      let f = flags[k]
      if (f and 1) != 0: c = [60, 110, 200]
      elif (f and 2) != 0: c = [30, 60, 30]
      if (f and 8) != 0: c = [20, 30, 60]
      if (f and 4) != 0: c = [140, 90, 40]
      for q in 0..2: img[k*3+q] = char(clamp(c[q], 0, 255))
    writeFile(prefix & ".ppm", "P6\n" & $nx & " " & $nz & "\n255\n" & img)
  var hearts, pickups: seq[JsonNode]
  for k, h in w.controlHearts: hearts.add %*{"idx": k, "pos": [h.pos.x, h.pos.z], "owner": h.owner}
  for k, p in w.pickups: pickups.add %*{"idx": k, "kind": ($p.kind).replace("Pickup", ""), "pos": [p.pos.x, p.pos.z]}
  writeFile(prefix & ".json", $(%*{"schema_version": SchemaVersion, "tool": "pw_map",
    "engine_release": PwRelease, "map": mapName, "rules": rules,
    "bounds": [x0, z0, x1, z1], "step": step, "nx": nx, "nz": nz, "height_range": [hmin, hmax],
    "layers": {"heights": "int16 le, nz*nx", "flags": "uint8, nz*nx, after heights"},
    "flag_bits": {"water": 1, "blocked": 2, "trench": 4, "off_island": 8, "blocked_for_cog": 16},
    "cog_radius": Radius, "capture_radius": ControlHeartRadius,
    "hearts": hearts, "pickups": pickups, "trenches": %w.trenches,
    "cover": %w.cover, "cover_note": "h == 0: circle of diameter w at (x + w/2, z + w/2); else rectangle",
    "homes": [[home(0).x, home(0).z], [home(1).x, home(1).z]]}))
  echo nx, "x", nz, " ms=", (getMonoTime()-t0).inMilliseconds, " cover=", w.cover.len,
    " trenches=", w.trenches.len, " terrain=", terrain

main()
