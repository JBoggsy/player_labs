' SK.motor: foundation mechanics with persistent grenade charging (authored source).
' Taken from reference/base.bas with every name moved into the sk_motor__ namespace and the
' integer arithmetic: integer square root, wet-line sampling, footwork
' legs, dry routing, the gun with lead and drift cancel, and the grenade charge. The goal, the
' holding flag and the quiet approach are decided by the calling capability, not here.
' Call order per tick: a capability calls sk_motor__act exactly once, on every tick.
DIM sk_motor__dr_f(5)

SUB sk_motor__init()
  ' Detour offsets beside a wet route, as tenths of the route's length (see dry route below).
  sk_motor__dr_f(0) = -10
  sk_motor__dr_f(1) = -6
  sk_motor__dr_f(2) = -3
  sk_motor__dr_f(3) = 3
  sk_motor__dr_f(4) = 6
  sk_motor__dr_f(5) = 10
  sk_motor__rng = selfId * 4099 + 977
  sk_motor__zig = 1
  IF selfId MOD 4 >= 2 THEN
    sk_motor__zig = -1
  END IF
END SUB

' Integer square root by Newton's method from above, into sk_motor__root.
' 23170^2 exceeds any squared map distance.
SUB sk_motor__isqrt(sk_motor_n)
  sk_motor__root = 0
  IF sk_motor_n <= 0 THEN
    EXIT SUB
  END IF
  sk_motor__root = 23170
  sk_motor__guess = (sk_motor__root + sk_motor_n \ sk_motor__root) \ 2
  sk_motor__iters = 0
  WHILE sk_motor__guess < sk_motor__root AND sk_motor__iters < 24
    sk_motor__root = sk_motor__guess
    sk_motor__guess = (sk_motor__root + sk_motor_n \ sk_motor__root) \ 2
    sk_motor__iters = sk_motor__iters + 1
  WEND
END SUB

' How much of the straight line between two points is under water, in ten samples: into sk_motor__wet.
SUB sk_motor__wet_line(sk_motor_ax, sk_motor_ay, sk_motor_bx, sk_motor_by)
  sk_motor__wet = 0
  sk_motor__s3 = 1
  WHILE sk_motor__s3 <= 10
    IF waterAt(sk_motor_ax + (sk_motor_bx - sk_motor_ax) * sk_motor__s3 \ 10, sk_motor_ay + (sk_motor_by - sk_motor_ay) * sk_motor__s3 \ 10) THEN
      sk_motor__wet = sk_motor__wet + 1
    END IF
    sk_motor__s3 = sk_motor__s3 + 1
  WEND
END SUB

' Time to walk a leg, in metres of dry walking: a wet metre costs wet_cost dry ones. Into sk_motor__leg_cost.
SUB sk_motor__leg_time(sk_motor_ax, sk_motor_ay, sk_motor_bx, sk_motor_by)
  sk_motor__wet_line(sk_motor_ax, sk_motor_ay, sk_motor_bx, sk_motor_by)
  sk_motor__isqrt((sk_motor_bx - sk_motor_ax) * (sk_motor_bx - sk_motor_ax) + (sk_motor_by - sk_motor_ay) * (sk_motor_by - sk_motor_ay))
  sk_motor__leg_cost = sk_motor__root \ 100 + sk_motor__root \ 100 * sk_motor__wet * (sk_motor__wet_cost - 1) \ 10
END SUB

' Small linear congruential generator; every product stays far inside int32.
SUB sk_motor__next_random()
  sk_motor__rng = (sk_motor__rng * 75 + 74) MOD 65537
END SUB

