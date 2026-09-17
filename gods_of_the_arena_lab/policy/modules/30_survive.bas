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
  ' An enemy hero attacking me, or one close while I am not healthy, is a fight
  ' this module does not take: a larger policy decides fights, this one farms.
  svThreat = 0
  oI = 0
  while oI < ehN
    oDx = ehPos(oI) / 8192 - scSelfX
    oDy = ehPos(oI) mod 8192 - scSelfY
    oD2 = oDx * oDx + oDy * oDy
    if ehMeta(oI) mod 65536 = selfId and oD2 <= cfgHeroHuntRange * cfgHeroHuntRange then
      svThreat = 1
    end if
    if selfHp * 100 < selfMaxHp * 60 and oD2 <= cfgHeroFearRange * cfgHeroFearRange then
      svThreat = 1
    end if
    oI = oI + 1
  wend
  ' An enemy tower shooting me: leave its range now (30 damage per second).
  svTower = 0
  oI = 0
  while oI < etN
    if etTgt(oI) / 8 = selfId then
      svTower = 1
    end if
    oI = oI + 1
  wend
  ' HP does not regenerate, so retreating without a heal only forfeits farm:
  ' retreat for a hero or tower threat, or when low with a heal in hand to drink.
  ' While punishing an overextended enemy under our tower, the tower is on our
  ' side: only HP decides.
  if pnTargetId <> 0 and svTower = 0 then
    svThreat = 0
  end if
  if svThreat = 1 or svTower = 1 or (svLow = 1 and shHealSlot >= 0) then
    svRetreat = 1
    oDx = scFortX - scSelfX
    oDy = scFortY - scSelfY
    approxDist(oDx, oDy)
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
    svRetX = (scSelfX + oDx * svStep / adD) / 60
    svRetY = (scSelfY + oDy * svStep / adD) / 60
  end if
  if selfHp * 100 < selfMaxHp * 55 then
    if shHealSlot >= 0 then
      svHealSlot = shHealSlot
    end if
  end if
end sub
