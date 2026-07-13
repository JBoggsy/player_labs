from wowborg.srp6 import compute_proof, compute_verifier, compute_x, crc_hash


N = int(
    "e487eb3bce8c142837159563d838a86fd17419c6cdc7d9d636b5b7d7550a54dd",
    16,
).to_bytes(32, "little")
G = b"\x07"
SALT = bytes.fromhex("00112233445566778899aabbccddeeff102132435465768798a9bacbdcedfe0f")
A_PRIVATE = bytes.fromhex("0102030405060708090a0b0c0d0e0f10111213")
B = bytes.fromhex("9a48b0bf4467e27726ac9d76d620cba0e92356fb425c693f3e58644da785390f")


def test_srp6_deterministic_vector() -> None:
    proof = compute_proof("coworld", "secret", B=B, g=G, N=N, salt=SALT, a=A_PRIVATE)
    assert proof.A.hex() == "dc269f97127055f57db20231a3cd206b41dfed8ed0978492d1377c19016e6448"
    assert proof.M1.hex() == "320feca9fef01dba6427e1e786b15eea60556086"
    assert proof.K.hex() == "512b847161cbf04c92195f23f8d7ab23eb864c39524f61728c5b6033a87b073d2fd8788ea8388d39"
    assert proof.crc.hex() == "5c4920425702f62f49c165032e3bc31d7cb00cf1"


def test_crc_hash_uses_win_x86_5875_integrity_constant() -> None:
    A = bytes.fromhex("dc269f97127055f57db20231a3cd206b41dfed8ed0978492d1377c19016e6448")
    assert crc_hash(A).hex() == "5c4920425702f62f49c165032e3bc31d7cb00cf1"


def test_x_and_verifier_are_stable() -> None:
    assert compute_x("coworld", "secret", SALT) == 815060554109440607327197639589470586604802232620
    assert compute_verifier("coworld", "secret", g=G, N=N, salt=SALT).hex() == (
        "38c295af557466b9f1885f97cca6d6db14c46c0b9c693137ff9c7432021db803"
    )
