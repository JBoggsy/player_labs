' unit K.pickups sha256:078751acc541fdc6962b03cf3f128fe1087e86c9f6f8fea949bb1d83c7219521 generated, do not edit
' Supplies seen in the last ten seconds, the nearest one we want now, our own supply takes, and
' supplies that became ready.
DIM k_pickups__mem_x(63)
DIM k_pickups__mem_y(63)
DIM k_pickups__mem_kind(63)
DIM k_pickups__mem_tick(63)
DIM k_pickups__own_ready(63)
' State memory of the previous tick, kept in one array to stay under the 512-global budget:
' 0 x, 1 y, 2 grenade, 3 spray, 4 hp, 5 armor, 6 uniform, 7 mist, 8 sniper, 9 radar
DIM k_pickups__prev(9)
' Scratch cells: 0 n, 1 cur_uniform, 2 cur_mist, 3 cur_sniper, 4 cur_radar, 5 cands, 6 cand,
' 7 i/j, 8 dx, 9 dy, 10 kind, 11 chg, 12 found, 13 carrier, 14 nearest_cost, 15 vis, 16 skip,
' 17 wanted, 18 cost
DIM k_pickups__t(18)

sub k_pickups__init()
  k_pickups__taken_id = -1
  k_pickups__ready_id = -1
  k_pickups__prev(0) = selfX
  k_pickups__prev(1) = selfY
  k_pickups__prev(2) = hasGrenade
  k_pickups__prev(3) = hasSpray
  k_pickups__prev(4) = selfHp
  k_pickups__prev(5) = armorHp
  k_pickups__prev(6) = hasUniform()
  k_pickups__prev(7) = mistingTicks()
  k_pickups__prev(8) = hasSniper()
  k_pickups__prev(9) = radarTicks()
end sub

