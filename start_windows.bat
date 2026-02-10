@echo off
echo === PII Redactor Startup ===
echo.
echo Starting backend...
start "PII-Backend" cmd /k "cd backend && pip install -r requirements.txt && python -m spacy download en_core_web_sm && uvicorn server:app --host 0.0.0.0 --port 8000"
echo Waiting 15 seconds for backend to start...
timeout /t 15 /nobreak
echo.
echo Starting frontend...
start "PII-Frontend" cmd /k "cd frontend && npm install && npm start"
echo.
echo === Both services starting. Check the two new terminal windows. ===
echo === Frontend will be at http://localhost:3000 ===
pause
