' Module: scan (prefix sc). One pass over the object list into typed arrays.
' Positions are stored in ku (tile * 60). Enemy objects are only those visible
' to my team this decision; allied objects are always present. Footmen are kept
' only within cfgScanRadius of me (budget).
'
' Outputs (valid for this decision):
'   efN, efId(i), efX(i), efY(i), efHp(i)     living enemy footmen
'   afN, afX(i), afY(i), afTgt(i)              living allied footmen and their targets
'   atN, atX(i), atY(i), atTgt(i), atDmg(i)    allied towers (any), their target and hit damage
'   etN, etX(i), etY(i), etTgt(i)              visible living enemy towers and their targets
'   ahN, ahTgt(i), ahDmg(i), ahPer(i)          living allied heroes (not me): target, damage, swing ticks
'   ehN, ehX(i), ehY(i), ehHp(i)               visible living enemy heroes
'   scFortX, scFortY                           own god (fort) position
'   scEFortX, scEFortY                         enemy god position (mirror of own)
'   fmSlot(ring)                               enemy footman id ring -> index into ef arrays, or -1
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
dim etX(15)
dim etY(15)
dim etTgt(15)
dim ahTgt(4)
dim ahDmg(4)
dim ahPer(4)
dim ehX(4)
dim ehY(4)
dim ehHp(4)
dim fmSlot(447)

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
  scI = 0
  while scI < efN
    fmSlot((efId(scI) - 1000) mod 448) = -1
    scI = scI + 1
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
  scI = 0
  while scI < scCount
    scKind = objectKind(scI)
    scTeam = objectTeam(scI)
    if scKind = 3 then
      if objectAlive(scI) = 1 then
        ' Footmen beyond cfgScanRadius are irrelevant to this hero's decisions and
        ' would cost instruction budget in every planner loop; skip them.
        scDx = objectX(scI) * 60 - scSelfX
        scDy = objectY(scI) * 60 - scSelfY
        if scDx * scDx + scDy * scDy > cfgScanRadius * cfgScanRadius then
          scKind = 0
        end if
      else
        scKind = 0
      end if
    end if
    if scKind = 3 then
      if objectAlive(scI) = 1 then
        if scTeam = selfTeam then
          if afN < 64 then
            afX(afN) = objectX(scI) * 60
            afY(afN) = objectY(scI) * 60
            afTgt(afN) = objectTarget(scI)
            afN = afN + 1
          end if
        else
          if efN < 64 then
            efId(efN) = objectId(scI)
            efX(efN) = objectX(scI) * 60
            efY(efN) = objectY(scI) * 60
            efHp(efN) = objectHp(scI)
            fmSlot((efId(efN) - 1000) mod 448) = efN
            efN = efN + 1
          end if
        end if
      end if
    end if
    if scKind = 4 then
      if scTeam = selfTeam then
        if atN < 16 then
          atX(atN) = objectX(scI) * 60
          atY(atN) = objectY(scI) * 60
          atTgt(atN) = objectTarget(scI)
          towerDmgFor(objectId(scI))
          atDmg(atN) = tdDmg
          atN = atN + 1
        end if
      else
        if objectHp(scI) > 0 then
          if etN < 16 then
            etX(etN) = objectX(scI) * 60
            etY(etN) = objectY(scI) * 60
            etTgt(etN) = objectTarget(scI)
            etN = etN + 1
          end if
        end if
      end if
    end if
    if scKind = 2 then
      if objectId(scI) <> selfId then
        if objectAlive(scI) = 1 then
          if scTeam = selfTeam then
            if ahN < 5 then
              ahTgt(ahN) = objectTarget(scI)
              heroDmgFor(objectClass(scI), objectLevel(scI))
              ahDmg(ahN) = hdDmg
              ahPer(ahN) = hdPer
              ahN = ahN + 1
            end if
          else
            if ehN < 5 then
              ehX(ehN) = objectX(scI) * 60
              ehY(ehN) = objectY(scI) * 60
              ehHp(ehN) = objectHp(scI)
              ehN = ehN + 1
            end if
          end if
        end if
      end if
    end if
    if scKind = 1 then
      if scTeam = selfTeam then
        scFortX = objectX(scI) * 60
        scFortY = objectY(scI) * 60
        scEFortX = (mapWidth - 1) * 60 - scFortX
        scEFortY = (mapHeight - 1) * 60 - scFortY
      end if
    end if
    scI = scI + 1
  wend
end sub
