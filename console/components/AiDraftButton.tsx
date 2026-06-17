"use client";
// "Bozza AI" → /api/ai-draft (Groq). Poi "Invia via Odoo" → /api/write (mail.mail, mai SMTP raw).
import { useState } from "react";
import { Icon } from "./Icons";

export function AiDraftButton({ subject, body, partnerName, to }: { subject: string; body: string; partnerName?: string; to?: string }) {
  const [loading, setLoading] = useState(false);
  const [draft, setDraft] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function gen() {
    setLoading(true); setErr(null); setStatus(null);
    try {
      const res = await fetch("/api/ai-draft", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject, body, partnerName }) });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "errore");
      setDraft(data.draft);
    } catch (e) { setErr((e as Error).message); } finally { setLoading(false); }
  }

  async function send() {
    if (!to) { setErr("destinatario non disponibile"); return; }
    setStatus("Invio…"); setErr(null);
    try {
      const res = await fetch("/api/write", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "sendMail", payload: { to, subject: `Re: ${subject}`, bodyHtml: (draft || "").replace(/\n/g, "<br>") } }) });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.message || "errore");
      setStatus(data.message);
    } catch (e) { setErr((e as Error).message); setStatus(null); }
  }

  return (
    <>
      <span className="btn" onClick={gen} style={{ opacity: loading ? 0.6 : 1 }}>
        <Icon name="ai" size={14} /> {loading ? "Genero…" : "Bozza AI"}
      </span>
      {draft != null ? (
        <div style={{ flexBasis: "100%", marginTop: 8 }}>
          <textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={8} style={{
            width: "100%", fontFamily: "var(--font)", fontSize: 13, padding: 10,
            border: "1px solid var(--line-2)", borderRadius: "var(--r-md)", background: "var(--paper)", color: "var(--ink)" }} />
          <div className="row" style={{ gap: 8, marginTop: 6 }}>
            <span className="btn pri" onClick={send}><Icon name="reply" size={14} /> Invia via Odoo</span>
            {status ? <span className="muted" style={{ fontSize: 12 }}>{status}</span> : null}
          </div>
        </div>
      ) : null}
      {err ? <div style={{ flexBasis: "100%", color: "var(--danger)", fontSize: 12, marginTop: 4 }}>Errore: {err}</div> : null}
    </>
  );
}
