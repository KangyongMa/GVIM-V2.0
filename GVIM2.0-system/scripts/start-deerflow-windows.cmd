@echo off
setlocal

set "PROJECT_ROOT=%~dp0.."
cd /d "%PROJECT_ROOT%"

echo Starting DeerFlow from:
echo   %CD%
echo.

if not exist "%CD%\scripts\start-backend-windows.cmd" (
  echo Missing backend script: scripts\start-backend-windows.cmd
  pause
  exit /b 1
)

if not exist "%CD%\scripts\start-frontend-windows.ps1" (
  echo Missing frontend script: scripts\start-frontend-windows.ps1
  pause
  exit /b 1
)

powershell.exe -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
if "%ERRORLEVEL%"=="0" (
  echo Backend already appears to be running on port 8001.
) else (
  start "DeerFlow Backend :8001" cmd /k ""%CD%\scripts\start-backend-windows.cmd""
)

powershell.exe -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
if "%ERRORLEVEL%"=="0" (
  echo Frontend already appears to be running on port 3000.
) else (
  start "DeerFlow Frontend :3000" powershell.exe -NoProfile -ExecutionPolicy Bypass -NoExit -File "%CD%\scripts\start-frontend-windows.ps1"
)

echo.
echo Backend window:  http://127.0.0.1:8001/health
echo Frontend window: http://localhost:3000
echo.
echo If a window reports that the port is already in use, close the old service window first.
pause
