' unit COM.disguise_alert sha256:4a819094b97327ff43f33b50cce0ab9e133d3a990d4b9105f3d65e862039d617 generated, do not edit
' Report uncertain disguise evidence and keep distinct witness reports.
DIM com_disguise_alert__xs_t(15)
' Scratch cells, kept in one array to stay under the 512-global budget:
' 0 l, 1 ex, 2 ey, 3 age, 4 k, 5 w, 6 h, 7 gx, 8 gy, 9 cell, 10 amb, 11 until, 12 px, 13 py,
' 14 dx, 15 dy
DIM com_disguise_alert__t(15)

sub com_disguise_alert__send()
  com_disguise_alert__t(0) = -1
  if k_contacts__xe_label >= 0 and k_contacts__xe_label < 16 then
    ' Strong evidence: our own conflicting position.
    com_disguise_alert__t(0) = k_contacts__xe_label
    com_disguise_alert__t(1) = k_contacts__xe_x
    com_disguise_alert__t(2) = k_contacts__xe_y
    com_disguise_alert__t(3) = worldTick + 1 - cm__heard_t(com_disguise_alert__t(0))
  else
    ' Weak evidence: the lowest label whose speech failed the message check.
    com_disguise_alert__t(4) = 0
    while com_disguise_alert__t(4) < 16
      if com_disguise_alert__t(0) < 0 and com_disguise_alert__t(4) <> selfId and com_disguise_alert__t(4) <> (selfId + 2) mod 16 then
        if cm__suspect_t(com_disguise_alert__t(4)) > 0 then
          if worldTick + 1 - cm__suspect_t(com_disguise_alert__t(4)) <= com_disguise_alert__x_window then
            com_disguise_alert__t(0) = com_disguise_alert__t(4)
            com_disguise_alert__t(1) = cm__suspect_x(com_disguise_alert__t(4))
            com_disguise_alert__t(2) = cm__suspect_y(com_disguise_alert__t(4))
            com_disguise_alert__t(3) = worldTick + 1 - cm__suspect_t(com_disguise_alert__t(4))
          end if
        end if
      end if
      com_disguise_alert__t(4) = com_disguise_alert__t(4) + 1
    wend
  end if
  if com_disguise_alert__t(0) >= 0 then
    if com_disguise_alert__xs_t(com_disguise_alert__t(0)) = 0 or worldTick + 1 - com_disguise_alert__xs_t(com_disguise_alert__t(0)) >= com_disguise_alert__x_refresh then
      if com_disguise_alert__t(3) < 0 then
        com_disguise_alert__t(3) = 0
      end if
      if com_disguise_alert__t(3) > 255 then
        com_disguise_alert__t(3) = 255
      end if
      ' Cell of the point.
      com_disguise_alert__t(5) = mapMaxX() - mapMinX() + 1
      com_disguise_alert__t(6) = mapMaxY() - mapMinY() + 1
      com_disguise_alert__t(7) = 0
      com_disguise_alert__t(8) = 0
      if com_disguise_alert__t(5) > 0 then
        com_disguise_alert__t(7) = (com_disguise_alert__t(1) - mapMinX()) * 256 / com_disguise_alert__t(5)
      end if
      if com_disguise_alert__t(6) > 0 then
        com_disguise_alert__t(8) = (com_disguise_alert__t(2) - mapMinY()) * 256 / com_disguise_alert__t(6)
      end if
      if com_disguise_alert__t(7) < 0 then
        com_disguise_alert__t(7) = 0
      end if
      if com_disguise_alert__t(7) > 255 then
        com_disguise_alert__t(7) = 255
      end if
      if com_disguise_alert__t(8) < 0 then
        com_disguise_alert__t(8) = 0
      end if
      if com_disguise_alert__t(8) > 255 then
        com_disguise_alert__t(8) = 255
      end if
      com_disguise_alert__t(9) = com_disguise_alert__t(7) + 256 * com_disguise_alert__t(8)
      cm__send(7, com_disguise_alert__t(0), com_disguise_alert__t(3), com_disguise_alert__t(9), sk_motor__quiet)
      if cm__sent = 1 then
        com_disguise_alert__xs_t(com_disguise_alert__t(0)) = worldTick + 1
      end if
    end if
  end if
