@echo off
setlocal

cd /d "%~dp0"

echo [HARDNESS] Installing backend dependencies...
py -m pip install -e . 2>nul || python -m pip install -e .
if errorlevel 1 (
  echo [HARDNESS] Backend install failed.
  exit /b 1
)

echo [HARDNESS] Installing frontend dependencies...
cd /d "%~dp0frontend"
npm install
if errorlevel 1 (
  echo [HARDNESS] Frontend install failed.
  exit /b 1
)

cd /d "%~dp0"

echo.
echo [HARDNESS] Configurazione API keys...
if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo [HARDNESS] Creato .env da .env.example
  echo.
  echo  ATTENZIONE: apri il file .env e inserisci le tue API key prima di avviare.
  echo  Es: OPENROUTER_API_KEY=sk-or-...
  echo.
) else (
  echo [HARDNESS] .env gia presente, nessuna modifica.
)

echo [HARDNESS] Installazione completata.
echo   - Avvia il backend:  start_backend.bat
echo   - Avvia il frontend: start_frontend.bat
exit /b 0

