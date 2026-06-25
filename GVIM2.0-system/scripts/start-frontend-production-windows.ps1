$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$FrontendDir = Join-Path $ProjectRoot "frontend"

Set-Location $FrontendDir

$env:SKIP_ENV_VALIDATION = "1"
$env:NODE_ENV = "production"
$env:NEXT_TELEMETRY_DISABLED = "1"

Write-Host "[frontend] Building production bundle..."
pnpm.cmd build

Write-Host "[frontend] Starting Next.js production server on 0.0.0.0:3000..."
pnpm.cmd exec next start --hostname 0.0.0.0 --port 3000
