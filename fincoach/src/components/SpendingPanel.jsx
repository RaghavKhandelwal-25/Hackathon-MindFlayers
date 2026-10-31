import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getExpenseSummary } from "../services/expenseService";
import { useFinance } from "../context/FinanceContext";
const inr = (n) => "₹" + Math.round(n || 0).toLocaleString("en-IN");

export default function SpendingPanel() {
  const { profile } = useFinance();
  const [s, setS] = useState(null);
  useEffect(() => {
    getExpenseSummary().then(setS).catch(() => setS(null));
  }, []);
  if (!s || !profile) return null;
  const fixed = +profile.fixedExpenses || 0,
    planned = +s.plannedVariableExpenses || 0,
    logged = s.totalSpent || 0,
    pct = planned > 0 ? (logged / planned) * 100 : 0,
    over = planned > 0 && logged > planned;
  return (
    <section className="card" style={{ marginBottom: "16px" }}>
      <h2 style={{ margin: 0 }}>🧾 Planned vs actual spending</h2>
      <p style={{ margin: "4px 0 14px", color: "var(--soft)" }}>
        This month: what you planned in your profile, compared with what you have logged in the Expense Tracker.
      </p>
      <div className="stats three" style={{ marginBottom: 14 }}>
        <div className="card stat money-card">
          <span>Planned monthly expenses</span>
          <strong>{inr(fixed + planned)}</strong>
          <small>{inr(fixed)} fixed + {inr(planned)} variable</small>
        </div>
        <div className="card stat money-card">
          <span>Logged this month</span>
          <strong>{inr(logged)}</strong>
          <small>{s.count} expense{s.count === 1 ? "" : "s"} tracked</small>
        </div>
        <div className="card stat money-card" style={over ? { borderColor: "#9b3b2e" } : undefined}>
          <span>{over ? "Over variable budget by" : "Variable budget left"}</span>
          <strong style={over ? { color: "#9b3b2e" } : undefined}>
            {planned > 0 ? inr(Math.abs(planned - logged)) : "—"}
          </strong>
          <small>{planned > 0 ? Math.round(pct) + "% of variable budget used" : "Set a variable budget in your profile"}</small>
        </div>
      </div>
      {planned > 0 && (
        <div className="bar full" style={{ marginBottom: 14 }}>
          <i style={{ width: Math.min(pct, 100) + "%", background: over ? "#9b3b2e" : undefined }} />
        </div>
      )}
      {s.byCategory.length > 0 ? (
        <>
          <strong>Where it went</strong>
          {s.byCategory.slice(0, 3).map((c) => (
            <div key={c.category} className="scen">
              <div className="row between">
                <span>{c.category}</span>
                <b className="money">{inr(c.amount)} · {c.percentage}%</b>
              </div>
              <div className="bar full"><i style={{ width: c.percentage + "%" }} /></div>
            </div>
          ))}
        </>
      ) : (
        <p style={{ color: "var(--soft)", margin: "0 0 8px" }}>
          Nothing logged yet this month. Add what you spend and Finbot will compare it with your plan.
        </p>
      )}
      <div className="row between" style={{ marginTop: 10, flexWrap: "wrap", gap: 8 }}>
        <small style={{ color: "var(--soft)" }}>
          Fixed costs (rent, EMI, bills) come from your profile. The tracker is for everyday spending.
        </small>
        <Link to="/expenses" className="ghost lg" style={{ textDecoration: "none" }}>Log an expense →</Link>
      </div>
    </section>
  );
}
