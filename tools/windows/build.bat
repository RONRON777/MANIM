@echo off
setlocal
set SCRIPT_DIR=%~dp0

if /I "%~1"=="installer" (
  powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%build.ps1" -Installer
) else (
  powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%build.ps1"
)

set EXIT_CODE=%ERRORLEVEL%
echo.
if not "%EXIT_CODE%"=="0" (
  echo [실패] 빌드 중 오류가 발생했습니다. 위 메시지를 확인하세요.
  pause
  exit /b %EXIT_CODE%
)
echo [완료] 빌드가 끝났습니다.
pause
exit /b 0
