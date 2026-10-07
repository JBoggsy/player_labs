' policy.bas | build 9d572cfd-1 | source 9d572cfd2e9cfb8de47e417c9dfccd4f76d05637 | strategy compiled foundation with measured improvements
' GENERATED from paintbot_pw_lab/strategy/STRATEGY.md by the strategy compiler. Do not edit:
' change the source and recompile.

' ==== runtime.lib ====
' runtime.lib: strategy runtime library, telemetry v2 print routines. Hand-written source,
' copied verbatim into every build (compilation design §4.1). Do not edit a build's copy.
'
' Contract with generated.tables (strategy_basic.py writes these; this file only reads them):
'   rt__n_rules, rt__def(r), rt__prio(r), rt__rcap(r)    rules 1..n: default and current
'                                                        priority, capability code
'   rt__ok(r)                                            1 when rule r's condition and role hold
'   rt__n_sits, rt__n_words, rt__flag(s)                 situation flags (code s, 0/1)
'   rt__n_adapt, rt__a_rule(a), rt__a_op(a), rt__a_amt(a), rt__a_dur(a)
'                                                        adaptation effects (op 1 add, 2 set;
'                                                        dur -1 = forever)
'   rt__min_hold, rt__margin, rt__interrupt              commitment (design §4.4)
'   rt__status, rt__cond                                 set by st__tick for the running cap
'   rt__in0, rt__in1, rt__in2                            bound inputs (st__bind)
'   rt__pe, rt__pb                                       this tick's print events / bytes
'                                                        (static worst per line)
'   st__pwd_print()                                      prints the PWD line and adds its cost
' Read-only exports for units: rt__rule, rt__cap, rt__since, rt__pver.
' Public kill switch: telemetryOff = 1 silences every telemetry line.
'
' Line formats and the event/byte counts below: API.md §4 / the compilation design.

DIM rt__def(63)
DIM rt__prio(63)
DIM rt__rcap(63)
DIM rt__ok(63)
DIM rt__flag(124)
DIM rt__fw(3)
DIM rt__a_on(31)
DIM rt__a_until(31)
DIM rt__a_prev(31)
DIM rt__a_rule(31)
DIM rt__a_op(31)
DIM rt__a_amt(31)
DIM rt__a_dur(31)

' Capability event: e = 1 start, 4 preempted, 5 died (condition code 0). 6 events, 64 bytes.
SUB rt__pwe(rt__pwe_c, rt__pwe_e)
  IF telemetryOff = 0 THEN
    IF rt__pwe_e = 1 THEN
      PRINT "PWE v=2 t="; worldTick; " c="; rt__pwe_c; " e=1 k=0"
    END IF
    IF rt__pwe_e = 4 THEN
      PRINT "PWE v=2 t="; worldTick; " c="; rt__pwe_c; " e=4 k=0"
    END IF
    IF rt__pwe_e = 5 THEN
      PRINT "PWE v=2 t="; worldTick; " c="; rt__pwe_c; " e=5 k=0"
    END IF
    rt__pe = rt__pe + 6
    rt__pb = rt__pb + 64
  END IF
END SUB

' Capability end: status 1 done (e=2), 2 abort (e=3), with its condition code. 7 events, 64 bytes.
SUB rt__pwe_end(rt__end_c, rt__end_s, rt__end_k)
  IF telemetryOff = 0 THEN
    IF rt__end_s = 1 THEN
      PRINT "PWE v=2 t="; worldTick; " c="; rt__end_c; " e=2 k="; rt__end_k
    ELSE
      PRINT "PWE v=2 t="; worldTick; " c="; rt__end_c; " e=3 k="; rt__end_k
    END IF
    rt__pe = rt__pe + 7
    rt__pb = rt__pb + 64
  END IF
END SUB

' A tick gap means the cog was dead: end the activation before anything else runs.
SUB rt__died()
  IF rt__cap > 0 AND rt__ended = 0 THEN
    rt__pwe(rt__cap, 5)
  END IF
  rt__rule = 0
  rt__cap = 0
  rt__ended = 0
END SUB

' Recompute one rule's priority from its default and every active effect on it, in adaptation
' code order: op 1 adds, op 2 sets; the result is clamped to 0..1000. Prints one PWP line
' (13 events, 92 bytes) for the adaptation that changed state.
SUB rt__recompute(rt__rc_a)
  rt__rc_r = rt__a_rule(rt__rc_a)
  rt__rc_old = rt__prio(rt__rc_r)
  rt__rc_p = rt__def(rt__rc_r)
  rt__rc_b = 1
  WHILE rt__rc_b <= rt__n_adapt
    IF rt__a_on(rt__rc_b) <> 0 THEN
      IF rt__a_rule(rt__rc_b) = rt__rc_r THEN
        IF rt__a_op(rt__rc_b) = 1 THEN
          rt__rc_p = rt__rc_p + rt__a_amt(rt__rc_b)
        ELSE
          rt__rc_p = rt__a_amt(rt__rc_b)
        END IF
      END IF
    END IF
    rt__rc_b = rt__rc_b + 1
  WEND
  IF rt__rc_p < 0 THEN
    rt__rc_p = 0
  END IF
  IF rt__rc_p > 1000 THEN
    rt__rc_p = 1000
  END IF
  rt__prio(rt__rc_r) = rt__rc_p
  rt__pver = rt__pver + 1
  IF telemetryOff = 0 THEN
    PRINT "PWP v=2 t="; worldTick; " a="; rt__rc_a; " r="; rt__rc_r; " o="; rt__rc_old; " n="; rt__rc_p; " p="; rt__pver
    rt__pe = rt__pe + 13
    rt__pb = rt__pb + 92
  END IF
