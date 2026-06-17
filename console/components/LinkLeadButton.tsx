"use client";
// "Collega" → /api/write linkMessageToLead (Odoo). Mock-safe.
import { useState } from "react";
import { Icon } from "./Icons";

export function LinkLeadButton({ messageId, leadId, leadName }: { messageId: number; leadId: number | null; leadName?: string }) {
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!leadId) {
    return <span className="btn" style={{ opacity: 0.6 }} title="Nessun lead da collegare"><Icon name="link" size={14} /> Collega (nessun lead)</span>;
  }

  async function run() {
    setBusy(true); setStatus(null);
    try {
      const res = await fetch("/api/write", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "linkMessageToLead", payload: { messageId, leadId } }) });
      const data = await res.json();
      setStatus(data.ok ? "collegata" : `errore`);
    } catch { setStatus("errore"); } finally { setBusy(false); }
  }

  return (
    <span className="btn" onClick={run} style={{ opacity: busy ? 0.6 : 1 }}>
      <Icon name="link" size={14} /> {status ?? `Collega a ${leadName ?? "lead"}`}
    </span>
  );
}
