' unit S.refuse_counter sha256:6686985b7d27ceb745c9a487709c7790e49dd9c196ba0664eb0e44469e5d75b7 generated, do not edit
SUB s_refuse_counter__eval()
  IF k_opening_signature__map_known = 1 AND k_opening_signature__route_class = 2 AND (k_counter_phase__phase = 1 OR k_counter_phase__phase = 2) AND k_pickups__critical = 0 THEN
    s_refuse_counter__on = 1
  ELSE
    s_refuse_counter__on = 0
  END IF
END SUB
