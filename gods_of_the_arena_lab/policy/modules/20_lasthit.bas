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

dim fmHp(511)
dim fmSeen(511)
dim fmEv1(511)
dim fmEv2(511)
dim efAtt(63)
dim efTw(63)
dim efHero(63)

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

' Records one object's HP into its ring slot as a repeating drop event
' (same attacker, same phase mod period, same amount: refresh; else shift).
sub lhRecordDrop(slot, hp, per)
  if fmSeen(slot) = 0 or worldTick - fmSeen(slot) > cfgSeenStale then
    fmEv1(slot) = 0
    fmEv2(slot) = 0
  else
    oD = fmHp(slot) - hp
    if oD > 0 and oD < 256 then
      oNew = (worldTick - 1) * 256 + oD
      oSame = 0
      if fmEv1(slot) > 0 then
        if fmEv1(slot) mod 256 = oD and ((worldTick - 1) - fmEv1(slot) / 256) mod per = 0 then
          oSame = 1
        end if
      end if
      if oSame = 1 then
        fmEv1(slot) = oNew
      else
        fmEv2(slot) = fmEv1(slot)
        fmEv1(slot) = oNew
      end if
    end if
  end if
  fmHp(slot) = hp
  fmSeen(slot) = worldTick
end sub

' Records HP drops of visible enemy footmen as repeating events.
sub lhUpdateMemory()
  oI = 0
  while oI < efN
    lhRecordDrop((efId(oI) - 1000) mod 448, efHp(oI), cfgFootmanPeriod)
    oI = oI + 1
  wend
end sub

' Counts attackers attached to each enemy footman this decision.
sub lhAttachers()
  oI = 0
  while oI < efN
    efAtt(oI) = 0
    efTw(oI) = 0
    efHero(oI) = 32
    oI = oI + 1
  wend
  oI = 0
  while oI < afN
    if afTgt(oI) >= 1000 then
      oJ = fmSlot((afTgt(oI) - 1000) mod 448)
      if oJ >= 0 then
        if efId(oJ) = afTgt(oI) then
          oDx = afX(oI) - efX(oJ)
          oDy = afY(oI) - efY(oJ)
          if oDx * oDx + oDy * oDy <= 8100 then
            efAtt(oJ) = efAtt(oJ) + 1
          end if
        end if
      end if
    end if
    oI = oI + 1
  wend
  oI = 0
  while oI < atN
    if atTgt(oI) >= 1000 then
      oJ = fmSlot((atTgt(oI) - 1000) mod 448)
      if oJ >= 0 then
        if efId(oJ) = atTgt(oI) then
          efTw(oJ) = atDmg(oI)
        end if
      end if
    end if
    oI = oI + 1
  wend
  oI = 0
  while oI < ahN
    if ahTgt(oI) >= 1000 then
      oJ = fmSlot((ahTgt(oI) - 1000) mod 448)
      if oJ >= 0 then
        if efId(oJ) = ahTgt(oI) then
          efHero(oJ) = ahDmg(oI) * 256 + ahPer(oI)
        end if
      end if
    end if
    oI = oI + 1
  wend
end sub

' Number of repeats of an event at tick evT with period per landing in
' [worldTick, worldTick + h]. Result in evHits.
sub lhEventHits(evT, per, h)
  evHits = (worldTick + h - evT) / per - (worldTick - 1 - evT) / per
end sub

' lhInc = predicted damage to the object in ring slot s over the next h ticks
' from its recorded drop events alone (each repeating with period per).
sub lhEventInc(s, h, per)
  lhInc = 0
  iE = 0
  while iE < 2
    if iE = 0 then
      iEv = fmEv1(s)
    else
      iEv = fmEv2(s)
    end if
    if iEv > 0 then
      iT = iEv / 256
      iA = iEv mod 256
      if worldTick - iT <= cfgEventStale then
        lhEventHits(iT, per, h)
        lhInc = lhInc + iA * evHits
      end if
    end if
    iE = iE + 1
  wend
end sub

