@echo off
setlocal
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..\..") do set ROOT_DIR=%%~fI
pushd "%ROOT_DIR%" >nul

set SPEC_PATH=%ROOT_DIR%\tools\windows\MANIM.spec
set DIST_DIR=%ROOT_DIR%\dist\MANIM
set DIST_CFG_DIR=%DIST_DIR%\config
set DIST_ROOT_CFG_DIR=%ROOT_DIR%\dist\config
set DIST_EXE=%ROOT_DIR%\dist\MANIM.exe
set DIST_PACKED_EXE=%DIST_DIR%\MANIM.exe
set CFG_FILE=%ROOT_DIR%\config\security.yaml
set README_FILE=%ROOT_DIR%\README.md
set README_OUT=%DIST_DIR%\README.txt

set PY_CMD=
where py >nul 2>&1
if not errorlevel 1 set PY_CMD=py
if "%PY_CMD%"=="" (
  where python >nul 2>&1
  if not errorlevel 1 set PY_CMD=python
)

if "%PY_CMD%"=="" (
  echo [FAILED] Python executable not found. Install Python 3.9+.
  set EXIT_CODE=1
  goto END
)

echo [1/4] Check Python/pip
%PY_CMD% --version || goto FAIL
%PY_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" ^
  || goto PYVER_FAIL
%PY_CMD% -m pip --version || goto FAIL

echo [2/4] Install build dependencies
%PY_CMD% -m pip install --user --upgrade pip || goto FAIL
%PY_CMD% -m pip install --user pyinstaller PySide6 PyYAML cryptography || goto FAIL

echo [3/4] Build MANIM.exe
%PY_CMD% -m PyInstaller --noconfirm --clean "%SPEC_PATH%" || goto FAIL

if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"
if not exist "%DIST_CFG_DIR%" mkdir "%DIST_CFG_DIR%"
if not exist "%DIST_ROOT_CFG_DIR%" mkdir "%DIST_ROOT_CFG_DIR%"
copy /Y "%DIST_EXE%" "%DIST_PACKED_EXE%" >nul || goto FAIL
copy /Y "%CFG_FILE%" "%DIST_CFG_DIR%\security.yaml" >nul || goto FAIL
copy /Y "%CFG_FILE%" "%DIST_ROOT_CFG_DIR%\security.yaml" >nul || goto FAIL
copy /Y "%README_FILE%" "%README_OUT%" >nul || goto FAIL
echo Output: %DIST_PACKED_EXE%

if /I "%~1"=="installer" (
  echo [4/4] Build installer with Inno Setup
  set "ISCC="
  for /f "delims=" %%P in ('where ISCC.exe 2^>nul') do (
    if not defined ISCC set "ISCC=%%P"
  )
  if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" ^
    set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
  if not defined ISCC set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
  if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
  if not exist "%ISCC%" (
    if /I not "%MANIM_AUTO_INSTALL_TOOLS%"=="1" (
      echo [FAILED] Inno Setup not found.
      echo [INFO] Install manually, or set MANIM_AUTO_INSTALL_TOOLS=1 for auto-install.
      goto FAIL
    )
    where winget >nul 2>&1
    if errorlevel 1 (
      echo [FAILED] Inno Setup is missing and winget is unavailable.
      echo [INFO] Install Inno Setup 6 manually, then rerun.
      goto FAIL
    )
    echo [INFO] Inno Setup not found. Installing automatically via winget...
    winget install --id JRSoftware.InnoSetup -e ^
      --accept-package-agreements --accept-source-agreements || goto FAIL
    for /f "delims=" %%P in ('where ISCC.exe 2^>nul') do (
      if not defined ISCC set "ISCC=%%P"
    )
    if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" ^
      set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
    if not defined ISCC set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
    if not exist "%ISCC%" (
      echo [FAILED] Inno Setup auto-install did not expose ISCC.exe.
      echo [INFO] Reopen cmd and rerun build_windows_installer.bat.
      goto FAIL
    )
  )
  "%ISCC%" "%ROOT_DIR%\tools\windows\installer.iss" || goto FAIL
  echo Installer output: %ROOT_DIR%\dist\installer\MANIM-Setup.exe
)

set EXIT_CODE=0
goto END

:PYVER_FAIL
echo [FAILED] Python 3.9+ is required.
where py >nul 2>&1
if not errorlevel 1 (
  echo [INFO] Python versions detected by py launcher:
  py -0p
)
set EXIT_CODE=1
goto END

:FAIL
set EXIT_CODE=1

:END
popd >nul
echo.
if not "%EXIT_CODE%"=="0" (
  echo [FAILED] Build did not complete. Check messages above.
  pause
  exit /b %EXIT_CODE%
)
echo [DONE] Build completed.
pause
exit /b 0
