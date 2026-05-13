param(
    [string]$ApiHost = "127.0.0.1",
    [int]$ApiPort = 8000,
    [string]$WebHost = "127.0.0.1",
    [int]$WebPort = 3000
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$apiDir = Join-Path $root "apps\api"
$webDir = Join-Path $root "apps\web"
$apiBaseUrl = "http://${ApiHost}:${ApiPort}"
$logDir = Join-Path $root "data\logs"
$apiLog = Join-Path $logDir "api.log"
$accessLog = Join-Path $logDir "access.log"

function Assert-Command {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing required command: $Name"
    }
}

Assert-Command "npm"

$uv = Get-Command "uv" -ErrorAction SilentlyContinue
$python = Get-Command "python" -ErrorAction SilentlyContinue
if (-not $uv -and -not $python) {
    throw "Missing required command: install either 'uv' or 'python'."
}

if (-not (Test-Path $apiDir)) {
    throw "API directory not found: $apiDir"
}

if (-not (Test-Path $webDir)) {
    throw "Web directory not found: $webDir"
}

if ($uv) {
    $apiCommand = "Set-Location '$apiDir'; uv run uvicorn app.main:app --reload --host $ApiHost --port $ApiPort"
}
else {
    $apiCommand = "Set-Location '$apiDir'; python -m uvicorn app.main:app --reload --host $ApiHost --port $ApiPort"
}

$webCommand = "Set-Location '$webDir'; `$env:NEXT_PUBLIC_API_BASE_URL='$apiBaseUrl'; npm run dev -- --hostname $WebHost --port $WebPort"
$logCommand = "New-Item -ItemType Directory -Force -Path '$logDir' | Out-Null; New-Item -ItemType File -Force -Path '$apiLog' | Out-Null; New-Item -ItemType File -Force -Path '$accessLog' | Out-Null; Get-Content '$apiLog', '$accessLog' -Wait"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $apiCommand
Start-Sleep -Seconds 1
Start-Process powershell -ArgumentList "-NoExit", "-Command", $webCommand
Start-Process powershell -ArgumentList "-NoExit", "-Command", $logCommand

Write-Host "Started API at $apiBaseUrl" -ForegroundColor Green
Write-Host "Started Web at http://${WebHost}:${WebPort}" -ForegroundColor Green
Write-Host "Streaming logs from $apiLog and $accessLog" -ForegroundColor Green
