' unit S.losing_fight sha256:933d43480f63f22c046731aa0507077367ac39bba68031ae45a85ff91ab3fcce generated, do not edit
' Retreat when enemies within gun reach outnumber nearby support.
sub s_losing_fight__eval()
  if k_contacts__fight_foes - k_contacts__friends_near >= 1 and carrying = 0 and k_squad_target__heart_count > 0 then
    s_losing_fight__on = 1
  else
    s_losing_fight__on = 0
  end if
  if s_losing_fight__on = 0 and carrying = 0 and k_squad_target__heart_count > 0 and k_contacts__foes_near - k_contacts__friends_near >= 1 then
    s_losing_fight__retreat_range_saved_total = s_losing_fight__retreat_range_saved_total + 1
  else
    s_losing_fight__retreat_range_saved_total = s_losing_fight__retreat_range_saved_total
  end if
end sub
