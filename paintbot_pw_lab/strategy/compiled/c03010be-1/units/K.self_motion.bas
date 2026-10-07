' unit K.self_motion sha256:d728b0e7a4b728c002b2f3aa5c914b09f3700b55ec2fdcf68dc431ba2ae10102 generated, do not edit
' Our own movement since the previous tick, and whether we lost hit points.
' Memory and scratch cells, kept in one array to stay under the 512-global budget:
' 0 last_x, 1 last_y, 2 last_hp, 3 last_uniform, 4 uni
DIM k_self_motion__t(4)

sub k_self_motion__init()
  k_self_motion__t(0) = selfX
  k_self_motion__t(1) = selfY
  k_self_motion__t(2) = selfHp
  k_self_motion__t(3) = 0
  k_self_motion__uniform_since = 0
end sub

sub k_self_motion__update()
  ' Step 1.
  k_self_motion__vx = selfX - k_self_motion__t(0)
  k_self_motion__vy = selfY - k_self_motion__t(1)
  ' Step 2: a respawn jump is not a velocity.
  if k_self_motion__vx > k_self_motion__teleport_step or k_self_motion__vx < 0 - k_self_motion__teleport_step or k_self_motion__vy > k_self_motion__teleport_step or k_self_motion__vy < 0 - k_self_motion__teleport_step then
    k_self_motion__vx = 0
    k_self_motion__vy = 0
    k_self_motion__teleported = 1
  else
    k_self_motion__teleported = 0
  end if
  ' Step 3.
  k_self_motion__t(0) = selfX
  k_self_motion__t(1) = selfY
  ' Step 4.
  if selfHp < k_self_motion__t(2) then
    k_self_motion__hp_drop = 1
  else
    k_self_motion__hp_drop = 0
  end if
  k_self_motion__t(2) = selfHp
  ' Step 5.
  k_self_motion__t(4) = hasUniform()
  if k_self_motion__t(4) = 1 and k_self_motion__t(3) = 0 then
    k_self_motion__uniform_since = worldTick + 1
  end if
  if k_self_motion__t(4) = 0 then
    k_self_motion__uniform_since = 0
  end if
  k_self_motion__t(3) = k_self_motion__t(4)
end sub
