"use client";
// Scheda lead ricca (Brief 4): header + stage stepper, pannelli (contatto/azienda, dossier,
// metriche), barra azioni (Scrivi mail → Composer; Campionatura → wizard; slot disattivi per
// Dossier/Documenti/Ricetta = brief successivo), timeline attività. Riusa i componenti esistenti.
import { useEffect, useState } from "react";
import Link from "next/link";
import { getLead, getLeadTimeline, rottingLabel, type LeadDetail, type LeadTimelineItem } from "@/lib/lead";
import { moneyCompact, dateLabel } from "@/components/Honest";
import { Composer, type Account } from "@/components/Composer";
import { CampionaturaButton } from "@/components/CampionaturaButton";
import { LeadTimeline } from "@/components/LeadTimeline";
import { QuickCreateDossier } from "@/components/QuickCreate";
import { SendDocumentsButton } from "@/components/SendDocumentsButton";
import { RicettaButton } from "@/components/RicettaButton";

export function LeadCardClient({ leadId, accounts }: { leadId: number; accounts: Account[] }) {
  const [lead, setLead] = useState<LeadDetail | null>(null);
  const [items, setItems] = useState<LeadTimelineItem[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [composeOpen, setComposeOpen] = useState(false);

  useEffect(() => {
    let alive = true;
    getLead(leadId).then((d) => { if (!alive) return; if (d && d.id) setLead(d); else setErr(d?.message ?? "lead non trovato"); }).catch((e) => alive && setErr((e as Error).message));
    getLeadTimeline(leadId).then((t) => { if (alive && t?.items) setItems(t.items); }).catch(() => {});
    return () => { alive = false; };
  }, [leadId]);

  if (err) return <div className="card" style={{ padding: 16, color: "var(--danger)" }}>Errore: {err}</div>;
  if (!lead) return <div className="muted" style={{ padding: 16 }}>Carico scheda…</div>;

  const rot = lead.rottingState ? rottingLabel[lead.rottingState] : null;
  const activeShipmentId = items.find((i) => i.type === "campionatura" && i.shipmentId)?.shipmentId;
  const composeTarget = { id: 0, subject: "", senderEmail: lead.emailFrom, senderName: lead.partner ? lead.partner.name : "" };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* HEADER */}
      <div className="card" style={{ padding: 16 }}>
        <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ fontSize: 18, fontWeight: 700 }}>{lead.name}</div>
            <div className="muted" style={{ fontSize: 13 }}>
              {lead.partner ? lead.partner.name : "—"} · Owner: {lead.owner || "non assegnato"}
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 16, fontWeight: 700 }}>{lead.expectedRevenue != null ? moneyCompact(lead.expectedRevenue) : "valore da stimare"}</div>
            {lead.nextAction ? (
              <div className="muted" style={{ fontSize: 12 }}>Prossima: {lead.nextAction.summary} · {dateLabel(lead.nextAction.date)}</div>
            ) : <div className="muted" style={{ fontSize: 12 }}>Nessuna azione pianificata</div>}
          </div>
        </div>
        <StageStepper stages={lead.stages} currentId={lead.stageId} />
      </div>

      {/* PANNELLI */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
        {/* contatto + azienda */}
        <div className="card" style={{ padding: 14 }}>
          <p className="sec-title">Contatto</p>
          {lead.partner ? (
            <>
              <Field label="Nome" value={lead.partner.name} link={`/partner/${lead.partner.id}`} />
              <Field label="Email" value={lead.partner.email} />
              <Field label="Telefono" value={lead.partner.phone} />
              <Field label="Luogo" value={[lead.partner.city, lead.partner.country].filter(Boolean).join(", ")} />
              {lead.company ? <Field label="Azienda" value={lead.company.name} link={`/partner/${lead.company.id}`} /> : null}
            </>
          ) : <div className="muted" style={{ fontSize: 13 }}>Nessun contatto collegato.</div>}
        </div>

        {/* dossier */}
        <div className="card" style={{ padding: 14 }}>
          <p className="sec-title">Dossier</p>
          {lead.dossier ? (
            <>
              <Field label="Nome" value={lead.dossier.name} />
              <Field label="Stato" value={lead.dossier.status} />
              <Field label="Valore stimato" value={lead.dossier.valueEstimate != null ? moneyCompact(lead.dossier.valueEstimate) : ""} />
            </>
          ) : <div className="muted" style={{ fontSize: 13 }}>Nessun dossier collegato.</div>}
        </div>

        {/* metriche */}
        <div className="card" style={{ padding: 14 }}>
          <p className="sec-title">Metriche</p>
          <Field label="Probabilità" value={lead.probability != null ? `${Math.round(lead.probability)}%` : ""} />
          <Field label="Score" value={lead.score != null ? String(lead.score) : ""} />
          <Field label="Età" value={lead.daysOpen != null ? `${lead.daysOpen} giorni` : ""} />
          {rot ? (
            <div style={{ marginTop: 6 }}>
              <span className="chip" style={{ background: "transparent", color: rot.color, border: `1px solid ${rot.color}` }}>{rot.label}</span>
            </div>
          ) : null}
        </div>
      </div>

      {/* BARRA AZIONI */}
      <div className="card" style={{ padding: 12 }}>
        <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
          <button className="btn-primary" onClick={() => setComposeOpen(true)} disabled={!lead.emailFrom}>✉ Scrivi mail</button>
          <CampionaturaButton partnerId={lead.partner ? lead.partner.id : null} leadId={lead.id} label="📦 Campionatura" />
          <QuickCreateDossier partnerId={lead.partner ? lead.partner.id : null} leadId={lead.id} defaultName={`Dossier ${lead.partner ? lead.partner.name : lead.name}`} small={false} label="Dossier" />
          <SendDocumentsButton leadId={lead.id} partnerId={lead.partner ? lead.partner.id : null} />
          <RicettaButton leadId={lead.id} partnerId={lead.partner ? lead.partner.id : null} />
        </div>
      </div>

      {/* TIMELINE */}
      <LeadTimeline items={items} activeShipmentId={activeShipmentId} />

      {composeOpen ? (
        <Composer mode="new" target={composeTarget} accounts={accounts} onClose={() => setComposeOpen(false)} />
      ) : null}
    </div>
  );
}

