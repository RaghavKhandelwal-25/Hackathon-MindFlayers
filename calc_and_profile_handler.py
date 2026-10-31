"""FinGuide Profile-Aware and Deterministic Calculation Handler.

Responsible for:
1. Detecting user-profile inquiries (income, expenses, budget, goals, preferences)
   and providing honest, profile-grounded answers without invoking PDF search.
2. Routing financial calculations (Compound Interest, SIP, Inflation, Budget/Cashflow,
   Percentage of Income) to deterministic Python functions.
3. Resolving missing calculation parameters from the user's recorded profile when applicable.
4. Prompting for missing parameters when necessary.
5. Formatting deterministic results in clean, accessible GitHub-flavored Markdown.
"""

from __future__ import annotations

import math
import re
from datetime import date, timedelta
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import storage
except ImportError:
    from finguide import storage

from finance_calculators import (
    calculate_budget,
    calculate_compound_interest,
    calculate_inflation,
    calculate_sip,
    format_inr,
)


class CalculationType(str, Enum):
    BUDGET = "budget"
    COMPOUND_INTEREST = "compound_interest"
    SIP = "sip"
    INFLATION = "inflation"
    PERCENTAGE_OF_PROFILE = "percentage_of_profile"
    GOAL_PLAN = "goal_plan"
    BUDGET_ANALYSIS = "budget_analysis"
    EXPENSE_TRACKING = "expense_tracking"
    UNKNOWN = "unknown"


@dataclass
class CalculationResult:
    is_handled: bool
    calc_type: Optional[CalculationType]
    markdown_answer: str
    requires_rag_fusion: bool = False
    rag_query: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


def parse_indian_number(text: str) -> Optional[float]:
    """Parse numeric values with potential Indian multipliers (k, lakh, lac, crore, cr)."""
    if not text:
        return None
    cleaned = text.lower().replace(",", "").replace("₹", "").replace("rs.", "").replace("rs", "").strip()

    # Pattern for number + suffix
    m = re.search(r"(\d+(?:\.\d+)?)\s*(crores?|cr|lakhs?|lacs?|lac|l|k)?\b", cleaned)
    if not m:
        return None

    val = float(m.group(1))
    suffix = m.group(2) or ""

    if suffix in ("cr", "crore", "crores"):
        val *= 10_000_000.0
    elif suffix in ("lakh", "lakhs", "lac", "lacs", "l"):
        val *= 100_000.0
    elif suffix in ("k", "thousand"):
        val *= 1_000.0

    return val


def handle_profile_question(
    query: str, profile: Optional[Dict[str, Any]]
) -> Optional[CalculationResult]:
    """Inspect query for questions about the user's recorded profile data.

    Returns CalculationResult if handled, or None if not a profile-specific question.
    """
    q = query.lower().strip()

    # If the user asks for a percentage calculation or explicit calculation, do not treat as raw profile inspection
    if re.search(r"\b(\d+(?:\.\d+)?\s*(?:%|percent))\b", q) or "calculate" in q:
        return None

    # Check for direct profile attributes
    is_income_q = bool(
        re.search(r"\b(my\s+(monthly\s+)?income|my\s+salary|how\s+much\s+(do\s+i|i)\s+(earn|make)|my\s+earnings)\b", q)
    )
    is_budget_q = bool(
        re.search(r"\b(my\s+(monthly\s+)?(investment\s+)?budget|how\s+much\s+can\s+i\s+invest|my\s+investing\s+budget)\b", q)
    )
    is_expense_q = bool(
        re.search(r"\b(my\s+expenses|my\s+fixed\s+expenses|my\s+variable\s+expenses|how\s+much\s+(do\s+i|i)\s+spend|my\s+spending)\b", q)
    )
    is_goal_q = bool(
        re.search(r"\b(my\s+(financial\s+)?goals?|what\s+are\s+my\s+goals?|my\s+targets?)\b", q)
    )
    is_pref_q = bool(
        re.search(r"\b(my\s+(risk\s+)?(preference|preferences|profile)|my\s+experience(\s+level)?)\b", q)
    )
    is_profile_overview = bool(
        re.search(r"\b(my\s+(financial\s+)?profile|show\s+my\s+details|what\s+do\s+you\s+know\s+about\s+me)\b", q)
    )

    if not any([is_income_q, is_budget_q, is_expense_q, is_goal_q, is_pref_q, is_profile_overview]):
        return None

    # If no profile data provided or empty profile
    if not profile or not any(profile.values()):
        return CalculationResult(
            is_handled=True,
            calc_type=None,
            markdown_answer=(
                "ℹ️ **No Financial Profile Recorded Yet**\n\n"
                "You haven't set up your financial profile yet in the application. "
                "To record your monthly income, expenses, and investment budget, click the **Set up profile** "
                "avatar button in the top right corner.\n\n"
                "Once saved, I can tailor financial guidance, calculate personalized budget allocations, "
                "and answer questions about your recorded details directly!"
            ),
        )

    # 1. Income Question
    if is_income_q:
        income = profile.get("monthlyIncome")
        if income is not None and str(income).strip() != "":
            inc_val = float(income)
            return CalculationResult(
                is_handled=True,
                calc_type=None,
                markdown_answer=(
                    f"### 📋 Your Recorded Monthly Income\n\n"
                    f"According to your current financial profile, your recorded **monthly income** is **{format_inr(inc_val)}**.\n\n"
                    f"- **Annual Equivalent**: {format_inr(inc_val * 12)}\n"
                    f"- **50% Needs Benchmark**: {format_inr(inc_val * 0.50)}\n"
                    f"- **20% Savings Benchmark**: {format_inr(inc_val * 0.20)}\n\n"
                    f"*Note: You can update this amount anytime by clicking your profile icon at the top right.*"
                ),
            )
        else:
            return CalculationResult(
                is_handled=True,
                calc_type=None,
                markdown_answer=(
                    "ℹ️ **Monthly Income Not Recorded**\n\n"
                    "Your financial profile does not currently have a recorded monthly income. "
                    "You can add or update your monthly income in the **Profile** modal."
                ),
            )

    # 2. Budget Question
    if is_budget_q:
        budget = profile.get("investmentBudget")
        income = profile.get("monthlyIncome")
        if budget is not None and str(budget).strip() != "":
            b_val = float(budget)
            pct_str = ""
            if income and float(income) > 0:
                pct = (b_val / float(income)) * 100
                pct_str = f" (representing **{pct:.1f}%** of your monthly income)"
            return CalculationResult(
                is_handled=True,
                calc_type=None,
                markdown_answer=(
                    f"### 💼 Your Recorded Investment Budget\n\n"
                    f"Your recorded **monthly investment budget** is **{format_inr(b_val)}**{pct_str}.\n\n"
                    f"This is the amount you have earmarked for monthly savings, SIPs, or portfolio investments."
                ),
            )
        else:
            return CalculationResult(
                is_handled=True,
                calc_type=None,
                markdown_answer=(
                    "ℹ️ **Investment Budget Not Set**\n\n"
                    "Your profile does not currently list a specific monthly investment budget. "
                    "You can configure this in your Profile modal anytime."
                ),
            )

    # 3. Expenses Question
    if is_expense_q:
        fixed = float(profile.get("fixedExpenses") or 0.0)
        variable = float(profile.get("variableExpenses") or 0.0)
        total = fixed + variable
        income = float(profile.get("monthlyIncome") or 0.0)

        rows = [
            f"| Fixed Expenses (Rent, Bills, EMIs) | {format_inr(fixed)} |",
            f"| Variable Expenses (Leisure, Dining) | {format_inr(variable)} |",
            f"| **Total Monthly Expenses** | **{format_inr(total)}** |",
        ]
        if income > 0:
            exp_pct = (total / income) * 100
            rows.append(f"| **Expense Ratio** | **{exp_pct:.1f}% of income** |")

        table_str = "\n".join(rows)
        return CalculationResult(
            is_handled=True,
            calc_type=None,
            markdown_answer=(
                f"### 🧾 Your Recorded Expenses\n\n"
                f"| Expense Category | Amount |\n"
                f"| :--- | :--- |\n"
                f"{table_str}\n\n"
                f"*Data sourced directly from your active financial profile.*"
            ),
        )

    # 4. Goals Question
    if is_goal_q:
        goals = profile.get("goals")
        if goals and str(goals).strip():
            return CalculationResult(
                is_handled=True,
                calc_type=None,
                markdown_answer=(
                    f"### 🎯 Your Recorded Financial Goals\n\n"
                    f"According to your profile, your active financial goals are:\n\n"
                    f"> {goals}\n\n"
                    f"You can also track specific target amounts and monthly progress under the **Set Goals** page in the navigation sidebar."
                ),
            )
        else:
            return CalculationResult(
                is_handled=True,
                calc_type=None,
                markdown_answer=(
                    "ℹ️ **No Specific Goals Recorded**\n\n"
                    "You haven't added any goals in your profile yet. "
                    "You can define short-term or long-term goals (e.g. buying a laptop, emergency fund) in your Profile modal or on the Set Goals tab."
                ),
            )

    # 5. Risk & Experience Question
    if is_pref_q:
        exp = profile.get("experience") or "Not specified"
        prefs = profile.get("preferences") or "Not specified"
        return CalculationResult(
            is_handled=True,
            calc_type=None,
            markdown_answer=(
                f"### 🧭 Your Investor Profile & Preferences\n\n"
                f"- **Experience Level**: {exp}\n"
                f"- **Risk & Preferences**: {prefs}\n\n"
                f"I use these preferences to calibrate educational explanations to your experience level."
            ),
        )

    # 6. General Profile Overview
    income = profile.get("monthlyIncome")
    budget = profile.get("investmentBudget")
    fixed = profile.get("fixedExpenses")
    variable = profile.get("variableExpenses")
    name = profile.get("fullName") or "User"

    return CalculationResult(
        is_handled=True,
        calc_type=None,
        markdown_answer=(
            f"### 👤 Financial Profile for {name}\n\n"
            f"| Metric | Recorded Value |\n"
            f"| :--- | :--- |\n"
            f"| **Monthly Income** | {format_inr(income) if income is not None else 'Not set'} |\n"
            f"| **Fixed Expenses** | {format_inr(fixed) if fixed is not None else 'Not set'} |\n"
            f"| **Variable Expenses** | {format_inr(variable) if variable is not None else 'Not set'} |\n"
            f"| **Monthly Investment Budget** | {format_inr(budget) if budget is not None else 'Not set'} |\n"
            f"| **Experience** | {profile.get('experience') or 'Not set'} |\n\n"
            f"*To edit any of these values, click the profile icon in the top header.*"
        ),
    )


