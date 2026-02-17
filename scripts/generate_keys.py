"""Generate environment key values for MANIM."""

from __future__ import annotations

import secrets

from manim_app.core.crypto import CryptoService


def main() -> None:
    """Print recommended key values for first-time setup."""
    db_key = secrets.token_urlsafe(48)
    encryption_key = CryptoService.generate_base64_key()

    print("export MANIM_DB_KEY='{}'".format(db_key))
    print("export MANIM_ENCRYPTION_KEY='{}'".format(encryption_key))


if __name__ == "__main__":
    main()