function StageStepper({ stages, currentId }: { stages: LeadDetail["stages"]; currentId: number }) {
  const flow = stages.filter((s) => !s.isLost && !/standby/i.test(s.name));
  const current = stages.find((s) => s.id === currentId);
  const currentIdx = flow.findIndex((s) => s.id === currentId);
  const terminal = current && (current.isLost || /standby/i.test(current.name));
  return (
    <div style={{ marginTop: 12 }}>
      <div className="row" style={{ gap: 4, flexWrap: "wrap" }}>
        {flow.map((s, i) => {
          const done = currentIdx >= 0 && i < currentIdx;
          const active = s.id === currentId;
          return (
            <div key={s.id} className="row" style={{ gap: 4, alignItems: "center" }}>
              <span style={{
                fontSize: 11, fontWeight: 600, padding: "3px 9px", borderRadius: 999,
                background: active ? "var(--accent)" : done ? "var(--ok-t)" : "var(--panel-2)",
                color: active ? "#fff" : done ? "var(--ok)" : "var(--muted)",
              }}>{s.name}</span>
              {i < flow.length - 1 ? <span style={{ color: "var(--line)" }}>›</span> : null}
            </div>
          );
        })}
      </div>
      {terminal ? (
        <div style={{ marginTop: 6 }}>
          <span className="chip" style={{ background: "var(--danger-t)", color: "var(--danger)" }}>{current!.name}</span>
        </div>
      ) : null}
    </div>
  );
}

function Field({ label, value, link }: { label: string; value: string; link?: string }) {
  return (
    <div style={{ marginBottom: 6 }}>
      <div className="muted" style={{ fontSize: 11 }}>{label}</div>
      {value ? (
        link ? <Link href={link} style={{ color: "var(--accent)", fontSize: 13, fontWeight: 600 }}>{value}</Link>
             : <div style={{ fontSize: 13 }}>{value}</div>
      ) : <div className="muted" style={{ fontSize: 12 }}>non disponibile</div>}
    </div>
  );
}
