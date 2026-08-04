## Firefight hysteresis, scored gun targets, and local focus claims.

import std/[algorithm, math, options, tables]
import belief_state, config, squads, types, worldmap

proc distance(a, b: Point): float = hypot((a.x - b.x).float, (a.y - b.y).float)

proc enemyDeaths(belief: Belief): Option[int] =
  if belief.worldmap.isNil:
    return none(int)
  let lives = belief.enemyLivesLeft
  if lives.isNone: none(int)
  else: some(belief.worldmap.teamTotalLives - lives.get)

proc rangeBucket*(distancePx: float): string =
  if distancePx < 200: "0_199"
  elif distancePx < 300: "200_299"
  elif distancePx < 400: "300_399"
  else: "400_plus"

proc lineClear*(belief: Belief, origin, target: Point): bool =
  belief.worldmap.isNil or belief.worldmap.rayClear(origin, target)

proc targetRefFor*(belief: Belief, enemy: Enemy): TargetRef =
  var identity = enemy.identity
  if identity.isNone:
    for track in belief.enemyTracks:
      if track.lastTick == belief.tick and track.pos == enemy.pos:
        identity = track.identity
        break
  TargetRef(identity: identity, pos: enemy.pos)

proc enemyMatchesRef(belief: Belief, enemy: Enemy, target: TargetRef): bool =
  if target.identity.isSome:
    if enemy.identity == target.identity: return true
    if enemy.identity.isSome: return false
    for track in belief.enemyTracks:
      if track.identity == target.identity and track.lastTick == belief.tick and
          track.pos == enemy.pos:
        return true
    return false
  if enemy.identity.isSome:
    return distance(enemy.pos, target.pos) <= FirefightClaimMatchPx.float
  let age = if belief.firefightTargetLastSeenTick >= 0:
    max(0, belief.tick - belief.firefightTargetLastSeenTick) else: 0
  let reach = age.float * MaxSpeedPxTick + TrackMatchSlackPx.float
  distance(enemy.pos, target.pos) <= max(FirefightClaimMatchPx.float, reach)

proc refsMatch*(belief: Belief, left, right: TargetRef): bool =
  if left.identity.isSome and right.identity.isSome:
    return left.identity == right.identity
  if distance(left.pos, right.pos) <= FirefightClaimMatchPx.float:
    return true
  for enemy in belief.enemies:
    if belief.enemyMatchesRef(enemy, left) and belief.enemyMatchesRef(enemy, right):
      return true

proc visibleTarget(
  belief: Belief, target: TargetRef
): Option[tuple[enemy: Enemy, target: TargetRef]] =
  var
    found = false
    best: Enemy
    bestDistance = Inf
  for enemy in belief.enemies:
    if belief.enemyMatchesRef(enemy, target):
      let d = distance(enemy.pos, target.pos)
      if d < bestDistance:
        found = true
        best = enemy
        bestDistance = d
  if found: some((best, belief.targetRefFor(best)))
  else: none(tuple[enemy: Enemy, target: TargetRef])

proc claimIsLocal(belief: Belief, claim: FocusClaim): bool =
  if belief.selfXy.isNone: return false
  let visible = belief.visibleTarget(claim.target)
  if visible.isSome:
    return distance(belief.selfXy.get, visible.get.enemy.pos) <=
      FirefightClaimLocalityPx.float
  var bestDistance = Inf
  for track in belief.enemyTracks:
    if belief.tick - track.lastTick > FirefightTargetMissingTicks:
      continue
    let matches = if claim.target.identity.isSome:
      track.identity == claim.target.identity
    else:
      distance(track.pos, claim.target.pos) <= FirefightClaimMatchPx.float
    if matches:
      bestDistance = min(bestDistance, distance(belief.selfXy.get, track.pos))
  if bestDistance < Inf:
    return bestDistance <= FirefightClaimLocalityPx.float
  distance(belief.selfXy.get, claim.target.pos) <= FirefightClaimLocalityPx.float

