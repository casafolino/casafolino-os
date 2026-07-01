"use client";
// Modal unico "Crea": step 1 = tipo (pill), step 2 = form/target contestuale.
// Sostituisce i 5 bottoni ActionBar. MAX riuso, ZERO backend change (riusa le route esistenti):
//  - Preventivo → WizardModal (PartnerPicker→lead→quotazione), come oggi.
//  - Task       → commitQuicktask action=task (assegnatario persona OR Pool, logica Phase 2).
//  - Email      → PartnerPicker(cliente) → CatalogModal (invio catalogo, come oggi).
//  - Campionat. → PartnerPicker(cliente) → CampionaturaModal (cliente + 3 assegnatari).
//  - Follow-up  → toggle Cliente/Interno: Cliente = mail.activity (action=follow-up);
//                 Interno = cf.task assegnato al collega (action=task) — nessun modello nuovo,
//                 perché un follow-up senza cliente hard-raise lato backend (vedi brief).
// "Apri dossier" resta bottone separato in ActionBar (non è creazione).
import { useEffect, useState } from "react";
import { PartnerPicker, type PartnerResolved } from "@/components/PartnerPicker";
import { Composer, type Account } from "@/components/Composer";
import { CampionaturaModal } from "@/components/CampionaturaButton";
import { WizardModal } from "@/components/PreventivoWizard";
import { commitQuicktask } from "@/lib/quicktask";
import { getTaskBoard } from "@/lib/lavboard";
import type { LibraryItem, MailTemplate } from "@/lib/bundle";
import { BP } from "@/lib/basePath";

type CreaType = "preventivo" | "task" | "email" | "campionatura" | "followup";

const TYPES: { key: CreaType; label: string; icon: string; hint: string }[] = [
  { key: "preventivo", label: "Preventivo", icon: "€", hint: "Cliente → quotazione" },
  { key: "task", label: "Task", icon: "✓", hint: "Assegna a persona interna oppure lascia in Pool" },
  { key: "email", label: "Email", icon: "✉", hint: "Cliente → invio catalogo" },
  { key: "campionatura", label: "Campionatura", icon: "◫", hint: "Cliente + assegnatari (chi esegue)" },
  { key: "followup", label: "Follow-up", icon: "⏰", hint: "Cliente oppure interno (collega)" },
];

const inp: React.CSSProperties = {
  width: "100%", padding: "8px 10px", borderRadius: 8, fontSize: 13,
  border: "1px solid var(--line)", background: "var(--paper)",
};

function Modal({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: 16 }}>
      <div className="card" onClick={(e) => e.stopPropagation()} style={{ width: "min(560px,100%)", maxHeight: "92vh", overflow: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontWeight: 700, fontSize: 16 }}>{title}</div>
          <button className="btn-mini" onClick={onClose}>✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

// Elenco assegnatari (hr.employee) dalle colonne board (riuso Phase 2, manager-gated come il resto).
function useAssignees(): { id: number; name: string }[] {
  const [list, setList] = useState<{ id: number; name: string }[]>([]);
  useEffect(() => {
    getTaskBoard()
      .then((b) => {
        if (b && Array.isArray(b.columns)) {
          setList(b.columns
            .filter((c) => c.kind === "assignee" && typeof c.employeeId === "number")
            .map((c) => ({ id: c.employeeId as number, name: c.name })));
        }
      })
      .catch(() => { /* silenzioso: il campo persona resta vuoto, Pool sempre disponibile */ });
  }, []);
  return list;
}

