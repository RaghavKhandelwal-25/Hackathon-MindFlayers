"""Finbot Streamlit Chat Application.

Interactive financial education assistant combining verified local PDF documents
with official Indian financial regulatory & educational sources (RBI, SEBI, NCFE).
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import dotenv
import streamlit as st

# Configure page metadata
st.set_page_config(
    page_title="Finbot — Hybrid Financial Education Assistant",
    page_icon="🪙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("finguide.app")

# Ensure app directory is in sys.path
_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

# Explicitly load .env from project root
_ENV_FILE = _APP_DIR / ".env"
if _ENV_FILE.exists():
    dotenv.load_dotenv(dotenv_path=_ENV_FILE, override=True)
else:
    dotenv.load_dotenv()

# Import local modules
try:
    from ingest import get_default_paths, ingest_documents
    from query_router import IntentType, classify_intent
    from rag import GroqConfigurationError, IndexNotFoundError, RAGPipeline, RAGResult
    from web_retriever import OfficialWebRetriever, WebRetrievedPassage
except ImportError:
    from finguide.ingest import get_default_paths, ingest_documents
    from finguide.query_router import IntentType, classify_intent
    from finguide.rag import GroqConfigurationError, IndexNotFoundError, RAGPipeline, RAGResult
    from finguide.web_retriever import OfficialWebRetriever, WebRetrievedPassage


@st.cache_resource(show_spinner="Loading embedding model and knowledge bases...")
def get_rag_pipeline() -> RAGPipeline:
    """Instantiate and cache the RAGPipeline singleton so that the embedding model

    and vector stores are never reloaded on every user query.
    """
    return RAGPipeline()


def main():
    # Header and Educational Title
    st.markdown(
        """
        <div style="padding: 0.8rem 0; border-bottom: 2px solid #e0e0e0; margin-bottom: 1.2rem;">
            <h1 style="margin: 0; display: inline-block;">🪙 Finbot</h1>
            <span style="font-size: 1.2rem; color: #444; margin-left: 12px; font-weight: 500;">
                Hybrid Financial Education Assistant
            </span>
            <p style="margin-top: 6px; color: #666; font-size: 0.95rem;">
                Grounded in verified local educational PDFs and trusted official Indian regulatory portals (<strong>RBI</strong>, <strong>SEBI</strong>, <strong>NCFE</strong>).
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    data_dir, vectorstore_dir = get_default_paths()
    pipeline = get_rag_pipeline()
    web_retriever = pipeline.get_web_retriever()

    # Initialize Session State
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "pending_prompt" not in st.session_state:
        st.session_state.pending_prompt = None

    # Sidebar: Knowledge Base Status & Settings
    with st.sidebar:
        st.header("⚙️ System Status & Settings")

        # 1. Local PDF Knowledge Base Status
        stats = pipeline.get_index_stats()
        is_ready = stats.get("ready", False)

        st.subheader("📄 Local PDF Knowledge Base")
        if is_ready:
            st.success("✅ PDF Vector Index Active")
            st.caption(f"**Indexed Chunks:** {stats.get('total_chunks', 0)}")
            docs = stats.get("documents", [])
            if docs:
                with st.expander(f"📁 Ingested PDFs ({len(docs)})", expanded=False):
                    for doc in docs:
                        st.markdown(f"- `{doc}`")
        else:
            st.warning("⚠️ Local PDF Index Missing")
            st.info("Ingest documents in `data/pdfs/` to enable local PDF retrieval.")

        if st.button("🔄 Run PDF Ingestion", use_container_width=True):
            with st.spinner("Extracting text and building FAISS index..."):
                try:
                    num_chunks = ingest_documents()
                    st.cache_resource.clear()
                    st.success(f"Ingested {num_chunks} chunks successfully!")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Ingestion failed: {exc}")

        st.divider()

        # 2. Official Online Knowledge Sources (RBI, SEBI, NCFE)
        st.subheader("🌐 Official Online Sources")
        if web_retriever.is_cache_ready():
            st.success("✅ Official Regulators Active (RBI / SEBI / NCFE)")
            with st.expander("🏛️ Trusted Regulatory Portals", expanded=False):
                sources = web_retriever.get_supported_sources()
                for s in sources:
                    st.markdown(f"- [{s['title']}]({s['url']}) (`{s['category']}`)")
        else:
            st.warning("⚠️ Official web cache not initialized.")

        st.divider()

        # 3. LLM Setup
        st.subheader("🤖 Groq LLM Setup")
        env_key = os.getenv("GROQ_API_KEY", "")
        has_env_key = bool(env_key and env_key != "your_groq_api_key_here")

        if has_env_key:
            st.caption("🔒 `GROQ_API_KEY` loaded from environment.")
            user_api_key = st.text_input(
                "Override API Key (Optional)",
                type="password",
                placeholder="gsk_...",
                help="Leave empty to use the key from your .env file.",
            )
            active_key = user_api_key.strip() if user_api_key.strip() else env_key
        else:
            st.warning("No API key detected in `.env`.")
            active_key = st.text_input(
                "Enter Groq API Key",
                type="password",
                placeholder="gsk_...",
                help="Get your free API key at https://console.groq.com/keys",
            )

        model_options = [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "qwen/qwen3.8-27b",
            "allam-2-7b",
        ]
        env_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
        if env_model and env_model not in model_options:
            model_options.insert(0, env_model)
        default_idx = model_options.index(env_model) if env_model in model_options else 0

        selected_model = st.selectbox(
            "Model Identifier",
            options=model_options,
            index=default_idx,
            help="Configurable LLM from Groq.",
        )

        st.divider()

        # 4. Retrieval Tuning
        st.subheader("🔍 Retrieval Tuning")
        top_k = st.slider(
            "Top PDF Chunks (Top-K)",
            min_value=1,
            max_value=5,
            value=int(os.getenv("TOP_K", "4")),
            help="Number of relevant PDF document chunks retrieved per query.",
        )

        similarity_threshold = st.slider(
            "Relevance Threshold (Cosine Sim)",
            min_value=0.10,
            max_value=0.80,
            value=float(os.getenv("SIMILARITY_THRESHOLD", "0.35")),
            step=0.05,
            help="Minimum vector similarity score required for relevance.",
        )

        st.divider()

        # 5. Chat History Management
        if st.button("🗑️ Reset Conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.pending_prompt = None
            st.rerun()

        st.caption(
            "⚠️ **Disclaimer**: Finbot provides financial education only. "
            "It does not provide personalized investment advice or guaranteed return forecasts."
        )

    # Welcome Banner and Suggested Questions if conversation is empty
    if not st.session_state.messages:
        st.markdown(
            """
            ### Welcome to Finbot! 🪙
            Your dual-source financial literacy companion. Finbot explains financial concepts in beginner-friendly language,
            strictly grounded in **local financial education booklets** and **official Indian regulatory portals** (RBI, SEBI, NCFE).
            
            #### 💡 Try Asking:
            """
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🛡️ How do I protect against UPI fraud? (RBI Kehta Hai)", use_container_width=True):
                st.session_state.pending_prompt = "How does RBI Kehta Hai advise protecting against digital payment and UPI fraud?"
                st.rerun()
            if st.button("📊 What is the 50/30/20 budgeting rule?", use_container_width=True):
                st.session_state.pending_prompt = "What is the 50/30/20 budgeting rule?"
                st.rerun()
        with col2:
            if st.button("📈 What is a SIP and Rupee Cost Averaging?", use_container_width=True):
                st.session_state.pending_prompt = "What is a Systematic Investment Plan (SIP) and how does Rupee Cost Averaging work?"
                st.rerun()
            if st.button("⚖️ What are investor rights under SEBI SCORES?", use_container_width=True):
                st.session_state.pending_prompt = "What is the SEBI SCORES platform and what are my rights as a retail investor?"
                st.rerun()

        st.divider()

    # Main Chat Area: Render previous messages
    for msg in st.session_state.messages:
        role = msg["role"]
        content = msg["content"]
        pdf_sources = msg.get("sources", [])
        web_sources = msg.get("web_sources", [])

        with st.chat_message(role):
            st.markdown(content)

            # Display dual-source citations and references for assistant messages
            if role == "assistant" and (pdf_sources or web_sources):
                total_sources = len(pdf_sources) + len(web_sources)
                with st.expander(f"📚 View Citations & Sources ({total_sources})", expanded=False):
                    # Local PDF citations
                    if pdf_sources:
                        st.markdown("#### 📄 Local Financial Booklets")
                        for i, src in enumerate(pdf_sources, 1):
                            score_val = src.get("similarity_score")
                            score_disp = f" | `Sim Score: {score_val:.3f}`" if score_val is not None else ""
                            st.markdown(
                                f"**{i}. {src.get('doc_title', 'Document')}** — "
                                f"`Page {src.get('page_number', 'N/A')}` | "
                                f"`File: {src.get('doc_name', '')}`{score_disp}"
                            )
                            st.markdown(f"> *\"{src.get('text', '')}\"*")
                            st.write("")

                    # Official Online citations
                    if web_sources:
                        st.markdown("#### 🌐 Official Regulatory Portals (RBI / SEBI / NCFE)")
                        for j, wsrc in enumerate(web_sources, 1):
                            score_val = wsrc.get("similarity_score")
                            score_disp = f" | `Sim Score: {score_val:.3f}`" if score_val is not None else ""
                            date_disp = f" | `Updated: {wsrc.get('date')}`" if wsrc.get("date") else ""
                            st.markdown(
                                f"**{j}. [{wsrc.get('title', 'Official Portal')}]({wsrc.get('url', '#')})**{date_disp}{score_disp}"
                            )
                            st.markdown(f"> *\"{wsrc.get('text', '')}\"*")
                            st.write("")

    # Chat Input: Check if a suggested prompt was clicked or user typed input
    user_prompt = st.session_state.pending_prompt or st.chat_input("Ask a financial question (e.g., 'wht is sip' or 'RBI UPI safety rules')...")
    st.session_state.pending_prompt = None

    if user_prompt:
        # Check intent
        early_route = classify_intent(user_prompt, history=st.session_state.messages)

        # Check if local PDF index is missing when required
        if early_route.should_retrieve and not pipeline.is_index_ready() and not web_retriever.is_cache_ready():
            st.error(
                "❌ **Knowledge base is not ready.**\n\n"
                "Please place financial PDFs in `data/pdfs/` and click "
                "**'Run PDF Ingestion'** in the sidebar."
            )
            return

        # Display user message
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        # Assistant response generation
        with st.chat_message("assistant"):
            with st.spinner("Retrieving evidence and generating answer..."):
                try:
                    result: RAGResult = pipeline.query(
                        question=user_prompt,
                        top_k=top_k,
                        similarity_threshold=similarity_threshold,
                        override_groq_key=active_key,
                        override_model=selected_model,
                        conversation_history=st.session_state.messages,
                    )

                    # Show interpreted query caption if spelling/acronym normalization occurred
                    if (
                        result.interpreted_query
                        and result.interpreted_query.strip().lower() != user_prompt.strip().lower()
                        and result.intent in (IntentType.FINANCIAL_QUERY.value, IntentType.FOLLOW_UP.value)
                    ):
                        st.caption(f"🔍 *Interpreted query for retrieval: \"{result.interpreted_query}\"*")

                    # Show reasoning mode caption if multi-faceted reasoning was applied
                    q_type = getattr(result, "query_type", None)
                    if q_type and q_type not in ("factual", None):
                        type_labels = {
                            "comparative": "Comparative Analysis",
                            "advantages_disadvantages": "Benefits & Limitations Evaluation",
                            "risks_limitations": "Risk & Caveat Assessment",
                            "causal": "Causal & Mechanism Exploration",
                            "multi_part": "Multi-Part Query Synthesis",
                            "practical_example": "Conceptual & Illustrative Reasoning",
                        }
                        label = type_labels.get(q_type, q_type.replace("_", " ").title())
                        st.caption(f"🧠 *Reasoning Mode: {label} (Multi-facet evidence fusion)*")

                    # Friendly network status notification if fallback occurred
                    if getattr(result, "network_status", "cached") == "offline_fallback":
                        st.caption("ℹ️ *Notice: Live online portals were unreachable; used verified official cached guidance.*")

                    st.markdown(result.answer)

                    # Serialize sources for session state
                    serialized_pdf_sources = [
                        {
                            "chunk_id": chunk.chunk_id,
                            "doc_name": chunk.doc_name,
                            "doc_title": chunk.doc_title,
                            "page_number": chunk.page_number,
                            "similarity_score": chunk.similarity_score,
                            "text": chunk.text,
                        }
                        for chunk in result.sources
                    ]

                    serialized_web_sources = [
                        {
                            "passage_id": wchunk.passage_id,
                            "url": wchunk.url,
                            "title": wchunk.title,
                            "domain": wchunk.domain,
                            "date": wchunk.date,
                            "similarity_score": wchunk.similarity_score,
                            "text": wchunk.text,
                        }
                        for wchunk in result.web_sources
                    ]

                    total_sources = len(result.sources) + len(result.web_sources)
                    if total_sources > 0:
                        with st.expander(f"📚 View Citations & Sources ({total_sources})", expanded=False):
                            if result.sources:
                                st.markdown("#### 📄 Local Financial Booklets")
                                for i, src in enumerate(result.sources, 1):
                                    st.markdown(
                                        f"**{i}. {src.doc_title}** — "
                                        f"`Page {src.page_number}` | "
                                        f"`File: {src.doc_name}` | "
                                        f"`Sim Score: {src.similarity_score:.3f}`"
                                    )
                                    st.markdown(f"> *\"{src.text}\"*")
                                    st.write("")

                            if result.web_sources:
                                st.markdown("#### 🌐 Official Regulatory Portals (RBI / SEBI / NCFE)")
                                for j, wsrc in enumerate(result.web_sources, 1):
                                    date_str = f" | `Updated: {wsrc.date}`" if wsrc.date else ""
                                    st.markdown(
                                        f"**{j}. [{wsrc.title}]({wsrc.url})**{date_str} | "
                                        f"`Sim Score: {wsrc.similarity_score:.3f}`"
                                    )
                                    st.markdown(f"> *\"{wsrc.text}\"*")
                                    st.write("")
                    elif not result.sufficient_evidence and result.intent in (
                        IntentType.FINANCIAL_QUERY.value,
                        IntentType.FOLLOW_UP.value,
                    ):
                        st.info(
                            "ℹ️ **No matching passages found.** Neither local documents nor trusted official "
                            "online sources contain sufficient information meeting the relevance threshold for this query."
                        )

                    # Record in session state
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": result.answer,
                            "sources": serialized_pdf_sources,
                            "web_sources": serialized_web_sources,
                            "sufficient_evidence": result.sufficient_evidence,
                            "intent": result.intent,
                        }
                    )

                except Exception as exc:
                    st.error(f"❌ Error generating response: {exc}")


if __name__ == "__main__":
    main()