def handle_percentage_query(
    query: str, profile: Optional[Dict[str, Any]]
) -> Optional[CalculationResult]:
    """Handle queries like 'What is 10% of my income?', 'How much is 20 percent of my budget?'."""
    q = query.lower()

    # Match: X% of my (income|salary|budget|expenses)
    m = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:%|percent)\s+of\s+my\s+(monthly\s+)?(income|salary|budget|investment\s+budget|expenses|spending)",
        q,
    )
    if not m:
        # Match: how much is X% of my income
        m = re.search(
            r"how\s+much\s+is\s+(\d+(?:\.\d+)?)\s*(?:%|percent)\s+of\s+my\s+(monthly\s+)?(income|salary|budget|expenses)",
            q,
        )

    if not m:
        return None

    pct = float(m.group(1))
    target_field = m.group(m.lastindex).lower()

    if not profile:
        return CalculationResult(
            is_handled=True,
            calc_type=CalculationType.PERCENTAGE_OF_PROFILE,
            markdown_answer=(
                f"To calculate **{pct}%** of your {target_field}, I need your recorded profile data. "
                f"Please update your profile details in the top right corner."
            ),
        )

    base_val = None
    field_label = "income"

    if "income" in target_field or "salary" in target_field:
        base_val = profile.get("monthlyIncome")
        field_label = "Monthly Income"
    elif "budget" in target_field:
        base_val = profile.get("investmentBudget")
        field_label = "Monthly Investment Budget"
    elif "expense" in target_field or "spending" in target_field:
        fixed = float(profile.get("fixedExpenses") or 0.0)
        variable = float(profile.get("variableExpenses") or 0.0)
        base_val = fixed + variable
        field_label = "Total Monthly Expenses"

    if base_val is None or str(base_val).strip() == "":
        return CalculationResult(
            is_handled=True,
            calc_type=CalculationType.PERCENTAGE_OF_PROFILE,
            markdown_answer=(
                f"Your profile does not currently have a recorded value for **{field_label}**. "
                f"Please update your profile so I can calculate **{pct}%** for you."
            ),
        )

    base_float = float(base_val)
    result_val = (pct / 100.0) * base_float

    return CalculationResult(
        is_handled=True,
        calc_type=CalculationType.PERCENTAGE_OF_PROFILE,
        markdown_answer=(
            f"### 🧮 Percentage Calculation\n\n"
            f"| Parameter | Value |\n"
            f"| :--- | :--- |\n"
            f"| **Percentage** | **{pct}%** |\n"
            f"| **Recorded {field_label}** | **{format_inr(base_float)}** |\n"
            f"| **Calculated Amount** | **{format_inr(result_val)}** |\n\n"
            f"**Result**: **{pct}%** of your recorded {field_label.lower()} ({format_inr(base_float)}) is **{format_inr(result_val)}** per month."
        ),
        raw_data={"percentage": pct, "base_amount": base_float, "result": result_val},
    )


