' Module: scan (prefix sc). One pass over the object list into typed arrays.
' The VM allows 32 arrays in total; this module uses 24 and the planner 8.

' rsSlot = ring slot for any object id (footman, hero or structure).
sub lhRingSlot(id)
  if id >= 1000 then
    rsSlot = (id - 1000) mod 448
  else
    if id >= 100 then
      rsSlot = 448 + id - 100
    else
      rsSlot = 458 + id
    end if
  end if
end sub
' Positions are stored in ku (tile * 60). Enemy objects are only those visible
' to my team this decision; allied objects are always present. Footmen are kept
' only within cfgScanRadius of me (budget).
'
' Outputs (valid for this decision):
'   efN, efId(i), efX(i), efY(i), efHp(i)     living enemy footmen
'   afN, afX(i), afY(i), afTgt(i)              living allied footmen and their targets
'   atN, atX(i), atY(i), atTgt(i), atDmg(i)    allied towers (any), their target and hit damage
'   etN, etX(i), etY(i), etTgt(i), etHp(i)     visible living enemy towers and barracks:
'                                              etX = x * 64 + id, etTgt = target * 8 + kind * 2 + exposed
'   ahN, ahX(i), ahY(i), ahTgt(i), ahDmg(i), ahPer(i)  living allied heroes (not me)
'   ehN, ehPos(i), ehMeta(i), ehHp(i)          visible living enemy heroes: position packed as
'                                              x * 8192 + y (ku), id * 65536 + target id, HP * 16 + class
'   scFortX, scFortY                           own god (fort) position
'   scEFortX, scEFortY                         enemy god position (mirror of own)
'   ehPrev(hero id - 100)                     an enemy hero's position last decision (packed as ehPos), for stillness
'   fmSlot(ring)                               id ring -> index into ef arrays (footmen), or -1;
'                                              ring slot: footman (id-1000) mod 448, hero 448+id-100,
'                                              structure 458+id (see lhRingSlot)
'   scSelfX, scSelfY                           my position in ku

dim efId(63)
dim efX(63)
dim efY(63)
dim efHp(63)
dim afX(63)
dim afY(63)
dim afTgt(63)
dim atX(15)
dim atY(15)
dim atTgt(15)
dim atDmg(15)
dim etX(23)
dim etY(23)
dim etTgt(23)
dim etHp(23)
dim ahTgt(4)
dim ahX(4)
dim ahY(4)
dim ahDmg(4)
dim ahPer(4)
dim ehPos(4)
dim ehMeta(4)
dim ehHp(4)
dim fmSlot(511)
dim ehPrev(9)

' Sets hdDmg and hdPer (basic damage and swing ticks) for a hero class and level,
' ignoring items. Table from content.nim at the deployed commit.
sub heroDmgFor(cls, lvl)
  hdDmg = 25
  hdPer = 24
  if cls = 0 then
    hdDmg = 25 + (lvl - 1) * 5
    hdPer = 24
  end if
  if cls = 1 then
    hdDmg = 25 + (lvl - 1) * 6
    hdPer = 18
  end if
  if cls = 2 then
    hdDmg = 38 + (lvl - 1) * 8
    hdPer = 30
  end if
  if cls = 3 then
    hdDmg = 22 + (lvl - 1) * 4
    hdPer = 26
  end if
  if cls = 4 then
    hdDmg = 32 + (lvl - 1) * 7
    hdPer = 16
  end if
  if cls = 5 then
    hdDmg = 30 + (lvl - 1) * 6
    hdPer = 28
  end if
  if cls = 6 then
    hdDmg = 46 + (lvl - 1) * 9
    hdPer = 36
  end if
  if cls = 7 then
    hdDmg = 36 + (lvl - 1) * 8
    hdPer = 32
  end if
  if cls = 8 then
    hdDmg = 26 + (lvl - 1) * 5
    hdPer = 28
  end if
  if cls = 9 then
    hdDmg = 38 + (lvl - 1) * 8
    hdPer = 20
  end if
end sub

' hsMove = base move speed in ku per tick for a class (level growth ignored; a
' conservative estimate for "can I catch it").
sub heroSpeedFor(cls)
  hsMove = 6
  if cls = 4 then
    hsMove = 7
  end if
  if cls = 0 or cls = 5 then
    hsMove = 5
  end if
end sub

