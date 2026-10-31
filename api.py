"""FastAPI backend integration for FinGuide RAG pipeline.

Exposes RESTful endpoints for the React frontend (fincoach) and any external clients:
- GET /api/health: Pipeline, FAISS index, and model readiness status.
- POST /api/chat: Full RAG conversational query answering with dual-source citations (PDF and official web).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import AliasChoices, BaseModel, Field

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    dotenv.load_dotenv(dotenv_path=ENV_PATH, override=True)
else:
    dotenv.load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("finguide.api")

# Import RAG pipeline and SQLite storage
try:
    from rag import RAGPipeline, RAGResult, RetrievedChunk, WebRetrievedPassage
except ImportError:
    from finguide.rag import RAGPipeline, RAGResult, RetrievedChunk, WebRetrievedPassage

try:
    import storage
except ImportError:
    from finguide import storage

# Create FastAPI app
app = FastAPI(
    title="FinGuide RAG API",
    description="Evidence-grounded financial education RAG API with dual-source citations and functional goal planning.",
    version="1.0.0",
)

# Configure CORS to allow Raghav's React frontend
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global cached pipeline singleton
_pipeline: Optional[RAGPipeline] = None


def get_pipeline() -> RAGPipeline:
    """Return the cached RAG pipeline singleton, initializing if needed."""
    global _pipeline
    if _pipeline is None:
        logger.info("Initializing global FinGuide RAGPipeline...")
        _pipeline = RAGPipeline()
    return _pipeline


# Pydantic Request/Response Models
class HistoryItem(BaseModel):
    role: str = Field(..., description="Role of the sender: 'user', 'assistant', 'ai', etc.")
    content: Optional[str] = Field(None, description="Message text content")
    text: Optional[str] = Field(None, description="Alternative field for message text content")

    def get_text(self) -> str:
        return (self.content or self.text or "").strip()

    def get_normalized_role(self) -> str:
        r = self.role.strip().lower()
        if r in ("assistant", "ai", "bot", "finguide", "fincoach"):
            return "assistant"
        return "user"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's query or financial question")
    history: Optional[List[HistoryItem]] = Field(
        default_factory=list,
        description="Optional list of previous conversation turns",
    )
    profile: Optional[Dict[str, Any]] = Field(
        None, description="Optional user financial profile context (income, budget, expenses, goals)"
    )
    top_k: Optional[int] = Field(None, ge=1, le=10, description="Override top-k retrieval count")
    similarity_threshold: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Override similarity cutoff"
    )
    include_web_sources: Optional[bool] = Field(
        True, description="Whether to include official online regulator/NCFE evidence"
    )


class SourceCitation(BaseModel):
    title: str = Field(..., description="Source title or document name")
    type: str = Field(..., description="'pdf' for local documents, 'web' for official web sources")
    page: Optional[int] = Field(None, description="Page number for PDF documents")
    url: Optional[str] = Field(None, description="URL for official online sources")
    score: Optional[float] = Field(None, description="Normalized similarity or relevance score")
    date: Optional[str] = Field(None, description="Publication or update date if known")


class ChatResponse(BaseModel):
    reply: str = Field(..., description="Grounded answer synthesized by the LLM")
    sources: List[SourceCitation] = Field(
        default_factory=list, description="Unified structured source citations"
    )
    sufficient_evidence: bool = Field(
        True, description="Whether sufficient grounded evidence was found"
    )
    query_type: Optional[str] = Field(
        None, description="Classified information need type (e.g., factual, comparative)"
    )
    intent: Optional[str] = Field(None, description="Routing intent classification")
    network_status: Optional[str] = Field(
        "cached", description="Status of web retrieval: cached, live, or offline_fallback"
    )
    model_used: Optional[str] = Field(None, description="Groq model name used")


class HealthResponse(BaseModel):
    status: str
    index_ready: bool
    total_chunks: int
    documents: List[str]
    embedding_model: str
    groq_model: str


class ProfilePayload(BaseModel):
    fullName: Optional[str] = None
    email: Optional[str] = None
    age: Optional[Union[float, int]] = None
    occupation: Optional[str] = None
    monthlyIncome: Optional[float] = 0.0
    investmentBudget: Optional[float] = 0.0
    fixedExpenses: Optional[float] = 0.0
    variableExpenses: Optional[float] = 0.0
    experience: Optional[str] = None
    preferences: Optional[Union[List[str], str]] = None
    goals: Optional[Union[List[str], str]] = None


class GoalPayload(BaseModel):
    name: str = Field(..., min_length=1)
    targetAmount: float = Field(..., gt=0)
    currentSavings: Optional[float] = 0.0
    months: int = Field(..., gt=0)
    monthlyContribution: Optional[float] = None
    description: Optional[str] = None


class GoalPlanPayload(BaseModel):
    name: Optional[str] = "Goal"
    targetAmount: float = Field(..., gt=0)
    currentSavings: Optional[float] = 0.0
    months: int = Field(..., gt=0)
    monthlyContribution: Optional[float] = None


class SipSimulatorPayload(BaseModel):
    model_config = {"populate_by_name": True}

    monthlyContribution: float = Field(..., gt=0, validation_alias=AliasChoices("monthlyContribution", "monthlyAmount", "monthly"))
    annualReturn: float = Field(..., ge=0, le=100, validation_alias=AliasChoices("annualReturn", "annualReturnPct", "expectedReturn", "rate"))
    years: Optional[float] = Field(None, gt=0, le=60)
    months: Optional[int] = Field(None, gt=0, le=720)
    targetAmount: Optional[float] = Field(None, gt=0)


class ExpensePayload(BaseModel):
    amount: float = Field(..., gt=0)
    category: Optional[str] = "Other"
    note: Optional[str] = None
    date: Optional[str] = Field(None, description="YYYY-MM-DD, defaults to today")


@app.on_event("startup")
async def startup_event():
    """Log server startup readiness."""
    logger.info("FinGuide FastAPI service ready.")


@app.get("/", tags=["General"])
async def root():
    return {
        "message": "FinGuide Financial Education RAG API is running.",
        "docs_url": "/docs",
        "health_url": "/api/health",
    }


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Check system health, index status, and model configuration."""
    pipeline = get_pipeline()
    stats = pipeline.get_index_stats()
    return HealthResponse(
        status="ok",
        index_ready=stats.get("ready", False),
        total_chunks=stats.get("total_chunks", 0),
        documents=stats.get("documents", []),
        embedding_model=pipeline.embedding_model_name,
        groq_model=pipeline.groq_model_name,
    )


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(request: ChatRequest):
    """Process a user query through the FinGuide RAG pipeline and return grounded response and citations."""
    user_query = request.message.strip()
    if not user_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The 'message' field cannot be empty.",
        )

    pipeline = get_pipeline()

    # Normalize conversation history
    conv_history: List[Dict[str, str]] = []
    if request.history:
        for item in request.history:
            text = item.get_text()
            if text:
                conv_history.append(
                    {
                        "role": item.get_normalized_role(),
                        "content": text,
                    }
                )

    try:
        # Run query through RAG pipeline
        result: RAGResult = pipeline.query(
            question=user_query,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
            include_web_sources=request.include_web_sources if request.include_web_sources is not None else True,
            conversation_history=conv_history if conv_history else None,
            profile=request.profile,
        )

        # Build structured citations
        citations: List[SourceCitation] = []

        # 1. Local PDF sources
        for chunk in result.sources:
            citations.append(
                SourceCitation(
                    title=chunk.doc_title or chunk.doc_name,
                    type="pdf",
                    page=chunk.page_number,
                    url=None,
                    score=round(chunk.similarity_score, 4)
                    if chunk.similarity_score is not None
                    else None,
                )
            )

        # 2. Official web sources
        for wchunk in result.web_sources:
            citations.append(
                SourceCitation(
                    title=wchunk.title,
                    type="web",
                    page=None,
                    url=wchunk.url,
                    score=round(wchunk.similarity_score, 4)
                    if wchunk.similarity_score is not None
                    else None,
                    date=wchunk.date,
                )
            )

        return ChatResponse(
            reply=result.answer,
            sources=citations,
            sufficient_evidence=result.sufficient_evidence,
            query_type=getattr(result, "query_type", None),
            intent=getattr(result, "intent", None),
            network_status=getattr(result, "network_status", "cached"),
            model_used=result.model_used,
        )

    except Exception as exc:
        logger.error(f"Error handling /api/chat query '{user_query}': {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating response: {str(exc)}",
        )


