"""Unit and Integration Tests for Deterministic Financial Calculators, Profile Context, and Query Routing.

Covers:
1. Financial calculation functions (Budget, Compound Interest, SIP, Inflation).
2. Boundary cases, zero rates/costs, and input validation errors.
3. Currency formatting in the Indian numbering system.
4. Profile-aware question answering (Income, Budget, Expenses, Goals).
5. Percentage calculations derived from profile values.
6. Missing and invalid profile fields.
7. Query routing across greetings, profile queries, calculations, and hybrid RAG questions.
8. FastAPI /api/chat endpoint with profile context.
"""

from __future__ import annotations

import os as _os, tempfile as _tf
_os.environ.setdefault("FINGUIDE_DB_PATH", _os.path.join(_tf.mkdtemp(), "test_finguide.db"))  # never touch the real database

import math
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient

from api import app
from calc_and_profile_handler import (
    CalculationType,
    handle_calculation_query,
    handle_percentage_query,
    handle_profile_question,
    parse_indian_number,
)
from finance_calculators import (
    calculate_budget,
    calculate_compound_interest,
    calculate_inflation,
    calculate_sip,
    format_inr,
)
from rag import RAGPipeline


class TestDeterministicCalculators(unittest.TestCase):
    """Test mathematical accuracy, accounting conventions, and input validation of calculators."""

    def test_inr_formatting(self):
        self.assertEqual(format_inr(0), "₹0")
        self.assertEqual(format_inr(500), "₹500")
        self.assertEqual(format_inr(5000), "₹5,000")
        self.assertEqual(format_inr(50000), "₹50,000")
        self.assertEqual(format_inr(100000), "₹1,00,000")
        self.assertEqual(format_inr(1000000), "₹10,00,000")
        self.assertEqual(format_inr(10000000), "₹1,00,00,000")
        self.assertEqual(format_inr(-5000), "-₹5,000")

    def test_indian_number_parsing(self):
        self.assertEqual(parse_indian_number("5000"), 5000.0)
        self.assertEqual(parse_indian_number("5k"), 5000.0)
        self.assertEqual(parse_indian_number("1 lakh"), 100000.0)
        self.assertEqual(parse_indian_number("2.5 lac"), 250000.0)
        self.assertEqual(parse_indian_number("1 crore"), 10000000.0)
        self.assertEqual(parse_indian_number("₹10,00,000"), 1000000.0)

    def test_budget_calculation_standard(self):
        res = calculate_budget(
            monthly_income=50000.0,
            fixed_expenses=20000.0,
            variable_expenses=10000.0,
            monthly_investment_or_savings=10000.0,
        )
        self.assertEqual(res["total_expenses"], 30000.0)
        self.assertEqual(res["total_outflows"], 40000.0)
        self.assertEqual(res["remaining_balance"], 10000.0)
        self.assertEqual(res["savings_rate_pct"], 20.0)
        self.assertEqual(res["expense_ratio_pct"], 60.0)
        self.assertEqual(res["remaining_ratio_pct"], 20.0)

        # 50/30/20 benchmarks
        bench = res["rule_50_30_20_benchmark"]
        self.assertEqual(bench["needs_target_50"], 25000.0)
        self.assertEqual(bench["wants_target_30"], 15000.0)
        self.assertEqual(bench["savings_target_20"], 10000.0)

    def test_budget_calculation_zero_income(self):
        res = calculate_budget(
            monthly_income=0.0,
            fixed_expenses=5000.0,
            variable_expenses=2000.0,
        )
        self.assertEqual(res["total_outflows"], 7000.0)
        self.assertEqual(res["remaining_balance"], -7000.0)
        self.assertEqual(res["savings_rate_pct"], 0.0)

    def test_budget_calculation_invalid_inputs(self):
        with self.assertRaises(ValueError):
            calculate_budget(monthly_income=-100.0)
        with self.assertRaises(ValueError):
            calculate_budget(monthly_income=5000.0, fixed_expenses=-50.0)

    def test_compound_interest_known_values(self):
        # P = 100,000, r = 8%, t = 5 years, annual compounding
        # A = 100,000 * (1.08)^5 = 146,932.81
        res = calculate_compound_interest(
            principal=100000.0,
            annual_rate_pct=8.0,
            duration_years=5.0,
            compounding_frequency=1,
        )
        self.assertAlmostEqual(res["future_value"], 146932.81, places=1)
        self.assertAlmostEqual(res["interest_earned"], 46932.81, places=1)
        self.assertEqual(res["frequency_label"], "Annually")

    def test_compound_interest_quarterly(self):
        # Quarterly compounding
        res = calculate_compound_interest(
            principal=50000.0,
            annual_rate_pct=10.0,
            duration_years=3.0,
            compounding_frequency=4,
        )
        expected_fv = 50000.0 * ((1 + 0.10 / 4) ** (4 * 3))
        self.assertAlmostEqual(res["future_value"], round(expected_fv, 2), places=1)

    def test_compound_interest_zero_rate(self):
        res = calculate_compound_interest(
            principal=25000.0,
            annual_rate_pct=0.0,
            duration_years=5.0,
        )
        self.assertEqual(res["future_value"], 25000.0)
        self.assertEqual(res["interest_earned"], 0.0)

    def test_compound_interest_invalid_inputs(self):
        with self.assertRaises(ValueError):
            calculate_compound_interest(principal=-1000.0, annual_rate_pct=5.0, duration_years=2.0)
        with self.assertRaises(ValueError):
            calculate_compound_interest(principal=1000.0, annual_rate_pct=-5.0, duration_years=2.0)
        with self.assertRaises(ValueError):
            calculate_compound_interest(principal=1000.0, annual_rate_pct=5.0, duration_years=0.0)
        with self.assertRaises(ValueError):
            calculate_compound_interest(principal=1000.0, annual_rate_pct=5.0, duration_years=2.0, compounding_frequency=3)

    def test_sip_projection_known_values(self):
        # Monthly 5000 for 10 years at 12%
        res = calculate_sip(
            monthly_contribution=5000.0,
            annual_return_pct=12.0,
            duration_years=10.0,
        )
        self.assertEqual(res["total_contributions"], 600000.0)
        self.assertEqual(res["duration_months"], 120)
        # Annuity due FV: 5000 * ((1.01^120 - 1)/0.01) * 1.01 = ~1,161,695.38
        self.assertTrue(1160000 <= res["estimated_future_value"] <= 1165000)
        self.assertAlmostEqual(res["estimated_gain"], res["estimated_future_value"] - 600000.0, places=2)

    def test_sip_projection_zero_return(self):
        res = calculate_sip(
            monthly_contribution=2000.0,
            annual_return_pct=0.0,
            duration_months=24,
        )
        self.assertEqual(res["total_contributions"], 48000.0)
        self.assertEqual(res["estimated_future_value"], 48000.0)
        self.assertEqual(res["estimated_gain"], 0.0)

    def test_sip_projection_invalid_inputs(self):
        with self.assertRaises(ValueError):
            calculate_sip(monthly_contribution=0.0, annual_return_pct=10.0, duration_years=5.0)
        with self.assertRaises(ValueError):
            calculate_sip(monthly_contribution=1000.0, annual_return_pct=-2.0, duration_years=5.0)
        with self.assertRaises(ValueError):
            calculate_sip(monthly_contribution=1000.0, annual_return_pct=10.0)

    def test_inflation_projection_known_values(self):
        # 10 lakh cost today, 6% inflation, 15 years
        # FV = 1,000,000 * (1.06)^15 = 2,396,558.19
        res = calculate_inflation(
            current_cost=1000000.0,
            annual_inflation_rate_pct=6.0,
            duration_years=15.0,
        )
        self.assertAlmostEqual(res["estimated_future_cost"], 2396558.19, places=1)
        self.assertAlmostEqual(res["cost_difference"], 1396558.19, places=1)
        self.assertTrue(50.0 <= res["purchasing_power_loss_pct"] <= 65.0)

    def test_inflation_projection_zero_inflation(self):
        res = calculate_inflation(
            current_cost=50000.0,
            annual_inflation_rate_pct=0.0,
            duration_years=10.0,
        )
        self.assertEqual(res["estimated_future_cost"], 50000.0)
        self.assertEqual(res["cost_difference"], 0.0)
        self.assertEqual(res["purchasing_power_loss_pct"], 0.0)


