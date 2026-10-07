' unit COM.enemy_sighting sha256:4329fbd900ebaef2085dac732bf4d8992177cd6da171a694e7b06ee6e3202af6 generated, do not edit
' Report a visible enemy to teammates, and keep heard enemy tracks.
DIM com_enemy_sighting__es_t(15)
DIM com_enemy_sighting__es_x(15)
DIM com_enemy_sighting__es_y(15)
' Scratch cells, kept in one array to stay under the 512-global budget:
' 0 mates, 1 s, 2 pick, 3 pick_cost, 4 i, 5 bx, 6 by, 7 dx, 8 dy, 9 cost, 10 d2, 11 hp, 12 w,
' 13 h, 14 gx, 15 gy, 16 cell, 17 l, 18 seen
DIM com_enemy_sighting__t(18)

sub com_enemy_sighting__send()
  ' Is any teammate heard recently enough to place it?
  com_enemy_sighting__t(0) = 0
  com_enemy_sighting__t(1) = 0
  while com_enemy_sighting__t(1) < 16
    if com_enemy_sighting__t(1) <> selfId and com_enemy_sighting__t(1) mod 2 = selfTeam then
      if cm__heard_t(com_enemy_sighting__t(1)) > 0 then
        if worldTick + 1 - cm__heard_t(com_enemy_sighting__t(1)) <= com_enemy_sighting__heard_ttl then
          com_enemy_sighting__t(0) = 1
        end if
      end if
    end if
    com_enemy_sighting__t(1) = com_enemy_sighting__t(1) + 1
  wend
  com_enemy_sighting__t(2) = -1
  com_enemy_sighting__t(3) = 2147483647
  com_enemy_sighting__t(4) = 0
  while com_enemy_sighting__t(4) < 16
    if com_enemy_sighting__t(4) <> selfId and visible(com_enemy_sighting__t(4)) and k_contacts__hostile(com_enemy_sighting__t(4)) = 1 then
      com_enemy_sighting__t(5) = playerX(com_enemy_sighting__t(4))
      com_enemy_sighting__t(6) = playerY(com_enemy_sighting__t(4))
      com_enemy_sighting__t(7) = com_enemy_sighting__t(5) - com_enemy_sighting__es_x(com_enemy_sighting__t(4))
      com_enemy_sighting__t(8) = com_enemy_sighting__t(6) - com_enemy_sighting__es_y(com_enemy_sighting__t(4))
      if com_enemy_sighting__es_t(com_enemy_sighting__t(4)) = 0 or worldTick + 1 - com_enemy_sighting__es_t(com_enemy_sighting__t(4)) >= com_enemy_sighting__e_refresh or com_enemy_sighting__t(7) * com_enemy_sighting__t(7) + com_enemy_sighting__t(8) * com_enemy_sighting__t(8) > com_enemy_sighting__e_move * com_enemy_sighting__e_move then
        if com_enemy_sighting__t(0) = 1 then
          ' Distance to the nearest recently heard teammate.
          com_enemy_sighting__t(9) = 2147483647
          com_enemy_sighting__t(1) = 0
          while com_enemy_sighting__t(1) < 16
            if com_enemy_sighting__t(1) <> selfId and com_enemy_sighting__t(1) mod 2 = selfTeam then
              if cm__heard_t(com_enemy_sighting__t(1)) > 0 then
                if worldTick + 1 - cm__heard_t(com_enemy_sighting__t(1)) <= com_enemy_sighting__heard_ttl then
                  com_enemy_sighting__t(7) = com_enemy_sighting__t(5) - cm__heard_x(com_enemy_sighting__t(1))
                  com_enemy_sighting__t(8) = com_enemy_sighting__t(6) - cm__heard_y(com_enemy_sighting__t(1))
                  com_enemy_sighting__t(10) = com_enemy_sighting__t(7) * com_enemy_sighting__t(7) + com_enemy_sighting__t(8) * com_enemy_sighting__t(8)
                  if com_enemy_sighting__t(10) < com_enemy_sighting__t(9) then
                    com_enemy_sighting__t(9) = com_enemy_sighting__t(10)
                  end if
                end if
              end if
            end if
            com_enemy_sighting__t(1) = com_enemy_sighting__t(1) + 1
          wend
        else
          com_enemy_sighting__t(7) = com_enemy_sighting__t(5) - selfX
          com_enemy_sighting__t(8) = com_enemy_sighting__t(6) - selfY
          com_enemy_sighting__t(9) = com_enemy_sighting__t(7) * com_enemy_sighting__t(7) + com_enemy_sighting__t(8) * com_enemy_sighting__t(8)
        end if
        if com_enemy_sighting__t(2) < 0 or com_enemy_sighting__t(9) < com_enemy_sighting__t(3) then
          com_enemy_sighting__t(2) = com_enemy_sighting__t(4)
          com_enemy_sighting__t(3) = com_enemy_sighting__t(9)
        end if
      end if
    end if
    com_enemy_sighting__t(4) = com_enemy_sighting__t(4) + 1
  wend
  if com_enemy_sighting__t(2) >= 0 then
    com_enemy_sighting__t(5) = playerX(com_enemy_sighting__t(2))
    com_enemy_sighting__t(6) = playerY(com_enemy_sighting__t(2))
    com_enemy_sighting__t(11) = playerHp(com_enemy_sighting__t(2))
    if com_enemy_sighting__t(11) < 0 then
      com_enemy_sighting__t(11) = 0
    end if
    if com_enemy_sighting__t(11) > 15 then
      com_enemy_sighting__t(11) = 15
    end if
    ' Cell of the body.
    com_enemy_sighting__t(12) = mapMaxX() - mapMinX() + 1
    com_enemy_sighting__t(13) = mapMaxY() - mapMinY() + 1
    com_enemy_sighting__t(14) = 0
    com_enemy_sighting__t(15) = 0
    if com_enemy_sighting__t(12) > 0 then
      com_enemy_sighting__t(14) = (com_enemy_sighting__t(5) - mapMinX()) * 256 / com_enemy_sighting__t(12)
    end if
    if com_enemy_sighting__t(13) > 0 then
      com_enemy_sighting__t(15) = (com_enemy_sighting__t(6) - mapMinY()) * 256 / com_enemy_sighting__t(13)
    end if
    if com_enemy_sighting__t(14) < 0 then
      com_enemy_sighting__t(14) = 0
    end if
    if com_enemy_sighting__t(14) > 255 then
      com_enemy_sighting__t(14) = 255
    end if
    if com_enemy_sighting__t(15) < 0 then
      com_enemy_sighting__t(15) = 0
    end if
    if com_enemy_sighting__t(15) > 255 then
      com_enemy_sighting__t(15) = 255
    end if
    com_enemy_sighting__t(16) = com_enemy_sighting__t(14) + 256 * com_enemy_sighting__t(15)
    cm__send(0, com_enemy_sighting__t(2) + 16 * (com_enemy_sighting__t(11) + 16 * 8), 0, com_enemy_sighting__t(16), sk_motor__quiet)
    if cm__sent = 1 then
      com_enemy_sighting__es_t(com_enemy_sighting__t(2)) = worldTick + 1
      com_enemy_sighting__es_x(com_enemy_sighting__t(2)) = com_enemy_sighting__t(5)
      com_enemy_sighting__es_y(com_enemy_sighting__t(2)) = com_enemy_sighting__t(6)
    end if
  end if
