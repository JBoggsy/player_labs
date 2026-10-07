' unit K.counter_phase sha256:f4272e3b00cf7c4e60b9ef96ed0be2097b56a83a6949006c55409728f47950a3 generated, do not edit
DIM k_counter_phase__was_capturing(63)

SUB k_counter_phase__init()
  k_counter_phase__phase = 0
  k_counter_phase__trigger = 0
  k_counter_phase__release_tick = 0
  k_counter_phase__stage_ticks = 0
  k_counter_phase__counter_ticks = 0
  k_counter_phase__split_heart = -1
  k_counter_phase__target = 9 - selfTeam
  k_counter_phase__armed = 0
END SUB

SUB k_counter_phase__update()
  IF heartCount() = 10 AND worldTick >= k_counter_phase__start_tick THEN
    IF k_counter_phase__phase = 0 THEN
      IF worldTick >= k_counter_phase__stage_deadline THEN
        k_counter_phase__phase = 3
        k_counter_phase__trigger = 2
      ELSE
        k_counter_phase__phase = 1
        k_counter_phase__j = 0
        WHILE k_counter_phase__j < heartCount() AND k_counter_phase__j < 64
          k_counter_phase__was_capturing(k_counter_phase__j) = 0
          IF controlCaptureTeam(k_counter_phase__j) = 1 - selfTeam AND controlCaptureTicks(k_counter_phase__j) > 0 THEN
            k_counter_phase__was_capturing(k_counter_phase__j) = 1
          END IF
          k_counter_phase__j = k_counter_phase__j + 1
        WEND
        k_counter_phase__armed = 1
      END IF
    ELSE
      IF k_counter_phase__phase = 1 THEN
        k_counter_phase__stage_ticks = k_counter_phase__stage_ticks + 1
        k_counter_phase__split_heart = -1
        k_counter_phase__j = 0
        WHILE k_counter_phase__j < heartCount() AND k_counter_phase__j < 64
          k_counter_phase__active = 0
          IF controlCaptureTeam(k_counter_phase__j) = 1 - selfTeam AND controlCaptureTicks(k_counter_phase__j) > 0 THEN
            k_counter_phase__active = 1
          END IF
          IF k_counter_phase__active = 1 AND k_counter_phase__was_capturing(k_counter_phase__j) = 0 AND worldTick >= k_counter_phase__earliest_release AND controlOwner(k_counter_phase__target) = 1 - selfTeam AND k_counter_phase__split_heart = -1 THEN
            k_counter_phase__dx = controlX(k_counter_phase__j) - controlX(k_counter_phase__target)
            k_counter_phase__dy = controlY(k_counter_phase__j) - controlY(k_counter_phase__target)
            IF k_counter_phase__dx * k_counter_phase__dx + k_counter_phase__dy * k_counter_phase__dy >= k_counter_phase__split_distance_sq THEN
              k_counter_phase__split_heart = k_counter_phase__j
            END IF
          END IF
          k_counter_phase__was_capturing(k_counter_phase__j) = k_counter_phase__active
          k_counter_phase__j = k_counter_phase__j + 1
        WEND
        IF k_counter_phase__split_heart >= 0 THEN
          k_counter_phase__phase = 2
          k_counter_phase__trigger = 1
          k_counter_phase__release_tick = worldTick
        ELSE
          IF worldTick >= k_counter_phase__stage_deadline THEN
            k_counter_phase__phase = 3
            k_counter_phase__trigger = 2
            k_counter_phase__release_tick = worldTick
          END IF
        END IF
      END IF
      IF k_counter_phase__phase = 2 THEN
        IF worldTick - k_counter_phase__release_tick >= k_counter_phase__counter_duration THEN
          k_counter_phase__phase = 3
        ELSE
          k_counter_phase__counter_ticks = k_counter_phase__counter_ticks + 1
        END IF
      END IF
    END IF
  END IF
END SUB
