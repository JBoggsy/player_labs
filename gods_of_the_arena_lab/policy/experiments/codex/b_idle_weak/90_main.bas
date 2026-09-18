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
  mnIdleDx = mnWalkX - selfX
  mnIdleDy = mnWalkY - selfY
  if lhState = 1 and mnIdleDx * mnIdleDx + mnIdleDy * mnIdleDy <= 1 and (selfClass = 0 or selfClass = 3 or selfClass = 5 or selfClass = 8) then
    ' In the hold neighborhood: permit engine acquisition instead of another walk.
    attackTarget(0)
    mnVariantActs = mnVariantActs + 1
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
  print "EX "; worldTick; " "; mnVariantActs
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