' Tower hit damage from its stable id: lane towers are ids 10-27 in
' outer/inner/gate triples; god guards (28-31) hit like a gate tower.
sub towerDmgFor(tid)
  tdDmg = 30
  if tid >= 10 and tid <= 27 then
    tdTier = (tid - 10) mod 3
    if tdTier = 0 then
      tdDmg = 18
    end if
    if tdTier = 1 then
      tdDmg = 24
    end if
  end if
end sub

sub scanObjects()
  ' Clear the id ring entries used last decision.
  oI = 0
  while oI < efN
    fmSlot((efId(oI) - 1000) mod 448) = -1
    oI = oI + 1
  wend
  efN = 0
  afN = 0
  atN = 0
  etN = 0
  ahN = 0
  ehN = 0
  scSelfX = selfX * 60
  scSelfY = selfY * 60
  scCount = objectCount()
  oI = 0
  while oI < scCount
    scKind = objectKind(oI)
    scTeam = objectTeam(oI)
    if scKind = 3 then
      if objectAlive(oI) = 1 then
        ' Footmen beyond cfgScanRadius are irrelevant to this hero's decisions and
        ' would cost instruction budget in every planner loop; skip them.
        oDx = objectX(oI) * 60 - scSelfX
        oDy = objectY(oI) * 60 - scSelfY
        if oDx * oDx + oDy * oDy > cfgScanRadius * cfgScanRadius then
          scKind = 0
        end if
      else
        scKind = 0
      end if
    end if
    if scKind = 3 then
      if objectAlive(oI) = 1 then
        if scTeam = selfTeam then
          if afN < 64 then
            afX(afN) = objectX(oI) * 60
            afY(afN) = objectY(oI) * 60
            afTgt(afN) = objectTarget(oI)
            afN = afN + 1
          end if
        else
          if efN < 64 then
            efId(efN) = objectId(oI)
            efX(efN) = objectX(oI) * 60
            efY(efN) = objectY(oI) * 60
            efHp(efN) = objectHp(oI)
            fmSlot((efId(efN) - 1000) mod 448) = efN
            efN = efN + 1
          end if
        end if
      end if
    end if
    if scKind = 4 and scTeam = selfTeam then
      if atN < 16 then
        atX(atN) = objectX(oI) * 60
        atY(atN) = objectY(oI) * 60
        atTgt(atN) = objectTarget(oI)
        towerDmgFor(objectId(oI))
        atDmg(atN) = tdDmg
        atN = atN + 1
      end if
    end if
    if scTeam <> selfTeam and (scKind = 4 or scKind = 5) then
      ' Enemy towers and barracks. etX packs id (below 64) into the low bits;
      ' etTgt packs target * 8 + kind * 2 + exposed.
      if objectHp(oI) > 0 then
        if etN < 24 then
          etX(etN) = objectX(oI) * 60 * 64 + objectId(oI)
          etY(etN) = objectY(oI) * 60
          etTgt(etN) = objectTarget(oI) * 8 + scKind * 2 + objectAlive(oI)
          etN = etN + 1
        end if
      end if
    end if
    if scKind = 2 then
      if objectId(oI) <> selfId then
        if objectAlive(oI) = 1 then
          if scTeam = selfTeam then
            if ahN < 5 then
              ahTgt(ahN) = objectTarget(oI)
              ahX(ahN) = objectX(oI) * 60
              ahY(ahN) = objectY(oI) * 60
              heroDmgFor(objectClass(oI), objectLevel(oI))
              ahDmg(ahN) = hdDmg
              ahPer(ahN) = hdPer
              ahN = ahN + 1
            end if
          else
            if ehN < 5 then
              ehPos(ehN) = objectX(oI) * 60 * 8192 + objectY(oI) * 60
              ehMeta(ehN) = objectId(oI) * 65536 + objectTarget(oI)
              ehHp(ehN) = objectHp(oI) * 16 + objectClass(oI)
              ehN = ehN + 1
            end if
          end if
        end if
      end if
    end if
    if scKind = 1 then
      if scTeam = selfTeam then
        scFortX = objectX(oI) * 60
        scFortY = objectY(oI) * 60
        scEFortX = (mapWidth - 1) * 60 - scFortX
        scEFortY = (mapHeight - 1) * 60 - scFortY
      end if
    end if
    oI = oI + 1
  wend
end sub
