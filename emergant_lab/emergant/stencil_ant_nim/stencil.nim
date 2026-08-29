## Native stencil entry point.

import
  std/[base64, json, net, os, strutils],
  whisky,
  protocols,
  policy,
  trace

type WireRecorder = ref object
  file: File

proc newWireRecorder(): WireRecorder =
  let path = getEnv("STENCIL_WIRE_RECORD")
  if path.len > 0:
    result = WireRecorder(file: open(path, fmWrite))

proc record(recorder: WireRecorder, direction: string, data: string) =
  if recorder.isNil: return
  recorder.file.writeLine($(%*{
    "direction": direction,
    "type": "binary",
    "data": encode(data),
  }))
  recorder.file.flushFile()

proc close(recorder: WireRecorder) =
  if not recorder.isNil: recorder.file.close()

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
    recorder = newWireRecorder()
  defer: telemetry.close()
  defer: recorder.close()
  echo "stencil-nim: slot=", slot, " url=", endpoint

  var everConnected = false
  while true:
    try:
      let socket = newWebSocket(endpoint)
      socket.socket.setSockOpt(OptNoDelay, true, level = IPPROTO_TCP.cint)
      let spritesOff = spritesOffBlob()
      recorder.record("out", spritesOff)
      socket.send(spritesOff, BinaryMessage)
      everConnected = true
      client.reset()
      while true:
        let message = socket.receiveMessage(-1)
        if message.isNone:
          continue
        case message.get.kind
        of BinaryMessage:
          recorder.record("in", message.get.data)
          if not client.applyFrame(message.get.data):
            raise newException(ValueError, "Malformed sprite protocol packet.")
        of Ping:
          socket.send(message.get.data, Pong)
          continue
        of TextMessage, Pong:
          continue
        let command = policy.decide(client)
        telemetry.record(policy, command)
        let input = inputBlob(command.heldMask)
        recorder.record("out", input)
        socket.send(input, BinaryMessage)
        if command.chat.len > 0:
          let chat = chatBlob(command.chat)
          recorder.record("out", chat)
          socket.send(chat, BinaryMessage)
        if fastReady:
          let ready = readyBlob()
          recorder.record("out", ready)
          socket.send(ready, BinaryMessage)
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
