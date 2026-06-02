# Build Beacon: compile the UI, then bundle the one-file exe.
# Run from anywhere; it resolves the repo root from this script's location.
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "==> Building UI" -ForegroundColor Cyan
Set-Location (Join-Path $root "ui")
npm ci
npm run build
Set-Location $root

Write-Host "==> Generating tray/app icon" -ForegroundColor Cyan
python scripts/make_icon.py

Write-Host "==> Bundling exe with PyInstaller" -ForegroundColor Cyan
pyinstaller packaging/beacon.spec --noconfirm

Write-Host "==> Stamping version.json" -ForegroundColor Cyan
$version = (Select-String -Path (Join-Path $root "engine\version.py") -Pattern '__version__\s*=\s*"([^"]+)"').Matches.Groups[1].Value
$manifest = @{ version = $version; url = "https://github.com/your-org/luxafor-flag-controller/releases"; notes = "" } | ConvertTo-Json
$manifest | Out-File -FilePath (Join-Path $root "dist\version.json") -Encoding utf8

Write-Host "==> Done: dist\beacon.exe (v$version)" -ForegroundColor Green
