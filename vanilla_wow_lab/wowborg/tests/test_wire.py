from wowborg.crypt import HeaderCrypt
from wowborg.wire import ByteReader, ByteWriter, build_client_packet, parse_server_header


def test_byte_primitives_and_strings() -> None:
    writer = ByteWriter()
    writer.add_u8(0xAA)
    writer.add_u16_le(0x1234)
    writer.add_u16_be(0x5678)
    writer.add_u32_le(0x12345678)
    writer.add_u32_be(0x90ABCDEF)
    writer.add_u64_le(0x0102030405060708)
    writer.add_f32_le(1.5)
    writer.add_cstring("Cow")
    writer.add_fixed_ascii("WoW", 4)
    writer.add_reversed_fourcc("x86")
    writer.add_reversed_fourcc("enUS")

    reader = ByteReader(writer.finish())
    assert reader.read_u8() == 0xAA
    assert reader.read_u16_le() == 0x1234
    assert reader.read_u16_be() == 0x5678
    assert reader.read_u32_le() == 0x12345678
    assert reader.read_u32_be() == 0x90ABCDEF
    assert reader.read_u64_le() == 0x0102030405060708
    assert reader.read_f32_le() == 1.5
    assert reader.read_cstring() == "Cow"
    assert reader.read_bytes(4) == b"WoW\x00"
    assert reader.read_bytes(4).hex() == "36387800"
    assert reader.read_bytes(4).hex() == "53556e65"


def test_client_and_server_packet_framing() -> None:
    assert build_client_packet(493, b"abc", encrypted=False).hex() == "0007ed010000616263"

    crypt = HeaderCrypt(bytes(range(40)))
    assert build_client_packet(493, b"abc", crypt, encrypted=True).hex() == "0006f5f7fb00616263"

    opcode, body_len = parse_server_header(bytes.fromhex("0005dd00"), encrypted=False)
    assert opcode == 221
    assert body_len == 3

    server_send = HeaderCrypt(bytes(range(40)))
    header = bytearray(bytes.fromhex("0005dd00"))
    server_send.encrypt_send(header)
    client_recv = HeaderCrypt(bytes(range(40)))
    assert parse_server_header(bytes(header), client_recv, encrypted=True) == (221, 3)
