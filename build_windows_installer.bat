@echo off
setlocal
call "%~dp0tools\windows\build.bat" installer
exit /b %ERRORLEVEL%
