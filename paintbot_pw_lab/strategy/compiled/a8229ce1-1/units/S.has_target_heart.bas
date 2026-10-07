' unit S.has_target_heart sha256:6b60c6ab97e4664fa799fdb79198871401925214fa58d94ce890e32c8b29a453 generated, do not edit
' Our squad has a target heart.
sub s_has_target_heart__eval()
  if k_squad_target__objective >= 0 then
    s_has_target_heart__on = 1
  else
    s_has_target_heart__on = 0
  end if
end sub
