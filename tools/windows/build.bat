@echo off
setlocal
set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..\..") do set ROOT_DIR=%%~fI
pushd "%ROOT_DIR%" >nul

set PY_CMD=
where py >nul 2>&1
if not errorlevel 1 set PY_CMD=py
if "%PY_CMD%"=="" (
  where python >nul 2>&1
  if not errorlevel 1 set PY_CMD=python
)

if "%PY_CMD%"=="" (
  echo [실패] Python 실행 파일을 찾지 못했습니다. Python 3를 설치하세요.
  set EXIT_CODE=1
  goto END
)

echo [1/4] Check Python/pip
%PY_CMD% --version || goto FAIL
%PY_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" || goto PYVER_FAIL
%PY_CMD% -m pip --version || goto FAIL

echo [2/4] Install build dependencies
%PY_CMD% -m pip install --user --upgrade pip || goto FAIL
%PY_CMD% -m pip install --user pyinstaller PySide6 PyYAML cryptography || goto FAIL

echo [3/4] Build MANIM.exe
%PY_CMD% -m PyInstaller --noconfirm --clean tools\windows\MANIM.spec || goto FAIL

if not exist "dist\MANIM" mkdir "dist\MANIM"
if not exist "dist\MANIM\config" mkdir "dist\MANIM\config"
copy /Y "dist\MANIM.exe" "dist\MANIM\MANIM.exe" >nul || goto FAIL
copy /Y "config\security.yaml" "dist\MANIM\config\security.yaml" >nul || goto FAIL
copy /Y "README.md" "dist\MANIM\README.txt" >nul || goto FAIL
echo Output: dist\MANIM\MANIM.exe

if /I "%~1"=="installer" (
  echo [4/4] Build installer with Inno Setup
  set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
  if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
  if not exist "%ISCC%" (
    echo [실패] Inno Setup 6 not found. Install it and rerun with installer mode.
    goto FAIL
  )
  "%ISCC%" tools\windows\installer.iss || goto FAIL
  echo Installer output: dist\installer\MANIM-Setup.exe
)

set EXIT_CODE=0
goto END

:PYVER_FAIL
echo [실패] Python 3.9 이상이 필요합니다.
where py >nul 2>&1
if not errorlevel 1 (
  echo [안내] 현재 py 런처에서 인식된 Python 목록:
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
  echo [실패] 빌드 중 오류가 발생했습니다. 위 메시지를 확인하세요.
  pause
  exit /b %EXIT_CODE%
)
echo [완료] 빌드가 끝났습니다.
pause
exit /b 0
