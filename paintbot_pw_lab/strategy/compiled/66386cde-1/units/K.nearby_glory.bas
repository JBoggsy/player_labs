' unit K.nearby_glory sha256:be1ef4bf68f1dcfe8fc35b5987eddd9daa6ed4d00ffd0087679ad128cff4fb31 generated, do not edit
sub k_nearby_glory__update()
  k_nearby_glory__nearest = -1
  k_nearby_glory__goal_x = 0
  k_nearby_glory__goal_y = 0
  k_nearby_glory__best_d2 = k_nearby_glory__reach_sq
  k_nearby_glory__j = 0
  while k_nearby_glory__j < gloryHeartCount() and k_nearby_glory__j < 64
    k_nearby_glory__ttl = gloryHeartTicksLeft(k_nearby_glory__j)
    if k_nearby_glory__ttl >= k_nearby_glory__min_ttl then
      k_nearby_glory__x = gloryHeartX(k_nearby_glory__j)
      k_nearby_glory__y = gloryHeartY(k_nearby_glory__j)
      k_nearby_glory__dx = k_nearby_glory__x - selfX
      k_nearby_glory__dy = k_nearby_glory__y - selfY
      k_nearby_glory__d2 = k_nearby_glory__dx * k_nearby_glory__dx + k_nearby_glory__dy * k_nearby_glory__dy
      if k_nearby_glory__d2 < k_nearby_glory__best_d2 then
        k_nearby_glory__assigned = 1
        k_nearby_glory__i = 0
        while k_nearby_glory__i < 16
          if k_nearby_glory__i <> selfId and k_nearby_glory__i mod 2 = selfTeam and visible(k_nearby_glory__i) then
            k_nearby_glory__ally_dx = playerX(k_nearby_glory__i) - k_nearby_glory__x
            k_nearby_glory__ally_dy = playerY(k_nearby_glory__i) - k_nearby_glory__y
            k_nearby_glory__ally_d2 = k_nearby_glory__ally_dx * k_nearby_glory__ally_dx + k_nearby_glory__ally_dy * k_nearby_glory__ally_dy
            if k_nearby_glory__ally_d2 < k_nearby_glory__d2 or (k_nearby_glory__ally_d2 = k_nearby_glory__d2 and k_nearby_glory__i < selfId) then
              k_nearby_glory__assigned = 0
            end if
          end if
          k_nearby_glory__i = k_nearby_glory__i + 1
        wend
        if k_nearby_glory__assigned = 1 then
          k_nearby_glory__nearest = k_nearby_glory__j
          k_nearby_glory__goal_x = k_nearby_glory__x
          k_nearby_glory__goal_y = k_nearby_glory__y
          k_nearby_glory__best_d2 = k_nearby_glory__d2
        end if
      end if
    end if
    k_nearby_glory__j = k_nearby_glory__j + 1
  wend
end sub
