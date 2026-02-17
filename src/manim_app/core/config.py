"""Configuration loader for security and database settings."""

from __future__ import annotations

import os
import secrets
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from manim_app.core.crypto import CryptoService


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
DEFAULT_DB_KEY_ENV = "MANIM_DB_KEY"
DEFAULT_ENCRYPTION_KEY_ENV = "MANIM_ENCRYPTION_KEY"
RUNTIME_ENV_REL_PATH = Path("config/runtime.env")
_RUNTIME_ENV_LOADED = False


def _split_key_value(raw_line: str) -> tuple[str, str] | None:
    """Parse a shell or PowerShell key assignment line."""
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return None

    if line.startswith("$env:"):
        line = line[len("$env:") :]
    elif line.startswith("export "):
        line = line[len("export ") :]

    if "=" not in line:
        return None

    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None

    if (value.startswith("'") and value.endswith("'")) or (
        value.startswith('"') and value.endswith('"')
    ):
        value = value[1:-1]

    return key, value


def _iter_env_candidates() -> list[Path]:
    """Return candidate files that may contain runtime keys."""
    roots: list[Path] = [Path.cwd(), Path(__file__).resolve().parents[3]]
    if getattr(sys, "frozen", False):
        roots.insert(0, Path(sys.executable).resolve().parent)

    paths: list[Path] = []
    for root in roots:
        paths.extend(
            [
                root / ".env.local",
                root / ".env.local.ps1",
                root / RUNTIME_ENV_REL_PATH,
            ]
        )

    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(resolved)
    return unique


def _load_env_from_file(path: Path) -> None:
    """Load KEY=VALUE lines from a local file into process environment."""
    if not path.exists() or not path.is_file():
        return
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            parsed = _split_key_value(line)
            if not parsed:
                continue
            key, value = parsed
            if key and key not in os.environ:
                os.environ[key] = value


def _runtime_root() -> Path:
    """Return writable root for runtime env creation."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]


def _write_runtime_env(db_key: str, encryption_key: str) -> None:
    """Persist generated runtime keys in config/runtime.env."""
    path = _runtime_root() / RUNTIME_ENV_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            f"{DEFAULT_DB_KEY_ENV}='{db_key}'\n"
            f"{DEFAULT_ENCRYPTION_KEY_ENV}='{encryption_key}'\n"
        ),
        encoding="utf-8",
    )


def _runtime_env_path() -> Path:
    """Return absolute path for generated runtime key file."""
    return _runtime_root() / RUNTIME_ENV_REL_PATH


def _existing_db_candidates(config_db_path: str | None = None) -> list[Path]:
    """Return likely DB paths that indicate existing encrypted data."""
    runtime_root = _runtime_root()
    candidates: list[Path] = [
        runtime_root / "manim_secure.db",
        Path.cwd() / "manim_secure.db",
    ]
    if config_db_path:
        db_path = Path(config_db_path)
        if not db_path.is_absolute():
            db_path = (Path.cwd() / db_path).resolve()
        candidates.append(db_path)

    unique: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(resolved)
    return unique


def _ensure_runtime_env_loaded() -> None:
    """Load local env files once per process."""
    global _RUNTIME_ENV_LOADED
    if _RUNTIME_ENV_LOADED:
        return
    for path in _iter_env_candidates():
        _load_env_from_file(path)
    _RUNTIME_ENV_LOADED = True


def _bootstrap_default_keys_if_needed(config_db_path: str | None = None) -> None:
    """Auto-create default keys when no local key source exists."""
    db_key = os.getenv(DEFAULT_DB_KEY_ENV)
    encryption_key = os.getenv(DEFAULT_ENCRYPTION_KEY_ENV)
    if db_key and encryption_key:
        return

    runtime_env = _runtime_env_path()
    has_existing_db = any(path.exists() for path in _existing_db_candidates(config_db_path))
    if has_existing_db and not runtime_env.exists():
        raise RuntimeError(
            "Runtime key file is missing while database file exists. "
            "Restore key file or set MANIM_DB_KEY/MANIM_ENCRYPTION_KEY."
        )

    db_key = db_key or secrets.token_urlsafe(48)
    encryption_key = encryption_key or CryptoService.generate_base64_key()
    os.environ[DEFAULT_DB_KEY_ENV] = db_key
    os.environ[DEFAULT_ENCRYPTION_KEY_ENV] = encryption_key
    _write_runtime_env(db_key, encryption_key)


def ensure_runtime_keys(config_db_path: str | None = None) -> None:
    """Ensure runtime keys are loaded or bootstrapped for a configured DB path."""
    _ensure_runtime_env_loaded()
    _bootstrap_default_keys_if_needed(config_db_path)


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
    _ensure_runtime_env_loaded()
    if name in {DEFAULT_DB_KEY_ENV, DEFAULT_ENCRYPTION_KEY_ENV}:
        _bootstrap_default_keys_if_needed()
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable is missing: {name}")
    return value
