@echo off
setlocal
set SCRIPT_DIR=%~dp0
set ROOT_DIR=%SCRIPT_DIR%..\..

if /I "%~1"=="installer" (
  powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%build.ps1" -Installer
) else (
  powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%build.ps1"
)

exit /b %errorlevel%
