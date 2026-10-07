' unit COM.status_call sha256:d250f7f432a340941ea5b879a9953f49a9ae309421c06d46ce75efbd6661254b generated, do not edit
' Periodic contact callout and motor telemetry snapshot.
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
    com_status_call__regroup_ticks_total = sk_motor__regroup_ticks_total
    com_status_call__local_retreat_ticks_total = sk_motor__local_retreat_ticks_total
    com_status_call__continued_total = sk_motor__continued_total
    com_status_call__forced_total = sk_motor__forced_total
    com_status_call__tracking_updates_total = sk_motor__tracking_updates_total
    com_status_call__cover_capture_ticks_total = sk_motor__cover_capture_ticks_total
  else
    com_status_call__sent = 0
  end if
end sub
