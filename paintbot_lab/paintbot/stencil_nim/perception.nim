## Sprite-label perception: retained Sprite-v1 scene to a memoryless PaintState.

import std/[algorithm, math, options, sequtils, sets, strutils, tables]
import config, protocols, types

const
  CarryDistance = 24.0
  SelfSpriteBase = 5100
  PlayerSpriteBase = 100
  SelectedPlayerSpriteBase = 6000
  SoldierSkins = 2
  OverheadRadius = 34.0
  BadgeRadius = 30.0
  IdentityNames = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta"]

type
  SceneObject = tuple[objectId, spriteId, x, y, width, height: int, label: string]
  SceneIndex = object
    objects: seq[SceneObject]
    byLabel: Table[string, seq[int]]
  ActorMarkerPair = tuple[distance: float, actorIndex, markerIndex: int]

proc center(item: SceneObject): Point =
  (pyRound((item.x.float + item.width.float / 2.0) / RenderScale.float),
   pyRound((item.y.float + item.height.float / 2.0) / RenderScale.float))

proc distance(a, b: Point): float = hypot((a.x - b.x).float, (a.y - b.y).float)

proc objects(client: ProtocolClient): SceneIndex =
  for item in client.spriteObjects:
    let index = result.objects.len
    result.objects.add(item)
    result.byLabel.mgetOrPut(item.label, @[]).add(index)

iterator objectsWithLabel(scene: SceneIndex, label: string): SceneObject =
  if scene.byLabel.hasKey(label):
    for index in scene.byLabel[label]:
      yield scene.objects[index]

proc firstWithLabel(scene: SceneIndex, label: string): Option[SceneObject] =
  if scene.byLabel.hasKey(label) and scene.byLabel[label].len > 0:
    some(scene.objects[scene.byLabel[label][0]])
  else:
    none(SceneObject)

proc hasLabel(scene: SceneIndex, label: string): bool =
  scene.byLabel.hasKey(label) and scene.byLabel[label].len > 0

proc parseGameParams*(client: ProtocolClient): Option[tuple[teams: int, mapSize: Point]] =
  client.gameParams

proc parseEndzones*(client: ProtocolClient): Table[Team, EndzoneMarker] =
  client.endzoneMarkers

proc findSelf(
  scene: SceneIndex, colors: openArray[Team]
): tuple[pos: Option[Point], color: Option[Team], facing: Option[Facing], aim: Option[int]] =
  var exactAim = none(int)
  for item in scene.objects:
    if not item.label.startsWith("own aim "):
      continue
    try:
      let value = parseInt(item.label["own aim ".len .. ^1])
      if value >= 0 and value < AimBradsTurn:
        exactAim = some(value)
    except ValueError:
      discard
  for color in colors:
    for facing in [FacingRight, FacingLeft]:
      let label = "self " & color.teamName & " " &
        (if facing == FacingRight: "right" else: "left")
      let match = scene.firstWithLabel(label)
      if match.isNone:
        continue
      let item = match.get
      return (some(item.center), some(color), some(facing),
        if exactAim.isSome:
          exactAim
        else:
          # The soldier has only 16 visual rotations while the turret uses all
          # 256 integer-brad headings. Keep this as a compatibility fallback.
          let spriteId = item.spriteId
          if spriteId >= SelfSpriteBase:
            some(((spriteId - SelfSpriteBase) mod ObservedHeadingSteps) *
              (AimBradsTurn div ObservedHeadingSteps))
          else:
            none(int))

proc identityBadges(
  scene: SceneIndex, color: Team
): seq[tuple[identity: int, pos: Point]] =
  let prefix = "identity " & color.teamName & " "
  for item in scene.objects:
    if not item.label.startsWith(prefix):
      continue
    let name = item.label[prefix.len .. ^1].split(' ', 1)[0]
    let identity = IdentityNames.find(name)
    if identity >= 0:
      result.add((identity, item.center))

