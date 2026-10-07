' unit COM.status_call sha256:21d26f91eb201286de717821caec29cc8ec6df50e3b3039fc589a50df0642e05 generated, do not edit
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
    com_status_call__release_charge = sk_motor__release_charge
    com_status_call__release_need = sk_motor__release_need
    com_status_call__starts_total = sk_motor__starts_total
    com_status_call__blocked_total = sk_motor__blocked_total
    com_status_call__continued_total = sk_motor__continued_total
    com_status_call__forced_total = sk_motor__forced_total
  else
    com_status_call__sent = 0
  end if
end sub
