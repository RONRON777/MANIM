param(
  [switch]$Installer
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $Root

$SpecPath = Join-Path $Root 'tools\windows\MANIM.spec'
$DistDir = Join-Path $Root 'dist\MANIM'
$DistConfigDir = Join-Path $DistDir 'config'
$DistRootConfigDir = Join-Path $Root 'dist\config'
$DistExe = Join-Path $Root 'dist\MANIM.exe'
$DistPackedExe = Join-Path $DistDir 'MANIM.exe'
$SecurityConfig = Join-Path $Root 'config\security.yaml'
$ReadmeFile = Join-Path $Root 'README.md'
$ReadmeOut = Join-Path $DistDir 'README.txt'
$PythonCommand = $null

function Invoke-Checked {
  param(
    [Parameter(Mandatory = $true)]
    [string[]]$CommandParts
  )
  $command = $CommandParts[0]
  $args = @()
  if ($CommandParts.Count -gt 1) {
    $args = $CommandParts[1..($CommandParts.Count - 1)]
  }
  & $command @args
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed: $($CommandParts -join ' ')"
  }
}

function Resolve-PythonCommand {
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) {
    return @('py')
  }
  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) {
    return @('python')
  }
  throw 'Python executable not found. Install Python 3.9+ and retry.'
}

function Assert-PythonVersion {
  $command = $PythonCommand[0]
  $args = @('-c', 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)')
  & $command @args
  if ($LASTEXITCODE -ne 0) {
    Write-Host '[INFO] Python 3.9+ is required.'
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
      Write-Host '[INFO] Python versions detected by py launcher:'
      & py -0p
    }
    throw 'Unsupported Python version. Install/select Python 3.9+ and retry.'
  }
}

$PythonCommand = Resolve-PythonCommand
Assert-PythonVersion

Write-Host '[1/4] Check Python/pip'
Invoke-Checked -CommandParts ($PythonCommand + @('--version'))
Invoke-Checked -CommandParts ($PythonCommand + @('-m', 'pip', '--version'))

Write-Host '[2/4] Install build dependencies'
Invoke-Checked -CommandParts ($PythonCommand + @('-m', 'pip', 'install', '--user', '--upgrade', 'pip'))
Invoke-Checked -CommandParts (
  $PythonCommand + @('-m', 'pip', 'install', '--user', 'pyinstaller', 'PySide6', 'PyYAML', 'cryptography')
)

Write-Host '[3/4] Build MANIM.exe'
Invoke-Checked -CommandParts (
  $PythonCommand + @('-m', 'PyInstaller', '--noconfirm', '--clean', $SpecPath)
)

if (-not (Test-Path $DistDir)) {
  New-Item -ItemType Directory -Path $DistDir | Out-Null
}
if (-not (Test-Path $DistConfigDir)) {
  New-Item -ItemType Directory -Path $DistConfigDir | Out-Null
}
if (-not (Test-Path $DistRootConfigDir)) {
  New-Item -ItemType Directory -Path $DistRootConfigDir | Out-Null
}
Copy-Item $DistExe $DistPackedExe -Force
Copy-Item $SecurityConfig (Join-Path $DistConfigDir 'security.yaml') -Force
Copy-Item $SecurityConfig (Join-Path $DistRootConfigDir 'security.yaml') -Force
Copy-Item $ReadmeFile $ReadmeOut -Force

Write-Host "Output: $DistPackedExe"

if ($Installer) {
  Write-Host '[4/4] Build installer with Inno Setup'
  $iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
  if (-not (Test-Path $iscc)) {
    $iscc = "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
  }
  if (-not (Test-Path $iscc)) {
    throw 'Inno Setup 6 not found. Install it and rerun with installer mode.'
  }
  Invoke-Checked -CommandParts @($iscc, (Join-Path $Root 'tools\windows\installer.iss'))
  Write-Host 'Installer output: dist\installer\MANIM-Setup.exe'
}
