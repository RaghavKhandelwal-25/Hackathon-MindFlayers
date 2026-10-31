# Finbot — AI-Powered Financial Education Platform

<p align="center">
  <strong>Make smarter financial decisions.</strong><br/>
  An AI-powered personal finance companion for budgeting, goal planning, investment simulations, expense tracking, financial news, and scam awareness.
</p>

<p align="center">
  <a href="https://hackathon-mind-flayers.vercel.app/">Live Application</a>
  &nbsp;•&nbsp;
  <a href="https://finbot-backend-iqgn.onrender.com/">Backend API</a>
  &nbsp;•&nbsp;
  <a href="https://finbot-backend-iqgn.onrender.com/docs">API Documentation</a>
</p>

---

## Overview

**Finbot** is a full-stack financial education and money-management application designed to make personal finance easier to understand and act on. Users can create a financial profile, review their budget, track expenses, plan savings goals, simulate potential SIP growth, read updates from official Indian financial institutions, and learn to identify common financial scams.

The application combines a React frontend with a Python FastAPI backend. Its AI Financial Coach uses a hybrid Retrieval-Augmented Generation (RAG) pipeline to ground educational answers in local financial-education PDFs and trusted official sources, including the Reserve Bank of India (RBI), Securities and Exchange Board of India (SEBI), and National Centre for Financial Education (NCFE).

Financial projections and budget calculations are handled by deterministic backend logic. The language model is used to explain financial concepts and synthesize retrieved evidence; it is not treated as a calculator or a source of guaranteed investment outcomes.

## Live Deployment

