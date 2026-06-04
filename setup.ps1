$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

Write-Host ''
Write-Host '=== Footage Workflow Setup ===' -ForegroundColor Cyan
Write-Host ''

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host 'Python not found. Install from https://www.python.org/downloads/' -ForegroundColor Red
    exit 1
}

python --version

$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$rebuild = $false

if (-not (Test-Path $venvPython)) {
    $rebuild = $true
} else {
    try {
        & $venvPython --version | Out-Null
    } catch {
        $rebuild = $true
    }
    if ($LASTEXITCODE -ne 0) {
        $rebuild = $true
    }
}

if ($rebuild) {
    if (Test-Path '.venv') {
        Write-Host 'Removing old .venv - it was copied from another computer.' -ForegroundColor Yellow
        Remove-Item -Recurse -Force '.venv'
    }
    Write-Host 'Creating virtual environment...'
    python -m venv .venv
    $venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
}

Write-Host 'Installing Python packages...'
& $venvPython -m pip install -r requirements.txt

$configPath = Join-Path $PSScriptRoot 'config.yaml'
$examplePath = Join-Path $PSScriptRoot 'config.example.yaml'
if (-not (Test-Path $configPath)) {
    Copy-Item $examplePath $configPath
    Write-Host 'Created config.yaml - edit drive letters before first use.' -ForegroundColor Yellow
} else {
    Write-Host 'config.yaml already exists - skipped.'
}

Write-Host ''
Write-Host '=== Setup complete ===' -ForegroundColor Green
Write-Host ''
Write-Host 'Run: .\.venv\Scripts\Activate.ps1'
Write-Host 'Run: python main.py list-scripts'
Write-Host ''
