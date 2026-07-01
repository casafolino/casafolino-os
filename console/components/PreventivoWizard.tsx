"use client";
// Fase 1 — Wizard "da chiamata a preventivo". Ora consuma il componente condiviso PartnerPicker
// come primo step (azienda+contatto), poi Opportunità → Azione. La logica partner NON vive più qui.
// Ogni scrittura passa dai metodi gated (manager-only + audit). console_api non scrive mai in diretta.
import { useState } from "react";
import { createQuotation } from "@/lib/wizard";
import { createLeadRich } from "@/lib/create";
import { searchProducts, type ProductHit } from "@/lib/campionatura";
import { CatalogModal } from "@/components/CatalogModal";
import { PartnerPicker } from "@/components/PartnerPicker";
import { BP } from "@/lib/basePath";

function inp(bad = false): React.CSSProperties {
  return { width: "100%", padding: "8px 10px", borderRadius: 8, fontSize: 13,
    border: bad ? "1px solid var(--danger)" : "1px solid var(--line)", background: "var(--paper)" };
}

function Modal({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: 16 }}>
      <div className="card" onClick={(e) => e.stopPropagation()} style={{ width: "min(560px,100%)", maxHeight: "92vh", overflow: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
        {children}
      </div>
    </div>
  );
}

function Steps({ step }: { step: number }) {
  const labels = ["Partner", "Opportunità", "Azione"];
  return (
    <div className="row" style={{ gap: 6 }}>
      {labels.map((l, i) => (
        <div key={i} className="row" style={{ gap: 6, opacity: i + 1 === step ? 1 : 0.45 }}>
          <span className="opdot" style={{ background: i + 1 <= step ? "var(--accent)" : "var(--line)" }} />
          <span style={{ fontSize: 12, fontWeight: i + 1 === step ? 700 : 500 }}>{l}</span>
          {i < 2 ? <span className="muted" style={{ fontSize: 12 }}>›</span> : null}
        </div>
      ))}
    </div>
  );
}

export function PreventivoWizard({ label = "Nuovo preventivo" }: { label?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="btn-primary" onClick={() => setOpen(true)}>{label}</button>
      {open ? <WizardModal onClose={() => setOpen(false)} /> : null}
    </>
  );
}

export function WizardModal({ onClose, initialCompany }: { onClose: () => void; initialCompany?: { id: number; name: string } }) {
  // Dossier: partner già noto → salta il PartnerPicker e parte da "Opportunità" (step 2).
  const [step, setStep] = useState(initialCompany ? 2 : 1); // 1 = PartnerPicker, 2 = Opportunità, 3 = Azione
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [companyId, setCompanyId] = useState<number | null>(initialCompany?.id ?? null);
  const [companyName, setCompanyName] = useState(initialCompany?.name ?? "");
  const [leadId, setLeadId] = useState<number | null>(null);
  const [interest, setInterest] = useState<ProductHit[]>([]);

  function guard<T>(fn: () => Promise<T>) {
    setBusy(true); setErr(null);
    return fn().catch((e) => { setErr((e as Error).message); throw e; }).finally(() => setBusy(false));
  }

  return (
    <Modal onClose={onClose}>
      <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ fontWeight: 700, fontSize: 16 }}>Da chiamata a preventivo</div>
        <button className="btn-mini" onClick={onClose}>✕</button>
      </div>
      <Steps step={step} />
      {err ? <div style={{ fontSize: 12, color: "var(--danger)" }}>{err}</div> : null}

      {step === 1 ? (
        <PartnerPicker
          intro="Chi è il cliente? Trova o crea azienda e contatto."
          onCancel={onClose}
          onResolved={({ companyId, companyName }) => {
            setCompanyId(companyId); setCompanyName(companyName); setStep(2);
          }}
        />
      ) : null}

      {step === 2 ? (
        <Step3
          busy={busy} guard={guard} companyId={companyId} companyName={companyName}
          interest={interest} setInterest={setInterest}
          onBack={() => setStep(1)} onDone={(lid) => { setLeadId(lid); setStep(3); }}
        />
      ) : null}

      {step === 3 ? (
        <Step4
          busy={busy} guard={guard} companyId={companyId} leadId={leadId} interest={interest}
          onClose={onClose}
        />
      ) : null}
    </Modal>
  );
}