proc rangeTerm(distancePx: float): float =
  let idealMin = min(FirefightRangeIdealMinPx, FirefightRangeScoreFalloffPx)
  let idealMax = min(max(FirefightRangeIdealMaxPx, idealMin), FirefightRangeScoreFalloffPx)
  let close = min(FirefightRangeClosePx, idealMin)
  if distancePx <= close.float or distancePx > FirefightRangeScoreFalloffPx.float:
    return 0.0
  if distancePx < idealMin.float:
    return (distancePx - close.float) / max((idealMin - close).float, 1.0)
  if distancePx <= idealMax.float:
    return 1.0
  (FirefightRangeScoreFalloffPx.float - distancePx) /
    max((FirefightRangeScoreFalloffPx - idealMax).float, 1.0)

proc woundTerm(enemy: Enemy): float =
  if enemy.hpSegments.isNone: FirefightWoundUnknown
  else: (3 - enemy.hpSegments.get).float / 2.0

proc scoreTarget*(candidate: TargetCandidate, claimed: bool): TargetScore =
  let
    wound = woundTerm(candidate.enemy)
    rangeBand = rangeTerm(candidate.distancePx)
    claim = if claimed: 1.0 else: 0.0
    shootability = if candidate.shootable: 1.0 else: -1.0
    shield = if candidate.enemy.shielded: 1.0 else: 0.0
    score = FirefightWoundWeight * wound + FirefightRangeWeight * rangeBand +
      FirefightClaimWeight * claim + FirefightShootabilityWeight * shootability -
      FirefightAimCostWeight * candidate.aimCost - FirefightShieldWeight * shield
  TargetScore(candidate: candidate, score: score, wound: wound,
    rangeBand: rangeBand, claim: claim, shootability: shootability,
    aimCost: candidate.aimCost, shield: shield)

proc scoreCmp(a, b: TargetScore): int =
  result = cmp(b.score, a.score)
  if result != 0: return
  let aKnown = if a.candidate.target.identity.isSome: 0 else: 1
  let bKnown = if b.candidate.target.identity.isSome: 0 else: 1
  result = cmp(aKnown, bKnown)
  if result != 0: return
  let aIdentity = if a.candidate.target.identity.isSome:
    a.candidate.target.identity.get else: 8
  let bIdentity = if b.candidate.target.identity.isSome:
    b.candidate.target.identity.get else: 8
  result = cmp(aIdentity, bIdentity)
  if result != 0: return
  result = cmp(a.candidate.target.pos.y div NavCell,
               b.candidate.target.pos.y div NavCell)
  if result == 0:
    result = cmp(a.candidate.target.pos.x div NavCell,
                 b.candidate.target.pos.x div NavCell)

proc claimedTarget(belief: Belief, target: TargetRef): bool =
  FocusClaims and belief.focusClaim.isSome and
    belief.claimIsLocal(belief.focusClaim.get) and
    belief.refsMatch(belief.focusClaim.get.target, target)

proc recordSelectedTarget(belief: Belief, selected: TargetScore) =
  let target = selected.candidate.target
  let changed = belief.firefightTarget.isSome and
    not belief.refsMatch(belief.firefightTarget.get, target)
  if changed:
    inc belief.firefightTargetSwitches
    belief.firefightTargetSelectedTick = belief.tick
  elif belief.firefightTarget.isNone:
    belief.firefightTargetSelectedTick = belief.tick
  belief.firefightTarget = some(target)
  belief.firefightTargetScore = some(selected)
  belief.firefightTargetLastSeenTick = belief.tick
  belief.firefightTargetRangeCounts.inc(rangeBucket(selected.candidate.distancePx))

