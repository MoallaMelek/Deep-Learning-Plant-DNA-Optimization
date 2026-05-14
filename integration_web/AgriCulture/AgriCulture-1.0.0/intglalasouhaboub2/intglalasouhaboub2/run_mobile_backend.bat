@echo off
cd /d "%~dp0"
echo Starting mobile backend on http://127.0.0.1:8000
echo Logs: %~dp0backend-live.log
.\.venv\Scripts\python.exe -u -m uvicorn main_combine:app --host 0.0.0.0 --port 8000 --log-level info >> backend-live.log 2>&1
echo.
echo Backend stopped. Check backend-live.log for details.
pause
