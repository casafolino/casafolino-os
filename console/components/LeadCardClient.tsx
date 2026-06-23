"use client";
// Scheda lead/dossier "best-in-class" (Brief CRM Console v2 — F1). Restyle del livello grandi CRM.
// Layout: header identità → StagePath (fase corrente + next-best-action) → quick actions →
// body a 2 colonne (timeline al centro / right-rail di contesto). Edit INLINE per-campo (no modale):
// click sul campo → write() sul modello nativo (whitelist per ruolo) → toast + reload canonico,
// rollback su errore. Right-rail = lente read-only sul bundle partner (opportunità/campionature/ordini).
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getLead, getLeadTimeline, updateLead, fetchPartnerBundle, postLeadNote, createLeadActivity,
  nbaForStage, activityLabel, LEAD_EDITABLE_BY_ROLE, type LeadDetail, type LeadTimelineItem,
} from "@/lib/lead";
import type { PartnerBundle } from "@/lib/types";
import { moneyCompact, dateLabel } from "@/components/Honest";
import { Pill, Avatar, RailCard, Toast, InlineEditField } from "@/components/ds";
import { actionUrgency, activityTone, type Tone } from "@/lib/tokens";
import { Composer, type Account } from "@/components/Composer";
import { CampionaturaButton } from "@/components/CampionaturaButton";
import { LeadTimeline } from "@/components/LeadTimeline";
import { LeadOtherMails } from "@/components/LeadOtherMails";
import { QuickCreateDossier } from "@/components/QuickCreate";
import { SendDocumentsButton } from "@/components/SendDocumentsButton";
import { RicettaButton } from "@/components/RicettaButton";
import { SyncMailButton } from "@/components/SyncMailButton";

function normalizeUrl(url: string): string {
  const u = (url || "").trim();
  return /^https?:\/\//i.test(u) ? u : `https://${u}`;
}

