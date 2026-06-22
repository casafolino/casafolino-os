"use client";
// Scheda partner "eccezionale" (Brief 19) — STESSO design system di LeadCardClient (Brief 18):
// header + 4 metric card + barra azioni + pannelli con inviti + timeline identica. Solo dati reali
// dal bundle (nessun gateway nuovo). Estetica console: superfici chiare, bordi 0.5px, no gradienti/ombre.
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { SyncMailButton } from "@/components/SyncMailButton";
import type { PartnerBundle } from "@/lib/types";
import { moneyCompact, money, dateLabel } from "@/components/Honest";
import { operatorLabel } from "@/lib/theme";
import { Composer, type Account } from "@/components/Composer";
import { CampionaturaButton } from "@/components/CampionaturaButton";
import { SendDocumentsButton } from "@/components/SendDocumentsButton";
import { QuickCreateDossier, QuickCreateLead } from "@/components/QuickCreate";
import { LeadTimeline } from "@/components/LeadTimeline";
import type { LeadTimelineItem } from "@/lib/lead";

function initials(name: string): string {
  return (name || "").split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase() ?? "").join("") || "·";
}

// timeline IDENTICA alla lead: mappa il bundle (mail già free-domain guarded B16 + ordini/campioni)
// in LeadTimelineItem e usa lo STESSO componente LeadTimeline.
function buildTimeline(b: PartnerBundle): LeadTimelineItem[] {
  const items: LeadTimelineItem[] = [];
  for (const m of b.mailThread) {
    items.push({ type: "mail", date: m.date, title: m.subject || "(senza oggetto)", subtitle: m.senderName || m.senderEmail || "", direction: m.direction });
  }
  for (const o of b.orders) {
    items.push({
      type: o.isSample ? "campionatura" : "note",
      date: o.dateOrder,
      title: o.isSample ? `Campionatura ${o.name}` : `Ordine ${o.name}`,
      subtitle: money(o.amountTotal, b.revenue.currency),
    });
  }
  return items.sort((a, z) => (z.date || "").localeCompare(a.date || ""));
}

