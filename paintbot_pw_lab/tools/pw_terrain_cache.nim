## pw_terrain_cache: the shared terrain-table file for the lab's -d:pwTraining tools.
##
## Since coworld-v0.3.89 (#183) a training build computes a whole 64x64 terrain block the first
## time any point in it is read, so a short-lived process (one pw_trace per tape, one pw_map)
## pays ~20 s for most of the island. The engine can save a computed table and map it back
## read-only (topography.nim saveTerrain/loadTerrain). This module wires that in:
##
## - The cache directory comes from $PW_TERRAIN_CACHE_DIR, which the Python wrappers set
##   (tools/pw_terrain.py: <cache root>/terrain/<tag>/). Unset or empty = no cache, so a
##   binary run by hand behaves exactly as before.
## - One file per terrain flag set: island-f<bits>.pwterrain, <bits> = the eleven rules-derived
##   terrain flags in the engine's own order (topography.nim terrainFlagsKey). Every rules >= 35
##   tape shares f2047. pw_terrain.py names files the same way; keep the two in step.
## - A missing file is built once: under an exclusive flock on <file>.lock the first process
##   prewarms the whole world and saves (saveTerrain writes a temporary file and renames it);
##   the others wait on the lock, then load. A killed builder's lock is released by the OS and
##   its temporary file is deleted by the next builder or by pw_terrain.py.
## - A file the engine rejects is left alone (never overwritten): the run continues uncached
##   with a warning. `pw.py terrain-cache clear` removes it.
## Terrain values are identical either way (loadTerrain checks sampled cells against the direct
## functions); the per-tick hash check in pw_trace proves it on every tape.
## Built by tools/build_tools.sh, copied next to the tools as lab_pw_terrain_cache.nim.
import std/[os, posix, times]
import sim

proc flock(fd: cint, operation: cint): cint {.importc, header: "<sys/file.h>".}
const LockExclusive = 2.cint # LOCK_EX

when declared(saveTerrain):
  proc terrainCacheName(): string =
    var bits = 0
    for i, flag in [wideRamps, wilderness, deepWilderness, organicTerrain, islandTerrain,
        expandedIsland, riverTerrain, curvedRiver, fractalRiver, lakeTerrain, symmetricTerrain]:
      if flag: bits = bits or (1 shl i)
    "island-f" & $bits & ".pwterrain"

  proc loadCache(path: string): string =
    try:
      discard loadTerrain(path)
    except IOError as e:
      stderr.writeLine("WARNING: ", e.msg, "; running without the terrain cache ",
        "(clear it: uv run python paintbot_pw_lab/tools/pw.py terrain-cache clear)")
      return "rejected"
    try: setLastModificationTime(path, getTime()) # recency for pw_terrain.py's LRU cap
    except OSError: discard
    "loaded"

proc useTerrainCache*(): string =
  ## Call once the rules version and map are set (loadRecording, or configureRules +
  ## configureMap) and before newWorld. Returns what happened: "off" (no cache dir, a
  ## generated map, or a pre-0.3.89 build), "loaded", "built" or "rejected".
  when not declared(saveTerrain):
    return "off"
  else:
    # loadRecording only sets visionRulesVersion; the terrain flags (and so the table this
    # thread uses) are bound by configureRules, which newWorld calls first. Make that same
    # idempotent call now, or the file would be keyed and filled for the all-flags-off table.
    configureRules(visionRulesVersion)
    let dir = getEnv("PW_TERRAIN_CACHE_DIR")
    if dir.len == 0 or activeMap() >= 0: return "off"
    let path = dir / terrainCacheName()
    if fileExists(path): return loadCache(path)
    createDir(dir)
    let fd = posix.open(cstring(path & ".lock"), O_RDWR or O_CREAT, 0o644)
    if fd < 0: raiseOSError(osLastError(), path & ".lock")
    try:
      if flock(fd, LockExclusive) != 0: raiseOSError(osLastError(), path & ".lock")
      if fileExists(path): return loadCache(path) # another process built it while we waited
      for stale in walkFiles(path & ".tmp-*"): removeFile(stale)
      discard prewarmTerrain(minX(), minZ(), maxX(), maxZ())
      discard saveTerrain(path)
      "built"
    finally:
      discard posix.close(fd) # releases the lock
