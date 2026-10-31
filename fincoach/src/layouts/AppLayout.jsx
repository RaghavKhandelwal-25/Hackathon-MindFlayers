import { useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Home as HomeIcon,
  LayoutDashboard,
  Target,
  UserRound,
  Wallet,
  TrendingUp,
  Receipt,
  Newspaper,
  Gamepad2,
  Eye,
  EyeOff,
  Trash2,
} from "lucide-react";
import { useFinance } from "../context/FinanceContext";
import ProfileModal from "../components/ProfileModal";
import ClearDataDialog from "../components/ClearDataDialog";
const inr = (n) => "₹" + Math.round(n || 0).toLocaleString("en-IN");
export default function AppLayout() {
  const { profile, stats, profileOpen, openProfile, closeProfile, afterSave, hidden, setHidden } =
      useFinance(),
    { pathname } = useLocation(),
    navigate = useNavigate(),
    onHome = pathname === "/",
    [clearOpen, setClearOpen] = useState(false);
  const cards = [
    ["Monthly Income", stats && inr(stats.monthlyIncome)],
    ["Monthly Investment Budget", stats && inr(stats.investmentBudget)],
    ["Planned Expenses", stats && inr(stats.totalSpent)],
    ["Investment Percentage", stats && stats.investmentPercentage.toFixed(1) + "%"],
  ];
  const links = [
    ["/", HomeIcon, "Home", true],
    ["/dashboard", LayoutDashboard, "Dashboard"],
    ["/goals", Target, "Set Goals"],
    ["/simulator", TrendingUp, "Simulator"],
    ["/expenses", Receipt, "Expenses"],
    ["/news", Newspaper, "News"],
    ["/play", Gamepad2, "Play"],
  ];
  return (
    <div className={"shell" + (hidden ? " privacy" : "")}>
      <nav className="sidebar" aria-label="Main">
        <Link to="/" className="brand brandlink" aria-label="Finbot home">
          <Wallet size={22} />
          <div className="brand-text">
            <span className="brand-name">Finbot</span>
            <span className="brand-tag">Make smarter financial decisions</span>
          </div>
        </Link>
        {links.map(([to, Icon, label, end]) => (
          <NavLink key={to} to={to} end={!!end} className="nav">
            <Icon size={18} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <main className="main">
        <header className="head">
          {!onHome && <h1>Welcome, {profile?.fullName?.split(" ")[0] || "there"} 👋</h1>}
          <div className="head-actions">
            <button
              className="toggle"
              role="switch"
              aria-checked={hidden}
              onClick={() => setHidden(!hidden)}
              title="Hide or show your amounts"
            >
              {hidden ? <EyeOff size={16} /> : <Eye size={16} />}
              <span>{hidden ? "Amounts hidden" : "Hide amounts"}</span>
            </button>
            <button className="toggle clearbtn" onClick={() => setClearOpen(true)} title="Clear your saved data">
              <Trash2 size={16} />
              <span>Clear data</span>
            </button>
            <button className="avatar" onClick={() => openProfile()} aria-label="Open profile">
              <UserRound size={18} />
              {profile?.fullName ? "" : <small>Set up profile</small>}
            </button>
          </div>
        </header>
        {!onHome && (
          <section className="stats">
            {cards.map(([l, v]) => (
              <div className="card stat" key={l}>
                <span>{l}</span>
                <strong>{v ?? "—"}</strong>
              </div>
            ))}
          </section>
        )}
        <Outlet />
      </main>
      {clearOpen && <ClearDataDialog onClose={() => setClearOpen(false)} onDone={() => navigate("/")} />}
      {profileOpen && (
        <ProfileModal onClose={closeProfile} onSaved={() => afterSave && navigate(afterSave)} />
      )}
    </div>
  );
}
