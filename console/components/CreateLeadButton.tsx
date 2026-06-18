"use client";
// "Crea lead" → /api/write (Odoo crm.lead.create). Mock-safe.
import { useState } from "react";
import { BP } from "@/lib/basePath";

export function CreateLeadButton({ name, emailFrom, partnerId }: { name: string; emailFrom?: string; partnerId?: number | null }) {
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true); setStatus(null);
    try {
      const res = await fetch(`${BP}/api/write`, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "createLead", payload: { name, emailFrom, partnerId } }) });
      const data = await res.json();
      setStatus(data.ok ? data.message : `errore: ${data.message}`);
    } catch (e) { setStatus(`errore: ${(e as Error).message}`); } finally { setBusy(false); }
  }

  return (
    <span>
      <span className="empty-action" onClick={run} style={{ opacity: busy ? 0.6 : 1 }}>{busy ? "Creo…" : "Crea lead"}</span>
      {status ? <span className="muted" style={{ fontSize: 12, marginLeft: 8 }}>{status}</span> : null}
    </span>
  );
}
