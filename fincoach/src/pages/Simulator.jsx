import { useEffect, useState } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { simulateSip } from '../services/simulatorService'
import { DISCLAIMER } from './Dashboard'
const inr = n => '₹' + Math.round(n || 0).toLocaleString('en-IN')
const short = v => v >= 10000000 ? '₹' + (v / 10000000).toFixed(1) + 'Cr' : v >= 100000 ? '₹' + (v / 100000).toFixed(1) + 'L' : '₹' + Math.round(v / 1000) + 'k'
const DEFAULTS = { monthly: '5000', rate: '12', years: '10', target: '' }
export default function Simulator() {
  const [f, setF] = useState(DEFAULTS), [res, setRes] = useState(null), [busy, setBusy] = useState(false), [err, setErr] = useState('')
  const set = k => e => setF({ ...f, [k]: e.target.value })
  const run = async v => {
    const body = { monthlyContribution: +v.monthly, annualReturn: +v.rate, years: +v.years, ...(+v.target > 0 ? { targetAmount: +v.target } : {}) }
    if (!(body.monthlyContribution > 0)) return setErr('Monthly amount must be above 0.')
    if (!(body.annualReturn >= 0 && body.annualReturn <= 100)) return setErr('Expected return must be between 0 and 100%.')
    if (!(body.years > 0 && body.years <= 60)) return setErr('Years must be between 1 and 60.')
    setBusy(true); setErr('')
    try { setRes(await simulateSip(body)) } catch { setErr('Could not run the simulation. Is the backend running?') } finally { setBusy(false) }
  }
  useEffect(() => { run(DEFAULTS) }, [])
  const submit = e => { e.preventDefault(); run(f) }
  const s = res?.summary, g = res?.goalCheck
  const data = res && res.series.filter((p, i) => res.series.length <= 130 || p.month % 12 === 0 || i === res.series.length - 1)
  const maxFv = res ? Math.max(...res.scenarios.map(x => x.estimatedFutureValue)) : 1
  return (<>
    <form className="card goalform" onSubmit={submit}>
      <h2>"What if" SIP simulator</h2>
      <p style={{ margin: '0 0 12px', color: 'var(--soft)' }}>See how a small monthly investment could grow, or what you need to save to reach a goal like a laptop or a bike.</p>
      <div className="grid5 sim">
        <label>Monthly Investment (₹)<input type="number" min="1" value={f.monthly} onChange={set('monthly')} /></label>
        <label>Expected Return (% per year)<input type="number" min="0" max="100" step="0.5" value={f.rate} onChange={set('rate')} /></label>
        <label>Duration (years)<input type="number" min="1" max="60" step="0.5" value={f.years} onChange={set('years')} /></label>
        <label>Goal Amount (₹, optional)<input type="number" min="0" value={f.target} onChange={set('target')} placeholder="e.g. 80000" /></label>
        <div className="simbtn"><button className="btn" disabled={busy}>{busy ? 'Calculating…' : 'Simulate'}</button></div>
      </div>
      {err && <em>{err}</em>}
    </form>

    {res && <>
      <section className="stats three">
        <div className="card stat"><span>Total invested</span><strong>{inr(s.total_contributions)}</strong></div>
        <div className="card stat"><span>Estimated value</span><strong>{inr(s.estimated_future_value)}</strong></div>
        <div className="card stat"><span>Estimated gain</span><strong>{inr(s.estimated_gain)}</strong></div>
      </section>

      {g && <section className={'card goalcheck ' + (g.reachesTarget ? 'ok' : 'warn')}>
        <h2>Goal check: {inr(g.targetAmount)}</h2>
        {g.reachesTarget
          ? <p>✅ At {inr(s.monthly_contribution)}/month you are projected to reach this goal{g.monthsToTarget ? <> in about <b>{g.monthsToTarget} months</b></> : ''}.</p>
          : <p>⚠️ At {inr(s.monthly_contribution)}/month you would fall short by <b>{inr(g.shortfall)}</b>. To reach it in {s.duration_years} years you would need about <b>{inr(g.requiredMonthlyContribution)}/month</b>.</p>}
      </section>}

      <section className="plan">
        <div className="card">
          <h2>Growth over {s.duration_years} years</h2>
          <div className="chartbox"><ResponsiveContainer width="100%" height={280}><AreaChart data={data}>
            <XAxis dataKey="month" tickFormatter={m => m % 12 === 0 ? m / 12 + 'y' : ''} tick={{ fontSize: 12 }} /><YAxis tickFormatter={short} tick={{ fontSize: 12 }} width={56} />
            <Tooltip formatter={inr} labelFormatter={m => 'Month ' + m} /><Legend />
            <Area dataKey="invested" name="Amount invested" stroke="#8C5A3C" fill="#8C5A3C33" />
            <Area dataKey="value" name="Estimated value" stroke="#3E4A32" fill="#3E4A3255" /></AreaChart></ResponsiveContainer></div>
        </div>
        <div className="card">
          <h2>If returns differ</h2>
          {res.scenarios.map(x => <div key={x.label} className="scen">
            <div className="row between"><span>{x.label} ({x.annualReturnPct}%)</span><b>{inr(x.estimatedFutureValue)}</b></div>
            <div className="bar full"><i style={{ width: (x.estimatedFutureValue / maxFv) * 100 + '%' }} /></div></div>)}
          <small style={{ color: 'var(--soft)' }}>Returns vary with the market. These are not guarantees.</small>
        </div>
        <p className="disc wide">{res.disclaimer || DISCLAIMER}</p>
      </section>
    </>}
  </>)
}
