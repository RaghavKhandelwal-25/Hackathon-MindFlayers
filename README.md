# Finbot - AI Financial Coach

Finbot helps first-time investors budget, set goals, simulate SIP growth, track expenses, read RBI/SEBI updates and learn to spot scams. Its chatbot answers from SEBI/RBI/NCFE material and does exact calculations. It gives education only, not regulated investment advice.

## Project structure

```
finbot/
├── backend/            FastAPI + RAG chatbot (Python)
│   ├── api.py          API entry point (uvicorn api:app)
│   ├── rag.py, ingest.py, query_*.py, web_retriever.py   chatbot pipeline
│   ├── storage.py      SQLite storage (profile, goals, expenses)
│   ├── news_service.py, game_*.py, finance_calculators.py
│   ├── data/pdfs/      knowledge-base PDFs
│   ├── test_*.py       tests
│   ├── requirements.txt
│   └── .env.example    copy to .env and add your Groq key
├── frontend/           React + Vite app
│   ├── src/            pages, components, services
│   └── .env.example    API URL
├── docs/               extra notes
├── start-backend.bat / .sh
└── start-frontend.bat / .sh
```

## Run locally (two terminals, from this folder)

Needs Python 3.11 or 3.12, Node.js, and a free Groq key (console.groq.com/keys).

1. Backend: `start-backend.bat` (Windows, in PowerShell type `.\start-backend.bat`) or `./start-backend.sh`.
   First run creates `backend/.env` - paste your `GROQ_API_KEY`, then run again. It also builds the document index once (needs internet).
2. Frontend: `start-frontend.bat` or `./start-frontend.sh`, then open http://localhost:5173
3. API docs: http://localhost:8000/docs

## Deploy

**Backend** (any Python host; run inside `backend/`):
- Python 3.12. Install: `pip install -r requirements.txt`
- Build step: `python ingest.py` (creates the document index, which is not stored in Git)
- Start: `uvicorn api:app --host 0.0.0.0 --port $PORT`
- Environment variables: `GROQ_API_KEY`, optionally `GROQ_MODEL`, and `CORS_ORIGINS=https://your-frontend-url`
- Needs roughly 2 GB RAM (the embedding model). Note: data is stored in SQLite (`backend/data/finguide.db`), so use a persistent disk or accept that it resets on redeploy.

**Frontend** (Vercel, Netlify, etc.; root directory `frontend/`):
- Build: `npm run build`, output folder `dist`
- Set `VITE_API_BASE_URL=https://your-backend-url/api` before building
- Page-refresh routing is already handled (`vercel.json` and `public/_redirects`)

## API endpoints

| Area | Endpoints |
|---|---|
| Chat | `POST /api/chat`, `GET /api/health` |
| Profile / dashboard | `GET/POST/PUT/DELETE /api/profile`, `GET /api/dashboard`, `GET /api/budget/analysis` |
| Goals | `GET/POST /api/goals`, `PUT/DELETE /api/goals/{id}`, `POST /api/goals/plan` |
| Simulator | `POST /api/simulator/sip` |
| Expenses | `GET/POST /api/expenses`, `GET /api/expenses/summary`, `DELETE /api/expenses/{id}` |
| News | `GET /api/news` |
| Game | `GET /api/game/round` |

## Tests

From `backend/`: `python -m unittest discover -p "test_*.py"` (tests use a temporary database). Chatbot tests need the document index built first.
