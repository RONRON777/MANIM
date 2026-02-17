#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT_DIR"

TMP_DIR="$ROOT_DIR/.tmp"
VENV_PY="$ROOT_DIR/.venv/bin/python"
VENV_PIP="$ROOT_DIR/.venv/bin/pip"

ensure_venv() {
  if [ ! -x "$VENV_PY" ]; then
    echo "[INFO] creating virtualenv: .venv"
    mkdir -p "$TMP_DIR"
    TMPDIR="$TMP_DIR" python3 -m venv .venv
  fi
}

setup_env() {
  ensure_venv
  echo "[INFO] installing dependencies"
  mkdir -p "$TMP_DIR"
  if PYTHONPATH=src "$VENV_PY" - <<'PY'
import importlib.util
required = ["pytest", "cryptography", "yaml"]
missing = [name for name in required if importlib.util.find_spec(name) is None]
raise SystemExit(1 if missing else 0)
PY
  then
    echo "[INFO] core dependencies already installed"
  else
    TMPDIR="$TMP_DIR" "$VENV_PIP" install \
      "pytest>=8.3.0" \
      "cryptography>=44.0.0" \
      "PyYAML>=6.0.2"
  fi

  if PYTHONPATH=src "$VENV_PY" - <<'PY'
import importlib.util
raise SystemExit(0 if importlib.util.find_spec("PySide6") else 1)
PY
  then
    echo "[INFO] GUI dependency (PySide6) already installed"
  else
    echo "[INFO] installing GUI dependency: PySide6"
    if ! TMPDIR="$TMP_DIR" "$VENV_PIP" install "PySide6>=6.8.0"; then
      echo "[WARN] PySide6 install failed."
      echo "[WARN] GUI 실행 시 네트워크가 필요할 수 있습니다."
    fi
  fi
}

print_usage() {
  cat <<USAGE
Usage: ./run.sh <command>

Commands:
  setup   Create .venv and install dependencies
  keys    Print key export commands
  test    Run test suite
  app     Run GUI app
USAGE
}

run_keys() {
  ensure_venv
  PYTHONPATH=src "$VENV_PY" scripts/generate_keys.py --stdout --format shell-export
}

run_tests() {
  ensure_venv
  mkdir -p "$TMP_DIR"
  TMPDIR="$TMP_DIR" PYTHONPATH=src "$ROOT_DIR/.venv/bin/pytest" -q -p no:cacheprovider
}

run_app() {
  ensure_venv

  if [ -z "${MANIM_DB_KEY:-}" ] || [ -z "${MANIM_ENCRYPTION_KEY:-}" ]; then
    echo "[ERROR] MANIM_DB_KEY / MANIM_ENCRYPTION_KEY are required."
    echo "[HINT] run: ./run.sh keys"
    exit 1
  fi

  if ! PYTHONPATH=src "$VENV_PY" - <<'PY'
import importlib.util
raise SystemExit(0 if importlib.util.find_spec("PySide6") else 1)
PY
  then
    echo "[ERROR] PySide6가 설치되지 않았습니다."
    echo "[HINT] ./run.sh setup 을 다시 실행하세요."
    exit 1
  fi

  PYTHONPATH=src "$VENV_PY" -m manim_app.main
}

if [ $# -ne 1 ]; then
  print_usage
  exit 1
fi

case "$1" in
  setup)
    setup_env
    ;;
  keys)
    run_keys
    ;;
  test)
    run_tests
    ;;
  app)
    run_app
    ;;
  *)
    print_usage
    exit 1
    ;;
esac
