"use client";
// Scheda lead "eccezionale" (Brief 18) — livello grandi CRM, estetica console (superfici chiare,
// bordi 0.5px, niente gradienti/ombre, colore solo per significato). Gerarchia: header → stepper
// → 4 metriche → azioni → pannelli → timeline. Solo dati reali da console_get_lead. Nessun gateway nuovo.
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
import { SyncMailButton } from "@/components/SyncMailButton";

function initials(name: string): string {
  return (name || "").split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase() ?? "").join("") || "·";
}

// Urgenza prossima azione: scaduta (rosso) / imminente ≤3g (giallo) / futura.
function actionTone(date: string | null): { color: string; label: string } | null {
  if (!date) return null;
  const d = new Date(date).getTime();
  if (isNaN(d)) return null;
  const days = Math.floor((d - Date.now()) / 86400000);
  if (days < 0) return { color: "var(--danger)", label: "scaduta" };
  if (days <= 3) return { color: "var(--warn)", label: days === 0 ? "oggi" : `tra ${days}g` };
  return null;
}

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
  const danger = lead.rottingState === "danger" || lead.rottingState === "dead";
  const warn = lead.rottingState === "warning";
  const activeShipmentId = items.find((i) => i.type === "campionatura" && i.shipmentId)?.shipmentId;
  const composeTarget = { id: 0, subject: "", senderEmail: lead.emailFrom, senderName: lead.partner ? lead.partner.name : "" };

  const companyName = lead.company ? lead.company.name : (lead.partner ? lead.partner.name : "");
  const place = lead.partner ? [lead.partner.city, lead.partner.country].filter(Boolean).join(", ") : "";
  const role = lead.partner ? lead.partner.role : "";
  const subtitle = [companyName, place, role].filter(Boolean).join("  ·  ");
  const aTone = lead.nextAction ? actionTone(lead.nextAction.date) : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* ── HEADER ── */}
      <div className="card" style={{ padding: "18px 20px" }}>
        <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 22, fontWeight: 700, lineHeight: 1.15, letterSpacing: "-0.01em" }}>{lead.name}</div>
            {subtitle ? <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>{subtitle}</div> : null}
          </div>
          <div className="row" style={{ gap: 9, alignItems: "center", flexShrink: 0 }}>
            <span style={{ width: 32, height: 32, borderRadius: 999, background: "var(--accent-t)", color: "var(--accent)", display: "inline-flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 12 }}>{initials(lead.owner)}</span>
            <div style={{ textAlign: "right" }}>
              <div className="muted" style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: ".06em" }}>Owner</div>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{lead.owner || "non assegnato"}</div>
            </div>
          </div>
        </div>
      </div>

      {/* ── STEPPER ── */}
      <div className="card" style={{ padding: "14px 18px" }}>
        <StageStepper stages={lead.stages} currentId={lead.stageId} />
      </div>

      {/* ── 4 METRICHE ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <Metric label="Valore" value={lead.expectedRevenue != null ? moneyCompact(lead.expectedRevenue) : "—"} />
        <Metric label="Probabilità" value={lead.probability != null ? `${Math.round(lead.probability)}%` : "—"} />
        <Metric
          label="Giorni aperto"
          value={lead.daysOpen != null ? String(lead.daysOpen) : "—"}
          color={danger ? "var(--danger)" : warn ? "var(--warn)" : undefined}
          foot={rot ? rot.label : undefined}
          footColor={rot ? rot.color : undefined}
          alarm={danger}
        />
        <Metric label="Dossier" value={lead.dossier ? "1" : "0"} foot={lead.dossier ? lead.dossier.name : "nessuno"} />
      </div>

      {/* ── BARRA AZIONI (tutte vive) ── */}
      <div className="card" style={{ padding: 12 }}>
        <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
          <button className="btn-primary" onClick={() => setComposeOpen(true)} disabled={!lead.emailFrom}>✉ Scrivi mail</button>
          <CampionaturaButton partnerId={lead.partner ? lead.partner.id : null} leadId={lead.id} label="Campionatura" />
          <SendDocumentsButton leadId={lead.id} partnerId={lead.partner ? lead.partner.id : null} label="Documenti" />
          <QuickCreateDossier partnerId={lead.partner ? lead.partner.id : null} leadId={lead.id} defaultName={`Dossier ${lead.partner ? lead.partner.name : lead.name}`} small={false} label="Dossier" />
          <RicettaButton leadId={lead.id} partnerId={lead.partner ? lead.partner.id : null} label="Ricetta" />
        </div>
      </div>

      {/* ── 2 PANNELLI ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        {/* Contatto */}
        <div className="card" style={{ padding: 16 }}>
          <p className="sec-title">Contatto</p>
          {lead.partner ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <Row label="Nome" v={<Link href={`/partner/${lead.partner.id}`} style={{ color: "var(--accent)", fontWeight: 600 }}>{lead.partner.name}</Link>} />
              <Row label="Ruolo" v={lead.partner.role || <span className="muted">—</span>} />
              <Row label="Email" v={lead.partner.email || <span className="muted">—</span>} />
              {lead.company ? <Row label="Azienda" v={<Link href={`/partner/${lead.company.id}`} style={{ color: "var(--accent)", fontWeight: 600 }}>{lead.company.name}</Link>} /> : null}
            </div>
          ) : <div className="muted" style={{ fontSize: 13 }}>Nessun contatto collegato.</div>}
        </div>

        {/* Prossima azione */}
        <div className="card" style={{ padding: 16 }}>
          <p className="sec-title">Prossima azione</p>
          {lead.nextAction ? (
            <div>
              <div style={{ fontSize: 15, fontWeight: 600 }}>{lead.nextAction.summary}</div>
              <div className="row" style={{ gap: 8, marginTop: 6, alignItems: "center" }}>
                <span style={{ fontSize: 13, color: aTone ? aTone.color : "var(--muted)", fontWeight: aTone ? 600 : 400 }}>{dateLabel(lead.nextAction.date)}</span>
                {aTone ? <span className="chip" style={{ fontSize: 10, background: aTone.color === "var(--danger)" ? "var(--danger-t)" : "var(--warn-t)", color: aTone.color }}>{aTone.label}</span> : null}
              </div>
            </div>
          ) : (
            <div className="empty-honest" style={{ justifyContent: "space-between" }}>
              <span>Nessuna azione pianificata.</span>
              <span className="empty-action" onClick={() => setComposeOpen(true)}>+ Pianifica</span>
            </div>
          )}
        </div>
      </div>

      {/* ── TIMELINE (free-domain guarded, Brief 16) ── */}
      {lead.partner ? (
        <div className="row" style={{ justifyContent: "flex-end", marginBottom: -6 }}>
          <SyncMailButton partnerId={lead.partner.id} onDone={() => getLeadTimeline(leadId).then((t) => { if (t?.items) setItems(t.items); }).catch(() => {})} />
        </div>
      ) : null}
      <LeadTimeline items={items} activeShipmentId={activeShipmentId} />

      {composeOpen ? <Composer mode="new" target={composeTarget} accounts={accounts} onClose={() => setComposeOpen(false)} /> : null}
    </div>
  );
}

