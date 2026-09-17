' ===== module 00_config.bas =====
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
  cfgSeenStale = 1           ' reset phase after any nonconsecutive sighting
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

' ===== module 10_scan.bas =====
' Module: scan (prefix sc). One pass over the object list into typed arrays.
' Positions are stored in ku (tile * 60). Enemy objects are only those visible
' to my team this decision; allied objects are always present. Footmen are kept
' only within cfgScanRadius of me (budget).
'
' Outputs (valid for this decision):
'   efN, efId(i), efX(i), efY(i), efHp(i)     living enemy footmen
'   afN, afX(i), afY(i), afTgt(i)              living allied footmen and their targets
'   atN, atX(i), atY(i), atTgt(i), atDmg(i)    allied towers (any), their target and hit damage
'   etN, etX(i), etY(i), etTgt(i)              visible living enemy towers and their targets
'   ahN, ahTgt(i), ahDmg(i), ahPer(i)          living allied heroes (not me): target, damage, swing ticks
'   ehN, ehX(i), ehY(i), ehHp(i)               visible living enemy heroes
'   scFortX, scFortY                           own god (fort) position
'   scEFortX, scEFortY                         enemy god position (mirror of own)
'   fmSlot(ring)                               enemy footman id ring -> index into ef arrays, or -1
'   scSelfX, scSelfY                           my position in ku

dim efId(63)
dim efX(63)
dim efY(63)
dim efHp(63)
dim afX(63)
dim afY(63)
dim afTgt(63)
dim atX(15)
dim atY(15)
dim atTgt(15)
dim atDmg(15)
dim etX(15)
dim etY(15)
dim etTgt(15)
dim ahTgt(4)
dim ahDmg(4)
dim ahPer(4)
dim ehX(4)
dim ehY(4)
dim ehHp(4)
dim fmSlot(447)

' Sets hdDmg and hdPer (basic damage and swing ticks) for a hero class and level,
' ignoring items. Table from content.nim at the deployed commit.
sub heroDmgFor(cls, lvl)
  hdDmg = 25
  hdPer = 24
  if cls = 0 then
    hdDmg = 25 + (lvl - 1) * 5
    hdPer = 24
  end if
  if cls = 1 then
    hdDmg = 25 + (lvl - 1) * 6
    hdPer = 18
  end if
  if cls = 2 then
    hdDmg = 38 + (lvl - 1) * 8
    hdPer = 30
  end if
  if cls = 3 then
    hdDmg = 22 + (lvl - 1) * 4
    hdPer = 26
  end if
  if cls = 4 then
    hdDmg = 32 + (lvl - 1) * 7
    hdPer = 16
  end if
  if cls = 5 then
    hdDmg = 30 + (lvl - 1) * 6
    hdPer = 28
  end if
  if cls = 6 then
    hdDmg = 46 + (lvl - 1) * 9
    hdPer = 36
  end if
  if cls = 7 then
    hdDmg = 36 + (lvl - 1) * 8
    hdPer = 32
  end if
  if cls = 8 then
    hdDmg = 26 + (lvl - 1) * 5
    hdPer = 28
  end if
  if cls = 9 then
    hdDmg = 38 + (lvl - 1) * 8
    hdPer = 20
  end if
end sub

' Tower hit damage from its stable id: lane towers are ids 10-27 in
' outer/inner/gate triples; god guards (28-31) hit like a gate tower.
sub towerDmgFor(tid)
  tdDmg = 30
  if tid >= 10 and tid <= 27 then
    tdTier = (tid - 10) mod 3
    if tdTier = 0 then
      tdDmg = 18
    end if
    if tdTier = 1 then
      tdDmg = 24
    end if
  end if
end sub