end sub

sub com_enemy_sighting__recv()
  com_enemy_sighting__t(17) = cm__fa mod 16
  if com_enemy_sighting__t(17) < 0 then
    com_enemy_sighting__t(17) = com_enemy_sighting__t(17) + 16
  end if
  com_enemy_sighting__t(18) = worldTick - 1 - cm__fb
  ' An older or equal sighting never refreshes a track.
  if com_enemy_sighting__ht_until(com_enemy_sighting__t(17)) = 0 or com_enemy_sighting__t(18) > com_enemy_sighting__ht_t(com_enemy_sighting__t(17)) then
    com_enemy_sighting__t(12) = mapMaxX() - mapMinX() + 1
    com_enemy_sighting__t(13) = mapMaxY() - mapMinY() + 1
    com_enemy_sighting__t(14) = cm__cell mod 256
    com_enemy_sighting__t(15) = cm__cell / 256
    com_enemy_sighting__ht_x(com_enemy_sighting__t(17)) = mapMinX() + (com_enemy_sighting__t(14) * com_enemy_sighting__t(12) + com_enemy_sighting__t(12) / 2) / 256
    com_enemy_sighting__ht_y(com_enemy_sighting__t(17)) = mapMinY() + (com_enemy_sighting__t(15) * com_enemy_sighting__t(13) + com_enemy_sighting__t(13) / 2) / 256
    com_enemy_sighting__ht_t(com_enemy_sighting__t(17)) = com_enemy_sighting__t(18)
    com_enemy_sighting__ht_until(com_enemy_sighting__t(17)) = com_enemy_sighting__t(18) + com_enemy_sighting__heard_ttl
  end if
end sub
