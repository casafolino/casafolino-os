"use client";
// Composer F8 — Rispondi / Inoltra via gateway (console_reply / console_send).
// Kill-switch False → crea BOZZA in outbox (nessun invio reale). operator_uid dalla sessione.
import { useState } from "react";
import { BP } from "@/lib/basePath";

export type ComposerTarget = { id: number; subject: string; senderEmail: string; senderName: string };

export function Composer({ mode, target, onClose }: { mode: "reply" | "forward"; target: ComposerTarget; onClose: () => void }) {
  const cleanSubj = (target.subject || "").replace(/^(re|fwd|fw):\s*/i, "");
  const [to, setTo] = useState(mode === "reply" ? target.senderEmail : "");
  const [subject, setSubject] = useState((mode === "reply" ? "Re: " : "Fwd: ") + cleanSubj);
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function submit() {
    setBusy(true); setMsg(null);
    const url = mode === "reply" ? `${BP}/api/console/reply` : `${BP}/api/console/send`;
    const payload = mode === "reply"
      ? { messageId: target.id, body, subject }
      : { to, subject, body, sourceMessageId: target.id };
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

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", display: "grid", placeItems: "center", zIndex: 70 }} onClick={onClose}>
      <div className="card" style={{ padding: 18, width: 560, maxWidth: "92vw", display: "flex", flexDirection: "column", gap: 10 }} onClick={(e) => e.stopPropagation()}>
        <div style={{ fontWeight: 600 }}>{mode === "reply" ? "Rispondi" : "Inoltra"} · F8</div>
        <label style={{ fontSize: 12 }}>A
          <input value={to} onChange={(e) => setTo(e.target.value)} readOnly={mode === "reply"} style={{ ...inp, background: mode === "reply" ? "var(--panel-2)" : "#fff" }} />
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
            <button className="btn pri" disabled={busy || !body.trim() || !to.trim()} onClick={submit}>{busy ? "…" : mode === "reply" ? "Rispondi" : "Inoltra"}</button>
          </div>
        </div>
      </div>
    </div>
  );
}

const inp: React.CSSProperties = { width: "100%", marginTop: 3, padding: "8px 10px", border: "1px solid var(--line)", borderRadius: 7, fontSize: 13 };
