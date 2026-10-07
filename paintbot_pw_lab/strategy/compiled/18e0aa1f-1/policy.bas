' policy.bas | build 18e0aa1f-1 | source 18e0aa1f6501af95e2c98d5d62cdc1fff6fde9f8 | strategy baseline with comms v1 (M3 implementation)
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

' ==== runtime.comms ====
' Comms-v1 arithmetic. This is scrambling, not authentication.
' Generated initialization supplies cm__keys(0..5). No string handle survives a tick.
DIM cm__keys(5)
DIM cm__batch_a(8)
DIM cm__batch_b(8)

SUB cm__mask(cm__mt, cm__mb)
  cm__h1 = ((cm__mt MOD 30011) * cm__keys(0) + cm__keys(1) + cm__mb * cm__keys(2)) MOD 30011
  cm__h2 = (cm__h1 * cm__h1 + cm__keys(3)) MOD 32749
  cm__mask_value = cm__h1 * 32768 + cm__h2
END SUB

' Validate before packing, and after unpacking. Catalogue bounds also keep
' the telemetry send marker 2000000000 + pA inside signed int32.
SUB cm__validate()
  cm__ok = 0
  IF cm__type < 0 OR cm__type > 8 OR cm__speaker < 0 OR cm__speaker > 15 THEN
    EXIT SUB
  END IF
  IF cm__fa < 0 OR cm__fb < 0 OR cm__cell < 0 OR cm__cell > 65535 THEN
    EXIT SUB
  END IF
  cm__limit_a = 0
  cm__limit_b = 0
  IF cm__type = 0 THEN
    cm__limit_a = 2303
    cm__limit_b = 255
  END IF
  IF cm__type = 1 THEN
    cm__limit_a = 255
  END IF
  IF cm__type = 2 THEN
    cm__limit_a = 24
  END IF
  IF cm__type = 3 THEN
    cm__limit_a = 143
    cm__limit_b = 3
  END IF
  IF cm__type = 4 THEN
    cm__limit_a = 720
  END IF
  IF cm__type = 5 THEN
    cm__limit_a = 255
    cm__limit_b = 720
  END IF
  IF cm__type = 6 THEN
    cm__limit_a = 4095
  END IF
  IF cm__type = 7 THEN
    cm__limit_a = 15
    cm__limit_b = 255
  END IF
  IF cm__type = 8 THEN
    cm__limit_a = 15
  END IF
  IF cm__fa > cm__limit_a OR cm__fb > cm__limit_b THEN
    EXIT SUB
  END IF
  IF cm__type = 3 OR cm__type = 8 THEN
    IF cm__cell <> 0 THEN
      EXIT SUB
    END IF
  END IF
  cm__ok = 1
END SUB

SUB cm__check()
  cm__check_value = ((cm__core MOD 97) + 7 * (cm__pb MOD 97) + ((cm__time MOD 9973) * cm__keys(4)) MOD 97 + cm__keys(5)) MOD 97
END SUB

SUB cm__encode(cm__et, cm__es, cm__ea, cm__eb, cm__ec, cm__etime)
  cm__type = cm__et
  cm__speaker = cm__es
  cm__fa = cm__ea
  cm__fb = cm__eb
  cm__cell = cm__ec
  cm__time = cm__etime
  cm__validate()
  IF cm__time < 0 THEN
    cm__ok = 0
  END IF
  IF cm__ok = 0 THEN
    EXIT SUB
  END IF
  cm__core = cm__type + 16 * (cm__speaker + 16 * cm__fa)
  cm__pb = cm__cell + 65536 * cm__fb
  cm__check()
  cm__pa = cm__check_value + 100 * cm__core
  cm__mask(cm__time, 0)
  cm__block_a = 1000000000 + (cm__pa + cm__mask_value) MOD 1000000000
  cm__mask(cm__time, 1)
  cm__block_b = 1000000000 + (cm__pb + cm__mask_value) MOD 1000000000
END SUB

SUB cm__decode(cm__handle, cm__dtime)
  cm__ok = 0
  cm__time = cm__dtime
  IF cm__time < 0 THEN
    EXIT SUB
  END IF
  IF strLen(cm__handle) <> 20 THEN
    EXIT SUB
  END IF
  IF strByte(cm__handle, 0) <> 49 OR strByte(cm__handle, 10) <> 49 THEN
    EXIT SUB
  END IF
  cm__sa = 0
  cm__sb = 0
  cm__digit_i = 1
  WHILE cm__digit_i < 20
    IF cm__digit_i <> 10 THEN
      cm__digit = strByte(cm__handle, cm__digit_i) - 48
      IF cm__digit < 0 OR cm__digit > 9 THEN
        EXIT SUB
      END IF
      IF cm__digit_i < 10 THEN
        cm__sa = cm__sa * 10 + cm__digit
      ELSE
        cm__sb = cm__sb * 10 + cm__digit
      END IF
    END IF
    cm__digit_i = cm__digit_i + 1
  WEND
  cm__mask(cm__time, 0)
  cm__pa = (cm__sa - cm__mask_value + 1000000000) MOD 1000000000
  cm__mask(cm__time, 1)
  cm__pb = (cm__sb - cm__mask_value + 1000000000) MOD 1000000000
  cm__core = cm__pa / 100
  cm__type = cm__core MOD 16
  cm__speaker = (cm__core / 16) MOD 16
  cm__fa = cm__core / 256
  cm__cell = cm__pb MOD 65536
  cm__fb = cm__pb / 65536
  cm__validate()
  IF cm__ok = 0 THEN
    EXIT SUB
  END IF
  cm__check()
  IF cm__pa MOD 100 <> cm__check_value THEN
    cm__ok = 0
  END IF
END SUB

' One accepted packet per decoded event. The final entry may be our outgoing
' packet; its leading 2 is the direction marker in compact telemetry.
SUB cm__remember(cm__direction)
  ' Reserve the batch before optional priority snapshots consume spare budget.
  IF cm__batch_count = 0 THEN
    rt__pe = rt__pe + 4
    rt__pb = rt__pb + 25
  END IF
  rt__pe = rt__pe + 2
  rt__pb = rt__pb + 20
  cm__batch_a(cm__batch_count) = cm__pa + 1000000000 * cm__direction
  cm__batch_b(cm__batch_count) = cm__pb + 1000000000
  cm__batch_count = cm__batch_count + 1
END SUB

' The generated dispatcher calls cm__receive once before Knowledge. Cheap
' shape filtering scans all heard texts; at most eight candidates are decoded.
' cm__rx_valid indexes this tick's heard list, for motor's non-team sound cue.
DIM cm__rx_valid(63)
DIM cm__suspect_t(15)
DIM cm__suspect_x(15)
DIM cm__suspect_y(15)
DIM cm__heard_t(15)
DIM cm__heard_x(15)
DIM cm__heard_y(15)
SUB cm__receive()
  cm__batch_count = 0
  cm__sent = 0
  cm__attempts = 0
  cm__rx_index = 0
  WHILE cm__rx_index < heardCount()
    cm__rx_valid(cm__rx_index) = 0
    cm__rx_handle = heardText(cm__rx_index)
    cm__rx_slot = heardSlot(cm__rx_index)
    cm__rx_x = heardX(cm__rx_index)
    cm__rx_y = heardY(cm__rx_index)
    cm__ok = 0
    IF cm__attempts < cm__max_decode THEN
      IF strLen(cm__rx_handle) = 20 THEN
        IF strByte(cm__rx_handle, 0) = 49 AND strByte(cm__rx_handle, 10) = 49 THEN
          cm__attempts = cm__attempts + 1
          cm__decode(cm__rx_handle, worldTick - 1)
          IF cm__ok = 1 THEN
            IF cm__speaker MOD 2 = selfTeam AND cm__speaker <> selfId THEN
              cm__rx_valid(cm__rx_index) = 1
              cm__heard_t(cm__speaker) = worldTick + 1
              cm__heard_x(cm__speaker) = cm__rx_x
              cm__heard_y(cm__speaker) = cm__rx_y
              cm__remember(1)
              st__decoded()
            END IF
          END IF
        END IF
      END IF
      IF cm__ok = 0 THEN
        IF cm__rx_slot MOD 2 = selfTeam THEN
          cm__suspect_t(cm__rx_slot) = worldTick + 1
          cm__suspect_x(cm__rx_slot) = cm__rx_x
          cm__suspect_y(cm__rx_slot) = cm__rx_y
        END IF
      END IF
    END IF
    cm__rx_index = cm__rx_index + 1
  WEND
END SUB

' Called by COM send routines in priority order. A rejected proposal leaves
' cm__sent at zero so the next component can try. Cooldowns advance on success.
SUB cm__send(cm__st, cm__sfa, cm__sfb, cm__scell, cm__quiet)
  IF cm__sent = 1 THEN
    EXIT SUB
  END IF
  cm__urgent = cm__st = 2 OR cm__st = 8 OR cm__st = 7
  IF cm__urgent = 0 THEN
    IF cm__quiet <> 0 THEN
      EXIT SUB
    END IF
    IF cm__last_nonurgent > 0 THEN
      IF worldTick + 1 - cm__last_nonurgent < cm__min_gap THEN
        EXIT SUB
      END IF
    END IF
  END IF
  cm__encode(cm__st, selfId, cm__sfa, cm__sfb, cm__scell, worldTick)
  IF cm__ok = 0 THEN
    EXIT SUB
  END IF
  cm__out_handle = strFromInt(cm__block_a)
  cm__out_handle = strCatInt(cm__out_handle, cm__block_b)
  cm__sent = shout(cm__out_handle)
  IF cm__sent = 1 THEN
    cm__remember(2)
    IF cm__urgent = 0 THEN
      cm__last_nonurgent = worldTick + 1
    END IF
  END IF
END SUB

' Flush after snapshots, at the end of this tick. Fixed-width decimal PRINT
' items avoid strings (PRINT handles are numeric) and preserve every payload.
SUB cm__flush()
  IF cm__batch_count = 0 OR telemetryOff <> 0 THEN
    EXIT SUB
  END IF
  PRINT "PWC v=3 t="; worldTick; " b=";
  cm__batch_i = 0
  WHILE cm__batch_i < cm__batch_count
    PRINT cm__batch_a(cm__batch_i); cm__batch_b(cm__batch_i);
    cm__batch_i = cm__batch_i + 1
  WEND
  PRINT
END SUB

' ==== generated.tables ====
' generated.tables: rule, adaptation, commitment, constant and telemetry tables and the phase
' dispatch. Generated by strategy_basic.py from the source; do not edit.