// ---- Task: assegna a persona OPPURE Pool (riusa commitQuicktask action=task) ----
function TaskBranch({ onClose }: { onClose: () => void }) {
  const assignees = useAssignees();
  const [summary, setSummary] = useState("");
  const [due, setDue] = useState("");
  const [pool, setPool] = useState(true);
  const [empId, setEmpId] = useState<number | "">("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  async function submit() {
    setBusy(true); setErr(null);
    try {
      const r = await commitQuicktask({
        action_type: "task",
        summary: summary || undefined,
        due_date: due || undefined,
        assignee_employee_id: pool ? undefined : (empId ? Number(empId) : undefined),
      });
      if (r.ok) setOk(pool ? "Task creato in Pool ✓" : "Task assegnato ✓");
      else setErr(r.message || "Errore.");
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  if (ok) return <Done msg={ok} onClose={onClose} />;
  const canSubmit = summary.trim().length > 0 && (pool || !!empId);
  return (
    <div style={{ display: "grid", gap: 10 }}>
      <input value={summary} onChange={(e) => setSummary(e.target.value)} placeholder="Titolo task" style={inp} />
      <input type="date" value={due} onChange={(e) => setDue(e.target.value)} style={inp} />
      <div className="row" style={{ gap: 8 }}>
        <button className={pool ? "btn-primary" : "btn-secondary"} onClick={() => setPool(true)}>Pool</button>
        <button className={!pool ? "btn-primary" : "btn-secondary"} onClick={() => setPool(false)}>Assegna a persona</button>
      </div>
      {!pool ? (
        <select value={empId} onChange={(e) => setEmpId(e.target.value ? Number(e.target.value) : "")} style={inp}>
          <option value="">Scegli assegnatario…</option>
          {assignees.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
      ) : null}
      {err ? <div style={{ fontSize: 12, color: "var(--danger)" }}>{err}</div> : null}
      <button className="btn-primary" style={{ alignSelf: "flex-end" }} disabled={busy || !canSubmit} onClick={submit}>
        {busy ? "Creo…" : "Crea task"}
      </button>
    </div>
  );
}

// ---- Follow-up: Cliente (mail.activity) OPPURE Interno (cf.task su collega) ----
function FollowupBranch({ onClose }: { onClose: () => void }) {
  const assignees = useAssignees();
  const [mode, setMode] = useState<"cliente" | "interno">("cliente");
  const [partner, setPartner] = useState<PartnerResolved | null>(null);
  const [summary, setSummary] = useState("");
  const [due, setDue] = useState("");
  const [empId, setEmpId] = useState<number | "">("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  async function submit() {
    setBusy(true); setErr(null);
    try {
      const r = mode === "cliente"
        ? await commitQuicktask({ action_type: "follow-up", partner_id: partner!.companyId, summary: summary || undefined, due_date: due || undefined })
        : await commitQuicktask({ action_type: "task", assignee_employee_id: empId ? Number(empId) : undefined, summary: summary || undefined, due_date: due || undefined });
      if (r.ok) setOk("Follow-up creato ✓");
      else setErr(r.message || "Errore.");
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  if (ok) return <Done msg={ok} onClose={onClose} />;

  return (
    <div style={{ display: "grid", gap: 10 }}>
      <div className="row" style={{ gap: 8 }}>
        <button className={mode === "cliente" ? "btn-primary" : "btn-secondary"} onClick={() => setMode("cliente")}>Cliente</button>
        <button className={mode === "interno" ? "btn-primary" : "btn-secondary"} onClick={() => setMode("interno")}>Interno (collega)</button>
      </div>

      {mode === "cliente" && !partner ? (
        <PartnerPicker intro="Quale cliente?" contactStep={false} onResolved={setPartner} onCancel={onClose} />
      ) : (
        <>
          {mode === "cliente" ? (
            <div className="muted" style={{ fontSize: 12 }}>Cliente: {partner!.companyName}</div>
          ) : (
            <select value={empId} onChange={(e) => setEmpId(e.target.value ? Number(e.target.value) : "")} style={inp}>
              <option value="">Collega da controllare…</option>
              {assignees.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          )}
          <input value={summary} onChange={(e) => setSummary(e.target.value)} placeholder="Cosa ricordare (es. controllo esito campionatura)" style={inp} />
          <input type="date" value={due} onChange={(e) => setDue(e.target.value)} style={inp} />
          {err ? <div style={{ fontSize: 12, color: "var(--danger)" }}>{err}</div> : null}
          <button className="btn-primary" style={{ alignSelf: "flex-end" }}
            disabled={busy || !summary.trim() || (mode === "interno" && !empId)} onClick={submit}>
            {busy ? "Creo…" : "Crea follow-up"}
          </button>
        </>
      )}
    </div>
  );
}

function Done({ msg, onClose }: { msg: string; onClose: () => void }) {
  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div style={{ fontSize: 13, color: "var(--ok)" }}>{msg}</div>
      <button className="btn-primary" style={{ alignSelf: "flex-end" }} onClick={onClose}>Chiudi</button>
    </div>
  );
}

// Email = composer generico Odoo (gateway canonico console_send/reply), NON invio-catalogo.
// Precompila il destinatario con l'email del cliente scelto; il campo resta editabile
// (email generica / destinatario interno). Template nativi disponibili dal Composer.
function EmailCompose({ companyId, companyName, accounts, library, templates, onClose }: {
  companyId: number; companyName: string;
  accounts: Account[]; library: LibraryItem[]; templates: MailTemplate[]; onClose: () => void;
}) {
  const [email, setEmail] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    fetch(`${BP}/api/console/partner-bundle`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ partnerId: companyId }) })
      .then((r) => r.json())
      .then((b) => { if (alive) setEmail((b?.email ?? b?.partner?.email ?? "") as string); })
      .catch(() => { if (alive) setEmail(""); });
    return () => { alive = false; };
  }, [companyId]);
  if (email === null) return null; // attesa breve email cliente
  return (
    <Composer mode="new"
      target={{ id: 0, subject: "", senderEmail: email, senderName: companyName }}
      accounts={accounts} library={library} templates={templates} onClose={onClose} />
  );
}

