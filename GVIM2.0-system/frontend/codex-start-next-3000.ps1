$ErrorActionPreference = 'Stop'
Set-Location 'E:\Demo of GVIM\deer-flow-mainnew\deer-flow-main\frontend'
$env:SKIP_ENV_VALIDATION = '1'
$env:NEXT_TELEMETRY_DISABLED = '1'
pnpm.cmd dev -- --hostname 127.0.0.1 --port 3000