proc selectTarget*(
  belief: Belief, candidates: openArray[TargetCandidate]
): Option[TargetScore] =
  if not Firefight or not belief.firefightActive or candidates.len == 0:
    belief.firefightTargetScore = none(TargetScore)
    return none(TargetScore)
  var scored: seq[TargetScore]
  for candidate in candidates:
    scored.add(scoreTarget(candidate, belief.claimedTarget(candidate.target)))
  scored.sort(scoreCmp)
  let best = scored[0]
  if belief.firefightTarget.isNone:
    belief.recordSelectedTarget(best)
    return some(best)
  var current = none(TargetScore)
  for item in scored:
    if belief.refsMatch(belief.firefightTarget.get, item.candidate.target):
      current = some(item)
      break
  if current.isNone:
    belief.recordSelectedTarget(best)
    return some(best)
  if belief.refsMatch(current.get.candidate.target, best.candidate.target):
    belief.recordSelectedTarget(current.get)
    return current
  let age = belief.tick - belief.firefightTargetSelectedTick
  let immediate = not current.get.candidate.shootable and best.candidate.shootable
  let materiallyBetter = age >= FirefightTargetMinDwellTicks and
    best.score >= current.get.score + FirefightTargetSwitchMargin
  let selected = if immediate or materiallyBetter: best else: current.get
  belief.recordSelectedTarget(selected)
  some(selected)

proc releaseFocusClaim*(belief: Belief, reason: string) =
  if belief.focusClaim.isNone: return
  belief.focusClaim = none(FocusClaim)
  belief.focusLastReleaseReason = reason
  belief.focusClaimReleaseCounts.inc(reason)

proc receiveFocusClaim*(
  belief: Belief, claimantSeat: int, targetIdentity: Option[int], targetCell: Point
) =
  if not Firefight or not FocusClaims or claimantSeat == belief.seat: return
  inc belief.focusClaimsHeard
  let incomingTarget = TargetRef(identity: targetIdentity, pos: targetCell)
  let incoming = FocusClaim(
    claimantSeat: claimantSeat, target: incomingTarget,
    firstTick: belief.tick, refreshedTick: belief.tick,
    lastSeenTick: belief.tick, enemyDeathsAtLastSeen: belief.enemyDeaths)
  if not belief.claimIsLocal(incoming): return
  if belief.focusClaim.isSome and
      belief.tick - belief.focusClaim.get.refreshedTick > FirefightClaimTtlTicks:
    belief.releaseFocusClaim("claim_ttl")
  if belief.focusClaim.isNone:
    belief.focusClaim = some(incoming)
    return
  let current = belief.focusClaim.get
  let sameTarget = belief.refsMatch(current.target, incomingTarget)
  if current.claimantSeat == claimantSeat and sameTarget:
    # Preserve Python's `incoming.identity or current.identity` behavior: badge
    # zero is false and therefore falls back to the current identity.
    let identity = if incomingTarget.identity.isSome and incomingTarget.identity.get != 0:
      incomingTarget.identity else: current.target.identity
    belief.focusClaim = some(FocusClaim(
      claimantSeat: current.claimantSeat,
      target: TargetRef(identity: identity, pos: incomingTarget.pos),
      firstTick: current.firstTick, refreshedTick: belief.tick,
      lastSeenTick: belief.tick, enemyDeathsAtLastSeen: belief.enemyDeaths))
    return
  if current.firstTick == belief.tick:
    let currentRank = (belief.rankOf(current.claimantSeat), current.claimantSeat)
    let incomingRank = (belief.rankOf(claimantSeat), claimantSeat)
    if incomingRank < currentRank:
      belief.focusClaim = some(incoming)
      return
  inc belief.focusClaimsSuppressed

proc focusClaimToSend*(belief: Belief): Option[TargetRef] =
  if not Firefight or not FocusClaims or not belief.firefightActive or
      belief.iHaveArc or belief.firefightTargetScore.isNone or
      belief.tick - belief.focusLastClaimSentTick < FirefightClaimRebroadcastTicks:
    return none(TargetRef)
  let target = belief.firefightTargetScore.get.candidate.target
  if belief.focusClaim.isNone:
    return some(target)
  let claim = belief.focusClaim.get
  if claim.claimantSeat == belief.seat and belief.refsMatch(claim.target, target):
    return some(target)
  if belief.claimIsLocal(claim):
    inc belief.focusClaimsSuppressed
    return none(TargetRef)
  some(target)

