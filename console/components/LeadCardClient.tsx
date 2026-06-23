"use client";
// Scheda lead "eccezionale" (Brief 18) — livello grandi CRM, estetica console (superfici chiare,
// bordi 0.5px, niente gradienti/ombre, colore solo per significato). Gerarchia: header → stepper
// → 4 metriche → azioni → pannelli → timeline. Solo dati reali da console_get_lead. Nessun gateway nuovo.
import { useEffect, useState } from "react";
import Link from "next/link";
import { getLead, getLeadTimeline, updateLead, activityLabel, type LeadDetail, type LeadTimelineItem } from "@/lib/lead";
import { moneyCompact, dateLabel } from "@/components/Honest";
import { Composer, type Account } from "@/components/Composer";
import { CampionaturaButton } from "@/components/CampionaturaButton";
import { LeadTimeline } from "@/components/LeadTimeline";
import { LeadOtherMails } from "@/components/LeadOtherMails";
import { QuickCreateDossier } from "@/components/QuickCreate";
import { SendDocumentsButton } from "@/components/SendDocumentsButton";
import { RicettaButton } from "@/components/RicettaButton";
import { SyncMailButton } from "@/components/SyncMailButton";

function initials(name: string): string {
  return (name || "").split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase() ?? "").join("") || "·";
}

