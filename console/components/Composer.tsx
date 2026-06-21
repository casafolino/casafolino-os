"use client";
// Composer — Rispondi / Inoltra / Nuova mail via gateway (console_reply / console_send).
// Kill-switch False → crea BOZZA in outbox (nessun invio reale). operator_uid dalla sessione.
// "Nuova mail" (compose da zero): scegli la casella mittente (accountId), destinatario libero.
import { useState } from "react";
import { BP } from "@/lib/basePath";

export type ComposerTarget = { id: number; subject: string; senderEmail: string; senderName: string };
export type ComposerMode = "reply" | "forward" | "new";
export type Account = { id: number; name: string; email: string };

export function Composer({ mode, target, accounts = [], onClose }: {
  mode: ComposerMode;
  target: ComposerTarget;
  accounts?: Account[];
  onClose: () => void;
}) {
  const cleanSubj = (target.subject || "").replace(/^(re|fwd|fw):\s*/i, "");
  const [to, setTo] = useState(mode === "reply" ? target.senderEmail : "");
  const [subject, setSubject] = useState(mode === "reply" ? "Re: " + cleanSubj : mode === "forward" ? "Fwd: " + cleanSubj : "");
  const [body, setBody] = useState("");
  const [accountId, setAccountId] = useState<number>(accounts[0]?.id ?? 0);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const title = mode === "reply" ? "Rispondi · R" : mode === "forward" ? "Inoltra" : "Nuova mail";

  async function submit() {
    setBusy(true); setMsg(null);
    const url = mode === "reply" ? `${BP}/api/console/reply` : `${BP}/api/console/send`;
    const payload = mode === "reply"
      ? { messageId: target.id, body, subject }
      : mode === "forward"
        ? { to, subject, body, sourceMessageId: target.id }
        : { to, subject, body, accountId }; // compose da zero
    const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const j = await res.json().catch(() => ({ ok: false, message: "errore rete" }));
    setBusy(false);
    if (j.ok || j.draft_id) {
      const st = j.state === "draft" ? "bozza creata (invio reale disattivo)" : j.state === "sent" ? "inviata" : "ok";
      setMsg(`✓ ${st}`);
      setTimeout(onClose, 1300);
    } else {
      setMsg(`✕ ${j.message || j.blocked || "non riuscito"}`);
    }
  }

  const canSend = !busy && body.trim() && to.trim() && (mode !== "new" || accountId > 0);

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", display: "grid", placeItems: "center", zIndex: 70 }} onClick={onClose}>
      <div className="card" style={{ padding: 18, width: 560, maxWidth: "92vw", display: "flex", flexDirection: "column", gap: 10 }} onClick={(e) => e.stopPropagation()}>
        <div style={{ fontWeight: 600 }}>{title}</div>
        {mode === "new" ? (
          <label style={{ fontSize: 12 }}>Da (casella)
            <select value={accountId} onChange={(e) => setAccountId(Number(e.target.value))} style={inp}>
              {accounts.length === 0 ? <option value={0}>nessuna casella</option> : null}
              {accounts.map((a) => <option key={a.id} value={a.id}>{a.name} · {a.email}</option>)}
            </select>
          </label>
        ) : null}
        <label style={{ fontSize: 12 }}>A
          <input value={to} onChange={(e) => setTo(e.target.value)} readOnly={mode === "reply"} placeholder={mode === "new" ? "destinatario@…" : undefined} style={{ ...inp, background: mode === "reply" ? "var(--panel-2)" : "#fff" }} />
        </label>
        <label style={{ fontSize: 12 }}>Oggetto
          <input value={subject} onChange={(e) => setSubject(e.target.value)} style={inp} />
        </label>
        <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={9} placeholder="Scrivi il messaggio…" style={{ ...inp, resize: "vertical", fontFamily: "inherit" }} />
        {msg ? <div style={{ fontSize: 13, color: msg.startsWith("✓") ? "var(--ok)" : "var(--danger)" }}>{msg}</div> : null}
        <div className="row" style={{ gap: 8, justifyContent: "space-between", alignItems: "center" }}>
          <span className="muted" style={{ fontSize: 11 }}>Invio reale disattivo (kill-switch) → salva bozza.</span>
          <div className="row" style={{ gap: 8 }}>
            <button className="btn" onClick={onClose}>Annulla</button>
            <button className="btn pri" disabled={!canSend} onClick={submit}>{busy ? "…" : title.split(" ")[0]}</button>
          </div>
        </div>
      </div>
    </div>
  );
}

const inp: React.CSSProperties = { width: "100%", marginTop: 3, padding: "8px 10px", border: "1px solid var(--line)", borderRadius: 7, fontSize: 13 };
