' unit K.squad_target sha256:26554aca4446eb9ea610ec3ca9ca1ade3ba7d11028b4e5b3abef7707c0fccd75 generated, do not edit
' The heart our squad of four attacks: squad arithmetic, heart ownership and avoid memory.
DIM k_squad_target__avoid_until(63)

sub k_squad_target__update()
  ' Step 1: stall memory, using the objective of the previous tick.
  if k_squad_target__progress_period > 0 then
    if worldTick mod k_squad_target__progress_period = 0 then
      k_squad_target__px = selfX - k_squad_target__progress_x
      k_squad_target__py = selfY - k_squad_target__progress_y
      if k_squad_target__px * k_squad_target__px + k_squad_target__py * k_squad_target__py < k_squad_target__stall_sq and k_squad_target__objective >= 0 and k_squad_target__objective < 64 then
        k_squad_target__hx = controlX(k_squad_target__objective) - selfX
        k_squad_target__hy = controlY(k_squad_target__objective) - selfY
        if k_squad_target__hx * k_squad_target__hx + k_squad_target__hy * k_squad_target__hy > k_squad_target__far_sq then
          k_squad_target__avoid_until(k_squad_target__objective) = worldTick + k_squad_target__avoid_ticks
        end if
      end if
      k_squad_target__progress_x = selfX
      k_squad_target__progress_y = selfY
    end if
  end if

  ' Step 2: squad.
  k_squad_target__member = (selfId / 2) mod 8
  k_squad_target__squad = k_squad_target__member / 4
  k_squad_target__seat = k_squad_target__member mod 4

  ' Step 3: target.
  k_squad_target__objective = -1
  if heartCount() > 0 then
    k_squad_target__other = -1
    k_squad_target__pass = 0
    while k_squad_target__pass < 2
      k_squad_target__ref_y = homeY - k_squad_target__ref_offset
      if k_squad_target__pass = 1 then
        k_squad_target__ref_y = homeY + k_squad_target__ref_offset
      end if
      if selfTeam = 1 then
        k_squad_target__ref_y = k_squad_target__mirror_y - k_squad_target__ref_y
      end if
      k_squad_target__choice = -1
      k_squad_target__choice_cost = 2147483647
      k_squad_target__j = 0
      while k_squad_target__j < heartCount() and k_squad_target__j < 64
        if controlOwner(k_squad_target__j) <> selfTeam and k_squad_target__j <> k_squad_target__other then
          k_squad_target__dx = (controlX(k_squad_target__j) - homeX) / 8
          k_squad_target__dy = (controlY(k_squad_target__j) - k_squad_target__ref_y) / 8
          k_squad_target__cost = k_squad_target__dx * k_squad_target__dx + k_squad_target__dy * k_squad_target__dy
          if controlOwner(k_squad_target__j) = -1 then
            k_squad_target__cost = k_squad_target__cost - k_squad_target__neutral_bonus
          end if
          if k_squad_target__pass = k_squad_target__squad and k_squad_target__avoid_until(k_squad_target__j) > worldTick then
            k_squad_target__cost = k_squad_target__cost + k_squad_target__avoid_penalty
          end if
          if k_squad_target__cost < k_squad_target__choice_cost then
            k_squad_target__choice = k_squad_target__j
            k_squad_target__choice_cost = k_squad_target__cost
          end if
        end if
        k_squad_target__j = k_squad_target__j + 1
      wend
      if k_squad_target__pass = k_squad_target__squad then
        k_squad_target__objective = k_squad_target__choice
      else
        if k_squad_target__pass < k_squad_target__squad then
          k_squad_target__other = k_squad_target__choice
        end if
      end if
      k_squad_target__pass = k_squad_target__pass + 1
    wend
    if k_squad_target__objective < 0 and k_squad_target__other >= 0 then
      k_squad_target__objective = k_squad_target__other
    end if
  end if

  ' Step 4: idle capture (cover seats only).
  if k_squad_target__objective >= 0 and k_squad_target__seat >= 2 then
    if controlCaptureTeam(k_squad_target__objective) = selfTeam then
      k_squad_target__idle_capture = 0
    else
      k_squad_target__idle_capture = k_squad_target__idle_capture + 1
    end if
  end if
  k_squad_target__heart_count = heartCount()
end sub
