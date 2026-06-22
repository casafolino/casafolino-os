"use client";
// Brief 9 — Crea lead / Crea dossier rapidi, ubiqui. Scheletro Brief 8 (modal, revisione umana,
// niente auto-save). Manager-only (gateway). Da mail → titolo lead suggerito IA (editabile).
import { useEffect, useState } from "react";
import { suggestLead, createLeadRich, createDossier } from "@/lib/create";

function Modal({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: 16 }}>
      <div className="card" onClick={(e) => e.stopPropagation()} style={{ width: "min(460px,100%)", maxHeight: "90vh", overflow: "auto", padding: 18, display: "flex", flexDirection: "column", gap: 12 }}>
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontWeight: 700, fontSize: 16 }}>{title}</div>
          <button className="btn-mini" onClick={onClose}>✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

function inputStyle(): React.CSSProperties {
  return { width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--line)", fontSize: 13 };
}

// ── Crea lead ───────────────────────────────────────────────────────────────
export function QuickCreateLead({ partnerId, fromMailId, small = true, label = "Crea lead" }: {
  partnerId?: number | null; fromMailId?: number; small?: boolean; label?: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className={small ? "btn-mini" : "btn-secondary"} onClick={() => setOpen(true)}>{label}</button>
      {open ? <LeadModal partnerId={partnerId} fromMailId={fromMailId} onClose={() => setOpen(false)} /> : null}
    </>
  );
}

function LeadModal({ partnerId, fromMailId, onClose }: { partnerId?: number | null; fromMailId?: number; onClose: () => void }) {
  const [name, setName] = useState("");
  const [emailFrom, setEmailFrom] = useState("");
  const [pid, setPid] = useState<number | null>(partnerId ?? null);
  const [aiUsed, setAiUsed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  useEffect(() => {
    if (!fromMailId) return;
    suggestLead(fromMailId).then((s) => {
      if (s.title) setName(s.title);
      if (s.emailFrom) setEmailFrom(s.emailFrom);
      if (s.partnerId) setPid(s.partnerId);
      setAiUsed(!!s.aiUsed);
    }).catch(() => {});
  }, [fromMailId]);

  function onName(e: React.ChangeEvent<HTMLInputElement>) { setName(e.target.value); }

  async function save() {
    setBusy(true); setErr(null);
    try {
      const r = await createLeadRich({ data: { name, emailFrom: emailFrom || undefined }, partnerId: pid ?? undefined, fromMailId });
      if (r.ok) setDone(`Lead creato: ${r.name} (${r.stageName})`); else setErr(r.message ?? "errore");
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <Modal title="Crea lead" onClose={onClose}>
      {err ? <div style={{ color: "var(--danger)", fontSize: 13 }}>{err}</div> : null}
      {done ? (
        <>
          <div className="chip" style={{ background: "var(--ok-t)", color: "var(--ok)", alignSelf: "flex-start" }}>{done} ✓</div>
          <button className="btn-primary" onClick={onClose} style={{ alignSelf: "flex-end" }}>Chiudi</button>
        </>
      ) : (
        <>
          <div>
            <label className="muted" style={{ fontSize: 11 }}>Titolo {aiUsed && name ? <span className="chip" style={{ fontSize: 9, padding: "0 5px" }}>IA</span> : null}</label>
            <input value={name} onChange={onName} placeholder="Titolo opportunità" style={inputStyle()} />
          </div>
          <div className="muted" style={{ fontSize: 12 }}>Stage: <b>Primo Contatto</b> (default) · Owner: tu</div>
          <button className="btn-primary" onClick={save} disabled={busy || !name.trim()} style={{ alignSelf: "flex-end" }}>
            {busy ? "Creo…" : "Crea lead"}
          </button>
        </>
      )}
    </Modal>
  );
}

// ── Crea dossier ─────────────────────────────────────────────────────────────
export function QuickCreateDossier({ partnerId, leadId, defaultName, small = true, label = "Crea dossier", disabled = false }: {
  partnerId?: number | null; leadId?: number | null; defaultName?: string; small?: boolean; label?: string; disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className={small ? "btn-mini" : "btn-secondary"} onClick={() => setOpen(true)} disabled={disabled}>{label}</button>
      {open ? <DossierModal partnerId={partnerId} leadId={leadId} defaultName={defaultName} onClose={() => setOpen(false)} /> : null}
    </>
  );
}

function DossierModal({ partnerId, leadId, defaultName, onClose }: { partnerId?: number | null; leadId?: number | null; defaultName?: string; onClose: () => void }) {
  const [name, setName] = useState(defaultName ?? "");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  function onName(e: React.ChangeEvent<HTMLInputElement>) { setName(e.target.value); }

  async function save() {
    setBusy(true); setErr(null);
    try {
      const r = await createDossier({ data: { name }, partnerId: partnerId ?? undefined, leadId: leadId ?? undefined });
      if (r.ok) setDone(`Dossier creato: ${r.name}`); else setErr(r.message ?? "errore");
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <Modal title="Crea dossier" onClose={onClose}>
      {err ? <div style={{ color: "var(--danger)", fontSize: 13 }}>{err}</div> : null}
      {done ? (
        <>
          <div className="chip" style={{ background: "var(--ok-t)", color: "var(--ok)", alignSelf: "flex-start" }}>{done} ✓</div>
          <button className="btn-primary" onClick={onClose} style={{ alignSelf: "flex-end" }}>Chiudi</button>
        </>
      ) : (
        <>
          <div>
            <label className="muted" style={{ fontSize: 11 }}>Nome dossier</label>
            <input value={name} onChange={onName} placeholder="Nome dossier" style={inputStyle()} />
          </div>
          <div className="muted" style={{ fontSize: 12 }}>Status: <b>Esplorativo</b> · {partnerId ? "collegato al contatto" : leadId ? "collegato al lead" : "nessun collegamento"}</div>
          <button className="btn-primary" onClick={save} disabled={busy || !name.trim()} style={{ alignSelf: "flex-end" }}>
            {busy ? "Creo…" : "Crea dossier"}
          </button>
        </>
      )}
    </Modal>
  );
}
