' unit S.losing_fight sha256:f5a8a8388f9d7f65985452424be2a3792ead5e61a95d15758d81e379b00fb232 generated, do not edit
' We see more near enemies than near friends, so we refuse the fight.
sub s_losing_fight__eval()
  if k_contacts__foes_near - k_contacts__friends_near >= 1 and carrying = 0 and k_squad_target__heart_count > 0 then
    s_losing_fight__on = 1
  else
    s_losing_fight__on = 0
  end if
end sub
