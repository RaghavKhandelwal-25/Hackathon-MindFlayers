import { useState } from "react";
import { useFinance } from "../context/FinanceContext";

export default function ClearDataDialog({ onClose, onDone }) {
  const { clear } = useFinance();
  const [alsoAll, setAlsoAll] = useState(false),
    [busy, setBusy] = useState(false),
    [err, setErr] = useState("");
  const go = async () => {
    setBusy(true);
    setErr("");
    try {
      await clear(alsoAll);
      onDone?.();
      onClose();
    } catch {
      setErr("Could not clear your data. Try again.");
      setBusy(false);
    }
  };
  return (
    <div className="overlay" onClick={onClose}>
      <div className="card cleardialog" role="dialog" aria-modal="true" aria-labelledby="cd-title" onClick={(e) => e.stopPropagation()}>
        <h2 id="cd-title" style={{ margin: "0 0 6px" }}>Clear your saved data?</h2>
        <p style={{ margin: "0 0 12px", color: "var(--soft)" }}>
          This removes your profile from the dashboard. It cannot be undone.
        </p>
        <label className="cd-check">
          <input type="checkbox" checked={alsoAll} onChange={(e) => setAlsoAll(e.target.checked)} />
          Also delete my goals and logged expenses
        </label>
        {err && <em className="apierr">{err}</em>}
        <div className="row" style={{ gap: 10, marginTop: 14 }}>
          <button className="danger" disabled={busy} onClick={go}>{busy ? "Clearing…" : "Yes, clear it"}</button>
          <button className="ghost" onClick={onClose}>Keep my data</button>
        </div>
      </div>
    </div>
  );
}
