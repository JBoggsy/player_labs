## Paintbot protocol constants and environment-backed stencil tuning.
##
## Names and defaults mirror config.py. Geometry remains episode-scoped.

import std/[math, os, parseutils, strutils]

proc envInt(name: string, default: int): int =
  let raw = getEnv(name).strip
  if raw.len == 0 or parseInt(raw, result) != raw.len:
    result = default

proc envFloat(name: string, default: float): float =
  let raw = getEnv(name).strip
  if raw.len == 0 or parseFloat(raw, result) != raw.len:
    result = default

proc envBool(name: string, default: bool): bool =
  envInt(name, ord(default)) == 1

proc envTunableBool(name: string, default: bool): bool =
  let raw = getEnv(name)
  if raw.len == 0:
    return default
  case raw.strip.toLowerAscii
  of "0", "false", "off": false
  of "1", "true", "on": true
  else: raise newException(ValueError, name & " must be boolean")

proc envTunableInt(name: string, default, minimum: int, maximum = high(int)): int =
  let raw = getEnv(name).strip
  if raw.len == 0:
    return default
  if parseInt(raw, result) != raw.len or $result != raw:
    raise newException(ValueError, name & " must be an integer")
  if result < minimum:
    raise newException(ValueError, name & " must be >= " & $minimum)
  if result > maximum:
    raise newException(ValueError, name & " must be <= " & $maximum)

proc envTunableFloat(
  name: string, default, minimum: float, maximum = Inf
): float =
  let raw = getEnv(name).strip
  if raw.len == 0:
    return default
  if parseFloat(raw, result) != raw.len or classify(result) in {fcNan, fcInf, fcNegInf}:
    raise newException(ValueError, name & " must be a finite number")
  if result < minimum:
    raise newException(ValueError, name & " must be >= " & $minimum)
  if result > maximum:
    raise newException(ValueError, name & " must be <= " & $maximum)

const
  TeamColors* = ["red", "blue", "green", "yellow"]
  WebSocketPath* = "/player"

  ButtonUp* = 1'u8
  ButtonDown* = 2'u8
  ButtonLeft* = 4'u8
  ButtonRight* = 8'u8
  ButtonSelect* = 16'u8
  ButtonA* = 32'u8
  ButtonB* = 64'u8
  ButtonC* = 128'u8

  NavCell* = 8
  MaxSpeedPxTick* = 2.75
  RenderScale* = 1
  LivesPerPlayer* = 3
  AimBradsTurn* = 256
  AimTurnRate* = 5
  # The wire does not identify the variant. Use the narrowest deployed cone so
  # absence-based item tracking never claims a 4ffa8 pickup was visible when it
  # was actually outside that variant's 45-degree cone.
  GuaranteedVisionConeHalfDeg* = 45
  VisionBubble* = 90
  FireWindupTicks* = 5
  GrenadeRespawnTicks* = 5 * 24
  MedkitRespawnTicks* = 30 * 24
  ShieldRespawnTicks* = 30 * 24
  ArcRespawnTicks* = 30 * 24
  GrenadeChargeTicks* = 24
  GrenadeMinRange* = 30
  GrenadeBlastRadius* = 52
  GrenadeFlightTicks* = 2 * FireWindupTicks
  ItemPickupRange* = 12
  TrackMatchSlackPx* = 16
  TrackVelMaxGapTicks* = 8
  TrackVelEma* = 0.5
  DangerStampRadiusPx* = 16
  DangerTraceDownsample* = 4
  FirefightRangeScoreFalloffPx* = 350
  FirefightRadiusMaxPx* = 400
  GrenadeMinThrowPx* = 90
  GrenadeForceReleaseTicks* = 16
  ArcFireRangePx* = 170
  ArcMaxWidthPx* = 85
  ArcPursuitRangePx* = 400
  ArcIdealRangePx* = 100

