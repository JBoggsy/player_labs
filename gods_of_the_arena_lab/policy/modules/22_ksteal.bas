' Module: ksteal (prefix ks). Take the killing blow on enemy heroes and structures
' that teammates are already fighting; never start a fight alone.
'
' Inputs: scan arrays (eh* enemy heroes, et* enemy structures, ah* allied heroes,
' af* allied footmen), the drop-event rings (lhRecordDrop, lhEventInc), self data,
' cfg knobs. Outputs, rewritten every decision:
'   ksTargetId  object to hit now (enemy hero or structure), or 0
'   ksSlot      -1 basic attack, else the ability slot to castTarget on ksTargetId
'   ksHold      1 while an enemy hero is within cfgKsHoldKu: farm by windows only,
'               so the engine cannot auto-cast the kit on footmen
'   ksPrepOn, ksPrepX/Y  1 and a tile while a shielded structure nearby is about to
'               die: the farm layer stands there instead of at its hold point
' Telemetry: ksHeroWin, ksCasts, ksStructWin.
'
' Method: the footman last-hit prediction on hero and structure targets. A hero is
' "engaged" when an allied hero within cfgKsAllyKu of it targets it or its HP
' dropped within the last two seconds. For an engaged target in reach, predict HP
' at the landing tick of my basic hit and of each ready strike (melee: now;
' projectile: 45 ku per tick; short area casts: their delay). A window is
' 0 < predicted <= damage; prefer the spell with the earliest landing, then the
' basic hit. Structures: engaged when their HP is dropping and a footman shields
' me from the tower; basic hit only.

' Strike slot table for my class, entries k = 0..4 via ksSpec(k):
' spDmg, spRange (ku), spCast (ticks), spProj (1 projectile), spMana, spSlot,
' spArea (1: an area cast that lands where the target stands now, so it needs a
' target that is not moving; 2: a ring around me, target 0.7 to 2.3 tiles away).
' Slot 0 passives that are free projectiles are included (Ranger, Crossbowman,
' Lich). Casts over 24 ticks and line footprints are excluded.
sub ksSpec(k)
  spDmg = 0
  spSlot = -1
  spCast = 0
  spProj = 0
  spMana = 0
  spRange = 0
  spArea = 0
  if selfClass = 0 then
    if k = 0 then
      spSlot = 1
      spDmg = 40
      spRange = 90
      spMana = 20
    end if
    if k = 1 then
      spSlot = 3
      spDmg = 90
      spRange = 110
      spCast = 6
      spMana = 70
    end if
  end if
  if selfClass = 1 then
    if k = 0 then
      spSlot = 0
      spDmg = 16
      spRange = 420
      spProj = 1
    end if
    if k = 1 then
      spSlot = 1
      spDmg = 32
      spRange = 360
      spProj = 1
      spMana = 18
    end if
    if k = 2 then
      spSlot = 2
      spDmg = 48
      spRange = 390
      spCast = 24
      spMana = 32
      spArea = 1
    end if
  end if
  if selfClass = 2 then
    if k = 0 then
      spSlot = 1
      spDmg = 42
      spRange = 330
      spProj = 1
      spMana = 28
    end if
  end if
  if selfClass = 3 then
    if k = 0 then
      spSlot = 3
      spDmg = 85
      spRange = 200
      spCast = 24
      spMana = 75
      spArea = 1
    end if
  end if
  if selfClass = 4 then
    if k = 0 then
      spSlot = 1
      spDmg = 38
      spRange = 90
      spMana = 16
    end if
    if k = 1 then
      spSlot = 2
      spDmg = 52
      spRange = 120
      spCast = 6
      spMana = 28
    end if
    if k = 2 then
      spSlot = 3
      spDmg = 100
      spRange = 300
      spProj = 1
      spMana = 65
    end if
  end if
  if selfClass = 5 then
    if k = 0 then
      spSlot = 1
      spDmg = 42
      spRange = 90
      spMana = 18
    end if
    if k = 1 then
      spSlot = 2
      spDmg = 60
      spRange = 160
      spCast = 24
      spMana = 36
      spArea = 1
    end if
    if k = 2 then
      spSlot = 3
      spDmg = 110
      spRange = 138
      spCast = 12
      spMana = 80
      spArea = 2
    end if
  end if
  if selfClass = 6 then
    if k = 0 then
      spSlot = 0
      spDmg = 20
      spRange = 420
      spProj = 1
    end if
    if k = 1 then
      spSlot = 1
      spDmg = 50
      spRange = 400
      spProj = 1
      spMana = 22
    end if
    if k = 2 then
      spSlot = 2
      spDmg = 68
      spRange = 360
      spCast = 12
      spMana = 40
    end if
  end if
  if selfClass = 7 then
    if k = 0 then
      spSlot = 0
      spDmg = 14
      spRange = 360
      spProj = 1
    end if
    if k = 1 then
      spSlot = 1
      spDmg = 48
      spRange = 400
      spProj = 1
      spMana = 30
    end if
    if k = 2 then
      spSlot = 2
      spDmg = 66
      spRange = 300
      spCast = 24
      spMana = 48
      spArea = 1
    end if
    if k = 3 then
      spSlot = 3
      spDmg = 125
      spRange = 390
      spCast = 24
      spMana = 110
      spArea = 1
    end if
  end if
  if selfClass = 8 then
    if k = 0 then
      spSlot = 1
      spDmg = 36
      spRange = 280
      spProj = 1
      spMana = 24
    end if
    if k = 1 then
      spSlot = 3
      spDmg = 105
      spRange = 300
      spCast = 24
      spMana = 90
      spArea = 1
    end if
  end if
  if selfClass = 9 then
    if k = 0 then
      spSlot = 1
      spDmg = 45
      spRange = 90
    end if
    if k = 1 then
      spSlot = 2
      spDmg = 40
      spRange = 150
      spCast = 12
      spMana = 12
    end if
  end if
