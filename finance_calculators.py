"""Deterministic Financial Calculation Module for FinGuide.

Provides standalone, deterministic, mathematically rigorous functions for:
1. Budget & Cashflow analysis (Income, Expenses, Outflows, 50/30/20 comparison).
2. Compound Interest (Principal, Annual Rate, Duration, Frequency).
3. SIP (Systematic Investment Plan) projections (Monthly Contribution, Return, Horizon).
4. Inflation & Purchasing Power projections (Current Cost, Inflation Rate, Horizon).

Accounting and Financial Conventions:
- All interest/return/inflation rates are accepted as percentages (e.g., 8.0 for 8%).
- Monetary values are rounded to 2 decimal places in structured outputs.
- Indian Rupee formatting adheres to the Indian numbering system (lakhs, crores).
- SIP compounding uses the standard annuity-due formula (investments made at the start of each month).
- No network requests or non-deterministic LLM calls are made within this module.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple, Union


def format_inr(amount: Union[float, int]) -> str:
    """Format a monetary amount in Indian Rupees (INR) using Indian numbering system.

    Examples:
        5000 -> "₹5,000"
        100000 -> "₹1,00,000"
        2500000.50 -> "₹25,00,000.50"
    """
    if amount is None:
        return "₹0"
    try:
        amt = float(amount)
    except (ValueError, TypeError):
        return f"₹{amount}"

    is_negative = amt < 0
    amt = abs(amt)

    # Split into integer and decimal parts
    int_part = int(math.floor(amt))
    dec_part = round(amt - int_part, 2)
    dec_str = f"{dec_part:.2f}"[1:] if dec_part > 0 else ""

    s = str(int_part)
    if len(s) <= 3:
        formatted_int = s
    else:
        # Last 3 digits
        last_three = s[-3:]
        remaining = s[:-3]
        # Group remaining digits in pairs of 2 from right to left
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        formatted_int = ",".join(groups) + "," + last_three

    res = f"₹{formatted_int}{dec_str}"
    return f"-{res}" if is_negative else res


def calculate_budget(
    monthly_income: float,
    fixed_expenses: float = 0.0,
    variable_expenses: float = 0.0,
    monthly_investment_or_savings: float = 0.0,
) -> Dict[str, Any]:
    """Calculate cashflow and budget breakdown using conservative accounting principles.

    Accounting Conventions:
    - total_expenses = fixed_expenses + variable_expenses
    - total_outflows = total_expenses + monthly_investment_or_savings
    - remaining_balance = monthly_income - total_outflows
    - Avoids double-counting: savings/investments are distinct from consumption expenses.

    Validation:
    - monthly_income must be >= 0.
    - expenses and savings must be >= 0.
    """
    if monthly_income < 0:
        raise ValueError("Monthly income cannot be negative.")
    if fixed_expenses < 0 or variable_expenses < 0:
        raise ValueError("Expenses cannot be negative.")
    if monthly_investment_or_savings < 0:
        raise ValueError("Monthly savings/investment cannot be negative.")

    total_expenses = fixed_expenses + variable_expenses
    total_outflows = total_expenses + monthly_investment_or_savings
    remaining_balance = monthly_income - total_outflows

    # Percentages of income
    if monthly_income > 0:
        expense_ratio_pct = round((total_expenses / monthly_income) * 100, 2)
        savings_rate_pct = round((monthly_investment_or_savings / monthly_income) * 100, 2)
        remaining_ratio_pct = round((remaining_balance / monthly_income) * 100, 2)
        needs_target = round(monthly_income * 0.50, 2)
        wants_target = round(monthly_income * 0.30, 2)
        savings_target = round(monthly_income * 0.20, 2)
    else:
        expense_ratio_pct = 0.0
        savings_rate_pct = 0.0
        remaining_ratio_pct = 0.0
        needs_target = 0.0
        wants_target = 0.0
        savings_target = 0.0

    return {
        "monthly_income": round(monthly_income, 2),
        "fixed_expenses": round(fixed_expenses, 2),
        "variable_expenses": round(variable_expenses, 2),
        "total_expenses": round(total_expenses, 2),
        "monthly_investment_or_savings": round(monthly_investment_or_savings, 2),
        "total_outflows": round(total_outflows, 2),
        "remaining_balance": round(remaining_balance, 2),
        "expense_ratio_pct": expense_ratio_pct,
        "savings_rate_pct": savings_rate_pct,
        "remaining_ratio_pct": remaining_ratio_pct,
        "rule_50_30_20_benchmark": {
            "needs_target_50": needs_target,
            "wants_target_30": wants_target,
            "savings_target_20": savings_target,
            "actual_needs": round(fixed_expenses, 2),
            "actual_wants": round(variable_expenses, 2),
            "actual_savings": round(monthly_investment_or_savings, 2),
        },
        "formatted": {
            "monthly_income": format_inr(monthly_income),
            "fixed_expenses": format_inr(fixed_expenses),
            "variable_expenses": format_inr(variable_expenses),
            "total_expenses": format_inr(total_expenses),
            "monthly_investment_or_savings": format_inr(monthly_investment_or_savings),
            "total_outflows": format_inr(total_outflows),
            "remaining_balance": format_inr(remaining_balance),
        },
    }


def calculate_compound_interest(
    principal: float,
    annual_rate_pct: float,
    duration_years: float,
    compounding_frequency: int = 1,
) -> Dict[str, Any]:
    """Calculate compound interest and future value.

    Formula:
        A = P * (1 + r / n) ** (n * t)
        Interest Earned = A - P

    Parameters:
    - principal: Initial sum invested/borrowed (>= 0).
    - annual_rate_pct: Annual interest rate in percent (>= 0).
    - duration_years: Time horizon in years (> 0).
    - compounding_frequency: Times compounded per year (1=annual, 2=semi-annual, 4=quarterly, 12=monthly).
    """
    if principal < 0:
        raise ValueError("Principal cannot be negative.")
    if annual_rate_pct < 0:
        raise ValueError("Annual interest rate cannot be negative.")
    if duration_years <= 0:
        raise ValueError("Duration must be greater than zero.")
    if compounding_frequency not in (1, 2, 4, 12, 365):
        raise ValueError(
            f"Unsupported compounding frequency {compounding_frequency}. Allowed: 1 (annual), 2 (semi-annual), 4 (quarterly), 12 (monthly), 365 (daily)."
        )

    frequency_labels = {
        1: "Annually",
        2: "Semi-Annually",
        4: "Quarterly",
        12: "Monthly",
        365: "Daily",
    }

    r = annual_rate_pct / 100.0
    n = compounding_frequency
    t = duration_years

    if r == 0:
        future_value = principal
        interest_earned = 0.0
        ear = 0.0
    else:
        future_value = principal * ((1.0 + r / n) ** (n * t))
        interest_earned = future_value - principal
        ear = ((1.0 + r / n) ** n - 1.0) * 100.0

    return {
        "principal": round(principal, 2),
        "annual_rate_pct": annual_rate_pct,
        "duration_years": round(duration_years, 2),
        "compounding_frequency": compounding_frequency,
        "frequency_label": frequency_labels.get(n, "Custom"),
        "future_value": round(future_value, 2),
        "interest_earned": round(interest_earned, 2),
        "effective_annual_rate_pct": round(ear, 3),
        "formatted": {
            "principal": format_inr(principal),
            "future_value": format_inr(future_value),
            "interest_earned": format_inr(interest_earned),
        },
    }


def calculate_sip(
    monthly_contribution: float,
    annual_return_pct: float,
    duration_months: Optional[int] = None,
    duration_years: Optional[float] = None,
    timing: str = "beginning",
) -> Dict[str, Any]:
    """Calculate Systematic Investment Plan (SIP) future value and wealth gain.

    Timing & Compounding Convention:
    - Standard Indian mutual fund convention (annuity-due): contributions occur at the
      beginning of each monthly period, compounding monthly at i = annual_return_pct / 12 / 100.
      Formula: FV = P * [((1 + i)^n - 1) / i] * (1 + i)
    - If timing == 'end' (ordinary annuity):
      Formula: FV = P * [((1 + i)^n - 1) / i]

    Parameters:
    - monthly_contribution: Amount invested every month (> 0).
    - annual_return_pct: Expected annual compounding return in percent (>= 0).
    - duration_months: Total investment months (> 0).
    - duration_years: Total investment years (> 0, converted to months if provided).
    - timing: 'beginning' (standard annuity-due) or 'end'.
    """
    if monthly_contribution <= 0:
        raise ValueError("Monthly contribution must be greater than zero.")
    if annual_return_pct < 0:
        raise ValueError("Annual return percentage cannot be negative.")

    if duration_months is not None:
        if duration_months <= 0:
            raise ValueError("Duration in months must be greater than zero.")
        total_months = int(duration_months)
        total_years = round(total_months / 12.0, 2)
    elif duration_years is not None:
        if duration_years <= 0:
            raise ValueError("Duration in years must be greater than zero.")
        total_months = int(round(duration_years * 12))
        total_years = round(duration_years, 2)
    else:
        raise ValueError("Either duration_months or duration_years must be specified.")

    total_contributions = monthly_contribution * total_months
    i = (annual_return_pct / 100.0) / 12.0

    if i == 0:
        future_value = total_contributions
        estimated_gain = 0.0
    else:
        if timing.lower() == "beginning":
            # Annuity due (standard SIP convention)
            future_value = (
                monthly_contribution * (((1.0 + i) ** total_months - 1.0) / i) * (1.0 + i)
            )
        else:
            # Ordinary annuity
            future_value = monthly_contribution * (((1.0 + i) ** total_months - 1.0) / i)

        estimated_gain = future_value - total_contributions

    return {
        "monthly_contribution": round(monthly_contribution, 2),
        "annual_return_pct": annual_return_pct,
        "duration_months": total_months,
        "duration_years": total_years,
        "timing_convention": (
            "Annuity Due (Beginning of Month - Standard SIP)"
            if timing.lower() == "beginning"
            else "Ordinary Annuity (End of Month)"
        ),
        "total_contributions": round(total_contributions, 2),
        "estimated_future_value": round(future_value, 2),
        "estimated_gain": round(estimated_gain, 2),
        "growth_factor": round(future_value / total_contributions, 2)
        if total_contributions > 0
        else 1.0,
        "formatted": {
            "monthly_contribution": format_inr(monthly_contribution),
            "total_contributions": format_inr(total_contributions),
            "estimated_future_value": format_inr(future_value),
            "estimated_gain": format_inr(estimated_gain),
        },
    }


def calculate_inflation(
    current_cost: float,
    annual_inflation_rate_pct: float,
    duration_years: float,
) -> Dict[str, Any]:
    """Calculate the future cost of an expense or goal adjusted for inflation.

    Formula:
        Future Cost = Current Cost * (1 + inflation_rate) ** duration_years
        Cost Difference = Future Cost - Current Cost
        Purchasing Power Loss % = (1 - 1 / (1 + inflation_rate) ** duration_years) * 100

    Parameters:
    - current_cost: Present monetary cost (>= 0).
    - annual_inflation_rate_pct: Expected annual inflation rate in percent (>= 0).
    - duration_years: Horizon in years (> 0).
    """
    if current_cost < 0:
        raise ValueError("Current cost cannot be negative.")
    if annual_inflation_rate_pct < 0:
        raise ValueError("Annual inflation rate cannot be negative.")
    if duration_years <= 0:
        raise ValueError("Duration must be greater than zero.")

    inf_rate = annual_inflation_rate_pct / 100.0
    future_cost = current_cost * ((1.0 + inf_rate) ** duration_years)
    difference = future_cost - current_cost

    if inf_rate == 0:
        purchasing_power_loss = 0.0
    else:
        purchasing_power_loss = (1.0 - (1.0 / ((1.0 + inf_rate) ** duration_years))) * 100.0

    return {
        "current_cost": round(current_cost, 2),
        "annual_inflation_rate_pct": annual_inflation_rate_pct,
        "duration_years": round(duration_years, 2),
        "estimated_future_cost": round(future_cost, 2),
        "cost_difference": round(difference, 2),
        "purchasing_power_loss_pct": round(purchasing_power_loss, 2),
        "formatted": {
            "current_cost": format_inr(current_cost),
            "estimated_future_cost": format_inr(future_cost),
            "cost_difference": format_inr(difference),
        },
    }
