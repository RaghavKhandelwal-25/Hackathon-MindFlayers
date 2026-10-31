import { useEffect, useRef, useState, useCallback } from 'react'
import { ShieldAlert, ShieldCheck, Clock, Share2, RotateCcw, Flame, Play as PlayIcon, Check, X, LogOut } from 'lucide-react'
import { getRound } from '../services/gameService'
import { DISCLAIMER } from './Dashboard'
import './play.css'

const KEY = 'finbot.scamOrLegit.v1'
const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || {} } catch { return {} } }
const store = v => { try { localStorage.setItem(KEY, JSON.stringify(v)) } catch { /* storage unavailable: game still works */ } }
const dayGap = (a, b) => Math.round((new Date(b) - new Date(a)) / 86400000)
const RANKS = [[7, 'Scam-proof'], [5, 'Sharp eye'], [3, 'Getting there'], [0, 'Keep practising']]
const rank = n => RANKS.find(([min]) => n >= min)[1]
const gridOf = picks => picks.map(p => (p.correct ? '🟩' : '🟥')).join('')

function Explain({ card }) {
  const scam = card.verdict === 'scam'
  return (<div className="gexp">
    <h3>{scam ? 'Red flags' : 'Why it is fine'}</h3>
    <ul>{card.flags.map(f => <li key={f}>{f}</li>)}</ul>
    <p style={{ margin: '10px 0 0' }}>{card.why}</p>
    <div className="gtip"><b>Remember:</b> {card.tip}</div>
  </div>)
}

function Message({ card }) {
  return (<div className="gcard">
    <div className="gchan"><span className="gpill">{card.channel}</span><span>From: {card.sender}</span></div>
    <p className="gmsg">{card.text}</p>
  </div>)
}

