' unit COM.glory_seen sha256:b50a10ce1b5d715719f51433366239be4c600091f1ca83125b92592903c038e5 generated, do not edit
' Report glory hearts we see, and keep teammates' reports.
DIM com_glory_seen__hs_x(7)
DIM com_glory_seen__hs_y(7)
DIM com_glory_seen__hs_t(7)
' Scratch cells, kept in one array to stay under the 512-global budget:
' 0 m2, 1 pick, 2 i, 3 hx, 4 hy, 5 skip, 6 j, 7 dx, 8 dy, 9 px, 10 py, 11 left, 12 w, 13 h,
' 14 gx, 15 gy, 16 cell, 17 k, 18 old, 19 old_t
DIM com_glory_seen__t(19)

sub com_glory_seen__send()
  com_glory_seen__t(0) = com_glory_seen__h_match * com_glory_seen__h_match
  com_glory_seen__t(1) = -1
  com_glory_seen__t(2) = 0
  while com_glory_seen__t(2) < gloryHeartCount() and com_glory_seen__t(2) < 8
    if com_glory_seen__t(1) < 0 and gloryHeartTicksLeft(com_glory_seen__t(2)) >= 0 then
      com_glory_seen__t(3) = gloryHeartX(com_glory_seen__t(2))
      com_glory_seen__t(4) = gloryHeartY(com_glory_seen__t(2))
      com_glory_seen__t(5) = 0
      com_glory_seen__t(6) = 0
      while com_glory_seen__t(6) < 8
        ' A teammate reported it recently.
        if com_glory_seen__gl_until(com_glory_seen__t(6)) > worldTick and worldTick - com_glory_seen__gl_t(com_glory_seen__t(6)) < com_glory_seen__h_refresh then
          com_glory_seen__t(7) = com_glory_seen__t(3) - com_glory_seen__gl_x(com_glory_seen__t(6))
          com_glory_seen__t(8) = com_glory_seen__t(4) - com_glory_seen__gl_y(com_glory_seen__t(6))
          if com_glory_seen__t(7) * com_glory_seen__t(7) + com_glory_seen__t(8) * com_glory_seen__t(8) <= com_glory_seen__t(0) then
            com_glory_seen__t(5) = 1
          end if
        end if
        ' We reported it recently.
        if com_glory_seen__hs_t(com_glory_seen__t(6)) > 0 and worldTick + 1 - com_glory_seen__hs_t(com_glory_seen__t(6)) < com_glory_seen__h_refresh then
          com_glory_seen__t(7) = com_glory_seen__t(3) - com_glory_seen__hs_x(com_glory_seen__t(6))
          com_glory_seen__t(8) = com_glory_seen__t(4) - com_glory_seen__hs_y(com_glory_seen__t(6))
          if com_glory_seen__t(7) * com_glory_seen__t(7) + com_glory_seen__t(8) * com_glory_seen__t(8) <= com_glory_seen__t(0) then
            com_glory_seen__t(5) = 1
          end if
        end if
        com_glory_seen__t(6) = com_glory_seen__t(6) + 1
      wend
      if com_glory_seen__t(5) = 0 then
        com_glory_seen__t(1) = com_glory_seen__t(2)
        com_glory_seen__t(9) = com_glory_seen__t(3)
        com_glory_seen__t(10) = com_glory_seen__t(4)
        com_glory_seen__t(11) = gloryHeartTicksLeft(com_glory_seen__t(2))
      end if
    end if
    com_glory_seen__t(2) = com_glory_seen__t(2) + 1
  wend
  if com_glory_seen__t(1) >= 0 then
    if com_glory_seen__t(11) < 0 then
      com_glory_seen__t(11) = 0
    end if
    if com_glory_seen__t(11) > 720 then
      com_glory_seen__t(11) = 720
    end if
    ' Cell of the heart.
    com_glory_seen__t(12) = mapMaxX() - mapMinX() + 1
    com_glory_seen__t(13) = mapMaxY() - mapMinY() + 1
    com_glory_seen__t(14) = 0
    com_glory_seen__t(15) = 0
    if com_glory_seen__t(12) > 0 then
      com_glory_seen__t(14) = (com_glory_seen__t(9) - mapMinX()) * 256 / com_glory_seen__t(12)
    end if
    if com_glory_seen__t(13) > 0 then
      com_glory_seen__t(15) = (com_glory_seen__t(10) - mapMinY()) * 256 / com_glory_seen__t(13)
    end if
    if com_glory_seen__t(14) < 0 then
      com_glory_seen__t(14) = 0
    end if
    if com_glory_seen__t(14) > 255 then
      com_glory_seen__t(14) = 255
    end if
    if com_glory_seen__t(15) < 0 then
      com_glory_seen__t(15) = 0
    end if
    if com_glory_seen__t(15) > 255 then
      com_glory_seen__t(15) = 255
    end if
    com_glory_seen__t(16) = com_glory_seen__t(14) + 256 * com_glory_seen__t(15)
    cm__send(4, com_glory_seen__t(11), 0, com_glory_seen__t(16), sk_motor__quiet)
    if cm__sent = 1 then
      ' Our slot for this heart, else the oldest slot.
      com_glory_seen__t(17) = -1
      com_glory_seen__t(18) = 0
      com_glory_seen__t(19) = 2147483647
      com_glory_seen__t(6) = 0
      while com_glory_seen__t(6) < 8
        com_glory_seen__t(7) = com_glory_seen__t(9) - com_glory_seen__hs_x(com_glory_seen__t(6))
        com_glory_seen__t(8) = com_glory_seen__t(10) - com_glory_seen__hs_y(com_glory_seen__t(6))
        if com_glory_seen__t(17) < 0 and com_glory_seen__hs_t(com_glory_seen__t(6)) > 0 and com_glory_seen__t(7) * com_glory_seen__t(7) + com_glory_seen__t(8) * com_glory_seen__t(8) <= com_glory_seen__t(0) then
          com_glory_seen__t(17) = com_glory_seen__t(6)
        end if
        if com_glory_seen__hs_t(com_glory_seen__t(6)) < com_glory_seen__t(19) then
          com_glory_seen__t(18) = com_glory_seen__t(6)
          com_glory_seen__t(19) = com_glory_seen__hs_t(com_glory_seen__t(6))
        end if
        com_glory_seen__t(6) = com_glory_seen__t(6) + 1
      wend
      if com_glory_seen__t(17) < 0 then
        com_glory_seen__t(17) = com_glory_seen__t(18)
      end if
      com_glory_seen__hs_x(com_glory_seen__t(17)) = com_glory_seen__t(9)
      com_glory_seen__hs_y(com_glory_seen__t(17)) = com_glory_seen__t(10)
      com_glory_seen__hs_t(com_glory_seen__t(17)) = worldTick + 1
    end if
  end if
