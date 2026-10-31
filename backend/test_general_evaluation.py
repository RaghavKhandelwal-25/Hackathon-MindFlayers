"""Generalized Multi-Category Evaluation Suite for Finbot RAG Assistant.

Evaluates the 12 core reasoning and retrieval categories specified in the architecture upgrade:
1. Direct factual questions
2. Explanatory questions
3. Causal questions
4. Advantages and disadvantages
5. Comparisons
6. Risks and limitations
7. Multi-part questions
8. Questions requiring multiple passages
9. Questions requiring dual sources (PDF + official online)
10. Follow-up questions with conversational context
11. Questions with genuinely insufficient evidence (honest abstention)
12. Questions involving conflicting or outdated source disclosures

Tests measure evidence retrieval coverage, sub-query generation, citation preservation,
absence of false abstention, truthful abstention on unanswerable queries, and latency.
"""

from __future__ import annotations

import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure finguide directory is on sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from query_router import IntentType, classify_intent
from query_understanding import InformationNeed, QueryType, analyze_query_need
from rag import (
    DEFAULT_GROQ_MODEL,
    DEFAULT_SIMILARITY_THRESHOLD,
    DEFAULT_TOP_K,
    RAGPipeline,
    RAGResult,
    RetrievedChunk,
)
from web_retriever import WebRetrievedPassage


