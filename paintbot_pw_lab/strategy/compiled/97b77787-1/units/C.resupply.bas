' unit C.resupply sha256:f06cf1df14d6ed5a58b2d85e705d79e6ea78be1302fc682c55b812121c1680ad generated, do not edit
' Walk to the remembered supply.
sub c_resupply__start()
end sub

sub c_resupply__tick()
  ' Step 1.
  sk_motor__act(k_pickups__nearest_x, k_pickups__nearest_y, 0)
  ' Step 2: full-speed resupply when nothing is in sight but something was heard.
  if k_contacts__best < 0 and soundCount() > 0 and k_squad_target__objective >= 0 then
    c_resupply__qx = controlX(k_squad_target__objective) - selfX
    c_resupply__qy = controlY(k_squad_target__objective) - selfY
    if c_resupply__qx * c_resupply__qx + c_resupply__qy * c_resupply__qy < c_resupply__quiet_sq then
      sk_motor__skip_resupply_quiet()
    end if
  end if
  ' Step 3.
  c_resupply__status = 0
end sub
