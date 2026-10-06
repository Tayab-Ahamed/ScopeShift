# ScopeShift Windows PowerShell Launcher
# Starts demo_server, waits for /api/health, and launches the browser

param(
    [string]$Host = "127.0.0.1",
    [int]$Port = 8765,
    [switch]$NoBrowser,
    [switch]$SafeMode
)

$ErrorActionPreference = "Stop"

$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) {
    Write-Error "Python 3 is required but not found in PATH."
    exit 1
}

$argsList = @("run_demo.py", "--host", $Host, "--port", $Port)
if ($NoBrowser) { $argsList += "--no-browser" }
if ($SafeMode) { $argsList += "--safe-mode" }

& python @argsList
