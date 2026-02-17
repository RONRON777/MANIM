param()

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$VenvPython = Join-Path $Root '.venv\Scripts\python.exe'
$EnvFile = Join-Path $Root '.env.local.ps1'
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
  throw 'Python 실행 파일을 찾지 못했습니다. Python 3를 설치하고 다시 실행하세요.'
}

function Ensure-Venv {
  if (-not (Test-Path $VenvPython)) {
    & $BootstrapPython -m venv .venv
  }
}

function Setup-Env {
  Ensure-Venv
  & $VenvPython -m pip install --upgrade pip | Out-Host
  & $VenvPython -m pip install pytest cryptography PyYAML PySide6 | Out-Host
}

function Ensure-Keys {
  Ensure-Venv
  if (Test-Path $EnvFile) {
    . $EnvFile
  }
  if (-not $env:MANIM_DB_KEY -or -not $env:MANIM_ENCRYPTION_KEY) {
    $lines = & $VenvPython scripts/generate_keys.py
    $db = ($lines | Where-Object { $_ -like 'export MANIM_DB_KEY=*' })
    $enc = ($lines | Where-Object { $_ -like 'export MANIM_ENCRYPTION_KEY=*' })
    if (-not $db -or -not $enc) {
      throw '키 생성 실패'
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
  $BootstrapPython = Resolve-PythonCommand
  Write-Host '[1/3] 실행 환경 준비 중...'
  Setup-Env
  Write-Host '[2/3] 키 확인 중...'
  Ensure-Keys
  Write-Host '[3/3] 앱 실행 중...'
  $env:PYTHONPATH = 'src'
  & $VenvPython -m manim_app.main
}
catch {
  Write-Host ''
  Write-Host "[실패] $($_.Exception.Message)"
  exit 1
}
