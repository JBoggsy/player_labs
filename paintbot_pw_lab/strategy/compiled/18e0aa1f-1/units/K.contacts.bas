' unit K.contacts sha256:dd0503229b475bdddad47f0c59c3efd21b7f5b45424c92afc027ac1abe60ee13 generated, do not edit
' The visible enemy we fight, friend and hostile classification of visible bodies, the visible
' enemy carrier, the local fight balance, and the freshest heard enemy.
DIM k_contacts__old_x(15)
DIM k_contacts__old_y(15)
DIM k_contacts__seen_tick(15)
DIM k_contacts__kf_x(15)
DIM k_contacts__kf_y(15)
DIM k_contacts__kf_src(15)
' Scratch cells, kept in one array to stay under the 512-global budget:
' 0 i/j, 1 px, 2 py, 3 done, 4 ex, 5 ey, 6 own_ev, 7 witness, 8 fx, 9 fy, 10 focus_best,
' 11 focus_cost, 12 foe_sum_x, 13 foe_sum_y, 14 dx, 15 dy, 16 d2, 17 cost, 18 bx, 19 by,
' 20 heard_age, 21 heard_best_t
DIM k_contacts__t(21)

sub k_contacts__update()
  ' Step 0: classification.
  k_contacts__xe_label = -1
  k_contacts__xe_x = 0
  k_contacts__xe_y = 0
  k_contacts__t(0) = 0
  while k_contacts__t(0) < 16
    k_contacts__friend(k_contacts__t(0)) = 0
    k_contacts__hostile(k_contacts__t(0)) = 0
    k_contacts__t(0) = k_contacts__t(0) + 1
  wend
  k_contacts__friend(selfId) = 1
  k_contacts__t(0) = 0
  while k_contacts__t(0) < 16
    if k_contacts__t(0) <> selfId and visible(k_contacts__t(0)) then
      k_contacts__t(1) = playerX(k_contacts__t(0))
      k_contacts__t(2) = playerY(k_contacts__t(0))
      k_contacts__t(3) = 0
      ' Step 0a: a friendly disguise record wins over everything else.
      if com_disguise_friend__df_until(k_contacts__t(0)) > worldTick then
        if com_disguise_friend__df_until(k_contacts__t(0)) <> k_contacts__kf_src(k_contacts__t(0)) then
          k_contacts__kf_x(k_contacts__t(0)) = com_disguise_friend__df_x(k_contacts__t(0))
          k_contacts__kf_y(k_contacts__t(0)) = com_disguise_friend__df_y(k_contacts__t(0))
          k_contacts__kf_src(k_contacts__t(0)) = com_disguise_friend__df_until(k_contacts__t(0))
        end if
        k_contacts__t(4) = k_contacts__t(1) - k_contacts__kf_x(k_contacts__t(0))
        k_contacts__t(5) = k_contacts__t(2) - k_contacts__kf_y(k_contacts__t(0))
        if k_contacts__t(4) * k_contacts__t(4) + k_contacts__t(5) * k_contacts__t(5) <= com_disguise_friend__friend_radius * com_disguise_friend__friend_radius then
          k_contacts__kf_x(k_contacts__t(0)) = k_contacts__t(1)
          k_contacts__kf_y(k_contacts__t(0)) = k_contacts__t(2)
          k_contacts__friend(k_contacts__t(0)) = 1
          k_contacts__t(3) = 1
        end if
      end if
      if k_contacts__t(3) = 0 then
        if k_contacts__t(0) mod 2 <> selfTeam then
          ' Step 0b: enemy parity.
          k_contacts__hostile(k_contacts__t(0)) = 1
        else
          ' Step 0c: teammate parity, unless corroborated as a fake.
          k_contacts__friend(k_contacts__t(0)) = 1
          k_contacts__t(6) = 0
          if cm__heard_t(k_contacts__t(0)) > 0 then
            if worldTick + 1 - cm__heard_t(k_contacts__t(0)) <= com_disguise_alert__x_window then
              k_contacts__t(4) = k_contacts__t(1) - cm__heard_x(k_contacts__t(0))
              k_contacts__t(5) = k_contacts__t(2) - cm__heard_y(k_contacts__t(0))
              if k_contacts__t(4) * k_contacts__t(4) + k_contacts__t(5) * k_contacts__t(5) > com_disguise_alert__x_distance * com_disguise_alert__x_distance then
                k_contacts__t(6) = 1
              end if
            end if
          end if
          k_contacts__t(7) = 0
          if com_disguise_alert__xa_amb(k_contacts__t(0)) = 0 and com_disguise_alert__xa_t1(k_contacts__t(0)) > worldTick and com_disguise_alert__xa_t2(k_contacts__t(0)) > worldTick and com_disguise_alert__xa_s1(k_contacts__t(0)) <> com_disguise_alert__xa_s2(k_contacts__t(0)) then
            k_contacts__t(4) = k_contacts__t(1) - com_disguise_alert__xa_x1(k_contacts__t(0))
            k_contacts__t(5) = k_contacts__t(2) - com_disguise_alert__xa_y1(k_contacts__t(0))
            k_contacts__t(8) = k_contacts__t(1) - com_disguise_alert__xa_x2(k_contacts__t(0))
            k_contacts__t(9) = k_contacts__t(2) - com_disguise_alert__xa_y2(k_contacts__t(0))
            if k_contacts__t(4) * k_contacts__t(4) + k_contacts__t(5) * k_contacts__t(5) <= com_disguise_alert__x_radius * com_disguise_alert__x_radius and k_contacts__t(8) * k_contacts__t(8) + k_contacts__t(9) * k_contacts__t(9) <= com_disguise_alert__x_radius * com_disguise_alert__x_radius then
              k_contacts__t(7) = 1
            end if
          end if
          if k_contacts__t(6) or k_contacts__t(7) then
            k_contacts__hostile(k_contacts__t(0)) = 1
            k_contacts__friend(k_contacts__t(0)) = 0
          end if
          if k_contacts__t(6) and k_contacts__xe_label < 0 and k_contacts__t(0) <> (selfId + 2) mod 16 then
            k_contacts__xe_label = k_contacts__t(0)
            k_contacts__xe_x = k_contacts__t(1)
            k_contacts__xe_y = k_contacts__t(2)
          end if
        end if
      end if
    end if
    k_contacts__t(0) = k_contacts__t(0) + 1
  wend

  ' Step 1.
  k_contacts__best = -1
  k_contacts__best_cost = 2147483647
  k_contacts__t(10) = -1
  k_contacts__t(11) = 2147483647
  k_contacts__thief = -1
  k_contacts__foes_near = 0
  k_contacts__friends_near = 1
  k_contacts__t(12) = 0
  k_contacts__t(13) = 0
  k_contacts__foes_seen = 0

  ' Step 2.
  k_contacts__t(0) = 0
  while k_contacts__t(0) < 16
    if k_contacts__t(0) <> selfId and visible(k_contacts__t(0)) then
      k_contacts__t(1) = playerX(k_contacts__t(0))
      k_contacts__t(2) = playerY(k_contacts__t(0))
      k_contacts__t(14) = k_contacts__t(1) - selfX
      k_contacts__t(15) = k_contacts__t(2) - selfY
      k_contacts__t(16) = k_contacts__t(14) * k_contacts__t(14) + k_contacts__t(15) * k_contacts__t(15)
      if k_contacts__hostile(k_contacts__t(0)) = 1 then
        k_contacts__t(17) = k_contacts__t(16) - (3 - playerHp(k_contacts__t(0))) * k_contacts__hp_weight
        if playerCarrying(k_contacts__t(0)) then
          k_contacts__t(17) = k_contacts__t(17) - k_contacts__carrier_bonus
          k_contacts__thief = k_contacts__t(0)
        end if
        if k_contacts__t(17) < k_contacts__best_cost and k_contacts__t(16) <= k_contacts__range_sq then
          k_contacts__best = k_contacts__t(0)
          k_contacts__best_cost = k_contacts__t(17)
        end if
        if com_focus_call__fc_until > worldTick and k_contacts__t(0) = com_focus_call__fc_label and k_contacts__t(16) <= k_contacts__range_sq then
          k_contacts__t(4) = k_contacts__t(1) - com_focus_call__fc_x
          k_contacts__t(5) = k_contacts__t(2) - com_focus_call__fc_y
          if k_contacts__t(4) * k_contacts__t(4) + k_contacts__t(5) * k_contacts__t(5) <= com_focus_call__focus_radius * com_focus_call__focus_radius and k_contacts__t(17) < k_contacts__t(11) then
            k_contacts__t(10) = k_contacts__t(0)
            k_contacts__t(11) = k_contacts__t(17)
          end if
        end if
        k_contacts__foes_seen = k_contacts__foes_seen + 1
        k_contacts__t(12) = k_contacts__t(12) + k_contacts__t(1)
        k_contacts__t(13) = k_contacts__t(13) + k_contacts__t(2)
        if k_contacts__t(16) < k_contacts__near_foe_sq then
          k_contacts__foes_near = k_contacts__foes_near + 1
        end if
      end if
      if k_contacts__friend(k_contacts__t(0)) = 1 then
        if k_contacts__t(16) < k_contacts__near_friend_sq then
          k_contacts__friends_near = k_contacts__friends_near + 1
        end if
      end if
    end if
    k_contacts__t(0) = k_contacts__t(0) + 1
  wend
  k_contacts__focus_used = 0
  if k_contacts__t(10) >= 0 then
    k_contacts__best = k_contacts__t(10)
    k_contacts__best_cost = k_contacts__t(11)
    k_contacts__focus_used = 1
  end if

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
  k_contacts__t(0) = 0
  while k_contacts__t(0) < 16
    if visible(k_contacts__t(0)) then
      k_contacts__old_x(k_contacts__t(0)) = playerX(k_contacts__t(0))
      k_contacts__old_y(k_contacts__t(0)) = playerY(k_contacts__t(0))
      k_contacts__seen_tick(k_contacts__t(0)) = worldTick
    end if
    k_contacts__t(0) = k_contacts__t(0) + 1
  wend
  if k_contacts__foes_seen > 0 then
    k_contacts__foe_cx = k_contacts__t(12) / k_contacts__foes_seen
    k_contacts__foe_cy = k_contacts__t(13) / k_contacts__foes_seen
  else
    k_contacts__foe_cx = 0
    k_contacts__foe_cy = 0
  end if

  ' Step 5: engagers.
  k_contacts__best_engagers = 0
  if k_contacts__best >= 0 then
    k_contacts__t(18) = playerX(k_contacts__best)
    k_contacts__t(19) = playerY(k_contacts__best)
    k_contacts__t(0) = 0
    while k_contacts__t(0) < 16
      if k_contacts__t(0) <> selfId and visible(k_contacts__t(0)) and k_contacts__friend(k_contacts__t(0)) = 1 then
        k_contacts__t(4) = playerX(k_contacts__t(0)) - k_contacts__t(18)
        k_contacts__t(5) = playerY(k_contacts__t(0)) - k_contacts__t(19)
        if k_contacts__t(4) * k_contacts__t(4) + k_contacts__t(5) * k_contacts__t(5) <= k_contacts__engage_range_sq then
          k_contacts__best_engagers = k_contacts__best_engagers + 1
        end if
      end if
      k_contacts__t(0) = k_contacts__t(0) + 1
    wend
  end if

  ' Step 6: the freshest heard enemy that is not in view.
  k_contacts__heard_target = -1
  k_contacts__heard_x = 0
  k_contacts__heard_y = 0
  k_contacts__t(20) = 0
  k_contacts__t(21) = 0
  k_contacts__t(0) = 0
  while k_contacts__t(0) < 16
    if com_enemy_sighting__ht_until(k_contacts__t(0)) > worldTick and visible(k_contacts__t(0)) = 0 and com_disguise_friend__df_until(k_contacts__t(0)) <= worldTick then
      if k_contacts__heard_target < 0 or com_enemy_sighting__ht_t(k_contacts__t(0)) > k_contacts__t(21) then
        k_contacts__heard_target = k_contacts__t(0)
        k_contacts__t(21) = com_enemy_sighting__ht_t(k_contacts__t(0))
        k_contacts__heard_x = com_enemy_sighting__ht_x(k_contacts__t(0))
        k_contacts__heard_y = com_enemy_sighting__ht_y(k_contacts__t(0))
      end if
    end if
    k_contacts__t(0) = k_contacts__t(0) + 1
  wend
end sub
