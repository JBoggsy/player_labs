' unit C.fall_back sha256:ef05d271536a3786bec77078497b3867c38676df156be48e118966c01c267892 generated, do not edit
' Head for the heart that is far from the enemies and near us.
sub c_fall_back__start()
end sub

sub c_fall_back__tick()
  ' Step 1.
  c_fall_back__cx = k_contacts__foe_cx
  c_fall_back__cy = k_contacts__foe_cy
  c_fall_back__away = -1
  c_fall_back__away_score = -2147483647
  c_fall_back__j = 0
  while c_fall_back__j < heartCount() and c_fall_back__j < 64
    c_fall_back__ex = (controlX(c_fall_back__j) - c_fall_back__cx) / 16
    c_fall_back__ey = (controlY(c_fall_back__j) - c_fall_back__cy) / 16
    c_fall_back__mx = (controlX(c_fall_back__j) - selfX) / 16
    c_fall_back__my = (controlY(c_fall_back__j) - selfY) / 16
    c_fall_back__score = c_fall_back__ex * c_fall_back__ex + c_fall_back__ey * c_fall_back__ey - (c_fall_back__mx * c_fall_back__mx + c_fall_back__my * c_fall_back__my) / 2
    if c_fall_back__score > c_fall_back__away_score then
      c_fall_back__away = c_fall_back__j
      c_fall_back__away_score = c_fall_back__score
    end if
    c_fall_back__j = c_fall_back__j + 1
  wend
  ' Step 2.
  if c_fall_back__away >= 0 then
    c_fall_back__goal_x = controlX(c_fall_back__away)
    c_fall_back__goal_y = controlY(c_fall_back__away)
  else
    c_fall_back__goal_x = selfX
    c_fall_back__goal_y = selfY
  end if
  ' Step 3.
  sk_motor__act(c_fall_back__goal_x, c_fall_back__goal_y, 0)
  ' Step 4: quiet approach when nothing is in sight but something was heard.
  if k_contacts__best < 0 and soundCount() > 0 and k_squad_target__objective >= 0 then
    c_fall_back__qx = controlX(k_squad_target__objective) - selfX
    c_fall_back__qy = controlY(k_squad_target__objective) - selfY
    if c_fall_back__qx * c_fall_back__qx + c_fall_back__qy * c_fall_back__qy < c_fall_back__quiet_sq then
      sneak(1)
    end if
  end if
  ' Step 5.
  c_fall_back__status = 0
end sub
