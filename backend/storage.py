"""SQLite Persistence Layer for Finbot.

Provides local, persistent, thread-safe SQLite storage for:
1. User Profile (Income, Expenses, Budget, Experience, Goals)
2. Financial Goals (Target Amount, Current Savings, Months, Monthly Contribution)

All calculations and mutations are executed locally with full data consistency.
"""

from __future__ import annotations

import json
import logging
import math
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("finguide.storage")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = Path(os.getenv("FINGUIDE_DB_PATH") or (DATA_DIR / "finguide.db"))


def get_db_connection() -> sqlite3.Connection:
    """Return a thread-safe connection to the SQLite database."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables for user profile and financial goals."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profile (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    full_name TEXT,
                    email TEXT,
                    age REAL,
                    occupation TEXT,
                    monthly_income REAL,
                    investment_budget REAL,
                    fixed_expenses REAL,
                    variable_expenses REAL,
                    experience TEXT,
                    preferences TEXT,
                    goals TEXT,
                    updated_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS financial_goals (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    target_amount REAL NOT NULL,
                    current_savings REAL NOT NULL DEFAULT 0.0,
                    months INTEGER NOT NULL,
                    monthly_contribution REAL,
                    description TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS expenses (
                    id TEXT PRIMARY KEY,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    note TEXT,
                    spent_on TEXT NOT NULL,
                    created_at TEXT
                )
                """
            )
        logger.info(f"Initialized SQLite database at '{DB_PATH}'")
    finally:
        conn.close()


# Ensure tables are ready on module import
init_db()


# ==============================================================================
# PROFILE STORAGE
# ==============================================================================


def get_profile() -> Optional[Dict[str, Any]]:
    """Retrieve the single recorded user profile from the database."""
    conn = get_db_connection()
    try:
        row = conn.execute(
            """
            SELECT full_name, email, age, occupation, monthly_income,
                   investment_budget, fixed_expenses, variable_expenses,
                   experience, preferences, goals, updated_at
            FROM user_profile WHERE id = 1
            """
        ).fetchone()

        if not row:
            return None

        return {
            "fullName": row["full_name"] or "",
            "email": row["email"] or "",
            "age": row["age"],
            "occupation": row["occupation"] or "",
            "monthlyIncome": row["monthly_income"],
            "investmentBudget": row["investment_budget"],
            "fixedExpenses": row["fixed_expenses"],
            "variableExpenses": row["variable_expenses"],
            "experience": row["experience"] or "",
            "preferences": row["preferences"] or "",
            "goals": row["goals"] or "",
            "updatedAt": row["updated_at"],
        }
    finally:
        conn.close()


def save_profile(data: Dict[str, Any]) -> Dict[str, Any]:
    """Upsert the user profile in the database."""
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = get_db_connection()
    try:
        def to_num(val):
            if val is None or str(val).strip() == "":
                return None
            try:
                return float(val)
            except (ValueError, TypeError):
                return None

        full_name = str(data.get("fullName", "")).strip()
        email = str(data.get("email", "")).strip()
        age = to_num(data.get("age"))
        occupation = str(data.get("occupation", "")).strip()
        monthly_income = to_num(data.get("monthlyIncome"))
        investment_budget = to_num(data.get("investmentBudget"))
        fixed_expenses = to_num(data.get("fixedExpenses"))
        variable_expenses = to_num(data.get("variableExpenses"))
        experience = str(data.get("experience", "")).strip()
        preferences = str(data.get("preferences", "")).strip()
        goals = str(data.get("goals", "")).strip()

        with conn:
            conn.execute(
                """
                INSERT INTO user_profile (
                    id, full_name, email, age, occupation, monthly_income,
                    investment_budget, fixed_expenses, variable_expenses,
                    experience, preferences, goals, updated_at
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    full_name = excluded.full_name,
                    email = excluded.email,
                    age = excluded.age,
                    occupation = excluded.occupation,
                    monthly_income = excluded.monthly_income,
                    investment_budget = excluded.investment_budget,
                    fixed_expenses = excluded.fixed_expenses,
                    variable_expenses = excluded.variable_expenses,
                    experience = excluded.experience,
                    preferences = excluded.preferences,
                    goals = excluded.goals,
                    updated_at = excluded.updated_at
                """,
                (
                    full_name,
                    email,
                    age,
                    occupation,
                    monthly_income,
                    investment_budget,
                    fixed_expenses,
                    variable_expenses,
                    experience,
                    preferences,
                    goals,
                    now_iso,
                ),
            )
        return get_profile() or data
    finally:
        conn.close()