// S3 — il sito può arrivare come "dominio.com" senza schema: normalizza per un link valido.
function normalizeUrl(url: string): string {
  const u = (url || "").trim();
  return /^https?:\/\//i.test(u) ? u : `https://${u}`;
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

  // S1 — refetch timeline dopo un'assegnazione mail→lead (la mail compare qui, sparisce da "Altre mail").
  function refreshTimeline() {
    getLeadTimeline(leadId).then((t) => { if (t?.items) setItems(t.items); }).catch(() => {});
  }

  // Brief 20 P2 — salva un campo whitelisted; ottimistico (merge subito) + rollback se il server nega.
  async function save(values: Record<string, unknown>) {
    if (!lead) return;
    const snapshot = lead;
    setLead({ ...lead, ...mapOptimistic(values) });
    try {
      const r = await updateLead(leadId, values);
      if (r.ok) setLead((cur) => cur ? { ...cur, name: r.name ?? cur.name, expectedRevenue: r.expectedRevenue ?? cur.expectedRevenue, probability: r.probability ?? cur.probability, stageId: r.stageId ?? cur.stageId, stageName: r.stageName ?? cur.stageName, emailFrom: r.emailFrom ?? cur.emailFrom } : cur);
      else { setLead(snapshot); setErr(r.message ?? "salvataggio negato"); }
    } catch (e) { setLead(snapshot); setErr((e as Error).message); }
  }

  if (err) return <div className="card" style={{ padding: 16, color: "var(--danger)" }}>Errore: {err}</div>;
  if (!lead) return <div className="muted" style={{ padding: 16 }}>Carico scheda…</div>;

  // Brief 20 B — rotting da ATTIVITÀ REALE (neutral = grigio, mai rosso falso).
  const act = lead.activityState ? activityLabel[lead.activityState] : null;
  const danger = lead.activityState === "danger";
  const warn = lead.activityState === "warning";
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

      {/* ── STEPPER + Fase editabile ── */}
      <div className="card" style={{ padding: "14px 18px" }}>
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
          <span className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: ".05em" }}>Fase</span>
          <select value={lead.stageId} onChange={(e) => save({ stage_id: Number(e.target.value) })}
            style={{ padding: "4px 8px", borderRadius: 6, border: "1px solid var(--line)", fontSize: 12 }}>
            {lead.stages.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>
        <StageStepper stages={lead.stages} currentId={lead.stageId} />
      </div>

      {/* ── 4 METRICHE (Valore/Probabilità editabili inline) ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <Metric label="Valore" editValue={lead.expectedRevenue}
          display={lead.expectedRevenue != null ? moneyCompact(lead.expectedRevenue) : "—"}
          onSave={(v) => save({ expected_revenue: v })} />
        <Metric label="Probabilità" editValue={lead.probability} suffix="%"
          display={lead.probability != null ? `${Math.round(lead.probability)}%` : "—"}
          onSave={(v) => save({ probability: v })} />
        <Metric
          label="Inattivo da"
          value={lead.daysInactive != null ? `${lead.daysInactive}g` : "—"}
          color={danger ? "var(--danger)" : warn ? "var(--warn)" : act ? "var(--ink)" : "var(--muted)"}
          foot={act ? act.label : "nessuna attività"}
          footColor={act ? act.color : undefined}
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

      {/* ── PANNELLI: Contatto + Azienda (S3 — campi arricchiti, standard + Agente 007) ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        {/* Contatto */}
        <div className="card" style={{ padding: 16 }}>
          <p className="sec-title">Contatto</p>
          {lead.partner ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <Row label="Nome" v={<Link href={`/partner/${lead.partner.id}`} style={{ color: "var(--accent)", fontWeight: 600 }}>{lead.partner.name}</Link>} />
              {lead.partner.role || lead.partner.function ? <Row label="Ruolo" v={lead.partner.role || lead.partner.function} /> : null}
              <Row label="Email" v={<InlineText value={lead.emailFrom || lead.partner.email || ""} placeholder="email@…" onSave={(s) => save({ email_from: s })} />} />
              {lead.partner.phone ? <Row label="Telefono" v={lead.partner.phone} /> : null}
            </div>
          ) : <div className="muted" style={{ fontSize: 13 }}>Nessun contatto collegato.</div>}
        </div>

        {/* Azienda (S3 — arricchita) */}
        <div className="card" style={{ padding: 16 }}>
          <p className="sec-title">Azienda{lead.company && lead.company.enriched ? <span className="chip" style={{ marginLeft: 6, fontSize: 10, background: "var(--accent-t)", color: "var(--accent)" }}>007</span> : null}</p>
          {lead.company ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <Row label="Nome" v={<Link href={`/partner/${lead.company.id}`} style={{ color: "var(--accent)", fontWeight: 600 }}>{lead.company.name}</Link>} />
              {lead.company.vat ? <Row label="P.IVA" v={lead.company.vat} /> : null}
              {lead.company.website ? <Row label="Sito" v={<a href={normalizeUrl(lead.company.website)} target="_blank" rel="noreferrer" style={{ color: "var(--accent)" }}>{lead.company.website}</a>} /> : null}
              {lead.company.country || lead.company.city ? <Row label="Paese" v={[lead.company.city, lead.company.country].filter(Boolean).join(", ")} /> : null}
              {lead.company.channel ? <Row label="Canale" v={lead.company.channel} /> : null}
              {lead.company.sector ? <Row label="Settore" v={lead.company.sector} /> : null}
              {lead.company.certifications ? <Row label="Certificazioni" v={lead.company.certifications} /> : null}
            </div>
          ) : <div className="muted" style={{ fontSize: 13 }}>Nessuna azienda collegata.</div>}
        </div>
      </div>

      {/* ── Prossima azione (full width) ── */}
      <div className="card" style={{ padding: 16 }}>
        <p className="sec-title">Prossima azione</p>
        {lead.nextAction ? (
            <div>
              <div style={{ fontSize: 15, fontWeight: 600 }}>{lead.nextAction.summary}</div>
              <div className="row" style={{ gap: 8, marginTop: 6, alignItems: "center" }}>
                <input type="date" defaultValue={(lead.nextAction.date || "").slice(0, 10)} onChange={(e) => save({ cf_date_next_followup: e.target.value })}
                  style={{ fontSize: 12, padding: "3px 6px", borderRadius: 6, border: "1px solid var(--line)", color: aTone ? aTone.color : "var(--muted)" }} />
                {aTone ? <span className="chip" style={{ fontSize: 10, background: aTone.color === "var(--danger)" ? "var(--danger-t)" : "var(--warn-t)", color: aTone.color }}>{aTone.label}</span> : null}
              </div>
            </div>
          ) : (
            <div className="empty-honest" style={{ justifyContent: "space-between" }}>
              <span>Nessuna azione pianificata.</span>
              <input type="date" onChange={(e) => e.target.value && save({ cf_date_next_followup: e.target.value })}
                style={{ fontSize: 12, padding: "3px 6px", borderRadius: 6, border: "1px solid var(--accent)" }} />
            </div>
          )}
      </div>

      {/* ── TIMELINE (free-domain guarded, Brief 16) ── */}
      {lead.partner ? (
        <div className="row" style={{ justifyContent: "flex-end", marginBottom: -6 }}>
          <SyncMailButton partnerId={lead.partner.id} onDone={() => getLeadTimeline(leadId).then((t) => { if (t?.items) setItems(t.items); }).catch(() => {})} />
        </div>
      ) : null}
      <LeadTimeline items={items} activeShipmentId={activeShipmentId} />

      {/* ── S1 — Altre mail con questo partner (non assegnate): assegnabili a mano + thread-assist ── */}
      <LeadOtherMails leadId={leadId} hasPartner={!!lead.partner} onAssigned={refreshTimeline} />

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

