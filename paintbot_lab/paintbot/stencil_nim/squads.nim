## Roster-aware squads, leaderless order consensus, and multi-team conversion.

import std/[algorithm, math, options, sets, tables]
import belief_state, config, types, worldmap

type Squad* = tuple[name: char, seats: seq[int]]

proc squadTable(belief: Belief): seq[Squad] =
  if belief.colors.len == 2:
    # This parity split matches the disabled ladder's equal four-agent blocks.
    # Normal campaign 2v2-mode invasions now use a 7-seat captain plus 1-seat
    # ally on each team, so static parity can include the ally or exclude owned
    # captain seats. Keep the existing v52 behavior for this controller-only
    # iteration; roster-aware squad discovery is a separate open task.
    let parity = belief.seat mod 2
    @[('A', @[parity, parity + 2]), ('B', @[parity + 4, parity + 6])]
  elif belief.seatsPerTeam <= 4:
    @[('A', @[0, 1]), ('B', @[2, 3])]
  else:
    @[('A', @[0, 1, 2]), ('C', @[3, 4]), ('B', @[5, 6, 7])]

proc squadOf*(belief: Belief, selectedSeat = -1): Squad =
  let seat = if selectedSeat < 0: belief.seat else: selectedSeat
  let squads = squadTable(belief)
  for squad in squads:
    if seat in squad.seats:
      return squad
  squads[^1]

proc rankOf*(belief: Belief, selectedSeat = -1): int =
  let seat = if selectedSeat < 0: belief.seat else: selectedSeat
  let squad = belief.squadOf(seat)
  let rank = squad.seats.find(seat)
  if rank >= 0: rank else: 0

proc squadSize*(belief: Belief): int = belief.squadOf.seats.len
proc consensusQuorum*(belief: Belief): int = belief.squadSize div 2 + 1

proc sectorOffsetBrads*(belief: Belief): int =
  let rank = belief.rankOf
  if rank == 0: return 0
  let sign = if rank mod 2 == 1: 1 else: -1
  sign * SquadSectorBrads * ((rank + 1) div 2)

proc teammatePositions(belief: Belief, squadOnly = false): seq[Point] =
  var mySquad = belief.squadOf.seats.toHashSet
  mySquad.excl(belief.seat)
  for teammate in belief.teammates:
    if squadOnly and (teammate.identity.isNone or teammate.identity.get notin mySquad):
      continue
    result.add(teammate.pos)
  for track in belief.teammateTracks:
    if belief.tick - track.lastTick > TrackTtlTicks div 2 or track.pos in result:
      continue
    if squadOnly and (track.identity.isNone or track.identity.get notin mySquad):
      continue
    result.add(track.pos)

proc buddiesNear*(belief: Belief, radiusPx: float): int =
  let selfXy = belief.selfXy.get
  for pos in belief.teammatePositions:
    if hypot((pos.x - selfXy.x).float, (pos.y - selfXy.y).float) <= radiusPx:
      inc result

proc nearestTo(points: openArray[Point], origin: Point): Point =
  result = points[0]
  var best = (result.x - origin.x) * (result.x - origin.x) +
    (result.y - origin.y) * (result.y - origin.y)
  for index in 1 ..< points.len:
    let distance = (points[index].x - origin.x) * (points[index].x - origin.x) +
      (points[index].y - origin.y) * (points[index].y - origin.y)
    if distance < best:
      best = distance
      result = points[index]

proc separationBias*(belief: Belief): Option[tuple[x, y: float]] =
  if belief.selfXy.isNone:
    return none(tuple[x, y: float])
  let mates = belief.teammatePositions
  if mates.len == 0:
    return none(tuple[x, y: float])
  let selfXy = belief.selfXy.get
  let nearest = nearestTo(mates, selfXy)
  let distance = hypot((nearest.x - selfXy.x).float, (nearest.y - selfXy.y).float)
  if distance > 0.5 and distance < SquadSeparationPx.float:
    return some(((selfXy.x - nearest.x).float / distance,
                 (selfXy.y - nearest.y).float / distance))
  none(tuple[x, y: float])