export default function Play() {
  const [saved, setSaved] = useState(load)
  const [phase, setPhase] = useState('intro'), [mode, setMode] = useState('daily')
  const [round, setRound] = useState(null), [daily, setDaily] = useState(null)
  const [i, setI] = useState(0), [picks, setPicks] = useState([]), [left, setLeft] = useState(25)
  const [err, setErr] = useState(''), [busy, setBusy] = useState(false), [copied, setCopied] = useState(false)
  const deadline = useRef(0)
  const secs = round?.secondsPerCard || 25
  const card = round?.cards[i]

  // Load today's round once so we know today's date and whether it was already played.
  useEffect(() => {
    getRound('daily').then(setDaily).catch(() => setErr('Could not load the game. Is the backend running?'))
  }, [])
  const playedToday = daily && saved.daily?.date === daily.date

  const begin = r => { setRound(r); setI(0); setPicks([]); setLeft(r.secondsPerCard); deadline.current = Date.now() + r.secondsPerCard * 1000; setPhase('playing') }
  const start = async m => {
    setBusy(true); setErr(''); setMode(m)
    try { begin(m === 'daily' && daily ? daily : await getRound(m)) }
    catch { setErr('Could not load the game. Is the backend running?') }
    finally { setBusy(false) }
  }

  const answer = useCallback(choice => {
    if (!card) return
    const rem = Math.max(0, (deadline.current - Date.now()) / 1000)
    const correct = choice === card.verdict
    const points = correct ? 100 + Math.round((rem / secs) * 50) : 0
    setPicks(p => (p.length > i ? p : [...p, { choice, correct, points, timedOut: choice === null }]))
    setPhase('reveal')
  }, [card, secs, i])

  // Countdown: runs only while a card is on screen waiting for an answer.
  useEffect(() => {
    if (phase !== 'playing') return
    const t = setInterval(() => {
      const rem = Math.max(0, (deadline.current - Date.now()) / 1000)
      setLeft(rem)
      if (rem <= 0) answer(null)
    }, 200)
    return () => clearInterval(t)
  }, [phase, answer])

  // Keyboard: S = Scam, L = Legit.
  useEffect(() => {
    if (phase !== 'playing') return
    const onKey = e => { const k = e.key.toLowerCase(); if (k === 's') answer('scam'); else if (k === 'l') answer('legit') }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [phase, answer])

  const total = picks.reduce((s, p) => s + p.points, 0), right = picks.filter(p => p.correct).length
  const next = () => {
    if (i + 1 < round.cards.length) { setI(i + 1); setLeft(secs); deadline.current = Date.now() + secs * 1000; setPhase('playing'); return }
    if (mode === 'daily' && round.date !== saved.daily?.date) {
      const gap = saved.lastDate ? dayGap(saved.lastDate, round.date) : null
      const streak = gap === 1 ? (saved.streak || 0) + 1 : 1
      const upd = { ...saved, lastDate: round.date, streak, best: Math.max(saved.best || 0, streak), daily: { date: round.date, score: total, right, n: round.cards.length, grid: gridOf(picks) } }
      store(upd); setSaved(upd)
    }
    setPhase('done')
  }

  const exit = () => { if (window.confirm('Leave this round? Your progress in it will be lost.')) setPhase('intro') }
  const result = phase === 'done' ? { date: round.date, score: total, right, n: round.cards.length, grid: gridOf(picks) } : saved.daily
  const share = async () => {
    const text = `Scam or Legit? ${result.date}${mode === 'practice' && phase === 'done' ? ' (practice)' : ''}\n${result.right}/${result.n} ${result.grid}\nPlay on Finbot`
    try { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000) } catch { setErr('Could not copy. Select the text and copy it yourself.') }
  }

  const header = (<div className="gtop">
    <div><h2 style={{ margin: 0 }}>Scam or Legit?</h2><small>Spot the scam before it spots you</small></div>
    {saved.streak > 0 && <span className="row" title="Days in a row"><Flame size={18} /> <b>{saved.streak}</b> day streak</span>}
  </div>)

  if (phase === 'intro') return (<>
    <section className="card">{header}
      <p style={{ margin: '12px 0 4px' }}>Seven messages, 25 seconds each. Decide if each one is a <b>scam</b> or <b>legit</b>, then see why. Faster correct answers score more.</p>
      <p style={{ margin: '0 0 14px', color: 'var(--soft)' }}>Tip: press <b>S</b> for Scam and <b>L</b> for Legit.</p>
      {err && <em className="apierr">{err}</em>}
      {playedToday ? (<>
        <div className="gcard"><b>You played today's round: {saved.daily.right}/{saved.daily.n} · {saved.daily.score} points</b>
          <div className="ggrid">{saved.daily.grid}</div>
          <div className="row"><button className="ghost row" onClick={share}><Share2 size={16} />{copied ? 'Copied!' : 'Share result'}</button></div></div>
        <div style={{ marginTop: 14 }}><button className="btn row" disabled={busy} onClick={() => start('practice')}><RotateCcw size={16} />{busy ? 'Loading…' : 'Practice with new cards'}</button></div>
      </>) : (<div className="row" style={{ flexWrap: 'wrap' }}>
        <button className="btn row" disabled={busy || !daily} onClick={() => start('daily')}><PlayIcon size={16} />{busy ? 'Loading…' : "Play today's round"}</button>
        <button className="ghost" disabled={busy} onClick={() => start('practice')}>Practice</button>
      </div>)}
    </section>
    <p className="disc wide">{daily?.disclaimer} {DISCLAIMER}</p>
  </>)

  if (phase === 'playing' || phase === 'reveal') {
    const pick = picks[i], reveal = phase === 'reveal'
    return (<>
      <section className="card">
        <div className="gmeta"><span>Card {i + 1} of {round.cards.length}{mode === 'practice' ? ' · practice' : ''}</span><span className="row"><Clock size={14} /> {Math.ceil(left)}s</span><span>Score {total}</span><button className="ghost row" onClick={exit} aria-label="Exit game"><LogOut size={14} />Exit</button></div>
        <div className={'gtimer' + (left < 6 && !reveal ? ' low' : '')} style={{ margin: '8px 0 14px' }} role="progressbar" aria-label="Time left" aria-valuemin={0} aria-valuemax={secs} aria-valuenow={Math.ceil(left)}><i style={{ width: (reveal ? 0 : (left / secs) * 100) + '%' }} /></div>
        <Message card={card} />
        {!reveal ? (<div className="gbtns" style={{ marginTop: 14 }}>
          <button className="gbtn scam" onClick={() => answer('scam')}><ShieldAlert size={20} />Scam <kbd>S</kbd></button>
          <button className="gbtn legit" onClick={() => answer('legit')}><ShieldCheck size={20} />Legit <kbd>L</kbd></button>
        </div>) : (<div style={{ marginTop: 14 }}>
          <div className={'gverdict ' + (pick.correct ? 'ok' : 'bad')} role="status">
            {pick.correct ? <Check size={20} /> : <X size={20} />}
            {pick.timedOut ? "Time's up" : pick.correct ? 'Correct' : 'Not quite'}: this is {card.verdict === 'scam' ? 'a scam' : 'legit'}
            <small>+{pick.points} points</small>
          </div>
          <Explain card={card} />
          <div style={{ marginTop: 14 }}><button className="btn" autoFocus onClick={next}>{i + 1 < round.cards.length ? 'Next card' : 'See my result'}</button></div>
        </div>)}
      </section>
      <p className="disc wide">{round.disclaimer}</p>
    </>)
  }

  // done
  return (<>
    <section className="card">{header}
      <p className="gscore">{right}/{round.cards.length} · {rank(right)}</p>
      <div className="ggrid" aria-label={`${right} correct out of ${round.cards.length}`}>{gridOf(picks)}</div>
      <div className="gstats">
        <div><span>Points</span><b>{total}</b></div>
        <div><span>Streak</span><b>{saved.streak || 0} day{saved.streak === 1 ? '' : 's'}</b></div>
        <div><span>Best streak</span><b>{saved.best || 0}</b></div>
      </div>
      {mode === 'practice' && <p style={{ color: 'var(--soft)', margin: '4px 0 8px' }}>Practice rounds do not count towards your streak.</p>}
      {err && <em className="apierr">{err}</em>}
      <div className="row" style={{ flexWrap: 'wrap' }}>
        <button className="btn row" onClick={share}><Share2 size={16} />{copied ? 'Copied!' : 'Share result'}</button>
        <button className="ghost row" disabled={busy} onClick={() => start('practice')}><RotateCcw size={16} />Practice again</button>
        <button className="ghost" onClick={() => setPhase('intro')}>Back</button>
      </div>
    </section>
    <section className="card">
      <h2>Review</h2>
      {round.cards.map((c, k) => (<div className="greview" key={c.id}>
        <div className="row" style={{ flexWrap: 'wrap', gap: 6 }}><span className={'gpill ' + c.verdict}>{c.verdict}</span><span className="gpill">{c.channel}</span>
          <small style={{ color: 'var(--soft)' }}>{picks[k]?.correct ? 'You got it' : picks[k]?.timedOut ? 'Time ran out' : 'You missed it'}</small></div>
        <p className="gmsg" style={{ margin: '8px 0' }}>{c.text}</p>
        <Explain card={c} />
      </div>))}
    </section>
    <p className="disc wide">{round.disclaimer} {DISCLAIMER}</p>
  </>)
}
