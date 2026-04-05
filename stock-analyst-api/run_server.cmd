@echo off
cd /d "%~dp0"
echo Starting FastAPI on http://127.0.0.1:8788  (docs: /docs)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8788
pause
