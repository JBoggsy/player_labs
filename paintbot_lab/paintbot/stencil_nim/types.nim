## Shared native stencil runtime types.

import std/[math, options, tables]

type
  Point* = tuple[x, y: int]

  Team* = enum
    Red
    Blue
    Green
    Yellow

  Role* = enum
    Attacker
    Defender

  Facing* = enum
    FacingLeft
    FacingRight

  EnemyWeapon* = enum
    WeaponUnknown
    WeaponGun
    WeaponSpray

  Loadout* = object
    weapon*: EnemyWeapon
    grenade*: bool
    shield*: bool
    barrier*: bool

  TrackSource* = enum
    TrackVisual
    TrackTeamShout
    TrackEnemyBubble

  Enemy* = object
    pos*: Point
    facing*: Facing
    aimBrads*: Option[int]
    color*: Team
    identity*: Option[int]
    hpSegments*: Option[int]
    weapon*: EnemyWeapon
    hasGrenade*: bool
    hasBarrier*: bool
    shielded*: bool

  HeardImpact* = object
    kind*: string
    pos*: Point
    firstTick*: int
    lastTick*: int

  PlayerTrack* = object
    pos*: Point
    lastTick*: int
    facing*: Facing
    aimBrads*: Option[int]
    color*: Team
    vel*: Option[tuple[x, y: float]]
    framesSeen*: int
    identity*: Option[int]
    hpSegments*: Option[int]
    weapon*: EnemyWeapon
    hasGrenade*: bool
    hasBarrier*: bool
    shielded*: bool
    source*: TrackSource

  TargetRef* = object
    identity*: Option[int]
    pos*: Point

  FocusClaim* = object
    claimantSeat*: int
    target*: TargetRef
    firstTick*: int
    refreshedTick*: int
    lastSeenTick*: int
    enemyDeathsAtLastSeen*: Option[int]

  TargetCandidate* = object
    enemy*: Enemy
    target*: TargetRef
    aimPos*: Point
    leadBrads*: int
    distancePx*: float
    aimCost*: float
    lineClear*: bool
    teammateBlocked*: bool
    shootable*: bool

  TargetScore* = object
    candidate*: TargetCandidate
    score*, genericScore*: float
    wound*: float
    rangeBand*: float
    claim*: float
    shootability*: float
    aimCost*: float
    shield*: float
    spray*: float
    defensiveThreat*, heartDistancePx*: float

  SprayFleeScore* = object
    point*: Point
    score*: float
    threatGain*: float
    coverPath*: float
    clumpRisk*: float
    centerTerm*: float

  HeartState* = object
    planted*: bool
    pos*: Option[Point]
    carriedPos*: Option[Point]

  EndzoneMarker* = object
    shape*: string
    x0*, y0*, x1*, y1*: int

  BarrageState* = object
    depth*, rate*, startSec*, saturateSec*: int

  VisibleItem* = tuple[kind: string, pos: Point]
  HeardSound* = tuple[kind: string, pos: Point]
  HeardShout* = tuple[team, address, text: string, pos: Point]

  PaintState* = object
    ready*: bool
    selfXy*: Option[Point]
    selfColor*: Option[Team]
    selfFacing*: Option[Facing]
    observedAim*: Option[int]
    fireReady*: bool
    enemies*: seq[Enemy]
    teammates*: seq[Enemy]
    hearts*: Table[Team, HeartState]
    iCarryHeartOf*: Option[Team]
    gameTeams*: Option[int]
    mapSize*: Option[Point]
    endzones*: Table[Team, EndzoneMarker]
    walkability*: seq[bool]
    walkabilityWidth*: int
    walkabilityHeight*: int
    walkabilityDecodeMs*: float
    visibleItems*: seq[VisibleItem]
    heardImpacts*: seq[HeardSound]
    heardShouts*: seq[HeardShout]
    hpPips*: Option[int]
    iHaveGrenade*: bool
    iHaveShield*: bool
    iHaveArc*: bool
    teamScores*: Table[Team, tuple[kills, deaths: int]]
    barrage*: Option[BarrageState]

  ItemKind* = enum
    Arc
    Grenade
    Medkit
    Shield

  ItemSpawn* = object
    kind*: ItemKind
    pos*: Point
    present*: bool
    absentUntil*: int
    lastSeen*: int

  ItemOption* = object
    spawnIndex*: int
    anchor*: Point
    anchorKind*: string
    routeToItemPx*: float
    routeViaItemPx*: float
    directRoutePx*: float
    detourPx*: float
    thresholdPx*: float
    accepted*: bool
    reason*: string

  ActionState* = object
    lastRot*: int
    aHeld*: bool
    fireHoldTicks*: int

  IntentKind* = enum
    NavigateTo
    Hold

  CostProfileKind* = enum
    ProfileDefault
    ProfileCarrier
    ProfileHunter

  MicroFlag* = enum
    MicroPeekDuck
    MicroSeparation
    MicroFormationBias
    MicroSprayPursuit
    MicroStealRushExempt

  Intent* = object
    kind*: IntentKind
    point*: Option[Point]
    idleAimCenterBrads*: Option[int]
    arriveRadius*: float
    reason*: string
    movingGoal*: bool
    clampToEndzone*: bool
    suppressFireFreeze*: bool
    profile*: CostProfileKind
    micro*: set[MicroFlag]

  Command* = object
    heldMask*: uint8
    chat*: string

proc teamName*(team: Team): string =
  case team
  of Red: "red"
  of Blue: "blue"
  of Green: "green"
  of Yellow: "yellow"

proc parseTeam*(name: string): Option[Team] =
  case name
  of "red": some(Red)
  of "blue": some(Blue)
  of "green": some(Green)
  of "yellow": some(Yellow)
  else: none(Team)

proc teamForSlot*(slot, teams: int): Team =
  Team(slot mod teams)

proc pyRound*(value: float): int =
  ## Python/NumPy integer rounding: nearest, with exact half ties to even.
  ## Nim's stdlib `round` instead sends half ties away from zero.
  let lower = floor(value).int
  let fraction = value - lower.float
  if fraction < 0.5:
    lower
  elif fraction > 0.5:
    lower + 1
  elif (lower and 1) == 0:
    lower
  else:
    lower + 1
