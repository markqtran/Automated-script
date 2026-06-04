# Download rclone.exe into this project folder (Windows)
# Run: powershell -ExecutionPolicy Bypass -File install-rclone.ps1

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (Test-Path 'rclone.exe') {
    Write-Host 'rclone.exe already exists in this folder.'
    & .\rclone.exe version
    exit 0
}

$url = 'https://downloads.rclone.org/rclone-current-windows-amd64.zip'
$zip = Join-Path $PSScriptRoot 'rclone.zip'

Write-Host 'Downloading rclone...'
Invoke-WebRequest -Uri $url -OutFile $zip

Write-Host 'Extracting...'
Expand-Archive -Path $zip -DestinationPath $PSScriptRoot -Force

$folder = Get-ChildItem -Directory -Filter 'rclone-*-windows-amd64' | Select-Object -First 1
if (-not $folder) {
    Write-Host 'Download failed - folder not found.' -ForegroundColor Red
    exit 1
}

Move-Item (Join-Path $folder.FullName 'rclone.exe') (Join-Path $PSScriptRoot 'rclone.exe') -Force
Remove-Item $zip -Force
Remove-Item $folder.FullName -Recurse -Force

Write-Host ''
Write-Host 'rclone installed.' -ForegroundColor Green
& .\rclone.exe version
Write-Host ''
Write-Host 'Next: .\rclone.exe config'
