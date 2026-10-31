import { useState } from "react";
import { X, UserRound } from "lucide-react";
import { useFinance } from "../context/FinanceContext";
const EXP = [
  "Beginner (First-time Investor)",
  "Intermediate (Some experience)",
  "Advanced (Active investor)",
];
export default function ProfileModal({ onClose }) {
  const { profile, save } = useFinance();
  const [f, setF] = useState({
    fullName: "",
    email: "",
    age: "",
    occupation: "",
    monthlyIncome: "",
    investmentBudget: "",
    fixedExpenses: "",
    variableExpenses: "",
    experience: EXP[0],
    preferences: "",
    goals: "",
    ...profile,
  });
  const [err, setErr] = useState({}),
    [busy, setBusy] = useState(false),
    [apiErr, setApiErr] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const validate = () => {
    const e = {};
    if (!f.fullName.trim()) e.fullName = "Enter your name";
    if (f.email && !/^\S+@\S+\.\S+$/.test(f.email))
      e.email = "Enter a valid email";
    if (!(f.age >= 16 && f.age <= 100)) e.age = "Age must be 16–100";
    [
      "monthlyIncome",
      "investmentBudget",
      "fixedExpenses",
      "variableExpenses",
    ].forEach((k) => {
      if (f[k] === "" || +f[k] < 0) e[k] = "Enter 0 or more";
    });
    if (+f.monthlyIncome <= 0) e.monthlyIncome = "Income must be above 0";
    if (+f.investmentBudget > +f.monthlyIncome)
      e.investmentBudget = "Cannot exceed income";
    setErr(e);
    return !Object.keys(e).length;
  };
  const submit = async (ev) => {
    ev.preventDefault();
    if (!validate()) return;
    setBusy(true);
    setApiErr("");
    try {
      await save(f);
      onClose();
    } catch {
      setApiErr("Could not save your profile. Try again.");
    } finally {
      setBusy(false);
    }
  };
  const field = (k, label, type = "text") => (
    <label className="pf">
      {label}
      <input type={type} value={f[k]} onChange={set(k)} />
      {err[k] && <em>{err[k]}</em>}
    </label>
  );
  return (
    <div className="overlay" onClick={onClose}>
      <form
        className="modal"
        onClick={(e) => e.stopPropagation()}
        onSubmit={submit}
        noValidate
        role="dialog"
        aria-modal="true"
        aria-labelledby="pf-title"
      >
        <div className="mhead">
          <span className="micon">
            <UserRound size={22} />
          </span>
          <div>
            <h2 id="pf-title">Your Financial Profile</h2>
            <p>Update your details to calibrate AI financial guidance</p>
          </div>
          <button
            type="button"
            className="mclose"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={22} />
          </button>
        </div>
        <div className="msec grid2">
          {field("fullName", "Full Name")}
          {field("email", "Email Address", "email")}
          {field("age", "Age", "number")}
          {field("occupation", "Occupation")}
        </div>
        <div className="msec grid2">
          {field("monthlyIncome", "Monthly Income (₹)", "number")}
          {field("investmentBudget", "Monthly Investment Budget (₹)", "number")}
          {field(
            "fixedExpenses",
            "Fixed Expenses (Rent, EMI, Bills) (₹)",
            "number",
          )}
          {field(
            "variableExpenses",
            "Variable Expenses (Dining, Leisure) (₹)",
            "number",
          )}
        </div>
        <div className="msec grid2">
          <label className="pf">
            Financial Experience Level
            <select value={f.experience} onChange={set("experience")}>
              {EXP.map((o) => (
                <option key={o}>{o}</option>
              ))}
            </select>
          </label>
          {field("preferences", "Risk & Investment Preferences")}
          <label className="pf full">
            Financial Goals
            <textarea
              rows="2"
              value={f.goals}
              onChange={set("goals")}
              placeholder="e.g. buy a laptop, build an emergency fund"
            />
          </label>
        </div>
        {apiErr && <em className="apierr">{apiErr}</em>}
        <div className="mfoot">
          <button type="button" className="ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn" disabled={busy}>
            {busy ? "Saving…" : "Save profile"}
          </button>
        </div>
      </form>
    </div>
  );
}