' Pick the next dodge leg: mostly reverse across the line to the threat, keep some progress
' toward the goal, and hold the leg for leg_ticks so a shot that starts now flies true.
SUB sk_motor__plan_leg(sk_motor_min, sk_motor_max)
  sk_motor__next_random()
  IF sk_motor__rng MOD 5 <> 0 THEN
    sk_motor__zig = 0 - sk_motor__zig
  END IF
  IF sk_motor__zig = 0 THEN
    sk_motor__zig = 1
  END IF
  sk_motor__next_random()
  sk_motor__leg_ticks = sk_motor_min + sk_motor__rng MOD (sk_motor_max - sk_motor_min + 1)
  sk_motor__tx = sk_motor__threat_x - selfX
  sk_motor__ty = sk_motor__threat_y - selfY
  sk_motor__isqrt(sk_motor__tx * sk_motor__tx + sk_motor__ty * sk_motor__ty)
  sk_motor__leg_x = 0
  sk_motor__leg_y = 0
  IF sk_motor__root > 0 THEN
    ' Perpendicular to the threat, scaled to 100.
    sk_motor__leg_x = (0 - sk_motor__ty) * 100 * sk_motor__zig \ sk_motor__root
    sk_motor__leg_y = sk_motor__tx * 100 * sk_motor__zig \ sk_motor__root
  END IF
  IF sk_motor__holding = 0 THEN
    sk_motor__fx = sk_motor__goal_x - selfX
    sk_motor__fy = sk_motor__goal_y - selfY
    sk_motor__isqrt(sk_motor__fx * sk_motor__fx + sk_motor__fy * sk_motor__fy)
    IF sk_motor__root > 60 THEN
      sk_motor__leg_x = sk_motor__leg_x * 3 \ 4 + sk_motor__fx * 100 \ sk_motor__root
      sk_motor__leg_y = sk_motor__leg_y * 3 \ 4 + sk_motor__fy * 100 \ sk_motor__root
    END IF
  END IF
  sk_motor__isqrt(sk_motor__leg_x * sk_motor__leg_x + sk_motor__leg_y * sk_motor__leg_y)
  IF sk_motor__root > 0 THEN
    sk_motor__leg_x = sk_motor__leg_x * 28 \ sk_motor__root
    sk_motor__leg_y = sk_motor__leg_y * 28 \ sk_motor__root
  END IF
END SUB

' Facing with nothing to shoot: sweep, then turn to speech and sound.
SUB sk_motor__look_around()
  sk_motor__scan = (worldTick \ 24 + selfId) MOD 4
  sk_motor__look_x = sk_motor__goal_x
  sk_motor__look_y = sk_motor__goal_y
  IF sk_motor__holding OR sk_motor__scan = 1 THEN
    ' Sweep toward the enemy side first; blue's sweep is the half turn of red's.
    sk_motor__facing = 1 - 2 * selfTeam
    sk_motor__look_x = selfX + 2000 * sk_motor__facing
    sk_motor__look_y = selfY
    IF sk_motor__scan = 1 THEN
      sk_motor__look_x = selfX
      sk_motor__look_y = selfY + 2000 * sk_motor__facing
    END IF
    IF sk_motor__scan = 2 THEN
      sk_motor__look_x = selfX - 2000 * sk_motor__facing
    END IF
    IF sk_motor__scan = 3 THEN
      sk_motor__look_x = selfX
      sk_motor__look_y = selfY - 2000 * sk_motor__facing
    END IF
  END IF
  IF heardCount() > 0 THEN
    sk_motor__look_x = heardX(0)
    sk_motor__look_y = heardY(0)
  END IF
  IF soundCount() > 0 THEN
    sk_motor__sound_best = -1
    sk_motor__sound_cost = 2147483647
    sk_motor__j = 0
    WHILE sk_motor__j < soundCount() AND sk_motor__j < 12
      sk_motor__cost = soundAge(sk_motor__j)
      IF soundKind(sk_motor__j) = 1 OR soundKind(sk_motor__j) = 2 THEN
        sk_motor__cost = sk_motor__cost - 48
      END IF
      IF sk_motor__cost < sk_motor__sound_cost THEN
        sk_motor__sound_best = sk_motor__j
        sk_motor__sound_cost = sk_motor__cost
      END IF
      sk_motor__j = sk_motor__j + 1
    WEND
    IF sk_motor__sound_best >= 0 THEN
      sk_motor__bearing = soundDirection(sk_motor__sound_best)
      sk_motor__dx_sound = 0
      sk_motor__dy_sound = 0
      IF sk_motor__bearing = 0 OR sk_motor__bearing = 1 OR sk_motor__bearing = 7 THEN
        sk_motor__dx_sound = 1000
      END IF
      IF sk_motor__bearing = 3 OR sk_motor__bearing = 4 OR sk_motor__bearing = 5 THEN
        sk_motor__dx_sound = -1000
      END IF
      IF sk_motor__bearing = 1 OR sk_motor__bearing = 2 OR sk_motor__bearing = 3 THEN
        sk_motor__dy_sound = 1000
      END IF
      IF sk_motor__bearing = 5 OR sk_motor__bearing = 6 OR sk_motor__bearing = 7 THEN
        sk_motor__dy_sound = -1000
      END IF
      sk_motor__look_x = selfX + sk_motor__dx_sound
      sk_motor__look_y = selfY + sk_motor__dy_sound
    END IF
  END IF
  lookAt(sk_motor__look_x, sk_motor__look_y)
