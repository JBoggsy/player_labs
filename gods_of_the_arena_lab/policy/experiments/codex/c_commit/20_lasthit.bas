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
