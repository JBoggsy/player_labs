## Planner danger representation and LOS-exposure producer.

import std/math
import config, types, worldmap

type
  DangerField* = object
    values*: seq[float32]
    gridW, gridH: int
    maximum: float32
    visitGeneration: uint32
    visited: seq[uint32]
    kernelRadius: int
    attenuationKernel: seq[float32]
    perimeterOffsets: seq[Point]

proc ensureSize(field: var DangerField, map: WorldMap) =
  let size = map.gridW * map.gridH
  if field.gridW == map.gridW and field.gridH == map.gridH and
      field.values.len == size:
    return
  field.gridW = map.gridW
  field.gridH = map.gridH
  field.values = newSeq[float32](size)
  field.maximum = 0
  field.visited = newSeq[uint32](size)
  field.visitGeneration = 0

proc nextVisitGeneration(field: var DangerField) =
  if field.visitGeneration == high(uint32):
    for value in field.visited.mitems:
      value = 0
    field.visitGeneration = 1
  else:
    inc field.visitGeneration

proc attenuation(distancePx: float): float32 =
  if distancePx > DangerLosRangePx.float:
    return 0'f32
  if distancePx <= DangerLosFlatPx.float or
      DangerLosFlatPx == DangerLosRangePx:
    return 1'f32
  let fraction = (distancePx - DangerLosFlatPx.float) /
    (DangerLosRangePx - DangerLosFlatPx).float
  (1.0 - fraction * (1.0 - DangerLosFarFactor)).float32

proc ensureAttenuationKernel(field: var DangerField) =
  let radius = max(1, (DangerLosRangePx + NavCell - 1) div NavCell)
  if field.kernelRadius == radius and field.attenuationKernel.len > 0:
    return
  field.kernelRadius = radius
  let diameter = radius * 2 + 1
  field.attenuationKernel = newSeq[float32](diameter * diameter)
  field.perimeterOffsets.setLen(0)
  for dy in -radius .. radius:
    for dx in -radius .. radius:
      field.attenuationKernel[(dy + radius) * diameter + dx + radius] =
        attenuation(hypot(dx.float, dy.float) * NavCell.float)
  var included = newSeq[bool](diameter * diameter)
  template includeOffset(dx, dy: int) =
    let index = (dy + radius) * diameter + dx + radius
    if not included[index]:
      included[index] = true
      field.perimeterOffsets.add((dx, dy))
  let radiusSquared = radius * radius
  for dx in -radius .. radius:
    let dy = pyRound(sqrt(max(0, radiusSquared - dx * dx).float))
    includeOffset(dx, dy)
    includeOffset(dx, -dy)
  for dy in -radius .. radius:
    let dx = pyRound(sqrt(max(0, radiusSquared - dy * dy).float))
    includeOffset(dx, dy)
    includeOffset(-dx, dy)

proc addVisibleCell(
  field: var DangerField, map: WorldMap, origin: Point, gx, gy: int
) {.inline.} =
  if gx < 0 or gx >= map.gridW or gy < 0 or gy >= map.gridH:
    return
  let index = gy * map.gridW + gx
  if field.visited[index] == field.visitGeneration:
    return
  field.visited[index] = field.visitGeneration
  let
    diameter = field.kernelRadius * 2 + 1
    kernelX = gx - origin.x + field.kernelRadius
    kernelY = gy - origin.y + field.kernelRadius
  field.values[index] += field.attenuationKernel[kernelY * diameter + kernelX]

proc sightCellBlocked(map: WorldMap, x, y: int): bool {.inline.} =
  if x < 0 or x >= map.gridW or y < 0 or y >= map.gridH:
    return true
  let
    pixelX = x * NavCell + NavCell div 2
    pixelY = y * NavCell + NavCell div 2
  map.wall[pixelY * map.width + pixelX]

proc castSupercoverRay(
  field: var DangerField, map: WorldMap, origin: Point, targetX, targetY: int
) =
  let
    dx = targetX - origin.x
    dy = targetY - origin.y
    nx = abs(dx)
    ny = abs(dy)
    stepX = cmp(dx, 0)
    stepY = cmp(dy, 0)
  var
    x = origin.x
    y = origin.y
    ix = 0
    iy = 0
  while ix < nx or iy < ny:
    let decision = (1 + 2 * ix) * ny - (1 + 2 * iy) * nx
    if decision == 0:
      let
        sideX = x + stepX
        sideY = y + stepY
      if map.sightCellBlocked(sideX, y) or map.sightCellBlocked(x, sideY):
        break
      field.addVisibleCell(map, origin, sideX, y)
      field.addVisibleCell(map, origin, x, sideY)
      x = sideX
      y = sideY
      inc ix
      inc iy
    elif decision < 0:
      x += stepX
      inc ix
    else:
      y += stepY
      inc iy
    if map.sightCellBlocked(x, y):
      break
    field.addVisibleCell(map, origin, x, y)

proc castPerimeterRays(field: var DangerField, map: WorldMap, source: Point) =
  let origin = map.cellOf(source)
  field.nextVisitGeneration()
  field.addVisibleCell(map, origin, origin.x, origin.y)
  for offset in field.perimeterOffsets:
    field.castSupercoverRay(
      map, origin, origin.x + offset.x, origin.y + offset.y)

proc addCloseFloor(field: var DangerField, map: WorldMap, source: Point) =
  if DangerCloseFloor == 0.0 or DangerClosePx == 0:
    return
  let
    origin = map.cellOf(source)
    radiusCells = (DangerClosePx + NavCell - 1) div NavCell
    radiusSquared = DangerClosePx * DangerClosePx
  for gy in max(0, origin.y - radiusCells) ..
      min(map.gridH - 1, origin.y + radiusCells):
    for gx in max(0, origin.x - radiusCells) ..
        min(map.gridW - 1, origin.x + radiusCells):
      let center = cellCenter((gx, gy))
      let dx = center.x - source.x
      let dy = center.y - source.y
      if dx * dx + dy * dy <= radiusSquared:
        field.values[gy * map.gridW + gx] += DangerCloseFloor.float32

proc rebuildLosDanger*(
  field: var DangerField, map: WorldMap, sources: openArray[Point]
) =
  ## Replaces the complete field. Each source contributes once per visible
  ## cell even when several perimeter rays traverse that cell.
  field.ensureSize(map)
  field.ensureAttenuationKernel()
  for value in field.values.mitems:
    value = 0
  for source in sources:
    field.castPerimeterRays(map, source)
    field.addCloseFloor(map, source)
  field.maximum = 0
  for value in field.values.mitems:
    if DangerLosWeight != 1.0:
      value *= DangerLosWeight.float32
    field.maximum = max(field.maximum, value)

proc sample*(field: DangerField, map: WorldMap, point: Point): float =
  if field.values.len != map.gridW * map.gridH:
    return 0.0
  let cell = map.cellOf(point)
  field.values[cell.y * map.gridW + cell.x].float

proc fieldMax*(field: DangerField): float =
  field.maximum.float
