' unit COM.grenade_warning sha256:2ac13417e4f4d9e23b9c98e7b45d9237071e9504d64275774060847acdc10e96 generated, do not edit
' Warn teammates where our grenade will land, and keep their warnings.
' Memory and scratch cells, kept in one array to stay under the 512-global budget:
' 0 gs_x, 1 gs_y, 2 gs_until, 3 dx, 4 dy, 5 w, 6 h, 7 gx, 8 gy, 9 cell, 10 px, 11 py, 12 k, 13 j
DIM com_grenade_warning__t(13)

sub com_grenade_warning__send()
  if sk_motor__charging = 1 then
    com_grenade_warning__t(3) = sk_motor__charge_x - com_grenade_warning__t(0)
    com_grenade_warning__t(4) = sk_motor__charge_y - com_grenade_warning__t(1)
    if sk_motor__charge_started = 1 or com_grenade_warning__t(2) <= worldTick or com_grenade_warning__t(3) * com_grenade_warning__t(3) + com_grenade_warning__t(4) * com_grenade_warning__t(4) > com_grenade_warning__g_move * com_grenade_warning__g_move then
      ' Cell of the landing point.
      com_grenade_warning__t(5) = mapMaxX() - mapMinX() + 1
      com_grenade_warning__t(6) = mapMaxY() - mapMinY() + 1
      com_grenade_warning__t(7) = 0
      com_grenade_warning__t(8) = 0
      if com_grenade_warning__t(5) > 0 then
        com_grenade_warning__t(7) = (sk_motor__charge_x - mapMinX()) * 256 / com_grenade_warning__t(5)
      end if
      if com_grenade_warning__t(6) > 0 then
        com_grenade_warning__t(8) = (sk_motor__charge_y - mapMinY()) * 256 / com_grenade_warning__t(6)
      end if
      if com_grenade_warning__t(7) < 0 then
        com_grenade_warning__t(7) = 0
      end if
      if com_grenade_warning__t(7) > 255 then
        com_grenade_warning__t(7) = 255
      end if
      if com_grenade_warning__t(8) < 0 then
        com_grenade_warning__t(8) = 0
      end if
      if com_grenade_warning__t(8) > 255 then
        com_grenade_warning__t(8) = 255
      end if
      com_grenade_warning__t(9) = com_grenade_warning__t(7) + 256 * com_grenade_warning__t(8)
      cm__send(2, sk_motor__release_in, 0, com_grenade_warning__t(9), sk_motor__quiet)
      if cm__sent = 1 then
        com_grenade_warning__t(0) = sk_motor__charge_x
        com_grenade_warning__t(1) = sk_motor__charge_y
        com_grenade_warning__t(2) = worldTick + sk_motor__release_in + 24
      end if
    end if
  end if
end sub

sub com_grenade_warning__recv()
  ' Point of the cell.
  com_grenade_warning__t(5) = mapMaxX() - mapMinX() + 1
  com_grenade_warning__t(6) = mapMaxY() - mapMinY() + 1
  com_grenade_warning__t(7) = cm__cell mod 256
  com_grenade_warning__t(8) = cm__cell / 256
  com_grenade_warning__t(10) = mapMinX() + (com_grenade_warning__t(7) * com_grenade_warning__t(5) + com_grenade_warning__t(5) / 2) / 256
  com_grenade_warning__t(11) = mapMinY() + (com_grenade_warning__t(8) * com_grenade_warning__t(6) + com_grenade_warning__t(6) / 2) / 256
  ' The zone slot that expires first.
  com_grenade_warning__t(12) = 0
  com_grenade_warning__t(13) = 1
  while com_grenade_warning__t(13) < 4
    if com_grenade_warning__gz_until(com_grenade_warning__t(13)) < com_grenade_warning__gz_until(com_grenade_warning__t(12)) then
      com_grenade_warning__t(12) = com_grenade_warning__t(13)
    end if
    com_grenade_warning__t(13) = com_grenade_warning__t(13) + 1
  wend
  com_grenade_warning__gz_x(com_grenade_warning__t(12)) = com_grenade_warning__t(10)
  com_grenade_warning__gz_y(com_grenade_warning__t(12)) = com_grenade_warning__t(11)
  com_grenade_warning__gz_until(com_grenade_warning__t(12)) = worldTick - 1 + cm__fa + 24
end sub
