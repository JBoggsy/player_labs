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
