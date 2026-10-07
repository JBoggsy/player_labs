' unit S.central_opening sha256:c7ae781cf44238f1bf50db31baf24940fe17b37f25c280b281d62e23b87008dd generated, do not edit
' Commit both squads to the central approaches during the opening.
sub s_central_opening__eval()
  if k_opening_signature__route_class = 1 and worldTick <= s_central_opening__opening_ticks and heartCount() >= 2 and k_pickups__critical = 0 then
    s_central_opening__on = 1
  else
    s_central_opening__on = 0
  end if
end sub
