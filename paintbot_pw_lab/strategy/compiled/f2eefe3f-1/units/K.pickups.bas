' unit K.pickups sha256:099187de4f06cc46c21c4b628635a1393751681d37545361cf765c0d1ebd4856 generated, do not edit
' Supplies seen in the last ten seconds, using observed maximum HP.
DIM k_pickups__mem_x(63)
DIM k_pickups__mem_y(63)
DIM k_pickups__mem_kind(63)
DIM k_pickups__mem_tick(63)

sub k_pickups__update()
  if selfHp > k_pickups__hp_cap then
    k_pickups__hp_cap = selfHp
  end if
  if selfHp > 0 and selfHp * 3 <= k_pickups__hp_cap then
    k_pickups__critical = 1
  else
    k_pickups__critical = 0
  end if

  ' Step 1: refresh the memory from what is in view.
  k_pickups__i = 0
  while k_pickups__i < pickupCount() and k_pickups__i < 64
    if pickupVisible(k_pickups__i) then
      k_pickups__mem_x(k_pickups__i) = pickupX(k_pickups__i)
      k_pickups__mem_y(k_pickups__i) = pickupY(k_pickups__i)
      k_pickups__mem_kind(k_pickups__i) = pickupKind(k_pickups__i)
      k_pickups__mem_tick(k_pickups__i) = worldTick + 1
    end if
    k_pickups__i = k_pickups__i + 1
  wend

  ' Step 2: a visible enemy carrier.
  k_pickups__carrier = 0
  k_pickups__i = 0
  while k_pickups__i < 16
    if k_pickups__i <> selfId and visible(k_pickups__i) and k_pickups__i mod 2 <> selfTeam and playerCarrying(k_pickups__i) then
      k_pickups__carrier = 1
    end if
    k_pickups__i = k_pickups__i + 1
  wend

  ' Step 3: choice.
  k_pickups__nearest = -1
  k_pickups__nearest_x = 0
  k_pickups__nearest_y = 0
  if carrying = 0 and k_pickups__carrier = 0 then
    k_pickups__nearest_cost = k_pickups__reach_sq
    k_pickups__j = 0
    while k_pickups__j < pickupCount() and k_pickups__j < 64
      if k_pickups__mem_tick(k_pickups__j) > 0 and worldTick - k_pickups__mem_tick(k_pickups__j) < k_pickups__memory_ticks then
        k_pickups__kind = k_pickups__mem_kind(k_pickups__j)
        if (k_pickups__kind = 0 and hasGrenade = 0) or (k_pickups__kind = 2 and selfHp < k_pickups__hp_cap) or (k_pickups__kind = 3 and armorHp < 3 and selfHp = k_pickups__hp_cap) then
          k_pickups__wanted = 1
        else
          k_pickups__wanted = 0
        end if
        if (k_pickups__kind = 0 and hasGrenade = 0) or (k_pickups__kind = 2 and selfHp < 3) or (k_pickups__kind = 3 and armorHp < 3 and selfHp = 3) then
          k_pickups__old_wanted = 1
        else
          k_pickups__old_wanted = 0
        end if
        if k_pickups__wanted <> k_pickups__old_wanted then
          k_pickups__hp_changed_total = k_pickups__hp_changed_total + 1
        end if
        if k_pickups__wanted then
          k_pickups__dx = k_pickups__mem_x(k_pickups__j) - selfX
          k_pickups__dy = k_pickups__mem_y(k_pickups__j) - selfY
          k_pickups__cost = k_pickups__dx * k_pickups__dx + k_pickups__dy * k_pickups__dy
          if k_pickups__kind = 2 and k_pickups__critical = 1 then
            k_pickups__cost = k_pickups__cost \ 4
          end if
          if k_pickups__cost < k_pickups__arrive_sq and pickupVisible(k_pickups__j) = 0 then
            k_pickups__mem_tick(k_pickups__j) = 0
          else
            if k_pickups__cost < k_pickups__nearest_cost then
              k_pickups__nearest = k_pickups__j
              k_pickups__nearest_cost = k_pickups__cost
            end if
          end if
        end if
      end if
      k_pickups__j = k_pickups__j + 1
    wend
    if k_pickups__nearest >= 0 then
      k_pickups__nearest_x = k_pickups__mem_x(k_pickups__nearest)
      k_pickups__nearest_y = k_pickups__mem_y(k_pickups__nearest)
    end if
  end if
end sub