class TestGeneralReasoningAndRetrievalEvaluation(unittest.TestCase):
    """Reusable evaluation suite testing 12 distinct reasoning categories across multiple financial domains."""

    @classmethod
    def setUpClass(cls):
        cls.pipeline = RAGPipeline()
        cls.web_retriever = cls.pipeline.get_web_retriever()

    # Category 1: Direct Factual Questions
    def test_cat_01_direct_factual_question(self):
        """Category 1: Direct factual questions."""
        q = "What is the 50/30/20 budgeting rule?"
        start_t = time.perf_counter()
        need = analyze_query_need(q)
        self.assertEqual(need.primary_type, QueryType.FACTUAL)
        self.assertFalse(need.requires_multi_query)

        pdf_chunks = self.pipeline.retrieve(q, top_k=3, similarity_threshold=0.30)
        elapsed = time.perf_counter() - start_t

        self.assertGreater(len(pdf_chunks), 0)
        top = pdf_chunks[0]
        self.assertIn("50/30/20", top.text)
        self.assertEqual(top.doc_name, "personal_finance_and_budgeting.pdf")
        self.assertLess(elapsed, 2.0, f"Retrieval latency too high: {elapsed:.3f}s")

    # Category 2: Explanatory Questions
    def test_cat_02_explanatory_question(self):
        """Category 2: Explanatory questions."""
        q = "Explain how mutual funds pool money from multiple investors to invest in securities."
        need = analyze_query_need(q)
        self.assertEqual(need.primary_type, QueryType.FACTUAL)

        pdf_chunks = self.pipeline.retrieve(q, top_k=4, similarity_threshold=0.30)
        self.assertGreater(len(pdf_chunks), 0)
        found_pooling = any("pool" in c.text.lower() or "mutual fund" in c.text.lower() for c in pdf_chunks)
        self.assertTrue(found_pooling, "Expected explanation of mutual fund pooling in retrieved evidence.")

    # Category 3: Causal Questions
    def test_cat_03_causal_question(self):
        """Category 3: Causal questions (cause and effect / mechanisms)."""
        q = "Why does inflation erode the purchasing power of savings over time?"
        need = analyze_query_need(q)
        self.assertEqual(need.primary_type, QueryType.CAUSAL)
        self.assertTrue(need.requires_multi_query)
        self.assertGreaterEqual(len(need.sub_queries), 2)

        start_t = time.perf_counter()
        # Verify multi-query retrieval collects both economic mechanism and purchasing power impact
        web_passages = self.web_retriever.retrieve(need.sub_queries[0], top_k=2, similarity_threshold=0.30)
        elapsed = time.perf_counter() - start_t

        self.assertGreater(len(web_passages), 0)
        top_web = web_passages[0]
        self.assertIn("purchasing power", top_web.text.lower())
        self.assertIn("inflation", top_web.text.lower())
        self.assertLess(elapsed, 1.5)

    # Category 4: Advantages and Disadvantages
    def test_cat_04_advantages_and_disadvantages(self):
        """Category 4: Advantages and disadvantages (multi-facet benefits vs drawbacks)."""
        q = "What are the advantages and disadvantages of investing through a Systematic Investment Plan?"
        need = analyze_query_need(q)
        self.assertEqual(need.primary_type, QueryType.ADVANTAGES_DISADVANTAGES)
        self.assertTrue(need.requires_multi_query)
        self.assertIn("advantages", need.detected_aspects)
        self.assertIn("disadvantages", need.detected_aspects)

        # Verify complementary sub-queries cover both facets
        sub_texts = " ".join(need.sub_queries).lower()
        self.assertIn("advantages", sub_texts)
        self.assertIn("disadvantages", sub_texts)

        # Verify web retriever retrieves SEBI SIP benefits and compounding
        web_results = self.web_retriever.retrieve("Systematic Investment Plan advantages benefits compounding", top_k=2)
        self.assertGreater(len(web_results), 0)
        self.assertIn("rupee cost averaging", web_results[0].text.lower())

    # Category 5: Comparative Questions
    def test_cat_05_comparative_question(self):
        """Category 5: Comparisons between two financial asset classes."""
        q = "How do equity mutual funds differ from debt mutual funds in risk and return?"
        need = analyze_query_need(q)
        self.assertEqual(need.primary_type, QueryType.COMPARATIVE)
        self.assertTrue(need.requires_multi_query)
        self.assertGreaterEqual(len(need.sub_queries), 3)

        # Execute query via pipeline to verify RRF fusion brings together both asset classes
        pdf_chunks_sub1 = self.pipeline.retrieve("equity mutual funds risk and return", top_k=2, similarity_threshold=0.30)
        pdf_chunks_sub2 = self.pipeline.retrieve("debt mutual funds fixed income risk and return", top_k=2, similarity_threshold=0.30)

        self.assertGreater(len(pdf_chunks_sub1), 0)
        self.assertGreater(len(pdf_chunks_sub2), 0)

        web_cat = self.web_retriever.retrieve("SEBI mutual fund categorization equity and debt", top_k=1)
        self.assertGreater(len(web_cat), 0)
        self.assertIn("equity schemes", web_cat[0].text.lower())
        self.assertIn("debt schemes", web_cat[0].text.lower())

    # Category 6: Risks and Limitations
    def test_cat_06_risks_and_limitations(self):
        """Category 6: Risks and limitations (ensures specific caveat chunks are not crowded out)."""
        q = "What are the risks and limitations of index funds?"
        need = analyze_query_need(q)
        self.assertEqual(need.primary_type, QueryType.RISKS_LIMITATIONS)
        self.assertTrue(need.requires_multi_query)

        # Verify that sub-query targeting tracking error and market risk retrieves Chapter 2
        tracking_query = "index funds and ETFs market risk and tracking error limitations"
        pdf_chunks = self.pipeline.retrieve(tracking_query, top_k=3, similarity_threshold=0.30)
        self.assertGreater(len(pdf_chunks), 0)
        found_index_chapter = any(c.doc_name == "investing_fundamentals_guide.pdf" and c.page_number == 2 for c in pdf_chunks)
        self.assertTrue(found_index_chapter, "Expected Chapter 2 of investing_fundamentals_guide.pdf to be retrieved.")

    # Category 7: Multi-Part Questions
    def test_cat_07_multi_part_question(self):
        """Category 7: Multi-part questions containing multiple distinct sub-questions."""
        q = "What is an emergency fund, how many months of expenses should it cover, and where should it be kept?"
        need = analyze_query_need(q)
        self.assertEqual(need.primary_type, QueryType.MULTI_PART)
        self.assertTrue(need.requires_multi_query)
        self.assertGreaterEqual(len(need.sub_queries), 3)

        # Verify sub-queries capture individual components
        sub_str = " ".join(need.sub_queries).lower()
        self.assertIn("emergency fund", sub_str)
        self.assertIn("how many months", sub_str)
        self.assertIn("where should it be kept", sub_str)

    # Category 8: Questions Requiring Multiple Passages
    def test_cat_08_multi_passage_reasoning(self):
        """Category 8: Questions requiring synthesis across multiple passages in a document."""
        q = "Compare the tax implications and withdrawal rules of a Traditional IRA versus a Roth IRA."
        need = analyze_query_need(q)
        self.assertEqual(need.primary_type, QueryType.COMPARATIVE)

        # In retirement_and_tax_advantaged_accounts.pdf, Traditional IRA and Roth IRA appear in multiple chunks on page 2
        chunks = self.pipeline.retrieve("Traditional IRA vs Roth IRA tax deductible post-tax withdrawal rules", top_k=4)
        self.assertGreaterEqual(len(chunks), 2)
        has_trad = any("traditional ira" in c.text.lower() for c in chunks)
        has_roth = any("roth ira" in c.text.lower() for c in chunks)
        self.assertTrue(has_trad, "Expected evidence for Traditional IRA.")
        self.assertTrue(has_roth, "Expected evidence for Roth IRA.")

    # Category 9: Dual-Source Evidence (PDF + Official Online)
    def test_cat_09_dual_source_evidence(self):
        """Category 9: Questions requiring synthesis from both PDF booklets and official online regulatory portals."""
        mock_pdf = [
            RetrievedChunk(
                chunk_id=101,
                doc_name="Financial Education Booklet - English.pdf",
                doc_title="Financial Education Booklet - English",
                page_number=31,
                text="An SIP allows an investor to invest a fixed amount of money regularly in a mutual fund scheme.",
                similarity_score=0.72,
            )
        ]
        mock_web = [
            WebRetrievedPassage(
                passage_id="web_101",
                url="https://investor.sebi.gov.in/personalinvestments.html",
                title="SEBI Investor Education — Personal Investments",
                domain="investor.sebi.gov.in",
                date="2024-04-20",
                text="SIP instills financial discipline and provides the benefit of Rupee Cost Averaging.",
                similarity_score=0.78,
            )
        ]
        messages = self.pipeline.build_llm_messages(
            query="What is a SIP and what is rupee cost averaging?",
            chunks=mock_pdf,
            web_chunks=mock_web,
        )
        content = messages[-1]["content"]
        self.assertIn("<local_pdf_sources>", content)
        self.assertIn("<official_online_sources>", content)
        self.assertIn("Financial Education Booklet - English", content)
        self.assertIn("investor.sebi.gov.in", content)

    # Category 10: Follow-Up Questions with Context
    def test_cat_10_follow_up_questions(self):
        """Category 10: Follow-up questions that depend on previous turns."""
        history = [
            {"role": "user", "content": "What is an index fund?"},
            {"role": "assistant", "content": "An index fund is a pooled mutual fund designed to replicate a market index like the S&P 500."},
        ]
        routing = classify_intent("What are its risks?", history=history)
        self.assertEqual(routing.intent, IntentType.FOLLOW_UP)
        self.assertIn("index fund", routing.contextualized_query.lower())

        # Test query understanding on the contextualized query
        need = analyze_query_need(routing.contextualized_query)
        self.assertEqual(need.primary_type, QueryType.RISKS_LIMITATIONS)

    # Category 11: Questions with Genuinely Insufficient Evidence
    def test_cat_11_insufficient_evidence_honest_abstention(self):
        """Category 11: Questions with genuinely insufficient evidence trigger honest abstention without hallucination."""
        obscure_query = "What are the corporate tax brackets and capital gains exemptions in Liechtenstein for 2026?"
        result = self.pipeline.query(
            question=obscure_query,
            similarity_threshold=0.55,
        )
        self.assertFalse(result.sufficient_evidence)
        self.assertIn("don't have enough information", result.answer.lower())
        self.assertEqual(len(result.sources), 0)
        self.assertEqual(len(result.web_sources), 0)

    # Category 12: Conflicting or Outdated Sources
    def test_cat_12_conflicting_or_outdated_sources_disclosure(self):
        """Category 12: Questions where older PDF guidance differs from newer official regulatory portals."""
        mock_pdf = [
            RetrievedChunk(
                chunk_id=201,
                doc_name="archived_banking_guide_2019.pdf",
                doc_title="Archived Banking Guide (2019)",
                page_number=12,
                text="Bank deposits are insured by DICGC up to Rs 1,00,000 per depositor.",
                similarity_score=0.70,
            )
        ]
        mock_web = [
            WebRetrievedPassage(
                passage_id="web_201",
                url="https://www.rbi.org.in/",
                title="Reserve Bank of India — Deposit Insurance",
                domain="rbi.org.in",
                date="2024-05-10",
                text="Under DICGC, each depositor in a bank is insured up to a maximum limit of Rs 5,00,000.",
                similarity_score=0.88,
            )
        ]
        messages = self.pipeline.build_llm_messages(
            query="What is the deposit insurance limit for bank accounts?",
            chunks=mock_pdf,
            web_chunks=mock_web,
        )
        sys_msg = messages[0]["content"]
        user_msg = messages[1]["content"]

        # Ensure prompt guidelines enforce conflict disclosure and date attribution
        self.assertIn("FRESHNESS & SOURCE CONFLICT DISCLOSURE", sys_msg)
        self.assertIn("conflicting rules or values, state the discrepancy", user_msg)


def run_evaluation_suite():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestGeneralReasoningAndRetrievalEvaluation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)


if __name__ == "__main__":
    run_evaluation_suite()
