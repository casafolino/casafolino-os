"use client";
// Fase 1 — Wizard "da chiamata a preventivo". 4 step, uscita anticipata a ogni step.
// Step1 Azienda (P.IVA dedup+VIES / Email / Nome) → Step2 Contatto → Step3 Opportunità → Step4 Azione.
// Ogni scrittura passa dai metodi gated (manager-only + audit). console_api non scrive mai in diretta.
import { useState } from "react";
import { vatLookup, enrich007, createQuotation, type VatLookup } from "@/lib/wizard";
import { createCompany } from "@/lib/cockpit";
import { createContact } from "@/lib/enrich";
import { createLeadRich } from "@/lib/create";
import { universalSearch } from "@/lib/pipeline";
import { searchProducts, type ProductHit } from "@/lib/campionatura";
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
  const labels = ["Azienda", "Contatto", "Opportunità", "Azione"];
  return (
    <div className="row" style={{ gap: 6 }}>
      {labels.map((l, i) => (
        <div key={i} className="row" style={{ gap: 6, opacity: i + 1 === step ? 1 : 0.45 }}>
          <span className="opdot" style={{ background: i + 1 <= step ? "var(--accent)" : "var(--line)" }} />
          <span style={{ fontSize: 12, fontWeight: i + 1 === step ? 700 : 500 }}>{l}</span>
          {i < 3 ? <span className="muted" style={{ fontSize: 12 }}>›</span> : null}
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

function WizardModal({ onClose }: { onClose: () => void }) {
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [companyId, setCompanyId] = useState<number | null>(null);
  const [companyName, setCompanyName] = useState("");
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
        <Step1
          busy={busy} guard={guard}
          onDone={(id, name) => { setCompanyId(id); setCompanyName(name); setStep(2); }}
        />
      ) : null}

      {step === 2 ? (
        <Step2
          busy={busy} guard={guard} companyId={companyId} companyName={companyName}
          onBack={() => setStep(1)} onSkip={() => setStep(3)} onDone={() => setStep(3)}
        />
      ) : null}

      {step === 3 ? (
        <Step3
          busy={busy} guard={guard} companyId={companyId} companyName={companyName}
          interest={interest} setInterest={setInterest}
          onBack={() => setStep(2)} onDone={(lid) => { setLeadId(lid); setStep(4); }}
        />
      ) : null}

      {step === 4 ? (
        <Step4
          busy={busy} guard={guard} companyId={companyId} leadId={leadId} interest={interest}
          onClose={onClose}
        />
      ) : null}
    </Modal>
  );
}

// ── Step 1 — Azienda ──────────────────────────────────────────────────────────
function Step1({ busy, guard, onDone }: { busy: boolean; guard: <T>(f: () => Promise<T>) => Promise<T>; onDone: (id: number, name: string) => void }) {
  const [mode, setMode] = useState<"piva" | "email" | "nome">("piva");
  const [vat, setVat] = useState("");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [lk, setLk] = useState<VatLookup | null>(null);
  const [enr, setEnr] = useState<string>("");

  async function doLookup() {
    const r = await guard(() => vatLookup({ vat }));
    setLk(r);
    if (r.prefill?.name) setName(r.prefill.name);
  }
  async function doEnrich() {
    const r = await guard(() => enrich007({ name: name || lk?.prefill?.name || "", vat }));
    setEnr([r.enrichment.settore, r.enrichment.dimensione, r.enrichment.sito].filter(Boolean).join(" · "));
  }
  async function doCreate(nm: string, dom?: string, citta?: string) {
    const r = await guard(() => createCompany({ data: { nome: nm, dominio: dom, citta } }));
    if (r.partnerId) onDone(r.partnerId, r.name || nm);
  }
  async function doEmailSearch() {
    const r = await guard(() => universalSearch(email));
    const p = r.groups.find((g) => g.type === "partner")?.items[0];
    if (p) onDone(p.id, p.title);
    else setMode("nome"); // nessun match → crea per nome
  }

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div className="row" style={{ gap: 6 }}>
        {(["piva", "email", "nome"] as const).map((m) => (
          <button key={m} className={mode === m ? "btn-secondary" : "btn-mini"} onClick={() => { setMode(m); setLk(null); }}>
            {m === "piva" ? "P.IVA" : m === "email" ? "Email" : "Nome azienda"}
          </button>
        ))}
      </div>

      {mode === "piva" ? (
        <>
          <div className="row" style={{ gap: 8 }}>
            <input value={vat} onChange={(e) => setVat(e.target.value)} placeholder="P.IVA (es. IT03687990790)" style={inp()} />
            <button className="btn-secondary" disabled={busy || !vat.trim()} onClick={doLookup}>Verifica</button>
          </div>
          {lk && !lk.isNew ? (
            <div className="card" style={{ padding: 0, overflow: "hidden" }}>
              <div className="muted" style={{ padding: "6px 10px", fontSize: 12 }}>Già presenti — seleziona per evitare doppioni</div>
              {lk.existing.map((e) => (
                <button key={e.id} className="row" style={{ width: "100%", padding: "8px 10px", textAlign: "left", borderTop: "1px solid var(--line)", background: "transparent" }}
                  onClick={() => onDone(e.id, e.name)}>
                  <span style={{ fontWeight: 600 }}>{e.name}</span>
                  <span className="muted grow ell" style={{ fontSize: 12 }}>{e.vat} · {e.city} {e.country}</span>
                </button>
              ))}
            </div>
          ) : null}
          {lk && lk.isNew ? (
            <div className="card" style={{ padding: 12, display: "grid", gap: 8 }}>
              <div style={{ fontSize: 12 }} className="muted">
                Nuova azienda {lk.vies?.valid ? "· VIES valida" : lk.formatValid ? "· formato valido" : "· verifica manuale"}
              </div>
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ragione sociale" style={inp(!name.trim())} />
              {lk.prefill?.city || lk.prefill?.street ? (
                <div className="muted" style={{ fontSize: 12 }}>{[lk.prefill.street, lk.prefill.zip, lk.prefill.city].filter(Boolean).join(" ")}</div>
              ) : null}
              {enr ? <div className="muted" style={{ fontSize: 12 }}>007: {enr}</div> : null}
              <div className="row" style={{ justifyContent: "space-between" }}>
                <button className="btn-mini" disabled={busy} onClick={doEnrich}>Arricchisci 007</button>
                <button className="btn-primary" disabled={busy || !name.trim()} onClick={() => doCreate(name)}>Crea azienda</button>
              </div>
            </div>
          ) : null}
        </>
      ) : null}

      {mode === "email" ? (
        <div className="row" style={{ gap: 8 }}>
          <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email del contatto" style={inp()} />
          <button className="btn-secondary" disabled={busy || !email.trim()} onClick={doEmailSearch}>Cerca</button>
        </div>
      ) : null}

      {mode === "nome" ? (
        <div className="row" style={{ gap: 8 }}>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Nome azienda (extra-UE / manuale)" style={inp(!name.trim())} />
          <button className="btn-primary" disabled={busy || !name.trim()} onClick={() => doCreate(name)}>Crea</button>
        </div>
      ) : null}
    </div>
  );
}

