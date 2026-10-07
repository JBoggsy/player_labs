' unit C.default_goal sha256:83445c35d72e4d8cb0246cd6628c4d45ef9174afe01bf0c18a25cad6b3c8b208 generated, do not edit
' After capture, pursue visible enemies while preserving the original fallback.
sub c_default_goal__start()
end sub

sub c_default_goal__tick()
  ' Step 1.
  if carrying then
    if ownHeartStolen and k_contacts__thief >= 0 then
      c_default_goal__goal_x = playerX(k_contacts__thief)
      c_default_goal__goal_y = playerY(k_contacts__thief)
    else
      c_default_goal__goal_x = homeX
      c_default_goal__goal_y = homeY
    end if
  else
    if k_contacts__thief >= 0 then
      c_default_goal__goal_x = playerX(k_contacts__thief)
      c_default_goal__goal_y = playerY(k_contacts__thief)
    else
      c_default_goal__goal_x = heartX
      c_default_goal__goal_y = heartY
    end if
  end if
  ' Step 2: approach a visible enemy after all squad objectives are owned.
  c_default_goal__pursuit = 0
  c_default_goal__hold = 0
  if carrying = 0 and k_contacts__thief < 0 and k_squad_target__heart_count > 0 and k_squad_target__objective < 0 then
    c_default_goal__target = k_contacts__best
    if c_default_goal__target < 0 then
      c_default_goal__nearest_d2 = 2147483647
      c_default_goal__i = 0
      while c_default_goal__i < 16
        if c_default_goal__i <> selfId and c_default_goal__i mod 2 <> selfTeam and visible(c_default_goal__i) then
          c_default_goal__dx = playerX(c_default_goal__i) - selfX
          c_default_goal__dy = playerY(c_default_goal__i) - selfY
          c_default_goal__d2 = c_default_goal__dx * c_default_goal__dx + c_default_goal__dy * c_default_goal__dy
          if c_default_goal__target < 0 or c_default_goal__d2 < c_default_goal__nearest_d2 then
            c_default_goal__target = c_default_goal__i
            c_default_goal__nearest_d2 = c_default_goal__d2
          end if
        end if
        c_default_goal__i = c_default_goal__i + 1
      wend
    end if
    if c_default_goal__target >= 0 then
      c_default_goal__pursuit = 1
      c_default_goal__goal_x = playerX(c_default_goal__target)
      c_default_goal__goal_y = playerY(c_default_goal__target)
      c_default_goal__dx = c_default_goal__goal_x - selfX
      c_default_goal__dy = c_default_goal__goal_y - selfY
      c_default_goal__d2 = c_default_goal__dx * c_default_goal__dx + c_default_goal__dy * c_default_goal__dy
      c_default_goal__stop_sq = c_default_goal__gun_stop_sq
      if hasSpray then
        c_default_goal__stop_sq = c_default_goal__spray_stop_sq
      end if
      if c_default_goal__d2 <= c_default_goal__stop_sq then
        c_default_goal__goal_x = selfX
        c_default_goal__goal_y = selfY
        c_default_goal__hold = 1
      end if
    end if
  end if
  ' Step 3.
  if c_default_goal__pursuit = 1 then
    sk_motor__cleanup(c_default_goal__goal_x, c_default_goal__goal_y, c_default_goal__hold)
  else
    sk_motor__act(c_default_goal__goal_x, c_default_goal__goal_y, 0)
  end if
  ' Step 4: quiet approach when nothing is in sight but something was heard.
  if k_contacts__best < 0 and soundCount() > 0 and k_squad_target__objective >= 0 then
    c_default_goal__qx = controlX(k_squad_target__objective) - selfX
    c_default_goal__qy = controlY(k_squad_target__objective) - selfY
    if c_default_goal__qx * c_default_goal__qx + c_default_goal__qy * c_default_goal__qy < c_default_goal__quiet_sq then
      sneak(1)
    end if
  end if
  ' Step 5.
  c_default_goal__status = 0
end sub
