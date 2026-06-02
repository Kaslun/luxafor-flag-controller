# Build Beacon: compile the UI, then bundle the one-file exe.
# Run from anywhere; it resolves the repo root from this script's location.
#
# Native tools (npm, pyinstaller) log progress to stderr. PowerShell's
# "Stop" preference turns any native stderr line into a terminating
# NativeCommandError, which would abort a perfectly good build. So we keep
# Stop for our own cmdlets but run native commands with the preference
# relaxed and check the real exit code instead.
$ErrorActionPreference = "Stop"

function Invoke-Native {
    param([Parameter(Mandatory)][scriptblock] $Command, [string] $What = "command")
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Command
    } finally {
        $ErrorActionPreference = $prev
    }
    if ($LASTEXITCODE -ne 0) {
        throw "$What failed (exit $LASTEXITCODE)"
    }
}

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "==> Building UI" -ForegroundColor Cyan
Set-Location (Join-Path $root "ui")
Invoke-Native { npm ci } "npm ci"
Invoke-Native { npm run build } "npm run build"
Set-Location $root

Write-Host "==> Generating tray/app icon" -ForegroundColor Cyan
Invoke-Native { python scripts/make_icon.py } "make_icon"

Write-Host "==> Bundling exe with PyInstaller" -ForegroundColor Cyan
Invoke-Native { pyinstaller packaging/beacon.spec --noconfirm --clean } "pyinstaller"

Write-Host "==> Stamping version.json" -ForegroundColor Cyan
$version = (Select-String -Path (Join-Path $root "engine\version.py") -Pattern '__version__\s*=\s*"([^"]+)"').Matches.Groups[1].Value
$manifest = @{ version = $version; url = "https://github.com/Kaslun/luxafor-flag-controller/releases"; notes = "" } | ConvertTo-Json
$manifest | Out-File -FilePath (Join-Path $root "dist\version.json") -Encoding utf8

Write-Host "==> Done: dist\beacon.exe (v$version)" -ForegroundColor Green
