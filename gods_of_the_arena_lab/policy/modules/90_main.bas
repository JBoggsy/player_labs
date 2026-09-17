' Module: main (prefix mn). Per-decision top-level flow and telemetry.
'
' Order: config, scan, inventory, bookkeeping, survive, last-hit plan, shop, act.
' Priority when acting: retreat > punish > kill steal > secure cast > poison > attack order > hold/walk.
' Telemetry line every cfgReportEvery ticks:
'   LH tick lastHits heroKills towerKills level orders secures poisons lost deaths gold 0 0 punishStarts punishTicks punishChaseTicks chaseTicks ksHeroWindows ksCasts ksStructWindows ksPrepTicks

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
' Income is footmen (15), heroes (100) and finishing blows on structures (75).
' Take hero kills only until the remainder is a multiple of 15, so an area spell
' paying 105 reads as seven footmen, not a hero. An estimate; the replay expander
' has the exact counts.
while mnDelta >= 100 and mnDelta mod 15 <> 0
  mnHeroKills = mnHeroKills + 1
  mnDelta = mnDelta - 100
  mnGained = 1
wend
' 75 gold is a structure kill when my ordered target was a structure that is gone,
' else five footmen from an area spell (exact counts come from the replay expander).
if mnOrderedId > 0 and mnOrderedId < 100 and mnDelta >= 75 then
  oGone = 1
  oJ = 0
  while oJ < etN
    if etX(oJ) mod 64 = mnOrderedId then
      oGone = 0
    end if
    oJ = oJ + 1
  wend
  if oGone = 1 then
    mnTowerKills = mnTowerKills + 1
    mnDelta = mnDelta - 75
    mnGained = 1
    mnOrderedId = 0
  end if
end if
while mnDelta >= 15
  mnLastHits = mnLastHits + 1
  mnDelta = mnDelta - 15
  mnGained = 1
wend
' An ordered target that vanished without paying us was taken by someone else
' (footman orders only; hero orders are cleared by the punish module).
if mnOrderedId >= 1000 then
  oJ = fmSlot((mnOrderedId - 1000) mod 448)
  mnStill = 0
  if oJ >= 0 then
    if efId(oJ) = mnOrderedId then
      mnStill = 1
    end if
  end if
  if mnStill = 0 then
    if mnGained = 0 then
      mnLost = mnLost + 1
    end if
    mnOrderedId = 0
  end if
end if

' ---- plans ----
pnPlan()
svPlan()
ksPlan()
lhStickId = mnOrderedId
lhPlan()

' ---- act ----
if svHealSlot >= 0 then
  useItem(svHealSlot)
end if
mnActed = 0
if svRetreat = 1 then
  walkTo(svRetX, svRetY)
  mnOrderedId = 0
  mnActed = 1
end if
if mnActed = 0 and pnTargetId <> 0 then
  ' Punish: an enemy hero farming under our tower is the best income on the map.
  if attackTarget(pnTargetId) = 1 then
    pnTicks = pnTicks + 1
    if mnOrderedId <> pnTargetId then
      pnStarts = pnStarts + 1
    end if
    mnOrderedId = pnTargetId
    mnActed = 1
  end if
