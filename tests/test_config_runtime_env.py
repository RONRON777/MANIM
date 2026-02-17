from __future__ import annotations

from pathlib import Path

from manim_app.core import config as app_config


def test_get_required_env_loads_from_local_env_file(monkeypatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "MANIM_DB_KEY='db-from-file'\nMANIM_ENCRYPTION_KEY='enc-from-file'\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MANIM_DB_KEY", raising=False)
    monkeypatch.delenv("MANIM_ENCRYPTION_KEY", raising=False)
    monkeypatch.setattr(app_config, "_RUNTIME_ENV_LOADED", False)
    monkeypatch.setattr(app_config, "_iter_env_candidates", lambda: [env_file])

    db_key = app_config.get_required_env("MANIM_DB_KEY")
    enc_key = app_config.get_required_env("MANIM_ENCRYPTION_KEY")

    assert db_key == "db-from-file"
    assert enc_key == "enc-from-file"


def test_get_required_env_bootstraps_runtime_keys(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MANIM_DB_KEY", raising=False)
    monkeypatch.delenv("MANIM_ENCRYPTION_KEY", raising=False)
    monkeypatch.setattr(app_config, "_RUNTIME_ENV_LOADED", False)
    monkeypatch.setattr(app_config, "_runtime_root", lambda: tmp_path)
    monkeypatch.setattr(app_config, "_iter_env_candidates", lambda: [])

    db_key = app_config.get_required_env("MANIM_DB_KEY")
    enc_key = app_config.get_required_env("MANIM_ENCRYPTION_KEY")

    runtime_env = tmp_path / "config" / "runtime.env"
    assert runtime_env.exists()
    content = runtime_env.read_text(encoding="utf-8")
    assert "MANIM_DB_KEY='" in content
    assert "MANIM_ENCRYPTION_KEY='" in content
    assert db_key
    assert enc_key
