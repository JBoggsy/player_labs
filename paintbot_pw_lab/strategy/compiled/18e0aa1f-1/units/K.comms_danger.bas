' unit K.comms_danger sha256:c775c0ad3680892749969efb905bc02bf5abc1186ffdb8459d2be55a1f6b87b6 generated, do not edit
' Live grenade zones and the most recent under-fire area that teammates reported.
sub k_comms_danger__update()
  ' Step 1: grenade zones.
  k_comms_danger__zone_count = 0
  k_comms_danger__i = 0
  while k_comms_danger__i < 4
    k_comms_danger__grenade_x(k_comms_danger__i) = com_grenade_warning__gz_x(k_comms_danger__i)
    k_comms_danger__grenade_y(k_comms_danger__i) = com_grenade_warning__gz_y(k_comms_danger__i)
    k_comms_danger__grenade_until(k_comms_danger__i) = com_grenade_warning__gz_until(k_comms_danger__i)
    if com_grenade_warning__gz_until(k_comms_danger__i) <= worldTick then
      k_comms_danger__grenade_until(k_comms_danger__i) = 0
    end if
    if k_comms_danger__grenade_until(k_comms_danger__i) > worldTick then
      k_comms_danger__zone_count = k_comms_danger__zone_count + 1
    end if
    k_comms_danger__i = k_comms_danger__i + 1
  wend
  ' Step 2: the latest under-fire report.
  if com_under_fire__du_until > worldTick then
    k_comms_danger__danger_x = com_under_fire__du_x
    k_comms_danger__danger_y = com_under_fire__du_y
    k_comms_danger__danger_dir = com_under_fire__du_dir
    k_comms_danger__danger_until = com_under_fire__du_until
  else
    k_comms_danger__danger_x = 0
    k_comms_danger__danger_y = 0
    k_comms_danger__danger_dir = 0
    k_comms_danger__danger_until = 0
  end if
end sub
