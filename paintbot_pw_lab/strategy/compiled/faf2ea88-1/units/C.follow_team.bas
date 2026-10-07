' unit C.follow_team sha256:f013b1c0c46e0b97a60164587af5d723938c8b154660a9a4c184d7298e054bb3 generated, do not edit
sub c_follow_team__start()
end sub

sub c_follow_team__tick()
  sk_motor__act(k_contacts__mate_x, k_contacts__mate_y, 0)
  if k_contacts__best < 0 and soundCount() > 0 and k_squad_target__objective >= 0 then
    c_follow_team__qx = controlX(k_squad_target__objective) - selfX
    c_follow_team__qy = controlY(k_squad_target__objective) - selfY
    if c_follow_team__qx * c_follow_team__qx + c_follow_team__qy * c_follow_team__qy < c_follow_team__quiet_sq then
      sneak(1)
    end if
  end if
  c_follow_team__status = 0
end sub