sub k_pickups__update()
  k_pickups__t(0) = pickupCount()
  k_pickups__t(1) = hasUniform()
  k_pickups__t(2) = mistingTicks()
  k_pickups__t(3) = hasSniper()
  k_pickups__t(4) = radarTicks()

  ' Step 0: own take, judged against the memory before this tick's refresh.
  k_pickups__t(5) = 0
  k_pickups__t(6) = -1
  k_pickups__t(7) = 0
  while k_pickups__t(7) < k_pickups__t(0) and k_pickups__t(7) < 64
    if k_pickups__mem_tick(k_pickups__t(7)) = worldTick then
      if pickupVisible(k_pickups__t(7)) = 0 then
        k_pickups__t(8) = k_pickups__mem_x(k_pickups__t(7)) - k_pickups__prev(0)
        k_pickups__t(9) = k_pickups__mem_y(k_pickups__t(7)) - k_pickups__prev(1)
        if k_pickups__t(8) * k_pickups__t(8) + k_pickups__t(9) * k_pickups__t(9) <= k_pickups__take_radius_sq then
          k_pickups__t(10) = k_pickups__mem_kind(k_pickups__t(7))
          k_pickups__t(11) = 0
          if k_pickups__t(10) = 0 then
            k_pickups__t(11) = hasGrenade = 1 and k_pickups__prev(2) = 0
          end if
          if k_pickups__t(10) = 1 then
            k_pickups__t(11) = hasSpray = 1 and k_pickups__prev(3) = 0
          end if
          if k_pickups__t(10) = 2 then
            k_pickups__t(11) = selfHp >= k_pickups__prev(4) + 2
          end if
          if k_pickups__t(10) = 3 then
            k_pickups__t(11) = armorHp = 3 and k_pickups__prev(5) < 3
          end if
          if k_pickups__t(10) = 4 then
            k_pickups__t(11) = k_pickups__t(1) = 1 and k_pickups__prev(6) = 0
          end if
          if k_pickups__t(10) = 5 then
            k_pickups__t(11) = k_pickups__t(2) > 0 and k_pickups__prev(7) = 0
          end if
          if k_pickups__t(10) = 6 then
            k_pickups__t(11) = k_pickups__t(3) = 1 and k_pickups__prev(8) = 0
          end if
          if k_pickups__t(10) = 7 then
            k_pickups__t(11) = k_pickups__t(4) > k_pickups__prev(9)
          end if
          if k_pickups__t(11) then
            k_pickups__t(5) = k_pickups__t(5) + 1
            k_pickups__t(6) = k_pickups__t(7)
          end if
        end if
      end if
    end if
    k_pickups__t(7) = k_pickups__t(7) + 1
  wend
  if k_pickups__t(5) = 1 then
    k_pickups__taken_id = k_pickups__t(6)
    k_pickups__taken_x = k_pickups__mem_x(k_pickups__t(6))
    k_pickups__taken_y = k_pickups__mem_y(k_pickups__t(6))
    k_pickups__taken_kind = k_pickups__mem_kind(k_pickups__t(6))
    k_pickups__taken_tick = worldTick
    if k_pickups__taken_kind = 0 then
      k_pickups__taken_ready_in = k_pickups__grenade_delay
    else
      k_pickups__taken_ready_in = k_pickups__supply_delay
    end if
    k_pickups__own_ready(k_pickups__t(6)) = worldTick + k_pickups__taken_ready_in
  end if

  ' Step 0b: the lowest station that became ready in view.
  k_pickups__t(12) = 0
  k_pickups__t(7) = 0
  while k_pickups__t(7) < k_pickups__t(0) and k_pickups__t(7) < 64 and k_pickups__t(12) = 0
    if pickupVisible(k_pickups__t(7)) then
      if k_pickups__mem_tick(k_pickups__t(7)) = 0 or k_pickups__own_ready(k_pickups__t(7)) > worldTick or com_pickup_taken__rk_until(k_pickups__t(7)) > worldTick then
        k_pickups__ready_id = k_pickups__t(7)
        k_pickups__ready_kind = pickupKind(k_pickups__t(7))
        k_pickups__ready_x = pickupX(k_pickups__t(7))
        k_pickups__ready_y = pickupY(k_pickups__t(7))
        k_pickups__ready_tick = worldTick
        k_pickups__t(12) = 1
      end if
    end if
    k_pickups__t(7) = k_pickups__t(7) + 1
  wend

  ' Step 0c: state memory.
  k_pickups__prev(0) = selfX
  k_pickups__prev(1) = selfY
  k_pickups__prev(2) = hasGrenade
  k_pickups__prev(3) = hasSpray
  k_pickups__prev(4) = selfHp
  k_pickups__prev(5) = armorHp
  k_pickups__prev(6) = k_pickups__t(1)
  k_pickups__prev(7) = k_pickups__t(2)
  k_pickups__prev(8) = k_pickups__t(3)
  k_pickups__prev(9) = k_pickups__t(4)

  ' Step 1: refresh the memory from what is in view, or from a newer ready report.
  k_pickups__t(7) = 0
  while k_pickups__t(7) < k_pickups__t(0) and k_pickups__t(7) < 64
    if pickupVisible(k_pickups__t(7)) then
      k_pickups__mem_x(k_pickups__t(7)) = pickupX(k_pickups__t(7))
      k_pickups__mem_y(k_pickups__t(7)) = pickupY(k_pickups__t(7))
      k_pickups__mem_kind(k_pickups__t(7)) = pickupKind(k_pickups__t(7))
      k_pickups__mem_tick(k_pickups__t(7)) = worldTick + 1
    else
      if com_pickup_ready__rr_t(k_pickups__t(7)) > k_pickups__mem_tick(k_pickups__t(7)) then
        k_pickups__mem_x(k_pickups__t(7)) = com_pickup_ready__rr_x(k_pickups__t(7))
        k_pickups__mem_y(k_pickups__t(7)) = com_pickup_ready__rr_y(k_pickups__t(7))
        k_pickups__mem_kind(k_pickups__t(7)) = com_pickup_ready__rr_kind(k_pickups__t(7))
        k_pickups__mem_tick(k_pickups__t(7)) = com_pickup_ready__rr_t(k_pickups__t(7))
        k_pickups__own_ready(k_pickups__t(7)) = 0
      end if
    end if
    k_pickups__t(7) = k_pickups__t(7) + 1
  wend

  ' Step 2: a visible enemy carrier.
  k_pickups__t(13) = 0
  k_pickups__t(7) = 0
  while k_pickups__t(7) < 16
    if k_pickups__t(7) <> selfId and visible(k_pickups__t(7)) and k_pickups__t(7) mod 2 <> selfTeam and playerCarrying(k_pickups__t(7)) then
      k_pickups__t(13) = 1
    end if
    k_pickups__t(7) = k_pickups__t(7) + 1
  wend

  ' Step 3: choice.
  k_pickups__nearest = -1
  k_pickups__nearest_x = 0
  k_pickups__nearest_y = 0
  if not carrying and k_pickups__t(13) = 0 then
    k_pickups__t(14) = k_pickups__reach_sq
    k_pickups__t(7) = 0
    while k_pickups__t(7) < k_pickups__t(0) and k_pickups__t(7) < 64
      if k_pickups__mem_tick(k_pickups__t(7)) > 0 and worldTick - k_pickups__mem_tick(k_pickups__t(7)) < k_pickups__memory_ticks then
        k_pickups__t(15) = pickupVisible(k_pickups__t(7))
        k_pickups__t(16) = 0
        if k_pickups__t(15) = 0 then
          if k_pickups__own_ready(k_pickups__t(7)) > worldTick then
            k_pickups__t(16) = 1
          end if
          if com_pickup_taken__rk_until(k_pickups__t(7)) > worldTick and com_pickup_taken__rk_t(k_pickups__t(7)) >= com_pickup_ready__rr_t(k_pickups__t(7)) then
            k_pickups__t(16) = 1
          end if
        end if
        if k_pickups__t(16) = 0 then
          k_pickups__t(10) = k_pickups__mem_kind(k_pickups__t(7))
          k_pickups__t(17) = (k_pickups__t(10) = 0 and not hasGrenade) or (k_pickups__t(10) = 2 and selfHp < 3) or (k_pickups__t(10) = 3 and armorHp < 3 and selfHp = 3)
          if k_pickups__t(17) then
            k_pickups__t(8) = k_pickups__mem_x(k_pickups__t(7)) - selfX
            k_pickups__t(9) = k_pickups__mem_y(k_pickups__t(7)) - selfY
            k_pickups__t(18) = k_pickups__t(8) * k_pickups__t(8) + k_pickups__t(9) * k_pickups__t(9)
            if k_pickups__t(10) = 2 and selfHp = 1 then
              k_pickups__t(18) = k_pickups__t(18) / 4
            end if
            if k_pickups__t(18) < k_pickups__arrive_sq and k_pickups__t(15) = 0 then
              k_pickups__mem_tick(k_pickups__t(7)) = 0
            else
              if k_pickups__t(18) < k_pickups__t(14) then
                k_pickups__nearest = k_pickups__t(7)
                k_pickups__t(14) = k_pickups__t(18)
              end if
            end if
          end if
        end if
      end if
      k_pickups__t(7) = k_pickups__t(7) + 1
    wend
    if k_pickups__nearest >= 0 then
      k_pickups__nearest_x = k_pickups__mem_x(k_pickups__nearest)
      k_pickups__nearest_y = k_pickups__mem_y(k_pickups__nearest)
    end if
  end if
end sub
