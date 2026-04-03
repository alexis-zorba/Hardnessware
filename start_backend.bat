@echo off
setlocal

cd /d "%~dp0"

if not exist ".env" (
  echo [HARDNESS] ATTENZIONE: .env non trovato. Le API key potrebbero non essere caricate.
  echo             Esegui install_workbench.bat per la prima configurazione.
  echo.
)

echo [HARDNESS] Starting backend on http://127.0.0.1:8000 ...
py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 2>nul || python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