# ==============================================================================
# USER PROFILE ENDPOINTS
# ==============================================================================


@app.get("/api/profile", tags=["Profile"])
async def get_user_profile():
    """Fetch the persistent user profile."""
    prof = storage.get_profile()
    return prof or {}


@app.post("/api/profile", tags=["Profile"])
@app.put("/api/profile", tags=["Profile"])
async def save_user_profile(payload: ProfilePayload):
    """Create or update the persistent user profile in SQLite."""
    try:
        saved = storage.save_profile(payload.model_dump())
        return saved
    except Exception as exc:
        logger.error(f"Error saving profile: {exc}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@app.delete("/api/profile", tags=["Profile"])
async def clear_user_profile(everything: bool = False):
    """Clear the saved profile (and, with ?everything=true, goals and logged expenses too)."""
    removed = storage.clear_user_data(everything)
    return {"status": "cleared", "removed": removed}


# ==============================================================================
# DASHBOARD & BUDGET ANALYSIS ENDPOINTS
# ==============================================================================


@app.get("/api/dashboard", tags=["Dashboard"])
async def get_dashboard_summary():
    """Return dashboard summary metrics computed from profile and goals."""
    prof = storage.get_profile() or {}
    inc = float(prof.get("monthlyIncome") or 0.0)
    inv = float(prof.get("investmentBudget") or 0.0)
    fixed = float(prof.get("fixedExpenses") or 0.0)
    var = float(prof.get("variableExpenses") or 0.0)
    total_spent = fixed + var
    inv_pct = (inv / inc * 100.0) if inc > 0 else 0.0
    return {
        "monthlyIncome": round(inc, 2),
        "investmentBudget": round(inv, 2),
        "totalSpent": round(total_spent, 2),
        "investmentPercentage": round(inv_pct, 1),
    }


@app.get("/api/budget/analysis", tags=["Budget"])
async def get_budget_analysis():
    """Return comprehensive monthly budget analysis, expense ratios, and savings capacity."""
    try:
        return storage.calculate_budget_analysis()
    except Exception as exc:
        logger.error(f"Error calculating budget analysis: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating budget analysis: {str(exc)}",
        )


# ==============================================================================
# FINANCIAL GOALS CRUD & PLANNING ENDPOINTS
# ==============================================================================


@app.get("/api/goals", tags=["Goals"])
async def list_user_goals():
    """List all financial goals saved in SQLite."""
    try:
        return storage.list_goals()
    except Exception as exc:
        logger.error(f"Error listing goals: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing goals: {str(exc)}",
        )


@app.post("/api/goals", tags=["Goals"])
async def create_user_goal(payload: GoalPayload):
    """Create a new financial goal in SQLite."""
    try:
        created = storage.create_goal(payload.model_dump())
        return created
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        logger.error(f"Error creating goal: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating goal: {str(exc)}",
        )


@app.put("/api/goals/{goal_id}", tags=["Goals"])
async def update_user_goal(goal_id: str, payload: GoalPayload):
    """Update an existing financial goal by ID."""
    try:
        updated = storage.update_goal(goal_id, payload.model_dump())
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Goal with id '{goal_id}' not found.",
            )
        return updated
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        logger.error(f"Error updating goal '{goal_id}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating goal: {str(exc)}",
        )


