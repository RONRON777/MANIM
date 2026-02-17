param(
  [switch]$Installer
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $Root

Write-Host '[1/4] Create build venv'
if (-not (Test-Path '.build_venv\Scripts\python.exe')) {
  py -3 -m venv .build_venv
}

$Py = Join-Path $Root '.build_venv\Scripts\python.exe'
$Pip = Join-Path $Root '.build_venv\Scripts\pip.exe'

Write-Host '[2/4] Install build dependencies'
& $Pip install --upgrade pip
& $Pip install pyinstaller PySide6 PyYAML cryptography

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