def handle_calculation_query(
    query: str, profile: Optional[Dict[str, Any]]
) -> Optional[CalculationResult]:
    """Detect and evaluate explicit financial calculation requests.

    Supports:
    - SIP calculations (e.g. 'SIP of 5000 for 10 years at 12%')
    - Compound Interest calculations (e.g. 'Compound interest on 1 lakh at 8% for 5 years')
    - Inflation calculations (e.g. 'What will 10 lakh cost after 15 years with 6% inflation?')
    - Budget breakdown calculations (e.g. 'Calculate my budget breakdown')
    """
    q = query.lower()

    # 1. Budget Breakdown Calculation
    if re.search(r"\b(calculate\s+my\s+budget|budget\s+breakdown|show\s+my\s+cashflow|my\s+budget\s+analysis|50/30/20\s+breakdown)\b", q):
        income = float(profile.get("monthlyIncome") or 0.0) if profile else 0.0
        fixed = float(profile.get("fixedExpenses") or 0.0) if profile else 0.0
        variable = float(profile.get("variableExpenses") or 0.0) if profile else 0.0
        budget = float(profile.get("investmentBudget") or 0.0) if profile else 0.0

        if income <= 0:
            return CalculationResult(
                is_handled=True,
                calc_type=CalculationType.BUDGET,
                markdown_answer=(
                    "To generate your deterministic budget breakdown, I need your monthly income. "
                    "Please set your income in your profile or ask with your income specified (e.g., *'Calculate budget for income 50000, fixed expenses 20000, variable 10000'*)."
                ),
            )

        res = calculate_budget(
            monthly_income=income,
            fixed_expenses=fixed,
            variable_expenses=variable,
            monthly_investment_or_savings=budget,
        )

        b = res["rule_50_30_20_benchmark"]
        return CalculationResult(
            is_handled=True,
            calc_type=CalculationType.BUDGET,
            markdown_answer=(
                f"### 📊 Monthly Budget & Cashflow Analysis\n\n"
                f"Based on your recorded profile figures, here is your deterministic budget breakdown:\n\n"
                f"| Component | Amount | % of Income |\n"
                f"| :--- | :--- | :--- |\n"
                f"| **Monthly Income** | **{res['formatted']['monthly_income']}** | 100.0% |\n"
                f"| Fixed Expenses (Needs) | {res['formatted']['fixed_expenses']} | {round((fixed/income)*100, 1)}% |\n"
                f"| Variable Expenses (Wants) | {res['formatted']['variable_expenses']} | {round((variable/income)*100, 1)}% |\n"
                f"| Planned Savings/Investments | {res['formatted']['monthly_investment_or_savings']} | {res['savings_rate_pct']}% |\n"
                f"| **Total Outflows** | **{res['formatted']['total_outflows']}** | {round((res['total_outflows']/income)*100, 1)}% |\n"
                f"| **Remaining Unallocated Cash** | **{res['formatted']['remaining_balance']}** | {res['remaining_ratio_pct']}% |\n\n"
                f"#### 50 / 30 / 20 Benchmark Comparison\n"
                f"- **Needs Target (50%)**: {format_inr(b['needs_target_50'])} (Actual: {format_inr(b['actual_needs'])})\n"
                f"- **Wants Target (30%)**: {format_inr(b['wants_target_30'])} (Actual: {format_inr(b['actual_wants'])})\n"
                f"- **Savings Target (20%)**: {format_inr(b['savings_target_20'])} (Actual: {format_inr(b['actual_savings'])})\n\n"
                f"*(Note: All calculations are deterministic arithmetic and do not constitute personal investment advice.)*"
            ),
            raw_data=res,
        )

    # 2. SIP Calculation
    # Look for keywords: sip, systematic investment plan, invest X every month, monthly investment
    is_sip_intent = bool(
        re.search(r"\b(sip|systematic\s+investment|monthly\s+investment|invest\s+(\d+|\w+)\s+(per|every|a)\s+month)\b", q)
    )
    # Check if calculation requested (how much, calculate, estimate, grow, future value, become, will i have)
    is_calc_intent = bool(
        re.search(r"\b(calculate|how\s+much|what\s+will|estimate|future\s+value|grow\s+to|returns?|become|will\s+i\s+(get|have))\b", q)
    )

    if is_sip_intent and is_calc_intent:
        # Extract parameters:
        # a) Monthly amount
        amount = None
        amt_match = re.search(r"(?:sip\s+of\s+|invest\s+|amount\s+|contribution\s+|rs\.?|₹)?(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:crores?|cr|lakhs?|lacs?|lac|l|k)?\s*(?:per\s+month|every\s+month|monthly|\/month)?", q)
        # Search specifically for monthly amount
        m_amt = re.search(r"(?:(?:of|rs\.?|₹|investing|save)\s+)?(\d+(?:,\d+)*(?:\.\d+)?\s*(?:crores?|cr|lakhs?|lacs?|lac|l|k)?)\s*(?:per\s+month|every\s+month|monthly|\/month|in\s+sip)", q)
        if m_amt:
            amount = parse_indian_number(m_amt.group(1))

        # If not explicitly in query, check profile investment budget
        if amount is None and profile and profile.get("investmentBudget"):
            try:
                amount = float(profile["investmentBudget"])
            except (ValueError, TypeError):
                pass

        # b) Rate of return (look for X%)
        rate = None
        r_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent)", q)
        if r_match:
            rate = float(r_match.group(1))
        else:
            # Default to standard equity benchmark return (12%) if not specified, but disclose
            rate = 12.0

        # c) Duration (years or months)
        years = None
        months = None
        dur_y_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b", q)
        if dur_y_match:
            years = float(dur_y_match.group(1))
        else:
            dur_m_match = re.search(r"(\d+)\s*(?:months?|mos?)\b", q)
            if dur_m_match:
                months = int(dur_m_match.group(1))

        if amount is None or (years is None and months is None):
            missing = []
            if amount is None:
                missing.append("monthly investment amount (e.g. ₹5,000)")
            if years is None and months is None:
                missing.append("investment duration (e.g. 5 years or 10 years)")
            return CalculationResult(
                is_handled=True,
                calc_type=CalculationType.SIP,
                markdown_answer=(
                    f"To calculate your SIP projection, please specify the missing information: "
                    f"**{', and '.join(missing)}**.\n\n"
                    f"*Example: 'If I invest ₹5,000 monthly in an SIP for 10 years at 12% return, how much will it grow to?'*"
                ),
            )

        try:
            res = calculate_sip(
                monthly_contribution=amount,
                annual_return_pct=rate,
                duration_years=years,
                duration_months=months,
            )
            return CalculationResult(
                is_handled=True,
                calc_type=CalculationType.SIP,
                markdown_answer=(
                    f"### 📈 Systematic Investment Plan (SIP) Projection\n\n"
                    f"| Metric | Value |\n"
                    f"| :--- | :--- |\n"
                    f"| **Monthly Contribution** | **{res['formatted']['monthly_contribution']}** |\n"
                    f"| **Duration** | **{res['duration_years']} years** ({res['duration_months']} months) |\n"
                    f"| **Assumed Annual Return** | **{res['annual_return_pct']}%** (compounded monthly) |\n"
                    f"| **Total Amount Invested** | **{res['formatted']['total_contributions']}** |\n"
                    f"| **Estimated Wealth Gain** | **{res['formatted']['estimated_gain']}** |\n"
                    f"| **Estimated Future Value** | **{res['formatted']['estimated_future_value']}** |\n\n"
                    f"**Summary**: By investing {res['formatted']['monthly_contribution']} monthly over {res['duration_years']} years, "
                    f"your total outlay of {res['formatted']['total_contributions']} is projected to grow to approximately **{res['formatted']['estimated_future_value']}** "
                    f"(a wealth multiple of **{res['growth_factor']}x**).\n\n"
                    f"*Assumptions & Methodology: Standard Indian mutual fund annuity-due convention with contributions at the start of each month. "
                    f"Market returns are subject to market risks and are not guaranteed.*"
                ),
                raw_data=res,
            )
        except Exception as exc:
            return CalculationResult(
                is_handled=True,
                calc_type=CalculationType.SIP,
                markdown_answer=f"⚠️ Unable to compute SIP projection: {str(exc)}",
            )

    # 3. Compound Interest Calculation
    is_ci_intent = bool(
        re.search(r"\b(compound\s+interest|compounding|compounded|ci\s+on)\b", q)
    )
    if is_ci_intent and is_calc_intent:
        # Principal
        p_match = re.search(r"(?:on|principal\s+of|invest\s+|sum\s+of|rs\.?|₹)\s*(\d+(?:,\d+)*(?:\.\d+)?\s*(?:crores?|cr|lakhs?|lacs?|lac|l|k)?)\b", q)
        principal = parse_indian_number(p_match.group(1)) if p_match else None

        # Rate
        r_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent)", q)
        rate = float(r_match.group(1)) if r_match else None

        # Duration
        dur_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b", q)
        duration = float(dur_match.group(1)) if dur_match else None

        # Frequency
        freq = 1
        if "quarterly" in q:
            freq = 4
        elif "monthly" in q:
            freq = 12
        elif "semi-annually" in q or "half-yearly" in q:
            freq = 2

        if principal is None or rate is None or duration is None:
            missing = []
            if principal is None:
                missing.append("principal amount (e.g. ₹1,00,000)")
            if rate is None:
                missing.append("interest rate (e.g. 8%)")
            if duration is None:
                missing.append("duration in years (e.g. 5 years)")
            return CalculationResult(
                is_handled=True,
                calc_type=CalculationType.COMPOUND_INTEREST,
                markdown_answer=(
                    f"To calculate compound interest, please provide: **{', and '.join(missing)}**.\n\n"
                    f"*Example: 'Calculate compound interest on ₹1,00,000 at 8% for 5 years compounded annually.'*"
                ),
            )

        try:
            res = calculate_compound_interest(
                principal=principal,
                annual_rate_pct=rate,
                duration_years=duration,
                compounding_frequency=freq,
            )
            return CalculationResult(
                is_handled=True,
                calc_type=CalculationType.COMPOUND_INTEREST,
                markdown_answer=(
                    f"### 💰 Compound Interest Calculation\n\n"
                    f"| Parameter | Value |\n"
                    f"| :--- | :--- |\n"
                    f"| **Principal (Initial Amount)** | **{res['formatted']['principal']}** |\n"
                    f"| **Annual Interest Rate** | **{res['annual_rate_pct']}%** |\n"
                    f"| **Compounding Frequency** | **{res['frequency_label']}** |\n"
                    f"| **Duration** | **{res['duration_years']} years** |\n"
                    f"| **Total Interest Earned** | **{res['formatted']['interest_earned']}** |\n"
                    f"| **Final Future Value** | **{res['formatted']['future_value']}** |\n\n"
                    f"**Result**: A principal of {res['formatted']['principal']} invested at {res['annual_rate_pct']}% compounded {res['frequency_label'].lower()} "
                    f"yields **{res['formatted']['interest_earned']}** in total interest, reaching **{res['formatted']['future_value']}** after {res['duration_years']} years."
                ),
                raw_data=res,
            )
        except Exception as exc:
            return CalculationResult(
                is_handled=True,
                calc_type=CalculationType.COMPOUND_INTEREST,
                markdown_answer=f"⚠️ Unable to compute compound interest: {str(exc)}",
            )

    # 4. Inflation Calculation
    is_inflation_intent = bool(
        re.search(r"\b(inflation|purchasing\s+power|cost\s+(in|after)\s+\d+\s+years?|what\s+will\s+.*cost)\b", q)
    )
    if is_inflation_intent and is_calc_intent:
        current_cost = None
        cost_match = re.search(r"(?:(?:cost|price|value)\s+of\s+|rs\.?|₹)\s*(\d+(?:,\d+)*(?:\.\d+)?\s*(?:crores?|cr|lakhs?|lacs?|lac|l|k)?)\b", q)
        if cost_match:
            current_cost = parse_indian_number(cost_match.group(1))
        if current_cost is None:
            cost_match2 = re.search(r"(\d+(?:,\d+)*(?:\.\d+)?\s*(?:crores?|cr|lakhs?|lacs?|lac|l|k)?)\s+(?:cost|price|value|expense)\b", q)
            if cost_match2:
                current_cost = parse_indian_number(cost_match2.group(1))

        r_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent)", q)
        inf_rate = float(r_match.group(1)) if r_match else 6.0  # Common RBI inflation band assumption

        dur_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b", q)
        duration = float(dur_match.group(1)) if dur_match else None

        if current_cost is None:
            candidates = re.findall(r"(\d+(?:,\d+)*(?:\.\d+)?\s*(?:crores?|cr|lakhs?|lacs?|lac|l|k)?)\b", q)
            for cand in candidates:
                val = parse_indian_number(cand)
                if val is not None and val != inf_rate and val != duration and val >= 100:
                    current_cost = val
                    break

        if current_cost is None or duration is None:
            missing = []
            if current_cost is None:
                missing.append("current cost (e.g. ₹10,00,000)")
            if duration is None:
                missing.append("time horizon (e.g. 15 years)")
            return CalculationResult(
                is_handled=True,
                calc_type=CalculationType.INFLATION,
                markdown_answer=(
                    f"To calculate future inflation impact, please provide: **{', and '.join(missing)}**.\n\n"
                    f"*Example: 'What will ₹10,00,000 cost after 15 years assuming 6% annual inflation?'*"
                ),
            )

        try:
            res = calculate_inflation(
                current_cost=current_cost,
                annual_inflation_rate_pct=inf_rate,
                duration_years=duration,
            )
            return CalculationResult(
                is_handled=True,
                calc_type=CalculationType.INFLATION,
                markdown_answer=(
                    f"### 📉 Inflation & Future Cost Projection\n\n"
                    f"| Metric | Value |\n"
                    f"| :--- | :--- |\n"
                    f"| **Current Cost / Expense** | **{res['formatted']['current_cost']}** |\n"
                    f"| **Assumed Annual Inflation Rate** | **{res['annual_inflation_rate_pct']}%** |\n"
                    f"| **Time Horizon** | **{res['duration_years']} years** |\n"
                    f"| **Estimated Future Cost** | **{res['formatted']['estimated_future_cost']}** |\n"
                    f"| **Cost Increase** | **{res['formatted']['cost_difference']}** |\n"
                    f"| **Purchasing Power Loss** | **{res['purchasing_power_loss_pct']}%** |\n\n"
                    f"**Summary**: An expense or goal costing {res['formatted']['current_cost']} today will require approximately "
                    f"**{res['formatted']['estimated_future_cost']}** in {res['duration_years']} years at {res['annual_inflation_rate_pct']}% annual inflation, "
                    f"requiring an additional {res['formatted']['cost_difference']}."
                ),
                raw_data=res,
            )
        except Exception as exc:
            return CalculationResult(
                is_handled=True,
                calc_type=CalculationType.INFLATION,
                markdown_answer=f"⚠️ Unable to compute inflation projection: {str(exc)}",
            )

    return None


