@echo off
setlocal
call "%~dp0tools\windows\build.bat"
exit /b %ERRORLEVEL%
