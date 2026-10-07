' unit S.losing_fight sha256:26fa46be62e5cbe4549707e0ad8de2284b1b020f3fbbf5a06e33c15e6f295024 generated, do not edit
' We see more near enemies than near friends, so we refuse the fight.
sub s_losing_fight__eval()
  if k_contacts__foes_near - k_contacts__friends_near >= 1 and not carrying and k_squad_target__heart_count > 0 then
    s_losing_fight__on = 1
  else
    s_losing_fight__on = 0
  end if
end sub