def handle_goal_and_budget_chat_query(
    query: str, profile: Optional[Dict[str, Any]] = None
) -> Optional[CalculationResult]:
    """Handle deterministic goal planning and monthly budget analysis queries using SQLite."""
    if not query:
        return None

    q = query.lower().strip()

    # Retrieve profile if not provided
    if profile is None:
        try:
            profile = storage.get_profile() or {}
        except Exception:
            profile = {}

    # Case 1: Remaining balance / surplus after expenses
    is_remaining_query = bool(
        re.search(
            r"\b(how\s+much\s+(?:money\s+)?remains?|remaining\s+balance|surplus|left\s+over|balance\s+after\s+expenses)\b",
            q,
        )
    )
    is_budget_breakdown_query = bool(
        re.search(
            r"\b(monthly\s+budget\s+analysis|budget\s+breakdown|budget\s+summary|monthly\s+cash\s*flow)\b",
            q,
        )
    )

    if (is_remaining_query or is_budget_breakdown_query) and not re.search(r"\b(sooner|faster|increase|compound|sip)\b", q):
        analysis = storage.calculate_budget_analysis(profile_override=profile)
        income = analysis["monthlyIncome"]
        if income <= 0:
            return CalculationResult(
                is_handled=True,
                calc_type=CalculationType.BUDGET,
                markdown_answer=(
                    "### 📊 Monthly Budget & Cash Flow Analysis\n\n"
                    "⚠️ **Income Not Set**: You have not recorded your monthly income in your profile yet.\n\n"
                    "Please set your monthly income in the **Profile** modal to calculate your exact remaining balance and expense ratios."
                ),
                raw_data=analysis,
            )

        rem = analysis["remainingBalance"]
        rem_formatted = format_inr(rem)
        inc_formatted = format_inr(income)
        exp_formatted = format_inr(analysis["totalExpenses"])
        goals_formatted = format_inr(analysis["totalGoalContributions"])

        status_line = (
            f"**{rem_formatted}** (Surplus)"
            if rem >= 0
            else f"⚠️ **{format_inr(abs(rem))}** (Deficit)"
        )

        table = (
            f"### 📊 Monthly Budget & Cash Flow Breakdown\n\n"
            f"| Category | Amount |\n"
            f"| :--- | :--- |\n"
            f"| **Monthly Income** | **{inc_formatted}** |\n"
            f"| **Fixed Expenses** | {format_inr(analysis['fixedExpenses'])} |\n"
            f"| **Variable Expenses** | {format_inr(analysis['variableExpenses'])} |\n"
            f"| **Total Recorded Expenses** | **{exp_formatted}** ({analysis['expenseRatioPct']}% of income) |\n"
            f"| **Committed Goal Contributions** | **{goals_formatted}** ({analysis['savingsRatePct']}% of income) |\n"
            f"| **Total Monthly Outflows** | **{format_inr(analysis['totalOutflows'])}** |\n"
            f"| **Remaining Net Balance** | {status_line} |\n\n"
        )
        if rem >= 0:
            explanation = (
                f"After accounting for total recorded expenses of {exp_formatted} and active goal contributions of {goals_formatted}, "
                f"you have **{rem_formatted}** remaining each month. This surplus represents your available capacity for additional investments or emergency savings."
            )
        else:
            explanation = (
                f"Your total monthly commitments ({format_inr(analysis['totalOutflows'])}) exceed your monthly income ({inc_formatted}) "
                f"by **{format_inr(abs(rem))}**. Consider reviewing variable expenses or adjusting your goal timelines to restore a positive monthly cash flow."
            )

        return CalculationResult(
            is_handled=True,
            calc_type=CalculationType.BUDGET,
            markdown_answer=f"{table}{explanation}",
            raw_data=analysis,
        )

    # Case 2: Affordability of a goal based on current budget
    is_affordability = bool(
        re.search(r"\b(can\s+i\s+afford|is\s+it\s+affordable|can\s+we\s+afford)\b", q)
    )
    if is_affordability:
        goals = storage.list_goals()
        target_goal = None
        for g in goals:
            if g["name"].lower() in q:
                target_goal = g
                break
        if not target_goal and goals:
            for g in goals:
                words = [w for w in g["name"].lower().split() if len(w) > 3]
                if any(w in q for w in words):
                    target_goal = g
                    break
        if not target_goal and len(goals) == 1:
            target_goal = goals[0]

        analysis = storage.calculate_budget_analysis(profile_override=profile)
        rem_balance = analysis["remainingBalance"]

        if target_goal:
            plan = storage.calculate_goal_plan(target_goal)
            req_monthly = plan["requiredMonthly"]
            surplus_for_goal = rem_balance + (target_goal.get("monthlyContribution") or req_monthly)
            can_afford = surplus_for_goal >= req_monthly

            ans = (
                f"### 🎯 Goal Affordability Analysis: {target_goal['name']}\n\n"
                f"| Metric | Details |\n"
                f"| :--- | :--- |\n"
                f"| **Goal Target** | **{format_inr(target_goal['targetAmount'])}** |\n"
                f"| **Current Savings** | {format_inr(target_goal['currentSavings'])} |\n"
                f"| **Remaining Amount** | {format_inr(plan['remaining'])} |\n"
                f"| **Timeline** | {target_goal['months']} months |\n"
                f"| **Required Monthly Savings** | **{format_inr(req_monthly)}** |\n"
                f"| **Available Monthly Cashflow** | **{format_inr(surplus_for_goal)}** |\n\n"
            )
            if can_afford:
                ans += (
                    f"✅ **Yes, this goal is affordable based on your current budget!**\n\n"
                    f"Your available monthly surplus of **{format_inr(surplus_for_goal)}** comfortably covers "
                    f"the required **{format_inr(req_monthly)}/month** needed to achieve '{target_goal['name']}' in {target_goal['months']} months, "
                    f"leaving an uncommitted monthly cushion of **{format_inr(surplus_for_goal - req_monthly)}**."
                )
            else:
                shortfall = req_monthly - surplus_for_goal
                ans += (
                    f"⚠️ **This goal stretches your current monthly budget.**\n\n"
                    f"Saving **{format_inr(req_monthly)}/month** exceeds your available surplus ({format_inr(surplus_for_goal)}) "
                    f"by **{format_inr(shortfall)}/month**.\n\n"
                    f"**Recommendations**:\n"
                    f"- Extend the timeline from {target_goal['months']} months to {math.ceil(plan['remaining'] / max(surplus_for_goal, 1))} months.\n"
                    f"- Reduce variable expenses ({format_inr(analysis['variableExpenses'])}) to free up additional monthly cash flow."
                )
            return CalculationResult(
                is_handled=True,
                calc_type=CalculationType.BUDGET,
                markdown_answer=ans,
                raw_data={"goal": target_goal, "plan": plan, "analysis": analysis},
            )
        else:
            amount_match = re.search(r"(?:₹|rs\.?)\s*(\d+(?:,\d+)*(?:\.\d+)?\s*(?:k|lakh|lac)?)", q)
            if amount_match:
                hypo_amount = parse_indian_number(amount_match.group(1))
                if hypo_amount:
                    can_afford = rem_balance >= hypo_amount
                    ans = (
                        f"### 🎯 Budget Affordability Check\n\n"
                        f"- **Hypothetical Outflow**: {format_inr(hypo_amount)}/month\n"
                        f"- **Current Net Monthly Balance**: {format_inr(rem_balance)}\n\n"
                    )
                    if can_afford:
                        ans += f"✅ **Yes, you can afford this.** You have a remaining balance of {format_inr(rem_balance)} after all recorded expenses and goal contributions."
                    else:
                        ans += f"⚠️ **No, this exceeds your current surplus.** Your remaining balance is {format_inr(rem_balance)}, leaving a monthly gap of {format_inr(hypo_amount - rem_balance)}."
                    return CalculationResult(
                        is_handled=True,
                        calc_type=CalculationType.BUDGET,
                        markdown_answer=ans,
                        raw_data={"hypo_amount": hypo_amount, "remaining_balance": rem_balance},
                    )

            return CalculationResult(
                is_handled=True,
                calc_type=CalculationType.BUDGET,
                markdown_answer=(
                    f"Based on your current recorded budget, your net monthly surplus after expenses and active goals is **{format_inr(rem_balance)}**.\n\n"
                    f"To check affordability for a specific goal, please specify the goal name (e.g. *'Can I afford my gold chain?'*) "
                    f"or add your goal under the **Set Goals** tab."
                ),
            )

    # Case 3: Hypothetical contribution change / sooner completion
    is_hypo_increase = bool(
        re.search(
            r"\b(increase\s+(?:my\s+)?contribution|what\s+happens\s+if\s+i\s+(?:increase|save|contribute)|how\s+much\s+(?:sooner|faster)\s+can\s+i\s+reach)\b",
            q,
        )
    )
    if is_hypo_increase:
        goals = storage.list_goals()
        target_goal = None
        for g in goals:
            if g["name"].lower() in q:
                target_goal = g
                break
        if not target_goal and goals:
            for g in goals:
                words = [w for w in g["name"].lower().split() if len(w) > 3]
                if any(w in q for w in words):
                    target_goal = g
                    break
        if not target_goal and len(goals) == 1:
            target_goal = goals[0]

        if not target_goal:
            return CalculationResult(
                is_handled=True,
                calc_type=CalculationType.GOAL_PLAN,
                markdown_answer=(
                    "You haven't specified which goal to evaluate, and no active goals were found. "
                    "Please create a goal in **Set Goals** (e.g. *'Buy a laptop'*) or mention its name."
                ),
            )

        target = target_goal["targetAmount"]
        current = target_goal["currentSavings"]
        remaining = max(target - current, 0.0)
        curr_months = target_goal["months"]
        curr_contrib = target_goal.get("monthlyContribution") or math.ceil(remaining / curr_months)

        new_amt_match = re.search(
            r"(?:to|by|save|contribute)\s*(?:₹|rs\.?)\s*(\d+(?:,\d+)*(?:\.\d+)?\s*(?:k|lakh|lac)?)",
            q,
        )
        if not new_amt_match:
            new_amt_match = re.search(r"(?:₹|rs\.?)\s*(\d+(?:,\d+)*(?:\.\d+)?\s*(?:k|lakh|lac)?)", q)

        new_contrib = None
        if new_amt_match:
            parsed = parse_indian_number(new_amt_match.group(1))
            if parsed and parsed > 0:
                if "increase" in q and "by" in q:
                    new_contrib = curr_contrib + parsed
                else:
                    new_contrib = parsed

        if new_contrib:
            new_months = math.ceil(remaining / new_contrib) if new_contrib > 0 else curr_months
            months_saved = max(curr_months - new_months, 0)

            ans = (
                f"### 🚀 Goal Acceleration Analysis: {target_goal['name']}\n\n"
                f"| Plan | Monthly Savings | Duration to Target | Completion |\n"
                f"| :--- | :--- | :--- | :--- |\n"
                f"| **Current Baseline** | {format_inr(curr_contrib)}/mo | **{curr_months} months** | On schedule |\n"
                f"| **Accelerated Plan** | **{format_inr(new_contrib)}/mo** | **{new_months} months** | **{months_saved} months sooner!** |\n\n"
                f"**Summary**: By increasing your monthly contribution to **{format_inr(new_contrib)}**, "
                f"you will accumulate the remaining {format_inr(remaining)} in **{new_months} months** instead of {curr_months} months—reaching your target **{months_saved} months earlier**."
            )
            return CalculationResult(
                is_handled=True,
                calc_type=CalculationType.GOAL_PLAN,
                markdown_answer=ans,
                raw_data={"goal": target_goal, "curr_contrib": curr_contrib, "new_contrib": new_contrib, "months_saved": months_saved},
            )
        else:
            illustrative_contrib = math.ceil(curr_contrib * 1.25)
            illustrative_months = math.ceil(remaining / illustrative_contrib)
            months_saved = max(curr_months - illustrative_months, 0)
            ans = (
                f"### 🚀 Goal Timeline for {target_goal['name']}\n\n"
                f"- **Remaining Target**: {format_inr(remaining)}\n"
                f"- **Current Timeline**: {curr_months} months at {format_inr(curr_contrib)}/month.\n\n"
                f"If you increase your monthly contribution by 25% to **{format_inr(illustrative_contrib)}/month**, "
                f"you would achieve your target in **{illustrative_months} months**—reaching your goal **{months_saved} months sooner**!"
            )
            return CalculationResult(
                is_handled=True,
                calc_type=CalculationType.GOAL_PLAN,
                markdown_answer=ans,
            )

    # Case 4: "How much do I need to save monthly for my [goal]?"
    is_save_need = bool(
        re.search(
            r"\b(how\s+much\s+(?:do\s+i\s+need\s+to\s+)?save\s+monthly|monthly\s+savings?\s+(?:needed\s+)?for|save\s+for\s+my)\b",
            q,
        )
    )
    if is_save_need:
        goals = storage.list_goals()
        target_goal = None
        for g in goals:
            if g["name"].lower() in q:
                target_goal = g
                break
        if not target_goal and goals:
            for g in goals:
                words = [w for w in g["name"].lower().split() if len(w) > 3]
                if any(w in q for w in words):
                    target_goal = g
                    break
        if not target_goal and len(goals) == 1:
            target_goal = goals[0]

        if target_goal:
            plan = storage.calculate_goal_plan(target_goal)
            req = plan["requiredMonthly"]
            rem = plan["remaining"]
            ans = (
                f"### 🎯 Monthly Savings Plan: {target_goal['name']}\n\n"
                f"| Metric | Value |\n"
                f"| :--- | :--- |\n"
                f"| **Target Amount** | **{format_inr(target_goal['targetAmount'])}** |\n"
                f"| **Current Savings** | {format_inr(target_goal['currentSavings'])} |\n"
                f"| **Remaining Amount** | {format_inr(rem)} |\n"
                f"| **Duration** | **{target_goal['months']} months** |\n"
                f"| **Required Monthly Savings** | **{format_inr(req)}** |\n\n"
                f"**Direct Answer**: To reach your target of {format_inr(target_goal['targetAmount'])} for **{target_goal['name']}** in {target_goal['months']} months, "
                f"you need to save **{format_inr(req)} per month**."
            )
            return CalculationResult(
                is_handled=True,
                calc_type=CalculationType.GOAL_PLAN,
                markdown_answer=ans,
                raw_data=plan,
            )
        else:
            if goals:
                names = ", ".join(f"'{g['name']}'" for g in goals)
                return CalculationResult(
                    is_handled=True,
                    calc_type=CalculationType.GOAL_PLAN,
                    markdown_answer=f"You currently have these goals saved: {names}. Which goal would you like to calculate monthly savings for?",
                )
            else:
                return CalculationResult(
                    is_handled=True,
                    calc_type=CalculationType.GOAL_PLAN,
                    markdown_answer=(
                        "You haven't created any financial goals yet. "
                        "You can add a goal under the **Set Goals** tab (specifying name, target amount, and timeline) to get an exact monthly savings schedule."
                    ),
                )

    # Case 5: List/show my goals
    is_list_goals = bool(
        re.search(
            r"\b(what\s+are\s+my\s+(?:financial\s+)?goals|list\s+(?:all\s+)?my\s+goals|show\s+(?:all\s+)?my\s+goals)\b",
            q,
        )
    )
    if is_list_goals:
        goals = storage.list_goals()
        if not goals:
            return CalculationResult(
                is_handled=True,
                calc_type=CalculationType.GOAL_PLAN,
                markdown_answer="You have not created any financial goals yet. Go to the **Set Goals** tab to add your first goal!",
            )
        lines = [
            "### 🎯 Your Active Financial Goals\n\n",
            "| Goal Name | Target | Saved | Progress | Timeline | Monthly Need |\n",
            "| :--- | :--- | :--- | :--- | :--- | :--- |\n",
        ]
        for g in goals:
            plan = storage.calculate_goal_plan(g)
            lines.append(
                f"| **{g['name']}** | {format_inr(g['targetAmount'])} | {format_inr(g['currentSavings'])} | "
                f"**{plan['progressPct']}%** | {g['months']} mo | {format_inr(plan['requiredMonthly'])}/mo |\n"
            )
        return CalculationResult(
            is_handled=True,
            calc_type=CalculationType.GOAL_PLAN,
            markdown_answer="".join(lines),
            raw_data={"goals": goals},
        )

    return None


