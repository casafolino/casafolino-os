"use client";
// WI-B — Barra azioni rapide (azione-first). Ogni verbo monta lo STESSO PartnerPicker come primo
// step ("quale partner?"), poi parte l'azione. Il contatto è il mattone di tutto.
// Verbi partner-first + scorciatoie pure (Inbox/Pipeline). La barra "Interpreta" (QuickTaskBar)
// resta complementare: i verbi sono la via "clicco e il picker mi guida".
import { useState } from "react";
import Link from "next/link";
import { PreventivoWizard } from "@/components/PreventivoWizard";
import { PartnerPicker, type PartnerResolved } from "@/components/PartnerPicker";
import { CatalogModal } from "@/components/CatalogModal";
import { CampionaturaModal } from "@/components/CampionaturaButton";
import { commitQuicktask } from "@/lib/quicktask";
import { BP } from "@/lib/basePath";

type Verb = "task" | "mail" | "campione" | "dossier" | "followup";

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

// Form compatto per task / follow-up (riusa il commit gated). Assegnatario → operatore (default backend).
function TaskForm({ verb, partnerId, companyName, onClose }: { verb: "task" | "followup"; partnerId: number; companyName: string; onClose: () => void }) {
  const [summary, setSummary] = useState("");
  const [due, setDue] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  async function submit() {
    setBusy(true); setErr(null);
    try {
      const r = await commitQuicktask({
        action_type: verb === "followup" ? "follow-up" : "task",
        partner_id: partnerId,
        summary: summary || undefined,
        due_date: due || undefined,
      });
      if (r.ok) setOk(verb === "followup" ? "Follow-up creato ✓" : "Task creato ✓");
      else setErr(r.message || "Errore.");
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  const inp: React.CSSProperties = { width: "100%", padding: "8px 10px", borderRadius: 8, fontSize: 13, border: "1px solid var(--line)", background: "var(--paper)" };

  if (ok) {
    return (
      <div style={{ display: "grid", gap: 12 }}>
        <div style={{ fontSize: 13, color: "var(--ok)" }}>{ok}</div>
        <button className="btn-primary" style={{ alignSelf: "flex-end" }} onClick={onClose}>Chiudi</button>
      </div>
    );
  }
  return (
    <div style={{ display: "grid", gap: 10 }}>
      <div className="muted" style={{ fontSize: 12 }}>{verb === "followup" ? "Follow-up" : "Task"} su {companyName}</div>
      <input value={summary} onChange={(e) => setSummary(e.target.value)} placeholder={verb === "followup" ? "Cosa ricordare (es. richiamare)" : "Titolo task"} style={inp} />
      {verb === "followup" ? (
        <input type="date" value={due} onChange={(e) => setDue(e.target.value)} style={inp} />
      ) : null}
      {err ? <div style={{ fontSize: 12, color: "var(--danger)" }}>{err}</div> : null}
      <button className="btn-primary" style={{ alignSelf: "flex-end" }} disabled={busy || (verb === "task" && !summary.trim())} onClick={submit}>
        {busy ? "Creo…" : (verb === "followup" ? "Crea follow-up" : "Crea task")}
      </button>
    </div>
  );
}

// Verbo generico azione-first: apre il picker, poi instrada all'azione.
function ActionLauncher({ verb, label }: { verb: Verb; label: string }) {
  const [open, setOpen] = useState(false);
  const [resolved, setResolved] = useState<PartnerResolved | null>(null);

  function start() { setResolved(null); setOpen(true); }
  function reset() { setOpen(false); setResolved(null); }

  function handleResolved(r: PartnerResolved) {
    if (verb === "dossier") { window.location.href = `${BP}/partner/${r.companyId}`; return; }
    setResolved(r);
  }

  const verbLabel: Record<Verb, string> = {
    task: "Assegna task", mail: "Scrivi mail", campione: "Registra campione",
    dossier: "Apri dossier", followup: "Aggiungi follow-up",
  };

  return (
    <>
      <button className="btn-secondary" onClick={start}>{label}</button>

      {open && !resolved ? (
        <Modal title={verbLabel[verb]} onClose={reset}>
          <PartnerPicker intro="Quale partner? Trovalo o crealo, poi parte l'azione." contactStep={false} onResolved={handleResolved} onCancel={reset} />
        </Modal>
      ) : null}

      {open && resolved && (verb === "task" || verb === "followup") ? (
        <Modal title={verbLabel[verb]} onClose={reset}>
          <TaskForm verb={verb} partnerId={resolved.companyId} companyName={resolved.companyName} onClose={reset} />
        </Modal>
      ) : null}

      {open && resolved && verb === "mail" ? (
        <CatalogModal partnerId={resolved.companyId} onClose={reset} />
      ) : null}

      {open && resolved && verb === "campione" ? (
        <CampionaturaModal partnerId={resolved.companyId} onClose={reset} />
      ) : null}
    </>
  );
}

export function ActionBar() {
  return (
    <div style={{ marginBottom: 12 }}>
      <div className="row" style={{ gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <PreventivoWizard label="Nuovo preventivo" />
        <ActionLauncher verb="task" label="Assegna task" />
        <ActionLauncher verb="mail" label="Scrivi mail" />
        <ActionLauncher verb="campione" label="Registra campione" />
        <ActionLauncher verb="followup" label="Aggiungi follow-up" />
        <ActionLauncher verb="dossier" label="Apri dossier" />
        <span className="muted" style={{ fontSize: 12, padding: "0 2px" }}>·</span>
        <Link href="/inbox" className="btn-mini">Inbox</Link>
        <Link href="/pipeline" className="btn-mini">Pipeline</Link>
      </div>
      <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
        Ogni verbo chiede prima il partner, poi parte l'azione — oppure scrivi la frase qui sotto.
      </div>
    </div>
  );
}