end sub

sub com_disguise_alert__recv()
  com_disguise_alert__t(0) = cm__fa
  com_disguise_alert__t(10) = 0
  com_disguise_alert__t(11) = worldTick - 1 - cm__fb + com_disguise_alert__disguise_ttl
  if com_disguise_alert__t(11) <= worldTick then
    exit sub
  end if
  if com_disguise_alert__t(0) < 0 or com_disguise_alert__t(0) > 15 then
    exit sub
  end if
  if com_disguise_alert__t(0) = selfId then
    com_disguise_alert__t(0) = (com_disguise_alert__t(0) + 2) mod 16
    com_disguise_alert__t(10) = 1
  end if
  ' Point of the cell.
  com_disguise_alert__t(5) = mapMaxX() - mapMinX() + 1
  com_disguise_alert__t(6) = mapMaxY() - mapMinY() + 1
  com_disguise_alert__t(7) = cm__cell mod 256
  com_disguise_alert__t(8) = cm__cell / 256
  com_disguise_alert__t(12) = mapMinX() + (com_disguise_alert__t(7) * com_disguise_alert__t(5) + com_disguise_alert__t(5) / 2) / 256
  com_disguise_alert__t(13) = mapMinY() + (com_disguise_alert__t(8) * com_disguise_alert__t(6) + com_disguise_alert__t(6) / 2) / 256
  ' Both witnesses expired: the label is no longer ambiguous.
  if com_disguise_alert__xa_t1(com_disguise_alert__t(0)) <= worldTick and com_disguise_alert__xa_t2(com_disguise_alert__t(0)) <= worldTick then
    com_disguise_alert__xa_amb(com_disguise_alert__t(0)) = 0
  end if
  if com_disguise_alert__t(10) = 1 then
    com_disguise_alert__xa_amb(com_disguise_alert__t(0)) = 1
  end if
  if com_disguise_alert__xa_t1(com_disguise_alert__t(0)) <= worldTick or (com_disguise_alert__xa_s1(com_disguise_alert__t(0)) = cm__speaker and com_disguise_alert__t(11) > com_disguise_alert__xa_t1(com_disguise_alert__t(0))) then
    com_disguise_alert__xa_s1(com_disguise_alert__t(0)) = cm__speaker
    com_disguise_alert__xa_x1(com_disguise_alert__t(0)) = com_disguise_alert__t(12)
    com_disguise_alert__xa_y1(com_disguise_alert__t(0)) = com_disguise_alert__t(13)
    com_disguise_alert__xa_t1(com_disguise_alert__t(0)) = com_disguise_alert__t(11)
    ' One sender never fills both witnesses.
    if com_disguise_alert__xa_s2(com_disguise_alert__t(0)) = cm__speaker then
      com_disguise_alert__xa_t2(com_disguise_alert__t(0)) = 0
    end if
  else
    if com_disguise_alert__xa_s1(com_disguise_alert__t(0)) <> cm__speaker then
      com_disguise_alert__t(14) = com_disguise_alert__t(12) - com_disguise_alert__xa_x1(com_disguise_alert__t(0))
      com_disguise_alert__t(15) = com_disguise_alert__t(13) - com_disguise_alert__xa_y1(com_disguise_alert__t(0))
      if com_disguise_alert__t(14) * com_disguise_alert__t(14) + com_disguise_alert__t(15) * com_disguise_alert__t(15) <= com_disguise_alert__x_radius * com_disguise_alert__x_radius then
        if com_disguise_alert__xa_t2(com_disguise_alert__t(0)) <= worldTick or (com_disguise_alert__xa_s2(com_disguise_alert__t(0)) = cm__speaker and com_disguise_alert__t(11) > com_disguise_alert__xa_t2(com_disguise_alert__t(0))) then
          com_disguise_alert__xa_s2(com_disguise_alert__t(0)) = cm__speaker
          com_disguise_alert__xa_x2(com_disguise_alert__t(0)) = com_disguise_alert__t(12)
          com_disguise_alert__xa_y2(com_disguise_alert__t(0)) = com_disguise_alert__t(13)
          com_disguise_alert__xa_t2(com_disguise_alert__t(0)) = com_disguise_alert__t(11)
        end if
      end if
    end if
  end if
end sub
