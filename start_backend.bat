@echo off
setlocal

cd /d "%~dp0"
echo [HARDNESS] Starting backend on http://127.0.0.1:8000 ...
py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

