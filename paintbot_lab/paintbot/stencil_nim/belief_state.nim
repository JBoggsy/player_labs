## Long-lived folded policy state, separated from update logic to avoid cycles.

import std/[options, sets, tables]
import nav, types, worldmap

type
  CarrierFix* = tuple[pos: Point, heading, heardTick: int]
  ThiefFix* = tuple[pos: Point, tick: int]
  GrenadeWarning* = tuple[pos: Point, tick: int]
  SquadDirective* = object
    kind*: char
    pos*: Point
    opponent*: Team
  SquadOrder* = object
    directive*: SquadDirective
    setTick*: int
    epoch*: int

  Belief* = ref object
    team*: Team
    seat*, slot*, tick*, seatsPerTeam*: int
    role*: Role
    holdPoint*: Option[Point]
    defensivePost*, defensivePostDuck*, defensivePostSightlineAim*: Option[Point]
    defensivePostOpponent*: Option[Team]
    defensivePostScore*: float
    defensivePostHeartDistance*: int
    defensivePostForward*: bool
    defensivePostTravelTicks*, defensivePostHoldTicks*: int
    defensivePostFallbacks*: int
    earlyDefenseComplete*: bool
    earlyDefensePoint*: Option[Point]
    selfXy*: Option[Point]
    alive*: bool
    worldmap*: WorldMap
    colors*: seq[Team]
    colorLocked*: bool
    stealTarget*: Option[Team]
    aimBrads*: int
    aimTargetBrads*, aimErrorBrads*: int
    aimLateralErrorPx*, targetRangePx*: float
    fireGateReason*: string
    targetRayClear*, targetTeammateBlocked*: bool
    prevObservedAim*: Option[int]
    fireReady*: bool
    enemies*, teammates*: seq[Enemy]
    hearts*: Table[Team, HeartState]
    iCarryHeartOf*: Option[Team]
    heartsRetired*: HashSet[Team]
    ownHeartStolen*: bool
    ownHeartThiefPos*: Option[Point]
    enemyTracks*, teammateTracks*: seq[PlayerTrack]
    danger*: seq[float32]
    dangerSpreadCarry*: float
    nav*: NavState
    sweepOffset*, sweepDir*: int
    micro*: string
    heardDuck*: bool
    itemSpawns*: seq[ItemSpawn]
    itemOptions*: seq[ItemOption]
    itemChoice*: Option[ItemOption]
    itemOpportunityTicks*, itemFetchTicks*, itemYieldTicks*: int
    itemOptionTicks*, itemReasonTicks*: CountTable[string]
    hpPips*: Option[int]
    teamScores*: Table[Team, tuple[kills, deaths: int]]
    barrage*: Option[BarrageState]
    barrageCenterTicks*: int
    iHaveGrenade*, iHaveShield*, iHaveArc*: bool
    heardEvents*: seq[HeardImpact]
    underFire*: bool
    firefightActive*: bool
    firefightEnteredTick*, firefightLastTriggerTick*: int
    firefightTicksTotal*, firefightEngagements*: int
    firefightTarget*: Option[TargetRef]
    firefightTargetScore*: Option[TargetScore]
    firefightTargetSelectedTick*, firefightTargetLastSeenTick*: int
    firefightTargetSwitches*: int
    defensiveTargetMultiTicks*, defensiveTargetChoiceChanges*: int
    defensiveCarrierOverrideTicks*, defensiveCarrierImmediateSwitches*: int
    focusClaim*: Option[FocusClaim]
    focusLastClaimSentTick*: int
    focusClaimsSent*, focusClaimsHeard*, focusClaimsSuppressed*: int
    focusClaimReleaseCounts*: CountTable[string]
    focusLastReleaseReason*: string
    friendlyFireSuppressed*, aimResyncs*, firingTurns*, sprayPursuitTicks*: int
    visibleGrenadeStarts*, visibleGrenadeReleases*: int
    grenadeTargetStarts*, grenadeTargetReleases*: CountTable[string]
    grenadeTargetedEnemies*, grenadeSafetyVetoes*, grenadeForceReleases*: int
    firefightTargetRangeCounts*, firefightShotRangeCounts*: CountTable[string]
    firefightArcExemptTicks*: int
    chatLastSentTick*: int
    chatEnemyArmed*: bool
    chatLastEnemyTick*, chatEnemySeenTick*: int
    chatSentCounts*, chatHeardCounts*: CountTable[string]
    carrierFix*: Option[CarrierFix]
    thiefFix*: Option[ThiefFix]
    grenadeWarnings*: seq[GrenadeWarning]
    chatProcessed*: Table[string, tuple[text: string, tick: int]]
    chatLastSentText*: string
    squadWaitSince*, squadWaitTicks*, squadCohesionTicks*: int
    order*: Option[SquadOrder]
    orderSource*: string
    orderArrived*: bool
    squadOrderPost*, squadOrderPostDuck*, squadOrderPostSightlineAim*: Option[Point]
    squadOrderPostOpponent*: Option[Team]
    squadOrderPostScore*: float
    squadOrderPostActive*: bool
    presence*: Table[int, int]
    lastPingTick*, lastProposalSentTick*, lastVoteSentTick*, lastCommitSentTick*: int
    rejoinPoint*: Option[Point]
    rejoinUntil*, respawnedTick*: int
    consensusEpoch*, consensusStartedTick*: int
    consensusState*: string
    consensusProposal*, consensusVote*: Option[SquadDirective]
    consensusProposals*, consensusVotes*: Table[int, SquadDirective]
    squadAdvanceStage*: int
    proposalsSent*, proposalsHeard*, votesSent*, votesHeard*: int
    commitsSent*, commitsHeard*: int
    consensusCommits*, consensusTimeouts*, consensusResyncs*: int
    orderFollowTicks*, orderMoveTicks*, orderHoldTicks*, orderWatchTicks*: int
    orderArrivals*: int
    pingsSent*, pingsHeard*: int
    backoffEvents*, rejoinTicks*, convertEvents*: int
    converting*: bool
    leadBrads*, throwChargeTicks*: int
    throwTarget*: Option[Point]
    throwReason*: string
    throwEnemyCount*: int
    throwLiveTarget*: bool

proc newBelief*(slot: int): Belief =
  Belief(
    team: teamForSlot(slot, 2), seat: min(slot div 2, 7), slot: slot,
    seatsPerTeam: 1,
    role: Attacker, colors: @[Red, Blue], sweepDir: 1,
    firefightEnteredTick: -1, firefightLastTriggerTick: -10_000,
    firefightTargetSelectedTick: -1, firefightTargetLastSeenTick: -1,
    focusLastClaimSentTick: -10_000,
    chatLastSentTick: -10_000, chatEnemyArmed: true,
    chatLastEnemyTick: -10_000, chatEnemySeenTick: -10_000,
    squadWaitSince: -1, lastPingTick: -10_000,
    lastProposalSentTick: -10_000, lastVoteSentTick: -10_000,
    lastCommitSentTick: -10_000,
    consensusStartedTick: -1, consensusState: "idle", rejoinUntil: -1,
    respawnedTick: -10_000)
