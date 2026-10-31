import { useEffect, useState, useCallback } from "react";
import { RefreshCw, ExternalLink } from "lucide-react";
import { getNews } from "../services/newsService";
import { DISCLAIMER } from "./Dashboard";
const FILTERS = [
  ["all", "All"],
  ["rbi", "RBI"],
  ["sebi", "SEBI"],
];
const fmtDate = (iso) =>
  iso
    ? new Date(iso).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : "";
const fmtTime = (iso) =>
  iso
    ? new Date(iso).toLocaleTimeString("en-IN", {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "";
export default function News() {
  const [source, setSource] = useState("all"),
    [data, setData] = useState(null),
    [busy, setBusy] = useState(true),
    [err, setErr] = useState("");
  const load = useCallback(
    async (refresh = false) => {
      setBusy(true);
      setErr("");
      try {
        setData(await getNews(source, refresh));
      } catch {
        setErr("Could not load news. Is the backend running?");
      } finally {
        setBusy(false);
      }
    },
    [source],
  );
  useEffect(() => {
    load();
  }, [load]);
  const srcs = data ? Object.values(data.sources) : [];
  const down = srcs.filter((s) => !s.ok);
  const updated = srcs
    .map((s) => s.fetchedAt)
    .filter(Boolean)
    .sort()
    .pop();
  return (
    <>
      <section className="row between" style={{ flexWrap: "wrap" }}>
        <div>
          <h2 style={{ margin: 0 }}>RBI &amp; SEBI updates</h2>
          <small style={{ color: "var(--soft)" }}>
            Live from the official RBI and SEBI feeds
            {updated ? ` · last fetched ${fmtTime(updated)}` : ""}
          </small>
        </div>
        <button
          className="ghost row"
          onClick={() => load(true)}
          disabled={busy}
          aria-label="Refresh news"
        >
          <RefreshCw size={16} className={busy ? "spin" : ""} />
          Refresh
        </button>
      </section>

      <div className="chips" role="tablist" aria-label="News source">
        {FILTERS.map(([k, label]) => (
          <button
            key={k}
            role="tab"
            aria-selected={source === k}
            className={"chip" + (source === k ? " on" : "")}
            onClick={() => setSource(k)}
          >
            {label}
          </button>
        ))}
      </div>

      {err && (
        <div className="card">
          <em className="apierr">{err}</em>
        </div>
      )}
      {down.map((s) => (
        <div className="card newswarn" key={s.name}>
          {s.name} is not responding right now
          {s.stale ? ". Showing older items." : "."} Try again in a few minutes.
        </div>
      ))}

      <section className="card">
        {busy && !data ? (
          <p style={{ color: "var(--soft)" }}>Loading news…</p>
        ) : data && data.items.length === 0 ? (
          <p style={{ color: "var(--soft)" }}>No news to show right now.</p>
        ) : (
          data?.items.map((a) => (
            <article className="newsrow" key={a.id}>
              <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
                <span className={"tag " + a.sourceKey}>{a.source}</span>
                <span className="tag">{a.type}</span>
                <small style={{ color: "var(--soft)" }}>
                  {fmtDate(a.published)}
                </small>
              </div>
              <a
                href={a.link}
                target="_blank"
                rel="noopener noreferrer"
                className="newstitle"
              >
                {a.title}
                <ExternalLink
                  size={14}
                  className="ext-icon"
                  aria-hidden="true"
                />
              </a>
              {a.summary && <p>{a.summary}</p>}
            </article>
          ))
        )}
      </section>
      <p className="disc wide">
        {data?.disclaimer ||
          "News is shown for general awareness only and is not investment advice."}{" "}
        {DISCLAIMER}
      </p>
    </>
  );
}
