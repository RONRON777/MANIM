"""Tests for encryption helpers."""

from manim_app.core.crypto import CryptoService, mask_account, mask_rrn


def test_encrypt_decrypt_round_trip() -> None:
    key = CryptoService.generate_base64_key()
    crypto = CryptoService.from_base64_key(key)

    cipher = crypto.encrypt_text("1234561234567")
    plain = crypto.decrypt_text(cipher)

    assert plain == "1234561234567"


def test_mask_helpers() -> None:
    assert mask_rrn("123456-1234567") == "123456-1******"
    assert mask_account("123456789012") == "********9012"