// optimistic merge: nomi campo gateway → chiavi LeadDetail
function mapOptimistic(values: Record<string, unknown>): Partial<LeadDetail> {
  const m: Partial<LeadDetail> = {};
  if ("name" in values) m.name = String(values.name ?? "");
  if ("expected_revenue" in values) m.expectedRevenue = Number(values.expected_revenue) || 0;
  if ("probability" in values) m.probability = Number(values.probability) || 0;
  if ("email_from" in values) m.emailFrom = String(values.email_from ?? "");
  return m;
}

// ── Metric card: numero grosso; se editValue/onSave → click-to-edit inline (Brief 20 P2) ──
function Metric({ label, value, display, editValue, suffix, onSave, color, foot, footColor, alarm }: {
  label: string; value?: string; display?: string; editValue?: number | null; suffix?: string;
  onSave?: (v: number) => void; color?: string; foot?: string; footColor?: string; alarm?: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [raw, setRaw] = useState("");
  const editable = !!onSave;
  function begin() { setRaw(editValue != null ? String(editValue) : ""); setEditing(true); }
  function commit() { setEditing(false); if (onSave) { const n = parseFloat(raw.replace(",", ".")); if (!isNaN(n)) onSave(n); } }
  return (
    <div className="card" style={{ padding: "14px 16px", borderColor: alarm ? "var(--danger)" : undefined }}>
      <div className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: ".05em" }}>{label}{editable ? " ✎" : ""}</div>
      {editing ? (
        <input autoFocus value={raw} onChange={(e) => setRaw(e.target.value)} onBlur={commit}
          onKeyDown={(e) => { if (e.key === "Enter") commit(); if (e.key === "Escape") setEditing(false); }}
          style={{ fontSize: 20, fontWeight: 700, marginTop: 4, width: "100%", border: "1px solid var(--accent)", borderRadius: 6, padding: "2px 6px" }} />
      ) : (
        <div onClick={editable ? begin : undefined}
          style={{ fontSize: 23, fontWeight: 700, lineHeight: 1.1, marginTop: 4, color: color ?? "var(--ink)", cursor: editable ? "text" : "default" }}>
          {display ?? value}{suffix && (display ?? value) !== "—" ? "" : ""}
        </div>
      )}
      {foot ? <div style={{ fontSize: 11, marginTop: 4, color: footColor ?? "var(--muted)", fontWeight: footColor ? 600 : 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{foot}</div> : null}
    </div>
  );
}

// ── Edit inline testo (email) ──
function InlineText({ value, placeholder, onSave }: { value: string; placeholder?: string; onSave: (s: string) => void }) {
  const [editing, setEditing] = useState(false);
  const [raw, setRaw] = useState(value);
  if (editing) {
    return <input autoFocus value={raw} placeholder={placeholder} onChange={(e) => setRaw(e.target.value)}
      onBlur={() => { setEditing(false); if (raw !== value) onSave(raw.trim()); }}
      onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); if (e.key === "Escape") { setRaw(value); setEditing(false); } }}
      style={{ fontSize: 13, padding: "2px 6px", borderRadius: 6, border: "1px solid var(--accent)", width: "100%" }} />;
  }
  return <span onClick={() => { setRaw(value); setEditing(true); }} style={{ cursor: "text" }}>{value || <span className="muted">+ aggiungi</span>}</span>;
}

function Row({ label, v }: { label: string; v: React.ReactNode }) {
  return (
    <div className="row" style={{ justifyContent: "space-between", gap: 10, fontSize: 13 }}>
      <span className="muted" style={{ fontSize: 11 }}>{label}</span>
      <span style={{ textAlign: "right", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{v}</span>
    </div>
  );
}