END SUB

' One adaptation per tick: expire it when its window is over (a fire on that tick is ignored),
' otherwise apply it on the rising edge of its fire flag while it is not active.
SUB rt__adapt_step(rt__as_a, rt__as_fire)
  rt__as_expired = 0
  IF rt__a_on(rt__as_a) <> 0 THEN
    IF rt__a_until(rt__as_a) >= 0 THEN
      IF worldTick >= rt__a_until(rt__as_a) THEN
        rt__a_on(rt__as_a) = 0
        rt__as_expired = 1
        rt__recompute(rt__as_a)
      END IF
    END IF
  END IF
  IF rt__as_fire <> 0 AND rt__a_prev(rt__as_a) = 0 AND rt__a_on(rt__as_a) = 0 AND rt__as_expired = 0 THEN
    rt__a_on(rt__as_a) = 1
    rt__a_until(rt__as_a) = -1
    IF rt__a_dur(rt__as_a) >= 0 THEN
      rt__a_until(rt__as_a) = worldTick + rt__a_dur(rt__as_a)
    END IF
    rt__recompute(rt__as_a)
  END IF
  rt__a_prev(rt__as_a) = 0
  IF rt__as_fire <> 0 THEN
    rt__a_prev(rt__as_a) = 1
  END IF
END SUB

' Rule selection with commitment (design §4.4; strategy_basic.reference_select mirrors it).
SUB rt__select()
  rt__best = 0
  rt__i = 1
  WHILE rt__i <= rt__n_rules
    IF rt__ok(rt__i) <> 0 THEN
      IF rt__best = 0 THEN
        rt__best = rt__i
      ELSE
        IF rt__prio(rt__i) > rt__prio(rt__best) THEN
          rt__best = rt__i
        END IF
      END IF
    END IF
    rt__i = rt__i + 1
  WEND
  rt__switch = 0
  IF rt__rule = 0 THEN
    rt__switch = 1
  ELSE
    IF rt__ended <> 0 THEN
      rt__switch = 1
    END IF
    IF rt__ok(rt__rule) = 0 THEN
      rt__switch = 1
    END IF
    IF rt__best > 0 AND rt__best <> rt__rule THEN
      IF rt__prio(rt__best) >= rt__interrupt THEN
        rt__switch = 1
      END IF
      IF worldTick - rt__since >= rt__min_hold AND rt__prio(rt__best) >= rt__prio(rt__rule) + rt__margin THEN
        rt__switch = 1
      END IF
    END IF
  END IF
  rt__new = 0
  IF rt__switch = 0 THEN
    rt__held = 1
  ELSE
    rt__held = 0
    IF rt__rule > 0 AND rt__ended = 0 THEN
      rt__pwe(rt__cap, 4)
    END IF
    rt__rule = rt__best
    rt__cap = rt__rcap(rt__best)
    rt__since = worldTick
    rt__ended = 0
    IF rt__rule > 0 THEN
      rt__new = 1
    END IF
  END IF
END SUB

' Start (on a new activation) and tick the selected capability; report done/abort.
SUB rt__run()
  IF rt__cap > 0 THEN
    IF rt__new <> 0 THEN
      st__start()
      rt__pwe(rt__cap, 1)
    END IF
    st__tick()
    IF rt__status <> 0 THEN
      rt__pwe_end(rt__cap, rt__status, rt__cond)
      rt__ended = 1
    END IF
  END IF
END SUB

' Decision line: on any change of r c i h p f, and at least every 24 ticks. The PRINT is
' generated (st__pwd_print): it folds inputs and the priority version to literals when the
' source makes them constant, prints the same text, and adds its exact static cost.
SUB rt__pwd()
  rt__changed = 0
  rt__w = 0
  WHILE rt__w < rt__n_words
    rt__word = 0
    rt__bit = 1
    rt__j = 0
    WHILE rt__j < 31
      rt__s = rt__w * 31 + rt__j + 1
      IF rt__s <= rt__n_sits THEN
        IF rt__flag(rt__s) <> 0 THEN
          rt__word = rt__word + rt__bit
        END IF
      END IF
      IF rt__j < 30 THEN
        rt__bit = rt__bit * 2
      END IF
      rt__j = rt__j + 1
    WEND
    IF rt__word <> rt__fw(rt__w) THEN
      rt__changed = 1
    END IF
    rt__fw(rt__w) = rt__word
    rt__w = rt__w + 1
  WEND
  IF rt__rule <> rt__p_rule OR rt__cap <> rt__p_cap OR rt__held <> rt__p_held OR rt__pver <> rt__p_pver THEN
    rt__changed = 1
  END IF
  IF rt__in0 <> rt__p_in0 OR rt__in1 <> rt__p_in1 OR rt__in2 <> rt__p_in2 THEN
    rt__changed = 1
  END IF
  IF rt__p_done = 0 OR worldTick - rt__p_t >= 24 THEN
    rt__changed = 1
  END IF
  IF rt__changed <> 0 AND telemetryOff = 0 THEN
    st__pwd_print()
    rt__p_rule = rt__rule
    rt__p_cap = rt__cap
    rt__p_held = rt__held
    rt__p_pver = rt__pver
    rt__p_in0 = rt__in0
    rt__p_in1 = rt__in1
    rt__p_in2 = rt__in2
    rt__p_t = worldTick
    rt__p_done = 1
  END IF