proc formationBias*(belief: Belief): Option[tuple[x, y: float]] =
  if belief.selfXy.isNone:
    return none(tuple[x, y: float])
  let mates = belief.teammatePositions
  if mates.len == 0:
    return none(tuple[x, y: float])
  let separation = belief.separationBias
  if separation.isSome:
    return separation
  let selfXy = belief.selfXy.get
  let nearest = nearestTo(mates, selfXy)
  let distance = hypot((nearest.x - selfXy.x).float, (nearest.y - selfXy.y).float)
  if belief.buddiesNear(SquadCohesionPx.float) < SquadMinBuddies and
      distance > SquadCohesionPx.float:
    let squadmates = belief.teammatePositions(true)
    let target = if squadmates.len > 0: nearestTo(squadmates, selfXy) else: nearest
    let targetDistance = hypot((target.x - selfXy.x).float, (target.y - selfXy.y).float)
    if targetDistance >= 0.5:
      return some(((target.x - selfXy.x).float / targetDistance,
                   (target.y - selfXy.y).float / targetDistance))
  none(tuple[x, y: float])

proc spreadPoint*(belief: Belief, pos: Point): Point =
  let rank = belief.rankOf
  let offset = if rank == 0: 0 else:
    (if rank mod 2 == 1: 1 else: -1) * SquadSpreadPx * ((rank + 1) div 2)
  let maxY = if belief.worldmap.isNil: pos.y else: belief.worldmap.height - 21
  let point = (pos.x, clamp(pos.y + offset, 20, maxY))
  if offset == 0 or belief.worldmap.isNil:
    return point
  let cover = belief.worldmap.nearestCover(point)
  if cover.isSome: cover.get else: point

proc updatePresence*(belief: Belief) =
  var mySquad = belief.squadOf.seats.toHashSet
  mySquad.excl(belief.seat)
  for teammate in belief.teammates:
    if teammate.identity.isSome and teammate.identity.get in mySquad:
      belief.presence[teammate.identity.get] = belief.tick

proc enemyLivesLeft*(belief: Belief): Option[int] =
  if belief.worldmap.isNil or belief.teamScores.len == 0:
    return none(int)
  let total = belief.seatsPerTeam * LivesPerPlayer
  var best = high(int)
  for color in belief.colors:
    if color == belief.team or not belief.teamScores.hasKey(color):
      continue
    let remaining = max(0, total - belief.teamScores[color].deaths)
    if remaining > 0:
      best = min(best, remaining)
  if best < high(int): some(best) else: none(int)

proc everyEnemyTrailsLives*(belief: Belief): bool =
  ## Team-score deaths are fog-independent. Since every team starts with the
  ## same lives, an enemy has fewer lives exactly when it has more deaths.
  if not belief.teamScores.hasKey(belief.team):
    return false
  let ownDeaths = belief.teamScores[belief.team].deaths
  var foundEnemy = false
  for color in belief.colors:
    if color == belief.team or color in belief.heartsRetired:
      continue
    if not belief.teamScores.hasKey(color) or
        belief.teamScores[color].deaths <= ownDeaths:
      return false
    foundEnemy = true
  foundEnemy

proc weakestEnemyColor*(belief: Belief): Option[Team] =
  if belief.worldmap.isNil or belief.teamScores.len == 0:
    return none(Team)
  let total = belief.seatsPerTeam * LivesPerPlayer
  var bestLives = high(int)
  for color in belief.colors:
    if color == belief.team or not belief.teamScores.hasKey(color):
      continue
    let remaining = max(0, total - belief.teamScores[color].deaths)
    if remaining > 0 and remaining < bestLives:
      bestLives = remaining
      result = some(color)

proc wipeInReach*(belief: Belief): bool =
  let lives = belief.enemyLivesLeft
  lives.isSome and lives.get <= ConvertEnemyLives

proc convertHuntPoint*(belief: Belief): Point =
  if belief.enemies.len > 0:
    return belief.enemies[0].pos
  var newestTick = low(int)
  for track in belief.enemyTracks:
    if belief.tick - track.lastTick <= TrackTtlTicks and track.lastTick > newestTick:
      newestTick = track.lastTick
      result = track.pos
  if newestTick > low(int):
    return
  if not belief.worldmap.isNil:
    let target = belief.weakestEnemyColor
    if target.isSome:
      return belief.worldmap.pedestal(target.get)
    return belief.worldmap.center
  result = if belief.selfXy.isSome: belief.selfXy.get else: (0, 0)

proc squadmatesAlive*(belief: Belief): int =
  var mySquad = belief.squadOf.seats.toHashSet
  mySquad.excl(belief.seat)
  for seat in mySquad:
    if belief.tick - belief.presence.getOrDefault(seat, -10_000) <= PresenceStaleTicks:
      inc result

proc preferredOpponent(belief: Belief): Team =
  if belief.stealTarget.isSome:
    return belief.stealTarget.get
  let weakest = belief.weakestEnemyColor
  if weakest.isSome:
    return weakest.get
  for color in belief.colors:
    if color != belief.team and color notin belief.heartsRetired:
      return color
  for color in belief.colors:
    if color != belief.team:
      return color
  belief.team

