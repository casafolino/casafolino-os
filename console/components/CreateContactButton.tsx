"use client";
// Brief 8 — "Crea contatto" da una mail aperta. Apre il pannello arricchimento: l'IA propone
// (firma+dominio), dedup in cima, campi editabili taggati IA, niente si salva finché il manager
// non conferma "Rivedi e salva". Manager-only (gateway).
import { useEffect, useState } from "react";
import {
  enrichContact, createContact,
  type EnrichResult, type ProposedData, type DedupCompany,
} from "@/lib/enrich";

export function CreateContactButton({ mailId, small = true }: { mailId: number; small?: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className={small ? "btn-mini" : "btn-primary"} onClick={() => setOpen(true)}>Crea contatto</button>
      {open ? <EnrichPanel mailId={mailId} onClose={() => setOpen(false)} /> : null}
    </>
  );
}

function EnrichPanel({ mailId, onClose }: { mailId: number; onClose: () => void }) {
  const [res, setRes] = useState<EnrichResult | null>(null);
  const [data, setData] = useState<ProposedData | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [linkCompanyId, setLinkCompanyId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);

  useEffect(() => {
    enrichContact(mailId)
      .then((r) => { if (r && r.proposed) { setRes(r); setData(r.proposed); } else setErr(r?.message ?? "errore arricchimento"); })
      .catch((e) => setErr((e as Error).message));
  }, [mailId]);

  function upd(section: keyof ProposedData, field: string) {
    return (e: React.ChangeEvent<HTMLInputElement>) => {
      setData((d) => d ? ({ ...d, [section]: { ...d[section], [field]: e.target.value } }) : d);
    };
  }

  async function linkExisting(partnerId: number, label: string) {
    setBusy(true); setErr(null);
    try {
      const r = await createContact({ linkPartnerId: partnerId, mailId });
      if (r.ok) setDone(`Collegato a ${label}`); else setErr(r.message ?? "errore");
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  async function save() {
    if (!data) return;
    setBusy(true); setErr(null);
    try {
      const r = await createContact({ data, mailId, linkCompanyId: linkCompanyId ?? undefined });
      if (r.ok) setDone(r.linked ? "Collegato" : `Creato: ${r.name}`); else setErr(r.message ?? "errore");
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  const contacts = res?.dedupCandidates.contacts ?? [];
  const companies = res?.dedupCandidates.companies ?? [];

  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: 16 }}>
      <div className="card" onClick={(e) => e.stopPropagation()} style={{ width: "min(560px,100%)", maxHeight: "90vh", overflow: "auto", padding: 18, display: "flex", flexDirection: "column", gap: 12 }}>
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontWeight: 700, fontSize: 16 }}>Crea contatto</div>
          <button className="btn-mini" onClick={onClose}>✕</button>
        </div>

        {err ? <div style={{ color: "var(--danger)", fontSize: 13 }}>{err}</div> : null}

        {done ? (
          <>
            <div className="chip" style={{ background: "var(--ok-t)", color: "var(--ok)", alignSelf: "flex-start" }}>{done} ✓</div>
            <button className="btn-primary" onClick={onClose} style={{ alignSelf: "flex-end" }}>Chiudi</button>
          </>
        ) : !data ? (
          <div className="muted">Arricchimento IA in corso…</div>
        ) : (
          <>
            {/* stato body */}
            {res && !res.hasBody ? (
              <div className="empty-honest">Solo dominio — firma non disponibile in questa mail. Completa a mano.</div>
            ) : (
              <div className="chip" style={{ background: "var(--panel-2)", color: "var(--muted)", alignSelf: "flex-start" }}>Proposto dall'IA dalla firma</div>
            )}

            {/* dedup banner */}
            {contacts.length ? (
              <div className="card" style={{ padding: 10, background: "var(--warn-t)", border: "1px solid var(--warn)" }}>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Contatto già esistente</div>
                {contacts.map((c) => (
                  <div key={c.id} className="row" style={{ justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                    <span style={{ fontSize: 12 }}>{c.name} · {c.email}{c.company ? ` · ${c.company}` : ""}</span>
                    <button className="btn-mini" disabled={busy} onClick={() => linkExisting(c.id, c.name)}>Collega</button>
                  </div>
                ))}
              </div>
            ) : null}

            {companies.length ? (
              <div className="card" style={{ padding: 10, background: "var(--warn-t)", border: "1px solid var(--warn)" }}>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Azienda esistente (stesso dominio/nome)</div>
                {companies.map((c) => (
                  <CompanyDedupRow key={c.id} c={c} selected={linkCompanyId === c.id} onToggle={() => setLinkCompanyId((v) => v === c.id ? null : c.id)} />
                ))}
                <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>Seleziona per collegare il nuovo contatto a un'azienda esistente, o lascia per crearne una nuova.</div>
              </div>
            ) : null}

            {/* campi contatto */}
            <Section title="Contatto">
              <Field label="Nome" value={data.contatto.nome} onChange={upd("contatto", "nome")} ai={res?.source === "signature"} />
              <Field label="Ruolo" value={data.contatto.ruolo} onChange={upd("contatto", "ruolo")} ai={res?.source === "signature"} />
              <Field label="Email" value={data.contatto.email} onChange={upd("contatto", "email")} />
              <Field label="Telefono" value={data.contatto.telefono} onChange={upd("contatto", "telefono")} ai={res?.source === "signature"} />
            </Section>
            <Section title="Azienda">
              <Field label="Nome" value={data.azienda.nome} onChange={upd("azienda", "nome")} ai={res?.source === "signature"} disabled={!!linkCompanyId} />
              <Field label="Dominio" value={data.azienda.dominio} onChange={upd("azienda", "dominio")} disabled={!!linkCompanyId} />
            </Section>
            <Section title="Indirizzo">
              <Field label="Via" value={data.indirizzo.via} onChange={upd("indirizzo", "via")} ai={res?.source === "signature"} />
              <Field label="CAP" value={data.indirizzo.cap} onChange={upd("indirizzo", "cap")} ai={res?.source === "signature"} />
              <Field label="Città" value={data.indirizzo.citta} onChange={upd("indirizzo", "citta")} ai={res?.source === "signature"} />
            </Section>

            <button className="btn-primary" onClick={save} disabled={busy || !data.contatto.nome} style={{ alignSelf: "flex-end" }}>
              {busy ? "Salvo…" : "Rivedi e salva"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function CompanyDedupRow({ c, selected, onToggle }: { c: DedupCompany; selected: boolean; onToggle: () => void }) {
  return (
    <div className="row" style={{ justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
      <span style={{ fontSize: 12 }}>{c.name}{c.domain ? ` · ${c.domain}` : ""} <span className="muted">({c.strength})</span></span>
      <button className="btn-mini" onClick={onToggle} style={selected ? { background: "var(--accent)", color: "#fff" } : undefined}>
        {selected ? "Collegata ✓" : "Collega"}
      </button>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="muted" style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: ".04em", marginBottom: 4 }}>{title}</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>{children}</div>
    </div>
  );
}

function Field({ label, value, onChange, ai, disabled }: {
  label: string; value: string; onChange: (e: React.ChangeEvent<HTMLInputElement>) => void; ai?: boolean; disabled?: boolean;
}) {
  return (
    <div>
      <label className="muted" style={{ fontSize: 11 }}>{label} {ai && value ? <span className="chip" style={{ fontSize: 9, padding: "0 5px" }}>IA</span> : null}</label>
      <input value={value} onChange={onChange} disabled={disabled}
        style={{ width: "100%", padding: "7px 10px", borderRadius: 8, border: "1px solid var(--line)", fontSize: 13, opacity: disabled ? 0.5 : 1 }} />
    </div>
  );
}
