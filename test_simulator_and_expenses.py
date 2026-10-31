"""Tests for the SIP what-if simulator and expense tracking endpoints (uses a temporary database)."""
import os
import tempfile
import unittest

os.environ["FINGUIDE_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_finguide.db")

from fastapi.testclient import TestClient  # noqa: E402

import storage  # noqa: E402
from api import app  # noqa: E402


class TestSimulatorAndExpenses(unittest.TestCase):
    def setUp(self):
        self.c = TestClient(app)
        for e in storage.list_expenses():
            storage.delete_expense(e["id"])

    def test_sip_simulator(self):
        r = self.c.post("/api/simulator/sip", json={"monthlyContribution": 5000, "annualReturn": 12, "years": 10, "targetAmount": 1000000})
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d["summary"]["total_contributions"], 600000.0)
        self.assertAlmostEqual(d["series"][-1]["value"], d["summary"]["estimated_future_value"], delta=1)
        self.assertEqual(len(d["scenarios"]), 3)
        self.assertTrue(d["goalCheck"]["reachesTarget"])
        self.assertIn("disclaimer", d)

    def test_sip_alias_and_validation(self):
        ok = self.c.post("/api/simulator/sip", json={"monthlyAmount": 1000, "annualReturnPct": 0, "months": 12})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()["summary"]["estimated_future_value"], 12000.0)
        self.assertEqual(self.c.post("/api/simulator/sip", json={"monthlyContribution": 1000, "annualReturn": 8}).status_code, 400)
        self.assertEqual(self.c.post("/api/simulator/sip", json={"monthlyContribution": -5, "annualReturn": 8, "years": 1}).status_code, 422)

    def test_expenses_flow(self):
        storage.save_profile({"fullName": "T", "monthlyIncome": 50000, "variableExpenses": 10000})
        e1 = self.c.post("/api/expenses", json={"amount": 250, "category": "Food", "date": "2026-10-05"}).json()
        self.c.post("/api/expenses", json={"amount": 750, "category": "Travel", "date": "2026-10-09"})
        self.c.post("/api/expenses", json={"amount": 100, "category": "Food", "date": "2026-09-30"})
        self.assertEqual(len(self.c.get("/api/expenses?month=2026-10").json()), 2)
        s = self.c.get("/api/expenses/summary?month=2026-10").json()
        self.assertEqual(s["totalSpent"], 1000.0)
        self.assertEqual(s["byCategory"][0]["category"], "Travel")
        self.assertEqual(s["remainingVariableBudget"], 9000.0)
        self.assertEqual(self.c.delete(f"/api/expenses/{e1['id']}").status_code, 200)
        self.assertEqual(self.c.delete(f"/api/expenses/{e1['id']}").status_code, 404)

    def test_expense_validation(self):
        self.assertEqual(self.c.post("/api/expenses", json={"amount": 0}).status_code, 422)
        self.assertEqual(self.c.post("/api/expenses", json={"amount": 10, "date": "05-10-2026"}).status_code, 400)


if __name__ == "__main__":
    unittest.main()


class TestChatExpenseQueries(unittest.TestCase):
    """The chatbot should answer from expenses logged on the Expenses page."""

    @classmethod
    def setUpClass(cls):
        from datetime import date, timedelta
        cls.c = TestClient(app)
        for e in storage.list_expenses():
            storage.delete_expense(e["id"])
        storage.save_profile({"fullName": "T", "monthlyIncome": 50000, "variableExpenses": 10000})
        today = date.today()
        last_month = today.replace(day=1) - timedelta(days=1)
        for amt, cat, d, note in [(300, "Food", today, "lunch"), (200, "Food", today, ""), (900, "Transport", today, "cab"),
                                  (500, "Food", last_month, "old")]:
            storage.create_expense({"amount": amt, "category": cat, "date": d.isoformat(), "note": note})

    def ask(self, text):
        return self.c.post("/api/chat", json={"message": text}).json()

    def test_total_this_month(self):
        r = self.ask("How much have I spent this month?")
        self.assertEqual(r["model_used"], "deterministic_tracker")
        self.assertIn("1,400", r["reply"])
        self.assertIn("Transport", r["reply"])

    def test_category(self):
        r = self.ask("How much did I spend on food this month?")
        self.assertIn("500", r["reply"])
        self.assertNotIn("1,400", r["reply"])

    def test_last_month(self):
        r = self.ask("how much did I spend last month")
        self.assertIn("500", r["reply"])

    def test_recent_list(self):
        r = self.ask("show my recent expenses")
        self.assertEqual(r["model_used"], "deterministic_tracker")
        self.assertIn("cab", r["reply"])

    def test_not_triggered_for_advice_or_profile(self):
        for q in ["Should I spend more on mutual funds?", "What are my fixed expenses?", "What is an expense ratio?"]:
            self.assertNotEqual(self.ask(q).get("model_used"), "deterministic_tracker", q)
