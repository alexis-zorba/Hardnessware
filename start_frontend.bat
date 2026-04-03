@echo off
setlocal

cd /d "%~dp0frontend"

if not exist "node_modules" (
  echo [HARDNESS] node_modules non trovato. Esegui install_workbench.bat prima.
  pause
  exit /b 1
)

echo [HARDNESS] Checking port 5173...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $conns = Get-NetTCPConnection -State Listen -LocalPort 5173 -ErrorAction SilentlyContinue; if ($conns) { $procIds = $conns | Select-Object -ExpandProperty OwningProcess -Unique; foreach ($procId in $procIds) { Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue; Write-Host ('[HARDNESS] Freed port 5173 (PID ' + $procId + ')'); } } } catch { }"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":5173 .*LISTENING"') do (
  taskkill /PID %%P /F >nul 2>nul
)
echo [HARDNESS] Starting frontend on http://127.0.0.1:5173 ...
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