DIM k_contacts__friend(15)
DIM k_contacts__hostile(15)
DIM k_comms_danger__grenade_x(3)
DIM k_comms_danger__grenade_y(3)
DIM k_comms_danger__grenade_until(3)
DIM com_disguise_friend__packet(1)
DIM com_disguise_friend__df_x(15)
DIM com_disguise_friend__df_y(15)
DIM com_disguise_friend__df_until(15)
DIM com_disguise_alert__packet(1)
DIM com_disguise_alert__xa_s1(15)
DIM com_disguise_alert__xa_x1(15)
DIM com_disguise_alert__xa_y1(15)
DIM com_disguise_alert__xa_t1(15)
DIM com_disguise_alert__xa_s2(15)
DIM com_disguise_alert__xa_x2(15)
DIM com_disguise_alert__xa_y2(15)
DIM com_disguise_alert__xa_t2(15)
DIM com_disguise_alert__xa_amb(15)
DIM com_focus_call__packet(1)
DIM com_glory_seen__packet(1)
DIM com_glory_seen__gl_x(7)
DIM com_glory_seen__gl_y(7)
DIM com_glory_seen__gl_until(7)
DIM com_glory_seen__gl_t(7)
DIM com_enemy_sighting__packet(1)
DIM com_enemy_sighting__ht_x(15)
DIM com_enemy_sighting__ht_y(15)
DIM com_enemy_sighting__ht_t(15)
DIM com_enemy_sighting__ht_until(15)
DIM com_grenade_warning__packet(1)
DIM com_grenade_warning__gz_x(3)
DIM com_grenade_warning__gz_y(3)
DIM com_grenade_warning__gz_until(3)
DIM com_under_fire__packet(1)
DIM com_pickup_taken__packet(1)
DIM com_pickup_taken__rk_until(63)
DIM com_pickup_taken__rk_t(63)
DIM com_pickup_ready__packet(1)
DIM com_pickup_ready__rr_x(63)
DIM com_pickup_ready__rr_y(63)
DIM com_pickup_ready__rr_kind(63)
DIM com_pickup_ready__rr_t(63)

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
  k_contacts__range_sq = 27562500
  k_contacts__near_foe_sq = 6760000
  k_contacts__near_friend_sq = 1440000
  k_contacts__engage_range_sq = 4549689
  k_pickups__memory_ticks = 240
  k_pickups__reach_sq = 4840000
  k_pickups__arrive_sq = 10000
  k_pickups__take_radius_sq = 14400
  k_pickups__grenade_delay = 120
  k_pickups__supply_delay = 720
  k_comms_danger__clear_radius = 450 ' @tune 250 700 50
  s_supply_worth__fight_clear_sq = 1440000
  sk_motor__wet_cost = 6
  sk_motor__lead_ticks = 6
  sk_motor__drift_ticks = 5
  sk_motor__gun_wait_light = 25
  sk_motor__gun_wait_heavy = 73
  sk_motor__spray_range_sq = 640000
  c_take_heart__hold_sq = 8100
  c_take_heart__quiet_sq = 810000
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
  com_disguise_friend__d_refresh = 24 ' @tune 12 72 12
  com_disguise_friend__friend_radius = 250 ' @tune 100 500 50
  com_disguise_friend__friend_ttl = 48 ' @tune 24 120 12
  com_disguise_friend__d_range_sq = 1638400
  com_disguise_alert__x_window = 24 ' @tune 12 72 12
  com_disguise_alert__x_distance = 1000 ' @tune 700 1500 100
  com_disguise_alert__x_radius = 300 ' @tune 100 600 50
  com_disguise_alert__disguise_ttl = 72 ' @tune 24 240 24
  com_disguise_alert__x_refresh = 24 ' @tune 12 72 12
  com_focus_call__focus_refresh = 24 ' @tune 12 48 12
  com_focus_call__focus_ttl = 36 ' @tune 12 72 12
  com_focus_call__focus_radius = 400 ' @tune 100 800 50
  com_focus_call__full_hp = 10
  com_glory_seen__h_refresh = 120 ' @tune 48 240 24
  com_glory_seen__h_match = 200
  com_enemy_sighting__e_refresh = 12 ' @tune 6 48 6
  com_enemy_sighting__e_move = 300 ' @tune 100 800 50
  com_enemy_sighting__heard_ttl = 48 ' @tune 24 120 12
  com_grenade_warning__g_move = 200 ' @tune 100 400 50
  com_under_fire__danger_ttl = 48 ' @tune 24 120 12
  com_pickup_taken__event_window = 24 ' @tune 6 48 6
  com_pickup_ready__event_window = 24 ' @tune 6 48 6
  st__role_squad = 0
  IF selfId = 0 OR selfId = 1 OR selfId = 2 OR selfId = 3 OR selfId = 8 OR selfId = 9 OR selfId = 10 OR selfId = 11 THEN
    st__role_squad = 1
  END IF
  IF selfId = 4 OR selfId = 5 OR selfId = 6 OR selfId = 7 OR selfId = 12 OR selfId = 13 OR selfId = 14 OR selfId = 15 THEN
    st__role_squad = 2
  END IF
  rt__n_rules = 5
  rt__def(1) = 400
  rt__prio(1) = 400
  rt__rcap(1) = 5
  rt__def(2) = 300
  rt__prio(2) = 300
  rt__rcap(2) = 4
  rt__def(3) = 200
  rt__prio(3) = 200
  rt__rcap(3) = 1
  rt__def(4) = 200
  rt__prio(4) = 200
  rt__rcap(4) = 2
  rt__def(5) = 100
  rt__prio(5) = 100
  rt__rcap(5) = 3
  rt__n_adapt = 0
  rt__min_hold = st_commitment__min_hold
  rt__margin = st_commitment__preempt_margin
  rt__interrupt = st_commitment__interrupt_at
  rt__n_sits = 3
  rt__n_words = 1
  cm__keys(0) = 7919
  cm__keys(1) = 17431
  cm__keys(2) = 23117
  cm__keys(3) = 1907
  cm__keys(4) = 31
  cm__keys(5) = 73
  cm__max_decode = 8
  cm__min_gap = 6
  sk_motor__init()
  k_self_motion__init()
  k_pickups__init()
  com_focus_call__init()
END SUB

SUB st__receive()
  com_enemy_sighting__got = 0
  com_focus_call__got = 0
  com_grenade_warning__got = 0
  com_under_fire__got = 0
  com_glory_seen__got = 0
  com_pickup_taken__got = 0
  com_pickup_ready__got = 0
  com_disguise_alert__got = 0
  com_disguise_friend__got = 0
  cm__receive()
END SUB

SUB st__decoded()
  IF cm__type = 0 THEN
    com_enemy_sighting__packet(0) = cm__pa
    com_enemy_sighting__packet(1) = cm__pb
    com_enemy_sighting__got = com_enemy_sighting__got + 1
    com_enemy_sighting__from = cm__speaker
    com_enemy_sighting__recv()
  END IF
  IF cm__type = 1 THEN
    com_focus_call__packet(0) = cm__pa
    com_focus_call__packet(1) = cm__pb
    com_focus_call__got = com_focus_call__got + 1
    com_focus_call__from = cm__speaker
    com_focus_call__recv()
  END IF
  IF cm__type = 2 THEN
    com_grenade_warning__packet(0) = cm__pa
    com_grenade_warning__packet(1) = cm__pb
    com_grenade_warning__got = com_grenade_warning__got + 1
    com_grenade_warning__from = cm__speaker
    com_grenade_warning__recv()
  END IF
  IF cm__type = 3 THEN
    com_under_fire__packet(0) = cm__pa
    com_under_fire__packet(1) = cm__pb
    com_under_fire__got = com_under_fire__got + 1
    com_under_fire__from = cm__speaker
    com_under_fire__recv()
  END IF
  IF cm__type = 4 THEN
    com_glory_seen__packet(0) = cm__pa
    com_glory_seen__packet(1) = cm__pb
    com_glory_seen__got = com_glory_seen__got + 1
    com_glory_seen__from = cm__speaker
    com_glory_seen__recv()
  END IF
  IF cm__type = 5 THEN
    com_pickup_taken__packet(0) = cm__pa
    com_pickup_taken__packet(1) = cm__pb
    com_pickup_taken__got = com_pickup_taken__got + 1
    com_pickup_taken__from = cm__speaker
    com_pickup_taken__recv()
  END IF
  IF cm__type = 6 THEN
    com_pickup_ready__packet(0) = cm__pa
    com_pickup_ready__packet(1) = cm__pb
    com_pickup_ready__got = com_pickup_ready__got + 1
    com_pickup_ready__from = cm__speaker
    com_pickup_ready__recv()
  END IF
  IF cm__type = 7 THEN
    com_disguise_alert__packet(0) = cm__pa
    com_disguise_alert__packet(1) = cm__pb
    com_disguise_alert__got = com_disguise_alert__got + 1
    com_disguise_alert__from = cm__speaker
    com_disguise_alert__recv()
  END IF
  IF cm__type = 8 THEN
    com_disguise_friend__packet(0) = cm__pa
    com_disguise_friend__packet(1) = cm__pb
    com_disguise_friend__got = com_disguise_friend__got + 1
    com_disguise_friend__from = cm__speaker
    com_disguise_friend__recv()
  END IF
END SUB

SUB st__knowledge()
  k_self_motion__update()
  k_squad_target__update()
  k_contacts__update()
  k_pickups__update()
  k_comms_danger__update()
  k_glory_hearts__update()
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
END SUB

SUB st__adapt()
END SUB

SUB st__conditions()
  rt__ok(1) = rt__flag(1)
  rt__ok(2) = rt__flag(2)
  rt__ok(3) = (rt__flag(3) AND (st__role_squad = 1))
  rt__ok(4) = (rt__flag(3) AND (st__role_squad = 2))
  rt__ok(5) = 1
END SUB

SUB st__bind()
  rt__in0 = 0
  rt__in1 = 0
  rt__in2 = 0
END SUB

SUB st__start()
  IF rt__cap = 1 THEN
    c_take_heart__status = 0
    c_take_heart__cond = 0
    c_take_heart__start()
  END IF
  IF rt__cap = 2 THEN
    c_cover_heart__status = 0
    c_cover_heart__cond = 0
    c_cover_heart__start()
  END IF
  IF rt__cap = 3 THEN
    c_default_goal__status = 0
    c_default_goal__cond = 0
    c_default_goal__start()
  END IF
  IF rt__cap = 4 THEN
    c_resupply__status = 0
    c_resupply__cond = 0
    c_resupply__start()
  END IF
  IF rt__cap = 5 THEN
    c_fall_back__status = 0
    c_fall_back__cond = 0
    c_fall_back__start()
  END IF
END SUB

SUB st__tick()
  IF rt__cap = 1 THEN
    c_take_heart__tick()
    rt__status = c_take_heart__status
    rt__cond = c_take_heart__cond
  END IF
  IF rt__cap = 2 THEN
    c_cover_heart__tick()
    rt__status = c_cover_heart__status
    rt__cond = c_cover_heart__cond
  END IF
  IF rt__cap = 3 THEN
    c_default_goal__tick()
    rt__status = c_default_goal__status
    rt__cond = c_default_goal__cond
  END IF
  IF rt__cap = 4 THEN
    c_resupply__tick()
    rt__status = c_resupply__status
    rt__cond = c_resupply__cond
  END IF
  IF rt__cap = 5 THEN
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
  IF rt__valid = 0 THEN
    rt__status = 2
    rt__cond = -1
  END IF
END SUB

SUB st__send()
  cm__sent = 0
  com_enemy_sighting__sent = 0
  com_focus_call__sent = 0
  com_grenade_warning__sent = 0
  com_under_fire__sent = 0
  com_glory_seen__sent = 0
  com_pickup_taken__sent = 0
  com_pickup_ready__sent = 0
  com_disguise_alert__sent = 0
  com_disguise_friend__sent = 0
  IF cm__sent = 0 THEN
    com_grenade_warning__send()
    com_grenade_warning__sent = cm__sent
    IF com_grenade_warning__sent <> 0 THEN
      com_grenade_warning__packet(0) = cm__pa
      com_grenade_warning__packet(1) = cm__pb
    END IF
  END IF
  IF cm__sent = 0 THEN
    com_disguise_friend__send()
    com_disguise_friend__sent = cm__sent
    IF com_disguise_friend__sent <> 0 THEN
      com_disguise_friend__packet(0) = cm__pa
      com_disguise_friend__packet(1) = cm__pb
    END IF
  END IF
  IF cm__sent = 0 THEN
    com_disguise_alert__send()
    com_disguise_alert__sent = cm__sent
    IF com_disguise_alert__sent <> 0 THEN
      com_disguise_alert__packet(0) = cm__pa
      com_disguise_alert__packet(1) = cm__pb
    END IF
  END IF
  IF cm__sent = 0 THEN
    com_focus_call__send()
    com_focus_call__sent = cm__sent
    IF com_focus_call__sent <> 0 THEN
      com_focus_call__packet(0) = cm__pa
      com_focus_call__packet(1) = cm__pb
    END IF
  END IF
  IF cm__sent = 0 THEN
    com_glory_seen__send()
    com_glory_seen__sent = cm__sent
    IF com_glory_seen__sent <> 0 THEN
      com_glory_seen__packet(0) = cm__pa
      com_glory_seen__packet(1) = cm__pb
    END IF
  END IF
  IF cm__sent = 0 THEN
    com_enemy_sighting__send()
    com_enemy_sighting__sent = cm__sent
    IF com_enemy_sighting__sent <> 0 THEN
      com_enemy_sighting__packet(0) = cm__pa
      com_enemy_sighting__packet(1) = cm__pb
    END IF
  END IF
  IF cm__sent = 0 THEN
    com_under_fire__send()
    com_under_fire__sent = cm__sent
    IF com_under_fire__sent <> 0 THEN
      com_under_fire__packet(0) = cm__pa
      com_under_fire__packet(1) = cm__pb
    END IF
  END IF
  IF cm__sent = 0 THEN
    com_pickup_taken__send()
    com_pickup_taken__sent = cm__sent
    IF com_pickup_taken__sent <> 0 THEN
      com_pickup_taken__packet(0) = cm__pa
      com_pickup_taken__packet(1) = cm__pb
    END IF
  END IF
  IF cm__sent = 0 THEN
    com_pickup_ready__send()
    com_pickup_ready__sent = cm__sent
    IF com_pickup_ready__sent <> 0 THEN
      com_pickup_ready__packet(0) = cm__pa
      com_pickup_ready__packet(1) = cm__pb
    END IF
  END IF
END SUB

SUB st__beliefs()
  IF telemetryOff = 0 AND worldTick MOD 24 = 0 THEN
    PRINT "PWB v=2 t="; worldTick; " k=2 d="; k_squad_target__objective; ","; k_squad_target__idle_capture
    rt__pe = rt__pe + 7
    rt__pb = rt__pb + 52
  END IF
  IF telemetryOff = 0 AND worldTick MOD 24 = 1 THEN
    PRINT "PWB v=2 t="; worldTick; " k=3 d="; k_contacts__best; ","; k_contacts__foes_near; ","; k_contacts__friends_near; ","; k_contacts__focus_used
    rt__pe = rt__pe + 11
    rt__pb = rt__pb + 76
  END IF
  IF telemetryOff = 0 AND worldTick MOD 24 = 2 THEN
    PRINT "PWB v=2 t="; worldTick; " k=4 d="; k_pickups__nearest; ","; k_pickups__taken_id
    rt__pe = rt__pe + 7
    rt__pb = rt__pb + 52
  END IF
  IF telemetryOff = 0 AND worldTick MOD 24 = 3 THEN
    PRINT "PWB v=2 t="; worldTick; " k=5 d="; k_comms_danger__zone_count; ","; k_comms_danger__danger_until
    rt__pe = rt__pe + 7
    rt__pb = rt__pb + 52
  END IF
  IF telemetryOff = 0 AND worldTick MOD 24 = 4 THEN
    PRINT "PWB v=2 t="; worldTick; " k=6 d="; k_glory_hearts__count; ","; k_glory_hearts__nearest_left
    rt__pe = rt__pe + 7
    rt__pb = rt__pb + 52
  END IF
END SUB

SUB st__pwd_print()
  PRINT "PWD v=2 t="; worldTick; " r="; rt__rule; " c="; rt__cap; " i=0,0,0 h="; rt__held; " p=0 f="; rt__fw(0)
  rt__pe = rt__pe + 11
  rt__pb = rt__pb + 50
END SUB

SUB st__flush()
  cm__flush()