let
  SweepHalfArc* = envInt("STENCIL_SWEEP_HALF_ARC", 32)
  AimDeadband* = envInt("STENCIL_AIM_DEADBAND", 2)
  AimResyncSlackBrads* = envInt("STENCIL_AIM_RESYNC_SLACK_BRADS", 8)
  FireSlackPx* = envInt("STENCIL_FIRE_SLACK_PX", 8)
  CloseRangePx* = envInt("STENCIL_CLOSE_RANGE_PX", 220)
  FriendlyFireCorridorPx* = envTunableInt("STENCIL_FF_CORRIDOR_PX", 22, 14)
  ReplanGoalCells* = envInt("STENCIL_REPLAN_GOAL_CELLS", 2)
  StuckTicks* = envInt("STENCIL_STUCK_TICKS", 8)
  DiagEveryTicks* = envInt("STENCIL_DIAG_EVERY_TICKS", 96)
  TrackTtlTicks* = envInt("STENCIL_TRACK_TTL_TICKS", 120)
  DangerDiffusionFactor* = envFloat("STENCIL_DANGER_DIFFUSION_FACTOR", 0.75)
  DangerDecayHalfLifeTicks* = envInt("STENCIL_DANGER_HALF_LIFE_TICKS", 48)
  PeekDuck* = envBool("STENCIL_PEEK_DUCK", true)
  DuckRangePx* = envInt("STENCIL_DUCK_RANGE_PX", 340)
  DuckThreatFreshTicks* = envInt("STENCIL_DUCK_THREAT_FRESH_TICKS", 30)
  PeekTargetFreshTicks* = envInt("STENCIL_PEEK_TARGET_FRESH_TICKS", 24)
  PeekDuckSearchCells* = envInt("STENCIL_PEEK_DUCK_SEARCH_CELLS", 3)
  PeekDuckRushExemptPx* = envInt("STENCIL_PEEK_DUCK_RUSH_EXEMPT_PX", 90)
  LeadAim* = envBool("STENCIL_LEAD_AIM", true)
  LeadTicks* = envFloat("STENCIL_LEAD_TICKS", 3.5)
  LeadMinFrames* = envInt("STENCIL_LEAD_MIN_FRAMES", 3)
  Firefight* = envTunableBool("STENCIL_FIREFIGHT", true)
  FocusClaims* = envTunableBool("STENCIL_FOCUS_CLAIMS", true)
  FirefightRadiusPx* = envTunableInt("STENCIL_FF_RADIUS_PX", 400,
    FirefightRangeScoreFalloffPx, FirefightRadiusMaxPx)
  FirefightDwellTicks* = envTunableInt("STENCIL_FF_DWELL_TICKS", 48, 1)
  FirefightTargetMinDwellTicks* = envTunableInt(
    "STENCIL_FF_TARGET_MIN_DWELL_TICKS", 8, 1)
  FirefightTargetSwitchMargin* = envTunableFloat(
    "STENCIL_FF_TARGET_SWITCH_MARGIN", 0.10, 0.0)
  FirefightRangeClosePx* = envTunableInt("STENCIL_FF_RANGE_CLOSE_PX", 120, 0,
    FirefightRangeScoreFalloffPx)
  FirefightRangeIdealMinPx* = envTunableInt(
    "STENCIL_FF_RANGE_IDEAL_MIN_PX", 220, 0, FirefightRangeScoreFalloffPx)
  FirefightRangeIdealMaxPx* = envTunableInt(
    "STENCIL_FF_RANGE_IDEAL_MAX_PX", 300, 0, FirefightRangeScoreFalloffPx)
  FirefightWoundWeight* = envTunableFloat("STENCIL_FF_WOUND_WEIGHT", 0.50, 0.0)
  FirefightWoundUnknown* = envTunableFloat(
    "STENCIL_FF_WOUND_UNKNOWN", 0.15, 0.0, 1.0)
  FirefightRangeWeight* = envTunableFloat("STENCIL_FF_RANGE_WEIGHT", 0.30, 0.0)
  FirefightClaimWeight* = envTunableFloat("STENCIL_FF_CLAIM_WEIGHT", 0.12, 0.0)
  FirefightShootabilityWeight* = envTunableFloat(
    "STENCIL_FF_SHOOTABILITY_WEIGHT", 0.35, 0.0)
  FirefightAimCostWeight* = envTunableFloat("STENCIL_FF_AIM_COST_WEIGHT", 0.18, 0.0)
  FirefightShieldWeight* = envTunableFloat("STENCIL_FF_SHIELD_WEIGHT", 0.10, 0.0)
  FirefightClaimRebroadcastTicks* = envTunableInt(
    "STENCIL_FF_CLAIM_REBROADCAST_TICKS", 30, 1)
  FirefightClaimTtlTicks* = envTunableInt("STENCIL_FF_CLAIM_TTL_TICKS", 72, 1)
  FirefightClaimMatchPx* = envTunableInt("STENCIL_FF_CLAIM_MATCH_PX", 96, NavCell)
  FirefightClaimLocalityPx* = envTunableInt(
    "STENCIL_FF_CLAIM_LOCALITY_PX", 400, NavCell)
  FirefightTargetMissingTicks* = envTunableInt(
    "STENCIL_FF_TARGET_MISSING_TICKS", 36, 1)
  FirefightDeathMissingTicks* = envTunableInt(
    "STENCIL_FF_DEATH_MISSING_TICKS", 8, 1)
  Items* = envBool("STENCIL_ITEMS", true)
  ItemConvenientDetourPx* = envInt("STENCIL_ITEM_CONVENIENT_DETOUR_PX", 48)
  MedkitConvenientDetourPx* = envInt("STENCIL_MEDKIT_CONVENIENT_DETOUR_PX", 420)
  ItemArcDetourPx* = envInt("STENCIL_ITEM_ARC_DETOUR_PX", 32)
  ItemYieldMarginPx* = envInt("STENCIL_ITEM_YIELD_MARGIN_PX", 16)
  GrenadeThrow* = envBool("STENCIL_GRENADE_THROW", true)
  GrenadeAimErrBrads* = envInt("STENCIL_GRENADE_AIM_ERR_BRADS", 4)
  GrenadeTargetFreshTicks* = envInt("STENCIL_GRENADE_TARGET_FRESH_TICKS", 30)
  GrenadeTeammateFreshTicks* = envInt("STENCIL_GRENADE_TEAMMATE_FRESH_TICKS", 12)
  GrenadeSingleHpMax* = envInt("STENCIL_GRENADE_SINGLE_HP_MAX", 2)
  Hearing* = envBool("STENCIL_HEARING", true)
  HeardMatchPx* = envInt("STENCIL_HEARD_MATCH_PX", 40)
  HeardTtlTicks* = envInt("STENCIL_HEARD_TTL_TICKS", 60)
  HeardDangerHeat* = envFloat("STENCIL_HEARD_DANGER_HEAT", 0.5)
  HeardDangerRadiusPx* = envInt("STENCIL_HEARD_DANGER_RADIUS_PX", 32)
  HeardDuckRangePx* = envInt("STENCIL_HEARD_DUCK_RANGE_PX", 180)
  HeardDuckFreshTicks* = envInt("STENCIL_HEARD_DUCK_FRESH_TICKS", 24)
  Chat* = envBool("STENCIL_CHAT", true)
  ChatMinIntervalTicks* = envInt("STENCIL_CHAT_MIN_INTERVAL_TICKS", 30)
  ChatEnemyRearmTicks* = envInt("STENCIL_CHAT_ENEMY_REARM_TICKS", 48)
  ChatEnemyReshoutTicks* = envInt("STENCIL_CHAT_ENEMY_RESHOUT_TICKS", 72)
  ChatFixTtlTicks* = envInt("STENCIL_CHAT_FIX_TTL_TICKS", 96)
  ChatBubbleDedupTicks* = envInt("STENCIL_CHAT_BUBBLE_DEDUP_TICKS", 80)
  UnderFireRangePx* = envInt("STENCIL_UNDER_FIRE_RANGE_PX", 90)
  UnderFireFreshTicks* = envInt("STENCIL_UNDER_FIRE_FRESH_TICKS", 24)
  ChatEnemyBubbleFix* = envBool("STENCIL_CHAT_ENEMY_BUBBLE_FIX", true)
  GrenadeWarnClearPx* = envInt("STENCIL_GRENADE_WARN_CLEAR_PX", 80)
  GrenadeWarnTtlTicks* = envInt("STENCIL_GRENADE_WARN_TTL_TICKS", 72)
  Squads* = envBool("STENCIL_SQUADS", false)
  SquadCohesionPx* = envInt("STENCIL_SQUAD_COHESION_PX", 120)
  SquadMinBuddies* = envInt("STENCIL_SQUAD_MIN_BUDDIES", 1)
  SquadSeparationPx* = envTunableInt("STENCIL_SQUAD_SEPARATION_PX", 40, 16, 120)
  SquadSpreadPx* = envInt("STENCIL_SQUAD_SPREAD_PX", 70)
  SquadWaitTimeoutTicks* = envInt("STENCIL_SQUAD_WAIT_TIMEOUT_TICKS", 150)
  SquadSectorBrads* = envInt("STENCIL_SQUAD_SECTOR_BRADS", 50)
  SquadCommand* = envBool("STENCIL_SQUAD_COMMAND", false)
  ChokeFraction* = envFloat("STENCIL_CHOKE_FRACTION", 0.45)
  RallyFraction* = envFloat("STENCIL_RALLY_FRACTION", 0.65)
  ConvertEnemyLives* = envInt("STENCIL_CONVERT_ENEMY_LIVES", 6)
  OrderTtlTicks* = envInt("STENCIL_ORDER_TTL_TICKS", 240)
  OrderRebroadcastTicks* = envInt("STENCIL_ORDER_REBROADCAST_TICKS", 72)
  PingIntervalTicks* = envInt("STENCIL_PING_INTERVAL_TICKS", 60)
  PresenceStaleTicks* = envInt("STENCIL_PRESENCE_STALE_TICKS", 190)
  BackoffStepPx* = envInt("STENCIL_BACKOFF_STEP_PX", 70)
  RejoinTimeoutTicks* = envInt("STENCIL_REJOIN_TIMEOUT_TICKS", 360)
  RejoinContactPx* = envInt("STENCIL_REJOIN_CONTACT_PX", 160)
  ConfiguredDefenderCount* = envInt("STENCIL_DEFENDERS", 3)
  HoldArrivePx* = envInt("STENCIL_HOLD_ARRIVE_PX", 28)

