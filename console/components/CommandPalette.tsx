"use client";
// F3 — Command palette (Cmd/Ctrl+K): cerca lead/partner/mail/dossier per nome e salta al record.
// Riusa universalSearch + searchHref (stesso backend della SearchBar). Montata globalmente nel layout
// così è disponibile su tutti i surface. Tastiera: ↑/↓ naviga, Invio apre, Esc chiude.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { universalSearch, searchHref, type SearchResult, type SearchGroup } from "@/lib/pipeline";

type Flat = { type: SearchGroup["type"]; id: number; title: string; subtitle: string };

export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [res, setRes] = useState<SearchResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [sel, setSel] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // hotkey globale Cmd/Ctrl+K
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 0);
    else { setQ(""); setRes(null); setSel(0); }
  }, [open]);

  useEffect(() => {
    if (q.trim().length < 2) { setRes(null); setSel(0); return; }
    const id = setTimeout(async () => {
      setBusy(true);
      try { const r = await universalSearch(q); setRes(r); setSel(0); }
      catch { setRes(null); } finally { setBusy(false); }
    }, 240);
    return () => clearTimeout(id);
  }, [q]);

  const flat: Flat[] = useMemo(
    () => res?.groups.flatMap((g) => g.items.map((it) => ({ type: g.type, id: it.id, title: it.title, subtitle: it.subtitle }))) ?? [],
    [res]
  );

  const go = useCallback((f: Flat) => {
    setOpen(false);
    router.push(searchHref[f.type](f.id));
  }, [router]);

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") { e.preventDefault(); setSel((s) => Math.min(s + 1, flat.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setSel((s) => Math.max(s - 1, 0)); }
    else if (e.key === "Enter" && flat[sel]) { e.preventDefault(); go(flat[sel]); }
  }

  if (!open) return null;

  const groupLabel: Record<SearchGroup["type"], string> = { lead: "Lead", partner: "Contatti", mail: "Mail", dossier: "Dossier" };

  let runningIdx = -1;
  return (
    <div
      onMouseDown={(e) => { if (e.target === e.currentTarget) setOpen(false); }}
      style={{ position: "fixed", inset: 0, zIndex: 100, background: "rgba(20,20,25,0.28)", display: "flex", alignItems: "flex-start", justifyContent: "center", paddingTop: "12vh" }}
    >
      <div className="card" style={{ width: "min(560px, 92vw)", maxHeight: "70vh", overflow: "hidden", boxShadow: "0 12px 40px rgba(0,0,0,0.22)", display: "flex", flexDirection: "column" }}>
        <input
          ref={inputRef}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Cerca lead, contatti, mail, dossier…"
          style={{ border: "none", borderBottom: "1px solid var(--line)", padding: "13px 16px", fontSize: 15, outline: "none", background: "transparent", color: "var(--ink)" }}
        />
        <div style={{ overflow: "auto", padding: 8 }}>
          {busy && !res ? <div className="muted" style={{ fontSize: 12, padding: 8 }}>Cerco…</div> : null}
          {res && flat.length === 0 ? <div className="empty-honest">Nessun risultato per “{res.query}”.</div> : null}
          {!res && !busy ? <div className="muted" style={{ fontSize: 12, padding: 8 }}>Digita almeno 2 caratteri. ↑/↓ per scorrere, Invio per aprire.</div> : null}
          {res?.groups.map((g) => (
            <div key={g.type} style={{ marginBottom: 6 }}>
              <div className="muted" style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: ".04em", padding: "4px 8px" }}>{groupLabel[g.type]}</div>
              {g.items.map((it) => {
                runningIdx += 1;
                const active = runningIdx === sel;
                return (
                  <div
                    key={`${g.type}-${it.id}`}
                    onMouseEnter={() => setSel(flat.findIndex((f) => f.type === g.type && f.id === it.id))}
                    onClick={() => go({ type: g.type, id: it.id, title: it.title, subtitle: it.subtitle })}
                    style={{ display: "block", padding: "8px 10px", borderRadius: 6, cursor: "pointer", background: active ? "var(--accent-t)" : "transparent" }}
                  >
                    <div style={{ fontSize: 13, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{it.title}</div>
                    {it.subtitle ? <div className="muted" style={{ fontSize: 11, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{it.subtitle}</div> : null}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