END SUB

' Footwork. In contact, move in short random legs across the line to the threat. When pathing
' is inactive and a shot is wanted, replace a leg with fewer than six ticks remaining.
' Sets sk_motor__move_x/_y and sk_motor__in_contact.
SUB sk_motor__footwork()
  sk_motor__move_x = sk_motor__goal_x
  sk_motor__move_y = sk_motor__goal_y
  sk_motor__in_contact = k_contacts__best >= 0 AND trenchId < 0
  IF sk_motor__in_contact THEN
    sk_motor__threat_x = playerX(k_contacts__best)
    sk_motor__threat_y = playerY(k_contacts__best)
    ' Blocked for three ticks: let the engine's pathing take over for a second.
    IF sk_motor__leg_ticks > 0 AND k_self_motion__vx * k_self_motion__vx + k_self_motion__vy * k_self_motion__vy < 64 THEN
      sk_motor__stalled = sk_motor__stalled + 1
    ELSE
      sk_motor__stalled = 0
    END IF
    IF sk_motor__stalled >= 3 THEN
      sk_motor__path_until = worldTick + 24
      sk_motor__stalled = 0
      sk_motor__leg_ticks = 0
    END IF
    sk_motor__want_shot = sk_motor__gun_wait = 0 AND (hasSpray = 0 OR sk_motor__spray_distance_sq < sk_motor__spray_range_sq)
    IF worldTick >= sk_motor__path_until THEN
      IF sk_motor__leg_ticks <= 0 OR (sk_motor__want_shot AND sk_motor__leg_ticks < 6) THEN
        IF sk_motor__want_shot THEN
          sk_motor__plan_leg(6, 9)
        ELSE
          sk_motor__plan_leg(3, 6)
        END IF
      END IF
      sk_motor__leg_ticks = sk_motor__leg_ticks - 1
      sk_motor__move_x = selfX + sk_motor__leg_x * 4
      sk_motor__move_y = selfY + sk_motor__leg_y * 4
      IF sk_motor__holding THEN
        ' Stay inside the ring: turn back toward its centre when the leg would leave it.
        sk_motor__dx = selfX + sk_motor__leg_x * 2 - sk_motor__goal_x
        sk_motor__dy = selfY + sk_motor__leg_y * 2 - sk_motor__goal_y
        IF sk_motor__dx * sk_motor__dx + sk_motor__dy * sk_motor__dy > 9000 THEN
          sk_motor__move_x = sk_motor__goal_x
          sk_motor__move_y = sk_motor__goal_y
          sk_motor__leg_ticks = 0
        END IF
      END IF
    END IF
  ELSE
    sk_motor__leg_ticks = 0
    sk_motor__stalled = 0
  END IF
END SUB

