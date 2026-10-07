' unit C.cover_heart sha256:9b11c2ac0ab5d14baf52103eb38516aba50ca1b40e08ff40f59fbc6f030c6f89 generated, do not edit
' Cover the squad target from outside the ring, and step in when nobody captures it
' (squad seats 2 and 3).
sub c_cover_heart__start()
end sub

sub c_cover_heart__tick()
  if k_opening_signature__map_known = 1 and k_opening_signature__route_class = 2 then
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
  else
  ' Step 1.
  c_cover_heart__hx = controlX(k_squad_target__objective)
  c_cover_heart__hy = controlY(k_squad_target__objective)
  c_cover_heart__goal_x = c_cover_heart__hx
  c_cover_heart__goal_y = c_cover_heart__hy
  ' Step 2: finish our active capture before considering the cover post.
  c_cover_heart__dx = c_cover_heart__hx - selfX
  c_cover_heart__dy = c_cover_heart__hy - selfY
  if k_squad_target__objective >= 0 and controlCaptureTeam(k_squad_target__objective) = selfTeam and c_cover_heart__dx * c_cover_heart__dx + c_cover_heart__dy * c_cover_heart__dy <= c_cover_heart__capture_sq then
    c_cover_heart__finish_capture = 1
  else
    c_cover_heart__finish_capture = 0
  end if
  if c_cover_heart__finish_capture = 0 and (c_cover_heart__dx * c_cover_heart__dx + c_cover_heart__dy * c_cover_heart__dy > c_cover_heart__step_in_sq or k_squad_target__idle_capture < c_cover_heart__idle_limit) then
    c_cover_heart__side = 1
    if k_squad_target__seat = 3 then
      c_cover_heart__side = -1
    end if
    c_cover_heart__ax = c_cover_heart__post_x - c_cover_heart__hx
    c_cover_heart__ay = c_cover_heart__post_y - c_cover_heart__hy
    if selfTeam = 0 then
      c_cover_heart__ax = c_cover_heart__ax + c_cover_heart__post_shift
    else
      c_cover_heart__ax = c_cover_heart__ax - c_cover_heart__post_shift
    end if
    sk_motor__isqrt(c_cover_heart__ax * c_cover_heart__ax + c_cover_heart__ay * c_cover_heart__ay)
    if sk_motor__root > 0 then
      c_cover_heart__goal_x = c_cover_heart__hx + (c_cover_heart__ax * 3 - c_cover_heart__ay * 2 * c_cover_heart__side) * c_cover_heart__post_radius \ sk_motor__root
      c_cover_heart__goal_y = c_cover_heart__hy + (c_cover_heart__ay * 3 + c_cover_heart__ax * 2 * c_cover_heart__side) * c_cover_heart__post_radius \ sk_motor__root
    end if
  end if
  ' Step 3.
  c_cover_heart__dx = c_cover_heart__goal_x - selfX
  c_cover_heart__dy = c_cover_heart__goal_y - selfY
  if c_cover_heart__dx * c_cover_heart__dx + c_cover_heart__dy * c_cover_heart__dy < c_cover_heart__hold_sq then
    c_cover_heart__hold = 1
  else
    c_cover_heart__hold = 0
  end if
  ' Step 4.
  if c_cover_heart__finish_capture = 1 then
    sk_motor__finish_cover_capture(c_cover_heart__hx, c_cover_heart__hy)
  else
    sk_motor__act(c_cover_heart__goal_x, c_cover_heart__goal_y, c_cover_heart__hold)
  end if
  ' Step 5: quiet approach when nothing is in sight but something was heard.
  if k_contacts__best < 0 and soundCount() > 0 then
    c_cover_heart__qx = controlX(k_squad_target__objective) - selfX
    c_cover_heart__qy = controlY(k_squad_target__objective) - selfY
    if c_cover_heart__qx * c_cover_heart__qx + c_cover_heart__qy * c_cover_heart__qy < c_cover_heart__quiet_sq then
      sneak(1)
    end if
  end if
  ' Step 6.
  end if
  c_cover_heart__status = 0
end sub
