' unit S.supply_worth sha256:562c4fb00dccbe7c5d7f9de4ad3a11e02cae113f436963f0381c63bf9cce40da generated, do not edit
' A wanted supply is remembered and no close fight stops us from fetching it.
sub s_supply_worth__eval()
  if k_pickups__nearest >= 0 and (k_contacts__best < 0 or k_contacts__best_cost > s_supply_worth__fight_clear_sq or selfHp = 1) then
    s_supply_worth__on = 1
  else
    s_supply_worth__on = 0
  end if
end sub
