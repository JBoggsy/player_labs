' unit COM.focus_call sha256:529883ffcc80e960109b683a91937354c691918bfd270b48d72a7e36786ab40b generated, do not edit
' Call our fight target so that teammates who see it prefer it.
' Memory and scratch cells, kept in one array to stay under the 512-global budget:
' 0 fs_label, 1 fs_t, 2 b, 3 hp, 4 w, 5 h, 6 gx, 7 gy, 8 cell
DIM com_focus_call__t(8)

sub com_focus_call__init()
  com_focus_call__t(0) = -1
  com_focus_call__fc_label = -1
end sub

sub com_focus_call__send()
  com_focus_call__t(2) = k_contacts__best
  if com_focus_call__t(2) >= 0 then
    com_focus_call__t(3) = playerHp(com_focus_call__t(2))
    if (com_focus_call__t(3) < com_focus_call__full_hp or k_contacts__best_engagers >= 2) and (com_focus_call__t(0) <> com_focus_call__t(2) or worldTick - com_focus_call__t(1) >= com_focus_call__focus_refresh) then
      if com_focus_call__t(3) < 0 then
        com_focus_call__t(3) = 0
      end if
      if com_focus_call__t(3) > 15 then
        com_focus_call__t(3) = 15
      end if
      ' Cell of the target.
      com_focus_call__t(4) = mapMaxX() - mapMinX() + 1
      com_focus_call__t(5) = mapMaxY() - mapMinY() + 1
      com_focus_call__t(6) = 0
      com_focus_call__t(7) = 0
      if com_focus_call__t(4) > 0 then
        com_focus_call__t(6) = (playerX(com_focus_call__t(2)) - mapMinX()) * 256 / com_focus_call__t(4)
      end if
      if com_focus_call__t(5) > 0 then
        com_focus_call__t(7) = (playerY(com_focus_call__t(2)) - mapMinY()) * 256 / com_focus_call__t(5)
      end if
      if com_focus_call__t(6) < 0 then
        com_focus_call__t(6) = 0
      end if
      if com_focus_call__t(6) > 255 then
        com_focus_call__t(6) = 255
      end if
      if com_focus_call__t(7) < 0 then
        com_focus_call__t(7) = 0
      end if
      if com_focus_call__t(7) > 255 then
        com_focus_call__t(7) = 255
      end if
      com_focus_call__t(8) = com_focus_call__t(6) + 256 * com_focus_call__t(7)
      cm__send(1, com_focus_call__t(2) + 16 * com_focus_call__t(3), 0, com_focus_call__t(8), sk_motor__quiet)
      if cm__sent = 1 then
        com_focus_call__t(0) = com_focus_call__t(2)
        com_focus_call__t(1) = worldTick
      end if
    end if
  end if
end sub

sub com_focus_call__recv()
  com_focus_call__fc_label = cm__fa mod 16
  if com_focus_call__fc_label < 0 then
    com_focus_call__fc_label = com_focus_call__fc_label + 16
  end if
  ' Point of the cell.
  com_focus_call__t(4) = mapMaxX() - mapMinX() + 1
  com_focus_call__t(5) = mapMaxY() - mapMinY() + 1
  com_focus_call__t(6) = cm__cell mod 256
  com_focus_call__t(7) = cm__cell / 256
  com_focus_call__fc_x = mapMinX() + (com_focus_call__t(6) * com_focus_call__t(4) + com_focus_call__t(4) / 2) / 256
  com_focus_call__fc_y = mapMinY() + (com_focus_call__t(7) * com_focus_call__t(5) + com_focus_call__t(5) / 2) / 256
  com_focus_call__fc_until = worldTick + com_focus_call__focus_ttl
end sub
