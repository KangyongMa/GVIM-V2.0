@echo off
setlocal

set "PROJECT_ROOT=%~dp0.."
cd /d "%PROJECT_ROOT%"

echo Starting DeerFlow in production mode from:
echo   %CD%
echo.

if not exist "%CD%\scripts\start-backend-windows.cmd" (
  echo Missing backend script: scripts\start-backend-windows.cmd
  pause
  exit /b 1
)

if not exist "%CD%\scripts\start-frontend-production-windows.ps1" (
  echo Missing frontend production script: scripts\start-frontend-production-windows.ps1
  pause
  exit /b 1
)

powershell.exe -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
if "%ERRORLEVEL%"=="0" (
  echo Backend already appears to be running on port 8001.
) else (
  start "DeerFlow Backend :8001" cmd /k ""%CD%\scripts\start-backend-windows.cmd""
)

powershell.exe -NoProfile -Command "$conn = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1; if (-not $conn) { exit 1 }; $proc = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $conn.OwningProcess); $root = (Resolve-Path '.').Path; if ($proc.CommandLine -and $proc.CommandLine.Contains($root) -and $proc.CommandLine.Contains('\frontend')) { Write-Host ('Stopping existing DeerFlow frontend on port 3000 (PID ' + $conn.OwningProcess + ').'); Stop-Process -Id $conn.OwningProcess -Force; exit 1 } else { exit 0 }"
if "%ERRORLEVEL%"=="0" (
  echo Frontend port 3000 is already in use.
  echo It does not look like this project's frontend process. Close that program, then run this script again.
) else (
  start "DeerFlow Frontend Production :3000" powershell.exe -NoProfile -ExecutionPolicy Bypass -NoExit -File "%CD%\scripts\start-frontend-production-windows.ps1"
)

echo.
echo Backend health:  http://127.0.0.1:8001/health
echo Frontend local:  http://localhost:3000
echo Frontend LAN:    http://192.168.31.179:3000
echo.
echo Production frontend uses: pnpm build, then pnpm start.
pause