END SUB

' ==== SK.motor ====
' SK.motor: baseline mechanics plus the specified communication receiver effects.
' Taken from reference/base.bas with every name moved into the sk_motor__ namespace and the
' same int32 expressions in the same order: integer square root, wet-line sampling, footwork
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
  sk_motor__guess = (sk_motor__root + sk_motor_n / sk_motor__root) / 2
  sk_motor__iters = 0
  WHILE sk_motor__guess < sk_motor__root AND sk_motor__iters < 24
    sk_motor__root = sk_motor__guess
    sk_motor__guess = (sk_motor__root + sk_motor_n / sk_motor__root) / 2
    sk_motor__iters = sk_motor__iters + 1
  WEND
END SUB

' How much of the straight line between two points is under water, in ten samples: into sk_motor__wet.
SUB sk_motor__wet_line(sk_motor_ax, sk_motor_ay, sk_motor_bx, sk_motor_by)
  sk_motor__wet = 0
  sk_motor__s3 = 1
  WHILE sk_motor__s3 <= 10
    IF waterAt(sk_motor_ax + (sk_motor_bx - sk_motor_ax) * sk_motor__s3 / 10, sk_motor_ay + (sk_motor_by - sk_motor_ay) * sk_motor__s3 / 10) THEN
      sk_motor__wet = sk_motor__wet + 1
    END IF
    sk_motor__s3 = sk_motor__s3 + 1
  WEND
END SUB

' Time to walk a leg, in metres of dry walking: a wet metre costs wet_cost dry ones. Into sk_motor__leg_cost.
SUB sk_motor__leg_time(sk_motor_ax, sk_motor_ay, sk_motor_bx, sk_motor_by)
  sk_motor__wet_line(sk_motor_ax, sk_motor_ay, sk_motor_bx, sk_motor_by)
  sk_motor__isqrt((sk_motor_bx - sk_motor_ax) * (sk_motor_bx - sk_motor_ax) + (sk_motor_by - sk_motor_ay) * (sk_motor_by - sk_motor_ay))
  sk_motor__leg_cost = sk_motor__root / 100 + sk_motor__root / 100 * sk_motor__wet * (sk_motor__wet_cost - 1) / 10
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
    sk_motor__leg_x = (0 - sk_motor__ty) * 100 * sk_motor__zig / sk_motor__root
    sk_motor__leg_y = sk_motor__tx * 100 * sk_motor__zig / sk_motor__root
  END IF
  IF sk_motor__holding = 0 THEN
    sk_motor__fx = sk_motor__goal_x - selfX
    sk_motor__fy = sk_motor__goal_y - selfY
    sk_motor__isqrt(sk_motor__fx * sk_motor__fx + sk_motor__fy * sk_motor__fy)
    IF sk_motor__root > 60 THEN
      sk_motor__leg_x = sk_motor__leg_x * 3 / 4 + sk_motor__fx * 100 / sk_motor__root
      sk_motor__leg_y = sk_motor__leg_y * 3 / 4 + sk_motor__fy * 100 / sk_motor__root
    END IF
  END IF
  sk_motor__isqrt(sk_motor__leg_x * sk_motor__leg_x + sk_motor__leg_y * sk_motor__leg_y)
  IF sk_motor__root > 0 THEN
    sk_motor__leg_x = sk_motor__leg_x * 28 / sk_motor__root
    sk_motor__leg_y = sk_motor__leg_y * 28 / sk_motor__root
  END IF
END SUB

' Facing with nothing to shoot: sweep, then turn to speech and sound.
SUB sk_motor__look_around()
  sk_motor__scan = (worldTick / 24 + selfId) MOD 4
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
  ' Heard enemy tracks and danger cues never become invisible fire targets.
  IF k_comms_danger__danger_until > worldTick THEN
    sk_motor__look_x = k_comms_danger__danger_x
    sk_motor__look_y = k_comms_danger__danger_y
    sk_motor__bearing = k_comms_danger__danger_dir
    IF sk_motor__bearing = 0 OR sk_motor__bearing = 1 OR sk_motor__bearing = 7 THEN
      sk_motor__look_x = sk_motor__look_x + 1000
    END IF
    IF sk_motor__bearing = 3 OR sk_motor__bearing = 4 OR sk_motor__bearing = 5 THEN
      sk_motor__look_x = sk_motor__look_x - 1000
    END IF
    IF sk_motor__bearing = 1 OR sk_motor__bearing = 2 OR sk_motor__bearing = 3 THEN
      sk_motor__look_y = sk_motor__look_y + 1000
    END IF
    IF sk_motor__bearing = 5 OR sk_motor__bearing = 6 OR sk_motor__bearing = 7 THEN
      sk_motor__look_y = sk_motor__look_y - 1000
    END IF
  END IF
  IF k_contacts__heard_target >= 0 THEN
    sk_motor__look_x = k_contacts__heard_x
    sk_motor__look_y = k_contacts__heard_y
  END IF
  sk_motor__i = 0
  sk_motor__heard_found = 0
  WHILE sk_motor__i < heardCount() AND sk_motor__heard_found = 0
    IF cm__rx_valid(sk_motor__i) = 0 THEN
      sk_motor__look_x = heardX(sk_motor__i)
      sk_motor__look_y = heardY(sk_motor__i)
      sk_motor__heard_found = 1
    END IF
    sk_motor__i = sk_motor__i + 1
  WEND
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
    sk_motor__want_shot = sk_motor__gun_wait = 0 AND (hasSpray = 0 OR k_contacts__best_cost < sk_motor__spray_range_sq)
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
        sk_motor__dr_mx = selfX + sk_motor__dr_dx / 2
        sk_motor__dr_my = selfY + sk_motor__dr_dy / 2
        sk_motor__dr_k = 0
        WHILE sk_motor__dr_k < 6
          sk_motor__dr_cx = sk_motor__dr_mx - sk_motor__dr_dy * sk_motor__dr_f(sk_motor__dr_k) / 10
          sk_motor__dr_cy = sk_motor__dr_my + sk_motor__dr_dx * sk_motor__dr_f(sk_motor__dr_k) / 10
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
    ' Hold fire when a visible friend, including a protected disguise, stands in the line.
    sk_motor__clear = 1
    sk_motor__sx = sk_motor__tx - selfX
    sk_motor__sy = sk_motor__ty - selfY
    sk_motor__isqrt(sk_motor__sx * sk_motor__sx + sk_motor__sy * sk_motor__sy)
    sk_motor__reach = sk_motor__root
    IF sk_motor__reach > 0 THEN
      sk_motor__i = 0
      WHILE sk_motor__i < 16
        IF sk_motor__i <> selfId AND k_contacts__friend(sk_motor__i) AND visible(sk_motor__i) THEN
          sk_motor__ox = playerX(sk_motor__i) - selfX
          sk_motor__oy = playerY(sk_motor__i) - selfY
          sk_motor__along = (sk_motor__ox * sk_motor__sx + sk_motor__oy * sk_motor__sy) / sk_motor__reach
          sk_motor__across = (sk_motor__ox * sk_motor__sy - sk_motor__oy * sk_motor__sx) / sk_motor__reach
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
    IF hasSpray = 0 OR k_contacts__best_cost < sk_motor__spray_range_sq THEN
      IF sk_motor__clear AND sk_motor__gun_wait = 0 THEN
        shootAt(sk_motor__tx, sk_motor__ty)
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

' Grenade: match the charge to the distance, never onto a visible friend (D/X classification,
' the thrower included). Sets sk_motor__threw = 1 on the tick the charge reaches the need.
SUB sk_motor__grenade()
  IF hasGrenade AND k_contacts__best >= 0 THEN
    sk_motor__nx = playerX(k_contacts__best)
    sk_motor__ny = playerY(k_contacts__best)
    sk_motor__dx = sk_motor__nx - selfX
    sk_motor__dy = sk_motor__ny - selfY
    sk_motor__d2 = sk_motor__dx * sk_motor__dx + sk_motor__dy * sk_motor__dy
    sk_motor__safe = 1
    sk_motor__i = 0
    WHILE sk_motor__i < 16
      IF k_contacts__friend(sk_motor__i) AND visible(sk_motor__i) THEN
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
      sk_motor__need = (sk_motor__root - 150) * 24 / 1130 + 1
      IF sk_motor__need < 1 THEN
        sk_motor__need = 1
      END IF
      lookAt(sk_motor__nx, sk_motor__ny)
      sk_motor__charging = grenadeCharge < sk_motor__need
      sk_motor__charge_x = sk_motor__nx
      sk_motor__charge_y = sk_motor__ny
      sk_motor__release_in = sk_motor__need - grenadeCharge
      IF sk_motor__release_in < 0 THEN
        sk_motor__release_in = 0
      END IF
      IF sk_motor__release_in > 24 THEN
        sk_motor__release_in = 24
      END IF
      chargeGrenade(sk_motor__charging)
      IF grenadeCharge >= sk_motor__need THEN
        sk_motor__threw = 1
      END IF
    END IF
  END IF
END SUB

' The whole per-tick motor tail, in the baseline's order. gx, gy: the goal point; hold: 1 when
' the cog stands on its post (the capability decides both).
SUB sk_motor__act(sk_motor_gx, sk_motor_gy, sk_motor_hold)
  sk_motor__threw = 0
  sk_motor__was_charging = sk_motor__charging
  sk_motor__charging = 0
  sk_motor__charge_started = 0
  sk_motor__quiet = 0
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
  sk_motor__footwork()
  sk_motor__avoid_grenades()
  IF sk_motor__evading THEN
    walkTo(sk_motor__move_x, sk_motor__move_y)
  ELSE
    sk_motor__dry_route()
  END IF
  sk_motor__gun()
  sk_motor__grenade()
  IF sk_motor__charging AND sk_motor__was_charging = 0 THEN
    sk_motor__charge_started = 1
  END IF
END SUB


' Capabilities keep their existing quiet predicate and call this after act.
SUB sk_motor__sneak(sk_motor_on)
  sk_motor__quiet = sk_motor_on
  sneak(sk_motor_on)
END SUB

' Prefer a point outside a reported blast zone when inside it or headed into it.
' This is a movement order, not a claim that the cog can leave instantly.
SUB sk_motor__avoid_grenades()
  sk_motor__evading = 0
  sk_motor__i = 0
  WHILE sk_motor__i < 4
    IF k_comms_danger__grenade_until(sk_motor__i) > worldTick THEN
      sk_motor__dx = selfX - k_comms_danger__grenade_x(sk_motor__i)
      sk_motor__dy = selfY - k_comms_danger__grenade_y(sk_motor__i)
      sk_motor__fx = sk_motor__move_x - k_comms_danger__grenade_x(sk_motor__i)
      sk_motor__fy = sk_motor__move_y - k_comms_danger__grenade_y(sk_motor__i)
      IF sk_motor__dx * sk_motor__dx + sk_motor__dy * sk_motor__dy < k_comms_danger__clear_radius * k_comms_danger__clear_radius OR sk_motor__fx * sk_motor__fx + sk_motor__fy * sk_motor__fy < k_comms_danger__clear_radius * k_comms_danger__clear_radius THEN
        sk_motor__isqrt(sk_motor__dx * sk_motor__dx + sk_motor__dy * sk_motor__dy)
        IF sk_motor__root = 0 THEN
          sk_motor__dx = 1 - 2 * selfTeam
          sk_motor__dy = 0
          sk_motor__root = 1
        END IF
        sk_motor__move_x = k_comms_danger__grenade_x(sk_motor__i) + sk_motor__dx * (k_comms_danger__clear_radius + 50) / sk_motor__root
        sk_motor__move_y = k_comms_danger__grenade_y(sk_motor__i) + sk_motor__dy * (k_comms_danger__clear_radius + 50) / sk_motor__root
        sk_motor__evading = 1
        sk_motor__dr_active = 0
      END IF
    END IF
    sk_motor__i = sk_motor__i + 1
  WEND
END SUB

' ==== K.self_motion ====
' unit K.self_motion sha256:d728b0e7a4b728c002b2f3aa5c914b09f3700b55ec2fdcf68dc431ba2ae10102 generated, do not edit
' Our own movement since the previous tick, and whether we lost hit points.
' Memory and scratch cells, kept in one array to stay under the 512-global budget:
' 0 last_x, 1 last_y, 2 last_hp, 3 last_uniform, 4 uni
DIM k_self_motion__t(4)

sub k_self_motion__init()
  k_self_motion__t(0) = selfX
  k_self_motion__t(1) = selfY
  k_self_motion__t(2) = selfHp
  k_self_motion__t(3) = 0
  k_self_motion__uniform_since = 0
end sub

sub k_self_motion__update()
  ' Step 1.
  k_self_motion__vx = selfX - k_self_motion__t(0)
  k_self_motion__vy = selfY - k_self_motion__t(1)
  ' Step 2: a respawn jump is not a velocity.
  if k_self_motion__vx > k_self_motion__teleport_step or k_self_motion__vx < 0 - k_self_motion__teleport_step or k_self_motion__vy > k_self_motion__teleport_step or k_self_motion__vy < 0 - k_self_motion__teleport_step then
    k_self_motion__vx = 0
    k_self_motion__vy = 0
    k_self_motion__teleported = 1
  else
    k_self_motion__teleported = 0
  end if
  ' Step 3.
  k_self_motion__t(0) = selfX
  k_self_motion__t(1) = selfY
  ' Step 4.
  if selfHp < k_self_motion__t(2) then
    k_self_motion__hp_drop = 1
  else
    k_self_motion__hp_drop = 0
  end if
  k_self_motion__t(2) = selfHp
  ' Step 5.
  k_self_motion__t(4) = hasUniform()
  if k_self_motion__t(4) = 1 and k_self_motion__t(3) = 0 then
    k_self_motion__uniform_since = worldTick + 1
  end if
  if k_self_motion__t(4) = 0 then
    k_self_motion__uniform_since = 0
  end if
  k_self_motion__t(3) = k_self_motion__t(4)
