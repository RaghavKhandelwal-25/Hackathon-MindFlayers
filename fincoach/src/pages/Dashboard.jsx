import { useRef, useEffect, useState, useCallback } from "react";
import { Send, Bot, RefreshCw, AlertCircle } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { sendMessage } from "../services/chatService";
import { useFinance } from "../context/FinanceContext";
import SpendingPanel from "../components/SpendingPanel";
import { getBudgetAnalysis } from "../services/dashboardService";

export const DISCLAIMER =
  "This platform provides financial education and hypothetical simulations only. It does not provide personalized regulated investment advice. Actual investment returns may differ, and investments involve risk.";
const SUGGEST = [
  "What is my monthly income?",
  "What is 10% of my income?",
  "Calculate my budget breakdown",
  "How much money remains after my recorded expenses?",
  "What are my financial goals?",
  "How much have I spent this month?",
  "If I invest ₹5,000 monthly in an SIP for 10 years at 12%, how much will it become?",
  "Explain the 50/30/20 budgeting rule in simple language.",
];

const inr = (n) => "₹" + Math.round(n || 0).toLocaleString("en-IN");

export default function Dashboard() {
  const { profile } = useFinance();
  const [budget, setBudget] = useState(null);
  const [budgetLoading, setBudgetLoading] = useState(false);
  const [msgs, setMsgs] = useState([
    {
      role: "ai",
      text: "Hey! I'm your AI Financial Coach. I can help you understand your money, manage your budget, explore investments, and run financial calculations. What would you like to explore today?",
    },
  ]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef();

  const loadBudget = useCallback(async () => {
    setBudgetLoading(true);
    try {
      const data = await getBudgetAnalysis();
      setBudget(data);
    } catch (err) {
      console.error("Failed to load budget analysis", err);
    } finally {
      setBudgetLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBudget();
  }, [loadBudget, profile]);

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs, busy]);

  const send = async (t) => {
    t = t.trim();
    if (!t || busy) return;
    const history = msgs;
    setMsgs((m) => [...m, { role: "user", text: t }]);
    setText("");
    setBusy(true);
    try {
      // Pass the current user profile context to the backend
      const r = await sendMessage(t, history, profile);
      setMsgs((m) => [
        ...m,
        {
          role: "ai",
          text: r.reply,
          sources: r.sources || [],
          sufficientEvidence: r.sufficient_evidence,
          queryType: r.query_type,
        },
      ]);
      // Refresh budget if a query could affect budget or goals
      if (
        t.toLowerCase().includes("goal") ||
        t.toLowerCase().includes("budget") ||
        t.toLowerCase().includes("save")
      ) {
        loadBudget();
      }
    } catch {
      setMsgs((m) => [
        ...m,
        {
          role: "ai",
          text: "Sorry, I could not reach the coach right now. Please try again.",
          error: true,
        },
      ]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {/* Monthly Budget Analysis Card */}
      <section className="card" style={{ marginBottom: "16px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "14px",
          }}
        >
          <div>
            <h2 style={{ margin: 0, fontSize: "1.2rem" }}>
              📊 Monthly Budget Analysis
            </h2>
            <small style={{ color: "var(--soft)" }}>
              Deterministic cash flow breakdown and active savings commitments
            </small>
          </div>
          <button
            type="button"
            className="ghost"
            onClick={loadBudget}
            disabled={budgetLoading}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              fontSize: "0.85rem",
            }}
          >
            <RefreshCw size={14} className={budgetLoading ? "spin" : ""} />
            {budgetLoading ? "Recalculating…" : "Recalculate"}
          </button>
        </div>

        {budget && budget.warnings && budget.warnings.length > 0 && (
          <div
            style={{
              background: budget.isDeficit ? "#fee2e2" : "#fef3c7",
              border: `1px solid ${budget.isDeficit ? "#ef4444" : "#f59e0b"}`,
              borderRadius: "10px",
              padding: "10px 14px",
              marginBottom: "14px",
              color: budget.isDeficit ? "#991b1b" : "#92400e",
              fontSize: "0.88rem",
            }}
          >
            {budget.warnings.map((w, idx) => (
              <div
                key={idx}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  marginTop: idx > 0 ? "4px" : 0,
                }}
              >
                <AlertCircle size={15} style={{ flexShrink: 0 }} />
                <span>{w}</span>
              </div>
            ))}
          </div>
        )}

        {budget ? (
          <div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: "12px",
                marginBottom: "16px",
              }}
            >
              <div
                style={{
                  background: "var(--card2)",
                  padding: "12px 14px",
                  border: "1px solid var(--line)",
                  borderRadius: "12px",
                }}
              >
                <span
                  style={{
                    fontSize: "0.8rem",
                    color: "var(--soft)",
                    display: "block",
                  }}
                >
                  Monthly Income
                </span>
                <strong className="money" style={{ fontSize: "1.25rem" }}>
                  {inr(budget.monthlyIncome)}
                </strong>
              </div>
              <div
                style={{
                  background: "var(--card2)",
                  padding: "12px 14px",
                  border: "1px solid var(--line)",
                  borderRadius: "12px",
                }}
              >
                <span
                  style={{
                    fontSize: "0.8rem",
                    color: "var(--soft)",
                    display: "block",
                  }}
                >
                  Planned Expenses
                </span>
                <strong className="money" style={{ fontSize: "1.25rem" }}>
                  {inr(budget.totalExpenses)}
                </strong>
                <small
                  style={{
                    display: "block",
                    color: "var(--soft)",
                    fontSize: "0.75rem",
                  }}
                >
                  {budget.expenseRatioPct}% of income
                </small>
              </div>
              <div
                style={{
                  background: "var(--card2)",
                  padding: "12px 14px",
                  border: "1px solid var(--line)",
                  borderRadius: "12px",
                }}
              >
                <span
                  style={{
                    fontSize: "0.8rem",
                    color: "var(--soft)",
                    display: "block",
                  }}
                >
                  Goal Commitments
                </span>
                <strong className="money" style={{ fontSize: "1.25rem" }}>
                  {inr(budget.totalGoalContributions)}
                </strong>
                <small
                  style={{
                    display: "block",
                    color: "var(--soft)",
                    fontSize: "0.75rem",
                  }}
                >
                  {budget.savingsRatePct}% savings rate
                </small>
              </div>
              <div
                style={{
                  background: budget.isDeficit ? "#fee2e2" : "var(--card2)",
                  padding: "12px 14px",
                  border: `1px solid ${budget.isDeficit ? "#f87171" : "var(--line)"}`,
                  borderRadius: "12px",
                }}
              >
                <span
                  style={{
                    fontSize: "0.8rem",
                    color: budget.isDeficit ? "#991b1b" : "var(--soft)",
                    display: "block",
                  }}
                >
                  {budget.isDeficit ? "Monthly Deficit" : "Remaining Balance"}
                </span>
                <strong
                  style={{
                    fontSize: "1.25rem",
                    color: budget.isDeficit ? "#dc2626" : "#2B2620",
                  }}
                >
                  {budget.isDeficit
                    ? `-${inr(Math.abs(budget.remainingBalance))}`
                    : inr(budget.remainingBalance)}
                </strong>
                <small
                  style={{
                    display: "block",
                    color: budget.isDeficit ? "#991b1b" : "var(--soft)",
                    fontSize: "0.75rem",
                  }}
                >
                  {budget.isDeficit ? "Deficit Alert" : "Uncommitted Surplus"}
                </small>
              </div>
            </div>

            <div
              style={{
                fontSize: "0.82rem",
                color: "var(--soft)",
                borderTop: "1px solid var(--line)",
                paddingTop: "10px",
              }}
            >
              <strong>Assumptions & Rules:</strong>
              <ul style={{ margin: "4px 0 0", paddingLeft: "1.2rem" }}>
                {budget.assumptions?.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </div>
          </div>
        ) : (
          <div
            style={{
              textAlign: "center",
              padding: "1rem",
              color: "var(--soft)",
            }}
          >
            Loading monthly budget analysis…
          </div>
        )}
      </section>

      <SpendingPanel />

      <section className="card chat">
        <div className="chat-head">
          <span className="bot">
            <Bot size={18} />
          </span>
          <div>
            <strong>AI Financial Coach</strong>
            <small>
              Evidence-grounded guidance and deterministic calculations
              calibrated to your profile
            </small>
          </div>
        </div>
        <div className="msgs" aria-live="polite">
          {msgs.map((m, i) => (
            <div key={i} className={`bubble ${m.role}${m.error ? " err" : ""}`}>
              {m.role === "ai" ? (
                <div className="markdown-body">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      table: ({ node, ...props }) => (
                        <div className="table-responsive">
                          <table {...props} />
                        </div>
                      ),
                      a: ({ node, ...props }) => (
                        <a
                          {...props}
                          target="_blank"
                          rel="noopener noreferrer"
                        />
                      ),
                    }}
                  >
                    {m.text || ""}
                  </ReactMarkdown>
                </div>
              ) : (
                <div className="user-msg">{m.text}</div>
              )}
            </div>
          ))}
          {busy && (
            <div className="bubble ai dots">
              <i />
              <i />
              <i />
            </div>
          )}
          {msgs.length === 1 && (
            <div className="chips">
              {SUGGEST.map((s) => (
                <button key={s} className="chip" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          )}
          <div ref={end} />
        </div>
        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            send(text);
          }}
        >
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Ask about your budget, SIPs, saving, compound interest, inflation…"
            aria-label="Message"
          />
          <button
            className="btn"
            disabled={busy || !text.trim()}
            aria-label="Send"
          >
            <Send size={16} />
          </button>
        </form>
        <p className="disc">{DISCLAIMER}</p>
      </section>
    </>
  );
}
