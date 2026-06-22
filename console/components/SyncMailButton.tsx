"use client";
// Brief 21 — "Sincronizza mail": recupera le mail vecchie (pre-cutoff) del contatto on-demand.
// Click → spinner → "Trovate N mail" → onDone (ricarica timeline). Manager-only (gateway).
import { useState } from "react";
import { BP } from "@/lib/basePath";

export function SyncMailButton({ partnerId, onDone }: { partnerId: number; onDone?: () => void }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function run() {
    setBusy(true); setMsg(null);
    try {
      const res = await fetch(`${BP}/api/console/partner/sync-mail`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ partnerId }),
      });
      const r = (await res.json()) as { ok?: boolean; newCount?: number; message?: string };
      if (r.ok) {
        setMsg(r.newCount ? `Trovate ${r.newCount} mail` : "Nessuna mail nuova");
        if (r.newCount && onDone) onDone();
      } else setMsg(r.message ?? "errore");
    } catch (e) { setMsg((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <span className="row" style={{ gap: 8, alignItems: "center" }}>
      <button className="btn-mini" onClick={run} disabled={busy}>{busy ? "Sincronizzo…" : "↻ Sincronizza mail"}</button>
      {msg ? <span className="muted" style={{ fontSize: 11 }}>{msg}</span> : null}
    </span>
  );
}
