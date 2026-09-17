' Module: config (prefix cfg). Tunable knobs only; no logic.
' All distances are in world units / 1000 ("ku": 60 ku = 1 tile) unless noted.
' cfgInit runs once per decision from main; assignments are cheap.

sub cfgInit()
  ' Last-hit planner
  cfgScanRadius = 1200         ' ku: footmen farther than this are not scanned (20 tiles)
  cfgRangeSlack = 6            ' ku inside my attack range to count as "in range"
  cfgStandoffBack = 60         ' ku behind max range for the ranged standoff point
  cfgMeleeStandoff = 50        ' ku from the anchor footman for melee heroes
  cfgChaseKu = 180             ' ku beyond my reach a footman may be before I stop considering it
  cfgAvoidAllyTarget = 1       ' 1: skip footmen an allied hero is already attacking
  cfgTowerAvoid = 420          ' stay this far (ku) from a living enemy tower (7 tiles)
  cfgFootmanPeriod = 32        ' ticks between an allied footman's hits
  cfgTowerPeriod = 24          ' ticks between tower hits
  cfgFootmanHit = 12
  cfgStickSlack = 12           ' keep an ordered target while predicted HP <= damage + this
  cfgStickBonus = 40           ' score bonus for the target already ordered (avoids swing resets)
  cfgEventStale = 96           ' forget a drop event older than this many ticks
  cfgSeenStale = 120           ' forget a footman not seen for this many ticks
  cfgPoisonSecure = 1          ' use poison to secure a kill the basic attack would miss
  cfgSpellSecure = 1           ' use the primary strike to secure a kill
  cfgPoisonStock = 1           ' poisons to keep in stock
  cfgPoisonMinGold = 40        ' only restock poison at or above this gold
  cfgUseAttackMoveIdle = 0     ' 1: attackMove when walking to the lane with nothing around

  ' Survival
  cfgRetreatPct = 35           ' retreat below this percent of max HP
  cfgRecoverPct = 70           ' resume below-threshold work above this percent
  cfgHeroFearRange = 360       ' ku: enemy hero this close while under 60% HP => back off
  cfgTowerEscape = 540         ' ku to step back when an enemy tower targets me (9 tiles)
  cfgRetreatStep = 600         ' ku to step back toward own fort per retreat order

  ' Telemetry
  cfgReportEvery = 240
  cfgDebug = 1                 ' 1: print a planner trace every cfgDebugEvery ticks
  cfgDebugEvery = 100000
  cfgDebugFrom = 0             ' per-footman trace window (ticks); 0-0 disables
  cfgDebugTo = 0
end sub