end sub

' ==== K.squad_target ====
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

' ==== K.contacts ====
' unit K.contacts sha256:dd0503229b475bdddad47f0c59c3efd21b7f5b45424c92afc027ac1abe60ee13 generated, do not edit
' The visible enemy we fight, friend and hostile classification of visible bodies, the visible
' enemy carrier, the local fight balance, and the freshest heard enemy.
DIM k_contacts__old_x(15)
DIM k_contacts__old_y(15)
DIM k_contacts__seen_tick(15)
DIM k_contacts__kf_x(15)
DIM k_contacts__kf_y(15)
DIM k_contacts__kf_src(15)
' Scratch cells, kept in one array to stay under the 512-global budget:
' 0 i/j, 1 px, 2 py, 3 done, 4 ex, 5 ey, 6 own_ev, 7 witness, 8 fx, 9 fy, 10 focus_best,
' 11 focus_cost, 12 foe_sum_x, 13 foe_sum_y, 14 dx, 15 dy, 16 d2, 17 cost, 18 bx, 19 by,
' 20 heard_age, 21 heard_best_t
DIM k_contacts__t(21)

sub k_contacts__update()
  ' Step 0: classification.
  k_contacts__xe_label = -1
  k_contacts__xe_x = 0
  k_contacts__xe_y = 0
  k_contacts__t(0) = 0
  while k_contacts__t(0) < 16
    k_contacts__friend(k_contacts__t(0)) = 0
    k_contacts__hostile(k_contacts__t(0)) = 0
    k_contacts__t(0) = k_contacts__t(0) + 1
  wend
  k_contacts__friend(selfId) = 1
  k_contacts__t(0) = 0
  while k_contacts__t(0) < 16
    if k_contacts__t(0) <> selfId and visible(k_contacts__t(0)) then
      k_contacts__t(1) = playerX(k_contacts__t(0))
      k_contacts__t(2) = playerY(k_contacts__t(0))
      k_contacts__t(3) = 0
      ' Step 0a: a friendly disguise record wins over everything else.
      if com_disguise_friend__df_until(k_contacts__t(0)) > worldTick then
        if com_disguise_friend__df_until(k_contacts__t(0)) <> k_contacts__kf_src(k_contacts__t(0)) then
          k_contacts__kf_x(k_contacts__t(0)) = com_disguise_friend__df_x(k_contacts__t(0))
          k_contacts__kf_y(k_contacts__t(0)) = com_disguise_friend__df_y(k_contacts__t(0))
          k_contacts__kf_src(k_contacts__t(0)) = com_disguise_friend__df_until(k_contacts__t(0))
        end if
        k_contacts__t(4) = k_contacts__t(1) - k_contacts__kf_x(k_contacts__t(0))
        k_contacts__t(5) = k_contacts__t(2) - k_contacts__kf_y(k_contacts__t(0))
        if k_contacts__t(4) * k_contacts__t(4) + k_contacts__t(5) * k_contacts__t(5) <= com_disguise_friend__friend_radius * com_disguise_friend__friend_radius then
          k_contacts__kf_x(k_contacts__t(0)) = k_contacts__t(1)
          k_contacts__kf_y(k_contacts__t(0)) = k_contacts__t(2)
          k_contacts__friend(k_contacts__t(0)) = 1
          k_contacts__t(3) = 1
        end if
      end if
      if k_contacts__t(3) = 0 then
        if k_contacts__t(0) mod 2 <> selfTeam then
          ' Step 0b: enemy parity.
          k_contacts__hostile(k_contacts__t(0)) = 1
        else
          ' Step 0c: teammate parity, unless corroborated as a fake.
          k_contacts__friend(k_contacts__t(0)) = 1
          k_contacts__t(6) = 0
          if cm__heard_t(k_contacts__t(0)) > 0 then
            if worldTick + 1 - cm__heard_t(k_contacts__t(0)) <= com_disguise_alert__x_window then
              k_contacts__t(4) = k_contacts__t(1) - cm__heard_x(k_contacts__t(0))
              k_contacts__t(5) = k_contacts__t(2) - cm__heard_y(k_contacts__t(0))
              if k_contacts__t(4) * k_contacts__t(4) + k_contacts__t(5) * k_contacts__t(5) > com_disguise_alert__x_distance * com_disguise_alert__x_distance then
                k_contacts__t(6) = 1
              end if
            end if
          end if
          k_contacts__t(7) = 0
          if com_disguise_alert__xa_amb(k_contacts__t(0)) = 0 and com_disguise_alert__xa_t1(k_contacts__t(0)) > worldTick and com_disguise_alert__xa_t2(k_contacts__t(0)) > worldTick and com_disguise_alert__xa_s1(k_contacts__t(0)) <> com_disguise_alert__xa_s2(k_contacts__t(0)) then
            k_contacts__t(4) = k_contacts__t(1) - com_disguise_alert__xa_x1(k_contacts__t(0))
            k_contacts__t(5) = k_contacts__t(2) - com_disguise_alert__xa_y1(k_contacts__t(0))
            k_contacts__t(8) = k_contacts__t(1) - com_disguise_alert__xa_x2(k_contacts__t(0))
            k_contacts__t(9) = k_contacts__t(2) - com_disguise_alert__xa_y2(k_contacts__t(0))
            if k_contacts__t(4) * k_contacts__t(4) + k_contacts__t(5) * k_contacts__t(5) <= com_disguise_alert__x_radius * com_disguise_alert__x_radius and k_contacts__t(8) * k_contacts__t(8) + k_contacts__t(9) * k_contacts__t(9) <= com_disguise_alert__x_radius * com_disguise_alert__x_radius then
              k_contacts__t(7) = 1
            end if
          end if
          if k_contacts__t(6) or k_contacts__t(7) then
            k_contacts__hostile(k_contacts__t(0)) = 1
            k_contacts__friend(k_contacts__t(0)) = 0
          end if
          if k_contacts__t(6) and k_contacts__xe_label < 0 and k_contacts__t(0) <> (selfId + 2) mod 16 then
            k_contacts__xe_label = k_contacts__t(0)
            k_contacts__xe_x = k_contacts__t(1)
            k_contacts__xe_y = k_contacts__t(2)
          end if
        end if
      end if
    end if
    k_contacts__t(0) = k_contacts__t(0) + 1
  wend

  ' Step 1.
  k_contacts__best = -1
  k_contacts__best_cost = 2147483647
  k_contacts__t(10) = -1
  k_contacts__t(11) = 2147483647
  k_contacts__thief = -1
  k_contacts__foes_near = 0
  k_contacts__friends_near = 1
  k_contacts__t(12) = 0
  k_contacts__t(13) = 0
  k_contacts__foes_seen = 0

  ' Step 2.
  k_contacts__t(0) = 0
  while k_contacts__t(0) < 16
    if k_contacts__t(0) <> selfId and visible(k_contacts__t(0)) then
      k_contacts__t(1) = playerX(k_contacts__t(0))
      k_contacts__t(2) = playerY(k_contacts__t(0))
      k_contacts__t(14) = k_contacts__t(1) - selfX
      k_contacts__t(15) = k_contacts__t(2) - selfY
      k_contacts__t(16) = k_contacts__t(14) * k_contacts__t(14) + k_contacts__t(15) * k_contacts__t(15)
      if k_contacts__hostile(k_contacts__t(0)) = 1 then
        k_contacts__t(17) = k_contacts__t(16) - (3 - playerHp(k_contacts__t(0))) * k_contacts__hp_weight
        if playerCarrying(k_contacts__t(0)) then
          k_contacts__t(17) = k_contacts__t(17) - k_contacts__carrier_bonus
          k_contacts__thief = k_contacts__t(0)
        end if
        if k_contacts__t(17) < k_contacts__best_cost and k_contacts__t(16) <= k_contacts__range_sq then
          k_contacts__best = k_contacts__t(0)
          k_contacts__best_cost = k_contacts__t(17)
        end if
        if com_focus_call__fc_until > worldTick and k_contacts__t(0) = com_focus_call__fc_label and k_contacts__t(16) <= k_contacts__range_sq then
          k_contacts__t(4) = k_contacts__t(1) - com_focus_call__fc_x
          k_contacts__t(5) = k_contacts__t(2) - com_focus_call__fc_y
          if k_contacts__t(4) * k_contacts__t(4) + k_contacts__t(5) * k_contacts__t(5) <= com_focus_call__focus_radius * com_focus_call__focus_radius and k_contacts__t(17) < k_contacts__t(11) then
            k_contacts__t(10) = k_contacts__t(0)
            k_contacts__t(11) = k_contacts__t(17)
          end if
        end if
        k_contacts__foes_seen = k_contacts__foes_seen + 1
        k_contacts__t(12) = k_contacts__t(12) + k_contacts__t(1)
        k_contacts__t(13) = k_contacts__t(13) + k_contacts__t(2)
        if k_contacts__t(16) < k_contacts__near_foe_sq then
          k_contacts__foes_near = k_contacts__foes_near + 1
        end if
      end if
      if k_contacts__friend(k_contacts__t(0)) = 1 then
        if k_contacts__t(16) < k_contacts__near_friend_sq then
          k_contacts__friends_near = k_contacts__friends_near + 1
        end if
      end if
    end if
    k_contacts__t(0) = k_contacts__t(0) + 1
  wend
  k_contacts__focus_used = 0
  if k_contacts__t(10) >= 0 then
    k_contacts__best = k_contacts__t(10)
    k_contacts__best_cost = k_contacts__t(11)
    k_contacts__focus_used = 1
  end if

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
  k_contacts__t(0) = 0
  while k_contacts__t(0) < 16
    if visible(k_contacts__t(0)) then
      k_contacts__old_x(k_contacts__t(0)) = playerX(k_contacts__t(0))
      k_contacts__old_y(k_contacts__t(0)) = playerY(k_contacts__t(0))
      k_contacts__seen_tick(k_contacts__t(0)) = worldTick
    end if
    k_contacts__t(0) = k_contacts__t(0) + 1
  wend
  if k_contacts__foes_seen > 0 then
    k_contacts__foe_cx = k_contacts__t(12) / k_contacts__foes_seen
    k_contacts__foe_cy = k_contacts__t(13) / k_contacts__foes_seen
  else
    k_contacts__foe_cx = 0
    k_contacts__foe_cy = 0
  end if

  ' Step 5: engagers.
  k_contacts__best_engagers = 0
  if k_contacts__best >= 0 then
    k_contacts__t(18) = playerX(k_contacts__best)
    k_contacts__t(19) = playerY(k_contacts__best)
    k_contacts__t(0) = 0
    while k_contacts__t(0) < 16
      if k_contacts__t(0) <> selfId and visible(k_contacts__t(0)) and k_contacts__friend(k_contacts__t(0)) = 1 then
        k_contacts__t(4) = playerX(k_contacts__t(0)) - k_contacts__t(18)
        k_contacts__t(5) = playerY(k_contacts__t(0)) - k_contacts__t(19)
        if k_contacts__t(4) * k_contacts__t(4) + k_contacts__t(5) * k_contacts__t(5) <= k_contacts__engage_range_sq then
          k_contacts__best_engagers = k_contacts__best_engagers + 1
        end if
      end if
      k_contacts__t(0) = k_contacts__t(0) + 1
    wend
  end if

  ' Step 6: the freshest heard enemy that is not in view.
  k_contacts__heard_target = -1
  k_contacts__heard_x = 0
  k_contacts__heard_y = 0
  k_contacts__t(20) = 0
  k_contacts__t(21) = 0
  k_contacts__t(0) = 0
  while k_contacts__t(0) < 16
    if com_enemy_sighting__ht_until(k_contacts__t(0)) > worldTick and visible(k_contacts__t(0)) = 0 and com_disguise_friend__df_until(k_contacts__t(0)) <= worldTick then
      if k_contacts__heard_target < 0 or com_enemy_sighting__ht_t(k_contacts__t(0)) > k_contacts__t(21) then
        k_contacts__heard_target = k_contacts__t(0)
        k_contacts__t(21) = com_enemy_sighting__ht_t(k_contacts__t(0))
        k_contacts__heard_x = com_enemy_sighting__ht_x(k_contacts__t(0))
        k_contacts__heard_y = com_enemy_sighting__ht_y(k_contacts__t(0))
      end if
    end if
    k_contacts__t(0) = k_contacts__t(0) + 1
  wend
end sub

' ==== K.pickups ====
' unit K.pickups sha256:078751acc541fdc6962b03cf3f128fe1087e86c9f6f8fea949bb1d83c7219521 generated, do not edit
' Supplies seen in the last ten seconds, the nearest one we want now, our own supply takes, and
' supplies that became ready.
DIM k_pickups__mem_x(63)
DIM k_pickups__mem_y(63)
DIM k_pickups__mem_kind(63)
DIM k_pickups__mem_tick(63)
DIM k_pickups__own_ready(63)
' State memory of the previous tick, kept in one array to stay under the 512-global budget:
' 0 x, 1 y, 2 grenade, 3 spray, 4 hp, 5 armor, 6 uniform, 7 mist, 8 sniper, 9 radar
DIM k_pickups__prev(9)
' Scratch cells: 0 n, 1 cur_uniform, 2 cur_mist, 3 cur_sniper, 4 cur_radar, 5 cands, 6 cand,
' 7 i/j, 8 dx, 9 dy, 10 kind, 11 chg, 12 found, 13 carrier, 14 nearest_cost, 15 vis, 16 skip,
' 17 wanted, 18 cost
DIM k_pickups__t(18)