end if
if mnActed = 0 and ksTargetId <> 0 then
  ' Kill steal: the finishing blow on a hero or structure teammates are fighting.
  if ksSlot >= 0 then
    if castTarget(ksSlot, ksTargetId) = 1 then
      ksCasts = ksCasts + 1
    end if
    if ksTargetId >= 100 and ksTargetId < 1000 then
      attackTarget(ksTargetId)
    end if
    mnOrderedId = ksTargetId
    mnActed = 1
  else
    if attackTarget(ksTargetId) = 1 then
      mnOrderedId = ksTargetId
      mnActed = 1
    end if
  end if
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
  if ksPrepOn = 1 then
    ' A low, shielded structure nearby: stand at reach for its finishing hit.
    mnWalkX = ksPrepX
    mnWalkY = ksPrepY
    ksPrepTicks = ksPrepTicks + 1
  else
    if lhState = 1 then
      mnWalkX = lhHoldX
      mnWalkY = lhHoldY
    else
      mnLaneFront()
      mnWalkX = mnFrontX
      mnWalkY = mnFrontY
    end if
  end if
  mnChase = 0
  if cfgChaseClass = 1 and ksHold = 0 and lhState = 1 and lhAnchor >= 0 then
    oDx = efX(lhAnchor) - scSelfX
    oDy = efY(lhAnchor) - scSelfY
    if oDx * oDx + oDy * oDy <= lhChase * lhChase then
      mnChase = 1
    end if
  end if
  mnIdleDx = mnWalkX - selfX
  mnIdleDy = mnWalkY - selfY
  if mnChase = 1 then
    ' Chase classes: keep the engine attacking the anchor footman instead of
    ' walking to a standoff point.
    if selfTarget = 0 then
      attackTarget(efId(lhAnchor))
    end if
    mnChases = mnChases + 1
  else
  if cfgIdleHere = 1 and ksHold = 0 and lhState = 1 and mnIdleDx * mnIdleDx + mnIdleDy * mnIdleDy <= 1 then
    ' Idle classes: at the standoff point, stop walking and let the engine
    ' auto-acquire and attack instead of holding for windows.
    attackTarget(0)
    mnIdles = mnIdles + 1
  else
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
  end if
  end if
  mnOrderedId = 0
end if

' ---- shopping (works anywhere) ----
shBuy()
mnExpectedGold = selfGold - shSpent

' ---- telemetry ----
if worldTick mod cfgReportEvery = 0 then
  print "LH ", worldTick, " ", mnLastHits, " ", mnHeroKills, " ", mnTowerKills, " ", selfLevel, " ", lhOrders, " ", lhSecures, " ", lhPoisons, " ", mnLost, " ", mnDeaths, " ", selfGold, " ", 0, " ", 0, " ", pnStarts, " ", pnTicks, " ", pnChaseTicks, " ", mnChases, " ", ksHeroWin, " ", ksCasts, " ", ksStructWin, " ", ksPrepTicks
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
  oI = 0
  while oI < afN
    oS = afX(oI) + afY(oI) - mnDiag
    oL = 1
    if oS <= -900 then
      oL = 0
    end if
    if oS >= 900 then
      oL = 2
    end if
    if oL = mnLane then
      oDx = afX(oI) - scFortX
      oDy = afY(oI) - scFortY
      oD = oDx * oDx + oDy * oDy
      mnFight = 0
      if afTgt(oI) <> 0 then
        mnFight = 1
      end if
      if mnFight > mnBestFight or (mnFight = mnBestFight and oD > mnBestD) then
        mnBestFight = mnFight
        mnBestD = oD
        mnBest = oI
      end if
    end if
    oI = oI + 1
  wend
  if mnBest >= 0 then
    mnFrontX = afX(mnBest) / 60
    mnFrontY = afY(mnBest) / 60
    ' A front with an enemy hero on it and no allied hero near it is a place
    ' to die, not to farm: wait where I am instead.
    mnUnsafe = 0
    oI = 0
    while oI < ehN
      oDx = ehPos(oI) / 8192 - afX(mnBest)
      oDy = ehPos(oI) mod 8192 - afY(mnBest)
      if oDx * oDx + oDy * oDy <= cfgHeroFearRange * cfgHeroFearRange then
        mnUnsafe = 1
      end if
      oI = oI + 1
    wend
    if mnUnsafe = 1 then
      oI = 0
      while oI < ahN
        oDx = ahX(oI) - afX(mnBest)
        oDy = ahY(oI) - afY(mnBest)
        if oDx * oDx + oDy * oDy <= cfgHeroFearRange * cfgHeroFearRange then
          mnUnsafe = 0
        end if
        oI = oI + 1
      wend
    end if
    if mnUnsafe = 1 then
      mnFrontX = selfX
      mnFrontY = selfY
    end if
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