END SUB

' Initial priority snapshot: one `PWP ... a=0` line per rule (o = n = default, p=0), printed at
' the end of a tick only while this tick's static print use leaves room (13 events, 92 bytes).
' Deferred to later ticks when there is no room, never skipped.
SUB rt__snapshot()
  IF telemetryOff = 0 AND rt__snap <= rt__n_rules THEN
    IF rt__pe + 13 <= 64 AND rt__pb + 92 <= 512 THEN
      PRINT "PWP v=2 t="; worldTick; " a=0 r="; rt__snap; " o="; rt__def(rt__snap); " n="; rt__def(rt__snap); " p=0"
      rt__pe = rt__pe + 13
      rt__pb = rt__pb + 92
      rt__snap = rt__snap + 1
    END IF
  END IF
END SUB

' ==== generated.tables ====
' generated.tables: rule, adaptation, commitment, constant and telemetry tables and the phase
' dispatch. Generated by strategy_basic.py from the source; do not edit.


SUB st__init()
  k_self_motion__teleport_step = 60
  k_squad_target__progress_period = 72
  k_squad_target__stall_sq = 40000
  k_squad_target__far_sq = 160000
  k_squad_target__avoid_ticks = 360
  k_squad_target__ref_offset = 1500
  k_squad_target__mirror_y = 4000
  k_squad_target__neutral_bonus = 20000
  k_squad_target__avoid_penalty = 4000000
  k_contacts__hp_weight = 160000
  k_contacts__carrier_bonus = 2500000
  k_contacts__former_range_sq = 27562500
  k_contacts__near_foe_sq = 6760000
  k_contacts__near_friend_sq = 1440000
  k_pickups__memory_ticks = 240
  k_pickups__reach_sq = 4840000
  k_pickups__arrive_sq = 10000
  s_supply_worth__fight_clear_sq = 1440000
  s_central_opening__opening_ticks = 720
  sk_motor__wet_cost = 6
  sk_motor__lead_ticks = 6
  sk_motor__drift_ticks = 5
  sk_motor__gun_wait_light = 25
  sk_motor__gun_wait_heavy = 73
  sk_motor__spray_range_sq = 640000
  c_central_opening__cover_back_cm = 500
  c_central_opening__bank_offset_cm = 600
  c_central_opening__dry_step_cm = 100
  c_central_opening__dry_steps = 8
  c_central_opening__hold_sq = 14400
  c_take_heart__hold_sq = 8100
  c_take_heart__quiet_sq = 810000
  c_cover_heart__capture_sq = 19600
  c_cover_heart__step_in_sq = 640000
  c_cover_heart__idle_limit = 96
  c_cover_heart__post_x = 3200
  c_cover_heart__post_y = 2000
  c_cover_heart__post_shift = 1200
  c_cover_heart__post_radius = 90
  c_cover_heart__hold_sq = 8100
  c_cover_heart__quiet_sq = 810000
  c_default_goal__quiet_sq = 810000
  c_resupply__quiet_sq = 810000
  c_fall_back__quiet_sq = 810000
  st_commitment__min_hold = 0
  st_commitment__preempt_margin = 0
  st_commitment__interrupt_at = 0
  st__role_squad = 0
  IF selfId = 0 OR selfId = 1 OR selfId = 2 OR selfId = 3 OR selfId = 8 OR selfId = 9 OR selfId = 10 OR selfId = 11 THEN
    st__role_squad = 1
  END IF
  IF selfId = 4 OR selfId = 5 OR selfId = 6 OR selfId = 7 OR selfId = 12 OR selfId = 13 OR selfId = 14 OR selfId = 15 THEN
    st__role_squad = 2
  END IF
  rt__n_rules = 6
  rt__def(1) = 400
  rt__prio(1) = 400
  rt__rcap(1) = 6
  rt__def(2) = 350
  rt__prio(2) = 350
  rt__rcap(2) = 1
  rt__def(3) = 300
  rt__prio(3) = 300
  rt__rcap(3) = 5
  rt__def(4) = 200
  rt__prio(4) = 200
  rt__rcap(4) = 2
  rt__def(5) = 200
  rt__prio(5) = 200
  rt__rcap(5) = 3
  rt__def(6) = 100
  rt__prio(6) = 100
  rt__rcap(6) = 4
  rt__n_adapt = 0
  rt__min_hold = st_commitment__min_hold
  rt__margin = st_commitment__preempt_margin
  rt__interrupt = st_commitment__interrupt_at
  rt__n_sits = 4
  rt__n_words = 1
  sk_motor__init()
  k_self_motion__init()
END SUB

SUB st__receive()
END SUB

SUB st__decoded()
END SUB

SUB st__knowledge()
  k_self_motion__update()
  k_squad_target__update()
  k_contacts__update()
  k_pickups__update()
END SUB

SUB st__situations()
  s_losing_fight__eval()
  rt__flag(1) = 0
  IF s_losing_fight__on <> 0 THEN
    rt__flag(1) = 1
  END IF
  s_supply_worth__eval()
  rt__flag(2) = 0
  IF s_supply_worth__on <> 0 THEN
    rt__flag(2) = 1
  END IF
  s_has_target_heart__eval()
  rt__flag(3) = 0
  IF s_has_target_heart__on <> 0 THEN
    rt__flag(3) = 1
  END IF
  s_central_opening__eval()
  rt__flag(4) = 0
  IF s_central_opening__on <> 0 THEN
    rt__flag(4) = 1
  END IF
