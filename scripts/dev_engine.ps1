# Run the engine in development (no bundle). Serves the API + tray, and the
# UI if you've run `npm run build` in ui/. For live UI editing, run
# `npm run dev` in ui/ in a second terminal (it proxies /api here).
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (Test-Path (Join-Path $root ".venv\Scripts\python.exe")) {
    $py = Join-Path $root ".venv\Scripts\python.exe"
} else {
    $py = "python"
}

& $py -m engine
