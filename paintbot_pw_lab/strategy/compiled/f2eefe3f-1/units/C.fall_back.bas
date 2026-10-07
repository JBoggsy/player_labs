' unit C.fall_back sha256:3a869093d2460df605126d376a263d753895e4455caf266251e468f138aa7ffb generated, do not edit
' Regroup behind the nearest eligible visible teammate, or retreat locally.
sub c_fall_back__start()
end sub

sub c_fall_back__tick()
  c_fall_back__cx = k_contacts__foe_cx
  c_fall_back__cy = k_contacts__foe_cy
  c_fall_back__buddy = -1
  c_fall_back__buddy_cost = 2147483647
  c_fall_back__i = 0
  while c_fall_back__i < 16
    if c_fall_back__i <> selfId and visible(c_fall_back__i) <> 0 and c_fall_back__i mod 2 = selfTeam then
      c_fall_back__dx = playerX(c_fall_back__i) - selfX
      c_fall_back__dy = playerY(c_fall_back__i) - selfY
      c_fall_back__d2 = c_fall_back__dx * c_fall_back__dx + c_fall_back__dy * c_fall_back__dy
      if c_fall_back__d2 > c_fall_back__buddy_min_sq and c_fall_back__d2 <= c_fall_back__buddy_max_sq and c_fall_back__d2 < c_fall_back__buddy_cost then
        c_fall_back__buddy = c_fall_back__i
        c_fall_back__buddy_cost = c_fall_back__d2
      end if
    end if
    c_fall_back__i = c_fall_back__i + 1
  wend
  if c_fall_back__buddy >= 0 then
    c_fall_back__anchor_x = playerX(c_fall_back__buddy)
    c_fall_back__anchor_y = playerY(c_fall_back__buddy)
    c_fall_back__has_buddy = 1
  else
    c_fall_back__anchor_x = selfX
    c_fall_back__anchor_y = selfY
    c_fall_back__has_buddy = 0
  end if
  c_fall_back__dx = c_fall_back__anchor_x - c_fall_back__cx
  c_fall_back__dy = c_fall_back__anchor_y - c_fall_back__cy
  c_fall_back__scale = c_fall_back__dx
  if c_fall_back__scale < 0 then
    c_fall_back__scale = -c_fall_back__scale
  end if
  c_fall_back__abs_y = c_fall_back__dy
  if c_fall_back__abs_y < 0 then
    c_fall_back__abs_y = -c_fall_back__abs_y
  end if
  if c_fall_back__abs_y > c_fall_back__scale then
    c_fall_back__scale = c_fall_back__abs_y
  end if
  if c_fall_back__scale = 0 then
    c_fall_back__dx = homeX - selfX
    c_fall_back__dy = homeY - selfY
    c_fall_back__scale = c_fall_back__dx
    if c_fall_back__scale < 0 then
      c_fall_back__scale = -c_fall_back__scale
    end if
    c_fall_back__abs_y = c_fall_back__dy
    if c_fall_back__abs_y < 0 then
      c_fall_back__abs_y = -c_fall_back__abs_y
    end if
    if c_fall_back__abs_y > c_fall_back__scale then
      c_fall_back__scale = c_fall_back__abs_y
    end if
  end if
  if c_fall_back__scale > 0 then
    c_fall_back__goal_x = c_fall_back__anchor_x + c_fall_back__dx * c_fall_back__retreat_step \ c_fall_back__scale
    c_fall_back__goal_y = c_fall_back__anchor_y + c_fall_back__dy * c_fall_back__retreat_step \ c_fall_back__scale
  else
    c_fall_back__goal_x = c_fall_back__anchor_x
    c_fall_back__goal_y = c_fall_back__anchor_y
  end if
  sk_motor__regroup(c_fall_back__goal_x, c_fall_back__goal_y, c_fall_back__has_buddy)
  c_fall_back__status = 0
end sub
