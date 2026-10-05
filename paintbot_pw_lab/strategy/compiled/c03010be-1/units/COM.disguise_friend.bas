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
