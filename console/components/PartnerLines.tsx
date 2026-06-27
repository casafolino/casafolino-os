"use client";
// WI-A — Faldone cliente livello 1: le LINEE di prodotto del cliente (lente su nativi).
// Sostituisce il box doppione "Dossier · + Crea dossier": un solo concetto di dossier nel fascicolo.
import { useEffect, useState } from "react";
import Link from "next/link";
import { getPartnerLines, type PartnerLine, type LineCatalogItem } from "@/lib/lines";

const STATE_STYLE: Record<string, React.CSSProperties> = {
  attivo: { background: "var(--ok-t)", color: "var(--ok)" },
  esplorazione: { background: "var(--warn-t)", color: "var(--warn)" },
  chiuso: { background: "var(--panel-2)", color: "var(--muted)" },
};
const STATE_LABEL: Record<string, string> = { attivo: "attivo", esplorazione: "esplorazione", chiuso: "chiuso" };

export function PartnerLines({ partnerId }: { partnerId: number }) {
  const [lines, setLines] = useState<PartnerLine[]>([]);
  const [catalog, setCatalog] = useState<LineCatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    let alive = true;
    getPartnerLines(partnerId)
      .then((r) => { if (alive && r.ok) { setLines(r.lines); setCatalog(r.catalog || []); } })
      .catch(() => {})
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [partnerId]);

  const presentIds = new Set(lines.map((l) => l.category_id));
  const addable = catalog.filter((c) => !presentIds.has(c.category_id));

  return (
    <div className="card" style={{ padding: "14px 16px" }}>
      <div className="row" style={{ justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <p className="sec-title" style={{ margin: 0 }}>Linee di prodotto</p>
        <div className="row" style={{ gap: 6, position: "relative" }}>
          <button className="btn" disabled={!addable.length} onClick={() => setAdding((a) => !a)}>+ Nuova linea</button>
          {adding ? (
            <div className="card" style={{ position: "absolute", top: "100%", right: 0, marginTop: 4, zIndex: 30, padding: 8, width: 240, maxHeight: 260, overflowY: "auto", boxShadow: "0 6px 20px rgba(0,0,0,.15)" }}>
              {addable.map((c) => (
                <Link key={c.category_id} href={`/partner/${partnerId}/line/${c.category_id}`}
                  className="hover-row" style={{ display: "block", padding: "6px 8px", borderRadius: 6, fontSize: 13, textDecoration: "none", color: "var(--ink)" }}>
                  {c.name}
                </Link>
              ))}
            </div>
          ) : null}
        </div>
      </div>

      {loading ? (
        <div className="muted" style={{ fontSize: 13 }}>Carico linee…</div>
      ) : lines.length === 0 ? (
        <div className="muted" style={{ fontSize: 13 }}>Nessuna linea ancora. Apri una linea con “+ Nuova linea” (campionatura o preventivo).</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {lines.map((l) => (
            <Link key={l.category_id} href={`/partner/${partnerId}/line/${l.category_id}`}
              className="hover-row" style={{ display: "block", padding: "10px 12px", borderRadius: 8, border: "1px solid var(--line)", textDecoration: "none", color: "var(--ink)" }}>
              <div className="row" style={{ gap: 8, alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ fontWeight: 600, fontSize: 13, color: "var(--accent)" }}>{l.name} →</span>
                <span className="chip" style={STATE_STYLE[l.state] || STATE_STYLE.chiuso}>{STATE_LABEL[l.state] || l.state}</span>
              </div>
              <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>
                {l.n_campionature} campionature · {l.n_preventivi} preventivi · {l.n_ordini} ordini
                {l.value ? <> · <b style={{ color: "var(--ink)" }}>€{Math.round(l.value).toLocaleString("it-IT")}</b></> : null}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