proc advancePoint(belief: Belief, stage: int, opponent: Team): Point =
  let map = belief.worldmap
  let enemyHome = map.pedestal(opponent)
  if stage >= 5:
    return enemyHome
  let targets = [0.22, 0.38, 0.55, 0.70, 0.84]
  let targetProgress = targets[clamp(stage, 0, targets.high)]
  let home = map.homeCenter(belief.team)
  let direct = map.routeDistance(home, enemyHome)
  var
    found = false
    best: Point
    bestUtility = Inf
  if classify(direct) != fcInf and direct > 0.0:
    for front in map.postFronts:
      if front.opponent != opponent:
        continue
      for candidate in front.candidates:
        let progress = map.routeDistance(home, candidate.pos) / direct
        if classify(progress) == fcInf:
          continue
        let utility = abs(progress - targetProgress) +
          (1.0 - candidate.score) * 0.12
        if not found or utility < bestUtility:
          found = true
          best = candidate.pos
          bestUtility = utility
  if found:
    return best
  let raw = (
    int(home.x.float + (enemyHome.x - home.x).float * targetProgress),
    int(home.y.float + (enemyHome.y - home.y).float * targetProgress))
  let cover = map.nearestCover(raw, 12)
  if cover.isSome: cover.get else: raw

proc nextProposal(belief: Belief): SquadDirective =
  let opponent = belief.preferredOpponent
  if belief.order.isNone:
    return SquadDirective(kind: 'M',
      pos: belief.advancePoint(belief.squadAdvanceStage, opponent),
      opponent: opponent)
  let current = belief.order.get.directive
  if belief.squadmatesAlive < belief.squadSize - 1:
    let position = if belief.selfXy.isSome:
      belief.worldmap.homeStep(belief.team, belief.selfXy.get, BackoffStepPx)
    else:
      current.pos
    return SquadDirective(kind: 'H', pos: position, opponent: current.opponent)
  case current.kind
  of 'M':
    if belief.orderArrived:
      SquadDirective(kind: 'W', pos: current.pos, opponent: current.opponent)
    else:
      current
  of 'W':
    if belief.squadAdvanceStage >= 5:
      SquadDirective(kind: 'H', pos: current.pos, opponent: current.opponent)
    else:
      SquadDirective(kind: 'M',
        pos: belief.advancePoint(belief.squadAdvanceStage + 1, opponent),
        opponent: opponent)
  of 'H':
    if belief.squadAdvanceStage >= 5:
      SquadDirective(kind: 'W', pos: current.pos, opponent: current.opponent)
    else:
      SquadDirective(kind: 'M',
        pos: belief.advancePoint(belief.squadAdvanceStage, opponent),
        opponent: opponent)
  else:
    SquadDirective(kind: 'H', pos: current.pos, opponent: current.opponent)

proc orderDue(belief: Belief): bool =
  if belief.order.isNone:
    return true
  let age = belief.tick - belief.order.get.setTick
  if age >= OrderTtlTicks:
    return true
  case belief.order.get.directive.kind
  of 'M': belief.orderArrived and age >= SquadMoveMinTicks
  of 'W': age >= SquadWatchTicks
  of 'H': age >= SquadHoldTicks
  else: true

proc canonicalDirective(belief: Belief, directive: SquadDirective): SquadDirective =
  ## Consensus messages quantize points to navigation cells. Store our own
  ## proposal in that same representation so independently received votes are
  ## byte-for-byte comparable to the local vote.
  let map = belief.worldmap
  SquadDirective(
    kind: directive.kind,
    pos: (
      clamp(directive.pos.x div NavCell, 0, map.gridW - 1) * NavCell + NavCell div 2,
      clamp(directive.pos.y div NavCell, 0, map.gridH - 1) * NavCell + NavCell div 2),
    opponent: directive.opponent)

proc beginConsensus*(belief: Belief) =
  if belief.consensusStartedTick >= 0 or belief.worldmap.isNil:
    return
  belief.consensusStartedTick = belief.tick
  belief.consensusState = "proposing"
  belief.consensusProposals.clear()
  belief.consensusVotes.clear()
  belief.consensusVote = none(SquadDirective)
  belief.consensusProposal = some(belief.canonicalDirective(belief.nextProposal))
  belief.consensusProposals[belief.seat] = belief.consensusProposal.get

