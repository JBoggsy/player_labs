' unit C.default_goal sha256:ddffaf0bea84c53624c78255164499994b4b6d23197b3e08a77c3309ff96bc84 generated, do not edit
' With no squad target, go for the thief, home, or the heart.
' Scratch cells, kept in one array to stay under the 512-global budget:
' 0 goal_x, 1 goal_y, 2 qx, 3 qy
DIM c_default_goal__t(3)

sub c_default_goal__start()
end sub

sub c_default_goal__tick()
  ' Step 1.
  if carrying then
    if ownHeartStolen and k_contacts__thief >= 0 then
      c_default_goal__t(0) = playerX(k_contacts__thief)
      c_default_goal__t(1) = playerY(k_contacts__thief)
    else
      c_default_goal__t(0) = homeX
      c_default_goal__t(1) = homeY
    end if
  else
    if k_contacts__thief >= 0 then
      c_default_goal__t(0) = playerX(k_contacts__thief)
      c_default_goal__t(1) = playerY(k_contacts__thief)
    else
      c_default_goal__t(0) = heartX
      c_default_goal__t(1) = heartY
    end if
  end if
  ' Step 2.
  sk_motor__act(c_default_goal__t(0), c_default_goal__t(1), 0)
  ' Step 3: quiet approach when nothing is in sight but something was heard.
  if k_contacts__best < 0 and soundCount() > 0 and k_squad_target__objective >= 0 then
    c_default_goal__t(2) = controlX(k_squad_target__objective) - selfX
    c_default_goal__t(3) = controlY(k_squad_target__objective) - selfY
    if c_default_goal__t(2) * c_default_goal__t(2) + c_default_goal__t(3) * c_default_goal__t(3) < c_default_goal__quiet_sq then
      sk_motor__sneak(1)
    end if
  end if
  ' Step 4.
  c_default_goal__status = 0
end sub
