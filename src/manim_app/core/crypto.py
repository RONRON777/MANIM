"""AES-256 helpers for encrypting sensitive fields."""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


NONCE_SIZE = 12
KEY_SIZE = 32


@dataclass
class CryptoService:
    """Encrypts and decrypts text using AES-256-GCM."""

    key: bytes

    @classmethod
    def from_base64_key(cls, key_b64: str) -> "CryptoService":
        key = base64.urlsafe_b64decode(key_b64.encode("utf-8"))
        if len(key) != KEY_SIZE:
            raise RuntimeError("Encryption key must decode to 32 bytes for AES-256.")
        return cls(key=key)

    @staticmethod
    def generate_base64_key() -> str:
        """Generate a base64-encoded 32-byte key."""
        return base64.urlsafe_b64encode(os.urandom(KEY_SIZE)).decode("utf-8")

    def encrypt_text(self, plain_text: str) -> bytes:
        """Encrypt UTF-8 text and return nonce+ciphertext bytes."""
        nonce = os.urandom(NONCE_SIZE)
        aes_gcm = AESGCM(self.key)
        cipher_text = aes_gcm.encrypt(nonce, plain_text.encode("utf-8"), None)
        return nonce + cipher_text

    def decrypt_text(self, encrypted: bytes) -> str:
        """Decrypt nonce+ciphertext bytes into UTF-8 text."""
        nonce = encrypted[:NONCE_SIZE]
        cipher_text = encrypted[NONCE_SIZE:]
        aes_gcm = AESGCM(self.key)
        plain = aes_gcm.decrypt(nonce, cipher_text, None)
        return plain.decode("utf-8")


def mask_rrn(rrn: str) -> str:
    """Mask a Korean RRN like 123456-1234567 => 123456-1******."""
    cleaned = rrn.replace("-", "")
    return f"{cleaned[:6]}-{cleaned[6]}******"


def mask_account(account: str) -> str:
    """Mask account or card number except last 4 digits."""
    if len(account) <= 4:
        return "*" * len(account)
    return "*" * (len(account) - 4) + account[-4:]
