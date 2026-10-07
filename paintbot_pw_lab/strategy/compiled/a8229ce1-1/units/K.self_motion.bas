' unit K.self_motion sha256:7d9fd1eaf31041f6c7478c749191bed6653b60597dd2e78541e501bd0cf18f29 generated, do not edit
' Our own movement since the previous tick; a respawn jump is not a velocity.
sub k_self_motion__init()
  k_self_motion__last_x = selfX
  k_self_motion__last_y = selfY
end sub

sub k_self_motion__update()
  k_self_motion__vx = selfX - k_self_motion__last_x
  k_self_motion__vy = selfY - k_self_motion__last_y
  if k_self_motion__vx > k_self_motion__teleport_step or k_self_motion__vx < 0 - k_self_motion__teleport_step or k_self_motion__vy > k_self_motion__teleport_step or k_self_motion__vy < 0 - k_self_motion__teleport_step then
    k_self_motion__vx = 0
    k_self_motion__vy = 0
    k_self_motion__teleported = 1
  else
    k_self_motion__teleported = 0
  end if
  k_self_motion__last_x = selfX
  k_self_motion__last_y = selfY
end sub