export function LeadCardClient({ leadId, accounts }: { leadId: number; accounts: Account[] }) {
  const [lead, setLead] = useState<LeadDetail | null>(null);
  const [items, setItems] = useState<LeadTimelineItem[]>([]);
  const [bundle, setBundle] = useState<PartnerBundle | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [composeOpen, setComposeOpen] = useState(false);
  const [toast, setToast] = useState<{ msg: string; tone: Tone } | null>(null);

  function loadLead() {
    return getLead(leadId)
      .then((d) => { if (d && d.id) setLead(d); else setErr(d?.message ?? "lead non trovato"); })
      .catch((e) => setErr((e as Error).message));
  }
  function refreshTimeline() {
    getLeadTimeline(leadId).then((t) => { if (t?.items) setItems(t.items); }).catch(() => {});
  }

  useEffect(() => {
    let alive = true;
    getLead(leadId).then((d) => { if (!alive) return; if (d && d.id) setLead(d); else setErr(d?.message ?? "lead non trovato"); }).catch((e) => alive && setErr((e as Error).message));
    getLeadTimeline(leadId).then((t) => { if (alive && t?.items) setItems(t.items); }).catch(() => {});
    return () => { alive = false; };
  }, [leadId]);

  // Right-rail lazy: carica il bundle solo quando conosciamo il partner.
  useEffect(() => {
    const pid = lead?.partner ? lead.partner.id : null;
    if (!pid) return;
    let alive = true;
    fetchPartnerBundle(pid).then((b) => { if (alive) setBundle(b); }).catch(() => {});
    return () => { alive = false; };
  }, [lead?.partner ? lead.partner.id : null]);

  function editableFields(l: LeadDetail): Set<string> {
    return new Set(LEAD_EDITABLE_BY_ROLE[l.role ?? "manager"] ?? LEAD_EDITABLE_BY_ROLE.manager);
  }
  function canEdit(field: string): boolean { return !!lead && editableFields(lead).has(field); }

  // Edit inline per-campo: optimistic → write nativo → reload canonico; rollback + toast su errore.
  async function saveField(field: string, raw: string): Promise<boolean> {
    if (!lead) return false;
    const snapshot = lead;
    const value: unknown = field === "stage_id" || field === "expected_revenue" || field === "probability"
      ? Number(raw) : raw;
    // optimistic locale
    setLead((prev) => prev ? applyLocal(prev, field, raw) : prev);
    try {
      const r = await updateLead(leadId, { [field]: value });
      if (r.ok) {
        setToast({ msg: "Salvato.", tone: "success" });
        await loadLead(); // ricalcola rotting / nextAction lato server
        return true;
      }
      setLead(snapshot);
      setToast({ msg: r.message ?? "Salvataggio negato.", tone: "danger" });
      return false;
    } catch (e) {
      setLead(snapshot);
      setToast({ msg: (e as Error).message, tone: "danger" });
      return false;
    }
  }

  if (err) return <div className="card" style={{ padding: 16, color: "var(--danger)" }}>Errore: {err}</div>;
  if (!lead) return <div className="muted" style={{ padding: 16 }}>Carico scheda…</div>;

  const act = lead.activityState ? activityLabel[lead.activityState] : null;
  const rotTone: Tone = activityTone[lead.activityState ?? "neutral"] ?? "neutral";
  const activeShipmentId = items.find((i) => i.type === "campionatura" && i.shipmentId)?.shipmentId;
  const composeTarget = { id: 0, subject: "", senderEmail: lead.emailFrom, senderName: lead.partner ? lead.partner.name : "" };

  const companyName = lead.company ? lead.company.name : (lead.partner ? lead.partner.name : "");
  const place = lead.partner ? [lead.partner.city, lead.partner.country].filter(Boolean).join(", ") : "";
  const typeBadge = lead.company ? "Azienda" : lead.partner ? "Contatto" : "Lead";
  const aUrg = lead.nextAction ? actionUrgency(lead.nextAction.date) : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* ── HEADER identità ── */}
      <div className="card" style={{ padding: "18px 20px" }}>
        <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
          <div className="row" style={{ gap: 14, alignItems: "center", minWidth: 0 }}>
            <Avatar name={companyName || lead.name} size={44} />
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 22, fontWeight: 600, lineHeight: 1.15, letterSpacing: "-0.01em" }}>
                <InlineEditField
                  value={lead.name ?? ""}
                  editable={canEdit("name")}
                  onSave={(v) => saveField("name", v)}
                  placeholder="senza nome"
                />
              </div>
              <div className="row muted" style={{ fontSize: 13, marginTop: 5, gap: 8, flexWrap: "wrap" }}>
                <Pill tone="neutral" style={{ fontSize: 10 }}>{typeBadge}</Pill>
                {place ? <span>{place}</span> : null}
                {lead.score != null ? <Pill tone="info" style={{ fontSize: 10 }}>score {lead.score}</Pill> : null}
              </div>
            </div>
          </div>
          <div className="row" style={{ gap: 9, alignItems: "center", flexShrink: 0 }}>
            <Avatar name={lead.owner} size={32} title={lead.owner} />
            <div style={{ textAlign: "right" }}>
              <div className="muted" style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: ".06em" }}>Owner</div>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{lead.owner || "non assegnato"}</div>
            </div>
          </div>
        </div>
      </div>

      {/* ── STAGE PATH + next-best-action ── */}
      <div className="card" style={{ padding: "14px 18px" }}>
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <span className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: ".05em" }}>Fase</span>
          {canEdit("stage_id") ? (
            <InlineEditField
              value={String(lead.stageId ?? "")}
              display={<span style={{ fontWeight: 600, fontSize: 12 }}>{lead.stageName}</span>}
              type="select"
              options={lead.stages.map((s) => ({ value: String(s.id), label: s.name }))}
              onSave={(v) => saveField("stage_id", v)}
              valueStyle={{ fontSize: 12, fontWeight: 600 }}
            />
          ) : (
            <span style={{ fontSize: 12, fontWeight: 600 }}>{lead.stageName}</span>
          )}
        </div>
        <StagePath stages={lead.stages} currentId={lead.stageId} />
        <div className="row" style={{ gap: 7, marginTop: 10, alignItems: "flex-start" }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: "var(--accent)" }}>Per avanzare</span>
          <span className="muted" style={{ fontSize: 12 }}>{nbaForStage(lead.stageName)}</span>
        </div>
      </div>

      {/* ── QUICK ACTIONS ── */}
      <div className="card" style={{ padding: 12 }}>
        <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
          <button className="btn-primary" onClick={() => setComposeOpen(true)} disabled={!lead.emailFrom}>✉ Email</button>
          <CampionaturaButton partnerId={lead.partner ? lead.partner.id : null} leadId={lead.id} label="Campionatura" />
          <SendDocumentsButton leadId={lead.id} partnerId={lead.partner ? lead.partner.id : null} label="Offerta / Documenti" />
          <QuickCreateDossier partnerId={lead.partner ? lead.partner.id : null} leadId={lead.id} defaultName={`Dossier ${lead.partner ? lead.partner.name : lead.name}`} small={false} label="Dossier" />
          <RicettaButton leadId={lead.id} partnerId={lead.partner ? lead.partner.id : null} label="Ricetta" />
        </div>
      </div>

      {/* ── BODY a 2 colonne: centro (note/timeline) + right-rail (lente) ── */}
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 320px", gap: 14, alignItems: "start" }}>
        {/* CENTRO */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
          {/* metriche editabili inline */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <MetricInline label="Valore" canEdit={canEdit("expected_revenue")}
              raw={lead.expectedRevenue != null ? String(lead.expectedRevenue) : ""}
              display={lead.expectedRevenue != null ? moneyCompact(lead.expectedRevenue) : "valore non stimato"}
              onSave={(v) => saveField("expected_revenue", v)} />
            <MetricInline label="Probabilità" canEdit={canEdit("probability")}
              raw={lead.probability != null ? String(Math.round(lead.probability)) : ""}
              display={lead.probability != null ? `${Math.round(lead.probability)}%` : "non impostata"}
              onSave={(v) => saveField("probability", v)} />
          </div>

          {/* contatto + azienda */}
          <div className="card" style={{ padding: 16 }}>
            <p className="sec-title">Contatto</p>
            {lead.partner ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <Row label="Nome" v={<Link href={`/partner/${lead.partner.id}`} style={{ color: "var(--accent)", fontWeight: 600 }}>{lead.partner.name}</Link>} />
                {lead.partner.role || lead.partner.function ? <Row label="Ruolo" v={lead.partner.role || lead.partner.function} /> : null}
                <Row label="Email" v={
                  <InlineEditField value={lead.emailFrom || lead.partner.email || ""} type="email"
                    editable={canEdit("email_from")} placeholder="imposta email"
                    onSave={(v) => saveField("email_from", v)} />
                } />
                {lead.partner.phone ? <Row label="Telefono" v={lead.partner.phone} /> : null}
              </div>
            ) : <div className="muted" style={{ fontSize: 13 }}>Nessun contatto collegato.</div>}
          </div>

          {lead.company ? (
            <div className="card" style={{ padding: 16 }}>
              <p className="sec-title">Azienda{lead.company.enriched ? <span className="chip" style={{ marginLeft: 6, fontSize: 10, background: "var(--accent-t)", color: "var(--accent)" }}>007</span> : null}</p>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <Row label="Nome" v={<Link href={`/partner/${lead.company.id}`} style={{ color: "var(--accent)", fontWeight: 600 }}>{lead.company.name}</Link>} />
                {lead.company.vat ? <Row label="P.IVA" v={lead.company.vat} /> : null}
                {lead.company.website ? <Row label="Sito" v={<a href={normalizeUrl(lead.company.website)} target="_blank" rel="noreferrer" style={{ color: "var(--accent)" }}>{lead.company.website}</a>} /> : null}
                {lead.company.country || lead.company.city ? <Row label="Paese" v={[lead.company.city, lead.company.country].filter(Boolean).join(", ")} /> : null}
                {lead.company.channel ? <Row label="Canale" v={lead.company.channel} /> : null}
                {lead.company.sector ? <Row label="Settore" v={lead.company.sector} /> : null}
                {lead.company.certifications ? <Row label="Certificazioni" v={lead.company.certifications} /> : null}
              </div>
            </div>
          ) : null}

          {/* composer note/task inline */}
          <NoteTaskComposer leadId={leadId} onDone={(t) => { setToast(t); refreshTimeline(); loadLead(); }} />

          {/* timeline */}
          {lead.partner ? (
            <div className="row" style={{ justifyContent: "flex-end", marginBottom: -6 }}>
              <SyncMailButton partnerId={lead.partner.id} onDone={refreshTimeline} />
            </div>
          ) : null}
          <LeadTimeline items={items} activeShipmentId={activeShipmentId} />
          <LeadOtherMails leadId={leadId} hasPartner={!!lead.partner} onAssigned={refreshTimeline} />
        </div>

        {/* RIGHT-RAIL (lente) */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <RailCard title="Segnali">
            <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
              <SignalRow label="Inattivo da"
                value={lead.daysInactive != null ? `${lead.daysInactive}g` : "nessuna attività"}
                pill={<Pill tone={rotTone} dot style={{ fontSize: 10 }}>{act ? act.label : "nessuna attività"}</Pill>} />
              <SignalRow label="Prossima azione"
                value={lead.nextAction ? dateLabel(lead.nextAction.date) : "non pianificata"}
                pill={aUrg ? <Pill tone={aUrg.tone} style={{ fontSize: 10 }}>{aUrg.label}</Pill> : null} />
              <SignalRow label="SLA (cf.task)"
                value={bundle?.signals.overdueFollowup ? "follow-up scaduto" : bundle ? "nei tempi" : "—"}
                pill={bundle ? <Pill tone={bundle.signals.overdueFollowup ? "danger" : "success"} dot style={{ fontSize: 10 }}>{bundle.signals.overdueFollowup ? "rosso" : "verde"}</Pill> : null} />
            </div>
          </RailCard>

          <RailCard title="Opportunità" count={bundle?.leads.length}>
            {!bundle ? <Skeleton /> : bundle.leads.length === 0 ? <Empty text="Nessuna altra opportunità." /> : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {bundle.leads.map((l) => (
                  <Link key={l.id} href={`/lead/${l.id}`} className="hover-row" style={{ display: "block", padding: "6px 4px", borderRadius: 6 }}>
                    <div className="row" style={{ justifyContent: "space-between", gap: 8 }}>
                      <span className="ell" style={{ fontSize: 12, fontWeight: 600 }}>{l.name}</span>
                      <span style={{ fontSize: 12, fontWeight: 600 }}>{moneyCompact(l.expectedRevenue)}</span>
                    </div>
                    <div className="row" style={{ gap: 6, marginTop: 3 }}>
                      {l.stage ? <Pill tone="neutral" style={{ fontSize: 10 }}>{l.stage}</Pill> : null}
                      {l.probability != null ? <span className="muted" style={{ fontSize: 11 }}>{Math.round(l.probability)}%</span> : null}
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </RailCard>

          <RailCard title="Campionature" count={bundle?.orders.filter((o) => o.isSample).length}>
            {!bundle ? <Skeleton /> : (() => {
              const s = bundle.orders.filter((o) => o.isSample);
              return s.length === 0 ? <Empty text="Nessuna campionatura." /> : (
                <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                  {s.map((o) => <OrderRow key={o.id} name={o.name} amount={o.amountTotal} state={o.state} date={o.dateOrder} />)}
                </div>
              );
            })()}
          </RailCard>

          <RailCard title="Ordini" count={bundle?.orders.filter((o) => !o.isSample).length}>
            {!bundle ? <Skeleton /> : (() => {
              const o = bundle.orders.filter((x) => !x.isSample).slice(0, 6);
              return o.length === 0 ? <Empty text="Nessun ordine." /> : (
                <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                  {o.map((x) => <OrderRow key={x.id} name={x.name} amount={x.amountTotal} state={x.state} date={x.dateOrder} />)}
                </div>
              );
            })()}
          </RailCard>
        </div>
      </div>

      {composeOpen ? <Composer mode="new" target={composeTarget} accounts={accounts} onClose={() => setComposeOpen(false)} /> : null}
      {toast ? <Toast message={toast.msg} tone={toast.tone} onDismiss={() => setToast(null)} /> : null}
    </div>
  );
}

// ── applica localmente un edit per la UI ottimistica ──
function applyLocal(l: LeadDetail, field: string, raw: string): LeadDetail {
  switch (field) {
    case "name": return { ...l, name: raw };
    case "expected_revenue": return { ...l, expectedRevenue: raw === "" ? null : Number(raw) };
    case "probability": return { ...l, probability: raw === "" ? null : Number(raw) };
    case "email_from": return { ...l, emailFrom: raw };
    case "stage_id": {
      const st = l.stages.find((s) => s.id === Number(raw));
      return { ...l, stageId: Number(raw), stageName: st?.name ?? l.stageName };
    }
    default: return l;
  }
}

// ── StagePath: fasi non-terminali connesse; terminale = badge stato finale ──
function StagePath({ stages, currentId }: { stages: LeadDetail["stages"]; currentId: number }) {
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
          <Pill tone={current!.isWon ? "success" : "danger"} style={{ fontSize: 12, fontWeight: 700 }}>Stato finale: {current!.name}</Pill>
        </div>
      ) : null}
    </div>
  );
}

// ── Metrica con valore editabile inline ──
function MetricInline({ label, raw, display, canEdit, onSave }: {
  label: string; raw: string; display: string; canEdit: boolean; onSave: (v: string) => Promise<boolean>;
}) {
  return (
    <div className="card" style={{ padding: "14px 16px" }}>
      <div className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: ".05em" }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 600, lineHeight: 1.1, marginTop: 4 }}>
        <InlineEditField value={raw} display={display} type="number" editable={canEdit} placeholder="imposta" onSave={onSave} />
      </div>
    </div>
  );
}

