' unit COM.status_call sha256:141ba82a5a67d4a5a1b6e2684c7748a0f6a35ed7649c8926c6d6996936369e19 generated, do not edit
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
    com_status_call__gun_held_total = sk_motor__gun_held_total
  else
    com_status_call__sent = 0
  end if
end sub
