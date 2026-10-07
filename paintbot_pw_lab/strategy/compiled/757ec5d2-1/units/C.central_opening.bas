' unit C.central_opening sha256:cf46ee499ee19bd21b88c2a2eb55d5a28d7c2fb406c91b27f273d379d3ec4bbf generated, do not edit
' Assign ring and dry-bank posts around the two hearts nearest the midpoint.
sub c_central_opening__start()
end sub

sub c_central_opening__tick()
  c_central_opening__mid_x = (homeX + heartX) \ 2
  c_central_opening__mid_y = (homeY + heartY) \ 2
  c_central_opening__first = -1
  c_central_opening__second = -1
  c_central_opening__pass = 0
  while c_central_opening__pass < 2
    c_central_opening__choice = -1
    c_central_opening__choice_cost = 2147483647
    c_central_opening__j = 0
    while c_central_opening__j < heartCount() and c_central_opening__j < 64
      if c_central_opening__j <> c_central_opening__first then
        c_central_opening__dx = (controlX(c_central_opening__j) - c_central_opening__mid_x) \ 8
        c_central_opening__dy = (controlY(c_central_opening__j) - c_central_opening__mid_y) \ 8
        c_central_opening__cost = c_central_opening__dx * c_central_opening__dx + c_central_opening__dy * c_central_opening__dy
        if c_central_opening__cost < c_central_opening__choice_cost then
          c_central_opening__choice = c_central_opening__j
          c_central_opening__choice_cost = c_central_opening__cost
        end if
      end if
      c_central_opening__j = c_central_opening__j + 1
    wend
    if c_central_opening__pass = 0 then
      c_central_opening__first = c_central_opening__choice
    else
      c_central_opening__second = c_central_opening__choice
    end if
    c_central_opening__pass = c_central_opening__pass + 1
  wend

  c_central_opening__member = (selfId \ 2) mod 8
  c_central_opening__squad = c_central_opening__member \ 4
  c_central_opening__seat = c_central_opening__member mod 4
  if c_central_opening__squad = selfTeam then
    c_central_opening__objective = c_central_opening__first
  else
    c_central_opening__objective = c_central_opening__second
  end if
  c_central_opening__gx = controlX(c_central_opening__objective)
  c_central_opening__gy = controlY(c_central_opening__objective)

  if c_central_opening__seat >= 2 then
    if controlY(c_central_opening__objective) < c_central_opening__mid_y then
      c_central_opening__outward = -1
    else
      c_central_opening__outward = 1
    end if
    if homeX > c_central_opening__mid_x then
      c_central_opening__back = 1
    else
      c_central_opening__back = -1
    end if
    if c_central_opening__seat = 2 then
      c_central_opening__offset = c_central_opening__cover_back_cm
    else
      c_central_opening__offset = 0
    end if
    c_central_opening__gx = c_central_opening__gx + c_central_opening__back * c_central_opening__offset
    c_central_opening__gy = c_central_opening__gy + c_central_opening__outward * c_central_opening__bank_offset_cm
    c_central_opening__tries = 0
    while waterAt(c_central_opening__gx, c_central_opening__gy) and c_central_opening__tries < c_central_opening__dry_steps
      c_central_opening__gy = c_central_opening__gy + c_central_opening__outward * c_central_opening__dry_step_cm
      c_central_opening__tries = c_central_opening__tries + 1
    wend
    if waterAt(c_central_opening__gx, c_central_opening__gy) then
      c_central_opening__gx = controlX(c_central_opening__objective)
      c_central_opening__gy = controlY(c_central_opening__objective)
    end if
  end if

  c_central_opening__dx = c_central_opening__gx - selfX
  c_central_opening__dy = c_central_opening__gy - selfY
  if c_central_opening__dx * c_central_opening__dx + c_central_opening__dy * c_central_opening__dy <= c_central_opening__hold_sq then
    c_central_opening__hold = 1
  else
    c_central_opening__hold = 0
  end if
  sk_motor__central_opening(c_central_opening__gx, c_central_opening__gy, c_central_opening__hold)
  c_central_opening__status = 0
end sub
