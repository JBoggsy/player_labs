' unit S.supply_worth sha256:e555c0632d6c80aace7671d9db48e6f289663d25c55cc11e0eb018469ba7554c generated, do not edit
' A wanted supply is remembered and no close fight stops us from fetching it.
sub s_supply_worth__init()
  s_supply_worth__opening_supply_blocked_total = 0
end sub

sub s_supply_worth__eval()
  s_supply_worth__blocked = 0
  if k_pickups__nearest >= 0 and (k_contacts__best < 0 or k_contacts__best_cost > s_supply_worth__fight_clear_sq or k_pickups__critical = 1) then
    s_supply_worth__on = 1
  else
    s_supply_worth__on = 0
  end if
  if s_supply_worth__on = 1 and k_pickups__critical = 0 and worldTick < s_supply_worth__opening_ticks and k_squad_target__seat < 2 then
    if k_squad_target__objective >= 0 then
      if controlOwner(k_squad_target__objective) = -1 then
        s_supply_worth__on = 0
        s_supply_worth__blocked = 1
      end if
    end if
  end if
  s_supply_worth__opening_supply_blocked_total = s_supply_worth__opening_supply_blocked_total + s_supply_worth__blocked
end sub
