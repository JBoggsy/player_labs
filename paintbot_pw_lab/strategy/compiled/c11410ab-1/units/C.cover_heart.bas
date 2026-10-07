' unit C.cover_heart sha256:9f3db361207ba8d4efb7db4a6029bd542998025899b4861177c9252240b81552 generated, do not edit
' Cover cogs directly occupy the target capture ring.
sub c_cover_heart__start()
end sub

sub c_cover_heart__tick()
  c_cover_heart__hx = controlX(k_squad_target__objective)
  c_cover_heart__hy = controlY(k_squad_target__objective)
  c_cover_heart__dx = c_cover_heart__hx - selfX
  c_cover_heart__dy = c_cover_heart__hy - selfY
  c_cover_heart__hold = 0
  if c_cover_heart__dx * c_cover_heart__dx + c_cover_heart__dy * c_cover_heart__dy < c_cover_heart__hold_sq then
    c_cover_heart__hold = 1
  end if
  sk_motor__direct_capture(c_cover_heart__hx, c_cover_heart__hy, c_cover_heart__hold)
  if k_contacts__best < 0 and soundCount() > 0 and c_cover_heart__dx * c_cover_heart__dx + c_cover_heart__dy * c_cover_heart__dy < c_cover_heart__quiet_sq then
    sneak(1)
  end if
  c_cover_heart__status = 0
end sub