sub scanObjects()
  ' Clear the id ring entries used last decision.
  scI = 0
  while scI < efN
    fmSlot((efId(scI) - 1000) mod 448) = -1
    scI = scI + 1
  wend
  efN = 0
  afN = 0
  atN = 0
  etN = 0
  ahN = 0
  ehN = 0
  scSelfX = selfX * 60
  scSelfY = selfY * 60
  scCount = objectCount()
  scI = 0
  while scI < scCount
    scKind = objectKind(scI)
    scTeam = objectTeam(scI)
    if scKind = 3 then
      if objectAlive(scI) = 1 then
        ' Footmen beyond cfgScanRadius are irrelevant to this hero's decisions and
        ' would cost instruction budget in every planner loop; skip them.
        scDx = objectX(scI) * 60 - scSelfX
        scDy = objectY(scI) * 60 - scSelfY
        if scDx * scDx + scDy * scDy > cfgScanRadius * cfgScanRadius then
          scKind = 0
        end if
      else
        scKind = 0
      end if
    end if
    if scKind = 3 then
      if objectAlive(scI) = 1 then
        if scTeam = selfTeam then
          if afN < 64 then
            afX(afN) = objectX(scI) * 60
            afY(afN) = objectY(scI) * 60
            afTgt(afN) = objectTarget(scI)
            afN = afN + 1
          end if
        else
          if efN < 64 then
            efId(efN) = objectId(scI)
            efX(efN) = objectX(scI) * 60
            efY(efN) = objectY(scI) * 60
            efHp(efN) = objectHp(scI)
            fmSlot((efId(efN) - 1000) mod 448) = efN
            efN = efN + 1
          end if
        end if
      end if
    end if
    if scKind = 4 then
      if scTeam = selfTeam then
        if atN < 16 then
          atX(atN) = objectX(scI) * 60
          atY(atN) = objectY(scI) * 60
          atTgt(atN) = objectTarget(scI)
          towerDmgFor(objectId(scI))
          atDmg(atN) = tdDmg
          atN = atN + 1
        end if
      else
        if objectHp(scI) > 0 then
          if etN < 16 then
            etX(etN) = objectX(scI) * 60
            etY(etN) = objectY(scI) * 60
            etTgt(etN) = objectTarget(scI)
            etN = etN + 1
          end if
        end if
      end if
    end if
    if scKind = 2 then
      if objectId(scI) <> selfId then
        if objectAlive(scI) = 1 then
          if scTeam = selfTeam then
            if ahN < 5 then
              ahTgt(ahN) = objectTarget(scI)
              heroDmgFor(objectClass(scI), objectLevel(scI))
              ahDmg(ahN) = hdDmg
              ahPer(ahN) = hdPer
              ahN = ahN + 1
            end if
          else
            if ehN < 5 then
              ehX(ehN) = objectX(scI) * 60
              ehY(ehN) = objectY(scI) * 60
              ehHp(ehN) = objectHp(scI)
              ehN = ehN + 1
            end if
          end if
        end if
      end if
    end if
    if scKind = 1 then
      if scTeam = selfTeam then
        scFortX = objectX(scI) * 60
        scFortY = objectY(scI) * 60
        scEFortX = (mapWidth - 1) * 60 - scFortX
        scEFortY = (mapHeight - 1) * 60 - scFortY
      end if
    end if
    scI = scI + 1
  wend
end sub

' ===== module 20_lasthit.bas =====
' Module: lasthit (prefix lh). Plans the footman last hit for this decision.
'
' Inputs: scan arrays (10_scan.bas), self data, cfg knobs, shPoisonSlot (40_shop.bas).
' Outputs, rewritten every decision:
'   lhState      0 no enemy footmen in play, 1 waiting for a window, 2 striking now
'   lhTargetId   footman to order attackTarget on now, or 0
'   lhSecureSlot ability slot to cast on lhSecureId to secure a kill, or -1
'   lhSecureId   footman id for the secure cast
'   lhPoisonId   footman id to poison this decision (attackTarget it, then useItem), or 0
'   lhHoldX, lhHoldY  tile to walk toward while waiting
' Telemetry counters: lhOrders, lhSecures, lhPoisons, lhLost.
'
' Method: for every visible enemy footman, predict its HP at the tick my next basic
' hit would land. Incoming damage comes from recorded HP-drop events (each repeats
' with its attacker's period: 32 ticks for footmen, 24 for towers, the class swing
' for heroes) plus an expected-value term for attached attackers that have not hit
' yet. A footman whose predicted HP is in (0, selfAttackDamage] is a window: order
' the attack now. One that would die first is a secure candidate: poison (instant,
' 35) or the class primary strike. Otherwise hold a walk target at the standoff
' point so the engine never auto-acquires and wastes hits.

dim fmHp(447)
dim fmSeen(447)
dim fmEv1(447)
dim fmEv2(447)
dim pvId(63)
dim efAtt(63)
dim efTw(63)
dim efHDmg(63)
dim efHPer(63)
dim efPred(63)

' adD = approximate planar distance of (dx, dy) in ku, within about 7 percent.
sub approxDist(dx, dy)
  adAx = dx
  if adAx < 0 then
    adAx = 0 - adAx
  end if
  adAy = dy
  if adAy < 0 then
    adAy = 0 - adAy
  end if
  if adAx >= adAy then
    adD = (adAx * 10 + adAy * 4) / 10
  else
    adD = (adAy * 10 + adAx * 4) / 10
  end if
end sub

' Primary-strike parameters for my class (slot 1). spDmg = 0 means no instant strike.
' spProj = 1 for projectiles (45 ku per tick of travel).
sub lhStrikeSpec()
  spDmg = 0
  spRange = 0
  spProj = 0
  spMana = 0
  if selfClass = 0 then
    spDmg = 40
    spRange = 90
    spMana = 20
  end if
  if selfClass = 1 then
    spDmg = 32
    spRange = 360
    spProj = 1
    spMana = 18
  end if
  if selfClass = 2 then
    spDmg = 42
    spRange = 330
    spProj = 1
    spMana = 28
  end if
  if selfClass = 4 then
    spDmg = 38
    spRange = 90
    spMana = 16
  end if
  if selfClass = 5 then
    spDmg = 42
    spRange = 90
    spMana = 18
  end if
  if selfClass = 6 then
    spDmg = 50
    spRange = 400
    spProj = 1
    spMana = 22
  end if
  if selfClass = 7 then
    spDmg = 48
    spRange = 400
    spProj = 1
    spMana = 30
  end if
  if selfClass = 8 then
    spDmg = 36
    spRange = 280
    spProj = 1
    spMana = 24
  end if
  if selfClass = 9 then
    spDmg = 45
    spRange = 90
    spMana = 0
  end if
