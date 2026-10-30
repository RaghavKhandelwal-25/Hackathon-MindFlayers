# FinGuide — Hybrid Financial Education Assistant

FinGuide is an AI-powered financial education assistant built with Python, Streamlit, Groq, Sentence Transformers, FAISS, and PyMuPDF.

It combines **local financial education booklets (PDFs)** with **verified official Indian financial regulatory & educational portals (RBI, SEBI, NCFE)** to deliver grounded, transparent, and verifiable answers across factual, explanatory, analytical, comparative, causal, and multi-part financial inquiries.

---

## 🏛️ Architecture & System Highlights

```text
                                  USER QUERY
                                      │
                                      ▼
                      Conversational & Intent Router
                   (query_router.py: Greetings, Gratitude,
                 Advice Guardrails, Out-of-Scope, Follow-ups)
                                      │
                       [Financial Query / Follow-up]
                                      │
                                      ▼
                   Generalized Query Understanding & Need Analysis
                 (query_understanding.py: Structural Analysis,
             Facet Detection, Instant Sub-Query Decomposition)
                                      │
               ┌──────────────────────┴──────────────────────┐
               │                                             │
               ▼                                             ▼
       Multi-Query PDF Retrieval               Multi-Query Online Retrieval
     (FAISS CPU + all-MiniLM)                  (RBI / SEBI / NCFE Cache &
               │                                Live Safe Fetcher)
               │                                             │
               └──────────────────────┬──────────────────────┘
                                      │
                                      ▼
                     Reciprocal Rank Fusion (RRF) &
                   Facet Coverage Relevance Filtering
                                      │
                                      ▼
                  Evidence-Aware Synthesis & Partial Grounding
                     (Groq API: openai/gpt-oss-120b)
                                      │
                                      ▼
                     Dual Citations & Verifiable Links
                 (📄 Booklets + Page # | 🌐 Official URLs)
```

1. **Generalized Query Understanding**:
   - Classifies inquiries across 9 reasoning categories: `factual`, `explanatory`, `causal`, `advantages_disadvantages`, `comparative`, `risks_limitations`, `multi_part`, `practical_example`, and `follow_up`.
   - Generates 2–4 targeted complementary sub-queries using instant structural linguistics (0ms LLM overhead) to guarantee comprehensive facet coverage.
2. **Multi-Query Retrieval & Reciprocal Rank Fusion (RRF)**:
   - Evaluates sub-queries across both local FAISS index and official regulatory portals.
   - Combines candidate passages using Reciprocal Rank Fusion ($RRF = \sum \frac{1}{60 + rank}$) and max similarity pooling, preventing single-facet chunks from being crowded out by generic matches.
   - Automatically scales candidate depth adaptively (`top_k = 4` for direct factual, `top_k = 6-8` for multi-part or comparative queries).
3. **Evidence-Aware Synthesis & Abstention**:
   - Replaces all-or-nothing rejection with facet-aware synthesis: answers all supported aspects with precise citations while explicitly declaring which specific sub-questions are not covered in the reference documents.
   - Strictly abstains only when the reference evidence set is completely devoid of relevant facts.
4. **Dual-Source Hybrid Retrieval**:
   - **Local PDFs**: FAISS IndexFlatIP cosine similarity search over local financial education booklets (`data/pdfs/`).
   - **Official Online Sources**: Allowlist-enforced retrieval from trusted official portals:
     - **RBI** (`rbi.org.in`, `rbikehtahai.rbi.org.in`): Digital payment security, UPI PIN safety, OTP confidentiality, DICGC deposit insurance (up to Rs 5 Lakh), monetary policy.
     - **SEBI** (`investor.sebi.gov.in`, `sebi.gov.in`): Mutual funds categorization, Systematic Investment Plans (SIP) & Rupee Cost Averaging, Rule of 72, SCORES 2.0 investor grievance redressal.
     - **NCFE** (`ncfe.org.in`): National Centre for Financial Education 5 core competencies, purchasing power inflation erosion, NFLAT curriculum.
5. **Strict Network & Domain Security**:
   - Host validation against an explicit allowlist (`rbi.org.in`, `sebi.gov.in`, `ncfe.org.in`).
   - Private IP/loopback blocking (`127.0.0.1`, `localhost`, `10.x`, `192.168.x`).
   - Safe redirect handler that validates target hosts on every 301/302 redirect.
   - Max 2MB response caps and 5.0-second timeouts.
