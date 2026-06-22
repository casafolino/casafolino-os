"use client";
// Brief 10 — Invia documenti: wizard che invia SOLO materiali dalla libreria curata via outbound
// (rail+kill-switch+audit, safe-attach anti-exfiltration nel gateway). Manager-only.
import { useEffect, useState } from "react";
import { getLibrary, sendDocuments, type LibraryDoc } from "@/lib/documents";

export function SendDocumentsButton({ leadId, partnerId, small = false, label = "Invia documenti" }: {
  leadId?: number | null; partnerId?: number | null; small?: boolean; label?: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className={small ? "btn-mini" : "btn-secondary"} onClick={() => setOpen(true)}>{label}</button>
      {open ? <Panel leadId={leadId} partnerId={partnerId} onClose={() => setOpen(false)} /> : null}
    </>
  );
}

function Panel({ leadId, partnerId, onClose }: { leadId?: number | null; partnerId?: number | null; onClose: () => void }) {
  const [docs, setDocs] = useState<LibraryDoc[]>([]);
  const [sel, setSel] = useState<Set<number>>(new Set());
  const [subject, setSubject] = useState("Documenti CasaFolino");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  useEffect(() => { getLibrary().then((d) => { if (Array.isArray(d)) setDocs(d); }).catch(() => {}); }, []);

  function toggle(id: number) { setSel((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; }); }
  function onSubject(e: React.ChangeEvent<HTMLInputElement>) { setSubject(e.target.value); }

  async function send() {
    setBusy(true); setErr(null);
    try {
      const r = await sendDocuments({ leadId: leadId ?? undefined, partnerId: partnerId ?? undefined, materialIds: [...sel], subject });
      if (r.ok) setDone(r.state === "sent" ? `Inviato a ${r.to}` : `In bozza (${r.state})`); else setErr(r.message ?? "errore");
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: 16 }}>
      <div className="card" onClick={(e) => e.stopPropagation()} style={{ width: "min(480px,100%)", maxHeight: "90vh", overflow: "auto", padding: 18, display: "flex", flexDirection: "column", gap: 12 }}>
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontWeight: 700, fontSize: 16 }}>Invia documenti</div>
          <button className="btn-mini" onClick={onClose}>✕</button>
        </div>
        {err ? <div style={{ color: "var(--danger)", fontSize: 13 }}>{err}</div> : null}
        {done ? (
          <>
            <div className="chip" style={{ background: "var(--ok-t)", color: "var(--ok)", alignSelf: "flex-start" }}>{done} ✓</div>
            <button className="btn-primary" onClick={onClose} style={{ alignSelf: "flex-end" }}>Chiudi</button>
          </>
        ) : (
          <>
            <div>
              <label className="muted" style={{ fontSize: 11 }}>Oggetto</label>
              <input value={subject} onChange={onSubject} style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--line)", fontSize: 13 }} />
            </div>
            <div>
              <label className="muted" style={{ fontSize: 11 }}>Libreria curata (solo materiali approvati)</label>
              {docs.length === 0 ? <div className="muted" style={{ fontSize: 12 }}>Nessun materiale in libreria.</div> : (
                <div className="card" style={{ marginTop: 4, padding: 4, maxHeight: 240, overflow: "auto" }}>
                  {docs.map((d) => (
                    <div key={d.id} onClick={() => toggle(d.id)} className="hover-row" style={{ padding: "6px 8px", cursor: "pointer", borderRadius: 6, display: "flex", gap: 8, alignItems: "center" }}>
                      <input type="checkbox" readOnly checked={sel.has(d.id)} />
                      <span style={{ fontSize: 13 }}>{d.name} <span className="muted">· {d.category} · {d.language}</span></span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <button className="btn-primary" onClick={send} disabled={busy || sel.size === 0} style={{ alignSelf: "flex-end" }}>
              {busy ? "Invio…" : `Invia ${sel.size || ""}`}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
