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
