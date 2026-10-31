import { useEffect, useState, useCallback } from 'react'
import { Trash2 } from 'lucide-react'
import { listExpenses, addExpense, removeExpense, getExpenseSummary } from '../services/expenseService'
import { DISCLAIMER } from './Dashboard'
const inr = n => '₹' + Math.round(n || 0).toLocaleString('en-IN')
const CATS = ['Food', 'Transport', 'Shopping', 'Bills', 'Entertainment', 'Health', 'Education', 'Other']
const today = () => new Date().toISOString().slice(0, 10)
export default function Expenses() {
  const [month, setMonth] = useState(today().slice(0, 7)), [items, setItems] = useState([]), [sum, setSum] = useState(null)
  const [f, setF] = useState({ amount: '', category: CATS[0], date: today(), note: '' }), [err, setErr] = useState(''), [busy, setBusy] = useState(false)
  const load = useCallback(async () => {
    try { const [l, s] = await Promise.all([listExpenses(month), getExpenseSummary(month)]); setItems(l); setSum(s); setErr('') }
    catch { setErr('Could not load expenses. Is the backend running?') }
  }, [month])
  useEffect(() => { load() }, [load])
  const set = k => e => setF({ ...f, [k]: e.target.value })
  const submit = async e => { e.preventDefault()
    if (!(+f.amount > 0)) return setErr('Enter an amount above 0.')
    setBusy(true); setErr('')
    try { await addExpense({ amount: +f.amount, category: f.category, date: f.date, note: f.note.trim() }); setF({ ...f, amount: '', note: '' }); if (f.date.slice(0, 7) !== month) setMonth(f.date.slice(0, 7)); else await load() }
    catch { setErr('Could not add the expense.') } finally { setBusy(false) } }
  const del = async id => { try { await removeExpense(id); await load() } catch { setErr('Could not delete the expense.') } }
  const left = sum?.remainingVariableBudget
  return (<>
    <form className="card goalform" onSubmit={submit}>
      <h2>Track an expense</h2>
      <div className="grid5 exp">
        <label>Amount (₹)<input type="number" min="1" value={f.amount} onChange={set('amount')} /></label>
        <label>Category<select value={f.category} onChange={set('category')}>{CATS.map(c => <option key={c}>{c}</option>)}</select></label>
        <label>Date<input type="date" value={f.date} onChange={set('date')} /></label>
        <label>Note (optional)<input value={f.note} onChange={set('note')} placeholder="Lunch with friends" /></label>
        <div className="simbtn"><button className="btn" disabled={busy}>{busy ? 'Adding…' : 'Add expense'}</button></div>
      </div>
      {err && <em>{err}</em>}
    </form>

    <section className="row between" style={{ flexWrap: 'wrap' }}>
      <h2 style={{ margin: 0 }}>Spending summary</h2>
      <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>Month<input type="month" value={month} onChange={e => e.target.value && setMonth(e.target.value)} style={{ width: 'auto', margin: 0 }} /></label>
    </section>

    {sum && <section className="stats three">
      <div className="card stat"><span>Spent this month</span><strong>{inr(sum.totalSpent)}</strong></div>
      <div className="card stat"><span>Entries</span><strong>{sum.count}</strong></div>
      <div className="card stat"><span>{left == null ? 'Variable budget left' : left >= 0 ? 'Variable budget left' : 'Over variable budget by'}</span><strong style={left < 0 ? { color: '#9b3b2e' } : undefined}>{left == null ? '—' : inr(Math.abs(left))}</strong></div>
    </section>}

    <section className="plan">
      <div className="card">
        <h2>Transactions</h2>
        {items.length === 0 ? <p style={{ color: 'var(--soft)' }}>No expenses logged for this month yet.</p> :
          items.map(x => <div className="goalrow" key={x.id}>
            <div><strong>{inr(x.amount)}</strong> · {x.category}<small>{x.date}{x.note ? ' · ' + x.note : ''}</small></div>
            <button className="ghost" onClick={() => del(x.id)} aria-label="Delete expense"><Trash2 size={16} /></button></div>)}
      </div>
      <div className="card">
        <h2>By category</h2>
        {sum && sum.byCategory.length > 0 ? sum.byCategory.map(c => <div key={c.category} className="scen">
          <div className="row between"><span>{c.category}</span><b>{inr(c.amount)} · {c.percentage}%</b></div>
          <div className="bar full"><i style={{ width: c.percentage + '%' }} /></div></div>) : <p style={{ color: 'var(--soft)' }}>Nothing to show yet.</p>}
      </div>
      <p className="disc wide">{DISCLAIMER}</p>
    </section>
  </>)
}