proc noteFocusClaimSent*(belief: Belief, target: TargetRef) =
  let firstTick = if belief.focusClaim.isSome and
      belief.focusClaim.get.claimantSeat == belief.seat and
      belief.refsMatch(belief.focusClaim.get.target, target):
    belief.focusClaim.get.firstTick else: belief.tick
  belief.focusClaim = some(FocusClaim(
    claimantSeat: belief.seat, target: target, firstTick: firstTick,
    refreshedTick: belief.tick, lastSeenTick: belief.tick,
    enemyDeathsAtLastSeen: belief.enemyDeaths))
  belief.focusLastClaimSentTick = belief.tick
  inc belief.focusClaimsSent

proc updateClaimLifecycle(belief: Belief) =
  if belief.focusClaim.isNone: return
  var claim = belief.focusClaim.get
  if belief.tick - claim.refreshedTick > FirefightClaimTtlTicks:
    belief.releaseFocusClaim("claim_ttl")
    return
  let visible = belief.visibleTarget(claim.target)
  if visible.isSome:
    claim.target = visible.get.target
    claim.lastSeenTick = belief.tick
    claim.enemyDeathsAtLastSeen = belief.enemyDeaths
    belief.focusClaim = some(claim)
    return
  let missing = belief.tick - claim.lastSeenTick
  let deaths = belief.enemyDeaths
  let deathCorrelated = deaths.isSome and claim.enemyDeathsAtLastSeen.isSome and
    deaths.get > claim.enemyDeathsAtLastSeen.get
  if missing >= FirefightDeathMissingTicks and deathCorrelated:
    belief.releaseFocusClaim("scoreboard_death")
  elif missing >= FirefightTargetMissingTicks:
    belief.releaseFocusClaim("target_missing")

proc updateFirefight*(belief: Belief) =
  if not Firefight: return
  if not belief.alive or belief.selfXy.isNone:
    if belief.focusClaim.isSome and belief.focusClaim.get.claimantSeat == belief.seat:
      belief.releaseFocusClaim("claimant_dead")
    belief.firefightActive = false
    belief.firefightTarget = none(TargetRef)
    belief.firefightTargetScore = none(TargetScore)
    belief.firefightTargetSelectedTick = -1
    belief.firefightTargetLastSeenTick = -1
    belief.updateClaimLifecycle()
    return
  var trigger = belief.underFire
  if not trigger:
    for enemy in belief.enemies:
      if distance(belief.selfXy.get, enemy.pos) <= FirefightRadiusPx.float:
        trigger = true
        break
  if trigger: belief.firefightLastTriggerTick = belief.tick
  let wouldBeActive = trigger or
    belief.tick - belief.firefightLastTriggerTick <= FirefightDwellTicks
  if belief.iHaveArc:
    if wouldBeActive: inc belief.firefightArcExemptTicks
    belief.firefightActive = false
    belief.firefightTarget = none(TargetRef)
    belief.firefightTargetScore = none(TargetScore)
    belief.updateClaimLifecycle()
    return
  if not belief.firefightActive and trigger:
    belief.firefightActive = true
    belief.firefightEnteredTick = belief.tick
    inc belief.firefightEngagements
    belief.firefightTarget = none(TargetRef)
    belief.firefightTargetScore = none(TargetScore)
    belief.firefightTargetSelectedTick = -1
    belief.firefightTargetLastSeenTick = -1
  elif belief.firefightActive and not wouldBeActive:
    belief.firefightActive = false
    belief.firefightTarget = none(TargetRef)
    belief.firefightTargetScore = none(TargetScore)
    belief.firefightTargetSelectedTick = -1
    belief.firefightTargetLastSeenTick = -1
  if belief.firefightActive: inc belief.firefightTicksTotal
  belief.updateClaimLifecycle()