# ==============================================================================
# FINANCIAL GOALS STORAGE
# ==============================================================================


def list_goals() -> List[Dict[str, Any]]:
    """Return all financial goals sorted by creation time."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, name, target_amount, current_savings, months,
                   monthly_contribution, description, created_at, updated_at
            FROM financial_goals
            ORDER BY created_at ASC
            """
        ).fetchall()

        results = []
        for r in rows:
            results.append(
                {
                    "id": r["id"],
                    "name": r["name"],
                    "targetAmount": r["target_amount"],
                    "currentSavings": r["current_savings"],
                    "months": r["months"],
                    "monthlyContribution": r["monthly_contribution"],
                    "description": r["description"] or "",
                    "createdAt": r["created_at"],
                    "updatedAt": r["updated_at"],
                }
            )
        return results
    finally:
        conn.close()


def get_goal(goal_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single goal by its unique ID."""
    conn = get_db_connection()
    try:
        row = conn.execute(
            """
            SELECT id, name, target_amount, current_savings, months,
                   monthly_contribution, description, created_at, updated_at
            FROM financial_goals
            WHERE id = ?
            """,
            (goal_id,),
        ).fetchone()

        if not row:
            return None

        return {
            "id": row["id"],
            "name": row["name"],
            "targetAmount": row["target_amount"],
            "currentSavings": row["current_savings"],
            "months": row["months"],
            "monthlyContribution": row["monthly_contribution"],
            "description": row["description"] or "",
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }
    finally:
        conn.close()


def find_goal_by_name(query_name: str) -> Optional[Dict[str, Any]]:
    """Find a saved goal by fuzzy or exact name match."""
    goals = list_goals()
    if not goals:
        return None

    clean_q = query_name.lower().strip()
    # 1. Exact match
    for g in goals:
        if g["name"].lower().strip() == clean_q:
            return g

    # 2. Substring match
    for g in goals:
        g_name = g["name"].lower().strip()
        if g_name in clean_q or clean_q in g_name:
            return g

    # 3. Word intersection match
    q_words = set(clean_q.split())
    for g in goals:
        g_words = set(g["name"].lower().split())
        if q_words.intersection(g_words):
            return g

    return None


def create_goal(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create and persist a new financial goal."""
    name = str(data.get("name", "")).strip()
    if not name:
        raise ValueError("Goal name cannot be empty.")

    try:
        target_amount = float(data["targetAmount"])
        if target_amount <= 0:
            raise ValueError("Target amount must be greater than zero.")
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError(f"Invalid target amount: {exc}")

    try:
        current_savings = float(data.get("currentSavings", 0.0) or 0.0)
        if current_savings < 0:
            raise ValueError("Current savings cannot be negative.")
        if current_savings > target_amount:
            raise ValueError("Current savings cannot exceed the target amount.")
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid current savings: {exc}")

    try:
        months = int(data["months"])
        if months <= 0:
            raise ValueError("Duration in months must be at least 1.")
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError(f"Invalid duration in months: {exc}")

    monthly_contribution = data.get("monthlyContribution")
    if monthly_contribution is not None and str(monthly_contribution).strip() != "":
        try:
            monthly_contribution = float(monthly_contribution)
            if monthly_contribution < 0:
                raise ValueError("Monthly contribution cannot be negative.")
        except (ValueError, TypeError):
            monthly_contribution = None
    else:
        monthly_contribution = None

    goal_id = str(data.get("id") or f"goal_{int(time.time() * 1000)}")
    description = str(data.get("description", "")).strip()
    now_iso = datetime.now(timezone.utc).isoformat()

    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO financial_goals (
                    id, name, target_amount, current_savings, months,
                    monthly_contribution, description, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    goal_id,
                    name,
                    target_amount,
                    current_savings,
                    months,
                    monthly_contribution,
                    description,
                    now_iso,
                    now_iso,
                ),
            )
        return get_goal(goal_id) or {}
    finally:
        conn.close()


