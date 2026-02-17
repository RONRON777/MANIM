#!/bin/sh

set -u

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT_DIR"

ENV_FILE="$ROOT_DIR/.env.local"
TMP_DIR="$ROOT_DIR/.tmp"
VENV_PY="$ROOT_DIR/.venv/bin/python"

say() {
  printf "%s\n" "$1"
}

fail() {
  say ""
  say "[실패] $1"
  if [ "${2:-}" != "" ]; then
    say "[안내] $2"
  fi
  say ""
  say "터미널을 닫지 말고, 안내대로 처리 후 다시 ./start.sh 를 실행하세요."
  exit 1
}

ensure_runtime() {
  mkdir -p "$TMP_DIR"

  if ! ./run.sh setup >"$TMP_DIR/start_setup.log" 2>&1; then
    if grep -q "No matching distribution found" "$TMP_DIR/start_setup.log" || \
       grep -q "Failed to establish a new connection" "$TMP_DIR/start_setup.log"; then
      fail "필수 프로그램 설치에 실패했습니다." "인터넷 연결을 확인하고 다시 시도해주세요."
    fi

    fail "환경 준비 중 오류가 발생했습니다." "로그 파일: .tmp/start_setup.log"
  fi

  if ! PYTHONPATH=src "$VENV_PY" - <<'PY'
import importlib.util
raise SystemExit(0 if importlib.util.find_spec("PySide6") else 1)
PY
  then
    fail "화면 프로그램(PySide6) 설치가 되지 않았습니다." "인터넷 연결 후 ./start.sh 를 다시 실행해주세요."
  fi
}

load_or_create_keys() {
  if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    . "$ENV_FILE"
  fi

  if [ -n "${MANIM_DB_KEY:-}" ] && [ -n "${MANIM_ENCRYPTION_KEY:-}" ]; then
    export MANIM_DB_KEY
    export MANIM_ENCRYPTION_KEY
    return
  fi

  KEY_OUTPUT=$(PYTHONPATH=src "$VENV_PY" scripts/generate_keys.py 2>&1) || \
    fail "암호화 키 생성에 실패했습니다." "로그: $KEY_OUTPUT"

  DB_KEY=$(printf "%s\n" "$KEY_OUTPUT" | sed -n "s/^export MANIM_DB_KEY='\(.*\)'$/\1/p")
  ENC_KEY=$(printf "%s\n" "$KEY_OUTPUT" | sed -n "s/^export MANIM_ENCRYPTION_KEY='\(.*\)'$/\1/p")

  if [ -z "$DB_KEY" ] || [ -z "$ENC_KEY" ]; then
    fail "생성된 키 형식을 읽을 수 없습니다." "scripts/generate_keys.py 출력 형식을 확인해주세요."
  fi

  cat > "$ENV_FILE" <<KEYS
MANIM_DB_KEY='$DB_KEY'
MANIM_ENCRYPTION_KEY='$ENC_KEY'
KEYS
  chmod 600 "$ENV_FILE"

  export MANIM_DB_KEY="$DB_KEY"
  export MANIM_ENCRYPTION_KEY="$ENC_KEY"

  say "[안내] 처음 실행이라 키 파일(.env.local)을 자동 생성했습니다."
}

run_app() {
  if ! ./run.sh app >"$TMP_DIR/start_app.log" 2>&1; then
    if grep -q "MANIM_DB_KEY / MANIM_ENCRYPTION_KEY are required" "$TMP_DIR/start_app.log"; then
      fail "암호화 키를 읽지 못했습니다." "파일 .env.local 을 확인하고 다시 실행해주세요."
    fi

    if grep -q "PySide6가 설치되지 않았습니다" "$TMP_DIR/start_app.log"; then
      fail "화면 프로그램(PySide6)이 없어 실행할 수 없습니다." "인터넷 연결 후 ./start.sh 를 다시 실행해주세요."
    fi

    if grep -q "SQLCipher is required but unavailable" "$TMP_DIR/start_app.log"; then
      fail "DB 암호화 모듈 설정 문제입니다." "config/security.yaml 의 allow_sqlite_fallback 값을 true 로 유지해주세요."
    fi

    fail "앱 실행 중 오류가 발생했습니다." "로그 파일: .tmp/start_app.log"
  fi
}

say "[1/3] 실행 환경 준비 중..."
ensure_runtime
say "[2/3] 키 확인 중..."
load_or_create_keys
say "[3/3] 앱 실행 중..."
run_app
