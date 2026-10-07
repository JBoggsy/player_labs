' unit COM.status_call sha256:989cea220aeb598097b8206392f2efe99dc3a90c404d852e4d9b02a0f1b466b9 generated, do not edit
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
    com_status_call__frontier_changed_total = k_squad_target__frontier_changed_total
    com_status_call__spray_distance_shots_total = sk_motor__spray_distance_shots_total
    com_status_call__direct_capture_ticks_total = sk_motor__direct_capture_ticks_total
    com_status_call__forced_total = sk_motor__forced_total
    com_status_call__tracking_updates_total = sk_motor__tracking_updates_total
    com_status_call__cover_capture_ticks_total = sk_motor__cover_capture_ticks_total
  else
    com_status_call__sent = 0
  end if
end sub