// ── Step Opportunità ──────────────────────────────────────────────────────────
function Step3({ busy, guard, companyId, companyName, interest, setInterest, onBack, onDone }: {
  busy: boolean; guard: <T>(f: () => Promise<T>) => Promise<T>; companyId: number | null; companyName: string;
  interest: ProductHit[]; setInterest: (p: ProductHit[]) => void; onBack: () => void; onDone: (leadId: number) => void;
}) {
  const [title, setTitle] = useState(companyName ? `Opportunità ${companyName}` : "");
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<ProductHit[]>([]);

  async function run() { if (q.trim()) setHits((await searchProducts(q.trim())).slice(0, 6)); }
  async function save() {
    const r = await guard(() => createLeadRich({ data: { name: title }, partnerId: companyId ?? undefined }));
    if (r.leadId) onDone(r.leadId);
  }
  return (
    <div style={{ display: "grid", gap: 10 }}>
      <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Titolo opportunità" style={inp(!title.trim())} />
      <div className="muted" style={{ fontSize: 12 }}>Interesse prodotto</div>
      {interest.length > 0 ? (
        <div className="row" style={{ gap: 6, flexWrap: "wrap" }}>
          {interest.map((p) => (
            <span key={p.id} className="chip" style={{ cursor: "pointer" }} onClick={() => setInterest(interest.filter((x) => x.id !== p.id))}>
              {p.name} ✕
            </span>
          ))}
        </div>
      ) : null}
      <div className="row" style={{ gap: 8 }}>
        <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") run(); }} placeholder="cerca creme, mieli, crispy chili…" style={inp()} />
        <button className="btn-mini" onClick={run}>cerca</button>
      </div>
      {hits.length > 0 ? (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          {hits.map((p) => (
            <button key={p.id} className="row" style={{ width: "100%", padding: "7px 10px", textAlign: "left", borderTop: "1px solid var(--line)", background: "transparent" }}
              onClick={() => { if (!interest.find((x) => x.id === p.id)) setInterest([...interest, p]); setHits([]); setQ(""); }}>
              <span style={{ fontWeight: 600 }}>{p.name}</span><span className="muted grow ell" style={{ fontSize: 12 }}>{p.code}</span>
            </button>
          ))}
        </div>
      ) : null}
      <div className="row" style={{ justifyContent: "space-between" }}>
        <button className="btn-mini" onClick={onBack}>‹ Indietro</button>
        <button className="btn-primary" disabled={busy || !title.trim()} onClick={save}>Crea opportunità</button>
      </div>
    </div>
  );
}

// ── Step Azione commerciale ───────────────────────────────────────────────────
function Step4({ busy, guard, companyId, leadId, interest, onClose }: {
  busy: boolean; guard: <T>(f: () => Promise<T>) => Promise<T>; companyId: number | null; leadId: number | null;
  interest: ProductHit[]; onClose: () => void;
}) {
  const [result, setResult] = useState<string | null>(null);

  async function quote() {
    if (!companyId) { setResult("Manca l'azienda."); return; }
    const r = await guard(() => createQuotation({
      partnerId: companyId, leadId: leadId ?? undefined,
      lines: interest.map((p) => ({ productId: p.id, qty: 1 })),
    }));
    setResult(r.orderId ? `Quotazione bozza ${r.name} creata (€${r.amountTotal ?? 0}).` : (r.message || "Errore."));
  }

  const [catalogOpen, setCatalogOpen] = useState(false);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div className="muted" style={{ fontSize: 12 }}>Opportunità creata. Scegli l'azione commerciale.</div>
      <div className="row" style={{ gap: 10 }}>
        <button className="btn-secondary" style={{ flex: 1 }} disabled={!companyId && !leadId} onClick={() => setCatalogOpen(true)}>
          Invia catalogo
        </button>
        <button className="btn-primary" style={{ flex: 1 }} disabled={busy || !companyId || interest.length === 0} onClick={quote}>
          Crea quotazione
        </button>
      </div>
      {catalogOpen ? <CatalogModal partnerId={companyId ?? undefined} leadId={leadId ?? undefined} onClose={() => setCatalogOpen(false)} /> : null}
      {interest.length === 0 ? <div className="muted" style={{ fontSize: 12 }}>Aggiungi prodotti allo step Opportunità per la quotazione.</div> : null}
      {result ? <div style={{ fontSize: 13, color: "var(--ok)" }}>{result}</div> : null}
      <div className="row" style={{ justifyContent: "flex-end", gap: 8 }}>
        {leadId ? <a className="btn-mini" href={`${BP}/lead/${leadId}`}>Apri opportunità</a> : null}
        <button className="btn-mini" onClick={onClose}>Chiudi</button>
      </div>
    </div>
  );
}