proc playersOfColor(scene: SceneIndex, color: Team): seq[Enemy] =
  let badges = identityBadges(scene, color)
  for facing in [FacingRight, FacingLeft]:
    let label = "player " & color.teamName & " " &
      (if facing == FacingRight: "right" else: "left")
    for item in objectsWithLabel(scene, label):
      let pos = item.center
      let aimBrads =
        if item.spriteId >= PlayerSpriteBase and
            item.spriteId < PlayerSpriteBase +
              SoldierSkins * TeamColors.len * ObservedHeadingSteps:
          some(((item.spriteId - PlayerSpriteBase) mod ObservedHeadingSteps) *
            (AimBradsTurn div ObservedHeadingSteps))
        elif item.spriteId >= SelectedPlayerSpriteBase and
            item.spriteId < SelectedPlayerSpriteBase +
              SoldierSkins * TeamColors.len * ObservedHeadingSteps:
          some(((item.spriteId - SelectedPlayerSpriteBase) mod ObservedHeadingSteps) *
            (AimBradsTurn div ObservedHeadingSteps))
        else:
          none(int)
      var
        bestIdentity = none(int)
        bestDistance = BadgeRadius
      for badge in badges:
        let d = distance(pos, badge.pos)
        if d < bestDistance:
          bestDistance = d
          bestIdentity = some(badge.identity)
      result.add(Enemy(pos: pos, facing: facing, aimBrads: aimBrads, color: color,
        identity: bestIdentity, hpSegments: none(int)))

proc visibleItems(scene: SceneIndex): seq[VisibleItem] =
  for item in scene.objects:
    let kind = case item.label
      of "grenade": "grenade"
      of "med kit": "medkit"
      of "shield": "shield"
      of "plasma arc", "spray can": "arc"
      else: ""
    if kind.len > 0:
      result.add((kind, item.center))

proc heardImpacts(scene: SceneIndex): seq[HeardSound] =
  for item in scene.objects:
    let kind = case item.label
      of "shot impact": "shot"
      of "grenade sound": "grenade"
      else: ""
    if kind.len > 0:
      result.add((kind, item.center))

proc heardShouts(scene: SceneIndex): seq[HeardShout] =
  for item in scene.objects:
    let marker = item.label.find(" shout ")
    if marker < 0:
      continue
    let team = item.label[0 ..< marker]
    if parseTeam(team).isNone:
      continue
    let rest = item.label[marker + " shout ".len .. ^1]
    let separator = rest.rfind(": ")
    if separator < 0:
      continue
    result.add((team, rest[0 ..< separator], rest[separator + 2 .. ^1], item.center))

proc teamScores(scene: SceneIndex): Table[Team, tuple[kills, deaths: int]] =
  const Prefix = "team score "
  for item in scene.objects:
    if not item.label.startsWith(Prefix):
      continue
    let parts = item.label[Prefix.len .. ^1].split(' ')
    if parts.len != 2:
      continue
    let team = parseTeam(parts[0].toLowerAscii)
    let score = parts[1].split('/', 1)
    if team.isNone or score.len != 2:
      continue
    try:
      result[team.get] = (parseInt(score[0]), parseInt(score[1]))
    except ValueError:
      discard

proc markerAssignments(
  actors, markers: openArray[Point]
): Table[int, int] =
  var pairs: seq[ActorMarkerPair]
  for actorIndex, actor in actors:
    for markerIndex, marker in markers:
      let d = distance(actor, marker)
      if d <= OverheadRadius:
        pairs.add((d, actorIndex, markerIndex))
  pairs.sort(proc(a, b: ActorMarkerPair): int = cmp(a.distance, b.distance))
  var
    assignedActors: HashSet[int]
    assignedMarkers: HashSet[int]
  for pair in pairs:
    if pair.actorIndex in assignedActors or pair.markerIndex in assignedMarkers:
      continue
    assignedActors.incl(pair.actorIndex)
    assignedMarkers.incl(pair.markerIndex)
    result[pair.actorIndex] = pair.markerIndex