END SUB

SUB st__adapt()
END SUB

SUB st__conditions()
  rt__ok(1) = rt__flag(1)
  rt__ok(2) = rt__flag(4)
  rt__ok(3) = rt__flag(2)
  rt__ok(4) = (rt__flag(3) AND (st__role_squad = 1))
  rt__ok(5) = (rt__flag(3) AND (st__role_squad = 2))
  rt__ok(6) = 1
END SUB

SUB st__bind()
  rt__in0 = 0
  rt__in1 = 0
  rt__in2 = 0
END SUB

SUB st__start()
  IF rt__cap = 1 THEN
    c_central_opening__status = 0
    c_central_opening__cond = 0
    c_central_opening__start()
  END IF
  IF rt__cap = 2 THEN
    c_take_heart__status = 0
    c_take_heart__cond = 0
    c_take_heart__start()
  END IF
  IF rt__cap = 3 THEN
    c_cover_heart__status = 0
    c_cover_heart__cond = 0
    c_cover_heart__start()
  END IF
  IF rt__cap = 4 THEN
    c_default_goal__status = 0
    c_default_goal__cond = 0
    c_default_goal__start()
  END IF
  IF rt__cap = 5 THEN
    c_resupply__status = 0
    c_resupply__cond = 0
    c_resupply__start()
  END IF
  IF rt__cap = 6 THEN
    c_fall_back__status = 0
    c_fall_back__cond = 0
    c_fall_back__start()
  END IF
END SUB

SUB st__tick()
  IF rt__cap = 1 THEN
    c_central_opening__tick()
    rt__status = c_central_opening__status
    rt__cond = c_central_opening__cond
  END IF
  IF rt__cap = 2 THEN
    c_take_heart__tick()
    rt__status = c_take_heart__status
    rt__cond = c_take_heart__cond
  END IF
  IF rt__cap = 3 THEN
    c_cover_heart__tick()
    rt__status = c_cover_heart__status
    rt__cond = c_cover_heart__cond
  END IF
  IF rt__cap = 4 THEN
    c_default_goal__tick()
    rt__status = c_default_goal__status
    rt__cond = c_default_goal__cond
  END IF
  IF rt__cap = 5 THEN
    c_resupply__tick()
    rt__status = c_resupply__status
    rt__cond = c_resupply__cond
  END IF
  IF rt__cap = 6 THEN
    c_fall_back__tick()
    rt__status = c_fall_back__status
    rt__cond = c_fall_back__cond
  END IF
  rt__valid = 0
  IF rt__cap = 1 THEN
    IF rt__status = 0 THEN
      rt__valid = 1
    END IF
  END IF
  IF rt__cap = 2 THEN
    IF rt__status = 0 THEN
      rt__valid = 1
    END IF
  END IF
  IF rt__cap = 3 THEN
    IF rt__status = 0 THEN
      rt__valid = 1
    END IF
  END IF
  IF rt__cap = 4 THEN
    IF rt__status = 0 THEN
      rt__valid = 1
    END IF
  END IF
  IF rt__cap = 5 THEN
    IF rt__status = 0 THEN
      rt__valid = 1
    END IF
  END IF
  IF rt__cap = 6 THEN
    IF rt__status = 0 THEN
      rt__valid = 1
    END IF
  END IF
  IF rt__valid = 0 THEN
    rt__status = 2
    rt__cond = -1
  END IF
END SUB

SUB st__send()
  com_status_call__sent = 0
  com_status_call__send()
  IF com_status_call__sent <> 0 AND telemetryOff = 0 THEN
    PRINT "PWC v=2 t="; worldTick; " m=1 s=1 w="; selfId; " d="; com_status_call__blocked_total; ","; com_status_call__continued_total; ","; com_status_call__opening_ticks_total; ","; com_status_call__tracking_updates_total; ","; com_status_call__cover_capture_ticks_total; ","; com_status_call__spray_distance_shots_total
    rt__pe = rt__pe + 17
    rt__pb = rt__pb + 118
  END IF
  com_grenade_out__sent = 0
  com_grenade_out__send()
  IF com_grenade_out__sent <> 0 AND telemetryOff = 0 THEN
    PRINT "PWC v=2 t="; worldTick; " m=2 s=1 w="; selfId; " d=0"
    rt__pe = rt__pe + 6
    rt__pb = rt__pb + 48
  END IF
END SUB

SUB st__beliefs()
  IF telemetryOff = 0 AND worldTick MOD 24 = 0 THEN
    PRINT "PWB v=2 t="; worldTick; " k=2 d="; k_squad_target__objective; ","; k_squad_target__idle_capture
    rt__pe = rt__pe + 7
    rt__pb = rt__pb + 52
  END IF
  IF telemetryOff = 0 AND worldTick MOD 24 = 1 THEN
    PRINT "PWB v=2 t="; worldTick; " k=3 d="; k_contacts__best; ","; k_contacts__foes_near; ","; k_contacts__friends_near; ","; k_contacts__range_rejected_total
    rt__pe = rt__pe + 11
    rt__pb = rt__pb + 76
  END IF
  IF telemetryOff = 0 AND worldTick MOD 24 = 2 THEN
    PRINT "PWB v=2 t="; worldTick; " k=4 d="; k_pickups__nearest; ","; k_pickups__hp_cap; ","; k_pickups__hp_changed_total
    rt__pe = rt__pe + 9
    rt__pb = rt__pb + 64
  END IF