6. **Verifiable Dual Citations**:
   - Local PDFs: `📄 [Document Title, Page X]`
   - Official Web: `🌐 [Source Title](URL) (Updated: YYYY-MM-DD)`

---

## 📁 Project Structure

```text
finguide/
├── app.py                      # Streamlit UI with dual citations, suggested questions & reasoning modes
├── ingest.py                   # PyMuPDF PDF chunking, local embeddings & FAISS index builder
├── query_router.py             # Intent classification, typo normalization & follow-up context
├── query_understanding.py      # Structural query analysis & multi-query facet decomposition
├── rag.py                      # Hybrid RAG orchestrator, multi-query RRF fusion & Groq LLM
├── web_retriever.py            # Official online knowledge retriever, cache manager & domain security
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable template
├── .gitignore                  # Git exclusions (.env, .venv, vectorstore, cache binaries)
├── README.md                   # Documentation & instructions
├── test_finguide.py            # 42 unit and 15 evaluation scenario tests
├── test_general_evaluation.py  # 12-category general reasoning and retrieval evaluation suite
├── data/
│   ├── pdfs/                   # Local financial education booklets
│   └── web_cache/              # Official knowledge cache from RBI, SEBI, NCFE
└── vectorstore/
    ├── index.faiss             # Persisted FAISS index
    └── metadata.json           # Chunk metadata
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10 – 3.12 (Python 3.11 recommended on Windows).
- Groq API Key from [console.groq.com](https://console.groq.com/keys).

### 2. Activate Virtual Environment & Install
```powershell
cd C:\Users\Nityam\Desktop\Sphinx\finguide
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Verify `.env` File
Ensure your `.env` contains:
```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
SIMILARITY_THRESHOLD=0.35
TOP_K=4
```

### 4. Run the Complete Test Suites (54 Tests)
```powershell
.\.venv\Scripts\python.exe -m unittest test_finguide.py test_general_evaluation.py
```
*(Runs 54 automated tests: 42 system & scenario tests + 12 multi-category reasoning evaluation tests).*

### 5. Launch the Streamlit App
```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🧪 Reasoning Evaluation Categories (12/12 Passed)

| # | Category | Representative Query | Sub-Query Decomposition & Fusion |
|---|---|---|---|
| 1 | Direct Factual | What is the 50/30/20 budgeting rule? | Single targeted retrieval (`personal_finance_and_budgeting.pdf` p.1) |
| 2 | Explanatory | Explain how mutual funds pool money from investors | Conceptual pooling & fund structure retrieval |
| 3 | Causal | Why does inflation erode purchasing power over time? | Mechanism + economic impact dual sub-queries |
| 4 | Advantages & Disadvantages | Advantages and disadvantages of investing via SIP | Sub-query 1 (benefits, compounding) + Sub-query 2 (disadvantages, costs) |
| 5 | Comparative | How do equity funds differ from debt funds in risk and return? | Entity 1 (equity) + Entity 2 (debt) + comparative circular retrieval |
| 6 | Risks & Limitations | What are the risks and limitations of index funds? | Overview + tracking error/market risk facet retrieval |
| 7 | Multi-Part | What is emergency fund, how many months, where to keep? | 3 independent sub-clause queries merged via RRF |
| 8 | Multi-Passage Reasoning | Traditional IRA vs Roth IRA tax and withdrawal rules | Cross-passage synthesis (deductions vs retirement distributions) |
| 9 | Dual-Source Evidence | What is SIP, and what does SEBI say about Rupee Cost Averaging? | PDF definition + SEBI official portal grounding |
| 10 | Follow-Up Context | "What are its risks?" after "What is an index fund?" | Conversational reference resolution + facet query generation |
| 11 | Genuinely Insufficient Evidence | Corporate tax brackets in Liechtenstein for 2026 | Truthful abstention without hallucinated figures or citations |
| 12 | Conflicting / Outdated Sources | Outdated deposit insurance limit in 2019 PDF vs current RBI limit | Freshness preference and explicit discrepancy disclosure |
