' Module: config (prefix cfg). Tunable knobs only; no logic.
' All distances are in world units / 1000 ("ku": 60 ku = 1 tile) unless noted.
' cfgInit runs once per decision from main; assignments are cheap.

sub cfgInit()
  ' Last-hit planner
  cfgScanRadius = 1200         ' ku: footmen farther than this are not scanned (20 tiles)
  cfgRangeSlack = 6            ' ku inside my attack range to count as "in range"
  cfgStandoffBack = 60         ' ku behind max range for the ranged standoff point
  cfgMeleeStandoff = 120       ' ku from the anchor footman for melee heroes
  cfgChaseKu = 180             ' ku beyond my reach a footman may be before I stop considering it
  cfgAvoidAllyTarget = 0       ' 1: skip footmen an allied hero is already attacking (helps mono-team play, costs mixed-team play)
  cfgTowerFarmAllies = 99      ' farm beside an idle enemy tower only with this many allied footmen inside its reach (99 = never; v10 A/B showed no gain)
  cfgTowerFarmAlliesKu = 390   ' ku: what counts as inside the tower's reach (6.5 tiles)
  cfgTowerAvoid = 420          ' stay this far (ku) from a living enemy tower (7 tiles)
  cfgFootmanPeriod = 32        ' ticks between an allied footman's hits
  cfgTowerPeriod = 24          ' ticks between tower hits
  cfgStickSlack = 12           ' keep an ordered target while predicted HP <= damage + this
  cfgStickBonus = 40           ' score bonus for the target already ordered (avoids swing resets)
  cfgEventStale = 96           ' forget a drop event older than this many ticks
  cfgSeenStale = 1             ' forget a footman's hit history after any sighting gap (a drop across a gap has no known tick)
  cfgPoisonStock = 1           ' poisons to keep in stock while a footman still takes two hits
  cfgPoisonMinGold = 40        ' only restock poison at or above this gold
  ' Idle at the standoff point and let the engine attack instead of holding
  ' for kill windows. Hosted A/B v4 versus v5 (2026-09-17, 32 episodes per arm,
  ' exact replay counts): idle for every class 4.88 versus 4.31 last hits per
  ' hero per 1,000 ticks. Set 0 to hold for windows (the v1 to v4 behavior).
  cfgIdleHere = 1
  ' Melee and low-damage classes convert half as often as the field when they
  ' walk to a standoff point and wait (time-budget analysis, 2026-09-17): they
  ' attack only 20 to 26 percent of the ticks a creep is in reach versus 90
  ' percent for the top farmers. For them, chase and attack the anchor footman
  ' continuously; the last-hit windows still take priority when one opens.
  cfgChaseClass = 0
  if selfClass = 0 or selfClass = 3 or selfClass = 4 or selfClass = 5 or selfClass = 8 or selfClass = 9 then
    cfgChaseClass = 1
  end if

  ' Kill steal: the finishing blow on heroes and structures teammates are fighting
  cfgKsteal = 1                ' 0 disables the module
  cfgKsHoldKu = 600            ' ku: an enemy hero within this => farm by windows only, spells held (10 tiles)
  cfgKsAllyKu = 480            ' ku: an allied hero this close to the target and attacking it counts as engaged
  cfgKsRecentTicks = 48        ' a drop within this many ticks also counts as engaged
  cfgKsMinHpPct = 40           ' take hero windows only above this percent of max HP
  cfgKsHeroChaseKu = 180       ' ku: walk at most this far beyond reach toward an engaged enemy hero (3 tiles; 12 tiles cost kills and lives, v15 A/B)
  cfgHeroPeriod = 24           ' assumed repeat period of a hero's incoming hits (ticks)
  cfgKsAreaSpells = 0          ' 1: also cast delayed area and ring spells on still targets (v16 A/B: more casts, fewer kills)
  cfgKsStructChaseKu = 480     ' ku: walk up to this far beyond reach for a structure's finishing hit (8 tiles)
  cfgKsStructAllies = 2        ' allied footmen inside the tower's range before I step in
  cfgKsStructPrepTicks = 240   ' stand ready beside a shielded structure predicted to die within this many ticks (10 s)
  cfgKsStructPrepKu = 900      ' ku: only for structures within this of me (15 tiles)

  ' Diagnostic only: print a KT line when the kill-steal hero target changes against
  ' the order applied last decision (a hero window opening, closing, or being
  ' overridden by retreat or punish). No behavior depends on it. See 90_main.bas.
  cfgKsTrace = 1

  ' Punish: attack an enemy hero that is farming inside our tower's reach
  cfgPunish = 1                ' 0 disables the module
  cfgPunishEnterKu = 420       ' enemy hero within this of an allied tower that is firing at it starts a punish (7 tiles)
  cfgPunishExitKu = 600        ' punish ends once the target is farther than this from the tower (10 tiles)
  cfgPunishEngageKu = 720      ' only start when the target is within this of me (12 tiles)
  cfgPunishMinHpPct = 50       ' start only above this percent of max HP
  cfgPunishStopHpPct = 35      ' stop below this percent
  cfgPunishChase = 0           ' 1: keep chasing past tower range when the kill is cheap (v10 A/B: 74 chase ticks in 48 games, no gain)
  cfgPunishChaseTicks = 120    ' chase only if the expected time to kill is at most this (5 s)
  cfgPunishChaseMaxKu = 900    ' never chase a target farther than this from me (15 tiles)
  cfgPunishAllyKu = 360        ' an allied hero within this of the target counts its DPS and permits a slower chase

  ' Survival
  cfgRetreatPct = 35           ' retreat below this percent of max HP
  cfgRecoverPct = 70           ' resume below-threshold work above this percent
  cfgHeroHuntRange = 480       ' ku: an enemy hero targeting me within this => retreat at any HP
  cfgHeroFearRange = 360       ' ku: enemy hero this close while under 60% HP => back off
  cfgTowerEscape = 540         ' ku to step back when an enemy tower targets me (9 tiles)
  cfgRetreatStep = 600         ' ku to step back toward own fort per retreat order

  ' Telemetry
  cfgReportEvery = 240
end sub
