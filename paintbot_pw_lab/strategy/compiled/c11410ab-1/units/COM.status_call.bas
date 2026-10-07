' unit COM.status_call sha256:8f6f16ac28e9cbc79b639a17e5b223a4fda0c888bde4a060d2f16060f1f4211a generated, do not edit
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
    com_status_call__glory_detour_ticks_total = sk_motor__glory_detour_ticks_total
    com_status_call__frontier_changed_total = k_squad_target__frontier_changed_total
    com_status_call__direct_capture_ticks_total = sk_motor__direct_capture_ticks_total
    com_status_call__tracking_updates_total = sk_motor__tracking_updates_total
    com_status_call__cover_capture_ticks_total = sk_motor__cover_capture_ticks_total
  else
    com_status_call__sent = 0
  end if
end sub
