@echo off
echo Starting CropDNA Platform Services...

echo 1. Starting Main Combined Backend (Port 8000)...
start "Main Backend (Port 8000)" cmd /k "cd /d %~dp0AgriCulture-1.0.0\intglalasouhaboub2\intglalasouhaboub2 && python -m uvicorn main_combine:app --reload --host 0.0.0.0 --port 8000"

echo 2. Starting RAG Server (Port 5007)...
start "RAG Server (Port 5007)" cmd /k "cd /d %~dp0cropdna && python -m uvicorn module7_server:app --port 5007"

echo 3. Starting React Frontend...
start "React Frontend" cmd /k "cd /d %~dp0AgriCulture-1.0.0\AgriCulture-1.0.0\client && npm run dev"

echo.
echo All services have been launched in separate windows!
echo - Main Backend: http://127.0.0.1:8000/docs
echo - RAG Server: http://127.0.0.1:5007
echo - React Frontend: Usually http://localhost:5173
echo.
pause
