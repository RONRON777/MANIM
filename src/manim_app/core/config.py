"""Configuration loader for security and database settings."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class DatabaseConfig:
    path: str
    key_env: str
    allow_sqlite_fallback: bool


@dataclass(frozen=True)
class EncryptionConfig:
    key_env: str


@dataclass(frozen=True)
class LoggingConfig:
    retention_days: int


@dataclass(frozen=True)
class AppConfig:
    database: DatabaseConfig
    encryption: EncryptionConfig
    logging: LoggingConfig


DEFAULT_CONFIG_REL_PATH = Path("config/security.yaml")


def resolve_default_config_path() -> Path:
    """Resolve configuration path for source and packaged execution."""
    env_path = os.getenv("MANIM_CONFIG_PATH")
    if env_path:
        return Path(env_path)

    candidates: list[Path] = []

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / DEFAULT_CONFIG_REL_PATH)

    candidates.append(Path.cwd() / DEFAULT_CONFIG_REL_PATH)
    candidates.append(Path(__file__).resolve().parents[3] / DEFAULT_CONFIG_REL_PATH)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0] if candidates else DEFAULT_CONFIG_REL_PATH


def load_config(config_path: Path | None = None) -> AppConfig:
    """Load the app configuration from YAML."""
    path = config_path or resolve_default_config_path()
    with path.open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file)

    return AppConfig(
        database=DatabaseConfig(
            path=str(raw["db"]["path"]),
            key_env=str(raw["db"]["key_env"]),
            allow_sqlite_fallback=bool(raw["db"].get("allow_sqlite_fallback", False)),
        ),
        encryption=EncryptionConfig(
            key_env=str(raw["encryption"]["key_env"]),
        ),
        logging=LoggingConfig(
            retention_days=int(raw["logging"].get("retention_days", 1095)),
        ),
    )


def get_required_env(name: str) -> str:
    """Return a required environment variable or raise a clear error."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable is missing: {name}")
    return value
