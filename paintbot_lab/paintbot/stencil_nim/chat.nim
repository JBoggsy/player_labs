## Stencil's compact ten-character team shout protocol.

import std/[math, options, strutils, tables]
import belief_state, config, fight, types, worldmap

const
  Base36 = "0123456789abcdefghijklmnopqrstuvwxyz"
  OrderKinds* = ['H', 'W', 'M']

type ChatMessage* = object
  kind*: string
  pos*: Point
  heading*: Option[int]
  seat*: Option[int]
  epoch*: Option[int]
  directive*: Option[SquadDirective]
  targetIdentity*: Option[int]

proc encode2(value: int): string =
  result.add(Base36[(value div 36) mod 36])
  result.add(Base36[value mod 36])

proc decode2(value: string): Option[int] =
  if value.len < 2:
    return none(int)
  let highDigit = Base36.find(value[0])
  let lowDigit = Base36.find(value[1])
  if highDigit < 0 or lowDigit < 0:
    return none(int)
  some(highDigit * 36 + lowDigit)

proc encodeCell*(map: WorldMap, pos: Point): string =
  encode2(clamp(pos.x div NavCell, 0, map.gridW - 1)) &
    encode2(clamp(pos.y div NavCell, 0, map.gridH - 1))

proc decodeCell*(map: WorldMap, code: string): Option[Point] =
  if code.len < 4:
    return none(Point)
  let gx = decode2(code[0 .. 1])
  let gy = decode2(code[2 .. 3])
  if gx.isNone or gy.isNone or gx.get >= map.gridW or gy.get >= map.gridH:
    return none(Point)
  some((gx.get * NavCell + NavCell div 2, gy.get * NavCell + NavCell div 2))

proc encode*(map: WorldMap, kind: string, pos: Point, heading = 0): string =
  let prefix = case kind
    of "enemy": "E"
    of "under_fire": "U"
    of "grenade": "G"
    of "carrier": "C"
    of "thief": "T"
    else: raise newException(ValueError, "unknown chat kind: " & kind)
  result = prefix & map.encodeCell(pos)
  if kind == "carrier":
    result.add($(floorMod(heading, 8)))

proc encodeConsensus(
  map: WorldMap, prefix: char, seat, epoch: int, directive: SquadDirective
): string =
  if directive.kind notin OrderKinds:
    raise newException(ValueError, "unknown squad directive")
  $prefix & $(floorMod(seat, 8)) & $Base36[floorMod(epoch, 36)] &
    $directive.kind & map.encodeCell(directive.pos) & $ord(directive.opponent)

proc encodeProposal*(
  map: WorldMap, seat, epoch: int, directive: SquadDirective
): string =
  map.encodeConsensus('Q', seat, epoch, directive)

proc encodeVote*(
  map: WorldMap, seat, epoch: int, directive: SquadDirective
): string =
  map.encodeConsensus('V', seat, epoch, directive)

proc encodeCommit*(
  map: WorldMap, seat, epoch: int, directive: SquadDirective
): string =
  map.encodeConsensus('C', seat, epoch, directive)

proc encodePing*(map: WorldMap, seat: int, pos: Point): string =
  "P" & $(floorMod(seat, 8)) & map.encodeCell(pos)

proc encodeFocusClaim*(map: WorldMap, seat: int, target: TargetRef): string =
  if target.identity.isSome:
    "FI" & $(floorMod(seat, 8)) & $(floorMod(target.identity.get, 8)) &
      map.encodeCell(target.pos)
  else:
    "FC" & $(floorMod(seat, 8)) & map.encodeCell(target.pos)

proc digitValue(character: char): int = ord(character) - ord('0')

proc decode*(map: WorldMap, text: string): Option[ChatMessage] =
  if text.len == 0:
    return none(ChatMessage)
  if text.startsWith("FI") and text.len >= 8 and text[2].isDigit and text[3].isDigit:
    let pos = map.decodeCell(text[4 .. 7])
    if pos.isSome:
      return some(ChatMessage(kind: "focus_claim", pos: pos.get,
        seat: some(digitValue(text[2])), targetIdentity: some(digitValue(text[3]))))
    return none(ChatMessage)
  if text.startsWith("FC") and text.len >= 7 and text[2].isDigit:
    let pos = map.decodeCell(text[3 .. 6])
    if pos.isSome:
      return some(ChatMessage(kind: "focus_claim", pos: pos.get,
        seat: some(digitValue(text[2]))))
    return none(ChatMessage)
  if text[0] in {'Q', 'V', 'C'} and text.len >= 9 and text[1].isDigit and
      text[3] in OrderKinds and text[8].isDigit:
    let
      epoch = Base36.find(text[2])
      opponent = digitValue(text[8])
      pos = map.decodeCell(text[4 .. 7])
    if pos.isSome and epoch >= 0 and opponent >= 0 and opponent <= ord(high(Team)):
      return some(ChatMessage(
        kind: (case text[0]
          of 'Q': "squad_proposal"
          of 'V': "squad_vote"
          else: "squad_commit"),
        pos: pos.get,
        seat: some(digitValue(text[1])), epoch: some(epoch),
        directive: some(SquadDirective(
          kind: text[3], pos: pos.get, opponent: Team(opponent)))))
    return none(ChatMessage)
  if text[0] == 'P' and text.len >= 6 and text[1].isDigit:
    let pos = map.decodeCell(text[2 .. 5])
    if pos.isSome:
      return some(ChatMessage(kind: "ping", pos: pos.get,
        seat: some(digitValue(text[1]))))
    return none(ChatMessage)
  let kind = case text[0]
    of 'E': "enemy"
    of 'U': "under_fire"
    of 'G': "grenade"
    of 'C': "carrier"
    of 'T': "thief"
    else: return none(ChatMessage)
  if text.len < 5:
    return none(ChatMessage)
  let pos = map.decodeCell(text[1 .. 4])
  if pos.isNone:
    return none(ChatMessage)
  var message = ChatMessage(kind: kind, pos: pos.get)
  if kind == "carrier" and text.len >= 6 and text[5].isDigit:
    message.heading = some(digitValue(text[5]) mod 8)
  some(message)