class TestProfileContextAndPercentage(unittest.TestCase):
    """Test user profile questions, missing data handling, and percentage queries."""

    def test_profile_income_question(self):
        profile = {"monthlyIncome": 50000, "investmentBudget": 10000}
        res = handle_profile_question("What is my monthly income?", profile=profile)
        self.assertIsNotNone(res)
        self.assertTrue(res.is_handled)
        self.assertIn("₹50,000", res.markdown_answer)
        self.assertIn("Monthly Income", res.markdown_answer)

    def test_profile_missing_profile(self):
        res = handle_profile_question("What is my monthly income?", profile=None)
        self.assertIsNotNone(res)
        self.assertTrue(res.is_handled)
        self.assertIn("No Financial Profile Recorded Yet", res.markdown_answer)

    def test_profile_missing_specific_field(self):
        profile = {"fullName": "Rahul"}
        res = handle_profile_question("What is my monthly income?", profile=profile)
        self.assertIsNotNone(res)
        self.assertTrue(res.is_handled)
        self.assertIn("Monthly Income Not Recorded", res.markdown_answer)

    def test_percentage_of_income(self):
        profile = {"monthlyIncome": 60000}
        res = handle_percentage_query("What is 10% of my income?", profile=profile)
        self.assertIsNotNone(res)
        self.assertTrue(res.is_handled)
        self.assertIn("₹6,000", res.markdown_answer)
        self.assertEqual(res.raw_data["result"], 6000.0)

    def test_percentage_of_budget(self):
        profile = {"investmentBudget": 15000}
        res = handle_percentage_query("How much is 20 percent of my budget?", profile=profile)
        self.assertIsNotNone(res)
        self.assertTrue(res.is_handled)
        self.assertIn("₹3,000", res.markdown_answer)

    def test_percentage_without_profile(self):
        res = handle_percentage_query("What is 10% of my income?", profile=None)
        self.assertIsNotNone(res)
        self.assertTrue(res.is_handled)
        self.assertIn("need your recorded profile data", res.markdown_answer)


