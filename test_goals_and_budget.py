"""Unit and Integration Tests for Goals Management and Budget Analysis.

Tests:
1. SQLite Storage & CRUD for profile and financial goals.
2. Goal planning calculations (remaining, required monthly, progress %, shortfall).
3. Monthly budget analysis (income, expenses, active goal contributions, remaining surplus/deficit, ratios).
4. Chatbot goal and budget queries (savings need, affordability, remaining cashflow, contribution acceleration).
5. FastAPI REST endpoints for profile, dashboard, budget analysis, goals CRUD, and goal planning.
"""

from __future__ import annotations

import unittest
from fastapi.testclient import TestClient

import storage
from calc_and_profile_handler import (
    handle_goal_and_budget_chat_query,
    CalculationType,
)
from api import app


class TestStorageAndCalculations(unittest.TestCase):
    """Test SQLite operations and deterministic calculation engines."""

    def setUp(self):
        # Save a clean test profile
        storage.save_profile({
            "fullName": "Aarav Sharma",
            "email": "aarav@example.com",
            "age": 29,
            "occupation": "Software Engineer",
            "monthlyIncome": 75000.0,
            "investmentBudget": 15000.0,
            "fixedExpenses": 25000.0,
            "variableExpenses": 15000.0,
            "experience": "intermediate",
            "preferences": "equity, sip, gold",
            "goals": "wealth accumulation",
        })

        # Clear existing goals for tests
        for g in storage.list_goals():
            storage.delete_goal(g["id"])

    def test_profile_crud(self):
        prof = storage.get_profile()
        self.assertIsNotNone(prof)
        self.assertEqual(prof["fullName"], "Aarav Sharma")
        self.assertEqual(prof["monthlyIncome"], 75000.0)
        self.assertEqual(prof["fixedExpenses"], 25000.0)
        self.assertEqual(prof["variableExpenses"], 15000.0)

    def test_goal_crud_and_validation(self):
        # 1. Create valid goal
        goal = storage.create_goal({
            "name": "Gold Chain",
            "targetAmount": 120000.0,
            "currentSavings": 20000.0,
            "months": 10,
            "monthlyContribution": None,
        })
        self.assertIsNotNone(goal["id"])
        self.assertEqual(goal["name"], "Gold Chain")
        self.assertEqual(goal["targetAmount"], 120000.0)
        self.assertEqual(goal["currentSavings"], 20000.0)
        self.assertEqual(goal["months"], 10)

        # 2. Retrieve goal
        retrieved = storage.get_goal(goal["id"])
        self.assertEqual(retrieved["name"], "Gold Chain")

        # 3. Find by name
        found = storage.find_goal_by_name("gold chain")
        self.assertIsNotNone(found)
        self.assertEqual(found["id"], goal["id"])

        # 4. Update goal
        updated = storage.update_goal(goal["id"], {
            "name": "Gold Chain 22K",
            "targetAmount": 130000.0,
            "currentSavings": 30000.0,
            "months": 10,
        })
        self.assertEqual(updated["name"], "Gold Chain 22K")
        self.assertEqual(updated["targetAmount"], 130000.0)
        self.assertEqual(updated["currentSavings"], 30000.0)

        # 5. Validation failures
        with self.assertRaises(ValueError):
            storage.create_goal({"name": "", "targetAmount": 1000, "months": 5})

        with self.assertRaises(ValueError):
            storage.create_goal({"name": "Car", "targetAmount": -500, "months": 5})

        with self.assertRaises(ValueError):
            storage.create_goal({"name": "Car", "targetAmount": 500, "currentSavings": 1000, "months": 5})

        with self.assertRaises(ValueError):
            storage.create_goal({"name": "Car", "targetAmount": 500, "months": 0})

        # 6. Delete goal
        deleted = storage.delete_goal(goal["id"])
        self.assertTrue(deleted)
        self.assertIsNone(storage.get_goal(goal["id"]))

    def test_goal_plan_calculation(self):
        # Target 1,00,000, saved 20,000, 10 months -> remaining 80,000 -> 8,000/mo
        plan = storage.calculate_goal_plan({
            "name": "Laptop",
            "targetAmount": 100000.0,
            "currentSavings": 20000.0,
            "months": 10,
        })
        self.assertEqual(plan["remaining"], 80000.0)
        self.assertEqual(plan["requiredMonthly"], 8000)
        self.assertEqual(plan["progressPct"], 20.0)
        self.assertTrue(plan["isSufficient"])
        self.assertEqual(plan["projectedShortfall"], 0.0)
        self.assertEqual(len(plan["series"]), 11)
        self.assertEqual(plan["series"][0]["month"], 0)
        self.assertEqual(plan["series"][10]["projected"], 100000.0)

    def test_goal_plan_insufficient_contribution(self):
        # Target 1,00,000, saved 20,000, 10 months, user offers 5,000/mo -> accumulates 70,000 -> shortfall 30,000
        plan = storage.calculate_goal_plan({
            "name": "Laptop",
            "targetAmount": 100000.0,
            "currentSavings": 20000.0,
            "months": 10,
            "monthlyContribution": 5000.0,
        })
        self.assertEqual(plan["remaining"], 80000.0)
        self.assertEqual(plan["requiredMonthly"], 8000)
        self.assertFalse(plan["isSufficient"])
        self.assertEqual(plan["projectedShortfall"], 30000.0)
        self.assertIn("shortfall", plan["explanation"].lower())

    def test_budget_analysis_calculation(self):
        # Create an active goal: Laptop 60,000 target, 0 saved, 12 months -> 5,000/mo
        storage.create_goal({
            "name": "Laptop",
            "targetAmount": 60000.0,
            "currentSavings": 0.0,
            "months": 12,
        })

        # Income: 75,000, Fixed: 25,000, Variable: 15,000 -> Total expenses: 40,000
        # Goals: 5,000 -> Total outflows: 45,000
        # Remaining balance: 30,000
        # Expense ratio: 40,000 / 75,000 = 53.3%
        # Savings rate: 5,000 / 75,000 = 6.7%
        analysis = storage.calculate_budget_analysis()
        self.assertEqual(analysis["monthlyIncome"], 75000.0)
        self.assertEqual(analysis["totalExpenses"], 40000.0)
        self.assertEqual(analysis["totalGoalContributions"], 5000.0)
        self.assertEqual(analysis["totalOutflows"], 45000.0)
        self.assertEqual(analysis["remainingBalance"], 30000.0)
        self.assertEqual(analysis["expenseRatioPct"], 53.3)
        self.assertEqual(analysis["savingsRatePct"], 6.7)
        self.assertFalse(analysis["isDeficit"])
        self.assertEqual(analysis["goalCapacity"], 30000.0)

    def test_budget_analysis_deficit_handling(self):
        # Override with expenses exceeding income
        deficit_profile = {
            "monthlyIncome": 30000.0,
            "fixedExpenses": 25000.0,
            "variableExpenses": 15000.0,
        }
        analysis = storage.calculate_budget_analysis(profile_override=deficit_profile)
        self.assertTrue(analysis["isDeficit"])
        self.assertEqual(analysis["remainingBalance"], -10000.0)
        self.assertTrue(any("deficit" in w.lower() for w in analysis["warnings"]))


