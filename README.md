# Finbot — AI-Powered Financial Education & Management Platform

Finbot is a personal finance web application that helps users understand their money, build better budgeting habits, plan financial goals, explore hypothetical investment growth, follow official financial-sector updates, and learn to identify online scams.

It combines a React frontend with a FastAPI backend. Its AI financial coach uses a **hybrid retrieval-augmented generation (RAG) pipeline**: it retrieves relevant information from local financial-education PDFs and trusted official Indian sources such as the Reserve Bank of India (RBI), Securities and Exchange Board of India (SEBI), and National Centre for Financial Education (NCFE). Financial calculations are handled by backend calculation logic rather than being left to the language model.

> **Disclaimer:** Finbot is an educational platform. It does not provide personalized regulated investment advice, guarantee returns, or recommend specific securities to buy or sell. Investment projections are hypothetical; actual returns may differ and investments involve risk.

---

## Contents

- [Features](#features)
- [Application Sections](#application-sections)
- [Technology Stack](#technology-stack)
- [How the AI Coach Works](#how-the-ai-coach-works)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Configuration](#environment-configuration)
- [API Reference](#api-reference)
- [Data and Privacy](#data-and-privacy)
- [Running Tests](#running-tests)
- [Deployment Notes](#deployment-notes)
- [Disclaimer](#disclaimer)

---

## Features

| Feature | Description |
|---|---|
| AI Financial Coach | Ask financial questions and receive educational answers grounded in financial PDFs and trusted official sources, with citations where available. |
| Financial Profile | Save and edit basic profile details, income, investment budget, expenses, experience level, preferences, and financial goals. |
| Dashboard | View income, investment budget, planned expenses, investment percentage, budget analysis, and the AI chat interface. |
| Budget Analysis | Review income, recorded expenses, goal commitments, remaining balance, and potential monthly deficit using deterministic calculations. |
| Goal Planning | Create, edit, and delete goals; calculate the required contribution and view projected progress. |
| SIP Simulator | Explore hypothetical SIP growth using monthly contributions, duration, and expected annual return. Compare pessimistic, expected, and optimistic scenarios and optionally check a target amount. |
| Expense Tracking | Add and remove expenses, filter by month, and view totals and category-wise spending summaries. |
| RBI & SEBI News | Read updates from official RBI and SEBI RSS feeds, filter by source, and request a refresh. |
| Scam or Legit Game | Learn to recognize common financial scams through interactive scenario cards. |
| Privacy Controls | Hide displayed financial amounts and clear saved profile data, with an option to clear goals and logged expenses as well. |

---

## Application Sections

Finbot currently includes the following navigation sections:

1. **Home** — Introduction to Finbot, profile setup entry point, and a quick overview of how the application works.
2. **Dashboard** — Financial summary cards, monthly budget analysis, and the AI Financial Coach.
3. **Set Goals** — Create and manage financial goals, generate savings plans, and view goal progress visualizations.
4. **Simulator** — Run a “what if” SIP simulation and compare estimated outcomes under different return assumptions.
5. **Expenses** — Record transactions and inspect monthly and category-wise spending.
6. **News** — Browse RBI and SEBI updates from their official feeds.
7. **Play** — Practice identifying suspicious and legitimate financial scenarios in the Scam or Legit game.

---

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React 18, Vite, JavaScript |
| Styling & UI | CSS, Lucide React |
| Routing | React Router |
| Charts | Recharts |
| Markdown rendering | React Markdown, remark-gfm |
| Backend | Python, FastAPI, Uvicorn |
| AI model API | Groq |
| Embeddings | Sentence Transformers |
| Vector search | FAISS CPU |
| PDF processing | PyMuPDF |
| Database | SQLite |
| News retrieval | Official RBI and SEBI RSS feeds, HTTPX |
| Configuration | python-dotenv |

---

## How the AI Coach Works

Finbot's chatbot is designed around evidence-grounded financial education rather than unrestricted, unsupported answers.

1. **Question understanding** — The backend examines the user's question, identifies its intent, and can break complex questions into focused sub-queries.
2. **Local document retrieval** — Relevant passages are retrieved from indexed financial-education PDFs using Sentence Transformers embeddings and FAISS similarity search.
3. **Official-source retrieval** — The system can retrieve relevant material from an allowlist of official RBI, SEBI, and NCFE websites. Cached official knowledge can be used when a live fetch is unavailable.
4. **Evidence combination** — Retrieved passages are ranked and combined so that different parts of a multi-part question can be addressed.
5. **Answer generation** — The Groq-hosted language model generates a response using the retrieved evidence and the user's supplied financial context when relevant.
6. **Source attribution** — The API returns source information for local PDF passages and official web passages. Answers can identify document pages or link to official sources.

The backend also includes guardrails for unsupported questions and personalized investment-advice requests. When the available evidence is insufficient, the assistant is designed to say so rather than invent financial facts.

### Knowledge sources

- Local financial-education PDFs stored in `backend/data/pdfs/`
- Official RBI resources and publications
- Official SEBI investor-education resources
- NCFE financial-literacy resources

The live retrieval layer restricts online source retrieval to configured trusted official domains.

---

## Architecture

```text
                  ┌──────────────────────────┐
                  │       React + Vite       │
                  │       Frontend           │
                  │                          │
                  │ Home • Dashboard • Goals │
                  │ Simulator • Expenses     │
                  │ News • Scam or Legit      │
                  └────────────┬─────────────┘
                               │ HTTP / JSON
                               ▼
                  ┌──────────────────────────┐
                  │       FastAPI API        │
                  │                          │
                  │ Profile • Dashboard      │
                  │ Chat • Goals • Simulator │
                  │ Expenses • News • Game   │
                  └───────┬──────────┬───────┘
                          │          │
              ┌───────────▼───┐  ┌───▼────────────────┐
              │ SQLite        │  │ Financial Logic    │
              │ Profile       │  │ Budget analysis    │
              │ Goals         │  │ Goal planning      │
              │ Expenses      │  │ SIP calculations   │
              └───────────────┘  └────────────────────┘

                          Chat request
                               │
                               ▼
                  ┌──────────────────────────┐
                  │       RAG Pipeline       │
                  │ Query understanding      │
                  │ Retrieval and ranking    │
                  │ Evidence-aware synthesis │
                  └───────┬──────────┬───────┘
                          │          │
                ┌─────────▼───┐  ┌───▼────────────────┐
                │ Local PDFs  │  │ Official web data  │
                │ PyMuPDF     │  │ RBI • SEBI • NCFE  │
                │ Embeddings  │  │ Retrieval + cache  │
                │ FAISS       │  └────────────────────┘
                └─────────────┘
                          │
                          ▼
                  ┌──────────────────────────┐
                  │       Groq API            │
                  │ Evidence-grounded answer │
                  └──────────────────────────┘
```

---

## Project Structure

```text
Hackathon-MindFlayers-main/
│
├── backend/
│   ├── api.py                       # FastAPI application and REST endpoints
│   ├── rag.py                       # RAG pipeline and answer generation
│   ├── ingest.py                    # PDF ingestion and FAISS index creation
│   ├── query_router.py              # Query intent routing
│   ├── query_understanding.py       # Query analysis and decomposition
│   ├── web_retriever.py             # Trusted official-source retrieval
│   ├── storage.py                   # SQLite persistence and data operations
│   ├── finance_calculators.py       # Financial and SIP calculations
│   ├── calc_and_profile_handler.py  # Profile and calculation support
│   ├── news_service.py              # RBI and SEBI RSS feed service
│   ├── game_cards.py                # Scam or Legit game scenarios
│   ├── game_service.py              # Game-round generation
│   ├── data/
│   │   ├── pdfs/                    # Financial education source documents
│   │   └── web_cache/               # Cached official-source knowledge
│   ├── requirements.txt
│   ├── .env.example
│   └── test_*.py                    # Backend test suites
│
├── frontend/
│   ├── src/
│   │   ├── components/              # Profile, spending and clear-data UI
│   │   ├── context/                 # Shared finance/profile state
│   │   ├── layouts/                 # Shared application layout
│   │   ├── pages/                   # Home, Dashboard, Goals, etc.
│   │   ├── services/                # Frontend API service modules
│   │   ├── App.jsx                  # Application routes
│   │   ├── main.jsx                 # React entry point
│   │   └── styles.css               # Global styling
│   ├── public/
│   ├── package.json
│   ├── vite.config.js
│   └── .env.example
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

## Getting Started

### Prerequisites

Install the following before running Finbot:

- **Python 3.11 or 3.12** (recommended)
- **Node.js** and npm
- A **Groq API key** for AI-generated chatbot responses
- Internet access for installing dependencies, building the PDF index, and retrieving live official-source updates

Get a Groq API key from [Groq Console](https://console.groq.com/keys).

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd Hackathon-MindFlayers-main
```

### 2. Set up the backend

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment:

**Windows PowerShell**
```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Create the backend environment file:

**Windows PowerShell**
```powershell
Copy-Item .env.example .env
```

**macOS / Linux**
```bash
cp .env.example .env
```

Open `backend/.env` and add your Groq API key:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
SIMILARITY_THRESHOLD=0.35
TOP_K=4
NEWS_CACHE_MINUTES=30
```

Build the local PDF vector index:

```bash
python ingest.py
```

This creates the FAISS index and its metadata under `backend/vectorstore/`. The first run downloads/initializes the embedding model and may take some time.

Start the API server:

```bash
python -m uvicorn api:app --reload --port 8000
```

The backend will be available at:

- API: `http://localhost:8000`
- Interactive API documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

### 3. Set up the frontend

Open a second terminal from the repository root:

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

The local API URL should be:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

Start the frontend:

```bash
npm run dev
```

Open `http://localhost:5173` in your browser.

### Quick start scripts

The repository also provides convenience scripts in the root directory:

| Operating system | Backend | Frontend |
|---|---|---|
| Windows | `.\start-backend.bat` | `.\start-frontend.bat` |
| macOS / Linux | `./start-backend.sh` | `./start-frontend.sh` |

The backend script installs Python dependencies, creates `backend/.env` from the example if needed, builds the PDF index if it is missing, and starts Uvicorn. The frontend script installs npm dependencies and starts Vite.

---

## Environment Configuration

### Backend — `backend/.env`

| Variable | Purpose | Default / Example |
|---|---|---|
| `GROQ_API_KEY` | API key used for LLM answer generation | Required |
| `GROQ_MODEL` | Groq model identifier | `openai/gpt-oss-120b` |
| `SIMILARITY_THRESHOLD` | Minimum relevance threshold for retrieval | `0.35` |
| `TOP_K` | Number of top retrieved chunks | `4` |
| `NEWS_CACHE_MINUTES` | Cache duration for news feeds | `30` |
| `CORS_ORIGINS` | Comma-separated deployed frontend origins | Optional |

### Frontend — `frontend/.env`

| Variable | Purpose | Local value |
|---|---|---|
| `VITE_API_BASE_URL` | Base URL for the FastAPI backend; include `/api` | `http://localhost:8000/api` |

Do not commit real API keys or private environment files to version control.

---

## API Reference

The backend exposes the following endpoints under `/api`.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Check backend and RAG pipeline status |
| `POST` | `/api/chat` | Submit a question to the AI Financial Coach |
| `GET` | `/api/profile` | Retrieve the saved profile |
| `POST` | `/api/profile` | Create a profile |
| `PUT` | `/api/profile` | Update the profile |
| `DELETE` | `/api/profile` | Clear profile data; use `?everything=true` to also clear goals and expenses |
| `GET` | `/api/dashboard` | Retrieve dashboard summary metrics |
| `GET` | `/api/budget/analysis` | Retrieve budget analysis |
| `GET` | `/api/goals` | List financial goals |
| `POST` | `/api/goals` | Create a financial goal |
| `PUT` | `/api/goals/{goal_id}` | Update a goal |
| `DELETE` | `/api/goals/{goal_id}` | Delete a goal |
| `POST` | `/api/goals/plan` | Generate a deterministic goal savings plan |
| `POST` | `/api/simulator/sip` | Calculate SIP projection and return scenarios |
| `GET` | `/api/expenses` | List expenses; optional `month=YYYY-MM` filter |
| `POST` | `/api/expenses` | Add an expense |
| `GET` | `/api/expenses/summary` | Retrieve monthly expense totals and category breakdown |
| `DELETE` | `/api/expenses/{expense_id}` | Delete an expense |
| `GET` | `/api/news` | Retrieve RBI and SEBI updates |
| `GET` | `/api/game/round` | Retrieve a Scam or Legit game round |

For news, the `source` query parameter accepts `all`, `rbi`, or `sebi`. Use `refresh=true` to request a fresh feed fetch, subject to the service's refresh limit.

For full request schemas and interactive endpoint testing, open `http://localhost:8000/docs` while the backend is running.

---

## Data and Privacy

- Profile, goal, and expense records are stored by the backend in a SQLite database.
- The default database location is `backend/data/finguide.db`.
- You can override the database path using `FINGUIDE_DB_PATH`.
- The **Hide amounts** control masks displayed financial values in the frontend. Its preference is stored in browser local storage.
- The **Clear data** flow can clear the saved profile. It also offers an option to delete goals and logged expenses.
- The frontend communicates with the backend through the configured API base URL.

This project does not implement a full authentication system in the supplied code. Do not expose an unprotected deployment to public users or store real user financial data in a production environment without adding appropriate authentication, authorization, transport security, and operational safeguards.

---

## Running Tests

Backend tests are located in `backend/`.

From the repository root:

```bash
cd backend
python -m unittest discover -p "test_*.py"
```

Some chatbot/RAG tests require the PDF vector index to be built first:

```bash
python ingest.py
```

Run the test suite after installing the backend dependencies and configuring the environment as required by the tests.

---

## Deployment Notes

### Backend

Deploy the FastAPI application to a Python-compatible hosting service.

Typical commands, executed from the `backend/` directory:

```bash
pip install -r requirements.txt
python ingest.py
uvicorn api:app --host 0.0.0.0 --port $PORT
```

Configure at least:

- `GROQ_API_KEY`
- `GROQ_MODEL` (if using a non-default model)
- `CORS_ORIGINS` with the deployed frontend origin

The PDF vector index must be generated or supplied to the deployed environment. The embedding model and FAISS index require additional memory and disk space. Since the application uses SQLite by default, configure persistent storage for the database if records must survive redeployments.

### Frontend

The frontend can be deployed to a static hosting platform such as Vercel or Netlify.

From `frontend/`:

```bash
npm install
npm run build
```

Set `VITE_API_BASE_URL` to the deployed backend URL ending in `/api`. The production build is generated in `frontend/dist/`.

---

## Disclaimer

Finbot is intended for financial literacy and educational exploration. It provides informational responses and hypothetical calculations, not personalized regulated investment advice. It does not guarantee investment returns or account for every user's circumstances. Always verify important information with official sources and consult a SEBI-registered investment adviser before making investment decisions.
