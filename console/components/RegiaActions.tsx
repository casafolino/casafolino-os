"use client";
// Regia — 4 azioni rapide sempre visibili (Brief: bottoni, non menu). Blank: ogni azione
// chiede prima il partner (PartnerPicker condiviso), poi parte. Riusa i componenti/gateway
// esistenti (nessun nuovo write-path). Le stesse 4 azioni, precompilate, vivono in DossierActions.
import { useState } from "react";
import { PartnerPicker, type PartnerResolved } from "@/components/PartnerPicker";
import { WizardModal } from "@/components/PreventivoWizard";
import { EmailCompose } from "@/components/CreaModal";
import { CampionaturaModal } from "@/components/CampionaturaButton";
import { commitQuicktask } from "@/lib/quicktask";
import type { Account } from "@/components/Composer";
import type { LibraryItem, MailTemplate } from "@/lib/bundle";

type Verb = "preventivo" | "mail" | "task" | "campione";

const VERB_LABEL: Record<Verb, string> = {
  preventivo: "Nuovo preventivo",
  mail: "Scrivi mail",
  task: "Assegna task",
  campione: "Registra campione",
};

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

function Launcher({ verb, primary, accounts, library, templates }: {
  verb: Verb; primary?: boolean; accounts: Account[]; library: LibraryItem[]; templates: MailTemplate[];
}) {
  const [open, setOpen] = useState(false);
  const [partner, setPartner] = useState<PartnerResolved | null>(null);
  function reset() { setOpen(false); setPartner(null); }

  return (
    <>
      <button className={primary ? "btn-primary" : "btn-secondary"} onClick={() => { setPartner(null); setOpen(true); }}>
        {VERB_LABEL[verb]}
      </button>

      {open && !partner ? (
        <Modal title={VERB_LABEL[verb]} onClose={reset}>
          <PartnerPicker intro="Quale cliente? Trovalo o crealo, poi parte l'azione." contactStep={false} onResolved={setPartner} onCancel={reset} />
        </Modal>
      ) : null}

      {open && partner && verb === "preventivo" ? (
        <WizardModal onClose={reset} initialCompany={{ id: partner.companyId, name: partner.companyName }} />
      ) : null}
      {open && partner && verb === "mail" ? (
        <EmailCompose companyId={partner.companyId} companyName={partner.companyName} accounts={accounts} library={library} templates={templates} onClose={reset} />
      ) : null}
      {open && partner && verb === "task" ? (
        <Modal title="Assegna task" onClose={reset}>
          <TaskForm partnerId={partner.companyId} companyName={partner.companyName} onClose={reset} />
        </Modal>
      ) : null}
      {open && partner && verb === "campione" ? (
        <CampionaturaModal partnerId={partner.companyId} onClose={reset} />
      ) : null}
    </>
  );
}

export function RegiaActions({ accounts, library, templates }: { accounts: Account[]; library: LibraryItem[]; templates: MailTemplate[] }) {
  return (
    <div className="row" style={{ gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
      <Launcher verb="preventivo" primary accounts={accounts} library={library} templates={templates} />
      <Launcher verb="mail" accounts={accounts} library={library} templates={templates} />
      <Launcher verb="task" accounts={accounts} library={library} templates={templates} />
      <Launcher verb="campione" accounts={accounts} library={library} templates={templates} />
    </div>
  );
}