proc validateConfig(): bool =
  template require(condition: bool, name, description: string) =
    if not condition:
      raise newException(ValueError, name & ": " & description)
  require(0 <= FirefightRangeClosePx and
      FirefightRangeClosePx < FirefightRangeIdealMinPx and
      FirefightRangeIdealMinPx <= FirefightRangeIdealMaxPx and
      FirefightRangeIdealMaxPx <= FirefightRangeScoreFalloffPx,
    "range_band_order",
    "0 <= close < ideal_min <= ideal_max <= FF_RANGE_SCORE_FALLOFF_PX.")
  require(FirefightTargetMinDwellTicks <= FirefightDwellTicks,
    "target_latch_within_mode",
    "Target minimum dwell must not exceed firefight dwell.")
  require(FirefightClaimRebroadcastTicks < FirefightClaimTtlTicks,
    "claim_refresh_before_expiry",
    "Claim rebroadcast interval must be shorter than claim TTL.")
  require(FirefightDeathMissingTicks < FirefightTargetMissingTicks and
      FirefightTargetMissingTicks < FirefightClaimTtlTicks,
    "claim_release_clock_order",
    "Death-missing ticks < target-missing ticks < claim TTL.")
  require(FirefightClaimMatchPx <= FirefightClaimLocalityPx,
    "claim_match_within_locality",
    "Anonymous claim match radius must not exceed claim locality.")
  require(not FocusClaims or Firefight,
    "focus_requires_firefight",
    "FOCUS_CLAIMS may be enabled only when FIREFIGHT is enabled.")
  require(FirefightClaimWeight <= FirefightWoundWeight * 0.5,
    "claim_bias_bounded_by_wound",
    "Claim bonus may not exceed one health-bar segment of wound score.")
  true

let ConfigValidated* = validateConfig()