sub k_pickups__init()
  k_pickups__taken_id = -1
  k_pickups__ready_id = -1
  k_pickups__prev(0) = selfX
  k_pickups__prev(1) = selfY
  k_pickups__prev(2) = hasGrenade
  k_pickups__prev(3) = hasSpray
  k_pickups__prev(4) = selfHp
  k_pickups__prev(5) = armorHp
  k_pickups__prev(6) = hasUniform()
  k_pickups__prev(7) = mistingTicks()
  k_pickups__prev(8) = hasSniper()
  k_pickups__prev(9) = radarTicks()
end sub

sub k_pickups__update()
  k_pickups__t(0) = pickupCount()
  k_pickups__t(1) = hasUniform()
  k_pickups__t(2) = mistingTicks()
  k_pickups__t(3) = hasSniper()
  k_pickups__t(4) = radarTicks()

  ' Step 0: own take, judged against the memory before this tick's refresh.
  k_pickups__t(5) = 0
  k_pickups__t(6) = -1
  k_pickups__t(7) = 0
  while k_pickups__t(7) < k_pickups__t(0) and k_pickups__t(7) < 64
    if k_pickups__mem_tick(k_pickups__t(7)) = worldTick then
      if pickupVisible(k_pickups__t(7)) = 0 then
        k_pickups__t(8) = k_pickups__mem_x(k_pickups__t(7)) - k_pickups__prev(0)
        k_pickups__t(9) = k_pickups__mem_y(k_pickups__t(7)) - k_pickups__prev(1)
        if k_pickups__t(8) * k_pickups__t(8) + k_pickups__t(9) * k_pickups__t(9) <= k_pickups__take_radius_sq then
          k_pickups__t(10) = k_pickups__mem_kind(k_pickups__t(7))
          k_pickups__t(11) = 0
          if k_pickups__t(10) = 0 then
            k_pickups__t(11) = hasGrenade = 1 and k_pickups__prev(2) = 0
          end if
          if k_pickups__t(10) = 1 then
            k_pickups__t(11) = hasSpray = 1 and k_pickups__prev(3) = 0
          end if
          if k_pickups__t(10) = 2 then
            k_pickups__t(11) = selfHp >= k_pickups__prev(4) + 2
          end if
          if k_pickups__t(10) = 3 then
            k_pickups__t(11) = armorHp = 3 and k_pickups__prev(5) < 3
          end if
          if k_pickups__t(10) = 4 then
            k_pickups__t(11) = k_pickups__t(1) = 1 and k_pickups__prev(6) = 0
          end if
          if k_pickups__t(10) = 5 then
            k_pickups__t(11) = k_pickups__t(2) > 0 and k_pickups__prev(7) = 0
          end if
          if k_pickups__t(10) = 6 then
            k_pickups__t(11) = k_pickups__t(3) = 1 and k_pickups__prev(8) = 0
          end if
          if k_pickups__t(10) = 7 then
            k_pickups__t(11) = k_pickups__t(4) > k_pickups__prev(9)
          end if
          if k_pickups__t(11) then
            k_pickups__t(5) = k_pickups__t(5) + 1
            k_pickups__t(6) = k_pickups__t(7)
          end if
        end if
      end if
    end if
    k_pickups__t(7) = k_pickups__t(7) + 1
  wend
  if k_pickups__t(5) = 1 then
    k_pickups__taken_id = k_pickups__t(6)
    k_pickups__taken_x = k_pickups__mem_x(k_pickups__t(6))
    k_pickups__taken_y = k_pickups__mem_y(k_pickups__t(6))
    k_pickups__taken_kind = k_pickups__mem_kind(k_pickups__t(6))
    k_pickups__taken_tick = worldTick
    if k_pickups__taken_kind = 0 then
      k_pickups__taken_ready_in = k_pickups__grenade_delay
    else
      k_pickups__taken_ready_in = k_pickups__supply_delay
    end if
    k_pickups__own_ready(k_pickups__t(6)) = worldTick + k_pickups__taken_ready_in
  end if

  ' Step 0b: the lowest station that became ready in view.
  k_pickups__t(12) = 0
  k_pickups__t(7) = 0
  while k_pickups__t(7) < k_pickups__t(0) and k_pickups__t(7) < 64 and k_pickups__t(12) = 0
    if pickupVisible(k_pickups__t(7)) then
      if k_pickups__mem_tick(k_pickups__t(7)) = 0 or k_pickups__own_ready(k_pickups__t(7)) > worldTick or com_pickup_taken__rk_until(k_pickups__t(7)) > worldTick then
        k_pickups__ready_id = k_pickups__t(7)
        k_pickups__ready_kind = pickupKind(k_pickups__t(7))
        k_pickups__ready_x = pickupX(k_pickups__t(7))
        k_pickups__ready_y = pickupY(k_pickups__t(7))
        k_pickups__ready_tick = worldTick
        k_pickups__t(12) = 1
      end if
    end if
    k_pickups__t(7) = k_pickups__t(7) + 1
  wend

  ' Step 0c: state memory.
  k_pickups__prev(0) = selfX
  k_pickups__prev(1) = selfY
  k_pickups__prev(2) = hasGrenade
  k_pickups__prev(3) = hasSpray
  k_pickups__prev(4) = selfHp
  k_pickups__prev(5) = armorHp
  k_pickups__prev(6) = k_pickups__t(1)
  k_pickups__prev(7) = k_pickups__t(2)
  k_pickups__prev(8) = k_pickups__t(3)
  k_pickups__prev(9) = k_pickups__t(4)

  ' Step 1: refresh the memory from what is in view, or from a newer ready report.
  k_pickups__t(7) = 0
  while k_pickups__t(7) < k_pickups__t(0) and k_pickups__t(7) < 64
    if pickupVisible(k_pickups__t(7)) then
      k_pickups__mem_x(k_pickups__t(7)) = pickupX(k_pickups__t(7))
      k_pickups__mem_y(k_pickups__t(7)) = pickupY(k_pickups__t(7))
      k_pickups__mem_kind(k_pickups__t(7)) = pickupKind(k_pickups__t(7))
      k_pickups__mem_tick(k_pickups__t(7)) = worldTick + 1
    else
      if com_pickup_ready__rr_t(k_pickups__t(7)) > k_pickups__mem_tick(k_pickups__t(7)) then
        k_pickups__mem_x(k_pickups__t(7)) = com_pickup_ready__rr_x(k_pickups__t(7))
        k_pickups__mem_y(k_pickups__t(7)) = com_pickup_ready__rr_y(k_pickups__t(7))
        k_pickups__mem_kind(k_pickups__t(7)) = com_pickup_ready__rr_kind(k_pickups__t(7))
        k_pickups__mem_tick(k_pickups__t(7)) = com_pickup_ready__rr_t(k_pickups__t(7))
        k_pickups__own_ready(k_pickups__t(7)) = 0
      end if
    end if
    k_pickups__t(7) = k_pickups__t(7) + 1
  wend

  ' Step 2: a visible enemy carrier.
  k_pickups__t(13) = 0
  k_pickups__t(7) = 0
  while k_pickups__t(7) < 16
    if k_pickups__t(7) <> selfId and visible(k_pickups__t(7)) and k_pickups__t(7) mod 2 <> selfTeam and playerCarrying(k_pickups__t(7)) then
      k_pickups__t(13) = 1
    end if
    k_pickups__t(7) = k_pickups__t(7) + 1
  wend

  ' Step 3: choice.
  k_pickups__nearest = -1
  k_pickups__nearest_x = 0
  k_pickups__nearest_y = 0
  if not carrying and k_pickups__t(13) = 0 then
    k_pickups__t(14) = k_pickups__reach_sq
    k_pickups__t(7) = 0
    while k_pickups__t(7) < k_pickups__t(0) and k_pickups__t(7) < 64
      if k_pickups__mem_tick(k_pickups__t(7)) > 0 and worldTick - k_pickups__mem_tick(k_pickups__t(7)) < k_pickups__memory_ticks then
        k_pickups__t(15) = pickupVisible(k_pickups__t(7))
        k_pickups__t(16) = 0
        if k_pickups__t(15) = 0 then
          if k_pickups__own_ready(k_pickups__t(7)) > worldTick then
            k_pickups__t(16) = 1
          end if
          if com_pickup_taken__rk_until(k_pickups__t(7)) > worldTick and com_pickup_taken__rk_t(k_pickups__t(7)) >= com_pickup_ready__rr_t(k_pickups__t(7)) then
            k_pickups__t(16) = 1
          end if
        end if
        if k_pickups__t(16) = 0 then
          k_pickups__t(10) = k_pickups__mem_kind(k_pickups__t(7))
          k_pickups__t(17) = (k_pickups__t(10) = 0 and not hasGrenade) or (k_pickups__t(10) = 2 and selfHp < 3) or (k_pickups__t(10) = 3 and armorHp < 3 and selfHp = 3)
          if k_pickups__t(17) then
            k_pickups__t(8) = k_pickups__mem_x(k_pickups__t(7)) - selfX
            k_pickups__t(9) = k_pickups__mem_y(k_pickups__t(7)) - selfY
            k_pickups__t(18) = k_pickups__t(8) * k_pickups__t(8) + k_pickups__t(9) * k_pickups__t(9)
            if k_pickups__t(10) = 2 and selfHp = 1 then
              k_pickups__t(18) = k_pickups__t(18) / 4
            end if
            if k_pickups__t(18) < k_pickups__arrive_sq and k_pickups__t(15) = 0 then
              k_pickups__mem_tick(k_pickups__t(7)) = 0
            else
              if k_pickups__t(18) < k_pickups__t(14) then
                k_pickups__nearest = k_pickups__t(7)
                k_pickups__t(14) = k_pickups__t(18)
              end if
            end if
          end if
        end if
      end if
      k_pickups__t(7) = k_pickups__t(7) + 1
    wend
    if k_pickups__nearest >= 0 then
      k_pickups__nearest_x = k_pickups__mem_x(k_pickups__nearest)
      k_pickups__nearest_y = k_pickups__mem_y(k_pickups__nearest)
    end if
  end if
end sub

' ==== K.comms_danger ====
' unit K.comms_danger sha256:c775c0ad3680892749969efb905bc02bf5abc1186ffdb8459d2be55a1f6b87b6 generated, do not edit
' Live grenade zones and the most recent under-fire area that teammates reported.
sub k_comms_danger__update()
  ' Step 1: grenade zones.
  k_comms_danger__zone_count = 0
  k_comms_danger__i = 0
  while k_comms_danger__i < 4
    k_comms_danger__grenade_x(k_comms_danger__i) = com_grenade_warning__gz_x(k_comms_danger__i)
    k_comms_danger__grenade_y(k_comms_danger__i) = com_grenade_warning__gz_y(k_comms_danger__i)
    k_comms_danger__grenade_until(k_comms_danger__i) = com_grenade_warning__gz_until(k_comms_danger__i)
    if com_grenade_warning__gz_until(k_comms_danger__i) <= worldTick then
      k_comms_danger__grenade_until(k_comms_danger__i) = 0
    end if
    if k_comms_danger__grenade_until(k_comms_danger__i) > worldTick then
      k_comms_danger__zone_count = k_comms_danger__zone_count + 1
    end if
    k_comms_danger__i = k_comms_danger__i + 1
  wend
  ' Step 2: the latest under-fire report.
  if com_under_fire__du_until > worldTick then
    k_comms_danger__danger_x = com_under_fire__du_x
    k_comms_danger__danger_y = com_under_fire__du_y
    k_comms_danger__danger_dir = com_under_fire__du_dir
    k_comms_danger__danger_until = com_under_fire__du_until
  else
    k_comms_danger__danger_x = 0
    k_comms_danger__danger_y = 0
    k_comms_danger__danger_dir = 0
    k_comms_danger__danger_until = 0
  end if
end sub

' ==== K.glory_hearts ====
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

' ==== S.losing_fight ====
' unit S.losing_fight sha256:26fa46be62e5cbe4549707e0ad8de2284b1b020f3fbbf5a06e33c15e6f295024 generated, do not edit
' We see more near enemies than near friends, so we refuse the fight.
sub s_losing_fight__eval()
  if k_contacts__foes_near - k_contacts__friends_near >= 1 and not carrying and k_squad_target__heart_count > 0 then
    s_losing_fight__on = 1
  else
    s_losing_fight__on = 0
  end if
end sub

' ==== S.supply_worth ====
' unit S.supply_worth sha256:562c4fb00dccbe7c5d7f9de4ad3a11e02cae113f436963f0381c63bf9cce40da generated, do not edit
' A wanted supply is remembered and no close fight stops us from fetching it.
sub s_supply_worth__eval()
  if k_pickups__nearest >= 0 and (k_contacts__best < 0 or k_contacts__best_cost > s_supply_worth__fight_clear_sq or selfHp = 1) then
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

' ==== C.take_heart ====
' unit C.take_heart sha256:7551b976d16fc3e69a716f65cb13b303e01ec2ddcaf42ee2f89133677ce83273 generated, do not edit
' Stand in the capture ring of the squad target (squad seats 0 and 1).
' Scratch cells, kept in one array to stay under the 512-global budget:
' 0 goal_x, 1 goal_y, 2 dx, 3 dy, 4 hold, 5 qx, 6 qy
DIM c_take_heart__t(6)

