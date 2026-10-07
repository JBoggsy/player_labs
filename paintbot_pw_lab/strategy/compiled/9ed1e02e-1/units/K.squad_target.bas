' unit K.squad_target sha256:54d9f109c6a7fb4b205395debc699a3f4a186d347865350ab84fbfe9a09599e0 generated, do not edit
' Four pairs select distinct frontier hearts from visible pair anchors.
DIM k_squad_target__avoid_until(63)
DIM k_squad_target__assigned(3)

sub k_squad_target__update()
  k_squad_target__previous_objective = k_squad_target__objective
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
  k_squad_target__member = (selfId \ 2) mod 8
  k_squad_target__squad = k_squad_target__member \ 4
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
          k_squad_target__dx = (controlX(k_squad_target__j) - homeX) \ 8
          k_squad_target__dy = (controlY(k_squad_target__j) - k_squad_target__ref_y) \ 8
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

  ' Step 3b: the legacy choice is only a same-tick telemetry reference.
  k_squad_target__legacy_objective = k_squad_target__objective
  k_squad_target__squad = k_squad_target__member \ 2
  k_squad_target__seat = (k_squad_target__member mod 2) * 2
  k_squad_target__k = 0
  while k_squad_target__k < 4
    k_squad_target__assigned(k_squad_target__k) = -1
    k_squad_target__k = k_squad_target__k + 1
  wend
  if heartCount() > 0 then
    k_squad_target__pass = 0
    while k_squad_target__pass < 4
      k_squad_target__ref_x = homeX
      k_squad_target__ref_y = homeY + (k_squad_target__pass * 2 - 3) * k_squad_target__pair_lane_offset
      if selfTeam = 1 then
        k_squad_target__ref_y = k_squad_target__mirror_y - k_squad_target__ref_y
      end if
      k_squad_target__leader = k_squad_target__pass * 4 + selfTeam
      k_squad_target__escort = k_squad_target__leader + 2
      if selfId = k_squad_target__leader then
        k_squad_target__ref_x = selfX
        k_squad_target__ref_y = selfY
      else
        if visible(k_squad_target__leader) then
          k_squad_target__ref_x = playerX(k_squad_target__leader)
          k_squad_target__ref_y = playerY(k_squad_target__leader)
        else
          if selfId = k_squad_target__escort then
            k_squad_target__ref_x = selfX
            k_squad_target__ref_y = selfY
          else
            if visible(k_squad_target__escort) then
              k_squad_target__ref_x = playerX(k_squad_target__escort)
              k_squad_target__ref_y = playerY(k_squad_target__escort)
            end if
          end if
        end if
      end if
      k_squad_target__choice = -1
      k_squad_target__choice_cost = 2147483647
      k_squad_target__j = 0
      while k_squad_target__j < heartCount() and k_squad_target__j < 64
        if controlOwner(k_squad_target__j) <> selfTeam then
          k_squad_target__used = 0
          k_squad_target__k = 0
          while k_squad_target__k < 4 and k_squad_target__k < k_squad_target__pass
            if k_squad_target__assigned(k_squad_target__k) = k_squad_target__j then
              k_squad_target__used = 1
            end if
            k_squad_target__k = k_squad_target__k + 1
          wend
          if k_squad_target__used = 0 then
            k_squad_target__dx = (controlX(k_squad_target__j) - k_squad_target__ref_x) \ 8
            k_squad_target__dy = (controlY(k_squad_target__j) - k_squad_target__ref_y) \ 8
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
        end if
        k_squad_target__j = k_squad_target__j + 1
      wend
      k_squad_target__assigned(k_squad_target__pass) = k_squad_target__choice
      k_squad_target__pass = k_squad_target__pass + 1
    wend
    k_squad_target__objective = k_squad_target__assigned(k_squad_target__squad)
    k_squad_target__k = 0
    while k_squad_target__k < 4
      if k_squad_target__objective < 0 then
        if k_squad_target__assigned(k_squad_target__k) >= 0 then
          k_squad_target__objective = k_squad_target__assigned(k_squad_target__k)
        end if
      end if
      k_squad_target__k = k_squad_target__k + 1
    wend
    if k_squad_target__previous_objective >= 0 and k_squad_target__previous_objective < heartCount() and k_squad_target__previous_objective < 64 then
      if controlOwner(k_squad_target__previous_objective) <> selfTeam and controlCaptureTeam(k_squad_target__previous_objective) = selfTeam then
        k_squad_target__hx = controlX(k_squad_target__previous_objective) - selfX
        k_squad_target__hy = controlY(k_squad_target__previous_objective) - selfY
        if k_squad_target__hx * k_squad_target__hx + k_squad_target__hy * k_squad_target__hy <= k_squad_target__capture_lock_sq then
          k_squad_target__objective = k_squad_target__previous_objective
        end if
      end if
    end if
    if k_squad_target__objective >= 0 and k_squad_target__objective <> k_squad_target__legacy_objective then
      k_squad_target__frontier_changed_total = k_squad_target__frontier_changed_total + 1
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
