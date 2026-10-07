' unit C.resupply sha256:0b747da6f4fbf4bffbbedc955353c62f02d99212ee01113f6c92f281890e33e8 generated, do not edit
' Walk to the remembered supply.
sub c_resupply__start()
end sub

sub c_resupply__tick()
  ' Step 1.
  sk_motor__act(k_pickups__nearest_x, k_pickups__nearest_y, 0)
  ' Step 2: quiet approach when nothing is in sight but something was heard.
  if k_contacts__best < 0 and soundCount() > 0 and k_squad_target__objective >= 0 then
    c_resupply__qx = controlX(k_squad_target__objective) - selfX
    c_resupply__qy = controlY(k_squad_target__objective) - selfY
    if c_resupply__qx * c_resupply__qx + c_resupply__qy * c_resupply__qy < c_resupply__quiet_sq then
      sk_motor__quiet_approach(k_squad_target__objective)
    end if
  end if
  ' Step 3.
  c_resupply__status = 0
end sub