class TestChatbotGoalsAndBudgetQueries(unittest.TestCase):
    """Test deterministic chat queries for goals and budget analysis."""

    def setUp(self):
        storage.save_profile({
            "fullName": "Priya Patel",
            "monthlyIncome": 80000.0,
            "fixedExpenses": 30000.0,
            "variableExpenses": 15000.0,
            "investmentBudget": 15000.0,
        })
        for g in storage.list_goals():
            storage.delete_goal(g["id"])

        # Add Gold Chain goal: 1,20,000 target, 20,000 current, 10 months -> 10,000/mo needed
        storage.create_goal({
            "name": "Gold Chain",
            "targetAmount": 120000.0,
            "currentSavings": 20000.0,
            "months": 10,
        })

    def test_chat_savings_needed_query(self):
        res = handle_goal_and_budget_chat_query("How much do I need to save monthly for my gold chain?")
        self.assertIsNotNone(res)
        self.assertTrue(res.is_handled)
        self.assertIn("Gold Chain", res.markdown_answer)
        self.assertIn("10,000", res.markdown_answer)
        self.assertIn("10 months", res.markdown_answer)

    def test_chat_affordability_query(self):
        # Income 80,000, Expenses 45,000, Gold Chain 10,000 -> Surplus 25,000 -> Affordable!
        res = handle_goal_and_budget_chat_query("Can I afford this goal based on my current budget?")
        self.assertIsNotNone(res)
        self.assertTrue(res.is_handled)
        self.assertIn("affordable", res.markdown_answer.lower())
        self.assertIn("Gold Chain", res.markdown_answer)

    def test_chat_remaining_balance_query(self):
        res = handle_goal_and_budget_chat_query("How much money remains after my recorded expenses?")
        self.assertIsNotNone(res)
        self.assertTrue(res.is_handled)
        self.assertIn("Monthly Budget & Cash Flow Breakdown", res.markdown_answer)
        self.assertIn("80,000", res.markdown_answer)
        self.assertIn("45,000", res.markdown_answer)  # 30k + 15k
        self.assertIn("25,000", res.markdown_answer)  # 80k - 45k - 10k = 25k

    def test_chat_hypothetical_increase_query(self):
        # Current: 10,000/mo for 10 months. Increase to 20,000/mo -> 1,00,000 / 20,000 = 5 months -> 5 months sooner!
        res = handle_goal_and_budget_chat_query("What happens if I increase my contribution to ₹20,000?")
        self.assertIsNotNone(res)
        self.assertTrue(res.is_handled)
        self.assertIn("Accelerated Plan", res.markdown_answer)
        self.assertIn("5 months", res.markdown_answer)
        self.assertIn("sooner", res.markdown_answer.lower())

    def test_chat_list_goals_query(self):
        res = handle_goal_and_budget_chat_query("What are my financial goals?")
        self.assertIsNotNone(res)
        self.assertTrue(res.is_handled)
        self.assertIn("Gold Chain", res.markdown_answer)
        self.assertIn("1,20,000", res.markdown_answer)


