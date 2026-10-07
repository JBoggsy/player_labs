' unit COM.status_call sha256:fbef575a721e70c024adf5f845120fe360d04777a52afa2c50d5765fd343bca6 generated, do not edit
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
    com_status_call__route_class = k_opening_signature__route_class
    com_status_call__classified_tick = k_opening_signature__classified_tick
    com_status_call__map_known = k_opening_signature__map_known
    com_status_call__opening_ticks_total = sk_motor__opening_ticks_total
    com_status_call__dry_combat_changed_total = sk_motor__dry_combat_changed_total
    com_status_call__cover_capture_ticks_total = sk_motor__cover_capture_ticks_total
  else
    com_status_call__sent = 0
  end if
end sub
