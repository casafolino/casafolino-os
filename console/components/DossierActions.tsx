"use client";
// Dossier — 4 azioni rapide PRECOMPILATE col partner corrente (Brief Dossier).
// Riusa i componenti/gateway esistenti: nessun nuovo write-path.
//  - Nuovo preventivo → WizardModal(initialCompany) → console_create_quotation
//  - Scrivi mail      → EmailCompose (Composer generico, destinatario = email cliente)
//  - Assegna task     → commitQuicktask(action_type=task, partner_id) → cf.task
//  - Registra campione→ CampionaturaModal(partnerId) → console_crea_campionatura
import { useState } from "react";
import { WizardModal } from "@/components/PreventivoWizard";
import { EmailCompose } from "@/components/CreaModal";
import { CampionaturaModal } from "@/components/CampionaturaButton";
import { commitQuicktask } from "@/lib/quicktask";
import type { Account } from "@/components/Composer";
import type { LibraryItem, MailTemplate } from "@/lib/bundle";

type Action = "preventivo" | "mail" | "task" | "campione" | null;

const inp: React.CSSProperties = {
  width: "100%", padding: "8px 10px", borderRadius: 8, fontSize: 13,
  border: "1px solid var(--line)", background: "var(--paper)",
};

function Modal({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: 16 }}>
      <div className="card" onClick={(e) => e.stopPropagation()} style={{ width: "min(520px,100%)", maxHeight: "92vh", overflow: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontWeight: 700, fontSize: 16 }}>{title}</div>
          <button className="btn-mini" onClick={onClose}>✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

// Task precompilato sul partner corrente.
function TaskForm({ partnerId, companyName, onClose }: { partnerId: number; companyName: string; onClose: () => void }) {
  const [summary, setSummary] = useState("");
  const [due, setDue] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState(false);

  async function submit() {
    setBusy(true); setErr(null);
    try {
      const r = await commitQuicktask({ action_type: "task", partner_id: partnerId, summary: summary || undefined, due_date: due || undefined });
      if (r.ok) setOk(true); else setErr(r.message || "Errore.");
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  if (ok) return (
    <div style={{ display: "grid", gap: 12 }}>
      <div style={{ fontSize: 13, color: "var(--ok)" }}>Task creato per {companyName} ✓</div>
      <button className="btn-primary" style={{ alignSelf: "flex-end" }} onClick={onClose}>Chiudi</button>
    </div>
  );
  return (
    <div style={{ display: "grid", gap: 10 }}>
      <div className="muted" style={{ fontSize: 12 }}>Task su {companyName}</div>
      <input value={summary} onChange={(e) => setSummary(e.target.value)} placeholder="Titolo task" style={inp} />
      <input type="date" value={due} onChange={(e) => setDue(e.target.value)} style={inp} />
      {err ? <div style={{ fontSize: 12, color: "var(--danger)" }}>{err}</div> : null}
      <button className="btn-primary" style={{ alignSelf: "flex-end" }} disabled={busy || !summary.trim()} onClick={submit}>
        {busy ? "Creo…" : "Crea task"}
      </button>
    </div>
  );
}

export function DossierActions({
  partnerId, companyName, accounts, library, templates,
}: {
  partnerId: number;
  companyName: string;
  accounts: Account[];
  library: LibraryItem[];
  templates: MailTemplate[];
}) {
  const [action, setAction] = useState<Action>(null);
  const close = () => setAction(null);

  return (
    <>
      <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
        <button className="btn-primary" onClick={() => setAction("preventivo")}>Nuovo preventivo</button>
        <button className="btn-secondary" onClick={() => setAction("mail")}>Scrivi mail</button>
        <button className="btn-secondary" onClick={() => setAction("task")}>Assegna task</button>
        <button className="btn-secondary" onClick={() => setAction("campione")}>Registra campione</button>
      </div>

      {action === "preventivo" ? (
        <WizardModal onClose={close} initialCompany={{ id: partnerId, name: companyName }} />
      ) : null}
      {action === "mail" ? (
        <EmailCompose companyId={partnerId} companyName={companyName} accounts={accounts} library={library} templates={templates} onClose={close} />
      ) : null}
      {action === "task" ? (
        <Modal title="Assegna task" onClose={close}>
          <TaskForm partnerId={partnerId} companyName={companyName} onClose={close} />
        </Modal>
      ) : null}
      {action === "campione" ? (
        <CampionaturaModal partnerId={partnerId} onClose={close} />
      ) : null}
    </>
  );
}