END SUB

SUB st__pwd_print()
  PRINT "PWD v=2 t="; worldTick; " r="; rt__rule; " c="; rt__cap; " i=0,0,0 h="; rt__held; " p=0 f="; rt__fw(0)
  rt__pe = rt__pe + 11
  rt__pb = rt__pb + 51
END SUB

SUB st__flush()
END SUB

' ==== SK.motor ====
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

' Count coordinated opening ticks without changing the combat motor.
SUB sk_motor__central_opening(sk_motor_open_x, sk_motor_open_y, sk_motor_open_hold)
  sk_motor__opening_ticks_total = sk_motor__opening_ticks_total + 1
  sk_motor__act(sk_motor_open_x, sk_motor_open_y, sk_motor_open_hold)
END SUB

' ==== K.self_motion ====
' unit K.self_motion sha256:7d9fd1eaf31041f6c7478c749191bed6653b60597dd2e78541e501bd0cf18f29 generated, do not edit
' Our own movement since the previous tick; a respawn jump is not a velocity.
sub k_self_motion__init()
  k_self_motion__last_x = selfX
  k_self_motion__last_y = selfY
end sub

sub k_self_motion__update()
  k_self_motion__vx = selfX - k_self_motion__last_x
  k_self_motion__vy = selfY - k_self_motion__last_y
  if k_self_motion__vx > k_self_motion__teleport_step or k_self_motion__vx < 0 - k_self_motion__teleport_step or k_self_motion__vy > k_self_motion__teleport_step or k_self_motion__vy < 0 - k_self_motion__teleport_step then
    k_self_motion__vx = 0
    k_self_motion__vy = 0
    k_self_motion__teleported = 1
  else
    k_self_motion__teleported = 0
  end if
  k_self_motion__last_x = selfX
  k_self_motion__last_y = selfY
end sub

' ==== K.squad_target ====
' unit K.squad_target sha256:681bb58606ac6cd883c72ba26d2c2d813b49b110fd9590c789c8693f7ba54ef8 generated, do not edit
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

' ==== K.contacts ====
' unit K.contacts sha256:2b802bedf722a441635a2f8a73eec2f6d178329d40dcbf414cfbe33f5d7cc586 generated, do not edit
' The visible enemy we fight, the visible enemy carrier, and the local fight balance.
DIM k_contacts__old_x(15)
DIM k_contacts__old_y(15)
DIM k_contacts__seen_tick(15)

sub k_contacts__update()
  ' Step 1.
  k_contacts__best = -1
  k_contacts__best_cost = 2147483647
  k_contacts__thief = -1
  k_contacts__foes_near = 0
  k_contacts__friends_near = 1
  k_contacts__foe_sum_x = 0
  k_contacts__foe_sum_y = 0
  k_contacts__foes_seen = 0

  ' Step 2.
  k_contacts__i = 0
  while k_contacts__i < 16
    if k_contacts__i <> selfId and visible(k_contacts__i) then
      k_contacts__dx = playerX(k_contacts__i) - selfX
      k_contacts__dy = playerY(k_contacts__i) - selfY
      k_contacts__d2 = k_contacts__dx * k_contacts__dx + k_contacts__dy * k_contacts__dy
      if k_contacts__i mod 2 <> selfTeam then
        k_contacts__cost = k_contacts__d2 - (3 - playerHp(k_contacts__i)) * k_contacts__hp_weight
        if playerCarrying(k_contacts__i) then
          k_contacts__cost = k_contacts__cost - k_contacts__carrier_bonus
          k_contacts__thief = k_contacts__i
        end if
        if k_contacts__cost < k_contacts__best_cost and k_contacts__d2 <= gunRange() * gunRange() then
          k_contacts__best = k_contacts__i
          k_contacts__best_cost = k_contacts__cost
        end if
        if k_contacts__d2 <= k_contacts__former_range_sq and k_contacts__d2 > gunRange() * gunRange() then
          k_contacts__range_rejected_total = k_contacts__range_rejected_total + 1
        end if
        k_contacts__foes_seen = k_contacts__foes_seen + 1
        k_contacts__foe_sum_x = k_contacts__foe_sum_x + playerX(k_contacts__i)
        k_contacts__foe_sum_y = k_contacts__foe_sum_y + playerY(k_contacts__i)
        if k_contacts__d2 < k_contacts__near_foe_sq then
          k_contacts__foes_near = k_contacts__foes_near + 1
        end if
      else
        if k_contacts__d2 < k_contacts__near_friend_sq then
          k_contacts__friends_near = k_contacts__friends_near + 1
        end if
      end if
    end if
    k_contacts__i = k_contacts__i + 1
  wend

  ' Step 3: best's motion, read before Step 4 overwrites the memory.
  k_contacts__best_vx = 0
  k_contacts__best_vy = 0
  if k_contacts__best >= 0 then
    if k_contacts__seen_tick(k_contacts__best) = worldTick - 1 then
      k_contacts__best_vx = playerX(k_contacts__best) - k_contacts__old_x(k_contacts__best)
      k_contacts__best_vy = playerY(k_contacts__best) - k_contacts__old_y(k_contacts__best)
    end if
  end if

  ' Step 4: memory of every visible seat, ours included, and the enemy centre.
  k_contacts__i = 0
  while k_contacts__i < 16
    if visible(k_contacts__i) then
      k_contacts__old_x(k_contacts__i) = playerX(k_contacts__i)
      k_contacts__old_y(k_contacts__i) = playerY(k_contacts__i)
      k_contacts__seen_tick(k_contacts__i) = worldTick
    end if
    k_contacts__i = k_contacts__i + 1
  wend
  if k_contacts__foes_seen > 0 then
    k_contacts__foe_cx = k_contacts__foe_sum_x \ k_contacts__foes_seen
    k_contacts__foe_cy = k_contacts__foe_sum_y \ k_contacts__foes_seen
  else
    k_contacts__foe_cx = 0
    k_contacts__foe_cy = 0
  end if
