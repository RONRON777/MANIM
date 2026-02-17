param()

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$TmpDir = Join-Path $Root '.tmp'
$VenvPython = Join-Path $Root '.venv\Scripts\python.exe'
$EnvFile = Join-Path $Root '.env.local.ps1'
$SrcPath = Join-Path $Root 'src'
$GenerateKeysScript = Join-Path $Root 'scripts\generate_keys.py'
$MainScript = Join-Path $Root 'src\manim_app\main.py'
$BootstrapPython = $null

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
  $command = $BootstrapPython[0]
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

function Ensure-Venv {
  if (-not (Test-Path $VenvPython)) {
    Invoke-Checked -CommandParts ($BootstrapPython + @('-m', 'venv', (Join-Path $Root '.venv')))
  }
}

function Setup-Env {
  Ensure-Venv
  Invoke-Checked -CommandParts @($VenvPython, '-m', 'pip', 'install', '--upgrade', 'pip')
  Invoke-Checked -CommandParts @(
    $VenvPython, '-m', 'pip', 'install', 'pytest', 'cryptography', 'PyYAML', 'PySide6'
  )
}

function Ensure-Keys {
  Ensure-Venv
  if (Test-Path $EnvFile) {
    . $EnvFile
  }
  if (-not $env:MANIM_DB_KEY -or -not $env:MANIM_ENCRYPTION_KEY) {
    $lines = & $VenvPython $GenerateKeysScript
    if ($LASTEXITCODE -ne 0) {
      throw 'Key generation failed.'
    }
    $db = ($lines | Where-Object { $_ -like 'export MANIM_DB_KEY=*' })
    $enc = ($lines | Where-Object { $_ -like 'export MANIM_ENCRYPTION_KEY=*' })
    if (-not $db -or -not $enc) {
      throw 'Could not parse generated keys.'
    }
    $dbValue = ($db -replace "^export MANIM_DB_KEY='", '') -replace "'$", ''
    $encValue = ($enc -replace "^export MANIM_ENCRYPTION_KEY='", '') -replace "'$", ''
    @(
      "`$env:MANIM_DB_KEY='$dbValue'",
      "`$env:MANIM_ENCRYPTION_KEY='$encValue'"
    ) | Set-Content -Encoding UTF8 $EnvFile
    . $EnvFile
  }
}

try {
  New-Item -ItemType Directory -Path $TmpDir -Force | Out-Null
  $BootstrapPython = Resolve-PythonCommand
  Assert-PythonVersion
  Write-Host '[1/3] Preparing runtime...'
  Setup-Env
  Write-Host '[2/3] Checking keys...'
  Ensure-Keys
  Write-Host '[3/3] Starting app...'
  $env:PYTHONPATH = $SrcPath
  Invoke-Checked -CommandParts @($VenvPython, $MainScript)
}
catch {
  Write-Host ''
  Write-Host "[FAILED] $($_.Exception.Message)"
  Write-Host "[INFO] Root path: $Root"
  exit 1
}