def update_goal(goal_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update an existing financial goal."""
    existing = get_goal(goal_id)
    if not existing:
        return None

    name = str(data.get("name", existing["name"])).strip()
    if not name:
        raise ValueError("Goal name cannot be empty.")

    target_amount = float(data.get("targetAmount", existing["targetAmount"]))
    if target_amount <= 0:
        raise ValueError("Target amount must be greater than zero.")

    current_savings = float(data.get("currentSavings", existing["currentSavings"]))
    if current_savings < 0:
        raise ValueError("Current savings cannot be negative.")
    if current_savings > target_amount:
        raise ValueError("Current savings cannot exceed the target amount.")

    months = int(data.get("months", existing["months"]))
    if months <= 0:
        raise ValueError("Duration in months must be at least 1.")

    monthly_contribution = data.get("monthlyContribution")
    if monthly_contribution is not None and str(monthly_contribution).strip() != "":
        monthly_contribution = float(monthly_contribution)
        if monthly_contribution < 0:
            raise ValueError("Monthly contribution cannot be negative.")
    else:
        monthly_contribution = None

    description = str(data.get("description", existing.get("description", ""))).strip()
    now_iso = datetime.now(timezone.utc).isoformat()

    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                UPDATE financial_goals
                SET name = ?, target_amount = ?, current_savings = ?, months = ?,
                    monthly_contribution = ?, description = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    name,
                    target_amount,
                    current_savings,
                    months,
                    monthly_contribution,
                    description,
                    now_iso,
                    goal_id,
                ),
            )
        return get_goal(goal_id)
    finally:
        conn.close()


def delete_goal(goal_id: str) -> bool:
    """Delete a financial goal by ID."""
    conn = get_db_connection()
    try:
        with conn:
            cur = conn.execute("DELETE FROM financial_goals WHERE id = ?", (goal_id,))
            return cur.rowcount > 0
    finally:
        conn.close()


# ==============================================================================
# CALCULATION ENGINES FOR GOAL PLAN AND BUDGET ANALYSIS
# ==============================================================================


def calculate_goal_plan(data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate deterministic savings projection plan for a financial goal.

    Formulas:
    - remaining = max(targetAmount - currentSavings, 0)
    - requiredMonthly = math.ceil(remaining / months)
    - progressPct = (currentSavings / targetAmount) * 100
    - isSufficient = (monthlyContribution * months) >= remaining
    """
    target = float(data.get("targetAmount", 0.0))
    current = float(data.get("currentSavings", 0.0) or 0.0)
    months = int(data.get("months", 1) or 1)
    if months <= 0:
        months = 1

    remaining = max(target - current, 0.0)
    required_monthly = math.ceil(remaining / months) if months > 0 else 0

    user_contrib = data.get("monthlyContribution")
    if user_contrib is not None and str(user_contrib).strip() != "":
        contrib_per_month = float(user_contrib)
    else:
        contrib_per_month = required_monthly

    is_achieved = current >= target
    is_sufficient = (contrib_per_month * months) >= remaining
    projected_shortfall = max(remaining - (contrib_per_month * months), 0.0)
    progress_pct = min(round((current / target) * 100, 1), 100.0) if target > 0 else 100.0

    # Build projection series
    series = []
    accumulated = current
    for m in range(months + 1):
        if m == 0:
            series.append({
                "month": m,
                "actual": round(current, 2),
                "projected": round(current, 2),
            })
        else:
            accumulated = min(accumulated + contrib_per_month, target)
            series.append({
                "month": m,
                "projected": round(accumulated, 2),
            })

    # Human-readable explanation
    if is_achieved:
        explanation = f"Congratulations! You have already achieved 100% of your target for {data.get('name', 'this goal')}."
    elif is_sufficient:
        explanation = (
            f"To reach your remaining goal of ₹{int(round(remaining)):,} in {months} months, "
            f"saving ₹{int(round(contrib_per_month)):,} per month will fully meet your target."
        )
    else:
        explanation = (
            f"At ₹{int(round(contrib_per_month)):,}/month for {months} months, you will accumulate "
            f"₹{int(round(current + contrib_per_month * months)):,}, leaving a projected shortfall of "
            f"₹{int(round(projected_shortfall)):,}. To meet your target on time, you need ₹{int(round(required_monthly)):,}/month."
        )

    return {
        "goal": {
            "name": data.get("name", "Financial Goal"),
            "targetAmount": round(target, 2),
            "currentSavings": round(current, 2),
            "months": months,
            "monthlyContribution": round(contrib_per_month, 2),
        },
        "remaining": round(remaining, 2),
        "requiredMonthly": required_monthly,
        "monthlyContribution": round(contrib_per_month, 2),
        "months": months,
        "progressPct": progress_pct,
        "isAchieved": is_achieved,
        "isSufficient": is_sufficient,
        "projectedShortfall": round(projected_shortfall, 2),
        "explanation": explanation,
        "assumptions": [
            "Pure cash savings projection without assuming investment market returns",
            "Consistent monthly contributions maintained across the entire timeline",
            "Inflation adjustment not factored into this savings benchmark",
        ],
        "series": series,
    }


def calculate_budget_analysis(profile_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Calculate comprehensive monthly budget analysis using profile and active goals.

    Accounting Conventions:
    - total_recorded_expenses = fixedExpenses + variableExpenses
    - total_goal_contributions = sum of required monthly contributions for all incomplete goals
    - other_outflows = total_goal_contributions
    - remaining_monthly_balance = monthlyIncome - total_recorded_expenses - other_outflows
    - investment_budget is reported as intended investment allocation capacity, not double-counted as an expense.
    """
    profile = profile_override or get_profile() or {}
    goals = list_goals()

    income = float(profile.get("monthlyIncome") or 0.0)
    fixed = float(profile.get("fixedExpenses") or 0.0)
    variable = float(profile.get("variableExpenses") or 0.0)
    inv_budget = float(profile.get("investmentBudget") or 0.0)

    total_expenses = fixed + variable

    # Calculate committed monthly goal contributions
    active_goals_contributions = 0.0
    for g in goals:
        rem = max(float(g["targetAmount"]) - float(g["currentSavings"]), 0.0)
        if rem > 0 and g["months"] > 0:
            if g.get("monthlyContribution") is not None and float(g["monthlyContribution"]) > 0:
                active_goals_contributions += float(g["monthlyContribution"])
            else:
                active_goals_contributions += math.ceil(rem / g["months"])

    total_outflows = total_expenses + active_goals_contributions
    remaining_balance = income - total_outflows

    # Ratios
    expense_ratio_pct = round((total_expenses / income) * 100, 1) if income > 0 else 0.0
    savings_rate_pct = round((active_goals_contributions / income) * 100, 1) if income > 0 else 0.0
    goal_capacity = max(remaining_balance, 0.0)

    # Missing data / warnings
    warnings: List[str] = []
    if income <= 0:
        warnings.append("Monthly income has not been recorded in your profile.")
    if fixed <= 0 and variable <= 0:
        warnings.append("No fixed or variable expenses have been recorded yet.")
    if remaining_balance < 0:
        warnings.append(
            f"Deficit alert: Your monthly commitments exceed your recorded income by ₹{int(round(abs(remaining_balance))):,}."
        )
    elif expense_ratio_pct > 75.0 and income > 0:
        warnings.append(f"High expense ratio: Your expenses consume {expense_ratio_pct}% of your income.")

    return {
        "monthlyIncome": round(income, 2),
        "fixedExpenses": round(fixed, 2),
        "variableExpenses": round(variable, 2),
        "totalExpenses": round(total_expenses, 2),
        "totalGoalContributions": round(active_goals_contributions, 2),
        "investmentBudget": round(inv_budget, 2),
        "totalOutflows": round(total_outflows, 2),
        "remainingBalance": round(remaining_balance, 2),
        "expenseRatioPct": expense_ratio_pct,
        "savingsRatePct": savings_rate_pct,
        "goalCapacity": round(goal_capacity, 2),
        "isDeficit": remaining_balance < 0,
        "warnings": warnings,
        "assumptions": [
            "Goal contributions represent ongoing monthly commitments toward active savings goals",
            "Investment budget is treated as an intended allocation capacity, not double-counted as an expense",
            "Remaining balance represents unallocated monthly surplus available for emergency reserves or investments",
        ],
    }


# ==============================================================================
# EXPENSE TRACKING
# ==============================================================================


def _expense_row(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "amount": row["amount"],
        "category": row["category"],
        "note": row["note"] or "",
        "date": row["spent_on"],
    }


def list_expenses(
    month: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None
) -> List[Dict[str, Any]]:
    """List logged expenses, newest first.

    `month` is 'YYYY-MM'; `start`/`end` are inclusive 'YYYY-MM-DD' bounds (all optional).
    """
    conn = get_db_connection()
    try:
        if start or end:
            rows = conn.execute(
                "SELECT * FROM expenses WHERE spent_on >= ? AND spent_on <= ? ORDER BY spent_on DESC, created_at DESC",
                (start or "0000-01-01", end or "9999-12-31"),
            ).fetchall()
        elif month:
            rows = conn.execute(
                "SELECT * FROM expenses WHERE spent_on LIKE ? ORDER BY spent_on DESC, created_at DESC",
                (f"{month}%",),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM expenses ORDER BY spent_on DESC, created_at DESC"
            ).fetchall()
        return [_expense_row(r) for r in rows]
    finally:
        conn.close()


def create_expense(data: Dict[str, Any]) -> Dict[str, Any]:
    """Log a single expense."""
    try:
        amount = float(data["amount"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("A numeric expense amount is required.")
    if amount <= 0:
        raise ValueError("Expense amount must be greater than zero.")
    category = str(data.get("category") or "").strip() or "Other"
    spent_on = str(data.get("date") or "").strip() or datetime.now().strftime("%Y-%m-%d")
    try:
        datetime.strptime(spent_on, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Date must be in YYYY-MM-DD format.")
    expense_id = f"exp_{int(time.time() * 1000)}"
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO expenses (id, amount, category, note, spent_on, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    expense_id,
                    amount,
                    category,
                    str(data.get("note") or "").strip(),
                    spent_on,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        return _expense_row(row)
    finally:
        conn.close()


def delete_expense(expense_id: str) -> bool:
    conn = get_db_connection()
    try:
        with conn:
            cur = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        return cur.rowcount > 0
    finally:
        conn.close()


def expense_summary(month: Optional[str] = None) -> Dict[str, Any]:
    """Total and per-category spending for a month (default: current month)."""
    month = month or datetime.now().strftime("%Y-%m")
    items = list_expenses(month)
    by_cat: Dict[str, float] = {}
    for e in items:
        by_cat[e["category"]] = by_cat.get(e["category"], 0.0) + e["amount"]
    total = sum(by_cat.values())
    profile = get_profile() or {}
    income = float(profile.get("monthlyIncome") or 0.0)
    planned_variable = float(profile.get("variableExpenses") or 0.0)
    return {
        "month": month,
        "count": len(items),
        "totalSpent": round(total, 2),
        "byCategory": [
            {"category": c, "amount": round(a, 2), "percentage": round(a / total * 100, 1) if total else 0.0}
            for c, a in sorted(by_cat.items(), key=lambda kv: -kv[1])
        ],
        "plannedVariableExpenses": round(planned_variable, 2),
        "remainingVariableBudget": round(planned_variable - total, 2) if planned_variable > 0 else None,
        "percentOfIncome": round(total / income * 100, 1) if income > 0 else None,
    }


# ==============================================================================
# CLEAR USER DATA
# ==============================================================================


def clear_user_data(everything: bool = False) -> Dict[str, int]:
    """Delete the saved profile. If `everything`, also delete goals and logged expenses."""
    conn = get_db_connection()
    try:
        with conn:
            removed = {"profile": conn.execute("DELETE FROM user_profile").rowcount}
            if everything:
                removed["goals"] = conn.execute("DELETE FROM financial_goals").rowcount
                removed["expenses"] = conn.execute("DELETE FROM expenses").rowcount
        return removed
    finally:
        conn.close()