end sub

' ==== K.pickups ====
' unit K.pickups sha256:099187de4f06cc46c21c4b628635a1393751681d37545361cf765c0d1ebd4856 generated, do not edit
' Supplies seen in the last ten seconds, using observed maximum HP.
DIM k_pickups__mem_x(63)
DIM k_pickups__mem_y(63)
DIM k_pickups__mem_kind(63)
DIM k_pickups__mem_tick(63)

sub k_pickups__update()
  if selfHp > k_pickups__hp_cap then
    k_pickups__hp_cap = selfHp
  end if
  if selfHp > 0 and selfHp * 3 <= k_pickups__hp_cap then
    k_pickups__critical = 1
  else
    k_pickups__critical = 0
  end if

  ' Step 1: refresh the memory from what is in view.
  k_pickups__i = 0
  while k_pickups__i < pickupCount() and k_pickups__i < 64
    if pickupVisible(k_pickups__i) then
      k_pickups__mem_x(k_pickups__i) = pickupX(k_pickups__i)
      k_pickups__mem_y(k_pickups__i) = pickupY(k_pickups__i)
      k_pickups__mem_kind(k_pickups__i) = pickupKind(k_pickups__i)
      k_pickups__mem_tick(k_pickups__i) = worldTick + 1
    end if
    k_pickups__i = k_pickups__i + 1
  wend

  ' Step 2: a visible enemy carrier.
  k_pickups__carrier = 0
  k_pickups__i = 0
  while k_pickups__i < 16
    if k_pickups__i <> selfId and visible(k_pickups__i) and k_pickups__i mod 2 <> selfTeam and playerCarrying(k_pickups__i) then
      k_pickups__carrier = 1
    end if
    k_pickups__i = k_pickups__i + 1
  wend

  ' Step 3: choice.
  k_pickups__nearest = -1
  k_pickups__nearest_x = 0
  k_pickups__nearest_y = 0
  if carrying = 0 and k_pickups__carrier = 0 then
    k_pickups__nearest_cost = k_pickups__reach_sq
    k_pickups__j = 0
    while k_pickups__j < pickupCount() and k_pickups__j < 64
      if k_pickups__mem_tick(k_pickups__j) > 0 and worldTick - k_pickups__mem_tick(k_pickups__j) < k_pickups__memory_ticks then
        k_pickups__kind = k_pickups__mem_kind(k_pickups__j)
        if (k_pickups__kind = 0 and hasGrenade = 0) or (k_pickups__kind = 2 and selfHp < k_pickups__hp_cap) or (k_pickups__kind = 3 and armorHp < 3 and selfHp = k_pickups__hp_cap) then
          k_pickups__wanted = 1
        else
          k_pickups__wanted = 0
        end if
        if (k_pickups__kind = 0 and hasGrenade = 0) or (k_pickups__kind = 2 and selfHp < 3) or (k_pickups__kind = 3 and armorHp < 3 and selfHp = 3) then
          k_pickups__old_wanted = 1
        else
          k_pickups__old_wanted = 0
        end if
        if k_pickups__wanted <> k_pickups__old_wanted then
          k_pickups__hp_changed_total = k_pickups__hp_changed_total + 1
        end if
        if k_pickups__wanted then
          k_pickups__dx = k_pickups__mem_x(k_pickups__j) - selfX
          k_pickups__dy = k_pickups__mem_y(k_pickups__j) - selfY
          k_pickups__cost = k_pickups__dx * k_pickups__dx + k_pickups__dy * k_pickups__dy
          if k_pickups__kind = 2 and k_pickups__critical = 1 then
            k_pickups__cost = k_pickups__cost \ 4
          end if
          if k_pickups__cost < k_pickups__arrive_sq and pickupVisible(k_pickups__j) = 0 then
            k_pickups__mem_tick(k_pickups__j) = 0
          else
            if k_pickups__cost < k_pickups__nearest_cost then
              k_pickups__nearest = k_pickups__j
              k_pickups__nearest_cost = k_pickups__cost
            end if
          end if
        end if
      end if
      k_pickups__j = k_pickups__j + 1
    wend
    if k_pickups__nearest >= 0 then
      k_pickups__nearest_x = k_pickups__mem_x(k_pickups__nearest)
      k_pickups__nearest_y = k_pickups__mem_y(k_pickups__nearest)
    end if
  end if
end sub

' ==== S.losing_fight ====
' unit S.losing_fight sha256:f5a8a8388f9d7f65985452424be2a3792ead5e61a95d15758d81e379b00fb232 generated, do not edit
' We see more near enemies than near friends, so we refuse the fight.
sub s_losing_fight__eval()
  if k_contacts__foes_near - k_contacts__friends_near >= 1 and carrying = 0 and k_squad_target__heart_count > 0 then
    s_losing_fight__on = 1
  else
    s_losing_fight__on = 0
  end if