class TestFastAPIGoalsAndBudgetEndpoints(unittest.TestCase):
    """Test FastAPI REST endpoints with TestClient."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        storage.save_profile({
            "fullName": "Neha Gupta",
            "monthlyIncome": 90000.0,
            "fixedExpenses": 35000.0,
            "variableExpenses": 15000.0,
            "investmentBudget": 20000.0,
        })
        for g in storage.list_goals():
            storage.delete_goal(g["id"])

    def test_profile_endpoints(self):
        # GET profile
        r = self.client.get("/api/profile")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["fullName"], "Neha Gupta")
        self.assertEqual(data["monthlyIncome"], 90000.0)

        # POST profile update
        r2 = self.client.post("/api/profile", json={
            "fullName": "Neha Gupta",
            "monthlyIncome": 95000.0,
            "fixedExpenses": 36000.0,
            "variableExpenses": 14000.0,
        })
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["monthlyIncome"], 95000.0)

    def test_dashboard_endpoint(self):
        r = self.client.get("/api/dashboard")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["monthlyIncome"], 90000.0)
        self.assertEqual(data["totalSpent"], 50000.0)
        self.assertIn("investmentPercentage", data)

    def test_budget_analysis_endpoint(self):
        r = self.client.get("/api/budget/analysis")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["monthlyIncome"], 90000.0)
        self.assertEqual(data["totalExpenses"], 50000.0)
        self.assertEqual(data["remainingBalance"], 40000.0)
        self.assertFalse(data["isDeficit"])

    def test_goals_crud_and_plan_endpoints(self):
        # 1. Create Goal
        r = self.client.post("/api/goals", json={
            "name": "Emergency Fund",
            "targetAmount": 300000.0,
            "currentSavings": 60000.0,
            "months": 12,
        })
        self.assertEqual(r.status_code, 200)
        goal = r.json()
        self.assertEqual(goal["name"], "Emergency Fund")
        goal_id = goal["id"]

        # 2. List Goals
        r_list = self.client.get("/api/goals")
        self.assertEqual(r_list.status_code, 200)
        self.assertEqual(len(r_list.json()), 1)

        # 3. Update Goal
        r_up = self.client.put(f"/api/goals/{goal_id}", json={
            "name": "Emergency Fund 6 Months",
            "targetAmount": 300000.0,
            "currentSavings": 80000.0,
            "months": 10,
        })
        self.assertEqual(r_up.status_code, 200)
        self.assertEqual(r_up.json()["name"], "Emergency Fund 6 Months")
        self.assertEqual(r_up.json()["currentSavings"], 80000.0)

        # 4. Generate Goal Plan
        r_plan = self.client.post("/api/goals/plan", json={
            "name": "Emergency Fund 6 Months",
            "targetAmount": 300000.0,
            "currentSavings": 80000.0,
            "months": 10,
        })
        self.assertEqual(r_plan.status_code, 200)
        plan = r_plan.json()
        self.assertEqual(plan["remaining"], 220000.0)
        self.assertEqual(plan["requiredMonthly"], 22000)
        self.assertEqual(plan["progressPct"], 26.7)
        self.assertTrue(plan["isSufficient"])

        # 5. Delete Goal
        r_del = self.client.delete(f"/api/goals/{goal_id}")
        self.assertEqual(r_del.status_code, 200)
        self.assertEqual(r_del.json()["status"], "deleted")


if __name__ == "__main__":
    unittest.main()
