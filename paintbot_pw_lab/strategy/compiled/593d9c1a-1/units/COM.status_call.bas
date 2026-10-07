' unit COM.status_call sha256:ac5fbd9a933c1d57cc5926c6ce73082529d0afaacabf050a43cbac950ccfe5b7 generated, do not edit
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
    com_status_call__phase = k_counter_phase__phase
    com_status_call__trigger = k_counter_phase__trigger
    com_status_call__release_tick = k_counter_phase__release_tick
    com_status_call__stage_ticks = k_counter_phase__stage_ticks
    com_status_call__counter_ticks = k_counter_phase__counter_ticks
    com_status_call__map_known = k_opening_signature__map_known
  else
    com_status_call__sent = 0
  end if
end sub