// ── Step 2 — Contatto ─────────────────────────────────────────────────────────
function Step2({ busy, guard, companyId, companyName, onBack, onSkip, onDone }: {
  busy: boolean; guard: <T>(f: () => Promise<T>) => Promise<T>; companyId: number | null; companyName: string;
  onBack: () => void; onSkip: () => void; onDone: () => void;
}) {
  const [nome, setNome] = useState("");
  const [ruolo, setRuolo] = useState("");
  const [email, setEmail] = useState("");
  const [tel, setTel] = useState("");

  async function save() {
    await guard(() => createContact({
      data: { contatto: { nome, ruolo, email, telefono: tel }, azienda: { nome: "", dominio: "" }, indirizzo: { via: "", cap: "", citta: "", paese: "" } },
      linkCompanyId: companyId ?? undefined,
    }));
    onDone();
  }
  return (
    <div style={{ display: "grid", gap: 10 }}>
      <div className="muted" style={{ fontSize: 12 }}>Contatto in {companyName || "azienda"}</div>
      <input value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Nome e cognome" style={inp(!nome.trim())} />
      <input value={ruolo} onChange={(e) => setRuolo(e.target.value)} placeholder="Ruolo (es. Buyer)" style={inp()} />
      <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" style={inp()} />
      <input value={tel} onChange={(e) => setTel(e.target.value)} placeholder="Telefono" style={inp()} />
      <div className="row" style={{ justifyContent: "space-between" }}>
        <button className="btn-mini" onClick={onBack}>‹ Indietro</button>
        <div className="row" style={{ gap: 8 }}>
          <button className="btn-mini" onClick={onSkip}>Salta</button>
          <button className="btn-primary" disabled={busy || !nome.trim()} onClick={save}>Salva e continua</button>
        </div>
      </div>
    </div>
  );
}

// ── Step 3 — Opportunità ──────────────────────────────────────────────────────
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

// ── Step 4 — Azione commerciale ───────────────────────────────────────────────
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

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div className="muted" style={{ fontSize: 12 }}>Opportunità creata. Scegli l'azione commerciale.</div>
      <div className="row" style={{ gap: 10 }}>
        <a className="btn-secondary" href={`${BP}/partner/${companyId ?? ""}`} style={{ flex: 1, textAlign: "center" }}>
          Invia catalogo (composer)
        </a>
        <button className="btn-primary" style={{ flex: 1 }} disabled={busy || !companyId || interest.length === 0} onClick={quote}>
          Crea quotazione
        </button>
      </div>
      {interest.length === 0 ? <div className="muted" style={{ fontSize: 12 }}>Aggiungi prodotti allo step Opportunità per la quotazione.</div> : null}
      {result ? <div style={{ fontSize: 13, color: "var(--ok)" }}>{result}</div> : null}
      <div className="row" style={{ justifyContent: "flex-end", gap: 8 }}>
        {leadId ? <a className="btn-mini" href={`${BP}/lead/${leadId}`}>Apri opportunità</a> : null}
        <button className="btn-mini" onClick={onClose}>Chiudi</button>
      </div>
    </div>
  );
}
