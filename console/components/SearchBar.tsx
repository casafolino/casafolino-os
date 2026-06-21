"use client";
// Ricerca universale (Brief 6): input → dropdown risultati raggruppati (Lead/Contatti/Mail/Dossier),
// ognuno linka al dettaglio. Debounce, niente full-body (perf gestita server-side). Manager-only (gateway).
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { universalSearch, searchHref, type SearchResult } from "@/lib/pipeline";

export function SearchBar() {
  const [q, setQ] = useState("");
  const [res, setRes] = useState<SearchResult | null>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  function onChange(e: React.ChangeEvent<HTMLInputElement>) { setQ(e.target.value); }

  useEffect(() => {
    if (q.trim().length < 2) { setRes(null); return; }
    const t = setTimeout(async () => {
      setBusy(true);
      try { const r = await universalSearch(q); setRes(r); setOpen(true); }
      catch { setRes(null); } finally { setBusy(false); }
    }, 280);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    function onDoc(e: MouseEvent) { if (box.current && !box.current.contains(e.target as Node)) setOpen(false); }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const empty = res && res.groups.length === 0;

  return (
    <div ref={box} style={{ position: "relative", width: 320, maxWidth: "60vw" }}>
      <input value={q} onChange={onChange} onFocus={() => res && setOpen(true)}
        placeholder="Cerca lead, contatti, mail, dossier…"
        style={{ width: "100%", padding: "8px 12px", borderRadius: 8, border: "1px solid var(--line)", fontSize: 13 }} />
      {open && (res || busy) ? (
        <div className="card" style={{ position: "absolute", top: 40, right: 0, width: "min(420px, 90vw)", maxHeight: "60vh", overflow: "auto", zIndex: 50, padding: 8, boxShadow: "0 6px 24px rgba(0,0,0,0.15)" }}>
          {busy ? <div className="muted" style={{ fontSize: 12, padding: 6 }}>Cerco…</div> : null}
          {empty ? <div className="empty-honest">Nessun risultato per “{res!.query}”.</div> : null}
          {res?.groups.map((g) => (
            <div key={g.type} style={{ marginBottom: 8 }}>
              <div className="muted" style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: ".04em", padding: "4px 6px" }}>{g.label}</div>
              {g.items.map((it) => (
                <Link key={`${g.type}-${it.id}`} href={searchHref[g.type](it.id)} onClick={() => setOpen(false)}
                  className="hover-row" style={{ display: "block", padding: "6px 8px", borderRadius: 6 }}>
                  <div style={{ fontSize: 13, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{it.title}</div>
                  {it.subtitle ? <div className="muted" style={{ fontSize: 11, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{it.subtitle}</div> : null}
                </Link>
              ))}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
