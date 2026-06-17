"use client";
// Tab interattivi del Dossier 360 (Campionature/Contatti/Lead/Ordini/Mail/Note) + timeline.
import { useState } from "react";
import { PartnerMailThread } from "./PartnerMailThread";
import { RelationshipTimeline } from "./RelationshipTimeline";
import { EmptyHonest, money, dateLabel } from "./Honest";
import type { DossierView, PartnerBundle, Tone } from "@/lib/types";

const TABS = ["Campionature", "Contatti", "Lead", "Ordini", "Mail", "Note"] as const;
type Tab = (typeof TABS)[number];

function tone(t: Tone): React.CSSProperties {
  switch (t) {
    case "ok": return { background: "var(--ok-t)", color: "var(--ok)" };
    case "warn": return { background: "var(--warn-t)", color: "var(--warn)" };
    case "danger": return { background: "var(--danger-t)", color: "var(--danger)" };
    default: return { background: "var(--panel-2)", color: "var(--muted)" };
  }
}

export function DossierTabs({ dossier, bundle }: { dossier: DossierView; bundle: PartnerBundle | null }) {
  const [tab, setTab] = useState<Tab>("Campionature");

  return (
    <>
      <div className="row" style={{ gap: 16, borderBottom: "1px solid var(--line)", marginBottom: 13 }}>
        {TABS.map((t) => (
          <span key={t} onClick={() => setTab(t)} style={{
            fontSize: 12, fontWeight: 600, paddingBottom: 8, cursor: "pointer",
            color: t === tab ? "var(--ink)" : "var(--muted)",
            borderBottom: t === tab ? "2px solid var(--accent)" : "none",
          }}>{t}</span>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 13 }}>
        <div>{renderPanel(tab, dossier, bundle)}</div>
        <div>{bundle ? <RelationshipTimeline bundle={bundle} limit={8} /> : <EmptyHonest label="Nessuna attività collegata." />}</div>
      </div>
    </>
  );
}

function renderPanel(tab: Tab, d: DossierView, b: PartnerBundle | null) {
  if (tab === "Campionature") {
    return d.samples.length === 0 ? <EmptyHonest label="Nessuna campionatura." actionLabel="Nuova campionatura" /> : (
      <>{d.samples.map((s) => (
        <div key={s.id} className="card" style={{ padding: "10px 12px", marginBottom: 8 }}>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <span style={{ fontWeight: 600, fontSize: 13 }}>{s.name}</span>
            <span className="chip" style={tone(s.statusTone)}>{s.statusLabel}</span>
          </div>
          <div className="muted" style={{ fontSize: 11, marginTop: 3 }}>{s.sub}</div>
        </div>
      ))}</>
    );
  }
  if (tab === "Mail") return <PartnerMailThread messages={b?.mailThread ?? []} title="Mail" />;
  if (tab === "Lead") {
    const leads = b?.leads ?? [];
    return leads.length === 0 ? <EmptyHonest label="Nessun lead nel dossier." actionLabel="Crea lead" /> : (
      <>{leads.map((l) => (
        <div key={l.id} className="card" style={{ padding: "10px 12px", marginBottom: 8 }}>
          <div style={{ fontWeight: 600, fontSize: 13 }}>{l.name}</div>
          <div className="muted" style={{ fontSize: 11 }}>{l.stage ?? "senza stage"} · score {l.score ?? "n/d"}</div>
        </div>
      ))}</>
    );
  }
  if (tab === "Ordini") {
    const orders = b?.orders ?? [];
    return orders.length === 0 ? <EmptyHonest label="Nessun ordine registrato." /> : (
      <>{orders.map((o) => (
        <div key={o.id} className="card row" style={{ padding: "10px 12px", marginBottom: 8, justifyContent: "space-between" }}>
          <span style={{ fontWeight: 600, fontSize: 13 }}>{o.name}{o.isSample ? " · campioni" : ""}</span>
          <span className="muted" style={{ fontSize: 12 }}>{dateLabel(o.dateOrder)} · {money(o.amountTotal, b?.revenue.currency ?? "EUR")}</span>
        </div>
      ))}</>
    );
  }
  if (tab === "Contatti") {
    return b ? (
      <div className="card" style={{ padding: "10px 12px" }}>
        <div style={{ fontWeight: 600, fontSize: 13 }}>{b.partner.name}</div>
        <div className="muted" style={{ fontSize: 12 }}>{b.partner.email ?? "email non disponibile"}{b.partner.phone ? ` · ${b.partner.phone}` : ""}</div>
      </div>
    ) : <EmptyHonest label="Nessun contatto collegato." actionLabel="Aggiungi contatto" />;
  }
  // Note
  return <EmptyHonest label="Nessuna nota nel dossier." actionLabel="Aggiungi nota" />;
}