end sub

sub com_glory_seen__recv()
  ' Point of the cell.
  com_glory_seen__t(12) = mapMaxX() - mapMinX() + 1
  com_glory_seen__t(13) = mapMaxY() - mapMinY() + 1
  com_glory_seen__t(14) = cm__cell mod 256
  com_glory_seen__t(15) = cm__cell / 256
  com_glory_seen__t(9) = mapMinX() + (com_glory_seen__t(14) * com_glory_seen__t(12) + com_glory_seen__t(12) / 2) / 256
  com_glory_seen__t(10) = mapMinY() + (com_glory_seen__t(15) * com_glory_seen__t(13) + com_glory_seen__t(13) / 2) / 256
  ' The slot already holding this heart, else the one that expires first.
  com_glory_seen__t(0) = com_glory_seen__h_match * com_glory_seen__h_match
  com_glory_seen__t(17) = -1
  com_glory_seen__t(18) = 0
  com_glory_seen__t(19) = 2147483647
  com_glory_seen__t(6) = 0
  while com_glory_seen__t(6) < 8
    com_glory_seen__t(7) = com_glory_seen__t(9) - com_glory_seen__gl_x(com_glory_seen__t(6))
    com_glory_seen__t(8) = com_glory_seen__t(10) - com_glory_seen__gl_y(com_glory_seen__t(6))
    if com_glory_seen__t(17) < 0 and com_glory_seen__gl_until(com_glory_seen__t(6)) > 0 and com_glory_seen__t(7) * com_glory_seen__t(7) + com_glory_seen__t(8) * com_glory_seen__t(8) <= com_glory_seen__t(0) then
      com_glory_seen__t(17) = com_glory_seen__t(6)
    end if
    if com_glory_seen__gl_until(com_glory_seen__t(6)) < com_glory_seen__t(19) then
      com_glory_seen__t(18) = com_glory_seen__t(6)
      com_glory_seen__t(19) = com_glory_seen__gl_until(com_glory_seen__t(6))
    end if
    com_glory_seen__t(6) = com_glory_seen__t(6) + 1
  wend
  if com_glory_seen__t(17) < 0 then
    com_glory_seen__t(17) = com_glory_seen__t(18)
  end if
  com_glory_seen__gl_x(com_glory_seen__t(17)) = com_glory_seen__t(9)
  com_glory_seen__gl_y(com_glory_seen__t(17)) = com_glory_seen__t(10)
  com_glory_seen__gl_t(com_glory_seen__t(17)) = worldTick
  com_glory_seen__gl_until(com_glory_seen__t(17)) = worldTick - 1 + cm__fa
end sub
