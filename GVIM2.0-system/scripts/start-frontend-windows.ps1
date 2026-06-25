$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot

Set-Location (Join-Path $ProjectRoot "frontend")

$env:SKIP_ENV_VALIDATION = "1"

pnpm.cmd dev
