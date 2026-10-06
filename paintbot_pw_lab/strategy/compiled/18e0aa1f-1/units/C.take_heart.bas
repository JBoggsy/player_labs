' unit C.take_heart sha256:7551b976d16fc3e69a716f65cb13b303e01ec2ddcaf42ee2f89133677ce83273 generated, do not edit
' Stand in the capture ring of the squad target (squad seats 0 and 1).
' Scratch cells, kept in one array to stay under the 512-global budget:
' 0 goal_x, 1 goal_y, 2 dx, 3 dy, 4 hold, 5 qx, 6 qy
DIM c_take_heart__t(6)

sub c_take_heart__start()
end sub

sub c_take_heart__tick()
  ' Step 1.
  c_take_heart__t(0) = controlX(k_squad_target__objective)
  c_take_heart__t(1) = controlY(k_squad_target__objective)
  ' Step 2.
  c_take_heart__t(2) = c_take_heart__t(0) - selfX
  c_take_heart__t(3) = c_take_heart__t(1) - selfY
  if c_take_heart__t(2) * c_take_heart__t(2) + c_take_heart__t(3) * c_take_heart__t(3) < c_take_heart__hold_sq then
    c_take_heart__t(4) = 1
  else
    c_take_heart__t(4) = 0
  end if
  ' Step 3.
  sk_motor__act(c_take_heart__t(0), c_take_heart__t(1), c_take_heart__t(4))
  ' Step 4: quiet approach when nothing is in sight but something was heard.
  if k_contacts__best < 0 and soundCount() > 0 then
    c_take_heart__t(5) = controlX(k_squad_target__objective) - selfX
    c_take_heart__t(6) = controlY(k_squad_target__objective) - selfY
    if c_take_heart__t(5) * c_take_heart__t(5) + c_take_heart__t(6) * c_take_heart__t(6) < c_take_heart__quiet_sq then
      sk_motor__sneak(1)
    end if
  end if
  ' Step 5.
  c_take_heart__status = 0
end sub
