@echo off
setlocal

echo [HARDNESS] Installing backend dependencies...
py -m pip install -e .
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

echo [HARDNESS] Installation completed successfully.
exit /b 0