export function PartnerClient({ bundle, accounts }: { bundle: PartnerBundle; accounts: Account[] }) {
  const router = useRouter();
  const [composeOpen, setComposeOpen] = useState(false);
  const p = bundle.partner;
  const lead0 = bundle.leads[0] ?? null;
  const dossier0 = bundle.dossiers[0] ?? null;

  const place = [p.city, p.country].filter(Boolean).join(", ");
  const subtitle = [p.isCompany ? "Azienda" : p.role, place].filter(Boolean).join("  ·  ");
  const ownerName = lead0 ? operatorLabel[lead0.operator] : "";
  const composeTarget = { id: 0, subject: "", senderEmail: p.email ?? "", senderName: p.name };
  const tl = buildTimeline(bundle);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* ── HEADER ── */}
      <div className="card" style={{ padding: "18px 20px" }}>
        <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 22, fontWeight: 700, lineHeight: 1.15, letterSpacing: "-0.01em" }}>{p.name}</div>
            <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>{subtitle || (p.email ?? "")}</div>
          </div>
          {ownerName ? (
            <div className="row" style={{ gap: 9, alignItems: "center", flexShrink: 0 }}>
              <span style={{ width: 32, height: 32, borderRadius: 999, background: "var(--accent-t)", color: "var(--accent)", display: "inline-flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 12 }}>{initials(ownerName)}</span>
              <div style={{ textAlign: "right" }}>
                <div className="muted" style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: ".06em" }}>Owner</div>
                <div style={{ fontSize: 13, fontWeight: 600 }}>{ownerName}</div>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {/* ── 4 METRICHE ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <Metric label="Fatturato" value={bundle.revenue.total > 0 ? money(bundle.revenue.total, bundle.revenue.currency) : "—"} />
        <Metric label="Ordini" value={String(bundle.revenue.orderCount)} foot={bundle.orders.some((o) => o.isSample) ? "include campioni" : undefined} />
        <Metric label="Mail" value={String(bundle.mailThread.length)} foot={bundle.signals.unreadMail ? `${bundle.signals.unreadMail} non lette` : "tutte lette"} footColor={bundle.signals.unreadMail ? "var(--warn)" : undefined} />
        <Metric label="Lead" value={String(bundle.leads.length)} foot={lead0 ? (lead0.stage ?? "") : "nessuno"} />
      </div>

      {/* ── BARRA AZIONI (tutte vive) ── */}
      <div className="card" style={{ padding: 12 }}>
        <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
          <button className="btn-primary" onClick={() => setComposeOpen(true)} disabled={!p.email}>✉ Scrivi mail</button>
          <CampionaturaButton partnerId={p.id} leadId={lead0?.id ?? null} label="Campionatura" />
          <SendDocumentsButton partnerId={p.id} leadId={lead0?.id ?? null} label="Documenti" />
          <QuickCreateDossier partnerId={p.id} defaultName={`Dossier ${p.name}`} small={false} label="Dossier" />
          <QuickCreateLead partnerId={p.id} small={false} label="Crea lead" />
        </div>
      </div>

      {/* ── PANNELLI: Contatto + Lead/Pipeline ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <div className="card" style={{ padding: 16 }}>
          <p className="sec-title">Contatto</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <Row label="Nome" v={p.name} />
            {p.role ? <Row label="Ruolo" v={p.role} /> : null}
            <Row label="Email" v={p.email || <span className="muted">—</span>} />
            {p.phone ? <Row label="Telefono" v={p.phone} /> : null}
            {place ? <Row label="Luogo" v={place} /> : null}
          </div>
        </div>

        <div className="card" style={{ padding: 16 }}>
          <p className="sec-title">Pipeline</p>
          {bundle.leads.length ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {bundle.leads.slice(0, 4).map((l) => (
                <Link key={l.id} href={`/lead/${l.id}`} className="hover-row" style={{ display: "block", padding: "8px 10px", borderRadius: 6, border: "1px solid var(--line)" }}>
                  <div className="row" style={{ justifyContent: "space-between" }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{l.name}</span>
                    <span className="muted" style={{ fontSize: 12 }}>{l.expectedRevenue != null ? moneyCompact(l.expectedRevenue) : "da stimare"}</span>
                  </div>
                  <div className="muted" style={{ fontSize: 11 }}>{l.stage ?? "senza stage"} · apri →</div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="empty-honest" style={{ justifyContent: "space-between" }}>
              <span>Nessun lead.</span>
              <QuickCreateLead partnerId={p.id} label="+ Crea lead" />
            </div>
          )}
        </div>
      </div>

      {/* ── PANNELLI: Dossier + Ordini ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <div className="card" style={{ padding: 16 }}>
          <p className="sec-title">Dossier</p>
          {dossier0 ? (
            <Link href="/dossier" className="hover-row" style={{ display: "block", padding: "8px 10px", borderRadius: 6, border: "1px solid var(--line)" }}>
              <div style={{ fontWeight: 600, fontSize: 13, color: "var(--accent)" }}>{dossier0.name} →</div>
              <div className="muted" style={{ fontSize: 11 }}>{dossier0.status ?? ""}{dossier0.valueEstimate != null ? ` · ${moneyCompact(dossier0.valueEstimate)}` : ""}</div>
            </Link>
          ) : (
            <div className="empty-honest" style={{ justifyContent: "space-between" }}>
              <span>Nessun dossier.</span>
              <QuickCreateDossier partnerId={p.id} defaultName={`Dossier ${p.name}`} label="+ Crea dossier" />
            </div>
          )}
        </div>

        <div className="card" style={{ padding: 16 }}>
          <p className="sec-title">Ordini · {bundle.orders.length}</p>
          {bundle.orders.length ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {bundle.orders.slice(0, 6).map((o) => (
                <div key={o.id} className="row" style={{ justifyContent: "space-between", fontSize: 13, padding: "3px 0" }}>
                  <span>{o.name}{o.isSample ? " · campioni" : ""}</span>
                  <span className="muted">{dateLabel(o.dateOrder)} · {money(o.amountTotal, bundle.revenue.currency)}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-honest" style={{ justifyContent: "space-between" }}>
              <span>Nessun ordine.</span>
              <CampionaturaButton partnerId={p.id} leadId={lead0?.id ?? null} small label="+ Campionatura" />
            </div>
          )}
        </div>
      </div>

      {/* ── TIMELINE (identica alla lead, free-domain guarded) ── */}
      <div className="row" style={{ justifyContent: "flex-end", marginBottom: -6 }}>
        <SyncMailButton partnerId={p.id} onDone={() => router.refresh()} />
      </div>
      <LeadTimeline items={tl} />

      {composeOpen ? <Composer mode="new" target={composeTarget} accounts={accounts} onClose={() => setComposeOpen(false)} /> : null}
    </div>
  );
}

function Metric({ label, value, foot, footColor }: { label: string; value: string; foot?: string; footColor?: string }) {
  return (
    <div className="card" style={{ padding: "14px 16px" }}>
      <div className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: ".05em" }}>{label}</div>
      <div style={{ fontSize: 23, fontWeight: 700, lineHeight: 1.1, marginTop: 4 }}>{value}</div>
      {foot ? <div style={{ fontSize: 11, marginTop: 4, color: footColor ?? "var(--muted)", fontWeight: footColor ? 600 : 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{foot}</div> : null}
    </div>
  );
}

function Row({ label, v }: { label: string; v: React.ReactNode }) {
  return (
    <div className="row" style={{ justifyContent: "space-between", gap: 10, fontSize: 13 }}>
      <span className="muted" style={{ fontSize: 11 }}>{label}</span>
      <span style={{ textAlign: "right", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{v}</span>
    </div>
  );
}