' Dry route. The navigator walks straight at any goal no wall blocks, and water blocks nothing,
' so an objective across the lake is reached by wading at a quarter speed. When the straight way
' to a target more than 8 m off crosses water, walk first to whichever of six points beside the
' route is quickest to go through, a wet metre costing wet_cost dry ones, and keep that point
' until it is reached, the target moves 10 m, or ten seconds pass. Issues the one walkTo.
SUB sk_motor__dry_route()
  sk_motor__dr_walk = 0
  sk_motor__dr_tx = sk_motor__move_x
  sk_motor__dr_ty = sk_motor__move_y
  sk_motor__dr_dx = sk_motor__dr_tx - selfX
  sk_motor__dr_dy = sk_motor__dr_ty - selfY
  IF sk_motor__dr_dx * sk_motor__dr_dx + sk_motor__dr_dy * sk_motor__dr_dy > 640000 THEN
    IF sk_motor__dr_active THEN
      sk_motor__dr_ex = sk_motor__dr_tx - sk_motor__dr_gx
      sk_motor__dr_ey = sk_motor__dr_ty - sk_motor__dr_gy
      IF sk_motor__dr_ex * sk_motor__dr_ex + sk_motor__dr_ey * sk_motor__dr_ey > 1000000 THEN
        sk_motor__dr_active = 0
      END IF
      sk_motor__dr_ex = sk_motor__dr_wx - selfX
      sk_motor__dr_ey = sk_motor__dr_wy - selfY
      IF sk_motor__dr_ex * sk_motor__dr_ex + sk_motor__dr_ey * sk_motor__dr_ey < 90000 THEN
        sk_motor__dr_active = 0
      END IF
      IF worldTick - sk_motor__dr_tick > 240 THEN
        sk_motor__dr_active = 0
      END IF
    END IF
    IF sk_motor__dr_active = 0 AND worldTick - sk_motor__dr_tick >= 12 THEN
      sk_motor__dr_tick = worldTick
      sk_motor__leg_time(selfX, selfY, sk_motor__dr_tx, sk_motor__dr_ty)
      IF sk_motor__wet > 0 THEN
        sk_motor__dr_best = sk_motor__leg_cost
        sk_motor__dr_best_k = -1
        sk_motor__dr_mx = selfX + sk_motor__dr_dx \ 2
        sk_motor__dr_my = selfY + sk_motor__dr_dy \ 2
        sk_motor__dr_k = 0
        WHILE sk_motor__dr_k < 6
          sk_motor__dr_cx = sk_motor__dr_mx - sk_motor__dr_dy * sk_motor__dr_f(sk_motor__dr_k) \ 10
          sk_motor__dr_cy = sk_motor__dr_my + sk_motor__dr_dx * sk_motor__dr_f(sk_motor__dr_k) \ 10
          IF sk_motor__dr_cx > mapMinX() + 200 AND sk_motor__dr_cx < mapMaxX() - 200 AND sk_motor__dr_cy > mapMinY() + 200 AND sk_motor__dr_cy < mapMaxY() - 200 THEN
            IF waterAt(sk_motor__dr_cx, sk_motor__dr_cy) = 0 THEN
              sk_motor__leg_time(selfX, selfY, sk_motor__dr_cx, sk_motor__dr_cy)
              sk_motor__dr_sc = sk_motor__leg_cost
              sk_motor__leg_time(sk_motor__dr_cx, sk_motor__dr_cy, sk_motor__dr_tx, sk_motor__dr_ty)
              sk_motor__dr_sc = sk_motor__dr_sc + sk_motor__leg_cost
              IF sk_motor__dr_sc < sk_motor__dr_best THEN
                sk_motor__dr_best = sk_motor__dr_sc
                sk_motor__dr_best_k = sk_motor__dr_k
                sk_motor__dr_wx = sk_motor__dr_cx
                sk_motor__dr_wy = sk_motor__dr_cy
              END IF
            END IF
          END IF
          sk_motor__dr_k = sk_motor__dr_k + 1
        WEND
        IF sk_motor__dr_best_k >= 0 THEN
          sk_motor__dr_active = 1
          sk_motor__dr_gx = sk_motor__dr_tx
          sk_motor__dr_gy = sk_motor__dr_ty
        END IF
      END IF
    END IF
    IF sk_motor__dr_active THEN
      sk_motor__dr_walk = 1
    END IF
  END IF
  IF sk_motor__dr_walk THEN
    walkTo(sk_motor__dr_wx, sk_motor__dr_wy)
  ELSE
    walkTo(sk_motor__move_x, sk_motor__move_y)
  END IF
END SUB

