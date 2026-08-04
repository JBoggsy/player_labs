## Native stencil entry point.

import
  std/[net, os, strutils],
  whisky,
  protocols,
  policy,
  trace

proc slotFromUrl(url: string): int =
  for part in url.split({'?', '&'}):
    if part.startsWith("slot="):
      try:
        return parseInt(part[5 .. ^1])
      except ValueError:
        return 0

proc run(url: string) =
  let
    endpoint = ensureWsPath(url, "/player")
    slot = slotFromUrl(url)
    policy = newStencilPolicy(slot)
    fastReady = getEnv("STENCIL_FAST_READY") == "1"
    client = initProtocolClient()
    telemetry = newTraceState()
  defer: telemetry.close()
  echo "stencil-nim: slot=", slot, " url=", endpoint

  var everConnected = false
  while true:
    try:
      let socket = newWebSocket(endpoint)
      socket.socket.setSockOpt(OptNoDelay, true, level = IPPROTO_TCP.cint)
      socket.send(spritesOffBlob(), BinaryMessage)
      everConnected = true
      client.reset()
      while true:
        let message = socket.receiveMessage(-1)
        if message.isNone:
          continue
        case message.get.kind
        of BinaryMessage:
          if not client.applyFrame(message.get.data):
            raise newException(ValueError, "Malformed sprite protocol packet.")
        of Ping:
          socket.send(message.get.data, Pong)
          continue
        of TextMessage, Pong:
          continue
        let command = policy.decide(client)
        telemetry.record(policy, command)
        socket.send(inputBlob(command.heldMask), BinaryMessage)
        if command.chat.len > 0:
          socket.send(chatBlob(command.chat), BinaryMessage)
        if fastReady:
          socket.send(readyBlob(), BinaryMessage)
    except Exception as error:
      if everConnected:
        echo "stencil-nim: game over, exiting: ", error.msg
        return
      echo "stencil-nim: connect retry: ", error.msg
      sleep(250)

when isMainModule:
  let url = getEnv("COWORLD_PLAYER_WS_URL", getEnv("COGAMES_ENGINE_WS_URL"))
  if url.len == 0:
    raise newException(ValueError, "COWORLD_PLAYER_WS_URL is required")
  run(url)