@app.delete("/api/goals/{goal_id}", tags=["Goals"])
async def delete_user_goal(goal_id: str):
    """Delete a financial goal by ID."""
    try:
        deleted = storage.delete_goal(goal_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Goal with id '{goal_id}' not found.",
            )
        return {"status": "deleted", "id": goal_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error deleting goal '{goal_id}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting goal: {str(exc)}",
        )


@app.post("/api/goals/plan", tags=["Goals"])
async def generate_goal_plan(payload: GoalPlanPayload):
    """Generate deterministic savings projection and plan for a goal."""
    try:
        plan = storage.calculate_goal_plan(payload.model_dump())
        return plan
    except Exception as exc:
        logger.error(f"Error generating goal plan: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating goal plan: {str(exc)}",
        )


# ==============================================================================
# SIP "WHAT IF" SIMULATOR
# ==============================================================================


@app.post("/api/simulator/sip", tags=["Simulator"])
async def simulate_sip(payload: SipSimulatorPayload):
    """Simulate SIP growth: summary, growth series, return scenarios and optional goal check."""
    from finance_calculators import simulate_sip_whatif

    if payload.months is None and payload.years is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide 'years' or 'months'.")
    months = payload.months if payload.months is not None else int(round(payload.years * 12))
    try:
        return simulate_sip_whatif(payload.monthlyContribution, payload.annualReturn, months, payload.targetAmount)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


# ==============================================================================
# EXPENSE TRACKING ENDPOINTS
# ==============================================================================


@app.get("/api/expenses", tags=["Expenses"])
async def list_user_expenses(month: Optional[str] = None):
    """List logged expenses (optionally for one month, format YYYY-MM)."""
    return storage.list_expenses(month)


@app.post("/api/expenses", tags=["Expenses"])
async def add_user_expense(payload: ExpensePayload):
    """Log a new expense."""
    try:
        return storage.create_expense(payload.model_dump())
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@app.get("/api/expenses/summary", tags=["Expenses"])
async def get_expense_summary(month: Optional[str] = None):
    """Spending total and per-category breakdown for a month (default: current)."""
    return storage.expense_summary(month)


@app.delete("/api/expenses/{expense_id}", tags=["Expenses"])
async def delete_user_expense(expense_id: str):
    """Delete a logged expense."""
    if not storage.delete_expense(expense_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Expense '{expense_id}' not found.")
    return {"status": "deleted", "id": expense_id}


# ==============================================================================
# NEWS (live RBI and SEBI feeds)
# ==============================================================================


@app.get("/api/news", tags=["News"])
async def get_market_news(source: str = "all", limit: int = 30, refresh: bool = False):
    """Latest RBI and SEBI updates from their official RSS feeds (cached ~30 minutes).

    source: all | rbi | sebi. refresh=true asks for a fresh copy (rate limited to once a minute per source).
    """
    import news_service

    source = source.lower()
    if source != "all" and source not in news_service.SOURCES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="source must be one of: all, rbi, sebi.")
    limit = max(1, min(limit, 100))
    return await news_service.get_news(source, limit, refresh)


# ==============================================================================
# GAME: "Scam or Legit?"
# ==============================================================================


@app.get("/api/game/round", tags=["Game"])
async def get_game_round(mode: str = "daily"):
    """Cards for one round of Scam or Legit. mode: daily (same for everyone today) or practice (random)."""
    import game_service

    try:
        return game_service.build_round(mode)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
