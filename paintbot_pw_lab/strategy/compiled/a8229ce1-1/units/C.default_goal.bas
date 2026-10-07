' unit C.default_goal sha256:38dab055e1e6feb3a8054df9882ec83e75eb49eac311c89d411d00c9273a5b31 generated, do not edit
' With no squad target, go for the thief, home, or the heart.
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
  ' Step 2.
  sk_motor__act(c_default_goal__goal_x, c_default_goal__goal_y, 0)
  ' Step 3: quiet approach when nothing is in sight but something was heard.
  if k_contacts__best < 0 and soundCount() > 0 and k_squad_target__objective >= 0 then
    c_default_goal__qx = controlX(k_squad_target__objective) - selfX
    c_default_goal__qy = controlY(k_squad_target__objective) - selfY
    if c_default_goal__qx * c_default_goal__qx + c_default_goal__qy * c_default_goal__qy < c_default_goal__quiet_sq then
      sk_motor__quiet_approach(k_squad_target__objective)
    end if
  end if
  ' Step 4.
  c_default_goal__status = 0
end sub
