' unit S.supply_worth sha256:097169d598f879dccd3abae806a3477c10e299ea8f5978d34be92cfa0a67187b generated, do not edit
' A wanted supply is remembered and no close fight stops us from fetching it.
sub s_supply_worth__eval()
  if k_pickups__nearest >= 0 and (k_contacts__best < 0 or k_contacts__best_cost > s_supply_worth__fight_clear_sq or k_pickups__critical = 1) then
    s_supply_worth__on = 1
  else
    s_supply_worth__on = 0
  end if
end sub