end sub

' Records HP drops of visible enemy footmen as repeating events. Also counts
' footmen that were within chase distance last decision and are gone now
' (lhVanished), for the missed-opportunity telemetry.
sub lhUpdateMemory()
  ' Footmen near me last decision (pvId) that are gone from this decision's list.
  lhVanished = 0
  lmI = 0
  while lmI < pvN
    if pvId(lmI) > 0 then
      lmJ = fmSlot((pvId(lmI) - 1000) mod 448)
      lmGone = 1
      if lmJ >= 0 then
        if efId(lmJ) = pvId(lmI) then
          lmGone = 0
        end if
      end if
      lhVanished = lhVanished + lmGone
    end if
    lmI = lmI + 1
  wend
  pvN = 0
  lmChase = selfAttackRange / 1000 + cfgChaseKu
  lmI = 0
  while lmI < efN
    lmS = (efId(lmI) - 1000) mod 448
    if fmSeen(lmS) > 0 and worldTick - fmSeen(lmS) > 1 and worldTick - fmSeen(lmS) <= 120 then
      lmGapResets = lmGapResets + 1
    end if
    if fmSeen(lmS) = 0 or worldTick - fmSeen(lmS) > cfgSeenStale then
      fmEv1(lmS) = 0
      fmEv2(lmS) = 0
    else
      lmD = fmHp(lmS) - efHp(lmI)
      if lmD > 0 then
        ' The same attacker hitting again has the same phase (tick mod 32) and
        ' amount: refresh that event instead of keeping two copies of one swing.
        lmNew = (worldTick - 1) * 256 + lmD
        lmSame = 0
        if fmEv1(lmS) > 0 then
          if fmEv1(lmS) mod 256 = lmD and ((worldTick - 1) - fmEv1(lmS) / 256) mod cfgFootmanPeriod = 0 then
            lmSame = 1
          end if
        end if
        if lmSame = 1 then
          fmEv1(lmS) = lmNew
        else
          if fmEv2(lmS) > 0 then
            if fmEv2(lmS) mod 256 = lmD and ((worldTick - 1) - fmEv2(lmS) / 256) mod cfgFootmanPeriod = 0 then
              lmSame = 2
            end if
          end if
          if lmSame = 2 then
            fmEv2(lmS) = fmEv1(lmS)
            fmEv1(lmS) = lmNew
          else
            fmEv2(lmS) = fmEv1(lmS)
            fmEv1(lmS) = lmNew
          end if
        end if
      end if
    end if
    fmHp(lmS) = efHp(lmI)
    fmSeen(lmS) = worldTick
    lmDx = efX(lmI) - scSelfX
    lmDy = efY(lmI) - scSelfY
    pvId(pvN) = 0
    if lmDx * lmDx + lmDy * lmDy <= lmChase * lmChase then
      pvId(pvN) = efId(lmI)
    end if
    pvN = pvN + 1
    lmI = lmI + 1
  wend
end sub

' Counts attackers attached to each enemy footman this decision.
sub lhAttachers()
  laI = 0
  while laI < efN
    efAtt(laI) = 0
    efTw(laI) = 0
    efHDmg(laI) = 0
    efHPer(laI) = 32
    laI = laI + 1
  wend
  laI = 0
  while laI < afN
    if afTgt(laI) >= 1000 then
      laJ = fmSlot((afTgt(laI) - 1000) mod 448)
      if laJ >= 0 then
        if efId(laJ) = afTgt(laI) then
          laDx = afX(laI) - efX(laJ)
          laDy = afY(laI) - efY(laJ)
          if laDx * laDx + laDy * laDy <= 8100 then
            efAtt(laJ) = efAtt(laJ) + 1
          end if
        end if
      end if
    end if
    laI = laI + 1
  wend
  laI = 0
  while laI < atN
    if atTgt(laI) >= 1000 then
      laJ = fmSlot((atTgt(laI) - 1000) mod 448)
      if laJ >= 0 then
        if efId(laJ) = atTgt(laI) then
          efTw(laJ) = atDmg(laI)
        end if
      end if
    end if
    laI = laI + 1
  wend
  laI = 0
  while laI < ahN
    if ahTgt(laI) >= 1000 then
      laJ = fmSlot((ahTgt(laI) - 1000) mod 448)
      if laJ >= 0 then
        if efId(laJ) = ahTgt(laI) then
          efHDmg(laJ) = ahDmg(laI)
          efHPer(laJ) = ahPer(laI)
        end if
      end if
    end if
    laI = laI + 1
  wend
end sub

