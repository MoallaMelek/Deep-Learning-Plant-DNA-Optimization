@echo off
echo Starting CropDNA Platform...
start "Module 7" cmd /k "conda activate dnabert_lc && cd C:\Users\alato\Downloads\cropdna && uvicorn module7_server:app --port 5007"
timeout /t 10
start "CropDNA Gateway" cmd /k "conda activate dnabert_lc && uvicorn main:app --port 8000 --reload"
echo Both servers started!