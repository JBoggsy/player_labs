' unit S.supply_worth sha256:63ebad0636dd0a15c4c46d074c832cf0b1844ffc77e2d5cd49a0d502dec43301 generated, do not edit
' A wanted supply is remembered and no close fight stops us from fetching it.
sub s_supply_worth__init()
  s_supply_worth__near_fight_blocked_total = 0
end sub

sub s_supply_worth__eval()
  s_supply_worth__rejected = 0
  if k_pickups__nearest >= 0 and (k_contacts__best < 0 or k_contacts__best_cost > s_supply_worth__fight_clear_sq or k_pickups__critical = 1) then
    s_supply_worth__on = 1
  else
    s_supply_worth__on = 0
  end if
  if s_supply_worth__on = 1 and k_pickups__critical = 0 and k_contacts__best >= 0 then
    s_supply_worth__dx = playerX(k_contacts__best) - selfX
    s_supply_worth__dy = playerY(k_contacts__best) - selfY
    if s_supply_worth__dx * s_supply_worth__dx + s_supply_worth__dy * s_supply_worth__dy <= s_supply_worth__fight_clear_sq then
      s_supply_worth__on = 0
      s_supply_worth__rejected = 1
    end if
  end if
  s_supply_worth__near_fight_blocked_total = s_supply_worth__near_fight_blocked_total + s_supply_worth__rejected
end sub
