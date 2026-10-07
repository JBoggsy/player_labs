' unit C.resupply sha256:9ef584118d9cd4b76ed605e9aa2af6d4b5dbc239c7161a408a95da1bda8bb117 generated, do not edit
' Walk to the remembered supply.
' Scratch cells, kept in one array to stay under the 512-global budget: 0 qx, 1 qy
DIM c_resupply__t(1)

sub c_resupply__start()
end sub

sub c_resupply__tick()
  ' Step 1.
  sk_motor__act(k_pickups__nearest_x, k_pickups__nearest_y, 0)
  ' Step 2: quiet approach when nothing is in sight but something was heard.
  if k_contacts__best < 0 and soundCount() > 0 and k_squad_target__objective >= 0 then
    c_resupply__t(0) = controlX(k_squad_target__objective) - selfX
    c_resupply__t(1) = controlY(k_squad_target__objective) - selfY
    if c_resupply__t(0) * c_resupply__t(0) + c_resupply__t(1) * c_resupply__t(1) < c_resupply__quiet_sq then
      sk_motor__sneak(1)
    end if
  end if
  ' Step 3.
  c_resupply__status = 0
end sub
