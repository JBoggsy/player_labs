"""Vanilla world header cipher, ported from ``game_client/crypts.nim``."""

from __future__ import annotations


class HeaderCrypt:
    """Mutable send/receive header cipher state."""

    def __init__(self, key: bytes) -> None:
        if not key:
            raise ValueError("world header crypt key must not be empty")
        self.key = bytes(key)
        self.send_index = 0
        self.send_prev = 0
        self.recv_index = 0
        self.recv_prev = 0

    def encrypt_send(self, data: bytearray) -> None:
        """Encrypt a client packet header in place."""

        for i, value in enumerate(data):
            key_index = self.send_index % len(self.key)
            encrypted = ((value ^ self.key[key_index]) + self.send_prev) & 0xFF
            self.send_index += 1
            self.send_prev = encrypted
            data[i] = encrypted

    def decrypt_recv(self, data: bytearray) -> None:
        """Decrypt a server packet header in place."""

        for i, encrypted in enumerate(data):
            key_index = self.recv_index % len(self.key)
            data[i] = (((encrypted + 256 - self.recv_prev) & 0xFF) ^ self.key[key_index]) & 0xFF
            self.recv_index += 1
            self.recv_prev = encrypted
