import { Link } from "react-router-dom";
import { Gamepad2, UserRound, ArrowRight } from "lucide-react";
import { useFinance } from "../context/FinanceContext";
import { DISCLAIMER } from "./Dashboard";

const STEPS = [
  ["Set up your profile", "Tell Finbot your income and spending so its guidance fits you."],
  ["Ask and explore", "Chat with the coach, run a simulation or check your budget."],
  ["Plan and learn", "Set goals, track expenses, read the news and play the scam game."],
];

export default function Home() {
  const { profile, openProfile } = useFinance();
  const name = profile?.fullName?.split(" ")[0];
  return (
    <>
      <section className="card hero">
        <p className="eyebrow">{name ? `Welcome back, ${name}` : "Hello there"}</p>
        <h1>Welcome to Finbot</h1>
        <p className="lead">
          Your friendly AI financial coach. Build a budget, set goals, see how your money could grow and learn to
          spot scams, all in one place.
        </p>
        <div className="herobtns">
          {profile ? (
            <>
              <Link to="/dashboard" className="btn lg">Go to dashboard <ArrowRight size={16} /></Link>
              <button className="ghost lg" onClick={() => openProfile()}><UserRound size={16} /> Edit my profile</button>
            </>
          ) : (
            <>
              <button className="btn lg" onClick={() => openProfile("/dashboard")}><UserRound size={16} /> Set up my profile</button>
              <Link to="/dashboard" className="ghost lg">Go to dashboard</Link>
            </>
          )}
          <Link to="/play" className="ghost lg"><Gamepad2 size={16} /> Play Scam or Legit</Link>
        </div>
        {!profile && <small className="hint">It takes about a minute. Your details stay on your own computer.</small>}
      </section>


      <h2 className="sectitle">How it works</h2>
      <section className="steps">
        {STEPS.map(([t, d], i) => (
          <div className="card step" key={t}>
            <span className="stepno">{i + 1}</span>
            <strong>{t}</strong>
            <span>{d}</span>
          </div>
        ))}
      </section>
      <p className="disc wide">{DISCLAIMER}</p>
    </>
  );
}