' Number of repeats of an event at tick evT with period per landing in
' [worldTick, worldTick + h]. Result in evHits.
sub lhEventHits(evT, per, h)
  evHits = (worldTick + h - evT) / per - (worldTick - 1 - evT) / per
end sub

' lhInc = predicted damage to enemy footman i over the next h ticks (inclusive
' of this tick's footman and tower updates, exclusive of my own hit).
sub lhIncoming(i, h)
  lhInc = 0
  liRep = 0
  liS = (efId(i) - 1000) mod 448
  liE = 0
  while liE < 2
    if liE = 0 then
      liEv = fmEv1(liS)
    else
      liEv = fmEv2(liS)
    end if
    if liEv > 0 then
      liT = liEv / 256
      liA = liEv mod 256
      if worldTick - liT <= cfgEventStale then
        liPer = cfgFootmanPeriod
        if efTw(i) > 0 and liA = efTw(i) then
          liPer = cfgTowerPeriod
        else
          if efHDmg(i) > 0 and liA = efHDmg(i) then
            liPer = efHPer(i)
          else
            liRep = liRep + liA / cfgFootmanHit
          end if
        end if
        lhEventHits(liT, liPer, h)
        lhInc = lhInc + liA * evHits
      end if
    end if
    liE = liE + 1
  wend
  ' Attached footmen without a recorded hit yet: expected value.
  liExtra = efAtt(i) - liRep
  if liExtra > 0 then
    lhInc = lhInc + liExtra * cfgFootmanHit * (h + 8) / cfgFootmanPeriod
  end if
end sub

' Standoff point behind an anchor position (ax, ay) toward my fort, at distance
' back ku. Writes lhHoldX, lhHoldY in tiles.
sub lhHoldBehind(ax, ay, back)
  hbDx = scFortX - ax
  hbDy = scFortY - ay
  approxDist(hbDx, hbDy)
  if adD < 1 then
    adD = 1
  end if
  lhHoldX = (ax + hbDx * back / adD) / 60
  lhHoldY = (ay + hbDy * back / adD) / 60
end sub

' 1 if (x, y) in ku is within cfgTowerAvoid of a visible living enemy tower that
' is not busy with a footman. Towers shoot footmen before heroes, so a tower whose
' target is a footman is safe to farm beside for now; the survive module handles
' the moment it switches to me.
sub lhNearEnemyTower(x, y)
  ntNear = 0
  ntI = 0
  while ntI < etN
    ntDx = etX(ntI) - x
    ntDy = etY(ntI) - y
    if ntDx * ntDx + ntDy * ntDy <= cfgTowerAvoid * cfgTowerAvoid then
      if etTgt(ntI) < 1000 then
        ntNear = 1
      end if
    end if
    ntI = ntI + 1
  wend
end sub

