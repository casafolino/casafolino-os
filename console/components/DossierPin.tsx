"use client";
// Pin dossier dal fascicolo-cliente: "📌 Aggiungi ai Dossier" / "Togli dai Dossier".
// Toggle is_dossier via metodo gated+auditato; alla pin sceglie/crea la cartella.
import { useEffect, useState } from "react";
import { getFolders, toggleDossier, type DossierFolder } from "@/lib/dossier";

export function DossierPin({ partnerId, initialIsDossier = false, initialFolderId = false }: {
  partnerId: number; initialIsDossier?: boolean; initialFolderId?: number | false;
}) {
  const [isDossier, setIsDossier] = useState(initialIsDossier);
  const [folderId, setFolderId] = useState<number | false>(initialFolderId);
  const [folders, setFolders] = useState<DossierFolder[]>([]);
  const [open, setOpen] = useState(false);
  const [newFolder, setNewFolder] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { getFolders().then((r) => setFolders(r.ok ? r.folders : [])).catch(() => {}); }, []);

  async function add() {
    setBusy(true); setErr(null);
    try {
      const r = await toggleDossier({
        partner_id: partnerId, is_dossier: true,
        folder_id: folderId === false ? null : folderId,
        new_folder_name: newFolder.trim() || undefined,
      });
      if (r.ok) { setIsDossier(true); setFolderId(r.folder_id); setOpen(false); setNewFolder(""); getFolders().then((f) => setFolders(f.ok ? f.folders : [])); }
      else setErr(r.message || "Errore");
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  async function remove() {
    setBusy(true); setErr(null);
    try {
      const r = await toggleDossier({ partner_id: partnerId, is_dossier: false });
      if (r.ok) { setIsDossier(false); setFolderId(false); } else setErr(r.message || "Errore");
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  if (isDossier) {
    const fname = folders.find((f) => f.id === folderId)?.name;
    return (
      <span className="row" style={{ gap: 6, alignItems: "center" }}>
        <span className="chip" style={{ background: "var(--accent-t)", color: "var(--accent)" }} title={fname ? `Cartella: ${fname}` : "Senza cartella"}>📌 Nei Dossier{fname ? ` · ${fname}` : ""}</span>
        <button className="btn" style={{ fontSize: 11 }} disabled={busy} onClick={remove}>Togli</button>
        {err ? <span style={{ fontSize: 11, color: "var(--danger)" }}>{err}</span> : null}
      </span>
    );
  }

  return (
    <span className="row" style={{ gap: 6, alignItems: "center", position: "relative" }}>
      <button className="btn" disabled={busy} onClick={() => setOpen((o) => !o)} title="Marca questo cliente come dossier curato">📌 Aggiungi ai Dossier</button>
      {open ? (
        <div className="card" style={{ position: "absolute", top: "100%", left: 0, marginTop: 4, zIndex: 30, padding: 12, width: 260, display: "flex", flexDirection: "column", gap: 8, boxShadow: "0 6px 20px rgba(0,0,0,.15)" }}>
          <div className="muted" style={{ fontSize: 12 }}>Cartella (opzionale)</div>
          <select value={folderId === false ? "" : folderId} onChange={(e) => setFolderId(e.target.value === "" ? false : Number(e.target.value))}
            style={{ fontSize: 13, padding: "6px 8px", borderRadius: 6, border: "1px solid var(--line)" }}>
            <option value="">Senza cartella</option>
            {folders.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
          </select>
          <input value={newFolder} onChange={(e) => setNewFolder(e.target.value)} placeholder="…o nuova cartella"
            style={{ fontSize: 13, padding: "6px 8px", borderRadius: 6, border: "1px solid var(--line)" }} />
          {err ? <div style={{ fontSize: 11, color: "var(--danger)" }}>{err}</div> : null}
          <div className="row" style={{ gap: 6, justifyContent: "flex-end" }}>
            <button className="btn" style={{ fontSize: 12 }} onClick={() => setOpen(false)}>Annulla</button>
            <button className="btn pri" style={{ fontSize: 12 }} disabled={busy} onClick={add}>Aggiungi</button>
          </div>
        </div>
      ) : null}
    </span>
  );
}
