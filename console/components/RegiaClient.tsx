"use client";
// Regia — 4 KPI (Brief) + lista pipeline piatta ordinata semaforo. Client: fetch on mount,
// click riga → Dossier del cliente. Rossi → gialli (giorni desc) → verdi (attività recente).
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getRegiaKpis, getRegiaPipeline, semaforoColor,
  type RegiaKpis, type RegiaPipelineRow,
} from "@/lib/regia";
import { BP } from "@/lib/basePath";

export function RegiaKpiRow() {
  const [k, setK] = useState<RegiaKpis | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    getRegiaKpis().then((r) => { if (r?.message) setErr(r.message); else setK(r); }).catch((e) => setErr((e as Error).message));
  }, []);

  const cells: { label: string; value: number | string; color?: string }[] = [
    { label: "Attivi", value: k?.attivi ?? "—" },
    { label: "Fermi +3gg", value: k?.fermi3 ?? "—", color: "var(--danger)" },
    { label: "In scadenza oggi", value: k?.scadenzaOggi ?? "—", color: "var(--warn)" },
    { label: "Nuovi lead 7gg", value: k?.nuovi7 ?? "—" },
  ];
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10, marginBottom: 20 }}>
      {cells.map((c) => (
        <div key={c.label} className="kpi">
          <div className="k">{c.label}</div>
          <div className="v" style={c.color && Number(c.value) > 0 ? { color: c.color } : undefined}>{c.value}</div>
        </div>
      ))}
      {err ? <div className="muted" style={{ gridColumn: "1/-1", fontSize: 12, color: "var(--danger)" }}>{err}</div> : null}
    </div>
  );
}

export function RegiaPipelineList() {
  const [rows, setRows] = useState<RegiaPipelineRow[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    getRegiaPipeline(100, 0).then((r) => { if (r?.message) setErr(r.message); else setRows(r.items || []); }).catch((e) => setErr((e as Error).message));
  }, []);

  if (err) return <div className="card" style={{ padding: 12 }}><span className="muted" style={{ fontSize: 12, color: "var(--danger)" }}>{err}</span></div>;
  if (rows === null) return <div className="card" style={{ padding: 12 }}><span className="muted" style={{ fontSize: 12 }}>Carico pipeline…</span></div>;
  if (rows.length === 0) return <div className="card" style={{ padding: 12 }}><span className="muted" style={{ fontSize: 12 }}>Nessuna opportunità attiva.</span></div>;

  return (
    <div className="card" style={{ overflow: "hidden" }}>
      {rows.map((r, i) => (
        <Link
          key={r.leadId}
          href={r.partnerId ? `/partner/${r.partnerId}` : `/lead/${r.leadId}`}
          prefetch={false}
          className="row"
          style={{ padding: "10px 13px", gap: 10, alignItems: "center", borderBottom: i < rows.length - 1 ? "1px solid var(--line)" : "none" }}
        >
          <span className="opdot" title={r.activityState ?? ""} style={{ background: semaforoColor[r.activityState ?? "neutral"] }} />
          <span style={{ fontWeight: 600, width: 200, flexShrink: 0 }} className="ell">{r.company}</span>
          <span className="muted" style={{ fontSize: 12, width: 140, flexShrink: 0 }} title="stage">{r.stage || "—"}</span>
          <span className="muted grow" style={{ fontSize: 12 }}>
            {r.daysInactive != null ? `fermo da ${r.daysInactive} gg` : "nessuna attività"}
          </span>
          <span className="av" title={r.owner} style={{ width: 24, height: 24, fontSize: 10 }}>{r.ownerInitials}</span>
        </Link>
      ))}
    </div>
  );
}

// helper base-path per eventuale uso futuro (mantiene BP importato coerente col resto)
export const regiaHref = (partnerId: number) => `${BP}/partner/${partnerId}`;
