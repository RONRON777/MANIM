@echo off
setlocal
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
set EXIT_CODE=%ERRORLEVEL%
echo.
if not "%EXIT_CODE%"=="0" (
  echo [FAILED] App launch failed. Check messages above.
  pause
  exit /b %EXIT_CODE%
)
echo [DONE] App process ended.
pause
exit /b 0