end sub

' ==== S.supply_worth ====
' unit S.supply_worth sha256:097169d598f879dccd3abae806a3477c10e299ea8f5978d34be92cfa0a67187b generated, do not edit
' A wanted supply is remembered and no close fight stops us from fetching it.
sub s_supply_worth__eval()
  if k_pickups__nearest >= 0 and (k_contacts__best < 0 or k_contacts__best_cost > s_supply_worth__fight_clear_sq or k_pickups__critical = 1) then
    s_supply_worth__on = 1
  else
    s_supply_worth__on = 0
  end if
end sub

' ==== S.has_target_heart ====
' unit S.has_target_heart sha256:6b60c6ab97e4664fa799fdb79198871401925214fa58d94ce890e32c8b29a453 generated, do not edit
' Our squad has a target heart.
sub s_has_target_heart__eval()
  if k_squad_target__objective >= 0 then
    s_has_target_heart__on = 1
  else
    s_has_target_heart__on = 0
  end if
end sub

' ==== S.central_opening ====
' unit S.central_opening sha256:db4e0be89bd111b79f4c9d58f32c771bf3f590a4e028933250740e65b83943d9 generated, do not edit
' Commit both squads to the central approaches during the opening.
sub s_central_opening__eval()
  if worldTick <= s_central_opening__opening_ticks and heartCount() >= 2 and k_pickups__critical = 0 then
    s_central_opening__on = 1
  else
    s_central_opening__on = 0
  end if
end sub

' ==== C.central_opening ====
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

' ==== C.take_heart ====
' unit C.take_heart sha256:f59e0462e455bd0767345774ddcc94f3b3d2391af30e7c32097ade92ae616dba generated, do not edit
' Stand in the capture ring of the squad target (squad seats 0 and 1).
sub c_take_heart__start()
end sub

sub c_take_heart__tick()
  c_take_heart__goal_x = controlX(k_squad_target__objective)
  c_take_heart__goal_y = controlY(k_squad_target__objective)
  c_take_heart__dx = c_take_heart__goal_x - selfX
  c_take_heart__dy = c_take_heart__goal_y - selfY
  if c_take_heart__dx * c_take_heart__dx + c_take_heart__dy * c_take_heart__dy < c_take_heart__hold_sq then
    c_take_heart__hold = 1
  else
    c_take_heart__hold = 0
  end if
  sk_motor__act(c_take_heart__goal_x, c_take_heart__goal_y, c_take_heart__hold)
  ' Quiet approach when nothing is in sight but something was heard.
  if k_contacts__best < 0 and soundCount() > 0 then
    c_take_heart__qx = controlX(k_squad_target__objective) - selfX
    c_take_heart__qy = controlY(k_squad_target__objective) - selfY
    if c_take_heart__qx * c_take_heart__qx + c_take_heart__qy * c_take_heart__qy < c_take_heart__quiet_sq then
      sneak(1)
    end if
  end if
  c_take_heart__status = 0
end sub

' ==== C.cover_heart ====
' unit C.cover_heart sha256:fcf12b0a63c0756e5136262eb6b92d9e8c296573f6097f8ce66df81f4419e766 generated, do not edit
' Cover the squad target from outside the ring, and step in when nobody captures it
' (squad seats 2 and 3).
sub c_cover_heart__start()
end sub

sub c_cover_heart__tick()
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
  c_cover_heart__status = 0
end sub

' ==== C.default_goal ====
' unit C.default_goal sha256:6e56e4ac481f51f4971f1614814cddb96ad581f289ad1b1230e7e29f93d4c272 generated, do not edit
' With no squad target, go for the thief, home, or the heart.
sub c_default_goal__start()
end sub

sub c_default_goal__tick()
  ' Step 1.
  if carrying then
    if ownHeartStolen and k_contacts__thief >= 0 then
      c_default_goal__goal_x = playerX(k_contacts__thief)
      c_default_goal__goal_y = playerY(k_contacts__thief)
    else
      c_default_goal__goal_x = homeX
      c_default_goal__goal_y = homeY
    end if
  else
    if k_contacts__thief >= 0 then
      c_default_goal__goal_x = playerX(k_contacts__thief)
      c_default_goal__goal_y = playerY(k_contacts__thief)
    else
      c_default_goal__goal_x = heartX
      c_default_goal__goal_y = heartY
    end if
  end if
  ' Step 2.
  sk_motor__act(c_default_goal__goal_x, c_default_goal__goal_y, 0)
  ' Step 3: quiet approach when nothing is in sight but something was heard.
  if k_contacts__best < 0 and soundCount() > 0 and k_squad_target__objective >= 0 then
    c_default_goal__qx = controlX(k_squad_target__objective) - selfX
    c_default_goal__qy = controlY(k_squad_target__objective) - selfY
    if c_default_goal__qx * c_default_goal__qx + c_default_goal__qy * c_default_goal__qy < c_default_goal__quiet_sq then
      sneak(1)
    end if
  end if
  ' Step 4.
  c_default_goal__status = 0
end sub

' ==== C.resupply ====
' unit C.resupply sha256:cd8990c5650af4b96e73a5ed6939f7fd690edd4a3514313546e4729c0fd667dd generated, do not edit
' Walk to the remembered supply.
sub c_resupply__start()
end sub

