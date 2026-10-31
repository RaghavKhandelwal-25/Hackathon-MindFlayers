@echo off
cd /d "%~dp0backend"
if not exist .env (
  copy .env.example .env >nul
  echo Created backend\.env - open it and paste your GROQ_API_KEY, then run this file again.
  pause
  exit /b
)
findstr /C:"your_groq_api_key_here" .env >nul && (
  echo WARNING: GROQ_API_KEY in backend\.env is still the placeholder. Chat answers will not work until you set it.
)
python -m pip install -r requirements.txt
if not exist vectorstore\index.faiss (
  echo Building the document index for the first time ^(needs internet, takes a few minutes^)...
  python ingest.py
)
python -m uvicorn api:app --reload --port 8000
