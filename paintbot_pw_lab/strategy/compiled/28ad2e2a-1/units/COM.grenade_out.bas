' unit COM.grenade_out sha256:0daa3c5423701b417c5094339907c230f3084615efbd9af3ff8931be209207f2 generated, do not edit
' Call out a grenade when the charge is ready.
sub com_grenade_out__send()
  if sk_motor__threw = 1 then
    shout(strNew("Grenade out!"))
    com_grenade_out__sent = 1
  else
    com_grenade_out__sent = 0
  end if
end sub