class TestQueryRoutingAndCalculators(unittest.TestCase):
    """Test query routing across greeting, profile, calculations, and hybrid queries."""

    def setUp(self):
        self.pipeline = RAGPipeline()

    def test_greeting_routing(self):
        res = self.pipeline.query("Hello! Good morning.")
        self.assertIn("Hello! Welcome to FinGuide", res.answer)
        self.assertFalse(res.sources)

    def test_profile_query_routing(self):
        profile = {"monthlyIncome": 80000, "investmentBudget": 20000}
        res = self.pipeline.query("What is my monthly income?", profile=profile)
        self.assertIn("₹80,000", res.answer)
        self.assertEqual(res.intent, "profile_inquiry")
        self.assertEqual(res.model_used, "deterministic_profile")
        self.assertFalse(res.sources, "Profile query should not retrieve PDF chunks")

    def test_pure_sip_calculation_routing(self):
        query = "If I invest ₹5,000 monthly in an SIP for 10 years at 12%, how much will it become?"
        res = self.pipeline.query(query)
        self.assertIn("Systematic Investment Plan (SIP) Projection", res.answer)
        self.assertIn("₹5,000", res.answer)
        self.assertIn("10.0 years", res.answer)
        self.assertEqual(res.intent, "calculation")
        self.assertEqual(res.model_used, "deterministic_calculator")

    def test_pure_compound_interest_calculation_routing(self):
        query = "Calculate compound interest on ₹1,00,000 at 8% for 5 years compounded annually."
        res = self.pipeline.query(query)
        self.assertIn("Compound Interest Calculation", res.answer)
        self.assertIn("₹1,00,000", res.answer)
        self.assertIn("₹1,46,932.81", res.answer)
        self.assertEqual(res.intent, "calculation")

    def test_inflation_calculation_routing(self):
        query = "What will 10 lakh cost after 15 years with 6% inflation?"
        res = self.pipeline.query(query)
        self.assertIn("Inflation & Future Cost Projection", res.answer)
        self.assertIn("₹10,00,000", res.answer)
        self.assertIn("₹23,96,558.19", res.answer)

    def test_missing_input_calculation_follow_up(self):
        # User asks for SIP without duration or amount
        res = handle_calculation_query("Calculate my SIP returns", profile=None)
        self.assertIsNotNone(res)
        self.assertTrue(res.is_handled)
        self.assertIn("please specify the missing information", res.markdown_answer)


class TestFastAPIChatIntegrationWithProfile(unittest.TestCase):
    """Test the FastAPI backend /api/chat endpoint with profile context and calculations."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_chat_with_profile_income(self):
        payload = {
            "message": "What is my monthly income?",
            "profile": {
                "monthlyIncome": 75000,
                "investmentBudget": 15000,
            },
        }
        res = self.client.post("/api/chat", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("₹75,000", data["reply"])
        self.assertEqual(data["query_type"], "personal_data")
        self.assertEqual(len(data["sources"]), 0)

    def test_chat_with_percentage_of_income(self):
        payload = {
            "message": "What is 10% of my income?",
            "profile": {
                "monthlyIncome": 75000,
            },
        }
        res = self.client.post("/api/chat", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("₹7,500", data["reply"])
        self.assertEqual(data["query_type"], "percentage_calculation")

    def test_chat_with_sip_calculation(self):
        payload = {
            "message": "If I invest 5000 every month in an SIP for 10 years at 12%, how much will it become?",
        }
        res = self.client.post("/api/chat", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("Systematic Investment Plan", data["reply"])
        self.assertIn("₹5,000", data["reply"])
        self.assertTrue(data["sufficient_evidence"])


if __name__ == "__main__":
    unittest.main()
