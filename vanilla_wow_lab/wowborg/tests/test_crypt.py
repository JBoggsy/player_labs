from wowborg.crypt import HeaderCrypt


def test_header_crypt_vectors_and_endpoint_symmetry() -> None:
    key = bytes(range(40))
    header = bytearray(bytes.fromhex("001122334455"))
    crypt = HeaderCrypt(key)
    crypt.encrypt_send(header)
    assert header.hex() == "00103060a0f0"

    # The same object's recv side is independent; decrypting its own send bytes
    # happens to work only because recv state is still at zero, not because send
    # state rewound.
    matching_peer = HeaderCrypt(key)
    matching_peer.decrypt_recv(header)
    assert header.hex() == "001122334455"

    sender = HeaderCrypt(key)
    receiver = HeaderCrypt(key)
    packet1 = bytearray(b"\x00\x02\xdd\x00")
    packet2 = bytearray(b"\x00\x04\xee\x00")
    sender.encrypt_send(packet1)
    sender.encrypt_send(packet2)
    assert packet1.hex() == "0003e2e5"
    assert packet2.hex() == "e9ead2d9"
    receiver.decrypt_recv(packet1)
    receiver.decrypt_recv(packet2)
    assert bytes(packet1) == b"\x00\x02\xdd\x00"
    assert bytes(packet2) == b"\x00\x04\xee\x00"