sub lhPlan()
  lhState = 0
  lhTargetId = 0
  lhSecureSlot = -1
  lhSecureId = 0
  lhPoisonId = 0
  lhUpdateMemory()
  lhAttachers()
  lhStrikeSpec()
  lhRange = selfAttackRange / 1000
  lhReach = lhRange - cfgRangeSlack
  if lhReach < 30 then
    lhReach = 30
  end if
  lhSpeed = selfMoveSpeed / 1000
  if lhSpeed < 1 then
    lhSpeed = 1
  end if
  heroDmgFor(selfClass, 1)
  lhWindup = hdPer * 45 / 100
  lhMelee = 0
  if lhRange < 120 then
    lhMelee = 1
  end if
  lhStrikeReady = 0
  if cfgSpellSecure = 1 and spDmg > 0 then
    if abilityCharges(1) > 0 and abilityCooldown(1) = 0 and selfMana >= spMana then
      lhStrikeReady = 1
    end if
  end if
  lhPoisonReady = 0
  if cfgPoisonSecure = 1 and shPoisonSlot >= 0 then
    lhPoisonReady = 1
  end if

  ' My lane and whether any enemy footman is visible in it.
  lhMyLane = 1
  lhSlot = (selfId - 100) mod 5
  if lhSlot < 2 then
    lhMyLane = 0
  end if
  if lhSlot > 2 then
    lhMyLane = 2
  end if
  lhDiag = (mapWidth - 1) * 60
  lhLaneCount = 0
  lhLocalCount = 0
  lhChase = lhReach + cfgChaseKu
  lhI = 0
  while lhI < efN
    lhDx = efX(lhI) - scSelfX
    lhDy = efY(lhI) - scSelfY
    if lhDx * lhDx + lhDy * lhDy <= lhChase * lhChase then
      lhLocalCount = lhLocalCount + 1
    end if
    lhS = efX(lhI) + efY(lhI) - lhDiag
    lhL = 1
    if lhS <= -900 then
      lhL = 0
    end if
    if lhS >= 900 then
      lhL = 2
    end if
    if lhL = lhMyLane then
      lhLaneCount = lhLaneCount + 1
    end if
    lhI = lhI + 1
  wend
  lhBest = -1
  lhBestScore = 2147483647
  lhAnchor = -1
  lhAnchorHp = 2147483647
  lhAnchorPos = 0
  lhAnchorD2 = 2147483647
  lhI = 0
  while lhI < efN
    lhDx = efX(lhI) - scSelfX
    lhDy = efY(lhI) - scSelfY
    lhD2 = lhDx * lhDx + lhDy * lhDy
    lhInR = 0
    if lhD2 <= lhReach * lhReach then
      lhInR = 1
    end if
    lhNearEnemyTower(efX(lhI), efY(lhI))
    ' Anchor tiers: footmen already within chase distance (any lane) come first,
    ' then footmen in my lane, then anything visible. This keeps the hero on
    ' local opportunities without wandering into another lane for a distant one.
    lhChase = lhReach + cfgChaseKu
    lhLocal = 0
    if lhD2 <= lhChase * lhChase then
      lhLocal = 1
    end if
    lhLaneOk = 1
    if lhLocal = 0 then
      if lhLocalCount > 0 then
        lhLaneOk = 0
      else
        if lhLaneCount > 0 then
          lhS = efX(lhI) + efY(lhI) - lhDiag
          lhL = 1
          if lhS <= -900 then
            lhL = 0
          end if
          if lhS >= 900 then
            lhL = 2
          end if
          if lhL <> lhMyLane then
            lhLaneOk = 0
          end if
        end if
      end if
    end if
    ' Only footmen I can reach quickly may be ordered; chasing across the map
    ' abandons the lane and never converts. Footmen an ally is already hitting
    ' are theirs.
    lhOrderOk = lhLocal
    if cfgAvoidAllyTarget = 1 then
      lhJ = 0
      while lhJ < ahN
        if ahTgt(lhJ) = efId(lhI) then
          lhOrderOk = 0
        end if
        lhJ = lhJ + 1
      wend
    end if
    if ntNear = 0 and lhLaneOk = 1 then
      ' Horizon for my basic hit on this footman.
      if lhInR = 1 then
        ' A reported cooldown of C lands during hero update C - 1 ticks from now.
        lhH = selfAttackCooldown - 1
        if lhH < 0 then
          lhH = 0
        end if
      else
        approxDist(lhDx, lhDy)
        lhH = (adD - lhReach) / lhSpeed + lhWindup
      end if
      lhIncoming(lhI, lhH)
      lhPred = efHp(lhI) - lhInc
      efPred(lhI) = lhPred
      lhWindow = selfAttackDamage
      if efId(lhI) = lhStickId then
        lhWindow = lhWindow + cfgStickSlack
      end if
      if lhOrderOk = 1 and lhPred > 0 and lhPred <= lhWindow then
        lhScore = lhH * 10 + lhPred
        if efId(lhI) = lhStickId then
          lhScore = lhScore - cfgStickBonus
        end if
        if lhScore < lhBestScore then
          lhBestScore = lhScore
          lhBest = lhI
          lhBestPred = lhPred
          lhBestH = lhH
          lhBestHp = efHp(lhI)
          lhBestInR = lhInR
        end if
      end if
      if lhOrderOk = 1 and lhPred <= 0 then
        ' The basic attack is too slow: try an instant source.
        if lhPoisonId = 0 and lhPoisonReady = 1 and lhInR = 1 and efHp(lhI) <= 35 then
          lhPoisonId = efId(lhI)
        else
          if lhSecureId = 0 and lhStrikeReady = 1 and lhD2 <= spRange * spRange then
            if spProj = 1 then
              ' Projectile: at least one tick of travel, resolves after this tick's units.
              approxDist(lhDx, lhDy)
              lhSH = (adD + 44) / 45
              if lhSH < 1 then
                lhSH = 1
              end if
              lhIncoming(lhI, lhSH)
              lhPredS = efHp(lhI) - lhInc
            else
              ' Melee cast resolves inside this decision, before any creep swings.
              lhPredS = efHp(lhI)
            end if
            if lhPredS > 0 and lhPredS <= spDmg then
              lhSecureId = efId(lhI)
              lhSecureSlot = 1
            end if
          end if
        end if
      end if
      ' Anchor: the footman with the smallest positive predicted HP, else the nearest.
      if lhPred > 0 then
        if lhAnchorPos = 0 or lhPred < lhAnchorHp then
          lhAnchorPos = 1
          lhAnchorHp = lhPred
          lhAnchor = lhI
        end if
      else
        if lhAnchorPos = 0 and lhD2 < lhAnchorD2 then
          lhAnchorD2 = lhD2
          lhAnchor = lhI
          lhAnchorHp = lhPred
        end if
      end if
      ' Trace budget: the VM allows about 64 print items per decision in practice.
      if cfgDebug = 1 and worldTick >= cfgDebugFrom and worldTick <= cfgDebugTo and lhI < 2 then
        print "F ", efId(lhI), " ", efHp(lhI), " d2 ", lhD2, " h ", lhH, " inc ", lhInc, " pred ", lhPred
      end if
    end if
    lhI = lhI + 1
  wend

  if lhAnchor >= 0 then
    lhState = 1
    if lhMelee = 1 then
      lhHoldBehind(efX(lhAnchor), efY(lhAnchor), cfgMeleeStandoff)
    else
      lhHoldBehind(efX(lhAnchor), efY(lhAnchor), lhRange - cfgStandoffBack)
    end if
  end if
  if lhBest >= 0 then
    lhState = 2
    lhTargetId = efId(lhBest)
  end if
  ' Never poison the footman the basic attack is about to take.
  if lhPoisonId <> 0 and lhPoisonId = lhTargetId then
    lhPoisonId = 0
  end if
  if lhSecureId <> 0 and lhSecureId = lhTargetId then
    lhSecureId = 0
    lhSecureSlot = -1
  end if
