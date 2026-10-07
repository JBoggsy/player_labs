' unit K.glory_hearts sha256:08ee4c2787a2b567bb0a747761cdc19f50d907b206de92f0bfbe81bf1d8f66e2 generated, do not edit
' Glory hearts we see or that teammates reported. Memory only. No rule uses it.
' Scratch cells, kept in one array to stay under the 512-global budget:
' 0 nearest_d2, 1 i, 2 left, 3 hx, 4 hy, 5 dx, 6 dy, 7 d2, 8 j, 9 dup
DIM k_glory_hearts__t(9)

sub k_glory_hearts__update()
  k_glory_hearts__count = 0
  k_glory_hearts__nearest_x = 0
  k_glory_hearts__nearest_y = 0
  k_glory_hearts__nearest_left = 0
  k_glory_hearts__t(0) = 2147483647
  ' Hearts in view.
  k_glory_hearts__t(1) = 0
  while k_glory_hearts__t(1) < gloryHeartCount() and k_glory_hearts__t(1) < 8
    k_glory_hearts__t(2) = gloryHeartTicksLeft(k_glory_hearts__t(1))
    if k_glory_hearts__t(2) >= 0 then
      k_glory_hearts__t(3) = gloryHeartX(k_glory_hearts__t(1))
      k_glory_hearts__t(4) = gloryHeartY(k_glory_hearts__t(1))
      k_glory_hearts__count = k_glory_hearts__count + 1
      k_glory_hearts__t(5) = k_glory_hearts__t(3) - selfX
      k_glory_hearts__t(6) = k_glory_hearts__t(4) - selfY
      k_glory_hearts__t(7) = k_glory_hearts__t(5) * k_glory_hearts__t(5) + k_glory_hearts__t(6) * k_glory_hearts__t(6)
      if k_glory_hearts__t(7) < k_glory_hearts__t(0) then
        k_glory_hearts__t(0) = k_glory_hearts__t(7)
        k_glory_hearts__nearest_x = k_glory_hearts__t(3)
        k_glory_hearts__nearest_y = k_glory_hearts__t(4)
        k_glory_hearts__nearest_left = k_glory_hearts__t(2)
      end if
    end if
    k_glory_hearts__t(1) = k_glory_hearts__t(1) + 1
  wend
  ' Reported hearts that no visible heart already covers.
  k_glory_hearts__t(8) = 0
  while k_glory_hearts__t(8) < 8
    if com_glory_seen__gl_until(k_glory_hearts__t(8)) > worldTick then
      k_glory_hearts__t(9) = 0
      k_glory_hearts__t(1) = 0
      while k_glory_hearts__t(1) < gloryHeartCount() and k_glory_hearts__t(1) < 8
        if gloryHeartTicksLeft(k_glory_hearts__t(1)) >= 0 then
          k_glory_hearts__t(5) = gloryHeartX(k_glory_hearts__t(1)) - com_glory_seen__gl_x(k_glory_hearts__t(8))
          k_glory_hearts__t(6) = gloryHeartY(k_glory_hearts__t(1)) - com_glory_seen__gl_y(k_glory_hearts__t(8))
          if k_glory_hearts__t(5) * k_glory_hearts__t(5) + k_glory_hearts__t(6) * k_glory_hearts__t(6) <= com_glory_seen__h_match * com_glory_seen__h_match then
            k_glory_hearts__t(9) = 1
          end if
        end if
        k_glory_hearts__t(1) = k_glory_hearts__t(1) + 1
      wend
      if k_glory_hearts__t(9) = 0 then
        k_glory_hearts__count = k_glory_hearts__count + 1
        k_glory_hearts__t(5) = com_glory_seen__gl_x(k_glory_hearts__t(8)) - selfX
        k_glory_hearts__t(6) = com_glory_seen__gl_y(k_glory_hearts__t(8)) - selfY
        k_glory_hearts__t(7) = k_glory_hearts__t(5) * k_glory_hearts__t(5) + k_glory_hearts__t(6) * k_glory_hearts__t(6)
        if k_glory_hearts__t(7) < k_glory_hearts__t(0) then
          k_glory_hearts__t(0) = k_glory_hearts__t(7)
          k_glory_hearts__nearest_x = com_glory_seen__gl_x(k_glory_hearts__t(8))
          k_glory_hearts__nearest_y = com_glory_seen__gl_y(k_glory_hearts__t(8))
          k_glory_hearts__nearest_left = com_glory_seen__gl_until(k_glory_hearts__t(8)) - worldTick
        end if
      end if
    end if
    k_glory_hearts__t(8) = k_glory_hearts__t(8) + 1
  wend
end sub
