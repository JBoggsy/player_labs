' unit COM.pickup_ready sha256:e3f7157eb590f40fe1191aa7b38837ae92ea2de93a5f21d0e328d33d1f1bf7aa generated, do not edit
' Report a supply that became ready, and keep teammates' ready reports.
' Memory and scratch cells, kept in one array to stay under the 512-global budget:
' 0 rs_tick, 1 w, 2 h, 3 gx, 4 gy, 5 cell, 6 j
DIM com_pickup_ready__t(6)

sub com_pickup_ready__send()
  if k_pickups__ready_id >= 0 then
    if k_pickups__ready_tick + 1 > com_pickup_ready__t(0) and worldTick - k_pickups__ready_tick <= com_pickup_ready__event_window and pickupVisible(k_pickups__ready_id) then
      ' Cell of the station.
      com_pickup_ready__t(1) = mapMaxX() - mapMinX() + 1
      com_pickup_ready__t(2) = mapMaxY() - mapMinY() + 1
      com_pickup_ready__t(3) = 0
      com_pickup_ready__t(4) = 0
      if com_pickup_ready__t(1) > 0 then
        com_pickup_ready__t(3) = (k_pickups__ready_x - mapMinX()) * 256 / com_pickup_ready__t(1)
      end if
      if com_pickup_ready__t(2) > 0 then
        com_pickup_ready__t(4) = (k_pickups__ready_y - mapMinY()) * 256 / com_pickup_ready__t(2)
      end if
      if com_pickup_ready__t(3) < 0 then
        com_pickup_ready__t(3) = 0
      end if
      if com_pickup_ready__t(3) > 255 then
        com_pickup_ready__t(3) = 255
      end if
      if com_pickup_ready__t(4) < 0 then
        com_pickup_ready__t(4) = 0
      end if
      if com_pickup_ready__t(4) > 255 then
        com_pickup_ready__t(4) = 255
      end if
      com_pickup_ready__t(5) = com_pickup_ready__t(3) + 256 * com_pickup_ready__t(4)
      cm__send(6, k_pickups__ready_id + 256 * k_pickups__ready_kind, 0, com_pickup_ready__t(5), sk_motor__quiet)
      if cm__sent = 1 then
        com_pickup_ready__t(0) = k_pickups__ready_tick + 1
      end if
    end if
  end if
end sub

sub com_pickup_ready__recv()
  com_pickup_ready__t(6) = cm__fa mod 256
  if com_pickup_ready__t(6) >= 0 and com_pickup_ready__t(6) < 64 then
    com_pickup_ready__rr_kind(com_pickup_ready__t(6)) = cm__fa / 256
    ' Point of the cell.
    com_pickup_ready__t(1) = mapMaxX() - mapMinX() + 1
    com_pickup_ready__t(2) = mapMaxY() - mapMinY() + 1
    com_pickup_ready__t(3) = cm__cell mod 256
    com_pickup_ready__t(4) = cm__cell / 256
    com_pickup_ready__rr_x(com_pickup_ready__t(6)) = mapMinX() + (com_pickup_ready__t(3) * com_pickup_ready__t(1) + com_pickup_ready__t(1) / 2) / 256
    com_pickup_ready__rr_y(com_pickup_ready__t(6)) = mapMinY() + (com_pickup_ready__t(4) * com_pickup_ready__t(2) + com_pickup_ready__t(2) / 2) / 256
    com_pickup_ready__rr_t(com_pickup_ready__t(6)) = worldTick
  end if
end sub
