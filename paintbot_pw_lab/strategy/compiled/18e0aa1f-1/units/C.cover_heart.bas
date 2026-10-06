' unit C.cover_heart sha256:6b97e602537eb6cb71487e0c9f9be9d7bb2e6fffe5eb82f86b5dcc027fd48509 generated, do not edit
' Cover the squad target from outside the ring, and step in when nobody captures it
' (squad seats 2 and 3).
' Scratch cells, kept in one array to stay under the 512-global budget:
' 0 hx, 1 hy, 2 goal_x, 3 goal_y, 4 dx, 5 dy, 6 side, 7 ax, 8 ay, 9 hold, 10 qx, 11 qy
DIM c_cover_heart__t(11)

sub c_cover_heart__start()
end sub

sub c_cover_heart__tick()
  ' Step 1.
  c_cover_heart__t(0) = controlX(k_squad_target__objective)
  c_cover_heart__t(1) = controlY(k_squad_target__objective)
  c_cover_heart__t(2) = c_cover_heart__t(0)
  c_cover_heart__t(3) = c_cover_heart__t(1)
  ' Step 2: the cover post, unless we are close and nobody has captured for a while.
  c_cover_heart__t(4) = c_cover_heart__t(0) - selfX
  c_cover_heart__t(5) = c_cover_heart__t(1) - selfY
  if c_cover_heart__t(4) * c_cover_heart__t(4) + c_cover_heart__t(5) * c_cover_heart__t(5) > c_cover_heart__step_in_sq or k_squad_target__idle_capture < c_cover_heart__idle_limit then
    c_cover_heart__t(6) = 1
    if k_squad_target__seat = 3 then
      c_cover_heart__t(6) = -1
    end if
    c_cover_heart__t(7) = c_cover_heart__post_x - c_cover_heart__t(0)
    c_cover_heart__t(8) = c_cover_heart__post_y - c_cover_heart__t(1)
    if selfTeam = 0 then
      c_cover_heart__t(7) = c_cover_heart__t(7) + c_cover_heart__post_shift
    else
      c_cover_heart__t(7) = c_cover_heart__t(7) - c_cover_heart__post_shift
    end if
    sk_motor__isqrt(c_cover_heart__t(7) * c_cover_heart__t(7) + c_cover_heart__t(8) * c_cover_heart__t(8))
    if sk_motor__root > 0 then
      c_cover_heart__t(2) = c_cover_heart__t(0) + (c_cover_heart__t(7) * 3 - c_cover_heart__t(8) * 2 * c_cover_heart__t(6)) * c_cover_heart__post_radius / sk_motor__root
      c_cover_heart__t(3) = c_cover_heart__t(1) + (c_cover_heart__t(8) * 3 + c_cover_heart__t(7) * 2 * c_cover_heart__t(6)) * c_cover_heart__post_radius / sk_motor__root
    end if
  end if
  ' Step 3.
  c_cover_heart__t(4) = c_cover_heart__t(2) - selfX
  c_cover_heart__t(5) = c_cover_heart__t(3) - selfY
  if c_cover_heart__t(4) * c_cover_heart__t(4) + c_cover_heart__t(5) * c_cover_heart__t(5) < c_cover_heart__hold_sq then
    c_cover_heart__t(9) = 1
  else
    c_cover_heart__t(9) = 0
  end if
  ' Step 4.
  sk_motor__act(c_cover_heart__t(2), c_cover_heart__t(3), c_cover_heart__t(9))
  ' Step 5: quiet approach when nothing is in sight but something was heard.
  if k_contacts__best < 0 and soundCount() > 0 then
    c_cover_heart__t(10) = controlX(k_squad_target__objective) - selfX
    c_cover_heart__t(11) = controlY(k_squad_target__objective) - selfY
    if c_cover_heart__t(10) * c_cover_heart__t(10) + c_cover_heart__t(11) * c_cover_heart__t(11) < c_cover_heart__quiet_sq then
      sk_motor__sneak(1)
    end if
  end if
  ' Step 6.
  c_cover_heart__status = 0
end sub
