' unit K.opening_signature sha256:cc81361ba7e986505e3cdbe179f6a1901ba4226997bf4957c39ff71955a81812 generated, do not edit
sub k_opening_signature__init()
  k_opening_signature__route_class = 0
  k_opening_signature__classified_tick = 0
end sub

sub k_opening_signature__update()
  if k_opening_signature__route_class = 0 and worldTick >= k_opening_signature__classify_tick then
    k_opening_signature__route_class = 2
    k_opening_signature__classified_tick = worldTick
    if worldTick = k_opening_signature__classify_tick and heartCount() = 10 then
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