sub c_take_heart__start()
end sub

sub c_take_heart__tick()
  ' Step 1.
  c_take_heart__t(0) = controlX(k_squad_target__objective)
  c_take_heart__t(1) = controlY(k_squad_target__objective)
  ' Step 2.
  c_take_heart__t(2) = c_take_heart__t(0) - selfX
  c_take_heart__t(3) = c_take_heart__t(1) - selfY
  if c_take_heart__t(2) * c_take_heart__t(2) + c_take_heart__t(3) * c_take_heart__t(3) < c_take_heart__hold_sq then
    c_take_heart__t(4) = 1
  else
    c_take_heart__t(4) = 0
  end if
  ' Step 3.
  sk_motor__act(c_take_heart__t(0), c_take_heart__t(1), c_take_heart__t(4))
  ' Step 4: quiet approach when nothing is in sight but something was heard.
  if k_contacts__best < 0 and soundCount() > 0 then
    c_take_heart__t(5) = controlX(k_squad_target__objective) - selfX
    c_take_heart__t(6) = controlY(k_squad_target__objective) - selfY
    if c_take_heart__t(5) * c_take_heart__t(5) + c_take_heart__t(6) * c_take_heart__t(6) < c_take_heart__quiet_sq then
      sk_motor__sneak(1)
    end if
  end if
  ' Step 5.
  c_take_heart__status = 0
end sub

' ==== C.cover_heart ====
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

' ==== C.default_goal ====
' unit C.default_goal sha256:ddffaf0bea84c53624c78255164499994b4b6d23197b3e08a77c3309ff96bc84 generated, do not edit
' With no squad target, go for the thief, home, or the heart.
' Scratch cells, kept in one array to stay under the 512-global budget:
' 0 goal_x, 1 goal_y, 2 qx, 3 qy
DIM c_default_goal__t(3)

sub c_default_goal__start()
end sub

sub c_default_goal__tick()
  ' Step 1.
  if carrying then
    if ownHeartStolen and k_contacts__thief >= 0 then
      c_default_goal__t(0) = playerX(k_contacts__thief)
      c_default_goal__t(1) = playerY(k_contacts__thief)
    else
      c_default_goal__t(0) = homeX
      c_default_goal__t(1) = homeY
    end if
  else
    if k_contacts__thief >= 0 then
      c_default_goal__t(0) = playerX(k_contacts__thief)
      c_default_goal__t(1) = playerY(k_contacts__thief)
    else
      c_default_goal__t(0) = heartX
      c_default_goal__t(1) = heartY
    end if
  end if
  ' Step 2.
  sk_motor__act(c_default_goal__t(0), c_default_goal__t(1), 0)
  ' Step 3: quiet approach when nothing is in sight but something was heard.
  if k_contacts__best < 0 and soundCount() > 0 and k_squad_target__objective >= 0 then
    c_default_goal__t(2) = controlX(k_squad_target__objective) - selfX
    c_default_goal__t(3) = controlY(k_squad_target__objective) - selfY
    if c_default_goal__t(2) * c_default_goal__t(2) + c_default_goal__t(3) * c_default_goal__t(3) < c_default_goal__quiet_sq then
      sk_motor__sneak(1)
    end if
  end if
  ' Step 4.
  c_default_goal__status = 0
end sub

' ==== C.resupply ====
' unit C.resupply sha256:9ef584118d9cd4b76ed605e9aa2af6d4b5dbc239c7161a408a95da1bda8bb117 generated, do not edit
' Walk to the remembered supply.
' Scratch cells, kept in one array to stay under the 512-global budget: 0 qx, 1 qy
DIM c_resupply__t(1)

sub c_resupply__start()
end sub

sub c_resupply__tick()
  ' Step 1.
  sk_motor__act(k_pickups__nearest_x, k_pickups__nearest_y, 0)
  ' Step 2: quiet approach when nothing is in sight but something was heard.
  if k_contacts__best < 0 and soundCount() > 0 and k_squad_target__objective >= 0 then
    c_resupply__t(0) = controlX(k_squad_target__objective) - selfX
    c_resupply__t(1) = controlY(k_squad_target__objective) - selfY
    if c_resupply__t(0) * c_resupply__t(0) + c_resupply__t(1) * c_resupply__t(1) < c_resupply__quiet_sq then
      sk_motor__sneak(1)
    end if
  end if
  ' Step 3.
  c_resupply__status = 0
end sub

' ==== C.fall_back ====
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

' ==== COM.disguise_friend ====
' unit COM.disguise_friend sha256:621bcc7eb48bdb466cd72022b56f05fd7703ef536bd0095caf1268a692185399 generated, do not edit
' Tell teammates that our disguised body is a friend, and keep their friend records.
' Memory and scratch cells, kept in one array to stay under the 512-global budget:
' 0 ds_t (starts at 0), 1 mate, 2 i, 3 dx, 4 dy, 5 label, 6 l
DIM com_disguise_friend__t(6)

sub com_disguise_friend__send()
  if k_self_motion__uniform_since > 0 then
    ' A teammate-parity body in view within hearing range.
    com_disguise_friend__t(1) = 0
    com_disguise_friend__t(2) = 0
    while com_disguise_friend__t(2) < 16
      if com_disguise_friend__t(2) <> selfId and com_disguise_friend__t(2) mod 2 = selfTeam and visible(com_disguise_friend__t(2)) then
        com_disguise_friend__t(3) = playerX(com_disguise_friend__t(2)) - selfX
        com_disguise_friend__t(4) = playerY(com_disguise_friend__t(2)) - selfY
        if com_disguise_friend__t(3) * com_disguise_friend__t(3) + com_disguise_friend__t(4) * com_disguise_friend__t(4) <= com_disguise_friend__d_range_sq then
          com_disguise_friend__t(1) = 1
        end if
      end if
      com_disguise_friend__t(2) = com_disguise_friend__t(2) + 1
    wend
    if com_disguise_friend__t(1) = 1 then
      if com_disguise_friend__t(0) < k_self_motion__uniform_since or worldTick + 1 - com_disguise_friend__t(0) >= com_disguise_friend__d_refresh then
        com_disguise_friend__t(5) = selfId + 1 - 2 * (selfId mod 2)
        cm__send(8, com_disguise_friend__t(5), 0, 0, sk_motor__quiet)
        if cm__sent = 1 then
          com_disguise_friend__t(0) = worldTick + 1
        end if
      end if
    end if
  end if
end sub

sub com_disguise_friend__recv()
  com_disguise_friend__t(6) = cm__fa
  if com_disguise_friend__t(6) >= 0 and com_disguise_friend__t(6) < 16 then
    if com_disguise_friend__t(6) = selfId then
      com_disguise_friend__t(6) = (com_disguise_friend__t(6) + 2) mod 16
    end if
    com_disguise_friend__df_x(com_disguise_friend__t(6)) = cm__rx_x
    com_disguise_friend__df_y(com_disguise_friend__t(6)) = cm__rx_y
    com_disguise_friend__df_until(com_disguise_friend__t(6)) = worldTick + com_disguise_friend__friend_ttl
  end if
end sub

' ==== COM.disguise_alert ====
' unit COM.disguise_alert sha256:4a819094b97327ff43f33b50cce0ab9e133d3a990d4b9105f3d65e862039d617 generated, do not edit
' Report uncertain disguise evidence and keep distinct witness reports.
DIM com_disguise_alert__xs_t(15)
' Scratch cells, kept in one array to stay under the 512-global budget:
' 0 l, 1 ex, 2 ey, 3 age, 4 k, 5 w, 6 h, 7 gx, 8 gy, 9 cell, 10 amb, 11 until, 12 px, 13 py,
' 14 dx, 15 dy
DIM com_disguise_alert__t(15)

sub com_disguise_alert__send()
  com_disguise_alert__t(0) = -1
  if k_contacts__xe_label >= 0 and k_contacts__xe_label < 16 then
    ' Strong evidence: our own conflicting position.
    com_disguise_alert__t(0) = k_contacts__xe_label
    com_disguise_alert__t(1) = k_contacts__xe_x
    com_disguise_alert__t(2) = k_contacts__xe_y
    com_disguise_alert__t(3) = worldTick + 1 - cm__heard_t(com_disguise_alert__t(0))
  else
    ' Weak evidence: the lowest label whose speech failed the message check.
    com_disguise_alert__t(4) = 0
    while com_disguise_alert__t(4) < 16
      if com_disguise_alert__t(0) < 0 and com_disguise_alert__t(4) <> selfId and com_disguise_alert__t(4) <> (selfId + 2) mod 16 then
        if cm__suspect_t(com_disguise_alert__t(4)) > 0 then
          if worldTick + 1 - cm__suspect_t(com_disguise_alert__t(4)) <= com_disguise_alert__x_window then
            com_disguise_alert__t(0) = com_disguise_alert__t(4)
            com_disguise_alert__t(1) = cm__suspect_x(com_disguise_alert__t(4))
            com_disguise_alert__t(2) = cm__suspect_y(com_disguise_alert__t(4))
            com_disguise_alert__t(3) = worldTick + 1 - cm__suspect_t(com_disguise_alert__t(4))
          end if
        end if
      end if
      com_disguise_alert__t(4) = com_disguise_alert__t(4) + 1
    wend
  end if
  if com_disguise_alert__t(0) >= 0 then
    if com_disguise_alert__xs_t(com_disguise_alert__t(0)) = 0 or worldTick + 1 - com_disguise_alert__xs_t(com_disguise_alert__t(0)) >= com_disguise_alert__x_refresh then
      if com_disguise_alert__t(3) < 0 then
        com_disguise_alert__t(3) = 0
      end if
      if com_disguise_alert__t(3) > 255 then
        com_disguise_alert__t(3) = 255
      end if
      ' Cell of the point.
      com_disguise_alert__t(5) = mapMaxX() - mapMinX() + 1
      com_disguise_alert__t(6) = mapMaxY() - mapMinY() + 1
      com_disguise_alert__t(7) = 0
      com_disguise_alert__t(8) = 0
      if com_disguise_alert__t(5) > 0 then
        com_disguise_alert__t(7) = (com_disguise_alert__t(1) - mapMinX()) * 256 / com_disguise_alert__t(5)
      end if
      if com_disguise_alert__t(6) > 0 then
        com_disguise_alert__t(8) = (com_disguise_alert__t(2) - mapMinY()) * 256 / com_disguise_alert__t(6)
      end if
      if com_disguise_alert__t(7) < 0 then
        com_disguise_alert__t(7) = 0
      end if
      if com_disguise_alert__t(7) > 255 then
        com_disguise_alert__t(7) = 255
      end if
      if com_disguise_alert__t(8) < 0 then
        com_disguise_alert__t(8) = 0
      end if
      if com_disguise_alert__t(8) > 255 then
        com_disguise_alert__t(8) = 255
      end if
      com_disguise_alert__t(9) = com_disguise_alert__t(7) + 256 * com_disguise_alert__t(8)
      cm__send(7, com_disguise_alert__t(0), com_disguise_alert__t(3), com_disguise_alert__t(9), sk_motor__quiet)
      if cm__sent = 1 then
        com_disguise_alert__xs_t(com_disguise_alert__t(0)) = worldTick + 1
      end if
    end if
  end if
end sub

sub com_disguise_alert__recv()
  com_disguise_alert__t(0) = cm__fa
  com_disguise_alert__t(10) = 0
  com_disguise_alert__t(11) = worldTick - 1 - cm__fb + com_disguise_alert__disguise_ttl
  if com_disguise_alert__t(11) <= worldTick then
    exit sub
  end if
  if com_disguise_alert__t(0) < 0 or com_disguise_alert__t(0) > 15 then
    exit sub
  end if
  if com_disguise_alert__t(0) = selfId then
    com_disguise_alert__t(0) = (com_disguise_alert__t(0) + 2) mod 16
    com_disguise_alert__t(10) = 1
  end if
  ' Point of the cell.
  com_disguise_alert__t(5) = mapMaxX() - mapMinX() + 1
  com_disguise_alert__t(6) = mapMaxY() - mapMinY() + 1
  com_disguise_alert__t(7) = cm__cell mod 256
  com_disguise_alert__t(8) = cm__cell / 256
  com_disguise_alert__t(12) = mapMinX() + (com_disguise_alert__t(7) * com_disguise_alert__t(5) + com_disguise_alert__t(5) / 2) / 256
  com_disguise_alert__t(13) = mapMinY() + (com_disguise_alert__t(8) * com_disguise_alert__t(6) + com_disguise_alert__t(6) / 2) / 256
  ' Both witnesses expired: the label is no longer ambiguous.
  if com_disguise_alert__xa_t1(com_disguise_alert__t(0)) <= worldTick and com_disguise_alert__xa_t2(com_disguise_alert__t(0)) <= worldTick then
    com_disguise_alert__xa_amb(com_disguise_alert__t(0)) = 0
  end if
  if com_disguise_alert__t(10) = 1 then
    com_disguise_alert__xa_amb(com_disguise_alert__t(0)) = 1
  end if
  if com_disguise_alert__xa_t1(com_disguise_alert__t(0)) <= worldTick or (com_disguise_alert__xa_s1(com_disguise_alert__t(0)) = cm__speaker and com_disguise_alert__t(11) > com_disguise_alert__xa_t1(com_disguise_alert__t(0))) then
    com_disguise_alert__xa_s1(com_disguise_alert__t(0)) = cm__speaker
    com_disguise_alert__xa_x1(com_disguise_alert__t(0)) = com_disguise_alert__t(12)
    com_disguise_alert__xa_y1(com_disguise_alert__t(0)) = com_disguise_alert__t(13)
    com_disguise_alert__xa_t1(com_disguise_alert__t(0)) = com_disguise_alert__t(11)
    ' One sender never fills both witnesses.
    if com_disguise_alert__xa_s2(com_disguise_alert__t(0)) = cm__speaker then
      com_disguise_alert__xa_t2(com_disguise_alert__t(0)) = 0
    end if
  else
    if com_disguise_alert__xa_s1(com_disguise_alert__t(0)) <> cm__speaker then
      com_disguise_alert__t(14) = com_disguise_alert__t(12) - com_disguise_alert__xa_x1(com_disguise_alert__t(0))
      com_disguise_alert__t(15) = com_disguise_alert__t(13) - com_disguise_alert__xa_y1(com_disguise_alert__t(0))
      if com_disguise_alert__t(14) * com_disguise_alert__t(14) + com_disguise_alert__t(15) * com_disguise_alert__t(15) <= com_disguise_alert__x_radius * com_disguise_alert__x_radius then
        if com_disguise_alert__xa_t2(com_disguise_alert__t(0)) <= worldTick or (com_disguise_alert__xa_s2(com_disguise_alert__t(0)) = cm__speaker and com_disguise_alert__t(11) > com_disguise_alert__xa_t2(com_disguise_alert__t(0))) then
          com_disguise_alert__xa_s2(com_disguise_alert__t(0)) = cm__speaker
          com_disguise_alert__xa_x2(com_disguise_alert__t(0)) = com_disguise_alert__t(12)
          com_disguise_alert__xa_y2(com_disguise_alert__t(0)) = com_disguise_alert__t(13)
          com_disguise_alert__xa_t2(com_disguise_alert__t(0)) = com_disguise_alert__t(11)
        end if
      end if
    end if
  end if
