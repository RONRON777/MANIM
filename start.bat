@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0start.ps1"
set EXIT_CODE=%ERRORLEVEL%
echo.
if not "%EXIT_CODE%"=="0" (
  echo [실패] 앱 실행 중 오류가 발생했습니다. 위 메시지를 확인하세요.
  pause
  exit /b %EXIT_CODE%
)
echo [완료] 앱이 종료되었습니다.
pause
exit /b 0
