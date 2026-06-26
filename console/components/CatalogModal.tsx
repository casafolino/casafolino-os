"use client";
// Fase 2 WI-A — modale "Invia catalogo": lingua → oggetto/corpo precompilati + allegato risolto.
// Revisione manuale obbligatoria prima dell'invio (niente invio cieco). Invio via ir.mail_server.
import { useEffect, useState } from "react";
import { catalogInit, sendCatalog, type CatalogInit } from "@/lib/catalog";

const LANGS = [
  { v: "it", label: "Italiano" },
  { v: "en", label: "English" },
  { v: "es", label: "Español" },
  { v: "de", label: "Deutsch" },
];

function inp(bad = false): React.CSSProperties {
  return { width: "100%", padding: "8px 10px", borderRadius: 8, fontSize: 13,
    border: bad ? "1px solid var(--danger)" : "1px solid var(--line)", background: "var(--paper)" };
}

export function CatalogModal({ partnerId, leadId, onClose }: { partnerId?: number; leadId?: number; onClose: () => void }) {
  const [lang, setLang] = useState("it");
  const [init, setInit] = useState<CatalogInit | null>(null);
  const [accountId, setAccountId] = useState<number>(0);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  async function load(l: string) {
    setBusy(true); setErr(null);
    try {
      const r = await catalogInit({ partnerId, leadId, language: l });
      if (r.message) { setErr(r.message); return; }
      setInit(r); setSubject(r.subject); setBody(r.body);
      setAccountId((prev) => prev || r.accounts[0]?.id || 0);
    } catch (e) { setErr((e as Error).message); }
    finally { setBusy(false); }
  }
  useEffect(() => { load(lang); /* eslint-disable-next-line */ }, [lang]);

  async function send() {
    setBusy(true); setErr(null);
    try {
      const r = await sendCatalog({ partnerId, leadId, accountId, language: lang, subject, body });
      if (r.ok && r.state === "sent") setDone(`Catalogo inviato a ${r.to}${r.attachmentSent ? " (con allegato)" : " (senza allegato)"}.`);
      else if (r.ok && r.state === "draft") setDone(`Bozza creata (invio reale disattivato sul server: kill-switch).${r.attachmentSent ? " Allegato pronto." : ""}`);
      else if (r.blocked) setErr(`Invio bloccato dalle guardie: ${r.blocked} (salvato in bozza).`);
      else setErr(r.message || "Errore invio.");
    } catch (e) { setErr((e as Error).message); }
    finally { setBusy(false); }
  }

  const canSend = !busy && accountId > 0 && !!init?.to && subject.trim().length > 0;

  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1100, padding: 16 }}>
      <div className="card" onClick={(e) => e.stopPropagation()} style={{ width: "min(560px,100%)", maxHeight: "92vh", overflow: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontWeight: 700, fontSize: 16 }}>Invia catalogo</div>
          <button className="btn-mini" onClick={onClose}>✕</button>
        </div>

        <div className="row" style={{ gap: 6 }}>
          {LANGS.map((l) => (
            <button key={l.v} className={lang === l.v ? "btn-secondary" : "btn-mini"} onClick={() => setLang(l.v)}>{l.label}</button>
          ))}
        </div>

        <div className="row" style={{ gap: 10, alignItems: "center" }}>
          <span className="muted" style={{ width: 90, fontSize: 12 }}>A</span>
          <div style={{ ...inp(!init?.to), flex: 1, padding: "7px 10px" }}>
            {init?.to ? <><strong>{init.toName || init.to}</strong> <span className="muted">&lt;{init.to}&gt;</span></> : <span className="muted">nessuna email sul destinatario</span>}
          </div>
        </div>

        <div className="row" style={{ gap: 10, alignItems: "center" }}>
          <span className="muted" style={{ width: 90, fontSize: 12 }}>Casella</span>
          <select value={accountId} onChange={(e) => setAccountId(Number(e.target.value))} style={{ ...inp(accountId === 0), flex: 1 }}>
            {(init?.accounts ?? []).length === 0 ? <option value={0}>nessuna casella configurata</option> : null}
            {(init?.accounts ?? []).map((a) => <option key={a.id} value={a.id}>{a.name} · {a.email}</option>)}
          </select>
        </div>

        <div>
          <span className="muted" style={{ fontSize: 12 }}>Allegato</span>
          {init?.material ? (
            <div style={{ ...inp(), marginTop: 4 }}>📎 {init.material.fileName || init.material.name} <span className="muted">({init.material.language})</span></div>
          ) : (
            <div style={{ ...inp(true), marginTop: 4, color: "var(--warn)" }}>{init?.warn || "Nessun catalogo per questa lingua — invio senza allegato."}</div>
          )}
        </div>

        <div>
          <span className="muted" style={{ fontSize: 12 }}>Oggetto</span>
          <input value={subject} onChange={(e) => setSubject(e.target.value)} style={{ ...inp(!subject.trim()), marginTop: 4 }} />
        </div>
        <div>
          <span className="muted" style={{ fontSize: 12 }}>Corpo (HTML)</span>
          <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={7} style={{ ...inp(), marginTop: 4, resize: "vertical", fontFamily: "inherit" }} />
        </div>

        {done ? <div style={{ fontSize: 13, color: "var(--ok)" }}>{done}</div> : null}
        {err ? <div style={{ fontSize: 13, color: "var(--danger)" }}>{err}</div> : null}

        <div className="row" style={{ justifyContent: "flex-end", gap: 8 }}>
          <button className="btn-mini" onClick={onClose}>Chiudi</button>
          <button className="btn-primary" disabled={!canSend} onClick={send}>{busy ? "…" : "Rivedi e invia"}</button>
        </div>
      </div>
    </div>
  );
}
