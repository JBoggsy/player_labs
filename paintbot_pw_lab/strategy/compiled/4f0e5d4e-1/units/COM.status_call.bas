' unit COM.status_call sha256:f09a608835f9dab80bc83385f05ebb9fa16dd32d778ce81329f2564fccd9d614 generated, do not edit
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
    com_status_call__spray_distance_shots_total = sk_motor__spray_distance_shots_total
    com_status_call__blocked_total = sk_motor__blocked_total
    com_status_call__continued_total = sk_motor__continued_total
    com_status_call__spacing_changed_total = sk_motor__spacing_changed_total
    com_status_call__tracking_updates_total = sk_motor__tracking_updates_total
    com_status_call__cover_capture_ticks_total = sk_motor__cover_capture_ticks_total
  else
    com_status_call__sent = 0
  end if
end sub
