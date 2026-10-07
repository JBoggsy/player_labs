' unit C.default_goal sha256:6e56e4ac481f51f4971f1614814cddb96ad581f289ad1b1230e7e29f93d4c272 generated, do not edit
' With no squad target, go for the thief, home, or the heart.
sub c_default_goal__start()
end sub

sub c_default_goal__tick()
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
  sk_motor__act(c_default_goal__goal_x, c_default_goal__goal_y, 0)
  if k_contacts__best < 0 and soundCount() > 0 and k_squad_target__objective >= 0 then
    c_default_goal__qx = controlX(k_squad_target__objective) - selfX
    c_default_goal__qy = controlY(k_squad_target__objective) - selfY
    if c_default_goal__qx * c_default_goal__qx + c_default_goal__qy * c_default_goal__qy < c_default_goal__quiet_sq then
      sneak(1)
    end if
  end if
  c_default_goal__status = 0
end sub