' lhInc = predicted damage to enemy footman i over the next h ticks (inclusive
' of this tick's footman and tower updates, exclusive of my own hit).
sub lhIncoming(i, h)
  lhInc = 0
  iRep = 0
  iS = (efId(i) - 1000) mod 448
  iE = 0
  while iE < 2
    if iE = 0 then
      iEv = fmEv1(iS)
    else
      iEv = fmEv2(iS)
    end if
    if iEv > 0 then
      iT = iEv / 256
      iA = iEv mod 256
      if worldTick - iT <= cfgEventStale then
        iPer = cfgFootmanPeriod
        if efTw(i) > 0 and iA = efTw(i) then
          iPer = cfgTowerPeriod
        else
          if efHero(i) / 256 > 0 and iA = efHero(i) / 256 then
            iPer = efHero(i) mod 256
          else
            iRep = iRep + iA / 12
          end if
        end if
        lhEventHits(iT, iPer, h)
        lhInc = lhInc + iA * evHits
      end if
    end if
    iE = iE + 1
  wend
  ' Attached footmen without a recorded hit yet: expected value.
  iExtra = efAtt(i) - iRep
  if iExtra > 0 then
    lhInc = lhInc + iExtra * 12 * (h + 8) / cfgFootmanPeriod
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
  iI = 0
  while iI < etN
    iDx = etX(iI) / 64 - x
    iDy = etY(iI) - y
    iTg = etTgt(iI) / 8
    if (etTgt(iI) / 2) mod 4 = 4 and iDx * iDx + iDy * iDy <= cfgTowerAvoid * cfgTowerAvoid then
      ' Safe beside the tower when it is busy with a footman, or idle with
      ' allied footmen inside its reach to absorb the first shots; the survive
      ' module leaves the moment it targets me.
      if iTg = selfId then
        ntNear = 1
      end if
      if iTg = 0 then
        iAllies = 0
        iJ = 0
        while iJ < afN
          iAx = afX(iJ) - etX(iI) / 64
          iAy = afY(iJ) - etY(iI)
          if iAx * iAx + iAy * iAy <= cfgTowerFarmAlliesKu * cfgTowerFarmAlliesKu then
            iAllies = iAllies + 1
          end if
          iJ = iJ + 1
        wend
        if iAllies < cfgTowerFarmAllies then
          ntNear = 1
        end if
      end if
    end if
    iI = iI + 1
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
  if spDmg > 0 then
    if abilityCharges(1) > 0 and abilityCooldown(1) = 0 and selfMana >= spMana then
      lhStrikeReady = 1
    end if
  end if
  lhPoisonReady = 0
  if shPoisonSlot >= 0 then
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
  oI = 0
  while oI < efN
    oDx = efX(oI) - scSelfX
    oDy = efY(oI) - scSelfY
    if oDx * oDx + oDy * oDy <= lhChase * lhChase then
      lhLocalCount = lhLocalCount + 1
    end if
    lhS = efX(oI) + efY(oI) - lhDiag
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
    oI = oI + 1
  wend
  lhBest = -1
  lhBestScore = 2147483647
  lhAnchor = -1
  lhAnchorHp = 2147483647
  lhAnchorPos = 0
  lhAnchorD2 = 2147483647
  oI = 0
  while oI < efN
    oDx = efX(oI) - scSelfX
    oDy = efY(oI) - scSelfY
    oD2 = oDx * oDx + oDy * oDy
    lhInR = 0
    if oD2 <= lhReach * lhReach then
      lhInR = 1
    end if
    lhNearEnemyTower(efX(oI), efY(oI))
    ' Anchor tiers: footmen already within chase distance (any lane) come first,
    ' then footmen in my lane, then anything visible. This keeps the hero on
    ' local opportunities without wandering into another lane for a distant one.
    lhChase = lhReach + cfgChaseKu
    lhLocal = 0
    if oD2 <= lhChase * lhChase then
      lhLocal = 1
    end if
    lhLaneOk = 1
    if lhLocal = 0 then
      if lhLocalCount > 0 then
        lhLaneOk = 0
      else
        if lhLaneCount > 0 then
          lhS = efX(oI) + efY(oI) - lhDiag
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
      oJ = 0
      while oJ < ahN
        if ahTgt(oJ) = efId(oI) then
          lhOrderOk = 0
        end if
        oJ = oJ + 1
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
        approxDist(oDx, oDy)
        lhH = (adD - lhReach) / lhSpeed + lhWindup
      end if
      lhIncoming(oI, lhH)
      lhPred = efHp(oI) - lhInc
      lhWindow = selfAttackDamage
      if efId(oI) = lhStickId then
        lhWindow = lhWindow + cfgStickSlack
      end if
      if lhOrderOk = 1 and lhPred > 0 and lhPred <= lhWindow then
        lhScore = lhH * 10 + lhPred
        if efId(oI) = lhStickId then
          lhScore = lhScore - cfgStickBonus
        end if
        if lhScore < lhBestScore then
          lhBestScore = lhScore
          lhBest = oI
        end if
      end if
      if lhOrderOk = 1 and lhPred <= 0 then
        ' The basic attack is too slow: try an instant source.
        if lhPoisonId = 0 and lhPoisonReady = 1 and lhInR = 1 and efHp(oI) <= 35 then
          lhPoisonId = efId(oI)
        else
          if lhSecureId = 0 and lhStrikeReady = 1 and oD2 <= spRange * spRange then
            if spProj = 1 then
              ' Projectile: at least one tick of travel, resolves after this tick's units.
              approxDist(oDx, oDy)
              lhSH = (adD + 44) / 45
              if lhSH < 1 then
                lhSH = 1
              end if
              lhIncoming(oI, lhSH)
              lhPredS = efHp(oI) - lhInc
            else
              ' Melee cast resolves inside this decision, before any creep swings.
              lhPredS = efHp(oI)
            end if
            if lhPredS > 0 and lhPredS <= spDmg then
              lhSecureId = efId(oI)
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
          lhAnchor = oI
        end if
      else
        if lhAnchorPos = 0 and oD2 < lhAnchorD2 then
          lhAnchorD2 = oD2
          lhAnchor = oI
          lhAnchorHp = lhPred
        end if
      end if
    end if
    oI = oI + 1
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