end sub

' ==== COM.focus_call ====
' unit COM.focus_call sha256:529883ffcc80e960109b683a91937354c691918bfd270b48d72a7e36786ab40b generated, do not edit
' Call our fight target so that teammates who see it prefer it.
' Memory and scratch cells, kept in one array to stay under the 512-global budget:
' 0 fs_label, 1 fs_t, 2 b, 3 hp, 4 w, 5 h, 6 gx, 7 gy, 8 cell
DIM com_focus_call__t(8)

sub com_focus_call__init()
  com_focus_call__t(0) = -1
  com_focus_call__fc_label = -1
end sub

sub com_focus_call__send()
  com_focus_call__t(2) = k_contacts__best
  if com_focus_call__t(2) >= 0 then
    com_focus_call__t(3) = playerHp(com_focus_call__t(2))
    if (com_focus_call__t(3) < com_focus_call__full_hp or k_contacts__best_engagers >= 2) and (com_focus_call__t(0) <> com_focus_call__t(2) or worldTick - com_focus_call__t(1) >= com_focus_call__focus_refresh) then
      if com_focus_call__t(3) < 0 then
        com_focus_call__t(3) = 0
      end if
      if com_focus_call__t(3) > 15 then
        com_focus_call__t(3) = 15
      end if
      ' Cell of the target.
      com_focus_call__t(4) = mapMaxX() - mapMinX() + 1
      com_focus_call__t(5) = mapMaxY() - mapMinY() + 1
      com_focus_call__t(6) = 0
      com_focus_call__t(7) = 0
      if com_focus_call__t(4) > 0 then
        com_focus_call__t(6) = (playerX(com_focus_call__t(2)) - mapMinX()) * 256 / com_focus_call__t(4)
      end if
      if com_focus_call__t(5) > 0 then
        com_focus_call__t(7) = (playerY(com_focus_call__t(2)) - mapMinY()) * 256 / com_focus_call__t(5)
      end if
      if com_focus_call__t(6) < 0 then
        com_focus_call__t(6) = 0
      end if
      if com_focus_call__t(6) > 255 then
        com_focus_call__t(6) = 255
      end if
      if com_focus_call__t(7) < 0 then
        com_focus_call__t(7) = 0
      end if
      if com_focus_call__t(7) > 255 then
        com_focus_call__t(7) = 255
      end if
      com_focus_call__t(8) = com_focus_call__t(6) + 256 * com_focus_call__t(7)
      cm__send(1, com_focus_call__t(2) + 16 * com_focus_call__t(3), 0, com_focus_call__t(8), sk_motor__quiet)
      if cm__sent = 1 then
        com_focus_call__t(0) = com_focus_call__t(2)
        com_focus_call__t(1) = worldTick
      end if
    end if
  end if
end sub

sub com_focus_call__recv()
  com_focus_call__fc_label = cm__fa mod 16
  if com_focus_call__fc_label < 0 then
    com_focus_call__fc_label = com_focus_call__fc_label + 16
  end if
  ' Point of the cell.
  com_focus_call__t(4) = mapMaxX() - mapMinX() + 1
  com_focus_call__t(5) = mapMaxY() - mapMinY() + 1
  com_focus_call__t(6) = cm__cell mod 256
  com_focus_call__t(7) = cm__cell / 256
  com_focus_call__fc_x = mapMinX() + (com_focus_call__t(6) * com_focus_call__t(4) + com_focus_call__t(4) / 2) / 256
  com_focus_call__fc_y = mapMinY() + (com_focus_call__t(7) * com_focus_call__t(5) + com_focus_call__t(5) / 2) / 256
  com_focus_call__fc_until = worldTick + com_focus_call__focus_ttl
end sub

' ==== COM.glory_seen ====
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

' ==== COM.enemy_sighting ====
' unit COM.enemy_sighting sha256:4329fbd900ebaef2085dac732bf4d8992177cd6da171a694e7b06ee6e3202af6 generated, do not edit
' Report a visible enemy to teammates, and keep heard enemy tracks.
DIM com_enemy_sighting__es_t(15)
DIM com_enemy_sighting__es_x(15)
DIM com_enemy_sighting__es_y(15)
' Scratch cells, kept in one array to stay under the 512-global budget:
' 0 mates, 1 s, 2 pick, 3 pick_cost, 4 i, 5 bx, 6 by, 7 dx, 8 dy, 9 cost, 10 d2, 11 hp, 12 w,
' 13 h, 14 gx, 15 gy, 16 cell, 17 l, 18 seen
DIM com_enemy_sighting__t(18)

sub com_enemy_sighting__send()
  ' Is any teammate heard recently enough to place it?
  com_enemy_sighting__t(0) = 0
  com_enemy_sighting__t(1) = 0
  while com_enemy_sighting__t(1) < 16
    if com_enemy_sighting__t(1) <> selfId and com_enemy_sighting__t(1) mod 2 = selfTeam then
      if cm__heard_t(com_enemy_sighting__t(1)) > 0 then
        if worldTick + 1 - cm__heard_t(com_enemy_sighting__t(1)) <= com_enemy_sighting__heard_ttl then
          com_enemy_sighting__t(0) = 1
        end if
      end if
    end if
    com_enemy_sighting__t(1) = com_enemy_sighting__t(1) + 1
  wend
  com_enemy_sighting__t(2) = -1
  com_enemy_sighting__t(3) = 2147483647
  com_enemy_sighting__t(4) = 0
  while com_enemy_sighting__t(4) < 16
    if com_enemy_sighting__t(4) <> selfId and visible(com_enemy_sighting__t(4)) and k_contacts__hostile(com_enemy_sighting__t(4)) = 1 then
      com_enemy_sighting__t(5) = playerX(com_enemy_sighting__t(4))
      com_enemy_sighting__t(6) = playerY(com_enemy_sighting__t(4))
      com_enemy_sighting__t(7) = com_enemy_sighting__t(5) - com_enemy_sighting__es_x(com_enemy_sighting__t(4))
      com_enemy_sighting__t(8) = com_enemy_sighting__t(6) - com_enemy_sighting__es_y(com_enemy_sighting__t(4))
      if com_enemy_sighting__es_t(com_enemy_sighting__t(4)) = 0 or worldTick + 1 - com_enemy_sighting__es_t(com_enemy_sighting__t(4)) >= com_enemy_sighting__e_refresh or com_enemy_sighting__t(7) * com_enemy_sighting__t(7) + com_enemy_sighting__t(8) * com_enemy_sighting__t(8) > com_enemy_sighting__e_move * com_enemy_sighting__e_move then
        if com_enemy_sighting__t(0) = 1 then
          ' Distance to the nearest recently heard teammate.
          com_enemy_sighting__t(9) = 2147483647
          com_enemy_sighting__t(1) = 0
          while com_enemy_sighting__t(1) < 16
            if com_enemy_sighting__t(1) <> selfId and com_enemy_sighting__t(1) mod 2 = selfTeam then
              if cm__heard_t(com_enemy_sighting__t(1)) > 0 then
                if worldTick + 1 - cm__heard_t(com_enemy_sighting__t(1)) <= com_enemy_sighting__heard_ttl then
                  com_enemy_sighting__t(7) = com_enemy_sighting__t(5) - cm__heard_x(com_enemy_sighting__t(1))
                  com_enemy_sighting__t(8) = com_enemy_sighting__t(6) - cm__heard_y(com_enemy_sighting__t(1))
                  com_enemy_sighting__t(10) = com_enemy_sighting__t(7) * com_enemy_sighting__t(7) + com_enemy_sighting__t(8) * com_enemy_sighting__t(8)
                  if com_enemy_sighting__t(10) < com_enemy_sighting__t(9) then
                    com_enemy_sighting__t(9) = com_enemy_sighting__t(10)
                  end if
                end if
              end if
            end if
            com_enemy_sighting__t(1) = com_enemy_sighting__t(1) + 1
          wend
        else
          com_enemy_sighting__t(7) = com_enemy_sighting__t(5) - selfX
          com_enemy_sighting__t(8) = com_enemy_sighting__t(6) - selfY
          com_enemy_sighting__t(9) = com_enemy_sighting__t(7) * com_enemy_sighting__t(7) + com_enemy_sighting__t(8) * com_enemy_sighting__t(8)
        end if
        if com_enemy_sighting__t(2) < 0 or com_enemy_sighting__t(9) < com_enemy_sighting__t(3) then
          com_enemy_sighting__t(2) = com_enemy_sighting__t(4)
          com_enemy_sighting__t(3) = com_enemy_sighting__t(9)
        end if
      end if
    end if
    com_enemy_sighting__t(4) = com_enemy_sighting__t(4) + 1
  wend
  if com_enemy_sighting__t(2) >= 0 then
    com_enemy_sighting__t(5) = playerX(com_enemy_sighting__t(2))
    com_enemy_sighting__t(6) = playerY(com_enemy_sighting__t(2))
    com_enemy_sighting__t(11) = playerHp(com_enemy_sighting__t(2))
    if com_enemy_sighting__t(11) < 0 then
      com_enemy_sighting__t(11) = 0
    end if
    if com_enemy_sighting__t(11) > 15 then
      com_enemy_sighting__t(11) = 15
    end if
    ' Cell of the body.
    com_enemy_sighting__t(12) = mapMaxX() - mapMinX() + 1
    com_enemy_sighting__t(13) = mapMaxY() - mapMinY() + 1
    com_enemy_sighting__t(14) = 0
    com_enemy_sighting__t(15) = 0
    if com_enemy_sighting__t(12) > 0 then
      com_enemy_sighting__t(14) = (com_enemy_sighting__t(5) - mapMinX()) * 256 / com_enemy_sighting__t(12)
    end if
    if com_enemy_sighting__t(13) > 0 then
      com_enemy_sighting__t(15) = (com_enemy_sighting__t(6) - mapMinY()) * 256 / com_enemy_sighting__t(13)
    end if
    if com_enemy_sighting__t(14) < 0 then
      com_enemy_sighting__t(14) = 0
    end if
    if com_enemy_sighting__t(14) > 255 then
      com_enemy_sighting__t(14) = 255
    end if
    if com_enemy_sighting__t(15) < 0 then
      com_enemy_sighting__t(15) = 0
    end if
    if com_enemy_sighting__t(15) > 255 then
      com_enemy_sighting__t(15) = 255
    end if
    com_enemy_sighting__t(16) = com_enemy_sighting__t(14) + 256 * com_enemy_sighting__t(15)
    cm__send(0, com_enemy_sighting__t(2) + 16 * (com_enemy_sighting__t(11) + 16 * 8), 0, com_enemy_sighting__t(16), sk_motor__quiet)
    if cm__sent = 1 then
      com_enemy_sighting__es_t(com_enemy_sighting__t(2)) = worldTick + 1
      com_enemy_sighting__es_x(com_enemy_sighting__t(2)) = com_enemy_sighting__t(5)
      com_enemy_sighting__es_y(com_enemy_sighting__t(2)) = com_enemy_sighting__t(6)
    end if
  end if
end sub

