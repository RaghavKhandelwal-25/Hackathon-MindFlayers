import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { LayoutDashboard, Target, UserRound, Wallet } from 'lucide-react'
import { useFinance } from '../context/FinanceContext'
import ProfileModal from '../components/ProfileModal'
const inr = n => '₹' + Math.round(n || 0).toLocaleString('en-IN')
export default function AppLayout() {
  const { profile, stats } = useFinance(), [open, setOpen] = useState(false)
  const cards = [['Monthly Income', stats && inr(stats.monthlyIncome)], ['Monthly Investment Budget', stats && inr(stats.investmentBudget)],
    ['Total Spent', stats && inr(stats.totalSpent)], ['Investment Percentage', stats && stats.investmentPercentage.toFixed(1) + '%']]
  return (
    <div className="shell">
      <nav className="sidebar" aria-label="Main">
        <div className="brand"><Wallet size={22} /><span>Ledgerly</span></div>
        <NavLink to="/" end className="nav"><LayoutDashboard size={18} /><span>Dashboard</span></NavLink>
        <NavLink to="/goals" className="nav"><Target size={18} /><span>Set Goals</span></NavLink>
      </nav>
      <main className="main">
        <header className="head">
          <h1>Welcome, {profile?.fullName?.split(' ')[0] || 'there'} 👋</h1>
          <button className="avatar" onClick={() => setOpen(true)} aria-label="Open profile"><UserRound size={18} />{profile?.fullName ? '' : <small>Set up profile</small>}</button>
        </header>
        <section className="stats">{cards.map(([l, v]) => <div className="card stat" key={l}><span>{l}</span><strong>{v ?? '—'}</strong></div>)}</section>
        <Outlet />
      </main>
      {open && <ProfileModal onClose={() => setOpen(false)} />}
    </div>)
}