# ==============================================================================
# EXPENSE TRACKING CHAT QUERIES (uses expenses logged on the Expenses page)
# ==============================================================================

_CATEGORY_WORDS = {
    "Food": ["food", "dining", "groceries", "grocery", "restaurant", "restaurants", "eating", "lunch", "dinner", "snacks"],
    "Transport": ["transport", "travel", "fuel", "petrol", "cab", "uber", "bus", "metro", "commute"],
    "Shopping": ["shopping", "clothes", "clothing", "amazon"],
    "Bills": ["bills", "bill", "rent", "electricity", "recharge", "internet"],
    "Entertainment": ["entertainment", "movie", "movies", "games", "gaming", "netflix", "outings"],
    "Health": ["health", "medical", "medicine", "medicines", "doctor", "gym"],
    "Education": ["education", "books", "course", "courses", "tuition", "fees"],
}
_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}


def _expense_period(q: str, today: date) -> Tuple[Optional[str], Optional[str], str]:
    """Return (start, end, label) for the period mentioned in the query."""
    iso = lambda d: d.isoformat()
    if "yesterday" in q:
        d = today - timedelta(days=1)
        return iso(d), iso(d), "yesterday"
    if re.search(r"\btoday\b", q):
        return iso(today), iso(today), "today"
    if re.search(r"\b(last|past|previous)\s+week\b", q):
        return iso(today - timedelta(days=6)), iso(today), "the last 7 days"
    if re.search(r"\bthis\s+week\b", q):
        return iso(today - timedelta(days=today.weekday())), iso(today), "this week"
    if re.search(r"\b(last|previous)\s+month\b", q):
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        return iso(last_prev.replace(day=1)), iso(last_prev), last_prev.strftime("%B %Y")
    for name, num in _MONTHS.items():
        if re.search(rf"\b{name}\b", q) and not (name == "may" and not re.search(r"\b(in|during|for|of)\s+may\b", q)):
            ym = re.search(rf"{name}\s+(20\d\d)", q)
            year = int(ym.group(1)) if ym else (today.year if num <= today.month else today.year - 1)
            first = date(year, num, 1)
            nxt = date(year + (num == 12), (num % 12) + 1, 1)
            return iso(first), iso(nxt - timedelta(days=1)), first.strftime("%B %Y")
    if re.search(r"\b(all\s+time|overall|in\s+total|ever)\b", q):
        return None, None, "all time"
    first = today.replace(day=1)
    return iso(first), iso(today), "this month"


