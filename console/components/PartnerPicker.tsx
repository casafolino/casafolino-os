"use client";
// PartnerPicker — componente CONDIVISO di risoluzione partner (azienda + contatto).
// Estratto dal wizard preventivo: ricerca P.IVA (dedup+VIES) / Email / Nome, arricchimento 007
// opzionale, creazione azienda+contatto. NESSUNA azione di business: risolve il partner e delega.
// Ogni azione della console lo monta come primo step → onResolved({companyId, companyName, contactId?}).
//
// Resilienza (lezione console hang): le chiamate passano da postJSON con timeout duro; se VIES/007
// non rispondono, la creazione manuale procede comunque — mai uno spinner infinito.
import { useState } from "react";
import { vatLookup, enrich007, type VatLookup } from "@/lib/wizard";
import { createCompany } from "@/lib/cockpit";
import { createContact } from "@/lib/enrich";
import { universalSearch } from "@/lib/pipeline";

export type PartnerResolved = { companyId: number; companyName: string; contactId?: number };

function inp(bad = false): React.CSSProperties {
  return { width: "100%", padding: "8px 10px", borderRadius: 8, fontSize: 13,
    border: bad ? "1px solid var(--danger)" : "1px solid var(--line)", background: "var(--paper)" };
}

export function PartnerPicker({
  onResolved, onCancel, contactStep = true, intro,
}: {
  onResolved: (r: PartnerResolved) => void;
  onCancel?: () => void;
  contactStep?: boolean;
  intro?: string;
}) {
  const [phase, setPhase] = useState<"company" | "contact">("company");
  const [companyId, setCompanyId] = useState<number | null>(null);
  const [companyName, setCompanyName] = useState("");

  function resolveCompany(id: number, name: string) {
    setCompanyId(id);
    setCompanyName(name);
    if (contactStep) setPhase("contact");
    else onResolved({ companyId: id, companyName: name });
  }

  return (
    <div style={{ display: "grid", gap: 12 }}>
      {intro ? <div className="muted" style={{ fontSize: 12 }}>{intro}</div> : null}
      {phase === "company" ? (
        <CompanyStep onDone={resolveCompany} onCancel={onCancel} />
      ) : (
        <ContactStep
          companyId={companyId} companyName={companyName}
          onBack={() => setPhase("company")}
          onDone={(contactId) => onResolved({ companyId: companyId as number, companyName, contactId })}
          onSkip={() => onResolved({ companyId: companyId as number, companyName })}
        />
      )}
    </div>
  );
}

// ── Sotto-step Azienda (P.IVA dedup+VIES / Email / Nome) ──────────────────────
function CompanyStep({ onDone, onCancel }: { onDone: (id: number, name: string) => void; onCancel?: () => void }) {
  const [mode, setMode] = useState<"piva" | "email" | "nome">("piva");
  const [vat, setVat] = useState("");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [lk, setLk] = useState<VatLookup | null>(null);
  const [enr, setEnr] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function doLookup() {
    setErr(null); setBusy(true);
    try {
      const r = await vatLookup({ vat });
      setLk(r);
      if (r.prefill?.name) setName(r.prefill.name);
    } catch {
      // Resilienza: VIES/backend non risponde → consenti comunque creazione manuale.
      setErr("Verifica non disponibile — puoi creare manualmente.");
      setLk({ ok: false, normalizedVat: vat, formatValid: false, isNew: true, existing: [],
        vies: null, prefill: { name, vat, street: "", city: "", zip: "", country: "" } });
    } finally { setBusy(false); }
  }
  async function doEnrich() {
    setBusy(true);
    try {
      const r = await enrich007({ name: name || lk?.prefill?.name || "", vat });
      setEnr([r.enrichment.settore, r.enrichment.dimensione, r.enrichment.sito].filter(Boolean).join(" · "));
    } catch {
      setEnr(""); // best-effort, silenzioso: l'arricchimento non blocca mai la creazione
    } finally { setBusy(false); }
  }
  async function doCreate(nm: string, dom?: string, citta?: string) {
    setErr(null); setBusy(true);
    try {
      const r = await createCompany({ data: { nome: nm, dominio: dom, citta } });
      if (r.partnerId) onDone(r.partnerId, r.name || nm);
      else setErr(r.message || "Creazione fallita.");
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  async function doEmailSearch() {
    setErr(null); setBusy(true);
    try {
      const r = await universalSearch(email);
      const p = r.groups.find((g) => g.type === "partner")?.items[0];
      if (p) onDone(p.id, p.title);
      else setMode("nome"); // nessun match → crea per nome
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div className="row" style={{ gap: 6, justifyContent: "space-between" }}>
        <div className="row" style={{ gap: 6 }}>
          {(["piva", "email", "nome"] as const).map((m) => (
            <button key={m} className={mode === m ? "btn-secondary" : "btn-mini"} onClick={() => { setMode(m); setLk(null); setErr(null); }}>
              {m === "piva" ? "P.IVA" : m === "email" ? "Email" : "Nome azienda"}
            </button>
          ))}
        </div>
        {onCancel ? <button className="btn-mini" onClick={onCancel}>✕</button> : null}
      </div>

      {err ? <div style={{ fontSize: 12, color: "var(--danger)" }}>{err}</div> : null}

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

// ── Sotto-step Contatto (opzionale, skippabile) ───────────────────────────────
function ContactStep({ companyId, companyName, onBack, onDone, onSkip }: {
  companyId: number | null; companyName: string;
  onBack: () => void; onDone: (contactId?: number) => void; onSkip: () => void;
}) {
  const [nome, setNome] = useState("");
  const [ruolo, setRuolo] = useState("");
  const [email, setEmail] = useState("");
  const [tel, setTel] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function save() {
    setErr(null); setBusy(true);
    try {
      const r = await createContact({
        data: { contatto: { nome, ruolo, email, telefono: tel }, azienda: { nome: "", dominio: "" }, indirizzo: { via: "", cap: "", citta: "", paese: "" } },
        linkCompanyId: companyId ?? undefined,
      });
      onDone(r.partnerId);
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  return (
    <div style={{ display: "grid", gap: 10 }}>
      <div className="muted" style={{ fontSize: 12 }}>Contatto in {companyName || "azienda"}</div>
      <input value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Nome e cognome" style={inp(!nome.trim())} />
      <input value={ruolo} onChange={(e) => setRuolo(e.target.value)} placeholder="Ruolo (es. Buyer)" style={inp()} />
      <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" style={inp()} />
      <input value={tel} onChange={(e) => setTel(e.target.value)} placeholder="Telefono" style={inp()} />
      {err ? <div style={{ fontSize: 12, color: "var(--danger)" }}>{err}</div> : null}
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
