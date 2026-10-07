' unit K.opening_signature sha256:40a9ea53ac81a5fe484cf065d8272b7b0c9f8f31d966bbd536e4d192950f6db6 generated, do not edit
sub k_opening_signature__init()
  k_opening_signature__route_class = 0
  k_opening_signature__classified_tick = 0
  k_opening_signature__map_known = 1
  if heartCount() <> 10 or pickupCount() <> 22 or trenchCount() <> 6 then
    k_opening_signature__map_known = 0
  end if
  if mapMinX() <> -4800 then
    k_opening_signature__map_known = 0
  end if
  if mapMinY() <> -2800 then
    k_opening_signature__map_known = 0
  end if
  if mapMaxX() <> 11200 then
    k_opening_signature__map_known = 0
  end if
  if mapMaxY() <> 6800 then
    k_opening_signature__map_known = 0
  end if
  if heartCount() = 10 then
    if controlX(0) <> 960 or controlY(0) <> 2000 then
      k_opening_signature__map_known = 0
    end if
    if controlX(1) <> 5440 or controlY(1) <> 2000 then
      k_opening_signature__map_known = 0
    end if
    if controlX(2) <> -3060 or controlY(2) <> 440 then
      k_opening_signature__map_known = 0
    end if
    if controlX(3) <> 9460 or controlY(3) <> 3560 then
      k_opening_signature__map_known = 0
    end if
    if controlX(4) <> 880 or controlY(4) <> -1720 then
      k_opening_signature__map_known = 0
    end if
    if controlX(5) <> 5520 or controlY(5) <> 5720 then
      k_opening_signature__map_known = 0
    end if
    if controlX(6) <> -3000 or controlY(6) <> 3500 then
      k_opening_signature__map_known = 0
    end if
    if controlX(7) <> 9400 or controlY(7) <> 500 then
      k_opening_signature__map_known = 0
    end if
    if controlX(8) <> 3200 or controlY(8) <> 1250 then
      k_opening_signature__map_known = 0
    end if
    if controlX(9) <> 3200 or controlY(9) <> 2750 then
      k_opening_signature__map_known = 0
    end if
  end if
  if trenchCount() = 6 then
    if trenchX(0) <> 1950 or trenchY(0) <> 650 or trenchW(0) <> 280 or trenchH(0) <> 280 then
      k_opening_signature__map_known = 0
    end if
    if trenchX(1) <> 4450 or trenchY(1) <> 3350 or trenchW(1) <> 280 or trenchH(1) <> 280 then
      k_opening_signature__map_known = 0
    end if
    if trenchX(2) <> 2600 or trenchY(2) <> 2050 or trenchW(2) <> 280 or trenchH(2) <> 280 then
      k_opening_signature__map_known = 0
    end if
    if trenchX(3) <> 3800 or trenchY(3) <> 1950 or trenchW(3) <> 280 or trenchH(3) <> 280 then
      k_opening_signature__map_known = 0
    end if
    if trenchX(4) <> 900 or trenchY(4) <> 2850 or trenchW(4) <> 280 or trenchH(4) <> 280 then
      k_opening_signature__map_known = 0
    end if
    if trenchX(5) <> 5500 or trenchY(5) <> 1150 or trenchW(5) <> 280 or trenchH(5) <> 280 then
      k_opening_signature__map_known = 0
    end if
  end if
  if selfTeam = 0 and (homeX <> 960 or homeY <> 2000) then
    k_opening_signature__map_known = 0
  end if
  if selfTeam = 1 and (homeX <> 5440 or homeY <> 2000) then
    k_opening_signature__map_known = 0
  end if
end sub

sub k_opening_signature__update()
  if k_opening_signature__route_class = 0 and worldTick >= k_opening_signature__classify_tick then
    k_opening_signature__route_class = 2
    k_opening_signature__classified_tick = worldTick
    if worldTick = k_opening_signature__classify_tick and k_opening_signature__map_known = 1 then
      k_opening_signature__outer = 7 - selfTeam
      k_opening_signature__central = 8 + selfTeam
      k_opening_signature__enemy = 1 - selfTeam
      if controlOwner(k_opening_signature__outer) = k_opening_signature__enemy or (controlCaptureTeam(k_opening_signature__outer) = k_opening_signature__enemy and controlCaptureTicks(k_opening_signature__outer) > 0) then
        k_opening_signature__outer_claim = 1
      else
        k_opening_signature__outer_claim = 0
      end if
      if controlOwner(k_opening_signature__central) = k_opening_signature__enemy or (controlCaptureTeam(k_opening_signature__central) = k_opening_signature__enemy and controlCaptureTicks(k_opening_signature__central) > 0) then
        k_opening_signature__central_claim = 1
      else
        k_opening_signature__central_claim = 0
      end if
      if k_opening_signature__outer_claim = 1 and k_opening_signature__central_claim = 0 then
        k_opening_signature__route_class = 1
      end if
    end if
  end if
end sub
