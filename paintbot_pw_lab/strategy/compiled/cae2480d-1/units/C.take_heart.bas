' unit C.take_heart sha256:f59e0462e455bd0767345774ddcc94f3b3d2391af30e7c32097ade92ae616dba generated, do not edit
' Stand in the capture ring of the squad target (squad seats 0 and 1).
sub c_take_heart__start()
end sub

sub c_take_heart__tick()
  c_take_heart__goal_x = controlX(k_squad_target__objective)
  c_take_heart__goal_y = controlY(k_squad_target__objective)
  c_take_heart__dx = c_take_heart__goal_x - selfX
  c_take_heart__dy = c_take_heart__goal_y - selfY
  if c_take_heart__dx * c_take_heart__dx + c_take_heart__dy * c_take_heart__dy < c_take_heart__hold_sq then
    c_take_heart__hold = 1
  else
    c_take_heart__hold = 0
  end if
  sk_motor__act(c_take_heart__goal_x, c_take_heart__goal_y, c_take_heart__hold)
  ' Quiet approach when nothing is in sight but something was heard.
  if k_contacts__best < 0 and soundCount() > 0 then
    c_take_heart__qx = controlX(k_squad_target__objective) - selfX
    c_take_heart__qy = controlY(k_squad_target__objective) - selfY
    if c_take_heart__qx * c_take_heart__qx + c_take_heart__qy * c_take_heart__qy < c_take_heart__quiet_sq then
      sneak(1)
    end if
  end if
  c_take_heart__status = 0
end sub