sub c_resupply__tick()
  ' Step 1.
  sk_motor__act(k_pickups__nearest_x, k_pickups__nearest_y, 0)
  ' Step 2: quiet approach when nothing is in sight but something was heard.
  if k_contacts__best < 0 and soundCount() > 0 and k_squad_target__objective >= 0 then
    c_resupply__qx = controlX(k_squad_target__objective) - selfX
    c_resupply__qy = controlY(k_squad_target__objective) - selfY
    if c_resupply__qx * c_resupply__qx + c_resupply__qy * c_resupply__qy < c_resupply__quiet_sq then
      sneak(1)
    end if
  end if
  ' Step 3.
  c_resupply__status = 0
end sub

' ==== C.fall_back ====
' unit C.fall_back sha256:9d0e13fcdbae1542c228a258cbcb448ce22f8729cff63af6d8a08314e8014f3e generated, do not edit
' Head for the heart that is far from the enemies and near us.
sub c_fall_back__start()
end sub

sub c_fall_back__tick()
  ' Step 1.
  c_fall_back__cx = k_contacts__foe_cx
  c_fall_back__cy = k_contacts__foe_cy
  c_fall_back__away = -1
  c_fall_back__away_score = -2147483647
  c_fall_back__j = 0
  while c_fall_back__j < heartCount() and c_fall_back__j < 64
    c_fall_back__ex = (controlX(c_fall_back__j) - c_fall_back__cx) \ 16
    c_fall_back__ey = (controlY(c_fall_back__j) - c_fall_back__cy) \ 16
    c_fall_back__mx = (controlX(c_fall_back__j) - selfX) \ 16
    c_fall_back__my = (controlY(c_fall_back__j) - selfY) \ 16
    c_fall_back__score = c_fall_back__ex * c_fall_back__ex + c_fall_back__ey * c_fall_back__ey - (c_fall_back__mx * c_fall_back__mx + c_fall_back__my * c_fall_back__my) \ 2
    if c_fall_back__score > c_fall_back__away_score then
      c_fall_back__away = c_fall_back__j
      c_fall_back__away_score = c_fall_back__score
    end if
    c_fall_back__j = c_fall_back__j + 1
  wend
  ' Step 2.
  if c_fall_back__away >= 0 then
    c_fall_back__goal_x = controlX(c_fall_back__away)
    c_fall_back__goal_y = controlY(c_fall_back__away)
  else
    c_fall_back__goal_x = selfX
    c_fall_back__goal_y = selfY
  end if
  ' Step 3.
  sk_motor__act(c_fall_back__goal_x, c_fall_back__goal_y, 0)
  ' Step 4: quiet approach when nothing is in sight but something was heard.
  if k_contacts__best < 0 and soundCount() > 0 and k_squad_target__objective >= 0 then
    c_fall_back__qx = controlX(k_squad_target__objective) - selfX
    c_fall_back__qy = controlY(k_squad_target__objective) - selfY
    if c_fall_back__qx * c_fall_back__qx + c_fall_back__qy * c_fall_back__qy < c_fall_back__quiet_sq then
      sneak(1)
    end if
  end if
  ' Step 5.
  c_fall_back__status = 0
end sub

' ==== COM.status_call ====
' unit COM.status_call sha256:7255d283c66ceb8baccf388bb72fd45c40cb2db89a0b088aca4ce51707d7a074 generated, do not edit
' Every fifteen seconds, say whether we are in contact, falling back, or moving.
sub com_status_call__send()
  if worldTick mod 360 = selfId * 21 then
    if k_contacts__best >= 0 then
      shout(strNew("Contact! Cover this lane."))
    else
      if k_contacts__foes_near - k_contacts__friends_near >= 1 then
        shout(strNew("Too many. Falling back."))
      else
        shout(strNew("Moving with the squad."))
      end if
    end if
    com_status_call__sent = 1
    com_status_call__spray_distance_shots_total = sk_motor__spray_distance_shots_total
    com_status_call__blocked_total = sk_motor__blocked_total
    com_status_call__continued_total = sk_motor__continued_total
    com_status_call__opening_ticks_total = sk_motor__opening_ticks_total
    com_status_call__tracking_updates_total = sk_motor__tracking_updates_total
    com_status_call__cover_capture_ticks_total = sk_motor__cover_capture_ticks_total
  else
    com_status_call__sent = 0
  end if
end sub

' ==== COM.grenade_out ====
' unit COM.grenade_out sha256:0daa3c5423701b417c5094339907c230f3084615efbd9af3ff8931be209207f2 generated, do not edit
' Call out a grenade when the charge is ready.
sub com_grenade_out__send()
  if sk_motor__threw = 1 then
    shout(strNew("Grenade out!"))
    com_grenade_out__sent = 1
  else
    com_grenade_out__sent = 0
  end if
end sub

' ==== runtime.main ====
' runtime.main: the per-tick order (strategy file format §3). Hand-written source, copied
' verbatim as the last block of every build; the only top-level executable code in policy.bas.
IF rt__started = 0 THEN
  rt__started = 1
  rt__snap = 1
  rt__last = worldTick - 1
  st__init()
END IF
rt__pe = 0
rt__pb = 0
IF worldTick <> rt__last + 1 THEN
  rt__died()
END IF
rt__last = worldTick
st__receive()
st__knowledge()
st__situations()
st__adapt()
st__conditions()
rt__select()
st__bind()
rt__run()
st__send()
rt__pwd()
st__beliefs()
rt__snapshot()
st__flush()

