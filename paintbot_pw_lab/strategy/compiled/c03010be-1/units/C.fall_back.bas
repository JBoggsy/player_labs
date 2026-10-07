' unit C.fall_back sha256:85f363cc3d538757e9273419a01d80e166b4aa98814a7a3c552f80d6b92eb208 generated, do not edit
' Head for the heart that is far from the enemies and near us.
' Scratch cells, kept in one array to stay under the 512-global budget:
' 0 cx, 1 cy, 2 away, 3 away_score, 4 j, 5 ex, 6 ey, 7 mx, 8 my, 9 score, 10 goal_x, 11 goal_y,
' 12 qx, 13 qy
DIM c_fall_back__t(13)

sub c_fall_back__start()
end sub

sub c_fall_back__tick()
  ' Step 1.
  c_fall_back__t(0) = k_contacts__foe_cx
  c_fall_back__t(1) = k_contacts__foe_cy
  c_fall_back__t(2) = -1
  c_fall_back__t(3) = -2147483647
  c_fall_back__t(4) = 0
  while c_fall_back__t(4) < heartCount() and c_fall_back__t(4) < 64
    c_fall_back__t(5) = (controlX(c_fall_back__t(4)) - c_fall_back__t(0)) / 16
    c_fall_back__t(6) = (controlY(c_fall_back__t(4)) - c_fall_back__t(1)) / 16
    c_fall_back__t(7) = (controlX(c_fall_back__t(4)) - selfX) / 16
    c_fall_back__t(8) = (controlY(c_fall_back__t(4)) - selfY) / 16
    c_fall_back__t(9) = c_fall_back__t(5) * c_fall_back__t(5) + c_fall_back__t(6) * c_fall_back__t(6) - (c_fall_back__t(7) * c_fall_back__t(7) + c_fall_back__t(8) * c_fall_back__t(8)) / 2
    if c_fall_back__t(9) > c_fall_back__t(3) then
      c_fall_back__t(2) = c_fall_back__t(4)
      c_fall_back__t(3) = c_fall_back__t(9)
    end if
    c_fall_back__t(4) = c_fall_back__t(4) + 1
  wend
  ' Step 2.
  if c_fall_back__t(2) >= 0 then
    c_fall_back__t(10) = controlX(c_fall_back__t(2))
    c_fall_back__t(11) = controlY(c_fall_back__t(2))
  else
    c_fall_back__t(10) = selfX
    c_fall_back__t(11) = selfY
  end if
  ' Step 3.
  sk_motor__act(c_fall_back__t(10), c_fall_back__t(11), 0)
  ' Step 4: quiet approach when nothing is in sight but something was heard.
  if k_contacts__best < 0 and soundCount() > 0 and k_squad_target__objective >= 0 then
    c_fall_back__t(12) = controlX(k_squad_target__objective) - selfX
    c_fall_back__t(13) = controlY(k_squad_target__objective) - selfY
    if c_fall_back__t(12) * c_fall_back__t(12) + c_fall_back__t(13) * c_fall_back__t(13) < c_fall_back__quiet_sq then
      sk_motor__sneak(1)
    end if
  end if
  ' Step 5.
  c_fall_back__status = 0
end sub
