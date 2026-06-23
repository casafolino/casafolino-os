"use client";
// Scheda lead "eccezionale" (Brief 18) — livello grandi CRM, estetica console (superfici chiare,
// bordi 0.5px, niente gradienti/ombre, colore solo per significato). Gerarchia: header → stepper
// → 4 metriche → azioni → pannelli → timeline. Solo dati reali da console_get_lead. Nessun gateway nuovo.
import { useEffect, useState } from "react";
import Link from "next/link";
import { getLead, getLeadTimeline, updateLead, activityLabel, LEAD_EDITABLE_BY_ROLE, type LeadDetail, type LeadTimelineItem } from "@/lib/lead";
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
  // S4 — vista read-only di default; un solo "Modifica" → bozza locale → Salva/Annulla.
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  function loadLead() {
    getLead(leadId).then((d) => { if (d && d.id) setLead(d); else setErr(d?.message ?? "lead non trovato"); }).catch((e) => setErr((e as Error).message));
  }

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

  // S4 — whitelist effettiva per ruolo (manager pieno; operatore ridotto — comunque gated lato server).
  function editableFields(l: LeadDetail): Set<string> {
    return new Set(LEAD_EDITABLE_BY_ROLE[l.role ?? "manager"] ?? LEAD_EDITABLE_BY_ROLE.manager);
  }
  function canEdit(field: string): boolean { return !!lead && editableFields(lead).has(field); }
  function df(k: string): string { return draft[k] ?? ""; }
  function setField(k: string, v: string) { setDraft((d) => ({ ...d, [k]: v })); }

  function beginEdit() {
    if (!lead) return;
    setErr(null);
    setDraft({
      name: lead.name ?? "",
      stage_id: String(lead.stageId ?? ""),
      expected_revenue: lead.expectedRevenue != null ? String(lead.expectedRevenue) : "",
      probability: lead.probability != null ? String(lead.probability) : "",
      email_from: lead.emailFrom ?? "",
      cf_date_next_followup: (lead.nextAction?.date || "").slice(0, 10),
    });
    setEditing(true);
  }
  function cancelEdit() { setEditing(false); setDraft({}); setErr(null); }

  // S4 — Salva: invia SOLO i campi whitelisted e realmente cambiati; il server è l'autorità finale.
  async function saveEdits() {
    if (!lead) return;
    const wl = editableFields(lead);
    const current: Record<string, string> = {
      name: lead.name ?? "", stage_id: String(lead.stageId ?? ""),
      expected_revenue: lead.expectedRevenue != null ? String(lead.expectedRevenue) : "",
      probability: lead.probability != null ? String(lead.probability) : "",
      email_from: lead.emailFrom ?? "", cf_date_next_followup: (lead.nextAction?.date || "").slice(0, 10),
    };
    const values: Record<string, unknown> = {};
    for (const k of wl) {
      if ((draft[k] ?? "") !== (current[k] ?? "")) {
        values[k] = k === "stage_id" ? Number(draft[k]) : draft[k];
      }
    }
    if (Object.keys(values).length === 0) { setEditing(false); setDraft({}); return; }
    setSaving(true);
    try {
      const r = await updateLead(leadId, values);
      if (r.ok) { setEditing(false); setDraft({}); loadLead(); } // ricarica canonico (rotting/nextAction ricalcolati)
      else setErr(r.message ?? "salvataggio negato");
    } catch (e) { setErr((e as Error).message); }
    finally { setSaving(false); }
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
            {/* S4 — un solo bottone Modifica; in edit mode → Salva/Annulla */}
            {editing ? (
              <>
                <button className="btn-primary" onClick={saveEdits} disabled={saving}>{saving ? "Salvo…" : "Salva"}</button>
                <button className="btn" onClick={cancelEdit} disabled={saving}>Annulla</button>
              </>
            ) : (
              <button className="btn" onClick={beginEdit} title="Modifica i campi consentiti">✎ Modifica</button>
            )}
            <span style={{ width: 32, height: 32, borderRadius: 999, background: "var(--accent-t)", color: "var(--accent)", display: "inline-flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 12 }}>{initials(lead.owner)}</span>
            <div style={{ textAlign: "right" }}>
              <div className="muted" style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: ".06em" }}>Owner</div>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{lead.owner || "non assegnato"}</div>
            </div>
          </div>
        </div>
        {editing ? <div className="muted" style={{ fontSize: 11, marginTop: 8 }}>Modalità modifica — editabili solo i campi consentiti dal tuo ruolo.</div> : null}
      </div>

      {/* ── STEPPER + Fase editabile ── */}
      <div className="card" style={{ padding: "14px 18px" }}>
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
          <span className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: ".05em" }}>Fase</span>
          {editing && canEdit("stage_id") ? (
            <select value={df("stage_id")} onChange={(e) => setField("stage_id", e.target.value)}
              style={{ padding: "4px 8px", borderRadius: 6, border: "1px solid var(--accent)", fontSize: 12 }}>
              {lead.stages.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          ) : (
            <span style={{ fontSize: 12, fontWeight: 600 }}>{lead.stageName}</span>
          )}
        </div>
        <StageStepper stages={lead.stages} currentId={editing && df("stage_id") ? Number(df("stage_id")) : lead.stageId} />
      </div>

      {/* ── 4 METRICHE — Valore/Probabilità editabili SOLO in edit mode (S4) ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <Metric label="Valore"
          display={lead.expectedRevenue != null ? moneyCompact(lead.expectedRevenue) : "—"}
          editing={editing && canEdit("expected_revenue")} editVal={df("expected_revenue")} onEdit={(v) => setField("expected_revenue", v)} />
        <Metric label="Probabilità" suffix="%"
          display={lead.probability != null ? `${Math.round(lead.probability)}%` : "—"}
          editing={editing && canEdit("probability")} editVal={df("probability")} onEdit={(v) => setField("probability", v)} />
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
              <Row label="Email" v={editing && canEdit("email_from")
                ? <input value={df("email_from")} placeholder="email@…" onChange={(e) => setField("email_from", e.target.value)}
                    style={{ fontSize: 13, padding: "2px 6px", borderRadius: 6, border: "1px solid var(--accent)", width: "100%" }} />
                : (lead.emailFrom || lead.partner.email || <span className="muted">—</span>)} />
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
                {editing && canEdit("cf_date_next_followup") ? (
                  <input type="date" value={df("cf_date_next_followup")} onChange={(e) => setField("cf_date_next_followup", e.target.value)}
                    style={{ fontSize: 12, padding: "3px 6px", borderRadius: 6, border: "1px solid var(--accent)" }} />
                ) : (
                  <span style={{ fontSize: 12, color: aTone ? aTone.color : "var(--muted)" }}>{dateLabel(lead.nextAction.date)}</span>
                )}
                {aTone ? <span className="chip" style={{ fontSize: 10, background: aTone.color === "var(--danger)" ? "var(--danger-t)" : "var(--warn-t)", color: aTone.color }}>{aTone.label}</span> : null}
              </div>
            </div>
          ) : editing && canEdit("cf_date_next_followup") ? (
            <div className="empty-honest" style={{ justifyContent: "space-between" }}>
              <span>Nessuna azione pianificata.</span>
              <input type="date" value={df("cf_date_next_followup")} onChange={(e) => setField("cf_date_next_followup", e.target.value)}
                style={{ fontSize: 12, padding: "3px 6px", borderRadius: 6, border: "1px solid var(--accent)" }} />
            </div>
          ) : (
            <div className="empty-honest"><span>Nessuna azione pianificata.</span></div>
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

// ── Metric card: numero grosso; in edit mode (S4) diventa input controllato dalla bozza ──
function Metric({ label, value, display, editing, editVal, suffix, onEdit, color, foot, footColor, alarm }: {
  label: string; value?: string; display?: string; editing?: boolean; editVal?: string; suffix?: string;
  onEdit?: (v: string) => void; color?: string; foot?: string; footColor?: string; alarm?: boolean;
}) {
  const editable = !!onEdit; // questa metrica è whitelisted
  return (
    <div className="card" style={{ padding: "14px 16px", borderColor: alarm ? "var(--danger)" : editing && editable ? "var(--accent)" : undefined }}>
      <div className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: ".05em" }}>{label}</div>
      {editing && editable ? (
        <input autoFocus={false} value={editVal ?? ""} onChange={(e) => onEdit!(e.target.value)}
          style={{ fontSize: 20, fontWeight: 700, marginTop: 4, width: "100%", border: "1px solid var(--accent)", borderRadius: 6, padding: "2px 6px" }} />
      ) : (
        <div style={{ fontSize: 23, fontWeight: 700, lineHeight: 1.1, marginTop: 4, color: color ?? "var(--ink)" }}>
          {display ?? value}{suffix && (display ?? value) !== "—" ? "" : ""}
        </div>
      )}
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
