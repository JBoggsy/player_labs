' unit C.focus_attack sha256:a1579cc7cb949a0bd7c62080163d79964f9be30620462b4d8252f64875c8da48 generated, do not edit
SUB c_focus_attack__start()
END SUB

SUB c_focus_attack__tick()
  c_focus_attack__dx = playerX(k_contacts__best) - selfX
  c_focus_attack__dy = playerY(k_contacts__best) - selfY
  sk_motor__isqrt(c_focus_attack__dx * c_focus_attack__dx + c_focus_attack__dy * c_focus_attack__dy)
  c_focus_attack__distance = sk_motor__root
  c_focus_attack__reach = c_focus_attack__gun_standoff
  IF hasSpray THEN
    c_focus_attack__reach = c_focus_attack__spray_standoff
  END IF
  c_focus_attack__goal_x = selfX
  c_focus_attack__goal_y = selfY
  c_focus_attack__hold = 1
  IF c_focus_attack__distance > c_focus_attack__reach AND c_focus_attack__distance > 0 THEN
    c_focus_attack__goal_x = playerX(k_contacts__best) - c_focus_attack__dx * c_focus_attack__reach \ c_focus_attack__distance
    c_focus_attack__goal_y = playerY(k_contacts__best) - c_focus_attack__dy * c_focus_attack__reach \ c_focus_attack__distance
    c_focus_attack__hold = 0
  END IF
  sk_motor__focus_act(c_focus_attack__goal_x, c_focus_attack__goal_y, c_focus_attack__hold)
  c_focus_attack__status = 0
END SUB
