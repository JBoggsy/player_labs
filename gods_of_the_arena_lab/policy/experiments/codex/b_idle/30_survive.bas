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
