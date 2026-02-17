"""Generate environment key values for MANIM."""

from __future__ import annotations

import argparse
import secrets
from pathlib import Path

from manim_app.core.crypto import CryptoService


def _render_line(name: str, value: str, env_format: str) -> str:
    if env_format == "powershell":
        return f"$env:{name}='{value}'"
    if env_format == "shell-export":
        return f"export {name}='{value}'"
    return f"{name}='{value}'"


def _write_env_file(path: Path, db_key: str, encryption_key: str, env_format: str) -> None:
    lines = [
        _render_line("MANIM_DB_KEY", db_key, env_format),
        _render_line("MANIM_ENCRYPTION_KEY", encryption_key, env_format),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Generate keys and optionally write/print env lines."""
    parser = argparse.ArgumentParser(description="Generate MANIM runtime keys.")
    parser.add_argument(
        "--write-env",
        default=None,
        help="Path to write generated keys. Omit to skip file output.",
    )
    parser.add_argument(
        "--format",
        choices=["shell", "shell-export", "powershell"],
        default="shell",
        help="Output format for written/printed lines.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Also print generated lines to stdout.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing env file.",
    )
    args = parser.parse_args()

    db_key = secrets.token_urlsafe(48)
    encryption_key = CryptoService.generate_base64_key()

    if args.write_env:
        target_path = Path(args.write_env)
        if target_path.exists() and not args.force:
            print(f"[INFO] key file already exists: {target_path}")
            return
        _write_env_file(target_path, db_key, encryption_key, args.format)
        print(f"[INFO] key file written: {target_path}")

    if args.stdout:
        print(_render_line("MANIM_DB_KEY", db_key, args.format))
        print(_render_line("MANIM_ENCRYPTION_KEY", encryption_key, args.format))


if __name__ == "__main__":
    main()