def _expense_category(q: str, known: List[str]) -> Optional[str]:
    for cat in known:
        if re.search(rf"\b{re.escape(cat.lower())}s?\b", q):
            return cat
    for canon, words in _CATEGORY_WORDS.items():
        if any(re.search(rf"\b{w}\b", q) for w in words):
            for cat in known:
                if cat.lower() == canon.lower():
                    return cat
            return canon
    return None


def handle_expense_query(query: str, profile: Optional[Dict[str, Any]] = None) -> Optional[CalculationResult]:
    """Answer questions about expenses the user has logged (totals, categories, recent items)."""
    if not query:
        return None
    q = query.lower().strip()

    if not re.search(r"\b(spent|spend|spending|expenditures?|expenses?|transactions?|purchases)\b", q):
        return None
    # advice / definition questions are not about the user's logged data
    if re.search(r"\b(should i|can i|how (?:can|do|to) (?:i )?(?:reduce|cut|save)|tips|ideas|budget for)\b", q):
        return None
    if re.search(r"\b(what is|what are|explain|define|meaning of)\b", q) and not re.search(r"\b(my|i)\b", q):
        return None
    if re.search(r"\b(fixed|variable|monthly budget|expense ratio)\b", q):
        return None

    personal = bool(re.search(
        r"\b(did i|have i|i have|i've|i spent|i spend|my spending|my expenditures?|so far|logged|tracked|my transactions|my purchases|recent|latest)\b", q))
    today = date.today()
    start, end, label = _expense_period(q, today)
    has_period = label != "this month" or bool(re.search(r"\bthis month\b", q))
    if not (personal or (has_period and re.search(r"\bmy\b", q))):
        return None

    all_items = storage.list_expenses()
    if not all_items:
        if not personal:
            return None  # let profile questions fall through
        return CalculationResult(
            is_handled=True,
            calc_type=CalculationType.EXPENSE_TRACKING,
            markdown_answer=(
                "### 🧾 No expenses logged yet\n\n"
                "You haven't logged any expenses yet. Open the **Expenses** page, add what you spend, "
                "and I can then answer questions like *\"How much did I spend on food this month?\"*."
            ),
        )

    known = sorted({e["category"] for e in all_items})
    category = _expense_category(q, known)
    items = storage.list_expenses(start=start, end=end)
    if category:
        items = [e for e in items if e["category"].lower() == category.lower()]
    scope = f"on **{category}**" if category else ""

    # List / recent transactions
    if re.search(r"\b(show|list|recent|latest|transactions?|purchases)\b", q) and not re.search(r"\bhow much\b", q):
        m = re.search(r"\b(?:last|latest|recent)\s+(\d{1,2})\b", q)
        limit = int(m.group(1)) if m else 10
        shown = items[:limit]
        if not shown:
            return CalculationResult(True, CalculationType.EXPENSE_TRACKING,
                                     f"### 🧾 Expenses\n\nNo expenses found {scope} for **{label}**.".replace("  ", " "))
        rows = "\n".join(f"| {e['date']} | {e['category']} | {format_inr(e['amount'])} | {e['note'] or '-'} |" for e in shown)
        return CalculationResult(
            True, CalculationType.EXPENSE_TRACKING,
            f"### 🧾 Your latest expenses ({label})\n\n| Date | Category | Amount | Note |\n| :--- | :--- | ---: | :--- |\n{rows}\n\n"
            f"Showing {len(shown)} of {len(items)} expense(s), totalling **{format_inr(sum(e['amount'] for e in items))}**.",
            raw_data={"count": len(items)},
        )

    total = sum(e["amount"] for e in items)
    if not items:
        return CalculationResult(True, CalculationType.EXPENSE_TRACKING,
                                 f"### 🧾 Spending ({label})\n\nYou have no logged expenses {scope} for **{label}**.".replace("  ", " "))

    by_cat: Dict[str, float] = {}
    for e in items:
        by_cat[e["category"]] = by_cat.get(e["category"], 0.0) + e["amount"]

    when = label if label.startswith(("this", "today", "yesterday", "the last")) else f"in {label}"
    lines = [f"### 🧾 Spending {scope} - {label}".replace("  ", " "), "",
             f"You spent **{format_inr(total)}** {scope} across **{len(items)}** logged expense(s) {when}.".replace("  ", " ")]
    if not category and len(by_cat) > 1:
        rows = "\n".join(f"| {c} | {format_inr(a)} | {a / total * 100:.1f}% |" for c, a in sorted(by_cat.items(), key=lambda kv: -kv[1]))
        top = max(by_cat.items(), key=lambda kv: kv[1])
        lines += ["", "| Category | Amount | Share |", "| :--- | ---: | ---: |", rows, "", f"Your biggest category is **{top[0]}** ({top[1] / total * 100:.0f}% of spending)."]
    income = float((profile or storage.get_profile() or {}).get("monthlyIncome") or 0.0)
    planned = float((profile or storage.get_profile() or {}).get("variableExpenses") or 0.0)
    if label == "this month" and not category:
        if planned > 0:
            diff = planned - total
            lines += ["", (f"Against your planned variable expenses of {format_inr(planned)}, you have **{format_inr(diff)}** left." if diff >= 0
                            else f"⚠️ That is **{format_inr(-diff)} over** your planned variable expenses of {format_inr(planned)}.")]
        if income > 0:
            lines += [f"That is {total / income * 100:.1f}% of your monthly income."]
    return CalculationResult(True, CalculationType.EXPENSE_TRACKING, "\n".join(lines), raw_data={"total": total, "count": len(items)})