end sub

' Evaluates one target: (iX, iY) ku, ring slot iS, HP iHp, attacker period iPer,
' structure flag iStruct. Writes ksCandSlot (-1 basic, -2 none) and ksCandH
' (landing ticks) for the earliest converting window.
sub ksWindow()
  ksCandSlot = -2
  ksCandH = 100000
  iDx = iX - scSelfX
  iDy = iY - scSelfY
  iD2 = iDx * iDx + iDy * iDy
  iReach = selfAttackRange / 1000 - cfgRangeSlack
  ' Heroes a teammate is fighting may be approached from farther than a footman:
  ' the prediction includes the walk, and a miss only costs the walk back to farm.
  iChase = cfgKsHeroChaseKu
  if iStruct = 1 then
    ' Structures allow at least the siege range (105 ku from the footprint) and
    ' may be walked to from farther away: a finishing hit is worth 100 XP.
    if iReach < 105 then
      iReach = 105
    end if
    iChase = cfgKsStructChaseKu
  end if
  ' Basic hit: in range now, or within chase distance (walk in, then windup).
  iH = -1
  if iD2 <= iReach * iReach then
    iH = selfAttackCooldown - 1
    if iH < 0 then
      iH = 0
    end if
  else
    if iD2 <= (iReach + iChase) * (iReach + iChase) then
      approxDist(iDx, iDy)
      heroDmgFor(selfClass, 1)
      iH = (adD - iReach) / (selfMoveSpeed / 1000 + 1) + hdPer * 45 / 100
    end if
  end if
  if iH >= 0 then
    lhEventInc(iS, iH, iPer)
    if iHp - lhInc > 0 and iHp - lhInc <= selfAttackDamage then
      ksCandSlot = -1
      ksCandH = iH
    end if
  end if
  if iStruct = 1 then
    exit sub
  end if
  ' Spells: each ready strike whose predicted damage window is open.
  iK = 0
  while iK < 5
    ksSpec(iK)
    if spSlot >= 0 and spArea >= 1 and cfgKsAreaSpells = 0 then
      spSlot = -1
    end if
    if spSlot >= 0 and spArea = 1 and iStill = 0 then
      spSlot = -1
    end if
    if spSlot >= 0 and spArea = 2 and (iD2 < 1600 or iD2 > 19600) then
      spSlot = -1
    end if
    if spSlot >= 0 then
      if iD2 <= spRange * spRange and abilityCharges(spSlot) > 0 and abilityCooldown(spSlot) = 0 and selfMana >= spMana then
        iSH = spCast
        if spProj = 1 then
          approxDist(iDx, iDy)
          iSH = (adD + 44) / 45
          if iSH < 1 then
            iSH = 1
          end if
        end if
        lhEventInc(iS, iSH, iPer)
        if iHp - lhInc > 0 and iHp - lhInc <= spDmg and iSH < ksCandH then
          ksCandSlot = spSlot
          ksCandH = iSH
        end if
      end if
    end if
    iK = iK + 1
  wend
end sub