' Gun: the ray leaves six moves after the order, from wherever we then stand, along the
' direction locked one move from now. Aim where they will be, minus our own drift.
SUB sk_motor__gun()
  IF k_contacts__best >= 0 THEN
    sk_motor__tx = playerX(k_contacts__best)
    sk_motor__ty = playerY(k_contacts__best)
    ' best_vx/_vy are 0 unless the target was also seen on the previous tick.
    sk_motor__tx = sk_motor__tx + k_contacts__best_vx * sk_motor__lead_ticks
    sk_motor__ty = sk_motor__ty + k_contacts__best_vy * sk_motor__lead_ticks
    IF sk_motor__in_contact AND worldTick >= sk_motor__path_until THEN
      sk_motor__tx = sk_motor__tx - sk_motor__leg_x * sk_motor__drift_ticks
      sk_motor__ty = sk_motor__ty - sk_motor__leg_y * sk_motor__drift_ticks
    ELSE
      sk_motor__tx = sk_motor__tx - k_self_motion__vx * sk_motor__drift_ticks
      sk_motor__ty = sk_motor__ty - k_self_motion__vy * sk_motor__drift_ticks
    END IF
    ' Hold fire when a visible teammate (by observed slot parity) stands in the line.
    sk_motor__clear = 1
    sk_motor__sx = sk_motor__tx - selfX
    sk_motor__sy = sk_motor__ty - selfY
    sk_motor__isqrt(sk_motor__sx * sk_motor__sx + sk_motor__sy * sk_motor__sy)
    sk_motor__reach = sk_motor__root
    IF sk_motor__reach > 0 THEN
      sk_motor__i = 0
      WHILE sk_motor__i < 16
        IF sk_motor__i <> selfId AND sk_motor__i MOD 2 = selfTeam AND visible(sk_motor__i) THEN
          sk_motor__ox = playerX(sk_motor__i) - selfX
          sk_motor__oy = playerY(sk_motor__i) - selfY
          sk_motor__along = (sk_motor__ox * sk_motor__sx + sk_motor__oy * sk_motor__sy) \ sk_motor__reach
          sk_motor__across = (sk_motor__ox * sk_motor__sy - sk_motor__oy * sk_motor__sx) \ sk_motor__reach
          IF sk_motor__across < 0 THEN
            sk_motor__across = 0 - sk_motor__across
          END IF
          IF sk_motor__along > 0 AND sk_motor__along < sk_motor__reach AND sk_motor__across < 95 THEN
            sk_motor__clear = 0
          END IF
        END IF
        sk_motor__i = sk_motor__i + 1
      WEND
    END IF
    IF hasSpray = 0 OR sk_motor__spray_distance_sq < sk_motor__spray_range_sq THEN
      IF sk_motor__clear AND sk_motor__gun_wait = 0 THEN
        shootAt(sk_motor__tx, sk_motor__ty)
        IF hasSpray AND k_contacts__best_cost >= sk_motor__spray_range_sq THEN
          sk_motor__spray_distance_shots_total = sk_motor__spray_distance_shots_total + 1
        END IF
        sk_motor__gun_wait = sk_motor__gun_wait_light
        IF armorHp > 0 OR trenchId >= 0 OR carrying THEN
          sk_motor__gun_wait = sk_motor__gun_wait_heavy
        END IF
        IF hasSpray THEN
          sk_motor__gun_wait = sk_motor__gun_wait_light
        END IF
      ELSE
        lookAt(sk_motor__tx, sk_motor__ty)
      END IF
    ELSE
      lookAt(sk_motor__tx, sk_motor__ty)
    END IF
  END IF
END SUB