proc directiveDistance(a, b: SquadDirective): int =
  let dx = a.pos.x - b.pos.x
  let dy = a.pos.y - b.pos.y
  dx * dx + dy * dy

proc consensusChoice(belief: Belief): Option[SquadDirective] =
  if belief.consensusProposals.len < belief.consensusQuorum:
    return none(SquadDirective)
  var
    kindCounts: CountTable[char]
    winningKind = 'H'
    winningCount = -1
  for _, proposal in belief.consensusProposals:
    kindCounts.inc(proposal.kind)
  # Safety is the deterministic tie-break, not sender identity: hold, then
  # watch, then move. No seat has privileged command authority.
  for kind in ['H', 'W', 'M']:
    let count = kindCounts[kind]
    if count > winningCount:
      winningKind = kind
      winningCount = count
  var candidates: seq[SquadDirective]
  for _, proposal in belief.consensusProposals:
    if proposal.kind == winningKind and proposal notin candidates:
      candidates.add(proposal)
  if candidates.len == 0:
    return none(SquadDirective)
  var
    best = candidates[0]
    bestDistance = high(int)
  for candidate in candidates:
    var totalDistance = 0
    for other in candidates:
      totalDistance += directiveDistance(candidate, other)
    if totalDistance < bestDistance or
        (totalDistance == bestDistance and
          (ord(candidate.opponent), candidate.pos.x, candidate.pos.y) <
          (ord(best.opponent), best.pos.x, best.pos.y)):
      best = candidate
      bestDistance = totalDistance
  some(best)

proc alignConsensusEpoch(belief: Belief, epoch: int): bool =
  ## A missed commit must not strand a member on an old wire epoch forever.
  ## Accept only forward movement within half the 36-value ring, so delayed
  ## shouts from an older epoch cannot roll the clock backward.
  let delta = floorMod(epoch - belief.consensusEpoch mod 36, 36)
  if delta == 0:
    return true
  if delta > 18:
    return false
  belief.consensusEpoch += delta
  belief.consensusStartedTick = -1
  belief.consensusState = "resynced"
  belief.consensusProposal = none(SquadDirective)
  belief.consensusVote = none(SquadDirective)
  belief.consensusProposals.clear()
  belief.consensusVotes.clear()
  inc belief.consensusResyncs
  true

proc receiveProposal*(belief: Belief, seat, epoch: int, directive: SquadDirective) =
  if seat == belief.seat or seat notin belief.squadOf.seats or
      not belief.alignConsensusEpoch(epoch):
    return
  if belief.consensusStartedTick < 0:
    belief.beginConsensus()
  belief.consensusProposals[seat] = belief.canonicalDirective(directive)
  belief.presence[seat] = belief.tick
  inc belief.proposalsHeard

proc receiveVote*(belief: Belief, seat, epoch: int, directive: SquadDirective) =
  if seat == belief.seat or seat notin belief.squadOf.seats or
      not belief.alignConsensusEpoch(epoch):
    return
  if belief.consensusStartedTick < 0:
    belief.beginConsensus()
  belief.consensusVotes[seat] = belief.canonicalDirective(directive)
  belief.presence[seat] = belief.tick
  inc belief.votesHeard

proc commitOrder(belief: Belief, directive: SquadDirective) =
  let previous = belief.order
  if previous.isSome and previous.get.directive.kind == 'W' and
      directive.kind == 'M' and belief.squadAdvanceStage < 5:
    inc belief.squadAdvanceStage
  belief.order = some(SquadOrder(
    directive: directive, setTick: belief.tick, epoch: belief.consensusEpoch))
  belief.orderSource = "consensus"
  belief.orderArrived = false
  belief.consensusState = "committed"
  inc belief.consensusCommits
  inc belief.consensusEpoch
  belief.consensusStartedTick = -1
  belief.consensusProposal = none(SquadDirective)
  belief.consensusVote = none(SquadDirective)
  belief.consensusProposals.clear()
  belief.consensusVotes.clear()

proc receiveCommit*(belief: Belief, seat, epoch: int, directive: SquadDirective) =
  if seat == belief.seat or seat notin belief.squadOf.seats or
      not belief.alignConsensusEpoch(epoch):
    return
  let canonical = belief.canonicalDirective(directive)
  # Lock a member's first vote for the epoch. Without that lock, late
  # proposals could change a vote and let two overlapping quorums commit
  # different directives in a three-member squad.
  let choice = if belief.consensusVote.isSome:
      belief.consensusVote
    else:
      belief.consensusChoice
  if (belief.consensusVote.isNone or belief.consensusVote.get != canonical) and
      (choice.isNone or choice.get != canonical):
    return
  belief.presence[seat] = belief.tick
  inc belief.commitsHeard
  belief.commitOrder(canonical)

