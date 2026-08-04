import
  std/[options, strutils, tables],
  bitworld/spriteprotocol,
  supersnappy,
  types

type
  SpriteInfo* = ref object
    defined*: bool
    width*: int
    height*: int
    label*: string

  ObjectState = object
    present: bool
    x: int
    y: int
    z: int
    layer: int
    spriteId: int
    orderPrev: int
    orderNext: int

  SpriteState = ref object
    sprites: seq[SpriteInfo]
    objects: seq[ObjectState]
    objectOrderHead: int
    objectOrderTail: int

  ProtocolClient* = ref object
    sprite: SpriteState
    walkabilityReady*: bool
    walkabilityWidth*: int
    walkabilityHeight*: int
    walkabilityMask*: seq[bool]
    gameParams*: Option[tuple[teams: int, mapSize: Point]]
    endzoneMarkers*: Table[Team, EndzoneMarker]
    packetBytes: seq[uint8]

proc initSpriteState(): SpriteState =
  ## Builds the initial sprite protocol state.
  SpriteState(objectOrderHead: -1, objectOrderTail: -1)

proc initProtocolClient*(): ProtocolClient =
  ## Builds protocol state for one websocket connection.
  ProtocolClient(sprite: initSpriteState())

proc reset*(client: ProtocolClient) =
  ## Clears queued wire data while preserving reusable frame buffers.
  client.sprite = initSpriteState()
  client.walkabilityReady = false
  client.walkabilityWidth = 0
  client.walkabilityHeight = 0
  client.walkabilityMask.setLen(0)
  client.gameParams = none(tuple[teams: int, mapSize: Point])
  client.endzoneMarkers.clear()

proc cacheStaticLabel(client: ProtocolClient, label: string) =
  ## Fold immutable episode metadata once when its sprite definition arrives.
  const
    GamePrefix = "game teams "
    EndzonePrefix = "endzone "
    EndzoneShapes = ["column", "square", "disc", "corner", "arm"]
  if label.startsWith(GamePrefix):
    let parts = label[GamePrefix.len .. ^1].split(' ')
    if parts.len == 3 and parts[1] == "map":
      let size = parts[2].split('x', 1)
      if size.len == 2:
        try:
          client.gameParams = some((clamp(parseInt(parts[0]), 2, 4),
            (parseInt(size[0]), parseInt(size[1]))))
        except ValueError:
          discard
    return
  if label.startsWith(EndzonePrefix):
    let parts = label[EndzonePrefix.len .. ^1].split(' ')
    if parts.len != 4 or parts[1] notin EndzoneShapes:
      return
    let team = parseTeam(parts[0])
    let start = parts[2].split(',', 1)
    let stop = parts[3].split(',', 1)
    if team.isNone or start.len != 2 or stop.len != 2:
      return
    try:
      client.endzoneMarkers[team.get] = EndzoneMarker(
        shape: parts[1],
        x0: parseInt(start[0]), y0: parseInt(start[1]),
        x1: parseInt(stop[0]), y1: parseInt(stop[1]))
    except ValueError:
      discard

proc queryEscape*(value: string): string =
  ## Escapes a small string for use in a websocket query parameter.
  const Hex = "0123456789ABCDEF"
  for ch in value:
    if ch in {'a' .. 'z'} or ch in {'A' .. 'Z'} or ch in {'0' .. '9'} or
        ch in {'-', '_', '.', '~'}:
      result.add(ch)
    else:
      let byte = ord(ch)
      result.add('%')
      result.add(Hex[(byte shr 4) and 0x0f])
      result.add(Hex[byte and 0x0f])

proc hasQueryParam(url, key: string): bool =
  ## Returns true when a URL already carries one query key.
  url.contains("?" & key & "=") or url.contains("&" & key & "=")

proc addQueryParam*(url, key, value: string): string =
  ## Adds one encoded query parameter to a URL.
  if value.len == 0 or url.hasQueryParam(key):
    return url
  url & (if '?' in url: "&" else: "?") & key & "=" & value.queryEscape()

proc playerConnectUrl*(
  endpoint,
  name,
  token: string,
  slot: int
): string =
  ## Adds player join query parameters to an endpoint.
  result = endpoint
  result = result.addQueryParam("name", name)
  if slot >= 0:
    result = result.addQueryParam("slot", $slot)
  result = result.addQueryParam("token", token)

proc ensureWsPath*(url: string, defaultPath: string): string =
  ## Inserts `defaultPath` when a websocket URL has no path.
  let scheme = url.find("://")
  let start =
    if scheme < 0:
      0
    else:
      scheme + 3
  for i in start ..< url.len:
    case url[i]
    of '/':
      return url
    of '?', '#':
      return url[0 ..< i] & defaultPath & url[i .. ^1]
    else:
      discard
  url & defaultPath

proc inputBlob*(mask: uint8): string =
  ## Builds one sprite player input packet.
  blobFromSpriteMask(mask)

proc chatBlob*(text: string): string =
  ## Builds one sprite player chat packet.
  blobFromSpriteChat(text)

proc readyBlob*(): string =
  ## Builds one sprite player-ready packet (0x85). The pinned bitworld
  ## predates the packet, so the id is declared here rather than imported.
  result = newString(1)
  result[0] = char(0x85)

proc spritesOffBlob*(): string =
  ## Builds one sprite sprites-off packet (0x87): this bot consumes state
  ## and labels only, never pixels. Declared here like readyBlob so the
  ## pinned bitworld needn't carry it.
  result = newString(1)
  result[0] = char(0x87)