' Grenade: preserve charging; track a fresh safe aim/need while armed, retain the last on loss.
' Rechecking eligibility must never silently drop an already charging grenade at our feet.
SUB sk_motor__grenade()
  sk_motor__eligible = 0
  IF hasGrenade = 0 OR grenadeCharge = 0 THEN
    sk_motor__charging = 0
  END IF
  IF hasGrenade AND k_contacts__best >= 0 THEN
    sk_motor__nx = playerX(k_contacts__best)
    sk_motor__ny = playerY(k_contacts__best)
    sk_motor__dx = sk_motor__nx - selfX
    sk_motor__dy = sk_motor__ny - selfY
    sk_motor__d2 = sk_motor__dx * sk_motor__dx + sk_motor__dy * sk_motor__dy
    sk_motor__safe = 1
    sk_motor__i = 0
    WHILE sk_motor__i < 16
      IF sk_motor__i MOD 2 = selfTeam AND visible(sk_motor__i) THEN
        sk_motor__fx = playerX(sk_motor__i) - sk_motor__nx
        sk_motor__fy = playerY(sk_motor__i) - sk_motor__ny
        IF sk_motor__fx * sk_motor__fx + sk_motor__fy * sk_motor__fy < 202500 THEN
          sk_motor__safe = 0
        END IF
      END IF
      sk_motor__i = sk_motor__i + 1
    WEND
    IF sk_motor__safe AND sk_motor__d2 > 160000 AND sk_motor__d2 < 1562500 THEN
      sk_motor__isqrt(sk_motor__d2)
      sk_motor__need = (sk_motor__root - 150) * 24 \ 1130 + 1
      IF sk_motor__need < 1 THEN
        sk_motor__need = 1
      END IF
      sk_motor__eligible = 1
    END IF
  END IF
  IF hasGrenade THEN
    IF sk_motor__charging = 0 AND sk_motor__eligible THEN
      IF mistingTicks() = 0 AND radarTicks() = 0 THEN
        sk_motor__charging = 1
        sk_motor__locked_x = sk_motor__nx
        sk_motor__locked_y = sk_motor__ny
        sk_motor__locked_need = sk_motor__need
        sk_motor__starts_total = sk_motor__starts_total + 1
      ELSE
        sk_motor__blocked_total = sk_motor__blocked_total + 1
      END IF
    END IF
    IF sk_motor__charging THEN
      IF sk_motor__eligible AND mistingTicks() = 0 AND radarTicks() = 0 THEN
        IF sk_motor__locked_x <> sk_motor__nx OR sk_motor__locked_y <> sk_motor__ny OR sk_motor__locked_need <> sk_motor__need THEN
          sk_motor__tracking_updates_total = sk_motor__tracking_updates_total + 1
          sk_motor__locked_x = sk_motor__nx
          sk_motor__locked_y = sk_motor__ny
          sk_motor__locked_need = sk_motor__need
        END IF
      END IF
      lookAt(sk_motor__locked_x, sk_motor__locked_y)
      sk_motor__release_charge = grenadeCharge
      sk_motor__release_need = sk_motor__locked_need
      IF mistingTicks() > 0 OR radarTicks() > 0 THEN
        ' Rules 49 forces release even when the charge command is held while disarmed.
        chargeGrenade(1)
        IF grenadeCharge > 0 THEN
          sk_motor__forced_total = sk_motor__forced_total + 1
          sk_motor__threw = 1
        END IF
        sk_motor__charging = 0
      ELSE
        IF grenadeCharge < sk_motor__locked_need THEN
          IF sk_motor__eligible = 0 OR grenadeCharge >= sk_motor__need THEN
            sk_motor__continued_total = sk_motor__continued_total + 1
          END IF
          chargeGrenade(1)
        ELSE
          chargeGrenade(0)
          sk_motor__threw = 1
          sk_motor__charging = 0
        END IF
      END IF
    END IF
  END IF
END SUB

' The whole per-tick motor tail, in the baseline's order. gx, gy: the goal point; hold: 1 when
' the cog stands on its post (the capability decides both).
SUB sk_motor__act(sk_motor_gx, sk_motor_gy, sk_motor_hold)
  sk_motor__threw = 0
  IF k_self_motion__teleported THEN
    sk_motor__gun_wait = 0
  END IF
  IF sk_motor__gun_wait > 0 THEN
    sk_motor__gun_wait = sk_motor__gun_wait - 1
  END IF
  sk_motor__goal_x = sk_motor_gx
  sk_motor__goal_y = sk_motor_gy
  sk_motor__holding = sk_motor_hold
  IF k_contacts__best < 0 THEN
    sk_motor__look_around()
  END IF
  sk_motor__spray_distance_sq = 0
  IF k_contacts__best >= 0 THEN
    sk_motor__spray_dx = playerX(k_contacts__best) - selfX
    sk_motor__spray_dy = playerY(k_contacts__best) - selfY
    sk_motor__spray_distance_sq = sk_motor__spray_dx * sk_motor__spray_dx + sk_motor__spray_dy * sk_motor__spray_dy
  END IF
  sk_motor__footwork()
  sk_motor__dry_route()
  sk_motor__gun()
  sk_motor__grenade()
END SUB

' A cover cog already capturing stays inside the ring until ownership or the objective changes.
SUB sk_motor__finish_cover_capture(sk_motor_capture_x, sk_motor_capture_y)
  sk_motor__cover_capture_ticks_total = sk_motor__cover_capture_ticks_total + 1
  sk_motor__act(sk_motor_capture_x, sk_motor_capture_y, 1)
END SUB

' Count the post-capture pursuit selected by C.default_goal; motor behavior is unchanged.
SUB sk_motor__cleanup(sk_motor_gx, sk_motor_gy, sk_motor_hold)
  sk_motor__cleanup_ticks_total = sk_motor__cleanup_ticks_total + 1
  sk_motor__act(sk_motor_gx, sk_motor_gy, sk_motor_hold)
END SUB