proc rejoinTarget*(belief: Belief): Option[Point]

proc updateConsensus*(belief: Belief) =
  belief.updatePresence()
  if belief.consensusStartedTick < 0:
    if belief.orderDue:
      belief.beginConsensus()
    elif belief.consensusState == "committed":
      belief.consensusState = "idle"
  if belief.consensusStartedTick < 0:
    return
  if belief.tick - belief.consensusStartedTick >= ConsensusTimeoutTicks:
    inc belief.consensusTimeouts
    belief.consensusStartedTick = -1
    belief.consensusState = "timeout"
    belief.consensusProposal = none(SquadDirective)
    belief.consensusVote = none(SquadDirective)
    belief.consensusProposals.clear()
    belief.consensusVotes.clear()
    # A live member can lose shout contact without dying. Reuse the bounded
    # respawn-rejoin path so an expired consensus pulls it back toward the
    # last observed squad position instead of falling into independent role
    # behavior indefinitely.
    if belief.alive:
      let target = belief.rejoinTarget()
      if target.isSome:
        belief.rejoinPoint = target
        belief.rejoinUntil = belief.tick + RejoinTimeoutTicks
    if belief.order.isSome and belief.tick - belief.order.get.setTick >= OrderTtlTicks:
      belief.order = none(SquadOrder)
      belief.orderSource = ""
    return
  belief.consensusProposals[belief.seat] = belief.consensusProposal.get
  # The first local vote is final for this epoch. Quorum counting and
  # rebroadcast must use that locked value even if later proposals would have
  # produced a different choice.
  let choice = if belief.consensusVote.isSome:
      belief.consensusVote
    else:
      belief.consensusChoice
  if choice.isNone:
    belief.consensusState = "proposing"
    return
  if belief.consensusVote.isNone:
    belief.consensusVote = choice
  belief.consensusVotes[belief.seat] = belief.consensusVote.get
  belief.consensusState = "voting"
  var matching = 0
  for _, vote in belief.consensusVotes:
    if vote == choice.get:
      inc matching
  if matching < belief.consensusQuorum:
    return
  belief.commitOrder(choice.get)

type RankedPost = tuple[post: PostCandidate, utility: float]

proc orderPost*(belief: Belief, directive: SquadDirective): Option[PostCandidate] =
  if belief.worldmap.isNil:
    return none(PostCandidate)
  var ranked: seq[RankedPost]
  for front in belief.worldmap.postFronts:
    if front.opponent != directive.opponent:
      continue
    for candidate in front.candidates:
      let distance = hypot((candidate.pos.x - directive.pos.x).float,
        (candidate.pos.y - directive.pos.y).float)
      if distance <= SquadPostSearchPx.float:
        ranked.add((candidate,
          candidate.score - 0.25 * distance / max(SquadPostSearchPx.float, 1.0)))
  ranked.sort(proc(a, b: RankedPost): int = cmp(b.utility, a.utility))
  var selected: seq[PostCandidate]
  for candidate in ranked:
    var separated = true
    for previous in selected:
      if hypot((candidate.post.pos.x - previous.pos.x).float,
          (candidate.post.pos.y - previous.pos.y).float) <
          SquadPostSeparationPx.float:
        separated = false
        break
    if separated:
      selected.add(candidate.post)
  if selected.len == 0:
    return none(PostCandidate)
  some(selected[min(belief.rankOf, selected.high)])

proc rejoinTarget*(belief: Belief): Option[Point] =
  var mySquad = belief.squadOf.seats.toHashSet
  mySquad.excl(belief.seat)
  var bestTick = -1
  for track in belief.teammateTracks:
    if track.identity.isSome and track.identity.get in mySquad and track.lastTick > bestTick:
      bestTick = track.lastTick
      result = some(track.pos)
  if result.isSome:
    return
  if belief.selfXy.isSome and not belief.worldmap.isNil:
    return some(belief.worldmap.homeStep(
      belief.team, belief.selfXy.get, BackoffStepPx * 2))

proc inSquadContact*(belief: Belief): bool =
  var mySquad = belief.squadOf.seats.toHashSet
  mySquad.excl(belief.seat)
  for teammate in belief.teammates:
    if teammate.identity.isSome and teammate.identity.get in mySquad and
        hypot((teammate.pos.x - belief.selfXy.get.x).float,
              (teammate.pos.y - belief.selfXy.get.y).float) <= RejoinContactPx.float:
      return true