export function CreaButton({ accounts, library, templates }: { accounts: Account[]; library: LibraryItem[]; templates: MailTemplate[] }) {
  const [open, setOpen] = useState(false);
  const [type, setType] = useState<CreaType | null>(null);
  const [partner, setPartner] = useState<PartnerResolved | null>(null);

  function reset() { setOpen(false); setType(null); setPartner(null); }
  function pick(t: CreaType) { setType(t); setPartner(null); }

  return (
    <>
      <button className="btn-primary" onClick={() => { reset(); setOpen(true); }}>+ Crea</button>
      {!open ? null
        // Modali auto-contenute (hanno backdrop proprio): renderizzate standalone.
        : type === "preventivo" ? <WizardModal onClose={reset} />
        : type === "email" && partner ? <EmailCompose companyId={partner.companyId} companyName={partner.companyName} accounts={accounts} library={library} templates={templates} onClose={reset} />
        : type === "campionatura" && partner ? <CampionaturaModal partnerId={partner.companyId} onClose={reset} />
        : (
          <Modal title="Crea" onClose={reset}>
            <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
              {TYPES.map((t) => (
                <button key={t.key} className={type === t.key ? "btn-primary" : "btn-secondary"} onClick={() => pick(t.key)}>
                  <span style={{ marginRight: 6 }}>{t.icon}</span>{t.label}
                </button>
              ))}
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              {type ? TYPES.find((t) => t.key === type)!.hint : "Scegli cosa creare."}
            </div>
            <div style={{ borderTop: "1px solid var(--line)", paddingTop: 12 }}>
              {type === "task" ? <TaskBranch onClose={reset} /> : null}
              {type === "followup" ? <FollowupBranch onClose={reset} /> : null}
              {type === "email" || type === "campionatura" ? (
                <PartnerPicker intro="Quale cliente? Trovalo o crealo, poi parte l'azione." contactStep={false} onResolved={setPartner} onCancel={() => setType(null)} />
              ) : null}
            </div>
          </Modal>
        )}
    </>
  );
}
