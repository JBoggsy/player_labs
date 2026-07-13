from wowborg import opcodes


def test_oracle_constants_are_pinned() -> None:
    assert opcodes.AUTH_PROTOCOL_VERSION == 8
    assert opcodes.CLIENT_BUILD == 5875
    assert opcodes.CMD_AUTH_LOGON_CHALLENGE == 0x00
    assert opcodes.CMD_AUTH_LOGON_PROOF == 0x01
    assert opcodes.CMD_REALM_LIST == 0x10
    assert opcodes.SMSG_AUTH_CHALLENGE == 492
    assert opcodes.CMSG_AUTH_SESSION == 493
    assert opcodes.SMSG_AUTH_RESPONSE == 494
    assert opcodes.CMSG_CHAR_ENUM == 55
    assert opcodes.SMSG_CHAR_ENUM == 59
    assert opcodes.CMSG_PLAYER_LOGIN == 61
    assert opcodes.SMSG_LOGIN_VERIFY_WORLD == 566
    assert opcodes.SMSG_CHARACTER_LOGIN_FAILED == 65
    assert opcodes.MSG_MOVE_WORLDPORT_ACK == 220
    assert opcodes.CMSG_SET_ACTIVE_MOVER == 618
    assert opcodes.CMSG_PING == 476
    assert opcodes.SMSG_PONG == 477
    assert opcodes.SRP_NUMBER == 32
    assert opcodes.SRP_DIGEST == 20
    assert opcodes.SRP_SESSION == 40
    assert opcodes.SRP_MULTIPLIER == 3
    assert opcodes.SRP_PRIVATE == 19
