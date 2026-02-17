param(
  [switch]$Installer
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $Root
$BootstrapPython = $null

function Resolve-PythonCommand {
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) {
    return @('py', '-3')
  }
  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) {
    return @('python')
  }
  throw 'Python 실행 파일을 찾지 못했습니다. Python 3를 설치하고 다시 시도하세요.'
}

$BootstrapPython = Resolve-PythonCommand

Write-Host '[1/4] Create build venv'
if (-not (Test-Path '.build_venv\Scripts\python.exe')) {
  & $BootstrapPython -m venv .build_venv
}

$Py = Join-Path $Root '.build_venv\Scripts\python.exe'

Write-Host '[2/4] Install build dependencies'
& $Py -m pip install --upgrade pip
& $Py -m pip install pyinstaller PySide6 PyYAML cryptography

Write-Host '[3/4] Build MANIM.exe'
& $Py -m PyInstaller --noconfirm --clean tools\windows\MANIM.spec

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
