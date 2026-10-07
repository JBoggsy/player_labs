' unit S.glory_worth sha256:6f02c9cd039657b425c802fa740621040b3f8834cbe77ab81b78e5d798af3b1d generated, do not edit
sub s_glory_worth__eval()
  s_glory_worth__on = 0
  if k_nearby_glory__nearest >= 0 and k_contacts__foes_seen = 0 and k_pickups__critical = 0 and carrying = 0 then
    s_glory_worth__on = 1
  end if
  s_glory_worth__j = 0
  while s_glory_worth__j < heartCount() and s_glory_worth__j < 64
    if controlCaptureTeam(s_glory_worth__j) = selfTeam then
      s_glory_worth__dx = controlX(s_glory_worth__j) - selfX
      s_glory_worth__dy = controlY(s_glory_worth__j) - selfY
      if s_glory_worth__dx * s_glory_worth__dx + s_glory_worth__dy * s_glory_worth__dy <= s_glory_worth__capture_sq then
        s_glory_worth__on = 0
      end if
    end if
    s_glory_worth__j = s_glory_worth__j + 1
  wend
end sub