| Component | URL | Hosting |
|---|---|---|
| Frontend | [hackathon-mind-flayers.vercel.app](https://hackathon-mind-flayers.vercel.app/) | Vercel |
| Backend | [finbot-backend-iqgn.onrender.com](https://finbot-backend-iqgn.onrender.com/) | Render |
| Backend API docs | [OpenAPI / Swagger UI](https://finbot-backend-iqgn.onrender.com/docs) | FastAPI |

The frontend communicates with the backend through the deployed API base URL:

```text
https://finbot-backend-iqgn.onrender.com/api
```

> **Deployment configuration:** The deployment notes supplied for this release identify `VITE_API_URL` as the Vercel environment variable. The repository snapshot inspected for this README has `frontend/src/services/api.js` reading `VITE_API_BASE_URL`. Vite environment variable names must match the name read by the frontend source exactly. Confirm the current `api.js` in the version being deployed and use that same key in Vercel; otherwise the frontend may fall back to `http://localhost:8000/api`. After changing a Vercel environment variable, trigger a new deployment because Vite embeds environment values at build time.

---

## Features

| Section | What it does |
|---|---|
| **Home** | Introduces Finbot and guides new users to set up a financial profile, open the dashboard, or try the scam-awareness game. |
| **Dashboard** | Shows key financial summaries, monthly budget analysis, deficit alerts, and the AI Financial Coach. |
| **Financial Profile** | Stores profile details such as income, investment budget, fixed and variable expenses, experience level, preferences, and goals. |
| **AI Financial Coach** | Answers financial education questions using retrieved evidence from local PDFs and trusted official online sources. |
| **Set Goals** | Creates, edits, and deletes financial goals; calculates savings requirements and displays progress projections. |
| **SIP Simulator** | Models hypothetical monthly SIP contributions over a selected period and compares pessimistic, expected, and optimistic return assumptions. |
| **Expenses** | Records expenses, filters transactions by month, and displays total and category-wise spending. |
| **RBI & SEBI News** | Fetches and displays updates from official RBI and SEBI feeds, with source filtering and refresh support. |
| **Scam or Legit** | Presents interactive financial scenarios to help users practice recognizing suspicious activity and common scams. |
| **Privacy controls** | Lets users hide displayed amounts and clear stored profile data, with an option to clear goals and expenses as well. |

## Technology Stack

### Frontend

- React 18
- Vite
- JavaScript
- React Router
- CSS
- Lucide React
- Recharts
- React Markdown and remark-gfm
- Fetch API

### Backend and AI

- Python
- FastAPI
- Uvicorn
- Groq API for LLM inference
- Sentence Transformers for text embeddings
- FAISS CPU for vector similarity search
- PyMuPDF for PDF text extraction
- HTTPX for trusted-source retrieval and RSS requests
- SQLite for profile, goal, and expense persistence
- python-dotenv for environment configuration

---

## How the AI Financial Coach Works

Finbot uses a hybrid RAG architecture to produce evidence-grounded financial education responses.

1. **Question routing** — The backend identifies the type and intent of the user's question, including greetings, follow-ups, factual questions, comparisons, and requests that require additional guardrails.
2. **Query understanding** — More complex questions can be decomposed into focused sub-queries so that individual parts of the question are covered.
3. **Local PDF retrieval** — Financial-education PDFs are extracted, chunked, embedded with Sentence Transformers, and indexed in FAISS. Relevant passages are retrieved for the user's question.
4. **Official-source retrieval** — The backend retrieves relevant information from trusted RBI, SEBI, and NCFE sources. It uses cached official knowledge when live retrieval is unavailable.
5. **Evidence ranking and fusion** — Candidate passages from different queries and sources are combined and ranked to improve coverage and relevance.
6. **Answer synthesis** — The retrieved evidence is passed to the configured Groq model to generate a clear, beginner-friendly explanation.
7. **Citations and evidence status** — The API can return citations to PDF documents and official web sources, along with evidence and retrieval status.

### Knowledge base

The backend includes financial-education PDFs under `backend/data/pdfs/`, including material covering:

- General financial education
- Securities markets
- Investing fundamentals
- Personal finance and budgeting
- Retirement and tax-advantaged accounts

The online retrieval component is designed around trusted official domains rather than unrestricted web search.

---

## Application Architecture

```text
┌─────────────────────────────────────────────────────┐
│                  React + Vite                       │
│                                                     │
│ Home | Dashboard | Goals | Simulator | Expenses     │
│ News | Scam or Legit                                │
│                                                     │
│ Profile / Shared Finance Context / API Services     │
└────────────────────────┬────────────────────────────┘
                         │ HTTPS / JSON
                         ▼
┌─────────────────────────────────────────────────────┐
│                    FastAPI                           │
│                                                     │
│ Profile | Dashboard | Budget | Goals | SIP          │
│ Expenses | News | Game | AI Chat                    │
└─────────────┬──────────────────────────┬────────────┘
              │                          │
              ▼                          ▼
┌────────────────────────┐   ┌─────────────────────────┐
│ SQLite persistence     │   │ Financial calculations  │
│ Profile                │   │ Budget analysis         │
│ Goals                  │   │ Goal savings plan       │
│ Expenses               │   │ SIP projections         │
└────────────────────────┘   └─────────────────────────┘

                         AI Chat
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│                    Hybrid RAG                        │
│                                                     │
│ Query Router → Query Understanding → Retrieval      │
│                                                     │
│   ┌────────────────────┐  ┌───────────────────────┐  │
│   │ Local PDF corpus   │  │ Official-source data  │  │
│   │ PyMuPDF            │  │ RBI / SEBI / NCFE     │  │
│   │ SentenceTransform. │  │ Live retrieval/cache  │  │
│   │ FAISS               │  │                       │  │
│   └──────────┬─────────┘  └───────────┬───────────┘  │
│              └────────────┬───────────┘              │
│                           ▼                          │
│                 Evidence fusion & ranking           │
│                           ▼                          │
│                  Groq LLM response                   │
│                           ▼                          │
│                Answer with source data               │
└─────────────────────────────────────────────────────┘
```

---

## Project Structure

```text
Hackathon-MindFlayers-main/
│
├── backend/
│   ├── api.py                       # FastAPI application and REST endpoints
│   ├── app.py                       # Streamlit/standalone backend interface
│   ├── rag.py                       # Hybrid RAG pipeline and answer generation
│   ├── ingest.py                    # PDF ingestion and FAISS index creation
│   ├── query_router.py              # Query intent classification and routing
│   ├── query_understanding.py       # Query analysis and decomposition
│   ├── web_retriever.py             # Trusted official-source retrieval
│   ├── storage.py                   # SQLite persistence
│   ├── finance_calculators.py       # Budget, goal, and SIP calculations
│   ├── calc_and_profile_handler.py  # Profile and calculation support
│   ├── news_service.py              # RBI and SEBI news feeds
│   ├── game_cards.py                # Scam-awareness scenarios
│   ├── game_service.py              # Game-round service
│   ├── data/
│   │   ├── pdfs/                    # Financial education PDFs
│   │   └── web_cache/               # Cached official-source knowledge
│   ├── requirements.txt
│   ├── .env.example
│   └── test_*.py                    # Backend test suites
│
├── frontend/
│   ├── src/
│   │   ├── components/              # Reusable UI components
│   │   ├── context/                 # Shared financial/profile state
│   │   ├── layouts/                 # Shared application layout
│   │   ├── pages/                   # Home, Dashboard, Goals, etc.
│   │   ├── services/                # API service modules
│   │   ├── App.jsx                  # Application routes
│   │   ├── main.jsx                 # React entry point
│   │   └── styles.css               # Global styles
│   ├── public/
│   ├── package.json
│   ├── .env.example
│   ├── vercel.json
│   └── vite.config.js
│
├── docs/
│   └── GAME.md
│
├── start-backend.bat
├── start-backend.sh
├── start-frontend.bat
└── start-frontend.sh
```

---

## Run Finbot Locally

### Prerequisites

- Python 3.11 or 3.12 recommended
- Node.js and npm
- Groq API key
- Internet connection for installing dependencies, initializing the embedding model, and retrieving official-source updates

Create a Groq API key at [Groq Console](https://console.groq.com/keys).

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd Hackathon-MindFlayers-main
```

### 2. Configure and start the backend

```bash
cd backend
python -m venv .venv
```

Activate the environment.

**Windows PowerShell**

```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create the environment file.

**Windows PowerShell**

```powershell
Copy-Item .env.example .env
```

**macOS / Linux**

```bash
cp .env.example .env
```

Add your Groq key to `backend/.env`:

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b

SIMILARITY_THRESHOLD=0.35
TOP_K=4
NEWS_CACHE_MINUTES=30

CORS_ORIGINS=https://hackathon-mind-flayers.vercel.app
```

Build the PDF index:

```bash
python ingest.py
```

Start FastAPI:

```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

The backend is available at:

- API base: `http://localhost:8000/api`
- Health: `http://localhost:8000/api/health`
- Swagger documentation: `http://localhost:8000/docs`

### 3. Configure and start the frontend

Open a second terminal:

```bash
cd frontend
npm install
```

Create the frontend environment file:

**Windows PowerShell**

```powershell
Copy-Item .env.example .env
```

**macOS / Linux**

```bash
cp .env.example .env
```

Set the API base URL using the variable name read by `frontend/src/services/api.js`:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

Then run:

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

### Quick-start scripts

The repository also includes scripts in the root directory:

| Task | Windows | macOS / Linux |
|---|---|---|
| Start backend | `.\start-backend.bat` | `./start-backend.sh` |
| Start frontend | `.\start-frontend.bat` | `./start-frontend.sh` |

Run the backend and frontend in separate terminals.

---

## Production Deployment

Finbot's current deployment uses **Vercel for the React frontend** and **Render for the FastAPI backend**.

### Frontend — Vercel

1. Import the GitHub repository into Vercel.
2. Set the **Root Directory** to `frontend`.
3. Use the following build settings:

   | Setting | Value |
   |---|---|
   | Framework | Vite |
   | Install command | `npm install` |
   | Build command | `npm run build` |
   | Output directory | `dist` |

4. Add the production backend API URL as a Vercel environment variable. Use the exact variable name read in `frontend/src/services/api.js`.

   ```env
   VITE_API_BASE_URL=https://finbot-backend-iqgn.onrender.com/api
   ```

5. Redeploy after changing environment variables. Vite reads `VITE_*` values at build time.

The repository includes `frontend/vercel.json` to rewrite frontend routes to `index.html`, allowing React Router routes to work after refreshing a page.

### Backend — Render

1. Create a new **Web Service** on Render and connect the repository.
2. Set the **Root Directory** to `backend`.
3. Configure:

   | Setting | Value |
   |---|---|
   | Runtime | Python |
   | Build command | `pip install -r requirements.txt && python ingest.py` |
   | Start command | `uvicorn api:app --host 0.0.0.0 --port $PORT` |

4. Add the required environment variables:

   ```env
   GROQ_API_KEY=your_groq_api_key
   GROQ_MODEL=openai/gpt-oss-120b
   SIMILARITY_THRESHOLD=0.35
   TOP_K=4
   NEWS_CACHE_MINUTES=30
   CORS_ORIGINS=https://hackathon-mind-flayers.vercel.app
   ```

5. Deploy the service and check its health endpoint:

   ```text
   https://finbot-backend-iqgn.onrender.com/api/health
   ```

### Deployment checklist

- [ ] Backend service is running on Render.
- [ ] `GROQ_API_KEY` is configured in Render.
- [ ] The PDF vector index is available after the backend build.
- [ ] `CORS_ORIGINS` includes the exact Vercel frontend origin.
- [ ] Vercel's API environment variable matches the variable name used in frontend source code.
- [ ] The Vercel deployment was rebuilt after changing environment variables.
- [ ] The frontend sends requests to `https://finbot-backend-iqgn.onrender.com/api`, not `localhost`.
- [ ] `/api/health` responds successfully.
- [ ] Profile, dashboard, chatbot, goals, simulator, expenses, news, and game flows have been tested on the deployed site.

### Production troubleshooting

| Symptom | What to check |
|---|---|
| Browser requests `localhost:8000` after deployment | The Vite API environment variable may be missing, incorrectly named, or not included in the latest Vercel build. Check `frontend/src/services/api.js`, Vercel Environment Variables, and redeploy. |
| Browser reports a CORS error | Set `CORS_ORIGINS` on Render to `https://hackathon-mind-flayers.vercel.app` with no trailing slash, then redeploy/restart the backend. |
| `ERR_CONNECTION_REFUSED` | Confirm the Render service is live and the frontend is using the deployed backend URL rather than localhost. |
| First backend request is slow | A Render service may be waking from an idle period. Retry after the service has started. |
| Chatbot fails but other API features work | Check the Render logs, `GROQ_API_KEY`, model configuration, and whether the FAISS index was generated successfully. |
| Chatbot has no document evidence | Verify that `python ingest.py` completed and the vector index is present in the deployed backend environment. |
| Data disappears after a redeploy | SQLite is file-based. Configure persistent storage for the database or use a managed database before relying on persistent production records. |

> **Important:** Do not use `localhost` as the API URL in a deployed frontend. In a user's browser, `localhost` refers to that user's own device, not the Render backend.

---

## API Reference

All application endpoints are exposed under `/api`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Reports RAG pipeline, index, and model readiness. |
| `POST` | `/api/chat` | Sends a question to the AI Financial Coach. |
| `GET` | `/api/profile` | Retrieves the saved financial profile. |
| `POST` | `/api/profile` | Creates or saves a profile. |
| `PUT` | `/api/profile` | Updates the profile. |
| `DELETE` | `/api/profile` | Clears profile data; `?everything=true` also clears goals and expenses. |
| `GET` | `/api/dashboard` | Retrieves dashboard summary values. |
| `GET` | `/api/budget/analysis` | Retrieves monthly budget analysis. |
| `GET` | `/api/goals` | Lists saved financial goals. |
| `POST` | `/api/goals` | Creates a financial goal. |
| `PUT` | `/api/goals/{goal_id}` | Updates a goal. |
| `DELETE` | `/api/goals/{goal_id}` | Deletes a goal. |
| `POST` | `/api/goals/plan` | Calculates a goal savings plan. |
| `POST` | `/api/simulator/sip` | Calculates hypothetical SIP projections. |
| `GET` | `/api/expenses` | Lists expenses; supports a month filter. |
| `POST` | `/api/expenses` | Adds an expense. |
| `GET` | `/api/expenses/summary` | Returns expense totals and category breakdown. |
| `DELETE` | `/api/expenses/{expense_id}` | Deletes an expense. |
| `GET` | `/api/news` | Retrieves RBI and SEBI news items. |
| `GET` | `/api/game/round` | Retrieves a Scam or Legit game round. |

For full request/response schemas, use the [live Swagger documentation](https://finbot-backend-iqgn.onrender.com/docs).

---

## Financial Calculations

Finbot separates deterministic calculations from AI-generated explanations.

- **Investment percentage:** Monthly investment budget divided by monthly income, multiplied by 100.
- **Budget analysis:** Uses profile income, recorded expenses, and active goal commitments to estimate the monthly balance and identify a deficit.
- **Goal planning:** Estimates the contribution needed to reach a target based on current savings and the selected duration.
- **SIP simulation:** Projects the future value of regular monthly contributions using the selected annual return assumption and duration. Scenario outputs are illustrative, not guaranteed.

The application should make assumptions visible wherever it presents projections. Market returns are uncertain and actual outcomes can differ from simulations.

---

## Data Storage and Privacy

- The backend uses SQLite for profile, financial goal, and expense persistence.
- The default database file is `backend/data/finguide.db`.
- The database path can be overridden with `FINGUIDE_DB_PATH`.
- The frontend's **Hide amounts** control masks financial values displayed in the interface.
- The **Clear data** flow can clear the saved profile and, when selected, goals and expense records.
- The frontend sends API requests to the configured backend URL.

The supplied implementation does not include a complete user authentication and multi-user authorization system. Do not treat it as a production banking application or store highly sensitive financial information without adding appropriate authentication, access controls, encryption, backups, and privacy safeguards.

---

## Tests

Backend test files are located in `backend/`.

Run the tests from the backend directory:

```bash
python -m unittest discover -p "test_*.py"
```

The chatbot and retrieval tests may require the PDF vector index to be generated first:

```bash
python ingest.py
```

---

## Contributing

Contributions and improvements are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Make focused changes and test them locally.
4. Keep API calls inside the frontend service layer.
5. Avoid committing `.env` files, API keys, local databases, or generated secrets.
6. Submit a pull request with a clear description of the change.

---

## Disclaimer

Finbot is an educational and informational tool. It does not provide personalized regulated investment advice, guarantee returns, or replace a qualified financial professional. Investment values can rise or fall, and all simulations are hypothetical. Verify important information with official sources and consult a SEBI-registered investment adviser before making investment decisions.