end sub

' ===== module 30_survive.bas =====
' Module: survive (prefix sv). Minimal self-preservation with priority over farming.
'
' Outputs, rewritten every decision:
'   svRetreat  1 when the hero should walk back toward its fort instead of farming
'   svRetX, svRetY  retreat tile
'   svHealSlot  inventory slot of a healing consumable to use now, or -1
' State: svLow (hysteresis flag). Telemetry: svRetreats (orders issued).

sub svPlan()
  svRetreat = 0
  svHealSlot = -1
  if selfHp * 100 < selfMaxHp * cfgRetreatPct then
    svLow = 1
  end if
  if selfHp * 100 >= selfMaxHp * cfgRecoverPct then
    svLow = 0
  end if
  ' An enemy hero close while I am not healthy is a fight I do not want.
  svThreat = 0
  if selfHp * 100 < selfMaxHp * 60 then
    svI = 0
    while svI < ehN
      svDx = ehX(svI) - scSelfX
      svDy = ehY(svI) - scSelfY
      if svDx * svDx + svDy * svDy <= cfgHeroFearRange * cfgHeroFearRange then
        svThreat = 1
      end if
      svI = svI + 1
    wend
  end if
  ' An enemy tower shooting me: leave its range now (30 damage per second).
  svTower = 0
  svI = 0
  while svI < etN
    if etTgt(svI) = selfId then
      svTower = 1
    end if
    svI = svI + 1
  wend
  ' HP does not regenerate, so retreating without a heal only forfeits farm:
  ' retreat for a hero or tower threat, or when low with a heal in hand to drink.
  if svThreat = 1 or svTower = 1 or (svLow = 1 and shHealSlot >= 0) then
    svRetreat = 1
    svDx = scFortX - scSelfX
    svDy = scFortY - scSelfY
    approxDist(svDx, svDy)
    if adD < 1 then
      adD = 1
    end if
    svStep = cfgRetreatStep
    if svTower = 1 then
      svStep = cfgTowerEscape
    end if
    if svStep > adD then
      svStep = adD
    end if
    svRetX = (scSelfX + svDx * svStep / adD) / 60
    svRetY = (scSelfY + svDy * svStep / adD) / 60
  end if
  if selfHp * 100 < selfMaxHp * 55 then
    if shHealSlot >= 0 then
      svHealSlot = shHealSlot
    end if
  end if
end sub

' ===== module 40_shop.bas =====
' Module: shop (prefix sh). Inventory scan and damage-first purchasing.
'
' shScanInventory: shPoisonSlot, shHealSlot (-1 if none), shPoisonCount, shEmpty
' shBuy: spends gold; records shSpent (gold spent this decision, for the
'   telemetry gold accounting in main).
'
' Order: gauntlets (+4) first because every point of damage raises the HP band a
' footman can be finished from; then the biggest damage item affordable. Poison is
' restocked to cfgPoisonStock because a poison is a guaranteed last hit.

sub shScanInventory()
  shPoisonSlot = -1
  shHealSlot = -1
  shPoisonCount = 0
  shEmpty = 0
  shHasGauntlets = 0
  shHasDagger = 0
  shHasSword = 0
  shHasAxe = 0
  shHasBow = 0
  shHasCrossbow = 0
  shHasWand = 0
  shHasBook = 0
  shHasStaff = 0
  shSlot = 0
  while shSlot < 6
    shId = itemId(shSlot)
    if shId = 0 then
      shEmpty = shEmpty + 1
    end if
    if shId = 4 then
      shPoisonSlot = shSlot
      shPoisonCount = itemCount(shSlot)
    end if
    if shId = 1 or shId = 2 then
      shHealSlot = shSlot
    end if
    if shId = 7 then
      shHasGauntlets = 1
    end if
    if shId = 11 then
      shHasDagger = 1
    end if
    if shId = 13 then
      shHasSword = 1
    end if
    if shId = 14 then
      shHasBow = 1
    end if
    if shId = 18 then
      shHasAxe = 1
    end if
    if shId = 19 then
      shHasCrossbow = 1
    end if
    if shId = 12 then
      shHasWand = 1
    end if
    if shId = 20 then
      shHasBook = 1
    end if
    if shId = 17 then
      shHasStaff = 1
    end if
    shSlot = shSlot + 1
  wend
