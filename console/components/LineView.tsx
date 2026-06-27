"use client";
// WI-B — Faldone cliente livello 2: dentro una LINEA. Header + metric card + "storia della linea"
// (timeline unificata dei nativi: ordini/preventivi/campionature) + azione campionatura.
// Lente pura: tutto calcolato live, zero duplicazione.
import { useEffect, useState } from "react";
import Link from "next/link";
import { getLineHistory, getPartnerLines, type LineHistoryItem, type PartnerLine } from "@/lib/lines";
import { CampionaturaButton } from "@/components/CampionaturaButton";

const KIND_STYLE: Record<string, React.CSSProperties> = {
  ordine: { background: "var(--ok-t)", color: "var(--ok)" },
  preventivo: { background: "var(--accent-t)", color: "var(--accent)" },
  campionatura: { background: "var(--warn-t)", color: "var(--warn)" },
};

function money(v: number): string { return `€${Math.round(v).toLocaleString("it-IT")}`; }

export function LineView({ partnerId, categoryId }: { partnerId: number; categoryId: number }) {
  const [items, setItems] = useState<LineHistoryItem[]>([]);
  const [head, setHead] = useState<{ partner: string; line: string }>({ partner: "", line: "" });
  const [metric, setMetric] = useState<PartnerLine | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    Promise.all([getLineHistory(partnerId, categoryId), getPartnerLines(partnerId)])
      .then(([h, l]) => {
        if (!alive) return;
        if (h.ok) { setItems(h.items); setHead({ partner: h.partner_name, line: h.category_name }); }
        if (l.ok) setMetric(l.lines.find((x) => x.category_id === categoryId) || null);
      })
      .catch(() => {})
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [partnerId, categoryId]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div><Link href={`/partner/${partnerId}`} className="muted" style={{ fontSize: 12 }}>← Faldone cliente</Link></div>

      <div className="card" style={{ padding: "14px 16px" }}>
        <div className="row" style={{ gap: 8, alignItems: "baseline", flexWrap: "wrap" }}>
          <Link href={`/partner/${partnerId}`} style={{ fontSize: 13, color: "var(--accent)", textDecoration: "none" }}>{head.partner || "Cliente"}</Link>
          <span className="muted">‹</span>
          <h2 style={{ fontSize: 18, margin: 0 }}>{head.line || "Linea"}</h2>
        </div>
        {/* metric card */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10, marginTop: 12 }}>
          <div className="kpi"><div className="k">Campionature</div><div className="v">{metric?.n_campionature ?? 0}</div></div>
          <div className="kpi"><div className="k">Preventivi</div><div className="v">{metric?.n_preventivi ?? 0}</div></div>
          <div className="kpi"><div className="k">Ordini</div><div className="v">{metric?.n_ordini ?? 0}</div></div>
          <div className="kpi"><div className="k">Valore</div><div className="v">{metric?.value ? money(metric.value) : "—"}</div></div>
        </div>
        <div className="row" style={{ gap: 8, marginTop: 12, flexWrap: "wrap" }}>
          <CampionaturaButton partnerId={partnerId} label="Nuova campionatura" />
        </div>
      </div>

      <h3 className="sec-title">Storia della linea</h3>
      <div className="card" style={{ overflow: "hidden" }}>
        {loading ? (
          <div className="muted" style={{ padding: 14, fontSize: 13 }}>Carico storia…</div>
        ) : items.length === 0 ? (
          <div className="muted" style={{ padding: 14, fontSize: 13 }}>Nessun record per questa linea. Avvia una campionatura o un preventivo.</div>
        ) : (
          items.map((it, i) => (
            <div key={`${it.model}-${it.id}`} className="row" style={{ padding: "10px 13px", gap: 10, alignItems: "center", borderBottom: i < items.length - 1 ? "1px solid var(--line)" : "none" }}>
              <span className="chip" style={{ ...(KIND_STYLE[it.kind] || {}), flexShrink: 0, width: 96, justifyContent: "center" }}>{it.kind_label}</span>
              <span style={{ fontWeight: 600, fontSize: 13, flexShrink: 0, width: 130 }}>{it.name}{it.sample_code ? <span className="muted" style={{ fontWeight: 400 }}> · {it.sample_code}</span> : null}</span>
              <span className="muted grow" style={{ fontSize: 12 }}>{(it.date || "").slice(0, 16)}</span>
              <span style={{ fontSize: 13, flexShrink: 0 }}>{it.amount ? money(it.amount) : ""}</span>
              <span className="muted" style={{ fontSize: 11, flexShrink: 0, width: 70, textAlign: "right" }}>{it.state}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
