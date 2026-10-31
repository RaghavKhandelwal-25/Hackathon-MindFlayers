#!/bin/bash
cd "$(dirname "$0")/backend" || exit 1
if [ ! -f .env ]; then cp .env.example .env; echo "Created backend/.env - add your GROQ_API_KEY, then run again."; exit 0; fi
grep -q "your_groq_api_key_here" .env && echo "WARNING: GROQ_API_KEY is still the placeholder."
python3 -m pip install -r requirements.txt
[ -f vectorstore/index.faiss ] || { echo "Building document index (first time, needs internet)..."; python3 ingest.py; }
python3 -m uvicorn api:app --reload --port 8000