// ── Composer note/task inline (note = mail.message; task = mail.activity con data) ──
function NoteTaskComposer({ leadId, onDone }: { leadId: number; onDone: (t: { msg: string; tone: Tone }) => void }) {
  const [mode, setMode] = useState<"note" | "task">("note");
  const [body, setBody] = useState("");
  const [due, setDue] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (busy) return;
    setBusy(true);
    try {
      const r = mode === "note"
        ? await postLeadNote(leadId, body)
        : await createLeadActivity(leadId, body, due);
      if (r.ok) { setBody(""); setDue(""); onDone({ msg: r.message, tone: "success" }); }
      else onDone({ msg: r.message, tone: "danger" });
    } catch (e) {
      onDone({ msg: (e as Error).message, tone: "danger" });
    } finally { setBusy(false); }
  }

  const canSubmit = body.trim() !== "" && (mode === "note" || /^\d{4}-\d{2}-\d{2}$/.test(due));
  return (
    <div className="card" style={{ padding: 12 }}>
      <div className="row" style={{ gap: 6, marginBottom: 8 }}>
        <button className="btn-mini" onClick={() => setMode("note")}
          style={mode === "note" ? { background: "var(--accent)", color: "#fff", borderColor: "var(--accent)" } : undefined}>Nota</button>
        <button className="btn-mini" onClick={() => setMode("task")}
          style={mode === "task" ? { background: "var(--accent)", color: "#fff", borderColor: "var(--accent)" } : undefined}>Task</button>
      </div>
      <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={2}
        placeholder={mode === "note" ? "Scrivi una nota interna…" : "Cosa va fatto…"}
        style={{ width: "100%", fontSize: 13, padding: "7px 9px", borderRadius: "var(--r-md)", border: "1px solid var(--line-2)", resize: "vertical", fontFamily: "inherit" }} />
      <div className="row" style={{ justifyContent: "space-between", marginTop: 8, gap: 8 }}>
        {mode === "task" ? (
          <input type="date" value={due} onChange={(e) => setDue(e.target.value)}
            style={{ fontSize: 12, padding: "5px 8px", borderRadius: "var(--r-md)", border: "1px solid var(--line-2)" }} />
        ) : <span />}
        <button className="btn-primary" onClick={submit} disabled={!canSubmit || busy}>
          {busy ? "Salvo…" : mode === "note" ? "Aggiungi nota" : "Pianifica task"}
        </button>
      </div>
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

function SignalRow({ label, value, pill }: { label: string; value: string; pill?: React.ReactNode }) {
  return (
    <div className="row" style={{ justifyContent: "space-between", gap: 8 }}>
      <div style={{ minWidth: 0 }}>
        <div className="muted" style={{ fontSize: 11 }}>{label}</div>
        <div className="ell" style={{ fontSize: 13, fontWeight: 600 }}>{value}</div>
      </div>
      {pill ?? null}
    </div>
  );
}

function OrderRow({ name, amount, state, date }: { name: string; amount: number; state: string; date: string | null }) {
  return (
    <div className="row" style={{ justifyContent: "space-between", gap: 8 }}>
      <div style={{ minWidth: 0 }}>
        <div className="ell" style={{ fontSize: 12, fontWeight: 600 }}>{name}</div>
        <div className="muted" style={{ fontSize: 11 }}>{date ? dateLabel(date) : state}</div>
      </div>
      <span style={{ fontSize: 12, fontWeight: 600 }}>{moneyCompact(amount)}</span>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <div className="muted" style={{ fontSize: 12 }}>{text}</div>;
}
function Skeleton() {
  return <div className="muted" style={{ fontSize: 12 }}>Carico…</div>;
}
