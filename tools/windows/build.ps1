param(
  [switch]$Installer
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $Root
$PythonCommand = $null

function Resolve-PythonCommand {
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) {
    return @('py')
  }
  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) {
    return @('python')
  }
  throw 'Python 실행 파일을 찾지 못했습니다. Python 3를 설치하고 다시 시도하세요.'
}

function Assert-PythonVersion {
  & $PythonCommand -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)"
  if ($LASTEXITCODE -ne 0) {
    Write-Host '[안내] Python 3.9 이상이 필요합니다.'
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
      Write-Host '[안내] 현재 py 런처에서 인식된 Python 목록:'
      & py -0p
    }
    throw '지원되지 않는 Python 버전입니다. Python 3.9+를 설치/기본값으로 설정하세요.'
  }
}

$PythonCommand = Resolve-PythonCommand
Assert-PythonVersion

Write-Host '[1/4] Check Python/pip'
& $PythonCommand --version
& $PythonCommand -m pip --version

Write-Host '[2/4] Install build dependencies'
& $PythonCommand -m pip install --user --upgrade pip
& $PythonCommand -m pip install --user pyinstaller PySide6 PyYAML cryptography

Write-Host '[3/4] Build MANIM.exe'
& $PythonCommand -m PyInstaller --noconfirm --clean tools\windows\MANIM.spec

if (-not (Test-Path 'dist\MANIM')) {
  New-Item -ItemType Directory -Path 'dist\MANIM' | Out-Null
}
if (-not (Test-Path 'dist\MANIM\config')) {
  New-Item -ItemType Directory -Path 'dist\MANIM\config' | Out-Null
}
Copy-Item 'dist\MANIM.exe' 'dist\MANIM\MANIM.exe' -Force
Copy-Item 'config\security.yaml' 'dist\MANIM\config\security.yaml' -Force
Copy-Item 'README.md' 'dist\MANIM\README.txt' -Force

Write-Host 'Output: dist\MANIM\MANIM.exe'

if ($Installer) {
  Write-Host '[4/4] Build installer with Inno Setup'
  $iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
  if (-not (Test-Path $iscc)) {
    throw 'Inno Setup 6 not found. Install it and rerun with -Installer.'
  }
  & $iscc tools\windows\installer.iss
  Write-Host 'Installer output: dist\installer\MANIM-Setup.exe'
}
