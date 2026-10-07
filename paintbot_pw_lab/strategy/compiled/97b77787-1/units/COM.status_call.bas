' unit COM.status_call sha256:4596985de77999b6223ae04f169fc6bd5b29aa5bda45d2983764fbdabb5bb859 generated, do not edit
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
    com_status_call__quiet_skipped_total = sk_motor__quiet_skipped_total
    com_status_call__resupply_quiet_skipped_total = sk_motor__resupply_quiet_skipped_total
  else
    com_status_call__sent = 0
  end if
end sub
