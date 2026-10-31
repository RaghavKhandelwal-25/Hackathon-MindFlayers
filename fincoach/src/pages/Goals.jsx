import { useEffect, useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import {
  listGoals,
  createGoal,
  updateGoal,
  deleteGoal,
  generatePlan,
} from "../services/goalService";
import { DISCLAIMER } from "./Dashboard";
const inr = (n) => "₹" + Math.round(n || 0).toLocaleString("en-IN");
const EMPTY = {
  name: "",
  targetAmount: "",
  currentSavings: "",
  months: "",
  monthlyContribution: "",
};
const COLORS = ["#5E6B4E", "#8C5A3C", "#C9A27A"];
export default function Goals() {
  const [goals, setGoals] = useState([]),
    [f, setF] = useState(EMPTY),
    [editId, setEditId] = useState(null);
  const [plan, setPlan] = useState(null),
    [busy, setBusy] = useState(false),
    [err, setErr] = useState("");
  const load = async () => {
    try {
      setGoals(await listGoals());
    } catch {
      setErr("Could not load goals.");
    }
  };
  useEffect(() => {
    load();
  }, []);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const payload = () => ({
    name: f.name.trim(),
    targetAmount: +f.targetAmount,
    currentSavings: +f.currentSavings || 0,
    months: +f.months,
    monthlyContribution: f.monthlyContribution ? +f.monthlyContribution : null,
  });
  const run = async (g) => {
    setBusy(true);
    setErr("");
    try {
      setPlan({ goal: g, ...(await generatePlan(g)) });
    } catch {
      setErr("Could not generate the plan. Try again.");
    } finally {
      setBusy(false);
    }
  };
  const submit = async (e) => {
    e.preventDefault();
    const g = payload();
    if (!g.name || g.targetAmount <= 0 || g.months <= 0)
      return setErr(
        "Enter a goal name, a target above 0 and a duration in months.",
      );
    if (g.currentSavings > g.targetAmount)
      return setErr("Current savings cannot exceed the target.");
    try {
      editId ? await updateGoal(editId, g) : await createGoal(g);
      setEditId(null);
      setF(EMPTY);
      await load();
      await run(g);
    } catch {
      setErr("Could not save the goal.");
    }
  };
  const edit = (g) => {
    setEditId(g.id);
    setF({
      name: g.name,
      targetAmount: g.targetAmount,
      currentSavings: g.currentSavings,
      months: g.months,
      monthlyContribution: g.monthlyContribution ?? "",
    });
  };
  const remove = async (id) => {
    if (window.confirm("Are you sure you want to delete this goal?")) {
      try {
        await deleteGoal(id);
        if (editId === id) {
          setEditId(null);
          setF(EMPTY);
        }
        if (plan?.goal?.id === id) {
          setPlan(null);
        }
        await load();
      } catch {
        setErr("Could not delete goal.");
      }
    }
  };
  const pie = plan && [
    { name: "Current savings", value: plan.goal.currentSavings },
    { name: "Remaining", value: plan.remaining },
    {
      name: "Planned contributions",
      value: plan.monthlyContribution * plan.months,
    },
  ];
  return (
    <>
      <form className="card goalform" onSubmit={submit}>
        <h2>{editId ? "Edit goal" : "Set a goal"}</h2>
        <div className="grid5">
          <label>
            Goal Name
            <input
              value={f.name}
              onChange={set("name")}
              placeholder="Buy a laptop"
            />
          </label>
          <label>
            Target Amount (₹)
            <input
              type="number"
              min="0"
              value={f.targetAmount}
              onChange={set("targetAmount")}
            />
          </label>
          <label>
            Current Savings (₹)
            <input
              type="number"
              min="0"
              value={f.currentSavings}
              onChange={set("currentSavings")}
            />
          </label>
          <label>
            Duration (months)
            <input
              type="number"
              min="1"
              value={f.months}
              onChange={set("months")}
            />
          </label>
          <label>
            Monthly Contribution (optional)
            <input
              type="number"
              min="0"
              value={f.monthlyContribution}
              onChange={set("monthlyContribution")}
            />
          </label>
        </div>
        {err && <em>{err}</em>}
        <div className="row">
          <button className="btn" disabled={busy}>
            {busy ? "Generating…" : "Generate Financial Plan"}
          </button>
          {editId && (
            <button
              type="button"
              className="ghost"
              onClick={() => {
                setEditId(null);
                setF(EMPTY);
              }}
            >
              Cancel edit
            </button>
          )}
        </div>
      </form>

      {goals.length > 0 ? (
        <section className="card">
          <h2>Your goals</h2>
          {goals.map((g) => (
            <div className="goalrow" key={g.id}>
              <div>
                <strong>{g.name}</strong>
                <small>
                  {inr(g.currentSavings)} of {inr(g.targetAmount)} · {g.months}{" "}
                  months (
                  {Math.min(
                    100,
                    Math.round(
                      ((g.currentSavings || 0) / g.targetAmount) * 100,
                    ),
                  )}
                  % reached)
                </small>
                <div className="bar">
                  <i
                    style={{
                      width:
                        Math.min(
                          100,
                          ((g.currentSavings || 0) / g.targetAmount) * 100,
                        ) + "%",
                    }}
                  />
                </div>
              </div>
              <div className="row">
                <button className="ghost" onClick={() => run(g)}>
                  Recalculate
                </button>
                <button
                  className="ghost"
                  onClick={() => edit(g)}
                  aria-label="Edit"
                >
                  <Pencil size={16} />
                </button>
                <button
                  className="ghost"
                  onClick={() => remove(g.id)}
                  aria-label="Delete"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </section>
      ) : (
        <div
          className="card"
          style={{ textAlign: "center", padding: "2rem 1rem" }}
        >
          <p style={{ color: "#6b7280" }}>
            No goals yet. Fill out the form above to set your first financial
            goal and calculate a personalized savings plan.
          </p>
        </div>
      )}

      {plan && (
        <section className="plan">
          <div className="card">
            <h2>Plan for {plan.goal.name}</h2>
            <p>{plan.explanation}</p>
            <div className="kv">
              <span>Remaining</span>
              <b>{inr(plan.remaining)}</b>
              <span>Monthly contribution</span>
              <b>{inr(plan.monthlyContribution)}</b>
              <span>Timeline</span>
              <b>{plan.months} months</b>
              {plan.progressPct !== undefined && (
                <>
                  <span>Progress</span>
                  <b>{plan.progressPct}%</b>
                </>
              )}
            </div>
            {plan.projectedShortfall > 0 && (
              <p
                style={{
                  color: "#b91c1c",
                  marginTop: "0.75rem",
                  fontWeight: 500,
                  fontSize: "0.9rem",
                }}
              >
                ⚠️ Projected Shortfall: {inr(plan.projectedShortfall)} at{" "}
                {inr(plan.monthlyContribution)}/month. Save{" "}
                {inr(plan.requiredMonthly)}/month to reach your goal on time.
              </p>
            )}
            <h3>Assumptions</h3>
            <ul>
              {plan.assumptions.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
            <div className="chartbox">
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={plan.series}>
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis
                    tickFormatter={(v) => "₹" + v / 1000 + "k"}
                    tick={{ fontSize: 12 }}
                  />
                  <Tooltip formatter={inr} />
                  <Area
                    dataKey="projected"
                    name="Projected"
                    stroke="#8C5A3C"
                    fill="#8C5A3C33"
                    strokeDasharray="5 4"
                  />
                  <Area
                    dataKey="actual"
                    name="Actual savings"
                    stroke="#3E4A32"
                    fill="#3E4A3255"
                    dot
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="card">
            <h2>Breakdown</h2>
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={pie}
                  dataKey="value"
                  innerRadius={55}
                  outerRadius={90}
                  paddingAngle={2}
                >
                  {pie.map((_, i) => (
                    <Cell key={i} fill={COLORS[i]} />
                  ))}
                </Pie>
                <Tooltip formatter={inr} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <p className="disc wide">{DISCLAIMER}</p>
        </section>
      )}
    </>
  );
}
