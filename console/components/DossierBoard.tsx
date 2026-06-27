"use client";
// Pagina Dossier curata: SOLO clienti pinnati (is_dossier), raggruppati per cartella.
// Niente anagrafica completa. Click su una card → fascicolo-cliente esistente (/partner/[id]).
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { BP } from "@/lib/basePath";
import {
  getDossierList, getFolders, toggleDossier, createFolder, renameFolder,
  type DossierGroup, type DossierFolder, type DossierCard,
} from "@/lib/dossier";

function initials(name: string): string {
  return (name || "").split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase()).join("");
}

export function DossierBoard() {
  const [groups, setGroups] = useState<DossierGroup[]>([]);
  const [folders, setFolders] = useState<DossierFolder[]>([]);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [newFolder, setNewFolder] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async (q?: string) => {
    setLoading(true); setErr(null);
    try {
      const [l, f] = await Promise.all([getDossierList(q ?? query), getFolders()]);
      setGroups(l.ok ? l.groups : []); setTotal(l.ok ? l.total : 0);
      setFolders(f.ok ? f.folders : []);
    } catch (e) { setErr((e as Error).message); } finally { setLoading(false); }
  }, [query]);

  useEffect(() => { load(""); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

  async function onCreateFolder() {
    const nm = newFolder.trim();
    if (!nm) return;
    setBusy(true); setErr(null);
    try { const r = await createFolder(nm); if (!r.ok) setErr(r.message || "Errore"); setNewFolder(""); await load(); }
    catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  async function onRenameFolder(id: number, current: string) {
    const nm = prompt("Rinomina cartella", current);
    if (!nm || !nm.trim() || nm.trim() === current) return;
    setBusy(true);
    try { await renameFolder(id, nm.trim()); await load(); } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  async function onMove(card: DossierCard, folderId: number | "") {
    setBusy(true);
    try { await toggleDossier({ partner_id: card.id, is_dossier: true, folder_id: folderId === "" ? null : Number(folderId) }); await load(); }
    catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  async function onUnpin(card: DossierCard) {
    if (!confirm(`Togliere ${card.name} dai Dossier?`)) return;
    setBusy(true);
    try { await toggleDossier({ partner_id: card.id, is_dossier: false }); await load(); }
    catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  const nonEmpty = groups.filter((g) => g.partners.length > 0);

  return (
    <div>
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 14, alignItems: "center" }}>
        <h2 style={{ fontSize: 19 }}>Dossier <span className="muted" style={{ fontSize: 13, fontWeight: 400 }}>· {total} curati</span></h2>
        <span className="muted" style={{ fontSize: 12 }}>solo clienti pinnati · per cartella</span>
      </div>

      {/* ricerca tra i soli dossier + gestione cartelle */}
      <div className="row" style={{ gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
        <input value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") load(query); }}
          placeholder="Cerca tra i dossier…" style={{ flex: 1, maxWidth: 320, fontSize: 13, padding: "8px 11px", border: "1px solid var(--line-2)", borderRadius: "var(--r-md)", background: "var(--paper)", color: "var(--ink)" }} />
        <button className="btn pri" disabled={busy} onClick={() => load(query)}>Cerca</button>
        <span style={{ flex: 1 }} />
        <input value={newFolder} onChange={(e) => setNewFolder(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") onCreateFolder(); }}
          placeholder="Nuova cartella…" style={{ width: 160, fontSize: 13, padding: "8px 11px", border: "1px solid var(--line-2)", borderRadius: "var(--r-md)", background: "var(--paper)", color: "var(--ink)" }} />
        <button className="btn" disabled={busy || !newFolder.trim()} onClick={onCreateFolder}>+ Cartella</button>
      </div>
      {err ? <div style={{ fontSize: 12, color: "var(--danger)", marginBottom: 8 }}>{err}</div> : null}

      {loading ? (
        <div className="muted" style={{ padding: 16, fontSize: 13 }}>Carico dossier…</div>
      ) : total === 0 ? (
        <div className="card" style={{ padding: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>Nessun dossier ancora.</div>
          <div className="muted" style={{ fontSize: 13 }}>Apri il fascicolo di un cliente e premi <b>📌 Aggiungi ai Dossier</b> per iniziare a curare i tuoi clienti-chiave.</div>
        </div>
      ) : (
        nonEmpty.map((g) => (
          <div key={String(g.id)} style={{ marginBottom: 18 }}>
            <div className="row" style={{ gap: 8, alignItems: "center", marginBottom: 8 }}>
              <h3 className="sec-title" style={{ margin: 0 }}>{g.name}</h3>
              <span className="chip" style={{ background: "var(--accent-t)", color: "var(--accent)" }}>{g.partners.length}</span>
              {g.id !== false ? <button className="btn" style={{ fontSize: 11, padding: "2px 6px" }} disabled={busy} onClick={() => onRenameFolder(g.id as number, g.name)}>✎ rinomina</button> : null}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              {g.partners.map((p) => (
                <div key={p.id} className="card" style={{ padding: "11px 13px" }}>
                  <div className="row" style={{ gap: 10 }}>
                    <div style={{ width: 34, height: 34, borderRadius: "50%", background: "var(--panel-2)", color: "var(--muted)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 600, fontSize: 12, flexShrink: 0 }}>{initials(p.name)}</div>
                    <div className="grow" style={{ minWidth: 0 }}>
                      <Link href={`/partner/${p.id}`} style={{ fontWeight: 600, fontSize: 13, color: "var(--accent)", textDecoration: "none" }} className="ell">{p.name} →</Link>
                      <div className="muted ell" style={{ fontSize: 11 }}>{[p.city, p.country].filter(Boolean).join(" · ") || p.email || "—"}</div>
                    </div>
                  </div>
                  <div className="row" style={{ gap: 6, marginTop: 8, alignItems: "center" }}>
                    <select value={p.folder_id === false ? "" : p.folder_id} disabled={busy} onChange={(e) => onMove(p, e.target.value as number | "")}
                      style={{ flex: 1, fontSize: 11, padding: "4px 6px", borderRadius: 6, border: "1px solid var(--line)" }}>
                      <option value="">Senza cartella</option>
                      {folders.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
                    </select>
                    <button className="btn" style={{ fontSize: 11, padding: "3px 7px" }} disabled={busy} title="Togli dai Dossier" onClick={() => onUnpin(p)}>📌✕</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))
      )}
      <div className="muted" style={{ fontSize: 11, marginTop: 10 }}>
        <Link href={`${BP}/inbox`} style={{ color: "var(--muted)" }}>← Inbox</Link>
      </div>
    </div>
  );
}