end sub

' Buys one item id if affordable with the gold left this decision.
sub shTryBuy(id, cost)
  if shGold >= cost then
    if buyItem(id) = 1 then
      shGold = shGold - cost
      shSpent = shSpent + cost
    end if
  end if
end sub

sub shBuy()
  shSpent = 0
  shGold = selfGold
  ' Poison first: a stocked poison converts a lost last hit into 25 XP.
  if shPoisonCount < cfgPoisonStock and shGold >= cfgPoisonMinGold then
    shTryBuy(4, 40)
  end if
  ' A heal when hurt, before gear: HP never regenerates.
  if selfHp * 100 < selfMaxHp * 55 and shHealSlot < 0 then
    shTryBuy(2, 50)
  end if
  ' Never fill the last free slot with equipment: consumables can then never be
  ' bought again (no selling). Keep one slot for poison and heals.
  if shEmpty <= 1 then
    exit sub
  end if
  if shHasGauntlets = 0 then
    shTryBuy(7, 70)
  end if
  ' Keep a small reserve so a poison restock stays possible.
  shGold = shGold - cfgPoisonMinGold
  if shHasAxe = 0 then
    shTryBuy(18, 180)
  end if
  if shHasCrossbow = 0 then
    shTryBuy(19, 180)
  end if
  if shHasBook = 0 then
    shTryBuy(20, 190)
  end if
  if shHasSword = 0 then
    shTryBuy(13, 150)
  end if
  if shHasBow = 0 then
    shTryBuy(14, 150)
  end if
  if shHasWand = 0 then
    shTryBuy(12, 140)
  end if
  if shHasDagger = 0 then
    shTryBuy(11, 110)
  end if
  if shHasStaff = 0 then
    shTryBuy(17, 170)
  end if
end sub

' ===== module 90_main.bas =====
' Module: main (prefix mn). Per-decision top-level flow and telemetry.
'
' Order: config, scan, inventory, bookkeeping, survive, last-hit plan, shop, act.
' Priority when acting: retreat > secure cast > poison > attack order > hold/walk.
' Telemetry line every cfgReportEvery ticks:
'   LH tick lastHits heroKills towerKills level orders secures poisons lost deaths gold early missed

cfgInit()
scanObjects()
shScanInventory()

' ---- bookkeeping: income from gold deltas, deaths from skipped decisions ----
if mnInit = 0 then
  mnInit = 1
  mnExpectedGold = selfGold
  mnLastTick = worldTick
end if
if worldTick - mnLastTick > 1 then
  mnDeaths = mnDeaths + 1
  svLow = 0
  mnOrderedId = 0
end if
mnLastTick = worldTick
mnDelta = selfGold - mnExpectedGold
mnGained = 0
' This module never attacks structures, so income is footmen (15) and heroes
' (100). Take hero kills only until the remainder is a multiple of 15, so an
' area spell paying 105 reads as seven footmen, not a hero. An estimate: 300
' is still ambiguous, and structure income from area spells would misread.
while mnDelta >= 100 and mnDelta mod 15 <> 0
  mnHeroKills = mnHeroKills + 1
  mnDelta = mnDelta - 100
  mnGained = 1
wend
while mnDelta >= 15
  mnLastHits = mnLastHits + 1
  mnDelta = mnDelta - 15
  mnGained = 1
wend
' A basic hit landed on the ordered target and it survived: the window was early.
if mnOrderedId <> 0 and selfAttacksLanded > mnLanded and mnGained = 0 then
  mnJ = fmSlot((mnOrderedId - 1000) mod 448)
  if mnJ >= 0 then
    if efId(mnJ) = mnOrderedId then
      mnEarly = mnEarly + 1
    end if
  end if
end if
mnLanded = selfAttacksLanded
' Enemy footmen that vanished within chase distance while I was not on them.
if mnGained = 0 then
  mnMissed = mnMissed + lhVanished
end if
' An ordered target that vanished without paying us was taken by someone else.
if mnOrderedId <> 0 then
  mnJ = fmSlot((mnOrderedId - 1000) mod 448)
  mnStill = 0
  if mnJ >= 0 then
    if efId(mnJ) = mnOrderedId then
      mnStill = 1
    end if
  end if
  if mnStill = 0 then
    if mnGained = 0 then
      mnLost = mnLost + 1
      if cfgDebug = 1 then
        print "LOST ", worldTick, " id ", mnOrderedId, " pred ", mnOrderedPred, " h ", mnOrderedH, " t ", mnOrderedTick
      end if
    end if
    mnOrderedId = 0
  end if
end if

' ---- plans ----
svPlan()
lhStickId = mnOrderedId
lhPlan()

' ---- act ----
if svHealSlot >= 0 then
  useItem(svHealSlot)
end if
mnActed = 0
if svRetreat = 1 then
  walkTo(svRetX, svRetY)
  svRetreats = svRetreats + 1
  mnOrderedId = 0
  mnActed = 1
