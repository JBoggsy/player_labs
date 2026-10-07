' unit S.central_opening sha256:db4e0be89bd111b79f4c9d58f32c771bf3f590a4e028933250740e65b83943d9 generated, do not edit
' Commit both squads to the central approaches during the opening.
sub s_central_opening__eval()
  if worldTick <= s_central_opening__opening_ticks and heartCount() >= 2 and k_pickups__critical = 0 then
    s_central_opening__on = 1
  else
    s_central_opening__on = 0
  end if
end sub