proc attachOverheadState(
  scene: SceneIndex, selfXy: Point,
  enemies, teammates: var seq[Enemy]
): tuple[hp: Option[int], grenade, shield, arc: bool] =
  var
    hpValues: seq[int]
    hpPositions: seq[Point]
    carried = initTable[string, seq[Point]]()
  for label in ["grenade carried", "shield carried", "plasma arc carried", "spray can carried"]:
    carried[label] = @[]
  for item in scene.objects:
    if item.label.startsWith("hp "):
      let fields = item.label.split({' ', '/'})
      if fields.len >= 2:
        try:
          hpValues.add(parseInt(fields[1]))
          hpPositions.add(item.center)
        except ValueError:
          discard
    elif carried.hasKey(item.label):
      carried[item.label].add(item.center)

  var
    selfHpMarker = -1
    selfHpDistance = OverheadRadius
  result.hp = none(int)
  for markerIndex, markerPos in hpPositions:
    let d = distance(selfXy, markerPos)
    if d < selfHpDistance:
      selfHpDistance = d
      selfHpMarker = markerIndex
      result.hp = some(hpValues[markerIndex])

  let actors = enemies.mapIt(it.pos) & teammates.mapIt(it.pos)
  var remainingHpIndices: seq[int]
  var remainingHpPositions: seq[Point]
  for markerIndex, markerPos in hpPositions:
    if markerIndex != selfHpMarker:
      remainingHpIndices.add(markerIndex)
      remainingHpPositions.add(markerPos)
  for actorIndex, markerIndex in markerAssignments(actors, remainingHpPositions):
    let hp = hpValues[remainingHpIndices[markerIndex]]
    if actorIndex < enemies.len:
      enemies[actorIndex].hpSegments = some(hp)
    else:
      teammates[actorIndex - enemies.len].hpSegments = some(hp)

  for label, positions in carried:
    var
      selfMarkers: HashSet[int]
      remaining: seq[Point]
    for markerIndex, markerPos in positions:
      if distance(selfXy, markerPos) <= OverheadRadius:
        selfMarkers.incl(markerIndex)
      else:
        remaining.add(markerPos)
    let hasSelf = selfMarkers.len > 0
    case label
    of "grenade carried": result.grenade = hasSelf
    of "shield carried": result.shield = hasSelf
    of "plasma arc carried", "spray can carried": result.arc = result.arc or hasSelf
    else: discard
    if label == "shield carried":
      for actorIndex in markerAssignments(actors, remaining).keys:
        if actorIndex < enemies.len:
          enemies[actorIndex].shielded = true
        else:
          teammates[actorIndex - enemies.len].shielded = true

proc perceive*(
  client: ProtocolClient, team: Team, colors: openArray[Team],
  includeWalkability = true
): PaintState =
  let scene = client.objects
  let self = findSelf(scene, colors)
  var actualTeam = team
  if self.color.isSome:
    actualTeam = self.color.get

  result.selfXy = self.pos
  result.selfColor = self.color
  result.selfFacing = self.facing
  result.observedAim = self.aim
  result.ready = self.pos.isSome
  result.fireReady = scene.hasLabel("fire icon")

  for color in colors:
    if color == actualTeam:
      result.teammates.add(playersOfColor(scene, color))
    else:
      result.enemies.add(playersOfColor(scene, color))
  for color in colors:
    let
      planted = scene.firstWithLabel(color.teamName & " flag planted")
      carried = scene.firstWithLabel(color.teamName & " flag")
      plantedPos = if planted.isSome: some(planted.get.center) else: none(Point)
      carriedPos = if carried.isSome: some(carried.get.center) else: none(Point)
    result.hearts[color] = HeartState(
      planted: planted.isSome,
      pos: if plantedPos.isSome: plantedPos else: carriedPos,
      carriedPos: carriedPos)

  result.iCarryHeartOf = none(Team)
  if self.pos.isSome:
    for color in colors:
      if color == actualTeam:
        continue
      let heart = result.hearts[color]
      if heart.carriedPos.isSome and distance(heart.carriedPos.get, self.pos.get) <= CarryDistance:
        result.iCarryHeartOf = some(color)
        break
  result.visibleItems = visibleItems(scene)
  result.heardImpacts = heardImpacts(scene)
  result.heardShouts = heardShouts(scene)
  if self.pos.isSome:
    let overhead = attachOverheadState(scene, self.pos.get, result.enemies, result.teammates)
    result.hpPips = overhead.hp
    result.iHaveGrenade = overhead.grenade
    result.iHaveShield = overhead.shield
    result.iHaveArc = overhead.arc or scene.hasLabel("weapon spray")
  else:
    result.hpPips = none(int)
  let params = parseGameParams(client)
  if params.isSome:
    result.gameTeams = some(params.get.teams)
    result.mapSize = some(params.get.mapSize)
  else:
    result.gameTeams = none(int)
    result.mapSize = none(Point)
  result.endzones = parseEndzones(client)
  if includeWalkability and client.walkabilityReady:
    result.walkability = client.walkabilityMask
    result.walkabilityWidth = client.walkabilityWidth
    result.walkabilityHeight = client.walkabilityHeight
  result.teamScores = teamScores(scene)