// ── Stepper fasi: non-terminali connesse; terminale = stato finale (badge), non step ──
function StageStepper({ stages, currentId }: { stages: LeadDetail["stages"]; currentId: number }) {
  const flow = stages.filter((s) => !s.isLost && !/standby/i.test(s.name) && !s.isWon);
  const current = stages.find((s) => s.id === currentId);
  const terminal = current && (current.isLost || current.isWon || /standby/i.test(current.name));
  const currentIdx = flow.findIndex((s) => s.id === currentId);

  return (
    <div>
      <div className="row" style={{ gap: 0, alignItems: "stretch", flexWrap: "wrap" }}>
        {flow.map((s, i) => {
          const done = !terminal && currentIdx >= 0 && i < currentIdx;
          const active = !terminal && s.id === currentId;
          return (
            <div key={s.id} className="row" style={{ alignItems: "center", flex: "1 1 0", minWidth: 90 }}>
              <div style={{
                flex: 1, textAlign: "center", fontSize: 12, fontWeight: 600, padding: "8px 6px", borderRadius: 6,
                background: active ? "var(--accent)" : done ? "var(--ok-t)" : "var(--panel-2)",
                color: active ? "#fff" : done ? "var(--ok)" : "var(--muted)",
                whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
              }}>{s.name}</div>
              {i < flow.length - 1 ? <span style={{ color: "var(--line-2)", padding: "0 2px", fontSize: 11 }}>›</span> : null}
            </div>
          );
        })}
      </div>
      {terminal ? (
        <div style={{ marginTop: 10 }}>
          <span className="chip" style={{
            fontSize: 12, fontWeight: 700,
            background: current!.isWon ? "var(--ok-t)" : "var(--danger-t)",
            color: current!.isWon ? "var(--ok)" : "var(--danger)",
          }}>Stato finale: {current!.name}</span>
        </div>
      ) : null}
    </div>
  );
}

// ── Metric card: numero grosso, colore solo per significato, foot opzionale ──
function Metric({ label, value, color, foot, footColor, alarm }: {
  label: string; value: string; color?: string; foot?: string; footColor?: string; alarm?: boolean;
}) {
  return (
    <div className="card" style={{ padding: "14px 16px", borderColor: alarm ? "var(--danger)" : undefined }}>
      <div className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: ".05em" }}>{label}</div>
      <div style={{ fontSize: 23, fontWeight: 700, lineHeight: 1.1, marginTop: 4, color: color ?? "var(--ink)" }}>{value}</div>
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
