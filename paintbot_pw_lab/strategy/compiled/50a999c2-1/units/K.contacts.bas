' unit K.contacts sha256:2b802bedf722a441635a2f8a73eec2f6d178329d40dcbf414cfbe33f5d7cc586 generated, do not edit
' The visible enemy we fight, the visible enemy carrier, and the local fight balance.
DIM k_contacts__old_x(15)
DIM k_contacts__old_y(15)
DIM k_contacts__seen_tick(15)

sub k_contacts__update()
  ' Step 1.
  k_contacts__best = -1
  k_contacts__best_cost = 2147483647
  k_contacts__thief = -1
  k_contacts__foes_near = 0
  k_contacts__friends_near = 1
  k_contacts__foe_sum_x = 0
  k_contacts__foe_sum_y = 0
  k_contacts__foes_seen = 0

  ' Step 2.
  k_contacts__i = 0
  while k_contacts__i < 16
    if k_contacts__i <> selfId and visible(k_contacts__i) then
      k_contacts__dx = playerX(k_contacts__i) - selfX
      k_contacts__dy = playerY(k_contacts__i) - selfY
      k_contacts__d2 = k_contacts__dx * k_contacts__dx + k_contacts__dy * k_contacts__dy
      if k_contacts__i mod 2 <> selfTeam then
        k_contacts__cost = k_contacts__d2 - (3 - playerHp(k_contacts__i)) * k_contacts__hp_weight
        if playerCarrying(k_contacts__i) then
          k_contacts__cost = k_contacts__cost - k_contacts__carrier_bonus
          k_contacts__thief = k_contacts__i
        end if
        if k_contacts__cost < k_contacts__best_cost and k_contacts__d2 <= gunRange() * gunRange() then
          k_contacts__best = k_contacts__i
          k_contacts__best_cost = k_contacts__cost
        end if
        if k_contacts__d2 <= k_contacts__former_range_sq and k_contacts__d2 > gunRange() * gunRange() then
          k_contacts__range_rejected_total = k_contacts__range_rejected_total + 1
        end if
        k_contacts__foes_seen = k_contacts__foes_seen + 1
        k_contacts__foe_sum_x = k_contacts__foe_sum_x + playerX(k_contacts__i)
        k_contacts__foe_sum_y = k_contacts__foe_sum_y + playerY(k_contacts__i)
        if k_contacts__d2 < k_contacts__near_foe_sq then
          k_contacts__foes_near = k_contacts__foes_near + 1
        end if
      else
        if k_contacts__d2 < k_contacts__near_friend_sq then
          k_contacts__friends_near = k_contacts__friends_near + 1
        end if
      end if
    end if
    k_contacts__i = k_contacts__i + 1
  wend

  ' Step 3: best's motion, read before Step 4 overwrites the memory.
  k_contacts__best_vx = 0
  k_contacts__best_vy = 0
  if k_contacts__best >= 0 then
    if k_contacts__seen_tick(k_contacts__best) = worldTick - 1 then
      k_contacts__best_vx = playerX(k_contacts__best) - k_contacts__old_x(k_contacts__best)
      k_contacts__best_vy = playerY(k_contacts__best) - k_contacts__old_y(k_contacts__best)
    end if
  end if

  ' Step 4: memory of every visible seat, ours included, and the enemy centre.
  k_contacts__i = 0
  while k_contacts__i < 16
    if visible(k_contacts__i) then
      k_contacts__old_x(k_contacts__i) = playerX(k_contacts__i)
      k_contacts__old_y(k_contacts__i) = playerY(k_contacts__i)
      k_contacts__seen_tick(k_contacts__i) = worldTick
    end if
    k_contacts__i = k_contacts__i + 1
  wend
  if k_contacts__foes_seen > 0 then
    k_contacts__foe_cx = k_contacts__foe_sum_x \ k_contacts__foes_seen
    k_contacts__foe_cy = k_contacts__foe_sum_y \ k_contacts__foes_seen
  else
    k_contacts__foe_cx = 0
    k_contacts__foe_cy = 0
  end if
end sub
