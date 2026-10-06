' unit COM.pickup_taken sha256:a17bf6ff53ee210a97d2d377451bb5f6464a1fdb7c54cf157a6fb72518f067b8 generated, do not edit
' Report a supply we took, and keep teammates' reports of taken supplies.
' Memory and scratch cells, kept in one array to stay under the 512-global budget:
' 0 ks_tick, 1 left, 2 w, 3 h, 4 gx, 5 gy, 6 cell, 7 j
DIM com_pickup_taken__t(7)

sub com_pickup_taken__send()
  if k_pickups__taken_id >= 0 and k_pickups__taken_tick + 1 > com_pickup_taken__t(0) and worldTick - k_pickups__taken_tick <= com_pickup_taken__event_window then
    com_pickup_taken__t(1) = k_pickups__taken_ready_in - (worldTick - k_pickups__taken_tick)
    if com_pickup_taken__t(1) < 0 then
      com_pickup_taken__t(1) = 0
    end if
    if com_pickup_taken__t(1) > 720 then
      com_pickup_taken__t(1) = 720
    end if
    ' Cell of the station.
    com_pickup_taken__t(2) = mapMaxX() - mapMinX() + 1
    com_pickup_taken__t(3) = mapMaxY() - mapMinY() + 1
    com_pickup_taken__t(4) = 0
    com_pickup_taken__t(5) = 0
    if com_pickup_taken__t(2) > 0 then
      com_pickup_taken__t(4) = (k_pickups__taken_x - mapMinX()) * 256 / com_pickup_taken__t(2)
    end if
    if com_pickup_taken__t(3) > 0 then
      com_pickup_taken__t(5) = (k_pickups__taken_y - mapMinY()) * 256 / com_pickup_taken__t(3)
    end if
    if com_pickup_taken__t(4) < 0 then
      com_pickup_taken__t(4) = 0
    end if
    if com_pickup_taken__t(4) > 255 then
      com_pickup_taken__t(4) = 255
    end if
    if com_pickup_taken__t(5) < 0 then
      com_pickup_taken__t(5) = 0
    end if
    if com_pickup_taken__t(5) > 255 then
      com_pickup_taken__t(5) = 255
    end if
    com_pickup_taken__t(6) = com_pickup_taken__t(4) + 256 * com_pickup_taken__t(5)
    cm__send(5, k_pickups__taken_id, com_pickup_taken__t(1), com_pickup_taken__t(6), sk_motor__quiet)
    if cm__sent = 1 then
      com_pickup_taken__t(0) = k_pickups__taken_tick + 1
    end if
  end if
end sub

sub com_pickup_taken__recv()
  com_pickup_taken__t(7) = cm__fa
  if com_pickup_taken__t(7) >= 0 and com_pickup_taken__t(7) < 64 then
    com_pickup_taken__rk_until(com_pickup_taken__t(7)) = worldTick - 1 + cm__fb
    com_pickup_taken__rk_t(com_pickup_taken__t(7)) = worldTick
  end if
end sub
