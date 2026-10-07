' unit C.resupply sha256:cd8990c5650af4b96e73a5ed6939f7fd690edd4a3514313546e4729c0fd667dd generated, do not edit
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
      sneak(1)
    end if
  end if
  ' Step 3.
  c_resupply__status = 0
end sub