sub com_enemy_sighting__recv()
  com_enemy_sighting__t(17) = cm__fa mod 16
  if com_enemy_sighting__t(17) < 0 then
    com_enemy_sighting__t(17) = com_enemy_sighting__t(17) + 16
  end if
  com_enemy_sighting__t(18) = worldTick - 1 - cm__fb
  ' An older or equal sighting never refreshes a track.
  if com_enemy_sighting__ht_until(com_enemy_sighting__t(17)) = 0 or com_enemy_sighting__t(18) > com_enemy_sighting__ht_t(com_enemy_sighting__t(17)) then
    com_enemy_sighting__t(12) = mapMaxX() - mapMinX() + 1
    com_enemy_sighting__t(13) = mapMaxY() - mapMinY() + 1
    com_enemy_sighting__t(14) = cm__cell mod 256
    com_enemy_sighting__t(15) = cm__cell / 256
    com_enemy_sighting__ht_x(com_enemy_sighting__t(17)) = mapMinX() + (com_enemy_sighting__t(14) * com_enemy_sighting__t(12) + com_enemy_sighting__t(12) / 2) / 256
    com_enemy_sighting__ht_y(com_enemy_sighting__t(17)) = mapMinY() + (com_enemy_sighting__t(15) * com_enemy_sighting__t(13) + com_enemy_sighting__t(13) / 2) / 256
    com_enemy_sighting__ht_t(com_enemy_sighting__t(17)) = com_enemy_sighting__t(18)
    com_enemy_sighting__ht_until(com_enemy_sighting__t(17)) = com_enemy_sighting__t(18) + com_enemy_sighting__heard_ttl
  end if
end sub

' ==== COM.grenade_warning ====
' unit COM.grenade_warning sha256:2ac13417e4f4d9e23b9c98e7b45d9237071e9504d64275774060847acdc10e96 generated, do not edit
' Warn teammates where our grenade will land, and keep their warnings.
' Memory and scratch cells, kept in one array to stay under the 512-global budget:
' 0 gs_x, 1 gs_y, 2 gs_until, 3 dx, 4 dy, 5 w, 6 h, 7 gx, 8 gy, 9 cell, 10 px, 11 py, 12 k, 13 j
DIM com_grenade_warning__t(13)

sub com_grenade_warning__send()
  if sk_motor__charging = 1 then
    com_grenade_warning__t(3) = sk_motor__charge_x - com_grenade_warning__t(0)
    com_grenade_warning__t(4) = sk_motor__charge_y - com_grenade_warning__t(1)
    if sk_motor__charge_started = 1 or com_grenade_warning__t(2) <= worldTick or com_grenade_warning__t(3) * com_grenade_warning__t(3) + com_grenade_warning__t(4) * com_grenade_warning__t(4) > com_grenade_warning__g_move * com_grenade_warning__g_move then
      ' Cell of the landing point.
      com_grenade_warning__t(5) = mapMaxX() - mapMinX() + 1
      com_grenade_warning__t(6) = mapMaxY() - mapMinY() + 1
      com_grenade_warning__t(7) = 0
      com_grenade_warning__t(8) = 0
      if com_grenade_warning__t(5) > 0 then
        com_grenade_warning__t(7) = (sk_motor__charge_x - mapMinX()) * 256 / com_grenade_warning__t(5)
      end if
      if com_grenade_warning__t(6) > 0 then
        com_grenade_warning__t(8) = (sk_motor__charge_y - mapMinY()) * 256 / com_grenade_warning__t(6)
      end if
      if com_grenade_warning__t(7) < 0 then
        com_grenade_warning__t(7) = 0
      end if
      if com_grenade_warning__t(7) > 255 then
        com_grenade_warning__t(7) = 255
      end if
      if com_grenade_warning__t(8) < 0 then
        com_grenade_warning__t(8) = 0
      end if
      if com_grenade_warning__t(8) > 255 then
        com_grenade_warning__t(8) = 255
      end if
      com_grenade_warning__t(9) = com_grenade_warning__t(7) + 256 * com_grenade_warning__t(8)
      cm__send(2, sk_motor__release_in, 0, com_grenade_warning__t(9), sk_motor__quiet)
      if cm__sent = 1 then
        com_grenade_warning__t(0) = sk_motor__charge_x
        com_grenade_warning__t(1) = sk_motor__charge_y
        com_grenade_warning__t(2) = worldTick + sk_motor__release_in + 24
      end if
    end if
  end if
end sub

sub com_grenade_warning__recv()
  ' Point of the cell.
  com_grenade_warning__t(5) = mapMaxX() - mapMinX() + 1
  com_grenade_warning__t(6) = mapMaxY() - mapMinY() + 1
  com_grenade_warning__t(7) = cm__cell mod 256
  com_grenade_warning__t(8) = cm__cell / 256
  com_grenade_warning__t(10) = mapMinX() + (com_grenade_warning__t(7) * com_grenade_warning__t(5) + com_grenade_warning__t(5) / 2) / 256
  com_grenade_warning__t(11) = mapMinY() + (com_grenade_warning__t(8) * com_grenade_warning__t(6) + com_grenade_warning__t(6) / 2) / 256
  ' The zone slot that expires first.
  com_grenade_warning__t(12) = 0
  com_grenade_warning__t(13) = 1
  while com_grenade_warning__t(13) < 4
    if com_grenade_warning__gz_until(com_grenade_warning__t(13)) < com_grenade_warning__gz_until(com_grenade_warning__t(12)) then
      com_grenade_warning__t(12) = com_grenade_warning__t(13)
    end if
    com_grenade_warning__t(13) = com_grenade_warning__t(13) + 1
  wend
  com_grenade_warning__gz_x(com_grenade_warning__t(12)) = com_grenade_warning__t(10)
  com_grenade_warning__gz_y(com_grenade_warning__t(12)) = com_grenade_warning__t(11)
  com_grenade_warning__gz_until(com_grenade_warning__t(12)) = worldTick - 1 + cm__fa + 24
end sub

' ==== COM.under_fire ====
' unit COM.under_fire sha256:8dd3e9fc032475fe2b27b87f983657ad46da95ac91808977b82acba5b66edb81 generated, do not edit
' Report that we lose hit points and see no enemy, and keep the latest such report.
' Scratch cells, kept in one array to stay under the 512-global budget:
' 0 dir, 1 dist, 2 best_age, 3 i, 4 age, 5 hp
DIM com_under_fire__t(5)

sub com_under_fire__send()
  if k_self_motion__hp_drop = 1 and k_contacts__foes_seen = 0 then
    ' The freshest gun sound.
    com_under_fire__t(0) = 8
    com_under_fire__t(1) = 3
    com_under_fire__t(2) = 2147483647
    com_under_fire__t(3) = 0
    while com_under_fire__t(3) < soundCount() and com_under_fire__t(3) < 12
      if soundKind(com_under_fire__t(3)) = 1 then
        com_under_fire__t(4) = soundAge(com_under_fire__t(3))
        if com_under_fire__t(4) < com_under_fire__t(2) then
          com_under_fire__t(2) = com_under_fire__t(4)
          com_under_fire__t(0) = soundDirection(com_under_fire__t(3))
          com_under_fire__t(1) = soundDistance(com_under_fire__t(3))
        end if
      end if
      com_under_fire__t(3) = com_under_fire__t(3) + 1
    wend
    com_under_fire__t(5) = selfHp
    if com_under_fire__t(5) < 0 then
      com_under_fire__t(5) = 0
    end if
    if com_under_fire__t(5) > 15 then
      com_under_fire__t(5) = 15
    end if
    cm__send(3, com_under_fire__t(5) + 16 * com_under_fire__t(0), com_under_fire__t(1), 0, sk_motor__quiet)
  end if
end sub

sub com_under_fire__recv()
  com_under_fire__du_x = cm__rx_x
  com_under_fire__du_y = cm__rx_y
  com_under_fire__du_dir = cm__fa / 16
  com_under_fire__du_until = worldTick + com_under_fire__danger_ttl
end sub

' ==== COM.pickup_taken ====
' unit COM.pickup_taken sha256:a17bf6ff53ee210a97d2d377451bb5f6464a1fdb7c54cf157a6fb72518f067b8 generated, do not edit
' Report a supply we took, and keep teammates' reports of taken supplies.
' Memory and scratch cells, kept in one array to stay under the 512-global budget:
' 0 ks_tick, 1 left, 2 w, 3 h, 4 gx, 5 gy, 6 cell, 7 j
DIM com_pickup_taken__t(7)

sub com_pickup_taken__send()
  if k_pickups__taken_id >= 0 and k_pickups__taken_tick + 1 > com_pickup_taken__t(0) and worldTick - k_pickups__taken_tick <= com_pickup_taken__event_window then
    com_pickup_taken__t(1) = k_pickups__taken_ready_in - (worldTick - k_pickups__taken_tick)
    if com_pickup_taken__t(1) < 0 then
      com_pickup_taken__t(1) = 0
    end if
    if com_pickup_taken__t(1) > 720 then
      com_pickup_taken__t(1) = 720
    end if
    ' Cell of the station.
    com_pickup_taken__t(2) = mapMaxX() - mapMinX() + 1
    com_pickup_taken__t(3) = mapMaxY() - mapMinY() + 1
    com_pickup_taken__t(4) = 0
    com_pickup_taken__t(5) = 0
    if com_pickup_taken__t(2) > 0 then
      com_pickup_taken__t(4) = (k_pickups__taken_x - mapMinX()) * 256 / com_pickup_taken__t(2)
    end if
    if com_pickup_taken__t(3) > 0 then
      com_pickup_taken__t(5) = (k_pickups__taken_y - mapMinY()) * 256 / com_pickup_taken__t(3)
    end if
    if com_pickup_taken__t(4) < 0 then
      com_pickup_taken__t(4) = 0
    end if
    if com_pickup_taken__t(4) > 255 then
      com_pickup_taken__t(4) = 255
    end if
    if com_pickup_taken__t(5) < 0 then
      com_pickup_taken__t(5) = 0
    end if
    if com_pickup_taken__t(5) > 255 then
      com_pickup_taken__t(5) = 255
    end if
    com_pickup_taken__t(6) = com_pickup_taken__t(4) + 256 * com_pickup_taken__t(5)
    cm__send(5, k_pickups__taken_id, com_pickup_taken__t(1), com_pickup_taken__t(6), sk_motor__quiet)
    if cm__sent = 1 then
      com_pickup_taken__t(0) = k_pickups__taken_tick + 1
    end if
  end if
end sub

sub com_pickup_taken__recv()
  com_pickup_taken__t(7) = cm__fa
  if com_pickup_taken__t(7) >= 0 and com_pickup_taken__t(7) < 64 then
    com_pickup_taken__rk_until(com_pickup_taken__t(7)) = worldTick - 1 + cm__fb
    com_pickup_taken__rk_t(com_pickup_taken__t(7)) = worldTick
  end if
end sub

' ==== COM.pickup_ready ====
' unit COM.pickup_ready sha256:e3f7157eb590f40fe1191aa7b38837ae92ea2de93a5f21d0e328d33d1f1bf7aa generated, do not edit
' Report a supply that became ready, and keep teammates' ready reports.
' Memory and scratch cells, kept in one array to stay under the 512-global budget:
' 0 rs_tick, 1 w, 2 h, 3 gx, 4 gy, 5 cell, 6 j
DIM com_pickup_ready__t(6)

sub com_pickup_ready__send()
  if k_pickups__ready_id >= 0 then
    if k_pickups__ready_tick + 1 > com_pickup_ready__t(0) and worldTick - k_pickups__ready_tick <= com_pickup_ready__event_window and pickupVisible(k_pickups__ready_id) then
      ' Cell of the station.
      com_pickup_ready__t(1) = mapMaxX() - mapMinX() + 1
      com_pickup_ready__t(2) = mapMaxY() - mapMinY() + 1
      com_pickup_ready__t(3) = 0
      com_pickup_ready__t(4) = 0
      if com_pickup_ready__t(1) > 0 then
        com_pickup_ready__t(3) = (k_pickups__ready_x - mapMinX()) * 256 / com_pickup_ready__t(1)
      end if
      if com_pickup_ready__t(2) > 0 then
        com_pickup_ready__t(4) = (k_pickups__ready_y - mapMinY()) * 256 / com_pickup_ready__t(2)
      end if
      if com_pickup_ready__t(3) < 0 then
        com_pickup_ready__t(3) = 0
      end if
      if com_pickup_ready__t(3) > 255 then
        com_pickup_ready__t(3) = 255
      end if
      if com_pickup_ready__t(4) < 0 then
        com_pickup_ready__t(4) = 0
      end if
      if com_pickup_ready__t(4) > 255 then
        com_pickup_ready__t(4) = 255
      end if
      com_pickup_ready__t(5) = com_pickup_ready__t(3) + 256 * com_pickup_ready__t(4)
      cm__send(6, k_pickups__ready_id + 256 * k_pickups__ready_kind, 0, com_pickup_ready__t(5), sk_motor__quiet)
      if cm__sent = 1 then
        com_pickup_ready__t(0) = k_pickups__ready_tick + 1
      end if
    end if
  end if
end sub

sub com_pickup_ready__recv()
  com_pickup_ready__t(6) = cm__fa mod 256
  if com_pickup_ready__t(6) >= 0 and com_pickup_ready__t(6) < 64 then
    com_pickup_ready__rr_kind(com_pickup_ready__t(6)) = cm__fa / 256
    ' Point of the cell.
    com_pickup_ready__t(1) = mapMaxX() - mapMinX() + 1
    com_pickup_ready__t(2) = mapMaxY() - mapMinY() + 1
    com_pickup_ready__t(3) = cm__cell mod 256
    com_pickup_ready__t(4) = cm__cell / 256
    com_pickup_ready__rr_x(com_pickup_ready__t(6)) = mapMinX() + (com_pickup_ready__t(3) * com_pickup_ready__t(1) + com_pickup_ready__t(1) / 2) / 256
    com_pickup_ready__rr_y(com_pickup_ready__t(6)) = mapMinY() + (com_pickup_ready__t(4) * com_pickup_ready__t(2) + com_pickup_ready__t(2) / 2) / 256
    com_pickup_ready__rr_t(com_pickup_ready__t(6)) = worldTick
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