proc ensureSprite(state: SpriteState, spriteId: int) =
  ## Ensures the sprite table can hold one sprite id.
  if spriteId >= state.sprites.len:
    state.sprites.setLen(spriteId + 1)

proc ensureObject(state: SpriteState, objectId: int) =
  ## Ensures the object table can hold one object id.
  if objectId >= state.objects.len:
    let previousLen = state.objects.len
    state.objects.setLen(objectId + 1)
    for index in previousLen .. objectId:
      state.objects[index].orderPrev = -1
      state.objects[index].orderNext = -1

proc appendObjectOrder(state: SpriteState, objectId: int) =
  let previous = state.objectOrderTail
  state.objects[objectId].orderPrev = previous
  state.objects[objectId].orderNext = -1
  if previous >= 0:
    state.objects[previous].orderNext = objectId
  else:
    state.objectOrderHead = objectId
  state.objectOrderTail = objectId

proc removeObjectOrder(state: SpriteState, objectId: int) =
  let
    previous = state.objects[objectId].orderPrev
    following = state.objects[objectId].orderNext
  if previous >= 0:
    state.objects[previous].orderNext = following
  else:
    state.objectOrderHead = following
  if following >= 0:
    state.objects[following].orderPrev = previous
  else:
    state.objectOrderTail = previous
  state.objects[objectId].orderPrev = -1
  state.objects[objectId].orderNext = -1

proc spriteInfo(state: SpriteState, spriteId: int): SpriteInfo =
  ## Returns sprite metadata or nil for an unknown sprite.
  if spriteId >= 0 and spriteId < state.sprites.len:
    return state.sprites[spriteId]

iterator spriteObjects*(
  client: ProtocolClient
): tuple[
  objectId: int,
  spriteId: int,
  x: int,
  y: int,
  width: int,
  height: int,
  label: string
] =
  ## Iterates present sprite objects with their sprite metadata.
  if not client.sprite.isNil:
    var objectId = client.sprite.objectOrderHead
    while objectId >= 0:
      let
        currentId = objectId
        objectState = client.sprite.objects[currentId]
      objectId = objectState.orderNext
      let sprite = client.sprite.spriteInfo(objectState.spriteId)
      if sprite.isNil or not sprite.defined:
        continue
      yield (
        objectId: currentId,
        spriteId: objectState.spriteId,
        x: objectState.x,
        y: objectState.y,
        width: sprite.width,
        height: sprite.height,
        label: sprite.label
      )

proc decodeWalkabilityPixels(
  width,
  height: int,
  compressed: string,
  mask: var seq[bool]
): bool =
  ## Decodes the sprite protocol walkability payload into a bool mask.
  var rawPixels = ""
  try:
    rawPixels = supersnappy.uncompress(compressed)
  except CatchableError:
    return false
  if width <= 0 or height <= 0 or rawPixels.len != width * height * 4:
    return false
  mask.setLen(width * height)
  for i in 0 ..< mask.len:
    mask[i] = rawPixels[i * 4 + 3].uint8 > 0
  true

proc applySpritePacket(
  client: ProtocolClient,
  packet: string
): bool =
  ## Applies sprite protocol messages to the retained scene state.
  blobToBytes(packet, client.packetBytes)
  try:
    for message in parseSpritePacket(client.packetBytes):
      case message.kind
      of spkSprite:
        let sprite = message.sprite
        client.cacheStaticLabel(sprite.label)
        let shouldDecodeWalkability = sprite.label == "walkability map" and
          sprite.compressedPixels.len > 0
        if shouldDecodeWalkability:
          if not decodeWalkabilityPixels(
            sprite.width,
            sprite.height,
            blobFromBytes(sprite.compressedPixels),
            client.walkabilityMask
          ):
            return false
          client.walkabilityReady = true
          client.walkabilityWidth = sprite.width
          client.walkabilityHeight = sprite.height
        client.sprite.ensureSprite(sprite.id)
        client.sprite.sprites[sprite.id] = SpriteInfo(
          defined: true,
          width: sprite.width,
          height: sprite.height,
          label: sprite.label
        )
      of spkObject:
        let objectDef = message.objectDef
        client.sprite.ensureObject(objectDef.id)
        if not client.sprite.objects[objectDef.id].present:
          client.sprite.appendObjectOrder(objectDef.id)
        client.sprite.objects[objectDef.id] = ObjectState(
          present: true,
          x: objectDef.x,
          y: objectDef.y,
          z: objectDef.z,
          layer: objectDef.layer,
          spriteId: objectDef.spriteId,
          orderPrev: client.sprite.objects[objectDef.id].orderPrev,
          orderNext: client.sprite.objects[objectDef.id].orderNext
        )
      of spkDeleteObject:
        let objectId = message.objectId
        if objectId >= 0 and objectId < client.sprite.objects.len:
          if client.sprite.objects[objectId].present:
            client.sprite.removeObjectOrder(objectId)
            client.sprite.objects[objectId].present = false
      of spkClearObjects:
        for item in client.sprite.objects.mitems:
          item.present = false
          item.orderPrev = -1
          item.orderNext = -1
        client.sprite.objectOrderHead = -1
        client.sprite.objectOrderTail = -1
      of spkViewport, spkLayer:
        discard
  except SpriteProtocolError:
    return false
  true

proc applyFrame*(client: ProtocolClient, packet: string): bool =
  ## Applies exactly one inbound Sprite-v1 websocket frame.
  ##
  ## This is the decision boundary used by the Python SDK: one successful
  ## world-changing packet produces one policy decision.  It is exported so
  ## the differential replay runner can drive the native policy with captured
  ## production packets without a websocket or a second protocol decoder.
  client.applySpritePacket(packet)