end if
if mnActed = 0 then
  if lhSecureSlot >= 0 then
    if castTarget(lhSecureSlot, lhSecureId) = 1 then
      lhSecures = lhSecures + 1
    end if
  end if
  if lhPoisonId <> 0 then
    if attackTarget(lhPoisonId) = 1 then
      if useItem(shPoisonSlot) = 1 then
        lhPoisons = lhPoisons + 1
      end if
    end if
  end if
  if lhTargetId <> 0 then
    if attackTarget(lhTargetId) = 1 then
      if mnOrderedId <> lhTargetId then
        lhOrders = lhOrders + 1
        mnOrderedPred = lhBestPred
        mnOrderedH = lhBestH
        mnOrderedTick = worldTick
        if cfgDebug = 1 then
          print "ORD ", worldTick, " id ", lhTargetId, " hp ", lhBestHp, " pred ", lhBestPred, " h ", lhBestH, " inR ", lhBestInR, " cd ", selfAttackCooldown
        end if
      end if
      mnOrderedId = lhTargetId
      mnActed = 1
    end if
  else
    if lhPoisonId <> 0 then
      ' The poison target was already ordered; keep it rather than walking away.
      mnOrderedId = lhPoisonId
      mnActed = 1
    end if
  end if
end if
if mnActed = 0 then
  if lhState = 1 then
    mnWalkX = lhHoldX
    mnWalkY = lhHoldY
  else
    mnLaneFront()
    mnWalkX = mnFrontX
    mnWalkY = mnFrontY
  end if
  if mnWalkX = selfX and mnWalkY = selfY then
    ' Already there: keep a live walk target so the engine does not auto-acquire.
    if mnNudge = 0 then
      mnNudge = 1
    else
      mnNudge = 0
    end if
    if scFortX > scSelfX then
      mnWalkX = selfX + mnNudge
    else
      mnWalkX = selfX - mnNudge
    end if
  end if
  if walkTo(mnWalkX, mnWalkY) = 0 then
    ' No path to the standoff tile (terrain or a building): aim at the anchor itself.
    if lhState = 1 then
      walkTo(efX(lhAnchor) / 60, efY(lhAnchor) / 60)
    end if
  end if
  mnOrderedId = 0
end if

' ---- shopping (works anywhere) ----
shBuy()
mnExpectedGold = selfGold - shSpent

' ---- telemetry ----
if cfgDebug = 1 and worldTick mod cfgDebugEvery = 0 then
  print "D ", worldTick, " st ", lhState, " ef ", efN, " tgt ", selfTarget, " at ", selfX, " ", selfY, " hold ", mnWalkX, " ", mnWalkY, " anc ", lhAnchorHp, " cd ", selfAttackCooldown, " hp ", selfHp, " ret ", svRetreat
end if
if worldTick mod cfgReportEvery = 0 then
  print "EX "; worldTick; " "; lmGapResets
  print "LH ", worldTick, " ", mnLastHits, " ", mnHeroKills, " ", mnTowerKills, " ", selfLevel, " ", lhOrders, " ", lhSecures, " ", lhPoisons, " ", mnLost, " ", mnDeaths, " ", selfGold, " ", mnEarly, " ", mnMissed
end if
end

' Lane front: the allied footman of my lane farthest from my god, preferring
' footmen that are fighting (a stuck straggler is never fighting); else the
' lane's waypoint. Writes mnFrontX, mnFrontY in tiles.
sub mnLaneFront()
  mnSeat = selfId - 100
  mnSlot = mnSeat mod 5
  mnLane = 1
  if mnSlot < 2 then
    mnLane = 0
  end if
  if mnSlot > 2 then
    mnLane = 2
  end if
  mnDiag = (mapWidth - 1) * 60
  mnBest = -1
  mnBestD = -1
  mnBestFight = 0
  mnI = 0
  while mnI < afN
    mnS = afX(mnI) + afY(mnI) - mnDiag
    mnL = 1
    if mnS <= -900 then
      mnL = 0
    end if
    if mnS >= 900 then
      mnL = 2
    end if
    if mnL = mnLane then
      mnDx = afX(mnI) - scFortX
      mnDy = afY(mnI) - scFortY
      mnD = mnDx * mnDx + mnDy * mnDy
      mnFight = 0
      if afTgt(mnI) <> 0 then
        mnFight = 1
      end if
      if mnFight > mnBestFight or (mnFight = mnBestFight and mnD > mnBestD) then
        mnBestFight = mnFight
        mnBestD = mnD
        mnBest = mnI
      end if
    end if
    mnI = mnI + 1
  wend
  if mnBest >= 0 then
    mnFrontX = afX(mnBest) / 60
    mnFrontY = afY(mnBest) / 60
  else
    mnFrontX = mapWidth / 2
    mnFrontY = mapHeight / 2
    if mnLane = 0 then
      mnFrontX = 14
      mnFrontY = 14
    end if
    if mnLane = 2 then
      mnFrontX = mapWidth - 15
      mnFrontY = mapHeight - 15
    end if
  end if
end sub

