' Module: shop (prefix sh). Inventory scan and damage-first purchasing.
'
' shScanInventory: shPoisonSlot, shHealSlot (-1 if none), shPoisonCount, shEmpty
' shBuy: spends gold; records shSpent (gold spent this decision, for the
'   telemetry gold accounting in main).
'
' Order: gauntlets (+4) early, then the biggest damage items, then HP; poison is
' stocked only while a footman takes two hits. The goal is a level and item
' advantage over the enemy heroes: every 15 gold of farm becomes stats.

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
  shHasArmor = 0
  shHasPauldrons = 0
  oI = 0
  while oI < 6
    oId = itemId(oI)
    if oId = 0 then
      shEmpty = shEmpty + 1
    end if
    if oId = 4 then
      shPoisonSlot = oI
      shPoisonCount = itemCount(oI)
    end if
    if oId = 1 or oId = 2 then
      shHealSlot = oI
    end if
    if oId = 7 then
      shHasGauntlets = 1
    end if
    if oId = 11 then
      shHasDagger = 1
    end if
    if oId = 13 then
      shHasSword = 1
    end if
    if oId = 14 then
      shHasBow = 1
    end if
    if oId = 18 then
      shHasAxe = 1
    end if
    if oId = 19 then
      shHasCrossbow = 1
    end if
    if oId = 12 then
      shHasWand = 1
    end if
    if oId = 20 then
      shHasBook = 1
    end if
    if oId = 17 then
      shHasStaff = 1
    end if
    if oId = 16 then
      shHasArmor = 1
    end if
    if oId = 15 then
      shHasPauldrons = 1
    end if
    oI = oI + 1
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
  ' Poison while a footman still needs two hits: a stocked poison converts a lost
  ' last hit into 25 XP. Once basic damage one-shots footmen the slot is worth
  ' more as equipment.
  if selfAttackDamage < 60 and shPoisonCount < cfgPoisonStock and shGold >= cfgPoisonMinGold then
    shTryBuy(4, 40)
  end if
  ' A heal when hurt, before gear: HP never regenerates.
  if selfHp * 100 < selfMaxHp * 55 and shHealSlot < 0 then
    shTryBuy(2, 50)
  end if
  ' Equipment fills every slot but one, which stays free for a heal (or the poison
  ' while it is still stocked). Income must become stats, not a gold balance: the
  ' best-farming seats used to end games with 380 gold unspent.
  shFree = shEmpty
  if shHealSlot >= 0 then
    shFree = shFree + 1
  end if
  if shFree <= 1 then
    exit sub
  end if
  if selfAttackDamage < 60 then
    shGold = shGold - cfgPoisonMinGold
  end if
  ' Cheap early damage first: +4 is a sixth of level-1 damage and widens every
  ' last-hit window. Then the big damage items, then HP for the fights.
  if shHasGauntlets = 0 and selfLevel < 4 then
    shTryBuy(7, 70)
  end if
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
  if shHasArmor = 0 then
    shTryBuy(16, 160)
  end if
  if shHasBow = 0 then
    shTryBuy(14, 150)
  end if
  if shHasPauldrons = 0 then
    shTryBuy(15, 140)
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
