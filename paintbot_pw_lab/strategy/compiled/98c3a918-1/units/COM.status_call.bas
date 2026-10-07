' unit COM.status_call sha256:b494678a36b17538a504c8c0cc4a2324162a46c4e6cff2029cbc9a7fc076d0b6 generated, do not edit
' Every fifteen seconds, say whether we are in contact, falling back, or moving.
sub com_status_call__send()
  if worldTick mod 360 = selfId * 21 then
    if k_contacts__best >= 0 then
      shout(strNew("Contact! Cover this lane."))
    else
      if k_contacts__foes_near - k_contacts__friends_near >= 1 then
        shout(strNew("Too many. Falling back."))
      else
        shout(strNew("Moving with the squad."))
      end if
    end if
    com_status_call__sent = 1
    com_status_call__blocked_total = sk_motor__blocked_total
    com_status_call__continued_total = sk_motor__continued_total
    com_status_call__forced_total = sk_motor__forced_total
    com_status_call__tracking_updates_total = sk_motor__tracking_updates_total
    com_status_call__repeat_trigger_total = sk_motor__repeat_trigger_total
    com_status_call__near_fight_blocked_total = s_supply_worth__near_fight_blocked_total
  else
    com_status_call__sent = 0
  end if
end sub