sub ksPlan()
  ksTargetId = 0
  ksSlot = -1
  ksHold = 0
  if cfgKsteal = 0 then
    exit sub
  end if
  ksBestH = 100000
  ' Enemy heroes: record drops, hold spells when one is near, find windows.
  oI = 0
  while oI < ehN
    oId = ehMeta(oI) / 65536
    lhRingSlot(oId)
    lhRecordDrop(rsSlot, ehHp(oI) / 16, cfgHeroPeriod)
    ' Still if it stood on the same tile last decision (area casts land there).
    iStill = 0
    if ehPrev(oId - 100) = ehPos(oI) then
      iStill = 1
    end if
    ehPrev(oId - 100) = ehPos(oI)
    iX = ehPos(oI) / 8192
    iY = ehPos(oI) mod 8192
    oDx = iX - scSelfX
    oDy = iY - scSelfY
    if oDx * oDx + oDy * oDy <= cfgKsHoldKu * cfgKsHoldKu then
      ksHold = 1
    end if
    ' Engaged: an allied hero near it is attacking it, or it took a hit lately.
    oEng = 0
    oJ = 0
    while oJ < ahN
      if ahTgt(oJ) = oId then
        oAx = ahX(oJ) - iX
        oAy = ahY(oJ) - iY
        if oAx * oAx + oAy * oAy <= cfgKsAllyKu * cfgKsAllyKu then
          oEng = 1
        end if
      end if
      oJ = oJ + 1
    wend
    if fmEv1(rsSlot) > 0 then
      if worldTick - fmEv1(rsSlot) / 256 <= cfgKsRecentTicks then
        oEng = 1
      end if
    end if
    if oEng = 1 and selfHp * 100 >= selfMaxHp * cfgKsMinHpPct then
      iS = rsSlot
      iHp = ehHp(oI) / 16
      iPer = cfgHeroPeriod
      iStruct = 0
      ksWindow()
      if ksCandSlot > -2 and ksCandH < ksBestH then
        ksBestH = ksCandH
        ksTargetId = oId
        ksSlot = ksCandSlot
      end if
    end if
    oI = oI + 1
  wend
  if ksTargetId <> 0 then
    ksHeroWin = ksHeroWin + 1
    exit sub
  end if
  ' Structures: only the finishing hit, only with a footman shield, only while
  ' someone else is already bringing it down. A shielded structure predicted to
  ' die within cfgKsStructPrepTicks is also a place to stand (ksPrepOn, ksPrepX/Y):
  ' the farm layer walks there so the one-second finishing window can open.
  ksPrepOn = 0
  oI = 0
  while oI < etN
    if etTgt(oI) mod 2 = 1 then
      oId = etX(oI) mod 64
      lhRingSlot(oId)
      lhRecordDrop(rsSlot, etHp(oI), cfgFootmanPeriod)
      if fmEv1(rsSlot) > 0 and etTgt(oI) / 8 <> selfId then
        ' A tower needs allied footmen in its range to shoot instead of me;
        ' a barracks (kind 5) does not attack.
        iX = etX(oI) / 64
        iY = etY(oI)
        oAllies = 0
        oJ = 0
        while oJ < afN
          oAx = afX(oJ) - iX
          oAy = afY(oJ) - iY
          if oAx * oAx + oAy * oAy <= cfgTowerFarmAlliesKu * cfgTowerFarmAlliesKu then
            oAllies = oAllies + 1
          end if
          oJ = oJ + 1
        wend
        if (etTgt(oI) / 2) mod 4 = 5 then
          oAllies = 99
        end if
        if worldTick - fmEv1(rsSlot) / 256 <= cfgKsRecentTicks and oAllies >= cfgKsStructAllies then
          oDx = iX - scSelfX
          oDy = iY - scSelfY
          lhEventInc(rsSlot, cfgKsStructPrepTicks, cfgFootmanPeriod)
          if ksPrepOn = 0 and etHp(oI) - lhInc <= 0 and oDx * oDx + oDy * oDy <= cfgKsStructPrepKu * cfgKsStructPrepKu then
            ' Stand at siege reach on my side of it, ready for the last hit.
            approxDist(oDx, oDy)
            if adD < 1 then
              adD = 1
            end if
            oD = selfAttackRange / 1000
            if oD < 105 then
              oD = 105
            end if
            ksPrepOn = 1
            ksPrepX = (iX - oDx * (oD - 30) / adD) / 60
            ksPrepY = (iY - oDy * (oD - 30) / adD) / 60
          end if
          iS = rsSlot
          iHp = etHp(oI)
          iPer = cfgFootmanPeriod
          iStruct = 1
          ksWindow()
          if ksCandSlot = -1 then
            ksTargetId = oId
            ksSlot = -1
            ksStructWin = ksStructWin + 1
            exit sub
          end if
        end if
      end if
    end if
    oI = oI + 1
  wend
end sub
