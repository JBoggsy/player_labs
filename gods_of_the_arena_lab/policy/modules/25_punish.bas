' Module: punish (prefix pn). Attack an enemy hero that farms inside our tower's
' reach. Towers shoot footmen first, so an enemy hero standing beside our tower
' with the wave dying is about to take tower fire; joining in converts that into a
' hero kill (150 XP, 100 gold, six footmen's worth) and the engine auto-casts the
' full kit on the target once attackTarget is set.
'
' Inputs: scan arrays (at* allied towers, eh* enemy heroes), self data, cfg knobs.
' Output: pnTargetId (enemy hero id to attack now, or 0). State: pnTargetId
' persists with hysteresis: enter when an allied tower is firing at the hero within
' cfgPunishEnterKu of it, exit once it is farther than cfgPunishExitKu from the tower.
' Telemetry (main): pnStarts, pnTicks.

' pnD2 = squared distance (ku) from hero index i to the nearest living allied tower;
' pnShot = 1 if an allied tower is currently firing at that hero (its target id).
sub pnTowerDist(i)
  iD2 = 2147483647
  pnShot = 0
  iX = ehPos(i) / 8192
  iY = ehPos(i) mod 8192
  iId = ehMeta(i) / 65536
  iJ = 0
  while iJ < atN
    iDx = atX(iJ) - iX
    iDy = atY(iJ) - iY
    if iDx * iDx + iDy * iDy < iD2 then
      iD2 = iDx * iDx + iDy * iDy
    end if
    if atTgt(iJ) = iId then
      pnShot = 1
    end if
    iJ = iJ + 1
  wend
end sub

' pnChaseOk = 1 if chasing enemy hero index i beyond tower cover is worth it.
sub pnChaseCheck(i)
  pnChaseOk = 0
  iX = ehPos(i) / 8192
  iY = ehPos(i) mod 8192
  iDx = iX - scSelfX
  iDy = iY - scSelfY
  iD2 = iDx * iDx + iDy * iDy
  if iD2 > cfgPunishChaseMaxKu * cfgPunishChaseMaxKu then
    exit sub
  end if
  ' DPS in HP per tick times 100: mine plus any allied hero adjacent to the target.
  heroDmgFor(selfClass, selfLevel)
  iDps = selfAttackDamage * 100 / hdPer
  iAlly = 0
  iJ = 0
  while iJ < ahN
    iAx = ahX(iJ) - iX
    iAy = ahY(iJ) - iY
    if iAx * iAx + iAy * iAy <= cfgPunishAllyKu * cfgPunishAllyKu then
      iDps = iDps + ahDmg(iJ) * 100 / ahPer(iJ)
      iAlly = 1
    end if
    iJ = iJ + 1
  wend
  if iDps < 1 then
    exit sub
  end if
  iHp = ehHp(i) / 16
  iTicks = iHp * 100 / iDps
  ' Closing time: distance beyond my range at my speed, only if I am faster.
  heroSpeedFor(ehHp(i) mod 16)
  iSpeed = selfMoveSpeed / 1000
  iReach = selfAttackRange / 1000
  if iD2 > iReach * iReach then
    if iSpeed <= hsMove and iAlly = 0 then
      exit sub
    end if
    approxDist(iDx, iDy)
    iGap = adD - iReach
    iClose = iSpeed - hsMove
    if iClose < 1 then
      iClose = 1
    end if
    iTicks = iTicks + iGap / iClose
  end if
  if iTicks <= cfgPunishChaseTicks then
    pnChaseOk = 1
  end if
end sub

sub pnPlan()
  if cfgPunish = 0 then
    pnTargetId = 0
    exit sub
  end if
  ' Keep the current target while it stays near our tower and I am healthy, or
  ' while chasing it is cheap: expected time to kill from its HP over my DPS
  ' plus an adjacent teammate's, and it cannot outrun me unless already in range.
  if pnTargetId <> 0 then
    pnKeep = 0
    oI = 0
    while oI < ehN
      if ehMeta(oI) / 65536 = pnTargetId then
        pnTowerDist(oI)
        if oD2 <= cfgPunishExitKu * cfgPunishExitKu then
          pnKeep = 1
        else
          if cfgPunish = 1 and cfgPunishChase = 1 then
            pnChaseCheck(oI)
            if pnChaseOk = 1 then
              pnKeep = 1
              pnChaseTicks = pnChaseTicks + 1
            end if
          end if
        end if
      end if
      oI = oI + 1
    wend
    if selfHp * 100 < selfMaxHp * cfgPunishStopHpPct then
      pnKeep = 0
    end if
    if pnKeep = 0 then
      pnTargetId = 0
    end if
  end if
  if pnTargetId <> 0 then
    exit sub
  end if
  if selfHp * 100 < selfMaxHp * cfgPunishMinHpPct then
    exit sub
  end if
  ' Start on the lowest-HP enemy hero inside our tower's reach and within engage range.
  pnBestHp = 2147483647
  oI = 0
  while oI < ehN
    pnTowerDist(oI)
    ' A tower firing at the hero is the signal: it stands inside tower range with
    ' no footman left to absorb the shots. Distance alone is not enough (heroes
    ' farm at the edge of tower range untouched).
    if pnShot = 1 and oD2 <= cfgPunishEnterKu * cfgPunishEnterKu then
      oDx = ehPos(oI) / 8192 - scSelfX
      oDy = ehPos(oI) mod 8192 - scSelfY
      if oDx * oDx + oDy * oDy <= cfgPunishEngageKu * cfgPunishEngageKu then
        if ehHp(oI) < pnBestHp then
          pnBestHp = ehHp(oI)
          pnTargetId = ehMeta(oI) / 65536
        end if
      end if
    end if
    oI = oI + 1
  wend
end sub