proc headingOctant*(velocity: Option[tuple[x, y: float]]): int =
  if velocity.isNone or
      (abs(velocity.get.x) < 0.2 and abs(velocity.get.y) < 0.2):
    return 0
  floorMod(pyRound(arctan2(-velocity.get.y, velocity.get.x) / (PI / 4.0)), 8)

proc chooseShout*(belief: Belief): Option[string] =
  if belief.selfXy.isNone or belief.worldmap.isNil:
    return none(string)
  let tick = belief.tick
  if tick - belief.chatLastSentTick < ChatMinIntervalTicks:
    return none(string)
  var
    message = ""
    kind = ""
  let voteDue = SquadCommand and belief.consensusVote.isSome and
    tick - belief.lastVoteSentTick >= ConsensusRebroadcastTicks
  let proposalDue = SquadCommand and belief.consensusProposal.isSome and
    tick - belief.lastProposalSentTick >= ConsensusRebroadcastTicks
  let commitDue = SquadCommand and belief.order.isSome and
    belief.orderSource == "consensus" and
    tick - belief.order.get.setTick <= ConsensusCommitEchoTicks and
    tick - belief.lastCommitSentTick >= ConsensusRebroadcastTicks
  if belief.iCarryHeartOf.isSome:
    var velocity = none(tuple[x, y: float])
    if belief.nav.lastXy.isSome:
      velocity = some(((belief.selfXy.get.x - belief.nav.lastXy.get.x).float,
                       (belief.selfXy.get.y - belief.nav.lastXy.get.y).float))
    message = belief.worldmap.encode(
      "carrier", belief.selfXy.get, headingOctant(velocity))
    kind = "carrier"
  elif belief.ownHeartStolen and belief.ownHeartThiefPos.isSome:
    message = belief.worldmap.encode("thief", belief.ownHeartThiefPos.get)
    kind = "thief"
  elif commitDue:
    let order = belief.order.get
    message = belief.worldmap.encodeCommit(
      belief.seat, order.epoch, order.directive)
    kind = "squad_commit"
    belief.lastCommitSentTick = tick
    inc belief.commitsSent
  elif voteDue:
    message = belief.worldmap.encodeVote(
      belief.seat, belief.consensusEpoch, belief.consensusVote.get)
    kind = "squad_vote"
    belief.lastVoteSentTick = tick
    inc belief.votesSent
  elif proposalDue:
    message = belief.worldmap.encodeProposal(
      belief.seat, belief.consensusEpoch, belief.consensusProposal.get)
    kind = "squad_proposal"
    belief.lastProposalSentTick = tick
    inc belief.proposalsSent
  elif belief.throwTarget.isSome and belief.throwChargeTicks > 0:
    message = belief.worldmap.encode("grenade", belief.throwTarget.get)
    kind = "grenade"
  elif belief.underFire and belief.enemies.len == 0:
    message = belief.worldmap.encode("under_fire", belief.selfXy.get)
    kind = "under_fire"
  else:
    let focusTarget = belief.focusClaimToSend
    if focusTarget.isSome:
      message = belief.worldmap.encodeFocusClaim(belief.seat, focusTarget.get)
      kind = "focus_claim"
      belief.noteFocusClaimSent(focusTarget.get)
    elif belief.enemies.len > 0:
      if belief.chatEnemyArmed and
          tick - belief.chatLastEnemyTick >= ChatEnemyReshoutTicks:
        var nearest = belief.enemies[0]
        var best = (nearest.pos.x - belief.selfXy.get.x) *
          (nearest.pos.x - belief.selfXy.get.x) +
          (nearest.pos.y - belief.selfXy.get.y) *
          (nearest.pos.y - belief.selfXy.get.y)
        for index in 1 ..< belief.enemies.len:
          let enemy = belief.enemies[index]
          let distance = (enemy.pos.x - belief.selfXy.get.x) *
            (enemy.pos.x - belief.selfXy.get.x) +
            (enemy.pos.y - belief.selfXy.get.y) *
            (enemy.pos.y - belief.selfXy.get.y)
          if distance < best:
            nearest = enemy
            best = distance
        message = belief.worldmap.encode("enemy", nearest.pos)
        kind = "enemy"
        belief.chatEnemyArmed = false
        belief.chatLastEnemyTick = tick
    elif SquadCommand and tick - belief.lastPingTick >= PingIntervalTicks:
      message = belief.worldmap.encodePing(belief.seat, belief.selfXy.get)
      kind = "ping"
      belief.lastPingTick = tick
      inc belief.pingsSent
  if belief.enemies.len > 0:
    belief.chatEnemySeenTick = tick
  elif tick - belief.chatEnemySeenTick > ChatEnemyRearmTicks:
    belief.chatEnemyArmed = true
  if message.len > 0:
    belief.chatLastSentTick = tick
    belief.chatSentCounts.inc(kind)
    return some(message)
  none(string)
