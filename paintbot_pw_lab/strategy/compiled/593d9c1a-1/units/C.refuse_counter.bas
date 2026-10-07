' unit C.refuse_counter sha256:6dd1d8b7c3f3400f45b1dde14215c8726fea30524789581d49fbe235b8acec9f generated, do not edit
SUB c_refuse_counter__start()
END SUB

SUB c_refuse_counter__tick()
  c_refuse_counter__member = (selfId \ 2) MOD 8
  IF selfTeam = 0 THEN
    c_refuse_counter__forward = 1
  ELSE
    c_refuse_counter__forward = -1
  END IF
  c_refuse_counter__gx = homeX
  c_refuse_counter__gy = homeY
  c_refuse_counter__target = k_counter_phase__target
  IF k_counter_phase__phase = 1 THEN
    IF c_refuse_counter__member < 2 THEN
      c_refuse_counter__choice = -1
      c_refuse_counter__best_cost = 2147483647
      c_refuse_counter__j = 0
      WHILE c_refuse_counter__j < heartCount() AND c_refuse_counter__j < 64
        IF controlOwner(c_refuse_counter__j) <> selfTeam AND controlOwner(c_refuse_counter__j) <> 1 - selfTeam AND c_refuse_counter__forward * (controlX(c_refuse_counter__j) - homeX) <= c_refuse_counter__safe_forward_cm THEN
          c_refuse_counter__dx = controlX(c_refuse_counter__j) - selfX
          c_refuse_counter__dy = controlY(c_refuse_counter__j) - selfY
          c_refuse_counter__cost = c_refuse_counter__dx * c_refuse_counter__dx + c_refuse_counter__dy * c_refuse_counter__dy
          IF c_refuse_counter__cost < c_refuse_counter__best_cost THEN
            c_refuse_counter__choice = c_refuse_counter__j
            c_refuse_counter__best_cost = c_refuse_counter__cost
          END IF
        END IF
        c_refuse_counter__j = c_refuse_counter__j + 1
      WEND
      IF c_refuse_counter__choice >= 0 THEN
        c_refuse_counter__gx = controlX(c_refuse_counter__choice)
        c_refuse_counter__gy = controlY(c_refuse_counter__choice)
      END IF
    ELSE
      c_refuse_counter__post = c_refuse_counter__member - 2
      c_refuse_counter__row = c_refuse_counter__post \ 3
      c_refuse_counter__lane = c_refuse_counter__post MOD 3 - 1
      c_refuse_counter__gx = homeX + c_refuse_counter__forward * (c_refuse_counter__stage_forward_cm + c_refuse_counter__row * c_refuse_counter__row_gap_cm)
      c_refuse_counter__gy = homeY + c_refuse_counter__lane * c_refuse_counter__lane_gap_cm
      c_refuse_counter__tries = 0
      WHILE waterAt(c_refuse_counter__gx, c_refuse_counter__gy) AND c_refuse_counter__tries < c_refuse_counter__dry_steps
        c_refuse_counter__gx = c_refuse_counter__gx - c_refuse_counter__forward * c_refuse_counter__dry_step_cm
        c_refuse_counter__tries = c_refuse_counter__tries + 1
      WEND
      IF waterAt(c_refuse_counter__gx, c_refuse_counter__gy) THEN
        c_refuse_counter__gx = homeX
      END IF
    END IF
  END IF
  IF k_counter_phase__phase = 2 THEN
    IF c_refuse_counter__member < 2 THEN
      c_refuse_counter__gx = controlX(c_refuse_counter__target)
      c_refuse_counter__gy = controlY(c_refuse_counter__target)
    ELSE
      c_refuse_counter__post = c_refuse_counter__member - 2
      c_refuse_counter__row = c_refuse_counter__post \ 3
      c_refuse_counter__lane = c_refuse_counter__post MOD 3 - 1
      c_refuse_counter__gx = controlX(c_refuse_counter__target) - c_refuse_counter__forward * (c_refuse_counter__counter_back_cm + c_refuse_counter__row * c_refuse_counter__row_gap_cm)
      c_refuse_counter__gy = controlY(c_refuse_counter__target) + c_refuse_counter__lane * c_refuse_counter__lane_gap_cm
      c_refuse_counter__tries = 0
      WHILE waterAt(c_refuse_counter__gx, c_refuse_counter__gy) AND c_refuse_counter__tries < c_refuse_counter__dry_steps
        c_refuse_counter__gx = c_refuse_counter__gx - c_refuse_counter__forward * c_refuse_counter__dry_step_cm
        c_refuse_counter__tries = c_refuse_counter__tries + 1
      WEND
      IF waterAt(c_refuse_counter__gx, c_refuse_counter__gy) THEN
        c_refuse_counter__gx = homeX
        c_refuse_counter__gy = homeY + c_refuse_counter__lane * c_refuse_counter__lane_gap_cm
      END IF
    END IF
  END IF
  c_refuse_counter__dx = c_refuse_counter__gx - selfX
  c_refuse_counter__dy = c_refuse_counter__gy - selfY
  IF c_refuse_counter__dx * c_refuse_counter__dx + c_refuse_counter__dy * c_refuse_counter__dy <= c_refuse_counter__hold_sq THEN
    c_refuse_counter__hold = 1
  ELSE
    c_refuse_counter__hold = 0
  END IF
  sk_motor__central_opening(c_refuse_counter__gx, c_refuse_counter__gy, c_refuse_counter__hold)
  c_refuse_counter__status = 0
END SUB
