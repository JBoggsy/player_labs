' unit S.focus_attack sha256:7893d59be8c5aa5d2a109a578ff601936e204d39b447820653aea0d565569f48 generated, do not edit
SUB s_focus_attack__eval()
  s_focus_attack__on = 0
  IF k_contacts__focus_ready = 1 AND carrying = 0 THEN
    s_focus_attack__on = 1
  END IF
  IF k_squad_target__objective >= 0 AND k_squad_target__objective < heartCount() AND k_squad_target__objective < 64 THEN
    IF controlCaptureTeam(k_squad_target__objective) = selfTeam THEN
      s_focus_attack__dx = controlX(k_squad_target__objective) - selfX
      s_focus_attack__dy = controlY(k_squad_target__objective) - selfY
      IF s_focus_attack__dx * s_focus_attack__dx + s_focus_attack__dy * s_focus_attack__dy <= s_focus_attack__capture_lock_sq THEN
        s_focus_attack__on = 0
      END IF
    END IF
  END IF
END SUB
